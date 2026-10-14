"""具体赛事名录：把 `calcdata/competitions.json` 展开成可加分的活动。

**为什么要有这个模块**

原来的「活动篮」里只有几条笼统的条目，比如「学生竞赛 · 团体项目（T/A/B 类，
含挑战杯、创新大赛、生命科学竞赛、iGEM）」。学生看到的是「参加竞赛能加分」，
但不知道**到底有哪些竞赛**、自己参加的那一个属于哪一档。这个模块把
《华南农业大学学生竞赛奖励办法》（华南农办〔2022〕38号）附件里的学科竞赛名录
逐条展开成一个 Activity：

    名录页（T 类 84 项 / A 类 16 项 / B 类 10 项）
        └─ competitions.json 的 competitions[]（内置数据，进 git）
             └─ 按 profile 挂上已核验的加分档位
                  └─ Activity(id = comp-a<附录>-<序号>) → 可直接加入活动篮

**联网数据**由 :mod:`harness.calc.online` 负责抓取与对账，缓存在
`data/cache/calc_competitions.json`（`data/` 不进 git）。联网发现的**新赛事**
同样会被展开成 Activity（多打一个 `competition-online` 的标），而只是「通知里
提到、还没进名录」的线索不进活动篮，只作为卡片展示，避免凭空造分值。

**数据可信度**：`profiles` 里的每个数字都抄自已核验的 `activities.json`；
「某个赛事属于哪一档」是组合口径（见各 profile 的 `note`），所以这些活动统一标
`provisional`，并保留到名录页与学院细则的双重出处。
"""
from __future__ import annotations

import copy
import html as htmlmod
import json
import re
import unicodedata
from pathlib import Path

from .model import Activity

# 仓库根目录（harness/calc/competitions.py → 上三级）
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DIR = REPO_ROOT / "calcdata"
OVERRIDE_DIR = REPO_ROOT / "data" / "calc"
ONLINE_CACHE = REPO_ROOT / "data" / "cache" / "calc_competitions.json"
FILENAME = "competitions.json"

CATEGORY = "学科竞赛"

# 附录号 → 名录归属（界面与出处都用得到）
APPENDIX_META: dict[int, dict] = {
    1: {
        "tier": "T",
        "title": "教育部中国高等教育学会科技竞赛名录",
        "subtitle": "《2023 全国普通高校大学生竞赛分析报告》竞赛目录",
        "organizer": "教育部 · 中国高等教育学会（全国普通高校大学生竞赛分析报告名录）",
    },
    2: {
        "tier": "A",
        "title": "中国学位与研究生教育学会研究生创新实践系列大赛名录",
        "subtitle": "2023 年中国研究生创新实践系列大赛主题赛事",
        "organizer": "中国学位与研究生教育学会",
    },
    3: {
        "tier": "B",
        "title": "广东省本科高校大学生十大学科竞赛名录",
        "subtitle": "广东省本科高校大学生十大学科竞赛",
        "organizer": "广东省教育厅（本科高校大学生十大学科竞赛）",
    },
}

# 这些赛事在《学生竞赛奖励办法》里被单独点名（T1 档、简称也叫得响）
SPECIAL_ORGANIZER = {
    "comp-a1-01": "教育部、共青团中央等（原「互联网+」）",
    "comp-a1-02": "共青团中央、中国科协、教育部等（大挑）",
    "comp-a1-03": "共青团中央、教育部等（小挑）",
    "comp-a1-44": "教育部高等学校生物技术、生物工程类专业教学指导委员会等",
}

# 默认成果档位的优先顺序（尽量给一个「大多数人会选」的档）
DEFAULT_ACHIEVE_ORDER = (
    "国家级 负责人",
    "T1 类 一等奖 负责人",
    "T2 类 一等奖 负责人",
    "A 类 一等奖 负责人",
    "B 类 一等奖 负责人",
    "国家级 一等奖 负责人",
    "国家级 一等奖 成员",
    "省部级 负责人",
    "市、校级 负责人",
    "参赛未获奖",
)


