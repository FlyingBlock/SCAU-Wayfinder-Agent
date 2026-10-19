"""计算器的数据模型。

设计原则：**规则是数据，不是代码**。绩点折算表、综测权重、门槛条件都写在
`calcdata/*.json` 里，代码只负责按数据算。这样学校改了细则，改数据文件即可，
而且每一条数值都能带上 `source` 出处，界面上可以逐条溯源。
"""
from __future__ import annotations

from dataclasses import dataclass, field


# --------------------------------------------------------------------------- #
# 分数 → 绩点
# --------------------------------------------------------------------------- #
@dataclass
class ScoreBand:
    """百分制分数区间 → 绩点。

    `lo` / `hi` 都是闭区间端点（hi 可为 100）。`mode` 用于区分
    「档位制」（区间内绩点固定）和「线性制」（区间内按比例插值）：

    - fixed : 区间内绩点恒为 `gp`
    - linear: 从 (lo, lp) 线性升到 (hi, hp)
    """

    lo: float
    hi: float
    gp: float = 0.0
    mode: str = "fixed"
    lp: float = 0.0
    hp: float = 0.0
    note: str = ""

    def contains(self, score: float) -> bool:
        return self.lo <= score <= self.hi

    def at(self, score: float) -> float:
        if self.mode == "linear" and self.hi > self.lo:
            ratio = (score - self.lo) / (self.hi - self.lo)
            return self.lp + ratio * (self.hp - self.lp)
        return self.gp


@dataclass
class GradeTable:
    """一整套折算规则：百分制、五级制、绩点上限。"""

    name: str = "百分制"
    max_gp: float = 5.0
    bands: list[ScoreBand] = field(default_factory=list)
    # 五级制 → 绩点
    levels: dict[str, float] = field(default_factory=dict)
    # 特殊成绩处理策略
    fail_score: float = 60.0            # 不及格线
    retake_policy: str = "capped"       # capped=补考/重修按封顶绩点 | actual=按实得分 | first=只按首次成绩
    retake_cap: float = 1.0             # capped 时补考及格可计的最高绩点
    include_retake_in_gpa: bool = True
    # 综合测评（智育基础分）用的平均绩点是否剔除重修课程。
    # 学籍/毕业/推免口径与综测评优口径是两套：前者按《学籍管理实施细则》
    # 第十二条把补考/重修及格者按 1.00 折算计入；后者按《本科生综合测评
    # 及评优实施办法》华农党发〔2020〕38号 第六条（一）「重修课程成绩不纳入
    # 平均绩点计算范围」，即整门课不计入。所以同一个学生会有两个绩点。
    comprehensive_excludes_retakes: bool = True
    note: str = ""

    def score_to_gp(self, score: float) -> float:
        """百分制分数 → 绩点。区间外按最近的档位取。"""
        if not self.bands:
            return 0.0
        s = max(0.0, min(100.0, float(score)))
        for band in self.bands:
            if band.contains(s):
                return round(min(band.at(s), self.max_gp), 4)
        # 低于所有区间 → 用最低档；高于 → 用最高档
        if s < self.bands[0].lo:
            return self.bands[0].at(self.bands[0].lo)
        return self.bands[-1].at(self.bands[-1].hi)

    def level_to_gp(self, level: str) -> float:
        key = (level or "").strip()
        if key in self.levels:
            return self.levels[key]
        return 0.0

    def gp_to_score(self, gp: float) -> float:
        """绩点 → 达到该绩点所需的最低百分制分数（用于反推课程目标分）。

        按 `bands` 的实际映射反解，不假定分段是两个端点之间的直线：

        - 分段内查得到这个绩点 → 用**两端点的真实分数**线性插值，
          而不是用 band.lo/band.hi。这样「0-60 分对应 0 绩点」这类
          不参与折算的分段不会污染反解结果。
        - 落到折算表区间之外（高于上限或低于下限）→ 返回最近端点的分数。

        以华南农业大学的官方折算表（绩点 = 分数÷10 − 5，60 分以下 0 绩点）为例：
        `gp_to_score(3.20)` 得到 82.0 分，`gp_to_score(1.00)` 得到 60.0 分。

        这一步的正确性直接影响「每门课要考多少分」的建议能不能兑现，
        所以宁可返回一个保守值，也不要用近似公式糊过去。
        """
        if not self.bands:
            return 0.0
        points: list[tuple[float, float]] = []
        for band in self.bands:
            if band.mode == "linear" and band.hi > band.lo:
                points.append((band.lp, band.lo))
                points.append((band.hp, band.hi))
            else:
                points.append((band.gp, band.lo))
        points.sort()
        # 同一绩点可能对应多个分数（理论上不该发生）：取最低的那个分数
        merged: dict[float, float] = {}
        for g, s in points:
            if g not in merged or s < merged[g]:
                merged[g] = s
        pts = sorted(merged.items())          # [(绩点, 分数)]
        if not pts:
            return 0.0

        target = float(gp)
        if target <= pts[0][0]:
            return float(pts[0][1])
        if target >= pts[-1][0]:
            return float(pts[-1][1])
        for (g0, s0), (g1, s1) in zip(pts, pts[1:]):
            if g0 <= target <= g1:
                if g1 == g0:
                    return float(s0)
                ratio = (target - g0) / (g1 - g0)
                return round(s0 + ratio * (s1 - s0), 2)
        return float(pts[-1][1])


