"""CLI 共享的格式化与参数辅助：命令实现只依赖这里，不互相 import。"""
from __future__ import annotations

import argparse

import json
import sys
from pathlib import Path

from ..core.config import SETTINGS


def _print_answer(ans) -> None:
    if ans.error:
        print("\n[生成失败] " + ans.error, file=sys.stderr)
    print("\n" + ans.text.strip())
    print("\n" + "─" * 78)
    print("引用来源：")
    from ..qa.agent import Agent

    ag = Agent.__new__(Agent)          # 仅复用格式化方法，不重新初始化依赖
    print(ag.build_citations(ans))
    print("─" * 78)
    print(f"证据 {len(ans.evidence)} 条｜子查询 {len(ans.subqueries)} 条｜"
          f"LLM {SETTINGS.llm.model}｜{ans.error and '（生成异常）' or ''}")


def _trace_printer(step: str, data: dict) -> None:
    labels = {
        "decompose": "① 意图分解",
        "retrieve": "② 检索",
        "retrieved": "   命中",
        "gaps": "④ 缺口检测",
        "evidence": "⑥ 证据聚合",
    }
    label = labels.get(step, step)
    if step == "decompose":
        print(f"{label}：{len(data.get('subqueries', []))} 条子查询", file=sys.stderr)
        for q in data.get("subqueries", []):
            print(f"    [{q['scope']:4}] {q['query']}  ← {q.get('why','')[:40]}", file=sys.stderr)
    elif step == "retrieve":
        for q in data.get("queries", []):
            print(f"{label} 第 {data.get('round')} 轮：{q}", file=sys.stderr)
    elif step == "retrieved":
        print(f"{label} 第 {data.get('round')} 轮新增 {data.get('new')} 条"
              f"（累计 {data.get('total')}）", file=sys.stderr)
    elif step == "gaps":
        miss = data.get("missing", [])
        print(f"{label}：{'证据已足够' if not miss else str(len(miss)) + ' 个缺口'}", file=sys.stderr)
        for q in miss:
            print(f"    ↻ [{q['scope']:4}] {q['query']}", file=sys.stderr)
    elif step == "evidence":
        print(f"{label}：{data.get('count')} 条进入生成", file=sys.stderr)


def _calc_profile(args: argparse.Namespace):
    """把 CLI 参数变成 Profile。成绩可以传 JSON 文件或 `课程代码=分数` 列表。"""
    from ..calc import Profile

    scores: dict[str, object] = {}
    if getattr(args, "scores", None):
        scores.update(json.loads(Path(args.scores).read_text(encoding="utf-8")))
    for item in (getattr(args, "score", None) or []):
        if "=" in item:
            code, _, val = item.partition("=")
            val = val.strip()
            try:
                scores[code.strip()] = float(val)
            except ValueError:
                scores[code.strip()] = val      # 五级制，如 G1201=优秀
    metrics: dict[str, float] = {}
    for item in (getattr(args, "metric", None) or []):
        if "=" in item:
            key, _, val = item.partition("=")
            try:
                metrics[key.strip()] = float(val)
            except ValueError:
                pass
    return Profile(
        major_id=getattr(args, "major", "") or "",
        scores=scores, metrics=metrics,
        cohort_size=int(getattr(args, "cohort", 0) or 0),
        rank=int(getattr(args, "rank", 0) or 0),
    )


def _calc_basket(args: argparse.Namespace):
    from ..calc import BasketItem

    items = []
    for raw in (getattr(args, "activity", None) or []):
        # 形式：活动ID[:名次][x份数]
        qty = 1
        if "x" in raw:
            raw, _, q = raw.rpartition("x")
            try:
                qty = max(1, int(q))
            except ValueError:
                qty = 1
        aid, _, achieve = raw.partition(":")
        items.append(BasketItem(activity_id=aid.strip(), achieve=achieve.strip(),
                                quantity=qty))
    return items
