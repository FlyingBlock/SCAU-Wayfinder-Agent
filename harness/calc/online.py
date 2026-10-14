"""活动篮的「刷新联网」：抓官网、和内置名录对账、发现新赛事与线索。

设计原则（和项目里其它抓取一致）：

1. **不调模型、不要 key、不花钱**。只用标准库 urllib + 正则，抓的是学校公开页面。
   断网时就退回内置数据，页面上明确显示「联网失败，仍用内置数据」，绝不让
   计算器因为没网而算不出来 —— 计算器本来就要能离线单独部署。
2. **不发明分值**。联网只做两件事：
   · 抓《学生竞赛奖励办法》名录页 → 和内置 `calcdata/competitions.json` 对账，
     报出新增 / 改名 / 级别变化，新增的赛事按附录自动挂上对应加分档位；
   · 抓几个竞赛通知栏目 → 提炼出「还有哪些活动」的线索卡片（不直接加分）。
3. **结果落盘**：`data/cache/calc_competitions.json`（`data/` 不进 git）。
   下一次打开页面直接读缓存，不用每刷一次页面都去抓学校服务器。
4. **礼貌抓取**：复用 :class:`harness.fetcher.Fetcher` 的限速与 robots 检查。

联网失败时**保留上一次成功的名录**（`stale_catalog`），只更新这次抓取的状态，
免得一次抽风把之前发现的新赛事抹掉。
"""
from __future__ import annotations

import datetime as _dt
import re
import time
import urllib.parse
from pathlib import Path

from ..fetcher import Fetcher
from . import competitions as comp

# HTTP 头只能是 latin-1，User-Agent 必须全 ASCII（写中文会 UnicodeEncodeError）
USER_AGENT = "Mozilla/5.0 (compatible; SCAU-Wayfinder/0.1; teaching-research-tool)"

# 默认抓取清单（正常情况下来自 competitions.json 的 meta.refresh_sources）
FALLBACK_SOURCES: list[dict] = [
    {"title": "《学生竞赛奖励办法》学科竞赛名录",
     "url": "https://sfs.scau.edu.cn/2026/0926/c20310a447244/page.htm",
     "kind": "catalog"},
    {"title": "校团委 · 挑战杯专栏", "url": "https://xtw.scau.edu.cn/tzb/list.htm",
     "kind": "notice"},
    {"title": "创新创业学院 · 通知公告", "url": "https://cxcyxy.scau.edu.cn/4449/list.htm",
     "kind": "notice"},
    {"title": "生命科学学院 · 学生通知", "url": "https://life.scau.edu.cn/xstz/list.htm",
     "kind": "notice"},
]

# 通知标题里出现这些词，才算「跟竞赛/项目有关」，别把普通通知也当线索。
# 刻意不收「选拔」「立项」这种泛词：否则「选拔年级委员」「课程立项」都会被当成赛事。
NOTICE_KEYWORDS = (
    "竞赛", "大赛", "挑战赛", "赛事", "选拔赛", "创新创业", "大创", "互联网+",
    "挑战杯", "训练计划", "项目申报", "学科竞赛", "杯",
)
# 明显是导航/栏目名的链接，跳过
NOTICE_NOISE = ("更多", "首页", "列表", "上一页", "下一页", "尾页", "学校主页",
                "English", "登录", "网站地图")

A_RE = re.compile(r"<a\b([^>]*)>(.*?)</a>", re.S | re.I)
ATTR_RE = re.compile(r"([\w:-]+)\s*=\s*[\"']([^\"']*)[\"']")
DATE_RE = re.compile(r"(20\d\d)\s*[-/年.]\s*(\d{1,2})\s*[-/月.]\s*(\d{1,2})")
TAG_RE = re.compile(r"<[^>]+>")

CATALOG_MIN_ITEMS = 20      # 名录页解析出少于这么多条，视为页面结构变了


def _now() -> str:
    return _dt.datetime.now().astimezone().replace(microsecond=0).isoformat()


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", TAG_RE.sub("", text or "")).strip()


