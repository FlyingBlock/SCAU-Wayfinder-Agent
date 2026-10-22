"""设置用例：模型 / OCR / 登录的校验、验证、落盘与状态组装。

API 层只负责把 ``Request`` 翻译成这里的函数调用，再把返回的 ``(dict, status)``
序列化；CLI 也可以复用同一组用例。这里不 import HTTP 类型，也不拼 HTML。
"""
from __future__ import annotations

import time

from ..core.config import ENV_FILE, LLMSettings
from ..crawl import auth as auth_mod
from ..documents import ocr as ocr_mod
from ..services import Services
from . import service

LOCAL_ONLY = "出于安全考虑，只有从本机（127.0.0.1）打开页面才能修改设置。"


def _forbidden(reason: str = LOCAL_ONLY) -> tuple[dict, int]:
    return {"ok": False, "writable": False, "error": reason}, 403


def _bad(message: str, **extra) -> tuple[dict, int]:
    payload = {"ok": False, "error": message}
    payload.update(extra)
    return payload, 400


# --------------------------------------------------------------------------- #
# 模型（LLM）
# --------------------------------------------------------------------------- #
def get_llm(local: bool, svc: Services) -> dict:
    return service.llm_state(local, settings=svc.settings)


def save_llm(payload: dict, svc: Services, *, local: bool) -> tuple[dict, int]:
    if not local:
        return _forbidden()
    if not payload:
        return _bad("请求体为空或不是合法 JSON")

    base_url = str(payload.get("base_url") or "").strip()
    model = str(payload.get("model") or "").strip()
    raw_key = payload.get("api_key")
    api_key = raw_key.strip() if isinstance(raw_key, str) else ""
    verify = bool(payload.get("verify", True))
    persist = bool(payload.get("persist", True))

    if base_url and not base_url.lower().startswith(("http://", "https://")):
        return _bad("base URL 要以 http:// 或 https:// 开头")

    current = svc.settings.llm
    effective_key = api_key or current.api_key
    effective_base = base_url.rstrip("/") or current.base_url
    effective_model = model or current.model
    base_changed = effective_base.rstrip("/") != current.base_url.rstrip("/")
    if verify and base_changed and not api_key:
        return _bad("修改 base URL 时必须同时提供该端点的 API key，"
                    "避免把当前 key 发到未验证的地址")

    verified, reply, ms = False, "", 0
    if verify:
        if not effective_key:
            return _bad("还没有 API key。本机的 Ollama / vLLM 也要随便填一个非空值。")
        t0 = time.time()
        ok, msg = svc.llm_client(LLMSettings(
            api_key=effective_key, base_url=effective_base,
            model=effective_model, timeout=60)).health()
        ms = int((time.time() - t0) * 1000)
        if not ok:
            return {
                "ok": False, "verified": False, "ms": ms,
                "hint": "检查 base URL / 模型名 / key / 网络；也可以关闭验证后直接保存。",
                "error": f"验证失败：{msg}",
            }, 400
        verified, reply = True, msg

    res = service.apply_llm_settings(
        api_key=api_key or None, base_url=base_url or None,
        model=model or None, persist=persist, settings=svc.settings,
    )
    parts = ["已更新 " + "、".join(res["applied"]) if res["applied"]
             else "三项都没填，配置未改动"]
    if verified:
        parts.append(f"真实调用验证通过（模型回复：{reply}）")
    parts.append(f"已写入 {ENV_FILE}" if res["wrote"]
                 else ("仅本次运行生效，未落盘" if res["applied"] else ""))
    return service.llm_state(local, {
        "ok": True, "verified": verified, "reply": reply, "ms": ms,
        "applied": res["applied"], "persisted": res["wrote"],
        "warning": res["warning"],
        "message": "；".join(p for p in parts if p),
    }, settings=svc.settings), 200


def test_llm(payload: dict, svc: Services, *, local: bool) -> tuple[dict, int]:
    """按表单里的值真实调一次模型，不落盘、不改当前配置。"""
    if not local:
        return _forbidden("出于安全考虑，只有从本机（127.0.0.1）打开页面才能测试连接。")
    current = svc.settings.llm
    base_url = (str(payload.get("base_url") or "").strip().rstrip("/")
                or current.base_url)
    model = str(payload.get("model") or "").strip() or current.model
    raw_key = payload.get("api_key")
    api_key = (raw_key.strip() if isinstance(raw_key, str) else "") or current.api_key
    if not api_key:
        return _bad("还没有 API key，请先填入")
    t0 = time.time()
    ok, msg = svc.llm_client(LLMSettings(
        api_key=api_key, base_url=base_url, model=model, timeout=60)).health()
    ms = int((time.time() - t0) * 1000)
    body = {"ok": ok, "ms": ms, "base_url": base_url, "model": model}
    if ok:
        body["reply"] = msg
        return body, 200
    body["error"] = msg
    return body, 400


