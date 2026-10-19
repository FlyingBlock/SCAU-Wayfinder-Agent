"""设置 API：只把 HTTP 请求交给 settings 用例，再把结果序列化。

权限判断、校验、真实调用验证、落盘、登录编排都在
:mod:`wayfinder.settings.commands`；本层不 import 全局配置，也不拼 UI 文案。
"""
from __future__ import annotations

from ..server.http import Request, Response, json_response
from ..services import Services
from ..settings import commands


def _send(result: tuple[dict, int]) -> Response:
    body, status = result
    return json_response(body, status)


def llm_get(req: Request, svc: Services) -> Response:
    return json_response(commands.get_llm(req.local, svc))


def llm_save(req: Request, svc: Services) -> Response:
    return _send(commands.save_llm(req.body, svc, local=req.local))


def llm_test(req: Request, svc: Services) -> Response:
    return _send(commands.test_llm(req.body, svc, local=req.local))


def ocr_get(req: Request, svc: Services) -> Response:
    return json_response(commands.get_ocr(req.local, svc))


def ocr_save(req: Request, svc: Services) -> Response:
    return _send(commands.save_ocr(req.body, svc, local=req.local))


def ocr_test(req: Request, svc: Services) -> Response:
    return _send(commands.test_ocr(req.body, svc, local=req.local))


def ocr_clear(req: Request, svc: Services) -> Response:
    return _send(commands.clear_ocr(req.local, svc))


def auth_get(req: Request, svc: Services) -> Response:
    return json_response(commands.get_auth(req.local, svc))


def auth_save(req: Request, svc: Services) -> Response:
    return _send(commands.save_auth(req.body, svc, local=req.local))


def auth_captcha(req: Request, svc: Services) -> Response:
    return _send(commands.complete_captcha(req.body, svc, local=req.local))


def auth_clear(req: Request, svc: Services) -> Response:
    return _send(commands.clear_auth(req.local, svc))


def auth_logout(req: Request, svc: Services) -> Response:
    return _send(commands.logout_auth(req.local, svc))