# --------------------------------------------------------------------------- #
# 一、页面解析（构建脚本与联网刷新共用同一套逻辑，避免两处口径不一致）
# --------------------------------------------------------------------------- #
APPENDIX_RE = re.compile(r"附录\s*([123])\s*[：:](.*)")
TIER_RE = re.compile(r"均为\s*([TAB])\s*类")
ITEM_RE = re.compile(r"^\s*(\d{1,3})\s*[.．、]?\s*(\S.*)$")
NOISE_RE = re.compile(
    r"^(备注|附录|联系我们|版权所有|管理登录|当前位置|序号|《|（[一二三四五六七八九十]）|"
    r"[0-9]{4}\s*年)")
TAIL_RE = re.compile(r"[（(]\s*(20\d\d\s*年[^）)]*|原[^）)]*|高职赛[^）)]*)")

# 生物类赛事的关键词。
#
# 别用「生物」做子串匹配：全国大学生**生物**流设计大赛、全国大学生**生物**理实验竞赛、
# 全国大学生**生物**联网设计竞赛中间都正好夹着「大学生生物」，会被误判成生物类。
# 所以只用无歧义的关键词，其余靠序号定点指认。
BIO_KEYS = ("生命科学", "生物化学", "生化实验")
GRAD_ONLY_KEYS = ("高职", "职业院校", "世界技能大赛")
SEQ_PROFILE_OVERRIDE = {
    (1, 1): "t1", (1, 2): "t1", (1, 3): "t1",
    (1, 44): "bio-t2",
    (3, 10): "bio-b",
}


def strip_html(html: str) -> list[str]:
    """HTML → 逐行文本。名录页是一串带序号的段落/表格行，这样够用。"""
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.S | re.I)
    body = re.search(r"<body.*?</body>", h, re.S | re.I)
    if body:
        h = body.group(0)
    h = re.sub(r"<br\s*/?>", "\n", h, flags=re.I)
    h = re.sub(r"</(p|div|tr|li|h[1-6]|td)>", "\n", h, flags=re.I)
    h = re.sub(r"<[^>]+>", "", h)
    h = htmlmod.unescape(h)
    h = re.sub(r"[ \t\u00a0]+", " ", h)
    return [ln.strip() for ln in h.splitlines() if ln.strip()]


def parse_catalog(lines: list[str]) -> list[dict]:
    """按附录分段解析出名录条目。

    用「预期序号」而不是只靠正则认条目：页面里既有 `1 中国国际…`（无分隔符），
    也有 `1．中国研究生…`（全角点），还有 `2023年中国研究生创新实践系列大赛`
    这种以年份开头的标题行。要求序号正好等于上一条 +1，标题行与正文行会被自然排除。
    """
    out: list[dict] = []
    appendix = 0
    tier = ""
    expected = 1
    for line in lines:
        m = APPENDIX_RE.search(line)
        if m:
            appendix = int(m.group(1))
            t = TIER_RE.search(line)
            tier = t.group(1) if t else ""
            expected = 1
            continue
        if not appendix or NOISE_RE.match(line):
            continue
        m = ITEM_RE.match(line)
        if not m:
            continue
        seq = int(m.group(1))
        if seq != expected:
            continue
        expected += 1
        raw = m.group(2).strip()
        name, tail = raw, ""
        tm = TAIL_RE.search(raw)
        if tm:
            name = raw[: tm.start()].strip()
            tail = raw[tm.start():].strip()
        name = name.rstrip("－-—· ").strip()
        out.append({"seq": seq, "name": name, "raw": raw,
                    "appendix": appendix, "tier": tier, "tail": tail})
    return out


