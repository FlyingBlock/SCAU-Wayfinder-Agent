"""设置域底层：落盘、运行时生效，以及登录动作。

高层校验/验证/响应组装在 :mod:`wayfinder.settings.commands`；本层不碰 HTTP，
也不生成任何 HTML/JS。CLI 与 Web 设置面板复用同一组 commands，
不会出现「两个入口写出两种 .env」的问题。

三类配置的规矩一致：
  1. 留空表示沿用当前值（key 不回显，不能要求用户重填）；
  2. 先原地更新当前进程（免重启生效），再按需合并写入根目录 `.env`；
  3. 写盘失败只作为 warning 返回，不阻断「本次运行已生效」。
"""
from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass

from ..core.config import (
    AUTH_ENV_KEYS,
    ENV_FILE,
    LLM_ENV_KEYS,
    LLM_LEGACY_KEYS,
    LLM_PRESETS,
    OCR_ENV_KEYS,
    SETTINGS,
    AuthSettings,
    LLMSettings,
    OCRSettings,
    env_file_shadowed_keys,
    write_env_file,
)

# --------------------------------------------------------------------------- #
# 通用
# --------------------------------------------------------------------------- #


def mask_key(key: str) -> str:
    """key 只回显头尾，整条 key 不出现在响应里。"""
    if not key:
        return ""
    if len(key) <= 10:
        return key[:2] + "*" * max(len(key) - 2, 0)
    return f"{key[:6]}…{key[-4:]}"


def is_local(host: str) -> bool:
    """改配置只允许本机请求：`--host 0.0.0.0` 暴露到局域网时别让人改 key。"""
    return (host or "") in ("127.0.0.1", "::1", "localhost", "::ffff:127.0.0.1")


def ocr_configured(settings=None) -> bool:
    """OCR 是否已配置（状态栏用）。读取传入的 Settings，不碰模块全局。"""
    try:
        cfg = settings or SETTINGS
        return bool(cfg.ocr.configured)
    except Exception:  # noqa: BLE001 - 状态查询失败按未配置处理
        return False


# --------------------------------------------------------------------------- #
# 模型（LLM）
# --------------------------------------------------------------------------- #


def apply_llm_settings(*, api_key: str | None = None, base_url: str | None = None,
                       model: str | None = None, persist: bool = True,
                       env_file=None, settings=None) -> dict:
    """把一份 LLM 配置应用到指定 ``Settings``，并按需落盘到 .env。

    默认操作进程级 ``SETTINGS``；组装根可以传入请求级配置对象。LLM 对象是
    原地修改的，改完下一个请求就生效。
    返回 `{"settings", "applied", "wrote", "warning"}`，永不抛异常。
    """
    cfg = settings or SETTINGS
    llm = cfg.llm
    updates: dict[str, str] = {}

    if base_url:
        clean = base_url.strip().rstrip("/")
        if clean:
            llm.base_url = clean
            updates["LLM_BASE_URL"] = clean
    if model:
        clean = model.strip()
        if clean:
            llm.model = clean
            updates["LLM_MODEL"] = clean
    if api_key:
        clean = api_key.strip()
        if clean:
            llm.api_key = clean
            updates["LLM_API_KEY"] = clean

    for key, val in updates.items():
        os.environ[key] = val

    warning = ""
    wrote = False
    if updates and persist:
        try:
            write_env_file(updates, remove_keys=LLM_LEGACY_KEYS, env_file=env_file)
            wrote = True
        except OSError as e:
            warning = f"配置已在本次运行中生效，但写入 .env 失败：{e}"

    return {"settings": llm, "applied": sorted(updates), "wrote": wrote,
            "warning": warning}


def llm_state(writable: bool, extra: dict | None = None, *,
              settings=None, env_file=None) -> dict:
    """设置面板「🧠 模型」分页的完整状态（key 只回显掩码）。"""
    cfg = settings or SETTINGS
    path = env_file or ENV_FILE
    llm = cfg.llm
    state = {
        "base_url": llm.base_url,
        "model": llm.model,
        "configured": llm.configured,
        "api_key_set": bool(llm.api_key),
        "api_key_masked": mask_key(llm.api_key),
        "env_file": str(path),
        "env_file_exists": path.is_file(),
        "writable": writable,
        "shadowed": sorted(env_file_shadowed_keys(path) & set(LLM_ENV_KEYS + LLM_LEGACY_KEYS)),
        "presets": [dict(p) for p in LLM_PRESETS],
    }
    state.update(extra or {})
    return state


