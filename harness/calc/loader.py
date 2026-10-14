"""读取计算器的数据文件（`calcdata/*.json`）。

用 JSON 而不是 YAML，是因为本仓库刻意不依赖 PyYAML（沙箱装不了包，见
`harness/seed.py` 的说明），而 JSON 是标准库自带的。但 JSON 不允许注释，
所以这里约定：

- 顶层 `"_comment"` 字段放整份文件的人类说明；
- 数组元素里的 `"_comment"` / `"note"` 字段放条目级说明；
- 对象里以 `_` 开头的键在读入时一律忽略。

数据文件清单：

| 文件 | 内容 |
|---|---|
| `rules.json`      | 绩点折算表、综测权重、加分折算系数 |
| `majors.json`     | 专业培养方案（课程、学分构成） |
| `goals.json`      | 保研 / 考研 / 奖学金门槛 |
| `activities.json` | 可加分活动与竞赛清单 |
| `competitions.json` | 《学生竞赛奖励办法》名录里的**具体赛事**（可选增强） |

**放在哪**：默认读仓库根的 `calcdata/`（会进 git，所以 clone 下来就有）。
如果 `data/calc/` 下存在同名文件，**优先用那一份** —— 那个目录在
`.gitignore` 里，适合放你按本学院细则改过的私人版本，既覆盖默认值
又不会被 git 跟踪。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from . import competitions as competitions_mod
from .model import (
    Activity,
    Course,
    CreditGroup,
    Goal,
    GradeTable,
    Major,
    Requirement,
    Rules,
    ScoreBand,
)
from .basket import DEFAULT_CHANNEL_RUBRIC

# 仓库根目录（harness/calc/loader.py → 上三级）
REPO_ROOT = Path(__file__).resolve().parents[2]
# 数据目录：默认进 git 的那份，以及可选的本地覆盖
DEFAULT_DIR = REPO_ROOT / "calcdata"
OVERRIDE_DIR = REPO_ROOT / "data" / "calc"

# 需要读的四个文件（赛事名录是可选增强，缺了只报警告）
_DATA_FILES = ("rules.json", "majors.json", "goals.json", "activities.json")
_OPTIONAL_FILES = ("competitions.json",)


class CalcDataError(RuntimeError):
    """数据文件缺失或格式不对。"""


@dataclass
class CalcData:
    rules: Rules = field(default_factory=Rules)
    majors: list[Major] = field(default_factory=list)
    goals: list[Goal] = field(default_factory=list)
    activities: list[Activity] = field(default_factory=list)
    meta: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    # 赛事名录的元信息（名录页出处、附录构成、联网刷新状态…），前端要用
    competitions: dict = field(default_factory=dict)

    def major(self, major_id: str) -> Major | None:
        for m in self.majors:
            if m.id == major_id:
                return m
        return None

    def activity(self, activity_id: str) -> Activity | None:
        for a in self.activities:
            if a.id == activity_id:
                return a
        return None


def _read_json(path: Path) -> dict:
    if not path.is_file():
        raise CalcDataError(f"缺少数据文件：{path}")
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as e:
        raise CalcDataError(f"{path.name} 不是合法 JSON：第 {e.lineno} 行 {e.msg}") from e


def _num(val, default: float = 0.0) -> float:
    try:
        if val is None or val == "":
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


def _strip_private(obj):
    """递归去掉以 `_` 开头的键（注释位），避免注释混进数值字典。"""
    if isinstance(obj, dict):
        return {k: _strip_private(v) for k, v in obj.items()
                if not str(k).startswith("_")}
    if isinstance(obj, list):
        return [_strip_private(v) for v in obj]
    return obj


# --------------------------------------------------------------------------- #
def _load_grade_table(raw: dict) -> GradeTable:
    bands = [
        ScoreBand(
            lo=_num(b.get("lo")), hi=_num(b.get("hi"), 100.0),
            gp=_num(b.get("gp")), mode=str(b.get("mode", "fixed")),
            lp=_num(b.get("lp")), hp=_num(b.get("hp")),
            note=str(b.get("note", "")),
        )
        for b in (raw.get("bands") or [])
    ]
    # 未配置上下界时补全，避免出现空隙
    for i, band in enumerate(bands):
        if band.mode == "linear" and not band.hp:
            band.hp = band.gp
            band.lp = 0.0
    return GradeTable(
        name=str(raw.get("name", "百分制")),
        max_gp=_num(raw.get("max_gp"), 5.0),
        bands=bands,
        levels={str(k): _num(v) for k, v in (raw.get("levels") or {}).items()},
        fail_score=_num(raw.get("fail_score"), 60.0),
        retake_policy=str(raw.get("retake_policy", "capped")),
        retake_cap=_num(raw.get("retake_cap"), 1.0),
        include_retake_in_gpa=bool(raw.get("include_retake_in_gpa", True)),
        comprehensive_excludes_retakes=bool(
            raw.get("comprehensive_excludes_retakes", True)),
        note=str(raw.get("note", "")),
    )


def _load_major(raw: dict) -> Major:
    groups = [
        CreditGroup(
            id=str(g.get("id", "")), name=str(g.get("name", "")),
            credits=_num(g.get("credits")),
            counts_toward_ranking=bool(g.get("counts_toward_ranking", True)),
            note=str(g.get("note", "")),
        )
        for g in (raw.get("credit_groups") or [])
    ]
    gid2rank = {g.id: g.counts_toward_ranking for g in groups}
    courses: list[Course] = []
    for c in (raw.get("courses") or []):
        group = str(c.get("group", ""))
        courses.append(Course(
            code=str(c.get("code", "")),
            name=str(c.get("name", "")),
            credits=_num(c.get("credits")),
            group=group,
            term=int(_num(c.get("term"), 0)),
            kind=str(c.get("kind", "必修")),
            assess=str(c.get("assess", "百分制")),
            counts_toward_gpa=bool(c.get("counts_toward_gpa", True)),
            counts_toward_ranking=bool(
                c.get("counts_toward_ranking", gid2rank.get(group, True))),
            note=str(c.get("note", "")),
        ))
    return Major(
        id=str(raw.get("id", "")), name=str(raw.get("name", "")),
        college=str(raw.get("college", "")),
        degree=str(raw.get("degree", "理学学士")),
        years=int(_num(raw.get("years"), 4)),
        total_credits=_num(raw.get("total_credits")),
        groups=groups, courses=courses,
        requirements=list(raw.get("requirements") or []),
        source=str(raw.get("source", "")),
        confidence=str(raw.get("confidence", "")),
        group_credits_official=_num(raw.get("group_credits_official")),
        credits_official=_num(raw.get("credits_official")),
    )


def _load_goals(raw: dict) -> list[Goal]:
    out: list[Goal] = []
    for g in (raw.get("goals") or []):
        reqs = [
            Requirement(
                metric=str(r.get("metric", "")),
                label=str(r.get("label", "")),
                op=str(r.get("op", ">=")),
                value=_num(r.get("value")),
                hard=bool(r.get("hard", True)),
                note=str(r.get("note", "")),
                source=str(r.get("source", "")),
                confidence=str(r.get("confidence", "")),
            )
            for r in (g.get("requirements") or [])
        ]
        out.append(Goal(
            id=str(g.get("id", "")), name=str(g.get("name", "")),
            kind=str(g.get("kind", "route")),
            summary=str(g.get("summary", "")),
            requirements=reqs,
            formula={str(k): _num(v) for k, v in (g.get("formula") or {}).items()},
            quota=str(g.get("quota", "")), amount=str(g.get("amount", "")),
            source=str(g.get("source", "")),
            confidence=str(g.get("confidence", "")),
        ))
    return out


def _load_activities(raw: dict) -> list[Activity]:
    out: list[Activity] = []
    for a in (raw.get("activities") or []):
        out.append(Activity(
            id=str(a.get("id", "")), name=str(a.get("name", "")),
            category=str(a.get("category", "")), level=str(a.get("level", "")),
            organizer=str(a.get("organizer", "")),
            channels={str(k): _num(v) for k, v in (a.get("channels") or {}).items()},
            # achieve_map 的值可能是数字（绝对分值）也可能是嵌套字典
            # {"综测": x, "推免": y}，所以这里保留原结构，交给 Activity 解释。
            achieve_map=dict(a.get("achieve_map") or {}),
            default_achieve=str(a.get("default_achieve", "")),
            rubric={str(k): str(v) for k, v in (a.get("rubric") or {}).items()},
            discount=str(a.get("discount", "level_ratio")),
            timing=str(a.get("timing", "")),
            eligibility=str(a.get("eligibility", "")),
            url=str(a.get("url", "")), source=str(a.get("source", "")),
            confidence=str(a.get("confidence", "")),
            note=str(a.get("note", "")),
            tags=[str(t) for t in (a.get("tags") or [])],
        ))
    return out


# --------------------------------------------------------------------------- #
def load_calc_data(directory: str | Path | None = None,
                   require: bool = True) -> CalcData:
    """读入全部计算器数据。`require=False` 时缺文件只记警告。

    目录解析顺序：

    1. 显式传入的 `directory`（测试与自定义部署用）；
    2. `data/calc/`（本地覆盖，在 .gitignore 里）；
    3. `calcdata/`（仓库自带，进 git）。

    覆盖是**按文件**生效的：你可以只把 `majors.json` 放到 `data/calc/`，
    其余三个文件仍然用 `calcdata/` 里的版本。
    """
    if directory:
        base = Path(directory)
        if not base.is_dir():
            msg = f"计算器数据目录不存在：{base}"
            if require:
                raise CalcDataError(msg)
            data = CalcData()
            data.warnings.append(msg)
            return data
        picked = {name: base / name for name in _DATA_FILES}
        # 显式目录下也接受可选的赛事名录（没有就不加载）
        picked["competitions.json"] = base / "competitions.json"

    else:
        picked = {}
        for name in _DATA_FILES:
            override = OVERRIDE_DIR / name
            default = DEFAULT_DIR / name
            if override.is_file():
                picked[name] = override
            elif default.is_file():
                picked[name] = default
            else:
                picked[name] = default      # 交给下面的 load() 报错
        picked["competitions.json"] = competitions_mod.default_path()

    data = CalcData()
    missing: list[str] = []

    def load(name: str):
        path = picked[name]
        if not path.is_file():
            missing.append(str(path))
            return {}
        return _read_json(path)

    rules_raw = load("rules.json")
    if rules_raw:
        data.rules = Rules(
            gpa=_load_grade_table(rules_raw.get("gpa") or {}),
            comprehensive=dict(_strip_private(rules_raw.get("comprehensive") or {})),
            weights={str(k): _num(v) for k, v in
                     _strip_private(rules_raw.get("weights") or {}).items()},
            channel_max={str(k): _num(v) for k, v in
                         _strip_private(rules_raw.get("channel_max") or {}).items()},
            equivalents=dict(_strip_private(rules_raw.get("equivalents") or {})),
            discount=dict(_strip_private(rules_raw.get("discount") or {})),
            notes=[str(n) for n in (rules_raw.get("notes") or [])],
            sources=list(rules_raw.get("sources") or []),
        )

    majors_raw = load("majors.json")
    if majors_raw:
        data.majors = [_load_major(m) for m in (majors_raw.get("majors") or [])]

    goals_raw = load("goals.json")
    if goals_raw:
        data.goals = _load_goals(goals_raw)

    acts_raw = load("activities.json")
    if acts_raw:
        data.activities = _load_activities(acts_raw)

    # 具体赛事名录（可选增强）：展开成 Activity 追加到清单里。
    # 用 **当前目录下** 的 competitions.json（显式目录或 data/calc/ 覆盖优先），
    # 联网刷新的缓存则固定读 data/cache/calc_competitions.json。
    comp_raw, comp_warnings = competitions_mod.load_competitions(picked["competitions.json"])
    data.warnings.extend(comp_warnings)
    if comp_raw:
        online = competitions_mod.load_online_cache()
        acts, comp_meta, warns = competitions_mod.build_activities(comp_raw, online)
        data.activities.extend(acts)
        data.competitions = comp_meta
        data.warnings.extend(warns)
        picked["online_cache"] = Path(competitions_mod.ONLINE_CACHE)

    if missing:
        msg = ("缺少计算器数据文件：" + "、".join(missing)
               + "。仓库自带的版本在 calcdata/ 下；"
                 "如果你把文件删了，请 git checkout calcdata/ 恢复。")
        if require:
            raise CalcDataError(msg)
        data.warnings.append(msg)

    data.meta = dict(majors_raw.get("meta") or {})
    data.meta.update({k: v for k, v in (goals_raw.get("meta") or {}).items()
                      if k not in data.meta})
    data.meta["dirs"] = {name: str(p) for name, p in picked.items()}
    _validate(data)
    return data


def _check_official_gpa_bands(data: CalcData) -> None:
    """逐分核对绩点折算表是否与学校公示口径一致。

    依据：《华南农业大学本科学生学籍管理实施细则》华南农办〔2021〕68号
    第十二条（一）（同文条款见《华南农业大学本科学生学分制实施细则》
    华南农办〔2010〕88号 第八条（一））——

        百分制记分，100分折算为5.00绩点，99分折算为4.90绩点，98分折算为
        4.80绩点……，依此类推，低于60分折算为0绩点。

    即 60 ≤ X ≤ 100 时 绩点 = X ÷ 10 − 5，X < 60 时 0 绩点。

    这不是「猜一个公式」：从 100 分起每降 1 分减 0.10，降到 60 分正好是 1.00，
    与同条「补考和重修……成绩及格及以上的，其绩点均折合为1.00」严丝合缝；
    五级制的 优秀4.50／良好3.50／中等2.50／及格1.50 在这条标尺上也正好是
    95／85／75／65 分。折算表是这个计算器的地基，一旦有人手改 `gpa.bands`
    跟官方口径脱钩，成绩单算出来的绩点、保研门槛判定、课程目标分反推会
    一起错，所以在这里逐分核对并把差异报成警告。
    """
    gpa = data.rules.gpa
    for score in range(60, 101):
        expected = score / 10 - 5
        actual = gpa.score_to_gp(score)
        if abs(actual - expected) > 1e-6:
            data.warnings.append(
                f"绩点折算与学校公示口径不一致：{score} 分算成 {actual:.2f} 绩点，"
                f"按《华南农业大学本科学生学籍管理实施细则》华南农办〔2021〕68号"
                f"第十二条（一）应为 {expected:.2f}。请检查 rules.json 的 gpa.bands。")
            break
    if abs(gpa.score_to_gp(gpa.fail_score - 1) - 0.0) > 1e-9:
        data.warnings.append(
            f"绩点折算与学校公示口径不一致：{gpa.fail_score - 1:g} 分未折算为 0 绩点"
            "（华南农办〔2021〕68号 第十二条（一）原文「低于60分折算为0绩点」）。"
            "请检查 rules.json 的 gpa.bands。")


def _validate(data: CalcData) -> None:
    """一致性检查：把数据文件的低级错误在启动时就暴露出来。"""
    gpa = data.rules.gpa
    if not gpa.bands:
        data.warnings.append("rules.json 没有配绩点折算区间（gpa.bands 为空），绩点会全部算成 0")
    else:
        _check_official_gpa_bands(data)
    # 这些类别是「提示信息」而非加分项，允许不挂任何通道
    info_only = {"风险提示", "信息"}
    seen: set[str] = set()
    for a in data.activities:
        if not a.id:
            data.warnings.append(f"活动缺少 id：{a.name}")
        if a.id in seen:
            data.warnings.append(f"活动 id 重复：{a.id}")
        seen.add(a.id)
        if not a.channels and a.category not in info_only:
            data.warnings.append(f"活动没有任何加分通道：{a.id} {a.name}")
        # 双评分表的配置一致性：通道的评分类别必须在 achieve_map 里有对应分值，
        # 否则该项会被静默算成 0（学生看到 0 分却不知道是数据写错了）。
        for problem in a.rubric_conflicts(DEFAULT_CHANNEL_RUBRIC):
            data.warnings.append(f"评分口径配置不一致：{problem}")
    for m in data.majors:
        codes: set[str] = set()
        for c in m.courses:
            if c.code in codes:
                data.warnings.append(f"{m.id} 课程代码重复：{c.code} {c.name}")
            codes.add(c.code)
            if c.credits <= 0:
                data.warnings.append(f"{m.id} 课程学分为 0：{c.code} {c.name}")
        declared = round(sum(g.credits for g in m.groups), 2)
        actual = round(sum(c.credits for c in m.courses), 2)
        if m.groups and abs(declared - actual) > 0.51:
            data.warnings.append(
                f"{m.id} 学分构成合计 {declared} 与课程列表合计 {actual} 不一致")