def pick_profile(appendix: int, seq: int, name: str, tail: str = "") -> str:
    """这条赛事该挂哪个加分档位（profiles 的键）。"""
    key = (appendix, seq)
    if key in SEQ_PROFILE_OVERRIDE:
        return SEQ_PROFILE_OVERRIDE[key]
    if appendix == 2:
        return "grad-a"
    if any(k in tail for k in GRAD_ONLY_KEYS) or any(k in name for k in GRAD_ONLY_KEYS):
        # 高职赛道：本科生不适用，仍给档位（按非生物类折半）但界面上会标出来
        return "nonbio-b" if appendix == 3 else "nonbio-t2"
    is_bio = any(k in name for k in BIO_KEYS)
    if appendix == 1:
        return "bio-t2" if is_bio else "nonbio-t2"
    return "bio-b" if is_bio else "nonbio-b"


def normalize_name(name: str) -> str:
    """赛事名归一化，用于「内置 ↔ 联网」对账。

    去掉引号、括号、空白、标点，统一全角加号与大小写。只用来比对，
    不改展示用的名称。
    """
    s = unicodedata.normalize("NFKC", str(name or ""))
    s = s.replace("＋", "+").replace("﹢", "+")
    s = re.sub(r"[\s\u3000]+", "", s)
    s = re.sub(r"[“”\"'‘’《》〈〉()（）\[\]【】·・,，.。、:：;；!！?？\-—－_/\\|+&]", "", s)
    return s.lower()


# --------------------------------------------------------------------------- #
# 二、读写数据文件
# --------------------------------------------------------------------------- #
def default_path() -> Path:
    override = OVERRIDE_DIR / FILENAME
    return override if override.is_file() else DEFAULT_DIR / FILENAME


def load_competitions(path: str | Path | None = None) -> tuple[dict, list[str]]:
    """读 competitions.json。返回 (数据, 警告列表)。

    文件不存在时返回空数据 + 警告：赛事名录是**可选增强**，缺了活动篮里
    还有通用条目，不该让整个计算器起不来。
    """
    p = Path(path) if path else default_path()
    if not p.is_file():
        return {}, [f"没有找到赛事名录文件：{p}（活动篮将只显示通用加分项）"]
    try:
        raw = json.loads(p.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        return {}, [f"{p.name} 不是合法 JSON：第 {e.lineno} 行 {e.msg}"]
    if not isinstance(raw, dict):
        return {}, [f"{p.name} 顶层不是对象"]
    return raw, []


def load_online_cache(path: str | Path | None = None) -> dict:
    """读联网刷新的缓存（没有就返回 {}）。"""
    p = Path(path) if path else ONLINE_CACHE
    if not p.is_file():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def save_online_cache(data: dict, path: str | Path | None = None) -> Path:
    """原子写缓存：先写临时文件再 replace。

    Web 层是多线程的，两次并发刷新如果直接原地写，可能让另一条读取线程
    读到半截 JSON；先写 `.tmp` 再 `os.replace` 就不会。
    """
    import os

    p = Path(path) if path else ONLINE_CACHE
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                   encoding="utf-8")
    os.replace(tmp, p)
    return p


# --------------------------------------------------------------------------- #
# 三、名录 → Activity
# --------------------------------------------------------------------------- #
def _pick_default_achieve(achieve_map: dict) -> str:
    for key in DEFAULT_ACHIEVE_ORDER:
        if key in achieve_map:
            return key
    return next(iter(achieve_map), "")


def _profile_of(profiles: dict, key: str) -> dict:
    prof = profiles.get(key)
    if isinstance(prof, dict):
        return prof
    # 名录里挂了一个不存在的档位：退回一个保守但可用的档，并在 note 里说明
    for fallback in ("nonbio-t2", "bio-t2", "t1", "grad-a", "nonbio-b", "bio-b"):
        if isinstance(profiles.get(fallback), dict):
            return dict(profiles[fallback], _missing_profile=key)
    return {}


