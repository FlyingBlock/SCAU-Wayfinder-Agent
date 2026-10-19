"""门槛判定：保研 / 考研 / 奖学金分别要什么，现在差多少。

判定是**纯数据驱动**的：门槛写成 `{metric, op, value}`，代码只负责比较。
这样换一套细则（比如学院推免办法改了四级分数线）只改数据文件。

除了「够不够」，还回答两个更实用的问题：

- **差多少**：`gap` 给出还差多少分 / 多少名次；
- **怎么补**：如果门槛卡在绩点上，用 :func:`wayfinder.calc.grade.target_breakdown`
  把「总绩点要到 X」分摊成「剩下每门课要考多少分」。
"""
from __future__ import annotations

import operator
from dataclasses import dataclass, field

from .grade import GPAResult, TargetBreakdown, target_breakdown
from .metrics import MetricsResult
from .model import Course, Goal, GradeTable, Requirement

_OPS = {
    ">=": operator.ge, "<=": operator.le, ">": operator.gt, "<": operator.lt,
    "==": operator.eq, "!=": operator.ne,
}


@dataclass
class CheckResult:
    """一条门槛的判定结果。"""

    metric: str
    label: str
    op: str
    value: float
    actual: float | None
    passed: bool | None            # None = 数据缺失，无法判定
    hard: bool = True
    gap: float = 0.0               # 还差多少（正数=还差这么多）
    note: str = ""
    source: str = ""
    confidence: str = ""
    metric_source: str = ""        # 这个数值是手填的还是推算的

    def as_dict(self) -> dict:
        return {
            "metric": self.metric, "label": self.label, "op": self.op,
            "required": self.value, "actual": self.actual, "passed": self.passed,
            "hard": self.hard, "gap": round(self.gap, 3), "note": self.note,
            "source": self.source, "confidence": self.confidence,
            "metric_source": self.metric_source,
        }

    def describe(self) -> str:
        if self.actual is None:
            return f"{self.label}：未填（要求 {self.op} {self.value:g}）"
        mark = "✅" if self.passed else ("❌" if self.hard else "⚠️")
        base = f"{mark} {self.label}：{self.actual:g} / 要求 {self.op} {self.value:g}"
        if self.passed is False and self.gap:
            base += f"（还差 {self.gap:g}）"
        return base


@dataclass
class GoalResult:
    """一条路线的完整判定。"""

    goal_id: str
    name: str
    kind: str = "route"
    summary: str = ""
    checks: list[CheckResult] = field(default_factory=list)
    # 硬门槛是否全过（缺数据算「未知」）
    hard_passed: bool | None = None
    unknown: list[str] = field(default_factory=list)
    # 卡在绩点上时的课程分摊方案 {target_gpa: breakdown}
    breakdowns: dict[str, TargetBreakdown] = field(default_factory=dict)
    quota: str = ""
    amount: str = ""
    source: str = ""
    confidence: str = ""

    @property
    def failed(self) -> list[CheckResult]:
        return [c for c in self.checks if c.passed is False]

    def as_dict(self) -> dict:
        return {
            "goal_id": self.goal_id, "name": self.name, "kind": self.kind,
            "summary": self.summary, "hard_passed": self.hard_passed,
            "unknown": self.unknown,
            "quota": self.quota, "amount": self.amount,
            "source": self.source, "confidence": self.confidence,
            "checks": [c.as_dict() for c in self.checks],
            "breakdowns": {
                k: {
                    "target_gpa": v.target_gpa, "achievable": v.achievable,
                    "message": v.message,
                    "difficulty": v.difficulty,
                    "difficulty_note": v.difficulty_note,
                    "remaining_credits": v.remaining_credits,
                    "required_remaining_gpa": v.required_remaining_gpa,
                    "required_remaining_score": v.required_remaining_score,
                    "max_possible_gpa": v.max_possible_gpa,
                    "per_course": v.per_course,
                } for k, v in self.breakdowns.items()
            },
        }


def evaluate_requirement(req: Requirement, metrics: MetricsResult) -> CheckResult:
    actual = metrics.get(req.metric)
    label = req.label or req.metric
    res = CheckResult(
        metric=req.metric, label=label, op=req.op, value=float(req.value),
        actual=actual, passed=None, hard=req.hard, note=req.note,
        source=req.source, confidence=req.confidence,
        metric_source=metrics.sources.get(req.metric, ""),
    )
    if actual is None:
        return res
    fn = _OPS.get(req.op, operator.ge)
    try:
        res.passed = bool(fn(float(actual), float(req.value)))
    except (TypeError, ValueError):
        res.passed = None
        return res
    if not res.passed:
        # gap 一律按「还差多少才够」的正数表示
        if req.op in (">=", ">"):
            res.gap = round(float(req.value) - float(actual), 4)
        elif req.op in ("<=", "<"):
            res.gap = round(float(actual) - float(req.value), 4)
    return res


def evaluate_goals(goals: list[Goal], metrics: MetricsResult,
                   gpa: GPAResult, courses: list[Course],
                   table: GradeTable) -> list[GoalResult]:
    """判定全部路线，并对卡绩点的路线给出课程分摊。"""
    out: list[GoalResult] = []
    for goal in goals:
        gr = GoalResult(
            goal_id=goal.id, name=goal.name, kind=goal.kind, summary=goal.summary,
            quota=goal.quota, amount=goal.amount, source=goal.source,
            confidence=goal.confidence,
        )
        for req in goal.requirements:
            gr.checks.append(evaluate_requirement(req, metrics))

        hards = [c for c in gr.checks if c.hard]
        unknown = [c.label for c in hards if c.passed is None]
        gr.unknown = unknown
        if unknown:
            gr.hard_passed = None
        else:
            gr.hard_passed = all(c.passed for c in hards)

        # 如果门槛里有绩点目标，反推剩余课程需要的分数
        for c in gr.checks:
            if c.metric in ("gpa", "ranking_gpa") and c.op in (">=", ">"):
                # 用到的绩点口径：排名课门槛用 ranking_gpa，否则用总绩点
                target = float(c.value)
                key = f"{c.metric}>={target:g}"
                gr.breakdowns[key] = target_breakdown(gpa, courses, table, target)
        out.append(gr)
    return out


def summary_table(results: list[GoalResult]) -> list[dict]:
    """给界面用的路线总览：每条路线过没过、差在哪。"""
    rows = []
    for r in results:
        if r.hard_passed is None:
            status = "待补数据"
        elif r.hard_passed:
            status = "已达标"
        else:
            status = "未达标"
        blocking = [c for c in r.checks if c.hard and c.passed is False]
        rows.append({
            "goal_id": r.goal_id, "name": r.name, "kind": r.kind,
            "status": status, "quota": r.quota, "amount": r.amount,
            "blocking": [c.describe() for c in blocking],
            "unknown": r.unknown,
        })
    return rows