# --------------------------------------------------------------------------- #
# 附件与 OCR
# --------------------------------------------------------------------------- #
def get_ocr(local: bool, svc: Services) -> dict:
    return service.ocr_state(local, settings=svc.settings)


def save_ocr(payload: dict, svc: Services, *, local: bool) -> tuple[dict, int]:
    if not local:
        return _forbidden()
    if not payload:
        return _bad("请求体为空或不是合法 JSON")
    provider = str(payload.get("provider") or "").strip().lower() or None
    raw_key = payload.get("api_key")
    raw_secret = payload.get("secret_key")
    api_key = raw_key.strip() if isinstance(raw_key, str) else ""
    secret = raw_secret.strip() if isinstance(raw_secret, str) else ""
    accurate = payload.get("accurate")
    accurate = bool(accurate) if accurate is not None else None
    verify = bool(payload.get("verify", True))
    persist = bool(payload.get("persist", True))

    ocr_cfg = svc.settings.ocr
    eff_key = api_key or ocr_cfg.api_key
    eff_secret = secret or ocr_cfg.secret_key
    eff_provider = provider or ocr_cfg.provider

    verified, reply = False, ""
    if verify and eff_provider == "baidu":
        if not (eff_key and eff_secret):
            return _bad("百度 OCR 需要 API Key 和 Secret Key 两个值都填。")
        probe = ocr_mod.OCRSettings(
            provider="baidu", api_key=eff_key, secret_key=eff_secret,
            accurate=(bool(accurate) if accurate is not None
                      else ocr_cfg.accurate))
        ok, msg = ocr_mod.health(probe)
        if not ok:
            return {
                "ok": False, "verified": False,
                "hint": "确认 AK/SK 来自同一个百度智能云应用，并且开通了「通用文字识别」；"
                        "也可以关闭验证后直接保存。",
                "error": msg,
            }, 400
        verified, reply = True, msg

    res = service.apply_ocr_settings(
        provider=provider, api_key=api_key or None,
        secret_key=secret or None, accurate=accurate, persist=persist,
        settings=svc.settings,
    )
    parts = ["已更新 " + "、".join(res["applied"]) if res["applied"]
             else "没有填写新值，配置未改动"]
    if verified:
        parts.append(reply)
    parts.append(f"已写入 {ENV_FILE}" if res["wrote"] else "仅本次运行生效，未落盘")
    return service.ocr_state(local, {
        "ok": True, "verified": verified, "reply": reply,
        "applied": res["applied"], "persisted": res["wrote"],
        "warning": res["warning"],
        "message": "；".join(p for p in parts if p),
    }, settings=svc.settings), 200


def test_ocr(payload: dict, svc: Services, *, local: bool) -> tuple[dict, int]:
    if not local:
        return _forbidden("出于安全考虑，只有从本机（127.0.0.1）打开页面才能测试。")
    raw_key = payload.get("api_key")
    raw_secret = payload.get("secret_key")
    ocr_cfg = svc.settings.ocr
    api_key = (raw_key.strip() if isinstance(raw_key, str) else "") or ocr_cfg.api_key
    secret = (raw_secret.strip() if isinstance(raw_secret, str) else "") or ocr_cfg.secret_key
    accurate = payload.get("accurate")
    probe = ocr_mod.OCRSettings(
        provider="baidu", api_key=api_key, secret_key=secret,
        accurate=(bool(accurate) if accurate is not None
                  else ocr_cfg.accurate))
    if not probe.configured:
        return _bad("还没填 API Key / Secret Key")
    ok, msg = ocr_mod.health(probe)
    return ({"ok": True, "message": msg} if ok else {"ok": False, "error": msg},
            200 if ok else 400)


def clear_ocr(local: bool, svc: Services) -> tuple[dict, int]:
    if not local:
        return _forbidden("只有从本机打开页面才能清除凭据。")
    res = service.clear_ocr_settings(settings=svc.settings)
    return service.ocr_state(local, {
        "ok": True, "warning": res["warning"], "message": "已清除 OCR 凭据",
    }, settings=svc.settings), 200


# --------------------------------------------------------------------------- #
# 登录
# --------------------------------------------------------------------------- #
def get_auth(local: bool, svc: Services) -> dict:
    return service.auth_state(local, settings=svc.settings)


