"""活动篮：勾选活动 → 实时算出各通道能拿多少分。

折算模型分两步，都能在界面上看到：

1. **等级系数**（`level_ratio`）：国家级 1.0、省级 0.6、市级 0.5、校级 0.35、
   院级 0.2。它回答「校级一等奖大概相当于国家级一等奖的几成」。
2. **名次系数**（`rank_ratio`）：一等奖 1.0、二等奖 0.7、三等奖 0.5、参与 0.2。

单次得分 = 基准分 × 等级系数 × 名次系数 × 份数。

这两张系数表写在 `calcdata/rules.json` 的 `discount` 段里，属于**可调参数**：
真实细则如果直接给死了「校级三等奖加 0.5 分」，就把该活动的 `discount` 设成
`none`，直接写死基准分，不让系数介入。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .model import Activity, Rules


@dataclass
class BasketItem:
    """活动篮里的一项：选了哪个活动、什么名次、几份。"""

    activity_id: str
    achieve: str = ""
    quantity: int = 1
    note: str = ""
    # 前端回显用，不进哈希
    name: str = ""

    def to_dict(self) -> dict:
        return {"activity_id": self.activity_id, "achieve": self.achieve,
                "quantity": self.quantity, "note": self.note}

    @classmethod
    def from_dict(cls, d: dict) -> "BasketItem":
        return cls(
            activity_id=str(d.get("activity_id") or d.get("id") or ""),
            achieve=str(d.get("achieve") or ""),
            quantity=max(1, int(d.get("quantity") or 1)),
            note=str(d.get("note") or ""),
        )


@dataclass
class ChannelAward:
    """一项活动在某个通道上的得分明细。"""

    channel: str
    metric_key: str
    base: float
    level_ratio: float = 1.0
    rank_ratio: float = 1.0
    quantity: int = 1
    points: float = 0.0
    discount: str = "level_ratio"
    note: str = ""
    clipped: bool = False          # 是否被该通道上限截断

    def explain(self) -> str:
        if self.discount == "none":
            return f"{self.base:g} × {self.quantity} = {self.points:g}"
        return (f"{self.base:g} × 等级{self.level_ratio:g} × "
                f"名次{self.rank_ratio:g} × {self.quantity} = {self.points:g}")


@dataclass
class BasketLine:
    """活动篮里一行：活动 + 它在各通道的得分。"""

    activity_id: str
    name: str
    category: str
    level: str
    achieve: str
    quantity: int
    awards: list[ChannelAward] = field(default_factory=list)
    total_points: float = 0.0
    source: str = ""
    confidence: str = ""
    url: str = ""

    def to_dict(self) -> dict:
        return {
            "activity_id": self.activity_id, "name": self.name,
            "category": self.category, "level": self.level,
            "achieve": self.achieve, "quantity": self.quantity,
            "total_points": round(self.total_points, 3),
            "awards": [
                {"channel": a.channel, "metric_key": a.metric_key,
                 "base": a.base, "points": round(a.points, 3),
                 "explain": a.explain(), "clipped": a.clipped}
                for a in self.awards
            ],
            "source": self.source, "confidence": self.confidence, "url": self.url,
        }


@dataclass
class BasketResult:
    items: list[BasketLine] = field(default_factory=list)
    channel_totals: dict[str, float] = field(default_factory=dict)
    metric_totals: dict[str, float] = field(default_factory=dict)
    channel_metrics: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    def metric_key(self, channel: str) -> str:
        return self.channel_metrics.get(channel, "")

    def as_dict(self) -> dict:
        return {
            "items": [i.to_dict() for i in self.items],
            "channel_totals": {k: round(v, 3) for k, v in self.channel_totals.items()},
            "metric_totals": {k: round(v, 3) for k, v in self.metric_totals.items()},
            "channel_metrics": self.channel_metrics,
            "warnings": self.warnings,
        }


# 通道 → 指标键。通道名就是 `Activity.channels` 的键。
# 「德育/智育/体育/美育/劳育」五个是**综测**通道，对应综合测评的五个分项；
# 「创新能力/发展素养」是**推免综合评价**通道，不进综测；
# 最后三个是学分/时长类，也不进综测。
DEFAULT_CHANNEL_METRICS: dict[str, str] = {
    "德育加分": "moral_bonus",
    "智育加分": "academic_bonus",
    "体育加分": "sports_arts_bonus",
    "美育加分": "aesthetic_bonus",
    "劳育加分": "labour_bonus",
    "创新能力": "innovation_score",
    "发展素养": "development_literacy",
    "第二课堂": "second_classroom",
    "创新创业学分": "innovation_credits",
    "志愿服务时长": "volunteer_hours",
    "综测加分": "comprehensive_bonus",
}

# 通道属于哪套评分表。同一件事（例如一篇 T2 论文）在综测里写
# 「第1-2作者 8 分」，在推免里写「基础分 6，第 2 作者 ×0.8」——分值互不相同，
# 所以每个通道必须知道自己该用哪套口径。
DEFAULT_CHANNEL_RUBRIC: dict[str, str] = {
    "德育加分": "综测", "智育加分": "综测", "体育加分": "综测",
    "美育加分": "综测", "劳育加分": "综测", "综测加分": "综测",
    "创新能力": "推免", "发展素养": "推免",
    "第二课堂": "学分", "创新创业学分": "学分", "志愿服务时长": "时长",
}


class Basket:
    """活动篮计算器。"""

    # 这些通道的单位不是「分」，而是学分或小时。混在一起求和没有意义，
    # 所以界面上的「最高能加多少分」只统计下面这些之外的点数通道。
    NON_SCORE_CHANNELS = {
        "第二课堂", "创新创业学分", "志愿服务时长",
    }

    def __init__(self, activities: list[Activity], rules: Rules | None = None):
        self.by_id = {a.id: a for a in activities}
        self.rules = rules or Rules()
        self.channel_metrics = dict(DEFAULT_CHANNEL_METRICS)
        # 通道属于哪套评分表：综测 / 推免。同一件事在两套表里的分值往往不同。
        self.channel_rubric = dict(DEFAULT_CHANNEL_RUBRIC)
        for channel, spec in (self.rules.equivalents or {}).items():
            if isinstance(spec, dict):
                if spec.get("metric"):
                    self.channel_metrics[channel] = str(spec["metric"])
                if spec.get("rubric"):
                    self.channel_rubric[channel] = str(spec["rubric"])

    def is_score_channel(self, channel: str) -> bool:
        """该通道的单位是不是「分」。"""
        return channel not in self.NON_SCORE_CHANNELS

    def metric_key(self, channel: str) -> str:
        return self.channel_metrics.get(channel, "")

    # ------------------------------------------------------------------ #
    def compute(self, items: list[BasketItem]) -> BasketResult:
        res = BasketResult()
        res.channel_metrics = dict(self.channel_metrics)

        channel_totals: dict[str, float] = {}
        metric_totals: dict[str, float] = {}
        counts: dict[str, int] = {}

        for item in items:
            act = self.by_id.get(item.activity_id)
            if act is None:
                res.warnings.append(f"活动不存在：{item.activity_id}")
                continue
            achieve = item.achieve or act.default_achieve or (
                act.achievements()[0] if act.achievements() else "")
            line = BasketLine(
                activity_id=act.id, name=act.name, category=act.category,
                level=act.level, achieve=achieve, quantity=max(1, item.quantity),
                source=act.source, confidence=act.confidence, url=act.url,
            )
            for channel, base in act.channels.items():
                # 每个通道用自己那套评分表的分值（同一件事在综测与推免里不同）
                prof = self._discount_profile(act, achieve, channel)
                metric_key = self.channel_metrics.get(channel, channel)
                pts = float(base) * prof["level"] * prof["rank"] * line.quantity
                rubric = self.rubric_of(channel)
                has_specific = act.value_for(channel, achieve) is not None
                award = ChannelAward(
                    channel=channel, metric_key=metric_key, base=float(base),
                    level_ratio=prof["level"], rank_ratio=prof["rank"],
                    quantity=line.quantity, points=pts, discount=act.discount,
                    note=(f"按「{rubric}」口径：{achieve}" if has_specific else ""),
                )
                line.awards.append(award)
                line.total_points += pts
                channel_totals[channel] = channel_totals.get(channel, 0.0) + pts
                metric_totals[metric_key] = metric_totals.get(metric_key, 0.0) + pts
            counts[act.category] = counts.get(act.category, 0) + 1
            res.items.append(line)

        # 通道上限（细则里常写「本项加分不超过 X 分」）
        caps = (self.rules.discount or {}).get("channel_caps", {}) or {}
        for channel, cap in caps.items():
            if channel in channel_totals and channel_totals[channel] > float(cap):
                over = channel_totals[channel] - float(cap)
                metric_key = self.channel_metrics.get(channel, channel)
                channel_totals[channel] = float(cap)
                metric_totals[metric_key] = max(
                    0.0, metric_totals.get(metric_key, 0.0) - over)
                res.warnings.append(
                    f"「{channel}」累计 {channel_totals[channel] + over:.2f} 分，"
                    f"已按细则上限截到 {float(cap):g} 分。")

        res.channel_totals = channel_totals
        res.metric_totals.update(metric_totals)
        return res

    # ------------------------------------------------------------------ #
    def _discount_profile(self, act: Activity, achieve: str,
                          channel: str = "") -> dict:
        """返回 {level: 系数, rank: 系数}。

        语义要点：**`rank` 是乘在通道基准分上的系数**。

        - 细则直接把分值写死时（本仓库的多数活动），`achieve_map` 里的数字
          就是**最终分值**，不是系数。这时必须让 `rank` 覆盖掉基准分，
          也就是 `rank = 该分值 / 基准分`，这样 `基准分 × 1.0 × rank` 才等于它。
        - 细则只给系数时（`discount = level_ratio`），`rank` 就是名次系数。
        """
        if act.discount == "none":
            # 绝对值口径：按通道取对应的分值，覆盖基准分
            v = act.value_for(channel, achieve,
                              self.rubric_of(channel)) if channel else None
            if v is None and channel:
                # 该成果在这个通道下没给分值 → 此项不加分
                return {"level": 1.0, "rank": 0.0, "absolute": 0.0}
            base = float(act.channels.get(channel, 0.0)) if channel else 0.0
            if base == 0:
                return {"level": 1.0, "rank": 0.0, "absolute": float(v or 0.0)}
            return {"level": 1.0, "rank": float(v) / base,
                    "absolute": float(v)}

        disc = (self.rules.discount or {}).get(act.discount or "level_ratio", {})
        level_ratios = disc.get("level_ratios") or {}
        rank_ratios = disc.get("rank_ratios") or {}
        level_ratio = float(level_ratios.get(act.level, disc.get("default_level", 1.0)))

        if channel:
            v = act.value_for(channel, achieve, self.rubric_of(channel))
            if v is not None:
                # 细则按「通道 × 成果」给了绝对分值 → 覆盖基准分
                base = float(act.channels.get(channel, 0.0))
                if base:
                    return {"level": level_ratio, "rank": float(v) / base,
                            "absolute": float(v)}
                return {"level": level_ratio, "rank": 0.0, "absolute": float(v)}

        if achieve in (act.achieve_map or {}):
            return {"level": level_ratio, "rank": 1.0}

        rank_ratio = float(rank_ratios.get(achieve, disc.get("default_rank", 1.0)))
        return {"level": level_ratio, "rank": rank_ratio}

    # ------------------------------------------------------------------ #
    def preview_all(self) -> dict:
        """不选任何活动时，每个活动的「单次得分」预览，用于列表展示。

        每个通道都按自己的评分类别取值：同一篇论文在「智育加分」（综测口径）
        和「创新能力」（推免口径）下可能得到完全不同的分数。
        """
        out: dict[str, dict] = {}
        for act in self.by_id.values():
            achieves = {}
            for ach in act.achievements():
                per_channel: dict[str, float] = {}
                ratios: dict[str, dict] = {}
                for ch, base in act.channels.items():
                    prof = self._discount_profile(act, ach, ch)
                    per_channel[ch] = round(
                        float(base) * prof["level"] * prof["rank"], 3)
                    ratios[ch] = {"level": prof["level"], "rank": prof["rank"]}
                # 总分只累加点数通道，避免把小时数和分数相加；
                # 再进一步区分「综测」和「推免」两套表，各自给一个合计。
                def _sum(rubric: str) -> float:
                    return round(sum(
                        v for ch, v in per_channel.items()
                        if self.is_score_channel(ch)
                        and self.rubric_of(ch) == rubric), 3)
                top = ratios.get(next(iter(act.channels), ""), {"level": 1.0, "rank": 1.0})
                achieves[ach] = {
                    "level_ratio": top["level"], "rank_ratio": top["rank"],
                    "channels": per_channel, "ratios": ratios,
                    "total": _sum("综测"),
                    "total_tuimian": _sum("推免"),
                    "raw_total": round(sum(per_channel.values()), 3),
                }
            out[act.id] = achieves
        return out

    def rubric_of(self, channel: str) -> str:
        """通道属于哪套评分表：综测 / 推免 / 其他。"""
        return self.channel_rubric.get(channel, "其他")