def build_activity(item: dict, profiles: dict, catalog_page: dict,
                   *, online: bool = False, confirmed_at: str = "") -> Activity:
    """把名录里的一条赛事展开成可加分的 Activity。"""
    appendix = int(item.get("appendix") or 1)
    ameta = APPENDIX_META.get(appendix, APPENDIX_META[1])
    profile_key = str(item.get("profile") or pick_profile(
        appendix, int(item.get("seq") or 0), str(item.get("name") or ""),
        str(item.get("tail_note") or "")))
    prof = _profile_of(profiles, profile_key)
    achieve_map = copy.deepcopy(prof.get("achieve_map") or {})
    channels = {str(k): float(v) for k, v in (prof.get("channels") or {}).items()}
    rubric = {str(k): str(v) for k, v in (prof.get("rubric") or {}).items()}

    tier = str(item.get("tier") or ameta["tier"])
    name = str(item.get("name") or "").strip()
    seq = item.get("seq")
    tags = [str(t) for t in (item.get("tags") or ["具体赛事", f"{tier} 类", "名录"])]
    if online:
        tags.append("联网新增")
    if prof.get("label"):
        tags.append(str(prof["label"]))
    if prof.get("_missing_profile"):
        tags.append("档位待补")

    note_bits = []
    if item.get("note"):
        note_bits.append(str(item["note"]))
    if item.get("tail_note"):
        note_bits.append(f"名录原名括注：{item['tail_note']}")
    if prof.get("note"):
        note_bits.append(str(prof["note"]))
    if prof.get("_missing_profile"):
        note_bits.append(
            f"名录里挂的档位「{prof['_missing_profile']}」在 profiles 里不存在，"
            f"这里临时按「{prof.get('label','')}」折算，请检查 competitions.json。")
    if online and confirmed_at:
        note_bits.append(f"此条由联网刷新于 {confirmed_at} 从官方名录页发现（内置数据里没有）。")

    source_bits = [
        f"名录：{catalog_page.get('title','《华南农业大学学生竞赛奖励办法》学科竞赛名录')}"
        f"（{catalog_page.get('url','')}，{catalog_page.get('published','')}发布）"
        f"——附录{appendix} {ameta['title']}，均记为 {tier} 类。",
    ]
    if prof.get("source"):
        source_bits.append(f"档位「{prof.get('label', profile_key)}」：{prof['source']}")

    return Activity(
        id=str(item.get("id") or f"comp-a{appendix}-{seq:02d}"),
        name=name,
        category=CATEGORY,
        level=str(item.get("level") or ("省级" if appendix == 3 else "国家级")),
        organizer=SPECIAL_ORGANIZER.get(str(item.get("id") or ""), ameta["organizer"]),
        channels=channels,
        achieve_map=achieve_map,
        default_achieve=_pick_default_achieve(achieve_map),
        rubric=rubric,
        discount=str(prof.get("discount") or "none"),
        timing=str(item.get("timing") or "报名时间以当年赛事通知为准"),
        eligibility=str(item.get("eligibility") or (
            "在校本科生（按赛事章程组队/个人参赛）；同一项目不累计，"
            "不同赛事可累计")),
        url=str(catalog_page.get("url") or ""),
        source=" ".join(source_bits),
        confidence=str(prof.get("confidence") or "provisional"),
        note=" ".join(note_bits),
        tags=tags,
        list_kind="competition-online" if online else "competition",
        extra={
            "seq": seq,
            "appendix": appendix,
            "appendix_title": ameta["title"],
            "tier": tier,
            "tier_label": f"{tier} 类",
            "profile": profile_key,
            "profile_label": prof.get("label", ""),
            "raw_name": item.get("raw_name") or item.get("raw") or name,
            "aliases": list(item.get("aliases") or []),
            "online": bool(online),
            "confirmed_at": confirmed_at,
            "catalog_url": catalog_page.get("url", ""),
        },
    )