# --------------------------------------------------------------------------- #
# 培养方案
# --------------------------------------------------------------------------- #
@dataclass
class CreditGroup:
    """学分构成里的一类（通识必修 / 学科基础 / 实践环节 …）。"""

    id: str
    name: str
    credits: float = 0.0
    # 该模块是否计入保研用的学业成绩排名（多数学校只算必修+专业核心）
    counts_toward_ranking: bool = True
    note: str = ""


@dataclass
class Course:
    """一门课。`credits` 是学分，`term` 是建议开课学期（1-8）。"""

    code: str
    name: str
    credits: float
    group: str = ""
    term: int = 0
    kind: str = "必修"                  # 必修 / 限选 / 任选 / 实践
    assess: str = "百分制"              # 百分制 / 五级制
    counts_toward_gpa: bool = True
    counts_toward_ranking: bool = True
    note: str = ""

    @property
    def is_practice(self) -> bool:
        return self.kind == "实践" or "实践" in self.name or "实习" in self.name


@dataclass
class Major:
    """一个专业的培养方案。"""

    id: str
    name: str
    college: str = ""
    degree: str = "理学学士"
    years: int = 4
    total_credits: float = 0.0
    # 官方培养方案写的毕业总学分。与 `total_credits`（本文件课程列表的合计）
    # 分开记：课程列表是规划用的，未必等于官方教学计划的每一门课。
    credits_official: float = 0.0
    groups: list[CreditGroup] = field(default_factory=list)
    # 官方教学计划按「必修/选修/实践」给的合计，用于界面上与课程列表对照
    group_credits_official: dict = field(default_factory=dict)
    courses: list[Course] = field(default_factory=list)
    # 毕业/学位相关的硬性要求
    requirements: list[dict] = field(default_factory=list)
    source: str = ""
    confidence: str = ""


# --------------------------------------------------------------------------- #
# 规则
# --------------------------------------------------------------------------- #
@dataclass
class Rules:
    """学校层面的评分规则：绩点折算、综测构成、加分等值换算。"""

    gpa: GradeTable = field(default_factory=GradeTable)
    # 综测构成：{dimensions: [...], bonus_routing: {...}, channel_metrics: {...},
    #           rank_curve: [...], formula_text: "..."}
    comprehensive: dict = field(default_factory=dict)
    # 综测各通道的权重（百分数，用于算综测总分排名）
    weights: dict[str, float] = field(default_factory=dict)
    # 通道满分（把各通道得分归一到 0-100 时用）
    channel_max: dict[str, float] = field(default_factory=dict)
    # 各种「1 分 = 多少积分」的等值换算
    equivalents: dict[str, dict] = field(default_factory=dict)
    # 加分折算策略的具名参数
    discount: dict[str, dict] = field(default_factory=dict)
    # 补充说明
    notes: list[str] = field(default_factory=list)
    sources: list[dict] = field(default_factory=list)


# --------------------------------------------------------------------------- #
# 学生
# --------------------------------------------------------------------------- #
@dataclass
class Profile:
    """学生当前状态。前端表单直接映射到这里。"""

    major_id: str = ""
    name: str = ""
    grade: str = ""                     # 入学年份，如 "2024"
    # 已修课程成绩：{课程 code: 分数}，分数为百分制或五级制字符串
    scores: dict[str, float | str] = field(default_factory=dict)
    # 补考 / 重修过的课（code 列表）：这些课按 `GradeTable.retake_cap` 封顶计绩点
    retakes: list[str] = field(default_factory=list)
    # 量化指标（四六级、体测、志愿时长…）
    metrics: dict[str, float] = field(default_factory=dict)
    # 专业人数、当前排名（用于排名类门槛判定）
    cohort_size: int = 0
    rank: int = 0
    # 手工填的现有综测分（没有逐项明细时用）
    manual_scores: dict[str, float] = field(default_factory=dict)
    # 计划投入的额外努力（例如"下学期想考到多少分"）—— 目前不用，留扩展
    target_gpa: float = 0.0

    def score_of(self, code: str):
        return self.scores.get(code)