# --------------------------------------------------------------------------- #
# 附件与 OCR
# --------------------------------------------------------------------------- #


def apply_ocr_settings(*, provider: str | None = None, api_key: str | None = None,
                       secret_key: str | None = None, accurate: bool | None = None,
                       persist: bool = True, env_file=None, settings=None) -> dict:
    """把一份 OCR 配置应用到指定 ``Settings`` 并按需落盘。与 LLM 同构。"""
    cfg = settings or SETTINGS
    updates: dict[str, str] = {}
    if provider is not None and provider.strip():
        p = provider.strip().lower()
        if p in ("baidu", "none", "off", "disabled", ""):
            updates["OCR_PROVIDER"] = "none" if p in ("none", "off", "disabled", "") else p
    if api_key is not None and api_key.strip():
        updates["BAIDU_OCR_API_KEY"] = api_key.strip()
    if secret_key is not None and secret_key.strip():
        updates["BAIDU_OCR_SECRET_KEY"] = secret_key.strip()
    if accurate is not None:
        updates["OCR_ACCURATE"] = "1" if accurate else "0"

    for key, val in updates.items():
        os.environ[key] = val

    warning = ""
    wrote = False
    if updates and persist:
        try:
            write_env_file(updates, env_file=env_file)
            wrote = True
        except OSError as e:
            warning = f"OCR 配置已在本次运行中生效，但写入 .env 失败：{e}"

    cfg.ocr.__dict__.update(OCRSettings.from_env().__dict__)
    return {"settings": cfg.ocr, "applied": sorted(updates), "wrote": wrote,
            "warning": warning}


def clear_ocr_settings(*, persist: bool = True, env_file=None, settings=None) -> dict:
    """清掉 OCR 凭据（设置面板「清除」按钮用）。"""
    cfg = settings or SETTINGS
    for key in ("BAIDU_OCR_API_KEY", "BAIDU_OCR_SECRET_KEY"):
        os.environ.pop(key, None)
    os.environ["OCR_PROVIDER"] = "none"
    updates = {"OCR_PROVIDER": "none", "BAIDU_OCR_API_KEY": "", "BAIDU_OCR_SECRET_KEY": ""}
    warning = ""
    wrote = False
    if persist:
        try:
            write_env_file(updates, env_file=env_file)
            wrote = True
        except OSError as e:
            warning = f"清除只对本次运行生效，写入 .env 失败：{e}"
    cfg.ocr.__dict__.update(OCRSettings.from_env().__dict__)
    return {"settings": cfg.ocr, "applied": sorted(updates), "wrote": wrote,
            "warning": warning}


def ocr_state(writable: bool, extra: dict | None = None, *, settings=None) -> dict:
    """设置面板「🖼 附件与 OCR」分页的状态。"""
    from ..corpus.store import Store
    from ..documents import attachments as attach_mod
    from ..documents import docparse
    from ..documents import ocr as ocr_mod

    cfg = settings or SETTINGS
    ocr_cfg = cfg.ocr
    st = Store(cfg.crawl.db_path)
    try:
        stats = st.stats()
    except Exception:  # noqa: BLE001 - 统计失败不该阻断设置页
        stats = {}
    st.close()
    a = attach_mod.AttachmentSettings.from_env()
    dstat = attach_mod.dir_stats(a.dir)
    state = {
        "provider": ocr_cfg.provider,
        "accurate": ocr_cfg.accurate,
        "configured": ocr_cfg.configured,
        "label": ocr_cfg.describe() if ocr_cfg.configured else "",
        "api_key_set": bool(ocr_cfg.api_key),
        "api_key_masked": ocr_mod.mask(ocr_cfg.api_key),
        "secret_key_set": bool(ocr_cfg.secret_key),
        "secret_key_masked": ocr_mod.mask(ocr_cfg.secret_key),
        "endpoint": ocr_cfg.endpoint,
        "env_file": str(ENV_FILE),
        "writable": writable,
        "shadowed": sorted(env_file_shadowed_keys() & set(OCR_ENV_KEYS)),
        "attach_dir": dstat["dir"],
        "attach_stat": {"files": dstat["files"], "bytes": dstat["bytes"],
                        "human": dstat["human"]},
        "attachments": stats.get("attachments", 0),
        "attachments_with_text": stats.get("attachments_with_text", 0),
        "attach_enabled": a.enabled,
        "attach_max_mb": a.max_bytes_per_file // 1048576,
        "attach_max_files": a.max_files_per_article,
        "supported": len(docparse.supported_extensions()),
    }
    state.update(extra or {})
    return state