def _title_of(text: str, limit: int = 80) -> str:
    """从链接文本里切出真正的标题。

    webplus 的列表页常常把「标题 + 摘要」整块套在一个 <a> 里，直接取文本会得到
    很长一串（标题后面跟着正文开头）。标题与摘要之间基本都有空格分隔，所以先按
    空格切；切不开再按长度截断，宁可短一点也别把摘要当标题。
    """
    text = _clean(text)
    if not text:
        return ""
    head = text.split(" ", 1)[0]
    if len(head) >= 8:
        text = head
    return text[:limit].strip()


def sources_from(raw: dict | None, kind: str | None = None) -> list[dict]:
    """从 competitions.json 的 meta.refresh_sources 取源；没有就用兜底清单。"""
    srcs = []
    for s in ((raw or {}).get("meta") or {}).get("refresh_sources") or []:
        if isinstance(s, dict) and s.get("url"):
            srcs.append({"title": str(s.get("title") or s["url"]),
                         "url": str(s["url"]), "kind": str(s.get("kind") or "notice"),
                         "use": str(s.get("use") or "")})
    if not srcs:
        srcs = [dict(s) for s in FALLBACK_SOURCES]
    if kind:
        return [s for s in srcs if s["kind"] == kind]
    return srcs


# --------------------------------------------------------------------------- #
# 通知栏目 → 「还有哪些活动」的线索
# --------------------------------------------------------------------------- #
def parse_notice_links(html: str, page_url: str) -> list[dict]:
    """从栏目列表页里提炼出与竞赛/项目有关的通知条目。"""
    out: list[dict] = []
    seen: set[str] = set()
    for raw_attrs, inner in A_RE.findall(html):
        attrs = {k.lower(): v for k, v in ATTR_RE.findall(raw_attrs)}
        href = (attrs.get("href") or "").strip()
        if not href or href.startswith(("#", "javascript:", "mailto:")):
            continue
        title = _title_of(attrs.get("title") or inner)
        if not title or len(title) < 8:
            continue
        if any(n in title for n in NOTICE_NOISE):
            continue
        if not any(k in title for k in NOTICE_KEYWORDS):
            continue
        url = urllib.parse.urljoin(page_url, href)
        if not url.startswith("http"):
            continue
        key = comp.normalize_name(title)
        if key in seen:
            continue
        seen.add(key)
        # 日期：先看链接附近的文本（webplus 列表页日期常在同一行）
        tail = html[html.find(raw_attrs) + len(raw_attrs):][:400] if raw_attrs in html else ""
        m = DATE_RE.search(_clean(inner) + " " + _clean(tail))
        pub = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else ""
        out.append({"title": title, "url": url, "pub_date": pub})
    return out


def match_clue(title: str, catalog: list[dict], builtin: list[dict]) -> dict:
    """把一条通知和名录/内置赛事对上号（松匹配：名称互为子串）。"""
    ntitle = comp.normalize_name(title)
    for c in catalog:
        nm = comp.normalize_name(c.get("name"))
        if nm and (nm in ntitle or ntitle in nm):
            return {"matched_name": c.get("name", ""), "matched_id": c.get("id", ""),
                    "matched_tier": c.get("tier", "")}
    for c in builtin:
        for candidate in [c.get("name")] + list(c.get("aliases") or []):
            nm = comp.normalize_name(candidate)
            if nm and len(nm) >= 4 and (nm in ntitle or ntitle in nm):
                return {"matched_name": c.get("name", ""),
                        "matched_id": c.get("id", ""),
                        "matched_tier": c.get("tier", "")}
    return {"matched_name": "", "matched_id": "", "matched_tier": ""}


