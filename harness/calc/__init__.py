"""绩点 / 德育 / 综测计算器。

纯标准库实现，不依赖 Web 层，可单独被 CLI 调用或写成测试。

模块分工：

- :mod:`harness.calc.model`        数据模型（培养方案、规则、门槛、活动）
- :mod:`harness.calc.loader`       读取 `calcdata/*.json` 并做校验
- :mod:`harness.calc.grade`        绩点换算与平均学分绩点
- :mod:`harness.calc.metrics`      只读推算值（志愿时长、四六级、I 值等）
- :mod:`harness.calc.basket`       活动篮：选活动 → 各通道加分
- :mod:`harness.calc.competitions` 《学生竞赛奖励办法》名录 → 具体赛事活动
- :mod:`harness.calc.online`       「刷新联网」：抓官网名录页 → 对账 → 缓存（不调模型）
- :mod:`harness.calc.goals`        门槛判定 + 分摊到课程的分数要求
- :mod:`harness.calc.engine`       Facade：一次调用算完全部结果
"""
from __future__ import annotations

from .basket import Basket, BasketItem, BasketResult, ChannelAward
from .comprehensive import ComprehensiveResult, compute_comprehensive
from .engine import CalcResult, Calculator
from .goals import CheckResult, GoalResult, evaluate_goals, summary_table
from .grade import CourseResult, GPAResult, GradeTable, TargetBreakdown
from .grade import compute_gpa, gpa_to_score, target_breakdown
from .loader import CalcData, CalcDataError, load_calc_data
from .metrics import METRIC_DEFS, MetricDef, MetricsResult, compute_metrics
from .model import (
    Activity,
    Course,
    CreditGroup,
    Goal,
    Major,
    Profile,
    Requirement,
    Rules,
    ScoreBand,
)

__all__ = [
    "Activity",
    "Basket",
    "BasketItem",
    "BasketResult",
    "CalcData",
    "CalcDataError",
    "CalcResult",
    "Calculator",
    "ChannelAward",
    "CheckResult",
    "ComprehensiveResult",
    "Course",
    "CourseResult",
    "CreditGroup",
    "GPAResult",
    "Goal",
    "GoalResult",
    "GradeTable",
    "Major",
    "MetricDef",
    "METRIC_DEFS",
    "MetricsResult",
    "Profile",
    "Requirement",
    "Rules",
    "ScoreBand",
    "TargetBreakdown",
    "compute_comprehensive",
    "compute_gpa",
    "compute_metrics",
    "evaluate_goals",
    "gpa_to_score",
    "load_calc_data",
    "summary_table",
    "target_breakdown",
]
