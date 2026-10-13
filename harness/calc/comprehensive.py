"""综测总分合成。

综测是「**分量表 + 加分**」的结构，不是单一公式，所以这里拆成两层：

1. **分项得分**（各 0-100 分）：智育、德育、体育、美育/劳动。每个分项怎么算
   由 `rules.json` 的 `comprehensive.dimensions` 描述：

   - `source: derived` 从成绩单推算（智育 = 加权平均分，或绩点×缩放）；
   - `source: metric`  直接取学生填的指标（德育分、体育素质分）。

2. **加权合成**：`综测总分 = Σ(分项得分 × 权重) + 直接加分`。

   `活动篮`里的通道如果映射到某个分项（例如「德育加分」→ 德育分项），
   会先加到该分项再乘以权重；映射到 `direct` 的通道则直接加到总分上。
   这样「加 1 分德育分」和「加 1 分综测分」的差别就能如实反映出来。

所有系数来自数据文件，代码不含任何学校特有的数字。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .metrics import MetricsResult
from .model import GradeTable, Rules


@dataclass
class Dimension:
    id: str
    name: str
    weight: float = 0.0
    source: str = "metric"          # derived / metric
    metric: str = ""                # source=metric 时读哪个指标
    derive: str = "avg_score"       # source=derived 时的算法名
    scale: float = 1.0              # derived 时的缩放系数
    cap: float = 100.0              # 该项上限
    floor: float = 0.0
    base: float = 0.0               # 固定基础分（手动填的指标缺省用）
    bonus_cap: float = 0.0          # 加分项上限（0 = 不单独限制，只受 cap 约束）
    note: str = ""


@dataclass
class DimensionScore:
    id: str
    name: str
    raw: float = 0.0                # 含加分后的分项得分
    base_raw: float = 0.0           # 加活动分之前的得分
    bonus: float = 0.0              # 来自活动篮的加分（已按 bonus_cap 截断）
    bonus_overflow: float = 0.0     # 因 bonus_cap 被截掉的加分
    weight: float = 0.0
    contribution: float = 0.0
    capped: bool = False
    bonus_capped: bool = False
    source: str = ""
    note: str = ""

    def as_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "raw": round(self.raw, 3),
            "base_raw": round(self.base_raw, 3), "bonus": round(self.bonus, 3),
            "bonus_overflow": round(self.bonus_overflow, 3),
            "weight": self.weight,
            "contribution": round(self.contribution, 3),
            "capped": self.capped, "bonus_capped": self.bonus_capped,
            "source": self.source, "note": self.note,
        }


@dataclass
class ComprehensiveResult:
    total: float = 0.0
    dimensions: list[DimensionScore] = field(default_factory=list)
    direct_bonus: float = 0.0
    direct_items: list[dict] = field(default_factory=list)
    unmapped_bonus: list[dict] = field(default_factory=list)
    excluded_channels: list[dict] = field(default_factory=list)
    rank_percent_estimate: float | None = None
    warnings: list[str] = field(default_factory=list)
    formula_text: str = ""

    def as_dict(self) -> dict:
        return {
            "total": round(self.total, 3),
            "dimensions": [d.as_dict() for d in self.dimensions],
            "direct_bonus": round(self.direct_bonus, 3),
            "direct_items": self.direct_items,
            "unmapped_bonus": self.unmapped_bonus,
            "excluded_channels": self.excluded_channels,
            "rank_percent_estimate": self.rank_percent_estimate,
            "warnings": self.warnings,
            "formula_text": self.formula_text,
        }

    def get(self, dim_id: str) -> DimensionScore | None:
        for d in self.dimensions:
            if d.id == dim_id:
                return d
        return None


def build_dimensions(rules: Rules) -> list[Dimension]:
    spec = (rules.comprehensive or {}) if hasattr(rules, "comprehensive") else {}
    out: list[Dimension] = []
    for item in (spec.get("dimensions") or []):
        out.append(Dimension(
            id=str(item.get("id", "")),
            name=str(item.get("name", item.get("id", ""))),
            weight=float(item.get("weight", 0.0)),
            source=str(item.get("source", "metric")),
            metric=str(item.get("metric", "")),
            derive=str(item.get("derive", "avg_score")),
            scale=float(item.get("scale", 1.0)),
            cap=float(item.get("cap", 100.0)),
            floor=float(item.get("floor", 0.0)),
            base=float(item.get("base", 0.0)),
            bonus_cap=float(item.get("bonus_cap", 0.0)),
            note=str(item.get("note", "")),
        ))
    return out


def compute_comprehensive(rules: Rules, metrics: MetricsResult,
                          table: GradeTable) -> ComprehensiveResult:
    """合成综测总分。"""
    res = ComprehensiveResult()
    spec = getattr(rules, "comprehensive", {}) or {}
    dims = build_dimensions(rules)

    # 通道 → 分项 / direct / none 的路由表。显式声明是必要的：
    # 没有它就无法区分「细则没给这个通道」和「这个通道本来就不算综测」。
    routing: dict[str, str] = dict(spec.get("bonus_routing") or {})

    # 活动篮里各通道的分数（metrics 里已经按通道汇总好，键是 metric_key）
    channel_metric_map: dict[str, str] = {
        str(k): str(v) for k, v in (spec.get("channel_metrics") or {}).items()}
    channel_bonus: dict[str, float] = {}
    for channel, metric_key in channel_metric_map.items():
        if channel not in routing:
            # 没在路由表里声明过的通道，认为它不进综测，避免把
            # 第二课堂学分、志愿服务时长这类量纲完全不同的数直加进总分。
            continue
        val = metrics.get(metric_key)
        if val:
            channel_bonus[channel] = float(val)

    # 先把加分路由到分项
    dim_bonus: dict[str, float] = {}
    for channel, pts in channel_bonus.items():
        route = routing.get(channel)
        if route is None:
            continue
        if route == "none":
            continue
        if route in ("direct", "total"):
            res.direct_bonus += pts
            res.direct_items.append({"channel": channel, "points": round(pts, 3)})
        else:
            dim_bonus[route] = dim_bonus.get(route, 0.0) + pts

    # 已声明但不进综测的通道，单独告知界面，免得学生以为没生效。
    # 注意：即使当前得分为 0 也要列出来——「这个通道算不算综测」是规则问题，
    # 不是数值问题，学生需要知道第二课堂学分不会被算进综测分。
    for ch, metric_key in channel_metric_map.items():
        val = metrics.get(metric_key)
        if val is None:
            continue
        if routing.get(ch) == "none":
            res.excluded_channels.append(
                {"channel": ch, "metric": metric_key,
                 "points": round(float(val), 3),
                 "why": "该通道只用于推免综合评价 / 学分认定，不计入综测总分"})
        elif ch not in routing:
            res.unmapped_bonus.append(
                {"channel": ch, "metric": metric_key,
                 "points": round(float(val), 3),
                 "why": "该通道未在 rules.json 的 bonus_routing 里声明，未计入综测"})

    for d in dims:
        ds = DimensionScore(id=d.id, name=d.name, weight=d.weight, note=d.note)
        if d.source == "derived":
            base_val = _derive(d, metrics, table)
            ds.source = f"由成绩单推算（{d.derive}）"
        else:
            val = metrics.get(d.metric)
            base_val = float(val) if val is not None else d.base
            ds.source = ("学生手填：" + (d.metric or "—")) if val is not None else "未填，按基础分"
        # 基础分本身受该分项的「基础分上限」约束
        base_cap = d.cap
        if d.bonus_cap:
            base_cap = max(0.0, d.cap - d.bonus_cap)
        if base_val > base_cap:
            base_val = base_cap
            ds.capped = True
        ds.base_raw = base_val

        # 加分单独受 bonus_cap 限制：细则常写「本项加分不超过 X 分」，
        # 这是对加分本身的限制，不是对总分的限制。
        raw_bonus = dim_bonus.get(d.id, 0.0)
        if d.bonus_cap and raw_bonus > d.bonus_cap:
            ds.bonus = d.bonus_cap
            ds.bonus_overflow = raw_bonus - d.bonus_cap
            ds.bonus_capped = True
        else:
            ds.bonus = raw_bonus
        if ds.bonus_capped:
            res.warnings.append(
                f"「{d.name}」加分累计 {raw_bonus:.2f} 分，已按细则上限"
                f" {d.bonus_cap:g} 分截断（超出 {ds.bonus_overflow:.2f} 分不计）。")

        raw = base_val + ds.bonus
        if raw > d.cap:
            raw = d.cap
            ds.capped = True
        if raw < d.floor:
            raw = d.floor
        ds.raw = raw
        ds.contribution = raw * d.weight
        res.dimensions.append(ds)

    res.total = sum(d.contribution for d in res.dimensions) + res.direct_bonus
    res.unmapped_bonus = [
        {"channel": k, "points": round(v, 3)} for k, v in channel_bonus.items()
        if k not in routing and not any(d.name and d.name in k for d in dims)
    ]
    res.rank_percent_estimate = _estimate_rank(res.total, spec)
    res.formula_text = spec.get("formula_text", "") or _formula_text(res)
    return res


# --------------------------------------------------------------------------- #
def _derive(d: Dimension, metrics: MetricsResult, table: GradeTable) -> float:
    """按算法名从指标里推算分项得分。"""
    if d.derive == "avg_score":
        return float(metrics.get("avg_score") or 0.0)
    if d.derive == "gpa":
        return float(metrics.get("gpa") or 0.0)
    if d.derive == "gpa_scaled":
        # 绩点 × 缩放系数（把 5 分制绩点映射到 100 分制时用）
        return float(metrics.get("gpa") or 0.0) * d.scale
    if d.derive == "gpa_ratio":
        # 生命科学学院口径：智育基础分 = 本人学年度平均绩点 ÷ 本年级本专业
        # 最高平均绩点 × 55。学生手填专业最高绩点则用真实值，否则用估计值。
        own = float(metrics.get("gpa") or 0.0)
        top = float(metrics.get("major_top_gpa") or 0.0)
        if own and top:
            return min(d.cap, own / top * d.base)
        # 没填最高绩点时退回「按加权平均分折算」，并在 note 里说明
        return float(metrics.get("avg_score") or 0.0)
    if d.derive == "constant":
        return d.base
    # 兜底：直接按指标名取
    return float(metrics.get(d.derive) or 0.0)


def _estimate_rank(total: float, spec: dict) -> float | None:
    """用配置的分数→百分位表插值估算综测排名。没有配就返回 None。

    这只是**粗略估算**，配置里必须写明它基于哪一年的哪份表格。
    """
    table = spec.get("rank_curve") or []
    if not table or total <= 0:
        return None
    pts = sorted((float(p["score"]), float(p["percent"])) for p in table)
    if total >= pts[-1][0]:
        return pts[-1][1]
    if total <= pts[0][0]:
        return pts[0][1]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if x0 <= total <= x1:
            if x1 == x0:
                return y1
            return round(y0 + (total - x0) / (x1 - x0) * (y1 - y0), 2)
    return None


def _formula_text(res: ComprehensiveResult) -> str:
    parts = [f"{d.name}×{d.weight:g}" for d in res.dimensions if d.weight]
    txt = " + ".join(parts) if parts else "（未配置综测权重）"
    if res.direct_bonus:
        txt += f" + 直接加分{res.direct_bonus:g}"
    return txt