def _online_extra_items(raw: dict, online: dict) -> list[dict]:
    """联网名录里、内置数据里没有的条目（按附录自动挂档位）。"""
    builtin = {
        normalize_name(c.get("name"))
        for c in (raw.get("competitions") or []) if c.get("name")
    }
    for c in (raw.get("competitions") or []):
        for a in (c.get("aliases") or []):
            builtin.add(normalize_name(a))
    seen: set[str] = set()
    out: list[dict] = []
    for e in (online.get("catalog") or []):
        name = str(e.get("name") or "").strip()
        key = normalize_name(name)
        if not name or not key or key in builtin or key in seen:
            continue
        seen.add(key)
        appendix = int(e.get("appendix") or 1)
        seq = int(e.get("seq") or 0)
        profile = pick_profile(appendix, seq, name, str(e.get("tail") or ""))
        out.append({
            "id": f"comp-online-a{appendix}-{seq:02d}",
            "seq": seq,
            "appendix": appendix,
            "name": name,
            "tier": str(e.get("tier") or APPENDIX_META.get(appendix, {}).get("tier", "T")),
            "profile": profile,
            "level": "省级" if appendix == 3 else "国家级",
            "tail_note": str(e.get("tail") or ""),
            "tags": ["具体赛事", f"{e.get('tier') or 'T'} 类", "名录"],
        })
    return out


def build_activities(raw: dict, online: dict | None = None
                     ) -> tuple[list[Activity], dict, list[str]]:
    """内置 + 联网新增 → Activity 列表，外加给前端用的元信息。

    返回 `(activities, meta, warnings)`。`meta["online"]` 里有联网对账结果、
    刷新时间与「线索」（通知里提到、还没进名录的赛事），前端据此画刷新状态条。
    """
    warnings: list[str] = []
    online = online or {}
    catalog_page = dict((raw.get("meta") or {}).get("catalog_page") or {})
    profiles = dict(raw.get("profiles") or {})
    confirmed_at = str(online.get("fetched_at") or "")

    activities: list[Activity] = []
    for item in (raw.get("competitions") or []):
        if not isinstance(item, dict) or not item.get("name"):
            continue
        try:
            activities.append(build_activity(item, profiles, catalog_page))
        except Exception as e:                       # noqa: BLE001 - 数据问题不该炸整页
            warnings.append(f"名录条目展开失败（{item.get('id') or item.get('name')}）："
                            f"{type(e).__name__}: {e}")

    extras: list[Activity] = []
    for item in _online_extra_items(raw, online):
        try:
            extras.append(build_activity(item, profiles, catalog_page,
                                         online=True, confirmed_at=confirmed_at))
        except Exception as e:                       # noqa: BLE001
            warnings.append(f"联网新增条目展开失败（{item.get('name')}）：{e}")

    counts: dict[str, int] = {}
    for a in activities:
        tier = str(a.extra.get("tier") or "")
        counts[tier] = counts.get(tier, 0) + 1

    meta = {
        "file": str(default_path()),
        "updated": (raw.get("meta") or {}).get("updated", ""),
        "basis": (raw.get("meta") or {}).get("basis", ""),
        "disclaimer": (raw.get("meta") or {}).get("disclaimer", ""),
        "catalog_page": catalog_page,
        "refresh_sources": list((raw.get("meta") or {}).get("refresh_sources") or []),
        "appendix": [
            {"appendix": k, **v,
             "count": sum(1 for a in activities if a.extra.get("appendix") == k)}
            for k, v in APPENDIX_META.items()
        ],
        "counts": {**counts, "total": len(activities), "online_added": len(extras)},
        "profiles": {
            k: {"label": v.get("label", ""), "note": v.get("note", ""),
                "source": v.get("source", ""), "confidence": v.get("confidence", ""),
                "achieve_map": v.get("achieve_map", {})}
            for k, v in profiles.items() if isinstance(v, dict)
        },
        "online": _online_meta(online) if online else None,
    }
    return activities + extras, meta, warnings


def _online_meta(online: dict) -> dict:
    """把缓存文件里给前端看的那部分挑出来（别名、未进名录的线索等）。"""
    diff = dict(online.get("diff") or {})
    return {
        "fetched_at": online.get("fetched_at", ""),
        "catalog_url": online.get("catalog_url", ""),
        "sources": list(online.get("sources") or []),
        "diff": diff,
        "clues": list(online.get("clues") or []),
        "counts": online.get("counts") or {},
    }
