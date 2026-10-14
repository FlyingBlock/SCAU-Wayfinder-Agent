"""计算器 Facade。

一次 `evaluate()` 调用把四件事算完并打包成一个 JSON 友好的结果：

    成绩单 ──▶ 平均学分绩点 ──┐
    活动篮 ──▶ 各通道加分   ──┼──▶ 综测总分 ──▶ 门槛判定（保研/考研/奖学金）
    表单   ──▶ 手填指标     ──┘                └──▶ 剩余课程目标分

Web 层和 CLI 都只调这一个入口，保证两边口径完全一致。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .basket import Basket, BasketItem, BasketResult
from .comprehensive import ComprehensiveResult, compute_comprehensive
from .goals import GoalResult, evaluate_goals, summary_table
from .grade import GPAResult, compute_gpa, target_breakdown
from .loader import CalcData, load_calc_data
from .metrics import METRIC_DEFS, MetricsResult, compute_metrics
from .model import Activity, Course, Goal, Major, Profile, Rules


@dataclass
class CalcResult:
    """一次完整计算的输出。"""

    major: Major | None = None
    profile: Profile = field(default_factory=Profile)
    gpa: GPAResult = field(default_factory=GPAResult)
    basket: BasketResult = field(default_factory=BasketResult)
    metrics: MetricsResult = field(default_factory=MetricsResult)
    comprehensive: ComprehensiveResult = field(default_factory=ComprehensiveResult)
    goals: list[GoalResult] = field(default_factory=list)
    overview: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "major": {
                "id": self.major.id, "name": self.major.name,
                "college": self.major.college, "degree": self.major.degree,
                "years": self.major.years, "total_credits": self.major.total_credits,
                "credits_official": self.major.credits_official,
                "source": self.major.source, "confidence": self.major.confidence,
            } if self.major else None,
            "gpa": self.gpa.as_dict(),
            "basket": self.basket.as_dict(),
            "metrics": self.metrics.as_dict(),
            "comprehensive": self.comprehensive.as_dict(),
            "goals": [g.as_dict() for g in self.goals],
            "overview": self.overview,
            "warnings": self.warnings,
        }


class Calculator:
    """绩点 / 德育 / 综测计算器。"""

    def __init__(self, data: CalcData | None = None,
                 directory: str | Path | None = None):
        self.data = data or load_calc_data(directory)
        self.rules: Rules = self.data.rules
        self.basket = Basket(self.data.activities, self.rules)

    # ------------------------------------------------------------------ #
    # 目录类查询（前端渲染用）
    # ------------------------------------------------------------------ #
    @property
    def majors(self) -> list[Major]:
        return self.data.majors

    @property
    def goals(self) -> list[Goal]:
        return self.data.goals

    @property
    def activities(self) -> list[Activity]:
        return self.data.activities

    def catalog(self) -> dict:
        """一次性给前端所有静态数据：专业、课程、规则、门槛、活动、指标。"""
        return {
            "majors": [self._major_json(m) for m in self.data.majors],
            "goals": [self._goal_json(g) for g in self.data.goals],
            "activities": [self._activity_json(a) for a in self.data.activities],
            "categories": sorted({a.category for a in self.data.activities if a.category}),
            "levels": sorted({a.level for a in self.data.activities if a.level}),
            "channels": sorted({c for a in self.data.activities for c in a.channels}),
            "metrics": [
                {"key": m.key, "label": m.label, "unit": m.unit, "kind": m.kind,
                 "fillable": m.fillable, "hint": m.hint,
                 "higher_is_better": m.higher_is_better}
                for m in METRIC_DEFS
            ],
            "grade_table": {
                "name": self.rules.gpa.name, "max_gp": self.rules.gpa.max_gp,
                "bands": [
                    {"lo": b.lo, "hi": b.hi, "gp": b.gp, "mode": b.mode,
                     "lp": b.lp, "hp": b.hp, "note": b.note}
                    for b in self.rules.gpa.bands
                ],
                "levels": self.rules.gpa.levels,
                "fail_score": self.rules.gpa.fail_score,
                "retake_policy": self.rules.gpa.retake_policy,
                "retake_cap": self.rules.gpa.retake_cap,
                "comprehensive_excludes_retakes":
                    self.rules.gpa.comprehensive_excludes_retakes,
                "note": self.rules.gpa.note,
            },
            "comprehensive": self.rules.comprehensive,
            "discount": self.rules.discount,
            "notes": self.rules.notes,
            "sources": self.rules.sources,
            "meta": self.data.meta,
            "warnings": self.data.warnings,
            "goal_requirements": None,
        }

    def _major_json(self, m: Major) -> dict:
        return {
            "id": m.id, "name": m.name, "college": m.college,
            "degree": m.degree, "years": m.years,
            "total_credits": m.total_credits,
            # 课程列表的学分合计（可能大于官方毕业总学分：列表里把选修课都列出来了，
            # 而一个学生不会全选）。绩点分母用的是这个数。
            "credits_listed": round(sum(c.credits for c in m.courses), 2),
            "credits_official": m.credits_official,
            "group_credits_official": m.group_credits_official,
            "source": m.source, "confidence": m.confidence,
            "credit_groups": [
                {"id": g.id, "name": g.name, "credits": g.credits,
                 "counts_toward_ranking": g.counts_toward_ranking, "note": g.note}
                for g in m.groups
            ],
            "requirements": m.requirements,
            "courses": [
                {"code": c.code, "name": c.name, "credits": c.credits,
                 "group": c.group, "term": c.term, "kind": c.kind,
                 "assess": c.assess, "counts_toward_gpa": c.counts_toward_gpa,
                 "counts_toward_ranking": c.counts_toward_ranking, "note": c.note}
                for c in m.courses
            ],
            "terms": self._terms(m),
        }

    @staticmethod
    def _terms(m: Major) -> list[dict]:
        """把课程按学期分组，方便前端画「大几上什么课」。"""
        buckets: dict[int, list[Course]] = {}
        for c in m.courses:
            buckets.setdefault(c.term, []).append(c)
        out = []
        for term in sorted(buckets):
            courses = sorted(buckets[term], key=lambda c: (-c.credits, c.code))
            out.append({
                "term": term,
                "label": _term_label(term),
                "credits": round(sum(c.credits for c in courses), 2),
                "courses": [
                    {"code": c.code, "name": c.name, "credits": c.credits,
                     "group": c.group, "kind": c.kind, "assess": c.assess}
                    for c in courses
                ],
            })
        return out

    def _goal_json(self, g: Goal) -> dict:
        return {
            "id": g.id, "name": g.name, "kind": g.kind, "summary": g.summary,
            "quota": g.quota, "amount": g.amount, "source": g.source,
            "confidence": g.confidence, "formula": g.formula,
            "requirements": [
                {"metric": r.metric, "label": r.label, "op": r.op, "value": r.value,
                 "hard": r.hard, "note": r.note, "source": r.source,
                 "confidence": r.confidence}
                for r in g.requirements
            ],
        }

    def _activity_json(self, a: Activity) -> dict:
        preview = self.basket.preview_all().get(a.id, {})
        return {
            "id": a.id, "name": a.name, "category": a.category, "level": a.level,
            "organizer": a.organizer, "channels": a.channels,
            "achieve_map": a.achieve_map, "default_achieve": a.default_achieve,
            "discount": a.discount, "timing": a.timing,
            "eligibility": a.eligibility, "url": a.url, "source": a.source,
            "confidence": a.confidence, "note": a.note, "tags": a.tags,
            "achievements": a.achievements(),
            "preview": preview,
            "rubric": {ch: self.basket.rubric_of(ch) for ch in a.channels},
            "channel_rubric": dict(self.basket.channel_rubric),
        }

    # ------------------------------------------------------------------ #
    # 主计算
    # ------------------------------------------------------------------ #
    def evaluate(self, profile: Profile,
                 basket_items: list[BasketItem] | None = None) -> CalcResult:
        major = self.data.major(profile.major_id) if profile.major_id else None
        courses = major.courses if major else []
        res = CalcResult(major=major, profile=profile)
        res.warnings.extend(self.data.warnings)

        if major is None:
            res.warnings.append("没有选择专业，或所选专业不在培养方案库里，"
                                "绩点与课程分摊都无法计算。")

        # 1) 成绩单 → 绩点
        res.gpa = compute_gpa(courses, profile, self.rules.gpa)

        # 2) 活动篮 → 各通道加分
        res.basket = self.basket.compute(list(basket_items or []))

        # 3) 汇总指标（手填优先）
        res.metrics = compute_metrics(profile, res.gpa, res.basket)

        # 4) 综测总分
        res.comprehensive = compute_comprehensive(self.rules, res.metrics,
                                                  self.rules.gpa)
        if res.comprehensive.total:
            res.metrics.values.setdefault("comprehensive", res.comprehensive.total)
            res.metrics.values["comprehensive"] = res.comprehensive.total
            res.metrics.sources["comprehensive"] = "由综测分项加权 + 活动篮加分合成"
        if (res.comprehensive.rank_percent_estimate is not None
                and "comprehensive_rank_percent" not in (profile.metrics or {})):
            res.metrics.values["comprehensive_rank_percent"] = \
                res.comprehensive.rank_percent_estimate
            res.metrics.sources["comprehensive_rank_percent"] = \
                "按 rules.json 的分数→排名曲线估算（粗估，非官方）"

        # 5) 门槛判定 + 课程目标分摊
        # 先按所选专业把「门槛里留白的目标值」补上（如毕业总学分要求）
        goals = self._resolve_goal_targets(self.data.goals, major)
        res.goals = evaluate_goals(goals, res.metrics, res.gpa,
                                   courses, self.rules.gpa)
        res.overview = summary_table(res.goals)
        return res

    @staticmethod
    def _resolve_goal_targets(goals: list[Goal], major: Major | None) -> list[Goal]:
        """把门槛里 value=0 的占位替换成来自所选专业的数值。

        目前只用于「毕业总学分」这类与专业绑定的门槛：数据文件里写 0，
        运行时替换成该专业培养方案的总学分，这样加专业不用改门槛文件。
        """
        if major is None:
            return goals
        import copy

        out: list[Goal] = []
        for g in goals:
            needs = any(r.metric == "credits_earned" and not r.value
                        for r in g.requirements)
            if not needs:
                out.append(g)
                continue
            g2 = copy.deepcopy(g)
            for r in g2.requirements:
                if r.metric == "credits_earned" and not r.value:
                    r.value = float(major.total_credits)
                    if not r.note:
                        r.note = (f"门槛值取自 {major.name} 培养方案总学分 "
                                  f"{major.total_credits:g}")
            out.append(g2)
        return out

    # ------------------------------------------------------------------ #
    def evaluate_dict(self, payload: dict) -> CalcResult:
        """给 HTTP 层用：直接把前端 JSON 转成 Profile + BasketItem。"""
        prof_raw = payload.get("profile") or {}
        profile = Profile(
            major_id=str(prof_raw.get("major_id") or ""),
            name=str(prof_raw.get("name") or ""),
            grade=str(prof_raw.get("grade") or ""),
            scores=dict(prof_raw.get("scores") or {}),
            retakes=[str(x) for x in (prof_raw.get("retakes") or [])],
            metrics={k: v for k, v in (prof_raw.get("metrics") or {}).items()},
            cohort_size=int(prof_raw.get("cohort_size") or 0),
            rank=int(prof_raw.get("rank") or 0),
            manual_scores=dict(prof_raw.get("manual_scores") or {}),
        )
        items = [BasketItem.from_dict(d) for d in (payload.get("basket") or [])]
        return self.evaluate(profile, items)

    # ------------------------------------------------------------------ #
    def target_for_course(self, major_id: str, scores: dict, target_gpa: float) -> dict:
        """单独问：「要在毕业时拿到 X 绩点，剩下每门课要考多少分」。"""
        major = self.data.major(major_id)
        if major is None:
            return {"error": f"未知专业：{major_id}"}
        profile = Profile(major_id=major_id, scores=dict(scores or {}))
        gpa = compute_gpa(major.courses, profile, self.rules.gpa)
        bd = target_breakdown(gpa, major.courses, self.rules.gpa, float(target_gpa))
        return {
            "current_gpa": round(gpa.gpa, 4),
            "target_gpa": float(target_gpa),
            "achievable": bd.achievable,
            "message": bd.message,
            "remaining_credits": bd.remaining_credits,
            "required_remaining_gpa": bd.required_remaining_gpa,
            "required_remaining_score": bd.required_remaining_score,
            "max_possible_gpa": bd.max_possible_gpa,
            "per_course": bd.per_course,
        }


def _term_label(term: int) -> str:
    if term <= 0:
        return "未标注学期"
    year = (term + 1) // 2
    half = "秋" if term % 2 == 1 else "春"
    return f"大{year}{half}（第 {term} 学期）"