# --------------------------------------------------------------------------- #
# 主流程
# --------------------------------------------------------------------------- #
def refresh(raw: dict | None = None, *, timeout: int = 12, retries: int = 1,
            max_notice_pages: int = 3, path: str | Path | None = None) -> dict:
    """抓一遍官网 → 对账 → 写缓存 → 返回本次刷新的摘要。

    `raw` 是内置 competitions.json 的内容（不传就自己读一遍）。
    """
    raw = raw if raw is not None else comp.load_competitions()[0]
    builtin = list((raw or {}).get("competitions") or [])
    catalog_page = dict(((raw or {}).get("meta") or {}).get("catalog_page") or {})
    srcs = sources_from(raw)
    catalog_srcs = [s for s in srcs if s["kind"] == "catalog"]
    notice_srcs = [s for s in srcs if s["kind"] != "catalog"][:max_notice_pages]
    if not catalog_srcs:
        catalog_srcs = [s for s in FALLBACK_SOURCES if s["kind"] == "catalog"]

    fetcher = Fetcher(USER_AGENT, timeout=timeout, retries=retries,
                      delay=0.3, jitter=0.2, cache_enabled=False)

    fetched_at = _now()
    source_reports: list[dict] = []
    catalog: list[dict] = []
    catalog_ok = False
    clues: list[dict] = []

    # ---- ① 名录页 -------------------------------------------------------- #
    for s in catalog_srcs:
        t0 = time.time()
        res = fetcher.fetch(s["url"])
        report = {
            "title": s.get("title") or s["url"], "url": s["url"], "kind": "catalog",
            "ok": bool(res.ok), "status": res.status, "error": res.error or "",
            "bytes": res.bytes, "items": 0, "elapsed": round(time.time() - t0, 2),
            "use": s.get("use", ""),
        }
        if res.ok and res.text:
            entries = comp.parse_catalog(comp.strip_html(res.text))
            report["items"] = len(entries)
            if len(entries) >= CATALOG_MIN_ITEMS:
                catalog = entries
                catalog_ok = True
                report["note"] = (f"解析出 {len(entries)} 条赛事"
                                  f"（T {sum(1 for e in entries if e['tier'] == 'T')} / "
                                  f"A {sum(1 for e in entries if e['tier'] == 'A')} / "
                                  f"B {sum(1 for e in entries if e['tier'] == 'B')}）")
            else:
                report["ok"] = False
                report["error"] = (f"只解析出 {len(entries)} 条，页面结构可能变了"
                                   f"（阈值 {CATALOG_MIN_ITEMS}）")
        source_reports.append(report)

    # ---- ② 各竞赛通知栏目 → 线索 ---------------------------------------- #
    seen_clues: set[str] = set()
    for s in notice_srcs:
        t0 = time.time()
        res = fetcher.fetch(s["url"])
        n = 0
        report = {
            "title": s.get("title") or s["url"], "url": s["url"], "kind": "notice",
            "ok": bool(res.ok), "status": res.status, "error": res.error or "",
            "bytes": res.bytes, "items": 0, "elapsed": round(time.time() - t0, 2),
            "use": s.get("use", ""),
        }
        if res.ok and res.text:
            for item in parse_notice_links(res.text, res.final_url or s["url"]):
                key = comp.normalize_name(item["title"])
                if key in seen_clues:
                    continue
                seen_clues.add(key)
                hit = match_clue(item["title"], catalog, builtin)
                clues.append({
                    "title": item["title"], "url": item["url"],
                    "pub_date": item["pub_date"],
                    "source": report["title"], "source_url": s["url"], **hit,
                })
                n += 1
            report["items"] = n
        source_reports.append(report)

    # 新的排在前面：栏目列表页的顺序不一定可靠，按发布日期倒排更直观
    clues.sort(key=lambda c: (c.get("pub_date") or "0000-00-00"), reverse=True)

    # ---- ③ 对账 ---------------------------------------------------------- #
    diff = diff_catalog(builtin, catalog)
    diff["ok"] = catalog_ok
    if not catalog_ok:
        diff["note"] = ("没能拿到官方名录页（或页面结构变了），本次只用通知栏目更新线索，"
                        "内置名录保持不变。")

    # 联网失败时保留上一次成功的名录，别让一次抽风抹掉已发现的新赛事
    prev = comp.load_online_cache(path)
    stale = False
    if not catalog and (prev.get("catalog")):
        catalog = list(prev["catalog"])
        stale = True
        diff["note"] = (diff.get("note", "") +
                        " 已保留上一次成功抓取的名录。").strip()

    counts = {
        "catalog_total": len(catalog),
        "T": sum(1 for e in catalog if e["tier"] == "T"),
        "A": sum(1 for e in catalog if e["tier"] == "A"),
        "B": sum(1 for e in catalog if e["tier"] == "B"),
        "added": len(diff["added"]),
        "removed": len(diff["removed"]),
        "renamed": len(diff["renamed"]),
        "clues": len(clues),
        "matched_clues": sum(1 for c in clues if c.get("matched_id")),
    }
    data = {
        "fetched_at": fetched_at,
        "catalog_url": (catalog_page.get("url")
                        or (catalog_srcs[0]["url"] if catalog_srcs else "")),
        "catalog_ok": catalog_ok,
        "stale_catalog": stale,
        "sources": source_reports,
        "catalog": catalog,
        "counts": counts,
        "diff": diff,
        "clues": clues[:60],
    }
    comp.save_online_cache(data, path)
    data["cache_path"] = str(path or comp.ONLINE_CACHE)
    data["ok"] = catalog_ok or bool(clues)
    return data


