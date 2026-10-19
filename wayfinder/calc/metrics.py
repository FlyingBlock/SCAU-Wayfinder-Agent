"""只读推算值（metrics）。

门槛条件（`Requirement`）不直接读表单项，而是读一个**统一的指标字典**。
这样做的好处：门槛文件里只写 `{"metric": "cet4_score", "op": ">=", "value": 425}`，
换一套学校细则只要改数据文件，判定代码一行都不用动。

指标来源优先级：学生手填 > 自动推算（从成绩单/活动篮算）。
每个指标都带 `fillable` 标记，说明该由界面上的哪一类输入填充。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .basket import BasketResult
from .grade import GPAResult
from .model import Profile


@dataclass
class MetricDef:
    """一个指标的元信息。"""

    key: str
    label: str
    unit: str = ""
    kind: str = "number"        # number / percent / bool / text
    fillable: str = "form"      # form=手填 | derived=自动推算 | basket=活动篮
    hint: str = ""
    higher_is_better: bool = True


@dataclass
class MetricsResult:
    values: dict[str, float] = field(default_factory=dict)
    sources: dict[str, str] = field(default_factory=dict)   # 指标 → 来源说明
    missing: list[str] = field(default_factory=list)        # 门槛需要但没填的

    def get(self, key: str, default: float | None = None):
        return self.values.get(key, default)

    def as_dict(self) -> dict:
        return {
            "values": {k: round(v, 4) if isinstance(v, float) else v
                       for k, v in self.values.items()},
            "sources": self.sources,
            "missing": self.missing,
        }


# 指标字典：界面上「填写你的情况」那一块就是照这个渲染的
METRIC_DEFS: list[MetricDef] = [
    MetricDef("gpa", "平均学分绩点", "", "number", "derived", "由已填成绩自动算出"),
    MetricDef("avg_score", "加权平均分", "分", "number", "derived", "由已填成绩自动算出"),
    MetricDef("ranking_gpa", "保研用学业成绩绩点", "", "number", "derived",
              "只计培养方案里标记为计入排名的课程"),
    MetricDef("gpa_no_retake", "综测智育用平均绩点（不含重修）", "", "number", "derived",
              "综合测评/评优口径：《华南农业大学本科生综合测评及评优实施办法》"
              "华农党发〔2020〕38号 第六条（一）「重修课程成绩不纳入平均绩点计算范围」，"
              "重修课整门不计入。与上面按学籍细则第十二条（三）折算 1.00 的绩点是"
              "两套口径，学生有重修记录时两者不相等。"),
    MetricDef("major_top_gpa", "同班型最高平均绩点", "", "number", "form",
              "生命科学学院推免口径：学业成绩得分 = 个人绩点 ÷ 同班型最高绩点 × 85。"
              "综测智育基础分用同一个数：本人绩点 ÷ 同班型最高绩点 × 55"
              "（这里的本人绩点用「不含重修」的那个）。"
              "不填则退回按加权平均分折算并提示"),
    MetricDef("gpa_ratio", "绩点 / 专业最高绩点", "%", "number", "derived",
              "智育基础分的直接依据，用「不含重修」的绩点计算"),
    MetricDef("credits_earned", "已获学分", "", "number", "derived", "已通过课程学分合计"),
    MetricDef("credits_total", "培养方案总学分", "", "number", "derived", ""),
    MetricDef("credits_remaining", "未出成绩学分", "", "number", "derived",
              "培养方案里还没拿到成绩的学分"),
    MetricDef("credits_shortfall", "未完成应修课程学分", "", "number", "derived",
              "按教学计划应修课程的缺口，0 表示课程都已修读（推免要求为 0）"),
    MetricDef("academic", "推免学业成绩得分", "分", "number", "derived",
              "生命科学学院口径：个人绩点 ÷ 同班型最高绩点 × 85，满分 85 分"),
    MetricDef("failed_count", "不及格课程门数", "门", "number", "derived", ""),
    MetricDef("rank_percent", "专业排名百分位", "%", "number", "form",
              "填专业人数和你的名次后自动算；也可直接填百分位"),
    MetricDef("cet4_score", "英语四级(CET-4)分数", "分", "number", "form", "没考填 0"),
    MetricDef("cet6_score", "英语六级(CET-6)分数", "分", "number", "form", "没考填 0"),
    MetricDef("ielts_score", "雅思成绩", "分", "number", "form", "没考留空"),
    MetricDef("toefl_score", "托福成绩", "分", "number", "form", "没考留空"),
    MetricDef("pe_score", "体质健康测试成绩", "分", "number", "form",
              "最近一次体测总分；推免口径常看前三年平均分"),
    MetricDef("pe_pass", "是否通过体质健康测试", "", "number", "form",
              "1 = 已通过，0 = 未通过（免测按通过计）"),
    MetricDef("thesis_grade", "毕业论文（设计）成绩", "", "number", "form",
              "4=优秀 3=良好 2=中等 1=及格 0=不及格"),
    MetricDef("volunteer_hours", "志愿服务时长", "小时", "number", "form", ""),
    MetricDef("development_literacy", "发展素养评价分", "分", "number", "derived",
              "推免综合评价的 5 分项，由活动篮「发展素养」通道累加"),
    MetricDef("poverty_certified", "已通过家庭经济困难认定", "", "number", "form",
              "1 = 已入库，0 = 未入库（国家励志奖学金硬性要求）"),
    MetricDef("innovation_score", "创新能力评价分", "分", "number", "derived",
              "推免综合评价的 10 分项，由活动篮「创新能力」通道累加"),
    MetricDef("comprehensive", "综测总分", "分", "number", "derived",
              "由智育/德育折算 + 活动篮各通道加分得出"),
    MetricDef("comprehensive_rank_percent", "综测排名百分位", "%", "number", "form", ""),
    MetricDef("moral_score", "德育基础分 + 班内互评分", "分", "number", "form",
              "细则第六条：德育基础分满分 10 + 班内互评分满分 5，合计最多 15 分。"
              "德育奖励分（上限 5）由活动篮「德育加分」通道自动累加"),
    MetricDef("discipline", "违纪处分次数", "次", "number", "form", "没有填 0"),
    MetricDef("pe_grade", "体育基础分", "分", "number", "form",
              "细则第八条：体育基础分 = 体测分数 ÷ 120 × 3（学年总分满分 120），"
              "满分 3 分。例如体测 80 分 → 2.0 分；免测按 60 分算 → 1.5 分"),
    MetricDef("aesthetic_score", "美育基础分", "分", "number", "form",
              "细则第九条：美育基础分满分 3 分，由班级在学年总结基础上评价"),
    MetricDef("labour_score", "劳育基础分", "分", "number", "form",
              "细则第十条：劳育基础分满分 3 分，由班级在学年总结基础上评价"),
    MetricDef("comprehensive_bonus", "综测加分合计", "分", "number", "basket",
              "活动篮「综测加分」通道累加（细则直接给综测总分的加分）"),
    MetricDef("moral_bonus", "德育加分", "分", "number", "basket",
              "活动篮「德育加分」通道累加；细则第六条上限 5 分"),
    MetricDef("academic_bonus", "智育创新能力加分", "分", "number", "basket",
              "活动篮「智育加分」通道累加；细则第七条上限 10 分"),
    MetricDef("sports_arts_bonus", "体育竞赛加分", "分", "number", "basket",
              "活动篮「体育加分」通道累加；细则第八条上限 2 分"),
    MetricDef("aesthetic_bonus", "美育活动加分", "分", "number", "basket",
              "活动篮「美育加分」通道累加；细则第九条上限 2 分"),
    MetricDef("labour_bonus", "劳育实践加分", "分", "number", "basket",
              "活动篮「劳育加分」通道累加；细则第十条上限 2 分"),
    MetricDef("second_classroom", "第二课堂学分", "学分", "number", "basket", "由活动篮累加"),
    MetricDef("innovation_credits", "创新创业学分", "学分", "number", "basket",
              "毕业硬门槛：华南农办〔2013〕2号 要求必须取得 3 个创新创业实践活动学分"),
    MetricDef("gpa_target_ratio", "目标达成率", "%", "number", "derived",
              "当前绩点 / 目标绩点"),
]

METRIC_BY_KEY = {m.key: m for m in METRIC_DEFS}


def compute_metrics(profile: Profile, gpa: GPAResult,
                    basket: BasketResult | None = None) -> MetricsResult:
    """汇总所有指标。学生手填的值优先于推算值。"""
    res = MetricsResult()
    vals = res.values

    # ---- 自动推算 ---------------------------------------------------------- #
    vals["gpa"] = round(gpa.gpa, 4)
    res.sources["gpa"] = "由成绩单加权算出（含重修，及格者按学籍细则折算 1.00）"
    vals["gpa_no_retake"] = round(gpa.gpa_no_retake, 4)
    res.sources["gpa_no_retake"] = (
        "剔除了重修课程的加权绩点（华农党发〔2020〕38号 第六条（一）："
        "重修课程成绩不纳入平均绩点计算范围），综测智育基础分用它")
    vals["avg_score"] = round(gpa.avg_score, 2)
    res.sources["avg_score"] = "由成绩单加权算出"
    vals["ranking_gpa"] = round(gpa.ranking_gpa, 4)
    res.sources["ranking_gpa"] = "只计培养方案中标记为计入排名的课程"
    # 两个口径分开用：推免学业成绩看教务系统的全学程平均学分绩点（含重修，
    # 及格者 1.00）；综测智育基础分看剔除重修的那个绩点。
    own_tuimian = gpa.gpa
    own_comprehensive = gpa.comprehensive_gpa
    top = (profile.metrics or {}).get("major_top_gpa")
    if top:
        try:
            top_f = float(top)
        except (TypeError, ValueError):
            top_f = 0.0
        if top_f > 0 and own_comprehensive > 0:
            vals["gpa_ratio"] = round(own_comprehensive / top_f, 4)
            res.sources["gpa_ratio"] = (
                f"我的绩点 {own_comprehensive:.3f}（不含重修）÷ "
                f"同班型最高绩点 {top_f:g}")
        if top_f > 0 and own_tuimian > 0:
            # 推免学业成绩得分：学院细则原文
            # 「得分=个人绩点/同班型最高绩点*85」，上限 85
            vals["academic"] = round(min(85.0, own_tuimian / top_f * 85.0), 3)
            res.sources["academic"] = (
                f"{own_tuimian:.3f} ÷ {top_f:g} × 85 = {vals['academic']:.2f}"
                "（生命科学学院推免综合评价细则 2026 修订）")
    elif own_tuimian > 0:
        # 没有真实最高绩点时，按「5 分制上限」给一个下界估计，
        # 折算出来的分项分会偏低，界面上会标明这一点。
        vals["gpa_ratio"] = round(own_comprehensive / 5.0, 4)
        res.sources["gpa_ratio"] = (
            "按绩点上限 5.0 估算（未填同班型最高绩点），实际比值会更高")
        vals["academic"] = round(min(85.0, own_tuimian / 5.0 * 85.0), 3)
        res.sources["academic"] = (
            f"{own_tuimian:.3f} ÷ 5.0 × 85 = {vals['academic']:.2f}"
            "（下界估计：未填同班型最高绩点，实际会更高）")
    vals["credits_earned"] = round(gpa.credits_earned, 2)
    res.sources["credits_earned"] = "已通过课程学分合计"
    vals["credits_total"] = round(gpa.credits_total, 2)
    res.sources["credits_total"] = "来自培养方案"
    vals["credits_remaining"] = round(gpa.credits_remaining, 2)
    res.sources["credits_remaining"] = "培养方案里还没拿到成绩的学分"
    # credits_shortfall = 已获学分距培养方案总学分的缺口。
    # 推免要求「按教学计划修完应修课程」，对应这个值为 0 或很小。
    vals["credits_shortfall"] = round(
        max(0.0, gpa.credits_total - gpa.credits_earned), 2)
    res.sources["credits_shortfall"] = "培养方案总学分 − 已获学分"
    vals["failed_count"] = float(len(gpa.failed))
    res.sources["failed_count"] = "由成绩单统计"

    # ---- 活动篮 ------------------------------------------------------------ #
    if basket is not None:
        for channel, total in basket.channel_totals.items():
            key = basket.metric_key(channel)
            if key:
                vals[key] = round(total, 3)
                res.sources[key] = f"活动篮「{channel}」通道累加，共 {len(basket.items)} 项活动"

    # ---- 学生手填（覆盖推算值） -------------------------------------------- #
    for key, val in (profile.metrics or {}).items():
        if val is None or val == "":
            continue
        try:
            vals[key] = float(val)
        except (TypeError, ValueError):
            continue
        res.sources[key] = "学生手填"

    # ---- 由专业人数 + 名次反算排名百分位 ----------------------------------- #
    if "rank_percent" not in (profile.metrics or {}):
        if profile.cohort_size and profile.rank:
            pct = profile.rank / profile.cohort_size * 100.0
            vals["rank_percent"] = round(pct, 2)
            res.sources["rank_percent"] = (
                f"按专业 {profile.cohort_size} 人、名次第 {profile.rank} 名算出"
            )

    # ---- 德育分兜底：没填就用 0，并标记缺失 -------------------------------- #
    vals.setdefault("discipline", 0.0)
    return res