# --------------------------------------------------------------------------- #
# 登录（统一身份认证）
# --------------------------------------------------------------------------- #


def apply_auth_settings(*, auto_login: bool | None = None, ocr_captcha: bool | None = None,
                        captcha_rounds: int | None = None, service: str | None = None,
                        captcha_url: str | None = None, persist: bool = True,
                        env_file=None, settings=None) -> dict:
    """把一份「登录行为」配置应用到指定 ``Settings`` 并按需落盘 `.env`。

    这几个开关总是全量写：复选框的状态就是用户的意思，不像 key 那样存在
    「留空＝不改动」的语义。字符串项留空表示清掉。
    """
    cfg = settings or SETTINGS
    updates: dict[str, str] = {}
    if auto_login is not None:
        updates["AUTH_AUTO_LOGIN"] = "1" if auto_login else "0"
    if ocr_captcha is not None:
        updates["AUTH_OCR_CAPTCHA"] = "1" if ocr_captcha else "0"
    if captcha_rounds is not None:
        updates["AUTH_CAPTCHA_ROUNDS"] = str(max(1, min(int(captcha_rounds), 8)))
    if service is not None:
        updates["AUTH_SERVICE"] = service.strip()
    if captcha_url is not None:
        updates["AUTH_CAPTCHA_URL"] = captcha_url.strip()

    for key, val in updates.items():
        os.environ[key] = val

    warning = ""
    wrote = False
    if updates and persist:
        try:
            write_env_file(updates, env_file=env_file)
            wrote = True
        except OSError as e:
            warning = f"登录配置已在本次运行中生效，但写入 .env 失败：{e}"

    cfg.auth.__dict__.update(AuthSettings.from_env().__dict__)
    return {"settings": cfg.auth, "applied": sorted(updates), "wrote": wrote,
            "warning": warning}


def clear_auth_credentials() -> dict:
    """清掉保存的账号密码（`.auth/credentials.json`）。开关本身保留。"""
    from ..crawl import auth as auth_mod

    existed = auth_mod.forget_credentials()
    return {"removed": existed, "state": auth_mod.credentials_state()}


def auth_state(writable: bool, extra: dict | None = None, *, settings=None) -> dict:
    """设置面板「🔐 账号与登录」分页的状态（密码从不回显）。"""
    from ..crawl import auth as auth_mod

    cfg = settings or SETTINGS
    sess = auth_mod.AuthSession()
    st = cfg.auth
    state = {
        "credentials": auth_mod.credentials_state(),
        "session": auth_mod.session_state(sess, settings=st),
        "settings": {
            "auto_login": st.auto_login,
            "ocr_captcha": st.ocr_captcha,
            "captcha_rounds": st.captcha_rounds,
            "service": st.service or auth_mod.DEFAULT_SERVICE,
            "service_custom": bool(st.service),
            "captcha_url": st.captcha_url,
        },
        "ocr_configured": ocr_configured(cfg),
        "cas_base": auth_mod.CAS_BASE,
        "default_service": auth_mod.DEFAULT_SERVICE,
        "env_file": str(ENV_FILE),
        "writable": writable,
        "shadowed": sorted(env_file_shadowed_keys() & set(AUTH_ENV_KEYS)),
    }
    state.update(extra or {})
    return state


@dataclass
class PendingLogin:
    session: object
    form: object
    user: str
    created: float