def diff_catalog(builtin: list[dict], online: list[dict]) -> dict:
    """内置名录 ↔ 联网名录的差异。

    以**归一化名称**为主键比：改名（同一序号不同名称）、级别变化（附录/tier 变了）
    都单独列出来，这样学生能看出「官方更新了名录」而不是我们数据坏了。
    """
    added: list[dict] = []
    removed: list[dict] = []
    renamed: list[dict] = []
    tier_changed: list[dict] = []

    b_by_name = {comp.normalize_name(c.get("name")): c for c in builtin if c.get("name")}
    o_by_name = {comp.normalize_name(e.get("name")): e for e in online if e.get("name")}
    b_by_seq = {(c.get("appendix"), c.get("seq")): c for c in builtin}
    o_by_seq = {(e.get("appendix"), e.get("seq")): e for e in online}

    for key, entry in o_by_name.items():
        if key in b_by_name:
            b = b_by_name[key]
            if str(b.get("tier")) != str(entry.get("tier")) or \
                    int(b.get("appendix") or 0) != int(entry.get("appendix") or 0):
                tier_changed.append({
                    "name": entry["name"],
                    "from": f"附录{b.get('appendix')} {b.get('tier')} 类",
                    "to": f"附录{entry.get('appendix')} {entry.get('tier')} 类",
                })
            continue
        # 同序号但名字变了 → 改名
        skey = (entry.get("appendix"), entry.get("seq"))
        b = b_by_seq.get(skey)
        if b and comp.normalize_name(b.get("name")) not in o_by_name:
            renamed.append({"seq": entry.get("seq"), "from": b.get("name"),
                            "to": entry.get("name"),
                            "tier": entry.get("tier"), "appendix": entry.get("appendix")})
        else:
            added.append({"seq": entry.get("seq"), "name": entry.get("name"),
                          "tier": entry.get("tier"), "appendix": entry.get("appendix"),
                          "tail": entry.get("tail", "")})

    for key, b in b_by_name.items():
        if key not in o_by_name and (b.get("appendix"), b.get("seq")) not in o_by_seq:
            removed.append({"seq": b.get("seq"), "name": b.get("name"),
                            "tier": b.get("tier"), "appendix": b.get("appendix")})
    return {"added": added, "removed": removed, "renamed": renamed,
            "tier_changed": tier_changed,
            "note": ("与内置名录完全一致，官方名录暂无变化"
                     if not (added or removed or renamed or tier_changed) else "")}
