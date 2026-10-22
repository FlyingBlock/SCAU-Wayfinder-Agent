"""路由装配：把各领域 API 注册成一张路由表。

`app.build_application()` 调用 `build_router(services)`；新增接口时改这一处，
传输层与前端都不需要知道具体实现。
"""
from __future__ import annotations

from ..protocol.http import HandlerFn, Router
from ..services import Services
from . import calculator, chat, corpus, settings


def _bind(fn, services: Services) -> HandlerFn:
    return lambda req: fn(req, services)


def build_router(services: Services) -> Router:
    r = Router()

    # ---- 对话与检索 ----
    r.get("/api/status", _bind(corpus.status, services))
    r.get("/api/search", _bind(corpus.search, services))
    r.get("/api/article", _bind(corpus.article, services))
    r.get("/api/ask", _bind(chat.ask, services))

    # ---- 附件 ----
    r.get("/api/attachment", _bind(corpus.attachment, services))
    r.get("/api/attachment/file", _bind(corpus.attachment_file, services))

    # ---- 计算器 ----
    r.get("/api/calc/catalog", _bind(calculator.catalog, services))
    r.get("/api/calc/activities", _bind(calculator.activities, services))
    r.get("/api/calc/target", _bind(calculator.target, services))
    r.post("/api/calc/evaluate", _bind(calculator.evaluate, services))
    r.post("/api/calc/activities/refresh", _bind(calculator.refresh_activities, services))

    # ---- 设置：模型 ----
    r.get("/api/settings/llm", _bind(settings.llm_get, services))
    r.post("/api/settings/llm", _bind(settings.llm_save, services))
    r.post("/api/settings/llm/test", _bind(settings.llm_test, services))

    # ---- 设置：附件与 OCR ----
    r.get("/api/settings/ocr", _bind(settings.ocr_get, services))
    r.post("/api/settings/ocr", _bind(settings.ocr_save, services))
    r.post("/api/settings/ocr/test", _bind(settings.ocr_test, services))
    r.post("/api/settings/ocr/clear", _bind(settings.ocr_clear, services))

    # ---- 设置：登录 ----
    r.get("/api/settings/auth", _bind(settings.auth_get, services))
    r.post("/api/settings/auth", _bind(settings.auth_save, services))
    r.post("/api/settings/auth/captcha", _bind(settings.auth_captcha, services))
    r.post("/api/settings/auth/clear", _bind(settings.auth_clear, services))
    r.post("/api/settings/auth/logout", _bind(settings.auth_logout, services))

    return r