class PendingLogins:
    """「OCR 认不出验证码 → 让人照着图填一次」的待续登录。

    验证码与 CAS 的 execution 字段都跟这一次 GET 的登录页绑定，所以人工填验证码
    时必须复用同一个 AuthSession 与同一份表单。这里只暂存会话、表单与账号，
    **不存密码**。5 分钟不用自动作废。
    """

    ttl = 300

    def __init__(self) -> None:
        self._items: dict[str, PendingLogin] = {}
        self._lock = threading.Lock()

    def stash(self, session, form, user: str) -> str:
        token = f"{int(time.time())}-{os.urandom(6).hex()}"
        now = time.time()
        with self._lock:
            expired = [k for k, v in self._items.items() if now - v.created > self.ttl]
            for k in expired:
                self._items.pop(k, None)
            self._items[token] = PendingLogin(session, form, user, now)
        return token

    def pop(self, token: str):
        if not token:
            return None
        with self._lock:
            entry = self._items.pop(token, None)
        if entry is None or time.time() - entry.created > self.ttl:
            return None
        return entry


PENDING_LOGINS = PendingLogins()


def login_payload(session, result) -> dict:
    """把一次登录结果整理成前端能直接用的 JSON。"""
    if not result.ok:
        return {"ok": False, "error": result.message,
                "captcha_seen": result.captcha_seen,
                "captcha_text": result.captcha_text,
                "captcha_rounds": result.captcha_rounds,
                "cookies": result.cookies,
                "hint": ("账号或密码不对？密码是统一身份认证的密码，不是教务系统单独设的。"
                         if not result.captcha_seen else
                         "验证码认错也有可能：可以换一张重试，或手填一次。")}
    try:
        session.save_cookies()
    except OSError:
        pass
    extra = ""
    if result.captcha_text:
        extra = f"（验证码 OCR 认成「{result.captcha_text}」，第 {result.captcha_rounds} 张）"
    return {"ok": True, "verified": True, "cookies": result.cookies,
            "final_url": result.final_url, "need_captcha": False,
            "message": f"登录成功{extra}，会话已存到 .auth/，crawl 会带着它抓"}


def do_login(user: str, password: str, service: str = "", *, settings=None) -> dict:
    """真登一次。OCR 认不出验证码时把图 + 待续 token 带回去让人填。"""
    from ..crawl import auth as auth_mod

    cfg = settings or SETTINGS
    sess = auth_mod.AuthSession()
    target = service or cfg.auth.service or auth_mod.DEFAULT_SERVICE
    form, captcha_text, cap_err = auth_mod.begin_login(sess, target)
    if not form.ok:
        return {"ok": False, "error": form.error or "打不开登录页",
                "hint": "检查网络，或确认 AUTH_SERVICE / 默认融合门户是不是可达。"}
    if any(b in ("slider", "sms", "2fa") for b in form.blockers):
        return {"ok": False,
                "error": "登录页要求 " + "、".join(form.blockers) + "，脚本过不去",
                "hint": "这种站点请改用浏览器 Cookie 导入（python -m wayfinder login --cookie）。"}
    if form.captcha_field and not captcha_text:
        token = PENDING_LOGINS.stash(sess, form, user)
        challenge = form.challenge
        return {"ok": False, "need_captcha": True, "token": token,
                "captcha_field": form.captcha_field,
                "captcha_image": challenge.data_url() if challenge else "",
                "error": "验证码 OCR 没认出来：" + (cap_err or "原因不明"),
                "hint": "照着下面的图填一次（填完直接登录），或换一张再试。"}
    res = sess.submit_login(form, user, password, captcha_text)
    return login_payload(sess, res)


def complete_captcha(token: str, text: str, password: str = "") -> dict:
    """OCR 认不出时，用人工填的验证码把这次登录做完。"""
    from ..crawl import auth as auth_mod

    entry = PENDING_LOGINS.pop(token)
    if entry is None:
        return {"ok": False,
                "error": "这次登录已经过期（超过 5 分钟或已被用掉），请重新发起登录"}
    password = password or auth_mod.load_credentials()[1]
    if not password:
        return {"ok": False, "error": "密码丢了，请重新填一次密码再登录"}
    res = entry.session.submit_login(entry.form, entry.user, password, text)
    out = login_payload(entry.session, res)
    if not out.get("ok") and res.captcha_seen:
        new_token = PENDING_LOGINS.stash(entry.session, entry.form, entry.user)
        out.update({"need_captcha": True, "token": new_token,
                    "captcha_image": res.captcha_data_url(),
                    "hint": "这个验证码不对，换一张再试。"})
    return out