# --------------------------------------------------------------------------- #
# 活动与门槛
# --------------------------------------------------------------------------- #
@dataclass
class Activity:
    """一项可加分的活动 / 竞赛 / 证书 / 学生工作。

    `channels` 是 {通道: 基准分}，例如 `{"综测加分": 4, "第二课堂": 1}`。
    `achieve_map` 把「取得成果」映射成系数或**绝对分值**。

    **两套评分表**：同一件事在「综测」和「推免综合评价」里的分值往往完全不同
    ——综测里一篇 T2 论文写「第1-2作者 8 分」，推免里写「基础分 6，第 2 作者 ×0.8」。
    所以 `achieve_map` 里可以对某个成果再嵌一层 `{"综测": x, "推免": y}`
    （键名见 `rules.json` 的 `rubric_channels`），让不同的通道走不同的分值。
    没有嵌套时，两层通道共用同一个分值。
    """

    id: str
    name: str
    category: str = ""                   # 竞赛 / 科研 / 德育 / 文体 / 证书 / 学生工作 / 志愿服务
    level: str = ""                      # 国家级 / 省级 / 校级 / 院级
    organizer: str = ""
    channels: dict[str, float] = field(default_factory=dict)
    achieve_map: dict[str, object] = field(default_factory=dict)
    default_achieve: str = ""
    # 按通道指定评分类别：{通道: "综测" | "推免"}
    rubric: dict[str, str] = field(default_factory=dict)
    discount: str = "level_ratio"        # 折算策略名（见 Rules.discount）
    timing: str = ""                     # 什么时候能报名 / 参加
    eligibility: str = ""                # 参赛资格
    url: str = ""
    source: str = ""                     # 加分依据出处
    confidence: str = ""
    note: str = ""
    tags: list[str] = field(default_factory=list)
    # 清单归属：general=activities.json 里的通用条目；
    # competition=《学生竞赛奖励办法》名录里的具体赛事（内置）；
    # competition-online=联网刷新后新发现的赛事。前端据此分组与筛选。
    list_kind: str = "general"
    # 名录类活动的附加上下文（序号/附录/档位/是否联网来源…），仅用于展示。
    extra: dict = field(default_factory=dict)

    @property
    def channel_names(self) -> list[str]:
        return list(self.channels)

    def achievements(self) -> list[str]:
        if self.achieve_map:
            return list(self.achieve_map)
        return [self.default_achieve or "参与"]

    def value_for(self, channel: str, achieve: str,
                  fallback_rubric: str = "") -> float | None:
        """取「某个通道 + 某个成果」的分值。

        返回 None 表示细则没有给出该组合的分值（该通道此项不加分），
        调用方应当把这一项按 0 处理，而不是回退到别的通道的分值。

        `achieve_map` 的值有两种形态：

        - 数字：两套评分表同分，直接用；
        - 嵌套字典：形如 ``{"综测": 8, "推免": 6}``，要先确定这个通道属于
          哪套表。优先用活动自带的 `rubric`（它能把同一个活动里混用的通道
          分别归到两套表）；活动没写时用 `fallback_rubric`（由 Basket 按
          通道名推断）。
        """
        raw = self.achieve_map.get(achieve)
        if raw is None:
            return None
        if not isinstance(raw, dict):
            return float(raw)
        rubric = self.rubric.get(channel) or fallback_rubric
        if rubric in raw:
            return float(raw[rubric])
        if rubric:
            # 明确知道这个通道属于哪套表，但该表没给分值 → 此项不加分
            return None
        # 完全无法判断这个通道属于哪套表：这是数据错误，宁可不加分也不要
        # 猜一个可能偏高的分值。校验器会在启动时把这种配置报出来。
        return None

    def rubric_conflicts(self, channel_rubric: dict[str, str]) -> list[str]:
        """找出「通道与成果分值的评分类别对不上」的配置错误。

        例如把 `智育加分`（综测通道）配成查 `推免` 的口径，那就是写错了。
        """
        problems: list[str] = []
        for achieve, raw in (self.achieve_map or {}).items():
            if not isinstance(raw, dict):
                continue
            for channel in self.channels:
                rubric = self.rubric.get(channel) or channel_rubric.get(channel, "")
                if rubric and rubric not in raw:
                    problems.append(
                        f"{self.id}：成果「{achieve}」缺「{rubric}」口径"
                        f"（通道 {channel}）")
        return problems


@dataclass
class Requirement:
    """门槛里的一条要求。`metric` 指向 metrics 里的键名。"""

    metric: str
    label: str = ""
    op: str = ">="                       # >= <= > < == max min
    value: float = 0.0
    hard: bool = True                    # 硬性门槛 / 加分项
    note: str = ""
    source: str = ""
    confidence: str = ""


@dataclass
class Goal:
    """一条路线（保研 / 考研 / 奖学金…）及其门槛。"""

    id: str
    name: str
    kind: str = "route"                  # route / scholarship
    summary: str = ""
    requirements: list[Requirement] = field(default_factory=list)
    # 该路线的综合成绩算法（可选）：{通道: 权重}
    formula: dict[str, float] = field(default_factory=dict)
    # 名额 / 比例 / 金额等描述性信息
    quota: str = ""
    amount: str = ""
    source: str = ""
    confidence: str = ""