def save_auth(payload: dict, svc: Services, *, local: bool) -> tuple[dict, int]:
    if not local:
        return _forbidden("出于安全考虑，只有从本机（127.0.0.1）打开页面才能填账号。")
    if not payload:
        return _bad("请求体为空或不是合法 JSON")
    username = str(payload.get("username") or "").strip()
    raw_pw = payload.get("password")
    password = raw_pw.strip() if isinstance(raw_pw, str) else ""
    save_password = bool(payload.get("save_password", True))
    verify = bool(payload.get("verify", True))
    persist = bool(payload.get("persist", True))
    auto_login = payload.get("auto_login")
    ocr_captcha = payload.get("ocr_captcha")
    rounds = payload.get("captcha_rounds")
    service_url = payload.get("service")
    captcha_url = payload.get("captcha_url")
    try:
        rounds_val = None if rounds in (None, "") else int(rounds)
    except (TypeError, ValueError):
        rounds_val = None

    res = service.apply_auth_settings(
        auto_login=None if auto_login is None else bool(auto_login),
        ocr_captcha=None if ocr_captcha is None else bool(ocr_captcha),
        captcha_rounds=rounds_val,
        service=None if service_url is None else str(service_url),
        captcha_url=None if captcha_url is None else str(captcha_url),
        persist=persist, settings=svc.settings,
    )

    stored_user, stored_pw = auth_mod.load_credentials()
    eff_user = username or stored_user
    eff_pw = password or stored_pw
    cred_saved = False
    if username and password and save_password:
        try:
            auth_mod.save_credentials(username, password)
            cred_saved = True
        except OSError as e:
            res["warning"] = (res["warning"] + "；" if res["warning"] else "") \
                + f"账号写盘失败：{e}"

    parts = []
    if res["applied"]:
        parts.append("已更新 " + "、".join(res["applied"]))
    if cred_saved:
        parts.append(f"账号 {auth_mod.mask_username(username)} 已保存到 "
                     f"{auth_mod.cred_file().name}")
    elif password and not save_password:
        parts.append("密码只在本次登录使用，未落盘")
    parts.append(f"已写入 {ENV_FILE}" if res["wrote"] else "仅本次运行生效，未落盘")

    base = {"ok": True, "applied": res["applied"], "persisted": res["wrote"],
            "credential_saved": cred_saved, "warning": res["warning"]}

    if not verify:
        return service.auth_state(local, {
            **base, "verified": False, "message": "；".join(p for p in parts if p),
        }), 200

    if not (eff_user and eff_pw):
        return service.auth_state(local, {
            **base, "verified": False,
            "error": "要真实登录一次得有账号和密码：填好后再保存，"
                     "或者关闭验证只保存设置。",
            "message": "；".join(p for p in parts if p) or "设置已保存",
        }), 200

    out = service.do_login(eff_user, eff_pw, svc.settings.auth.service,
                           settings=svc.settings)
    if out.get("need_captcha"):
        return service.auth_state(local, {**base, **out}), 200
    if not out.get("ok"):
        return service.auth_state(local, {
            **base, "verified": False, "error": out.get("error"),
            "hint": out.get("hint", ""),
            "message": "；".join(p for p in parts if p),
        }), 200
    parts.append(out.get("message", "登录成功"))
    return service.auth_state(local, {
        **base, "verified": True, **out,
        "message": "；".join(p for p in parts if p),
    }), 200


def complete_captcha(payload: dict, svc: Services, *, local: bool) -> tuple[dict, int]:
    """OCR 认不出时，用人工填的验证码把这次登录做完。"""
    if not local:
        return _forbidden("只有从本机打开页面才能登录。")
    token = str(payload.get("token") or "")
    text = str(payload.get("captcha") or "").strip()
    raw_pw = payload.get("password")
    password = raw_pw.strip() if isinstance(raw_pw, str) else ""
    if not text:
        return _bad("验证码不能为空")
    out = service.complete_captcha(token, text, password)
    if out.get("error") and not out.get("need_captcha") and not out.get("ok"):
        return service.auth_state(local, out), 400
    message = "验证码登录成功" if out.get("ok") else out.get("error", "登录失败")
    return service.auth_state(local, {**out, "message": message},
                              settings=svc.settings), (
        200 if out.get("ok") or out.get("need_captcha") else 400)


def clear_auth(local: bool, svc: Services) -> tuple[dict, int]:
    if not local:
        return _forbidden("只有从本机打开页面才能清除凭据。")
    res = service.clear_auth_credentials()
    message = ("已清除保存的账号密码（cookie 会话仍在，要一并清请使用退出登录）"
               if res["removed"] else "本来就没有保存账号")
    return service.auth_state(local, {
        "ok": True, "removed": res["removed"], "message": message,
    }, settings=svc.settings), 200


def logout_auth(local: bool, svc: Services) -> tuple[dict, int]:
    if not local:
        return _forbidden("只有从本机打开页面才能清除会话。")
    sess = auth_mod.AuthSession()
    n = sess.alive()
    sess.clear()
    return service.auth_state(local, {
        "ok": True, "message": f"已清除会话（{n} 个 cookie），账号密码保留",
    }, settings=svc.settings), 200
