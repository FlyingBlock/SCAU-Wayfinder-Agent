"""计算器 API：静态数据、整份成绩单求值、课程目标反推、赛事名录联网对账。

计算全部发生在 `wayfinder.calc`；这里只做参数解析与 JSON 序列化。
"""
from __future__ import annotations

import json

from ..server.http import Request, Response, error_response, json_response
from ..services import Services


def catalog(req: Request, svc: Services) -> Response:
    return json_response(svc.calculator().catalog())


def evaluate(req: Request, svc: Services) -> Response:
    payload = req.body
    if not payload:
        return error_response("请求体不是合法 JSON", 400)
    return json_response(svc.calculator().evaluate_dict(payload).as_dict())


def target(req: Request, svc: Services) -> Response:
    try:
        goal = float(req.query.get("gpa") or 0)
    except ValueError:
        goal = 0.0
    scores = {}
    raw = req.query.get("scores") or ""
    if raw:
        try:
            scores = json.loads(raw)
        except json.JSONDecodeError:
            scores = {}
    return json_response(svc.calculator().target_for_course(
        req.query.get("major") or "", scores, goal))


def refresh_activities(req: Request, svc: Services) -> Response:
    """「活动篮」页的『🔄 刷新联网』。

    抓《学生竞赛奖励办法》名录页与竞赛通知栏目，和内置名录对账并缓存。
    抓取失败不是错误状态：返回 ok=False + 每个源的原因，页面继续用内置数据。
    """
    from ..integrations import competitions as competitions_integration

    try:
        timeout = int(req.body.get("timeout") or 12)
    except (TypeError, ValueError):
        timeout = 12
    timeout = max(4, min(timeout, 30))
    try:
        res = competitions_integration.refresh(timeout=timeout)
    except Exception as e:  # noqa: BLE001 - 联网失败要能看懂
        return json_response({"ok": False, "error": f"{type(e).__name__}: {e}"})
    # 问答卡片缓存了 Calculator().catalog()，名录刷新后必须失效。
    from ..qa import cards as qa_cards

    qa_cards.reset_cache()
    return json_response({
        "ok": bool(res.get("ok")),
        "fetched_at": res.get("fetched_at", ""),
        "catalog_ok": res.get("catalog_ok"),
        "stale_catalog": res.get("stale_catalog"),
        "counts": res.get("counts", {}),
        "diff": res.get("diff", {}),
        "sources": res.get("sources", []),
        "clues": len(res.get("clues", [])),
        "cache_path": res.get("cache_path", ""),
    })
