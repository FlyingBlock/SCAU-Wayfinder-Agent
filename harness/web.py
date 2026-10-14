"""简陋但够用的 Web 界面：标准库 http.server + SSE 流式输出。

为什么不用 FastAPI：本机沙箱装不了包（指南 §3.4），而 http.server 足够
支撑单用户使用，且零依赖。前端是内嵌的 HTML 页面，无构建步骤。

整个界面是**一份** HTML（`harness.app.build_page()`）：左侧栏切换视图，
对话页、绩点计算器及其四个子页、数据口径说明都在同一页里，切换不刷新、不丢状态。

路由：
  GET  /                    单页应用（默认停在「主页对话」）
  GET  /calc                同上，deep-link 到计算器（① 我的成绩）
  GET  /calc/<子页>         同上，子页 = scores|goals|acts|rules
  GET  /calc-docs           同上，deep-link 到「④ 计算口径」
  GET  /api/status          库状态 + LLM/公网搜索配置灯
  GET  /api/search?q=&k=    纯检索（不花 token）
  GET  /api/article?id=     读某篇正文
  GET  /api/ask?q=&rounds=  提问，SSE 流式返回 trace + answer
  GET  /api/settings/llm    读当前 LLM 配置（key 只回显掩码）
  POST /api/settings/llm    保存 base URL / 模型名 / API key（可先真实调用验证）
  POST /api/settings/llm/test 只测试连通性，不保存
  GET  /api/settings/ocr    读 OCR / 附件配置（key 只回显掩码）
  POST /api/settings/ocr    保存 OCR 配置（可先真实调用验证）
  GET  /api/settings/auth   读登录配置：会话状态 + 账号（打码）+ 自动登录开关
  POST /api/settings/auth   保存账号密码与自动登录开关，并真的登一次验证
  POST /api/settings/auth/captcha  OCR 认不出验证码时，用人工填的验证码续登一次
  POST /api/settings/auth/clear    清除保存的账号密码
  POST /api/settings/auth/logout   清掉当前会话 cookie（凭据保留）
  GET  /api/calc/catalog    计算器全部静态数据（专业/课程/规则/门槛/活动）
  POST /api/calc/evaluate   提交成绩单 + 活动篮，返回完整计算结果
  GET  /api/calc/target     反推：达到目标绩点时剩余课程需要的分数
"""
from __future__ import annotations

import json
import os
import socket
import sys
import threading
import time
import urllib.parse
import webbrowser
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .agent import Agent
from .app import build_page
from .calcpages import CALC_DOCS_PAGE, CALC_PAGE          # noqa: F401  兼容旧引用
from .config import (
    AUTH_ENV_KEYS,
    ENV_FILE,
    LLM_ENV_KEYS,
    LLM_LEGACY_KEYS,
    LLM_PRESETS,
    OCR_ENV_KEYS,
    SETTINGS,
    LLMSettings,
    SearchSettings,
    apply_llm_settings,
    env_file_shadowed_keys,
)
from .llm import LLM
from .store import Store
from .websearch import WebSearcher


@lru_cache(maxsize=1)
def page_html() -> str:
    """单页应用 HTML（拼一次就缓存，页面几万字，不必每次请求重拼）。"""
    return build_page()


# --------------------------------------------------------------------------- #
# 「OCR 认不出验证码 → 让人照着图填一次」的待续登录。
#
# 验证码和 CAS 的 execution 字段都是**跟这一次 GET 的登录页绑定的**（换一次请求
# 就换一张图），所以人工填验证码时必须复用同一个 AuthSession 与同一份表单。
# 这里只暂存 (session, form, 账号) —— **不存密码**，密码由前端在续登时再发一次
# （或回退到 .auth/credentials.json 里那份）。5 分钟不用就自动作废。
# --------------------------------------------------------------------------- #
_PENDING_LOGINS: dict[str, tuple] = {}
_PENDING_LOCK = threading.Lock()
_PENDING_TTL = 300


def _stash_login(sess, form, user: str) -> str:
    token = f"{int(time.time())}-{os.urandom(6).hex()}"
    now = time.time()
    with _PENDING_LOCK:
        for k in [k for k, v in _PENDING_LOGINS.items() if now - v[3] > _PENDING_TTL]:
            _PENDING_LOGINS.pop(k, None)
        _PENDING_LOGINS[token] = (sess, form, user, now)
    return token


def _pop_login(token: str):
    if not token:
        return None
    with _PENDING_LOCK:
        entry = _PENDING_LOGINS.pop(token, None)
    if entry is None:
        return None
    if time.time() - entry[3] > _PENDING_TTL:
        return None
    return entry[:3]


def _ocr_on() -> bool:
    """OCR 是否已配置（状态栏用）。单独包一层是为了不把 ocr 模块拖进导入期。"""
    try:
        from . import ocr as ocr_mod

        return ocr_mod.SETTINGS.configured
    except Exception:
        return False


class Handler(BaseHTTPRequestHandler):
    server_version = "SCAUHarness/0.1"
    protocol_version = "HTTP/1.1"

    # ------------------------------------------------------------------ #
    def log_message(self, fmt, *args):        # 安静一点，只保留错误
        if args and str(args[1] if len(args) > 1 else "").startswith(("4", "5")):
            sys.stderr.write("[web] " + fmt % args + "\n")

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code: int = 200) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8")

    def _query(self) -> dict:
        q = urllib.parse.urlsplit(self.path).query
        return {k: v[0] for k, v in urllib.parse.parse_qs(q).items()}

    def _read_body(self) -> dict:
        """读 POST body 并解析成 dict。"""
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8", "ignore") or "{}")
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    # ------------------------------------------------------------------ #
    def do_GET(self) -> None:                 # noqa: N802
        path = urllib.parse.urlsplit(self.path).path
        try:
            if path in ("/", "/index.html", "/calc", "/calc/", "/calc-docs",
                        "/calc-docs/") or path.startswith("/calc/"):
                # 单页应用：/calc 与 /calc-docs 只是同一份页面的不同 hash 入口，
                # 由前端 hash 路由决定落在哪个视图（老书签因此继续有效）。
                self._send(200, page_html().encode("utf-8"), "text/html; charset=utf-8")
            elif path == "/api/status":
                self._status()
            elif path == "/api/search":
                self._search()
            elif path == "/api/article":
                self._article()
            elif path == "/api/ask":
                self._ask()
            elif path == "/api/settings/llm":
                self._settings_get()
            elif path == "/api/settings/ocr":
                self._ocr_settings_get()
            elif path == "/api/settings/auth":
                self._auth_settings_get()
            elif path == "/api/attachment":
                self._attachment()
            elif path == "/api/attachment/file":
                self._attachment_file()
            elif path == "/api/calc/catalog":
                self._calc_catalog()
            elif path == "/api/calc/target":
                self._calc_target()
            elif path == "/favicon.ico":
                self._send(204, b"", "image/x-icon")
            else:
                self._json({"error": "not found"}, 404)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            try:
                self._json({"error": f"{type(e).__name__}: {e}"}, 500)
            except Exception:
                pass

    def do_POST(self) -> None:                # noqa: N802
        path = urllib.parse.urlsplit(self.path).path
        try:
            if path == "/api/calc/evaluate":
                self._calc_evaluate()
            elif path == "/api/calc/activities/refresh":
                self._calc_activities_refresh()
            elif path == "/api/settings/llm":
                self._settings_save()
            elif path == "/api/settings/llm/test":
                self._settings_test()
            elif path == "/api/settings/ocr":
                self._ocr_settings_save()
            elif path == "/api/settings/ocr/test":
                self._ocr_settings_test()
            elif path == "/api/settings/ocr/clear":
                self._ocr_settings_clear()
            elif path == "/api/settings/auth":
                self._auth_settings_save()
            elif path == "/api/settings/auth/captcha":
                self._auth_settings_captcha()
            elif path == "/api/settings/auth/clear":
                self._auth_settings_clear()
            elif path == "/api/settings/auth/logout":
                self._auth_settings_logout()
            else:
                self._json({"error": "not found"}, 404)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            try:
                self._json({"error": f"{type(e).__name__}: {e}"}, 500)
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    def _status(self) -> None:
        st = Store(SETTINGS.crawl.db_path)
        s = st.stats()
        last = ""
        try:
            row = st.conn.execute("SELECT ts FROM crawl_log ORDER BY id DESC LIMIT 1").fetchone()
            last = row["ts"] if row else ""
        except Exception:
            pass
        st.close()
        self._json({
            "articles": s["articles"], "sites": s["sites"], "with_date": s["with_date"],
            "llm_configured": SETTINGS.llm.configured, "llm_model": SETTINGS.llm.model,
            "llm_base_url": SETTINGS.llm.base_url,
            "web_search": SearchSettings.from_env().provider, "last_crawl": last,
            "db": str(SETTINGS.crawl.db_path),
            "attachments": s.get("attachments", 0),
            "attachments_with_text": s.get("attachments_with_text", 0),
            "ocr_configured": _ocr_on(),
        })

    def _search(self) -> None:
        q = self._query()
        query = (q.get("q") or "").strip()
        k = min(int(q.get("k") or 12), 50)
        st = Store(SETTINGS.crawl.db_path)
        total = st.count_articles()
        hits = st.search(query, top_k=k, topic=q.get("topic") or None,
                         since=q.get("since") or None) if query else []
        st.close()
        self._json({
            "total": total,
            "hits": [
                {"id": h.article_id, "title": h.title, "url": h.url, "pub_date": h.pub_date,
                 "snippet": h.snippet, "college": h.college, "site_name": h.site_name,
                 "topic": h.topic, "score": round(h.score, 3)}
                for h in hits
            ],
        })

    def _article(self) -> None:
        q = self._query()
        st = Store(SETTINGS.crawl.db_path)
        art = st.get_article(int(q.get("id") or 0), max_chars=20000)
        st.close()
        self._json(art or {"error": "not found"})

    # ------------------------------------------------------------------ #
    # LLM 设置（侧栏底部「⚙️ 设置」的第一个分页：🧠 模型）
    #
    # 界面上填的三项就是 .env 里的 LLM_BASE_URL / LLM_MODEL / LLM_API_KEY；
    # 保存时既落盘（下次启动仍生效）又原地更新 SETTINGS.llm（不用重启服务）。
    # ------------------------------------------------------------------ #
    @staticmethod
    def _mask_key(key: str) -> str:
        """key 只回显头尾，整条 key 不出现在响应里。"""
        if not key:
            return ""
        if len(key) <= 10:
            return key[:2] + "*" * max(len(key) - 2, 0)
        return f"{key[:6]}…{key[-4:]}"

    def _is_local(self) -> bool:
        """改配置只允许本机请求：`--host 0.0.0.0` 暴露到局域网时别让人改 key。"""
        try:
            host = (self.client_address or ("",))[0]
        except Exception:
            host = ""
        return host in ("127.0.0.1", "::1", "localhost", "::ffff:127.0.0.1")

    def _llm_state(self, extra: dict | None = None) -> dict:
        llm = SETTINGS.llm
        state = {
            "base_url": llm.base_url,
            "model": llm.model,
            "configured": llm.configured,
            "api_key_set": bool(llm.api_key),
            "api_key_masked": self._mask_key(llm.api_key),
            "env_file": str(ENV_FILE),
            "env_file_exists": ENV_FILE.is_file(),
            "writable": self._is_local(),
            "shadowed": sorted(env_file_shadowed_keys() & set(LLM_ENV_KEYS + LLM_LEGACY_KEYS)),
            "presets": [dict(p) for p in LLM_PRESETS],
        }
        state.update(extra or {})
        return state

    def _settings_get(self) -> None:
        self._json(self._llm_state())

    def _settings_save(self) -> None:
        if not self._is_local():
            self._json({"ok": False, "writable": False,
                        "error": "出于安全考虑，只有从本机（127.0.0.1）打开页面才能改设置。"}, 403)
            return
        payload = self._read_body()
        if not payload:
            self._json({"ok": False, "error": "请求体为空或不是合法 JSON"}, 400)
            return

        base_url = str(payload.get("base_url") or "").strip()
        model = str(payload.get("model") or "").strip()
        raw_key = payload.get("api_key")
        api_key = raw_key.strip() if isinstance(raw_key, str) else ""
        verify = bool(payload.get("verify", True))
        persist = bool(payload.get("persist", True))

        if base_url and not base_url.lower().startswith(("http://", "https://")):
            self._json({"ok": False, "error": "base URL 要以 http:// 或 https:// 开头"}, 400)
            return

        # 留空的项表示「沿用现在的值」（key 不回显，所以不能要求重填）
        effective_key = api_key or SETTINGS.llm.api_key
        effective_base = base_url.rstrip("/") or SETTINGS.llm.base_url
        effective_model = model or SETTINGS.llm.model

        verified, reply, ms = False, "", 0
        if verify:
            if not effective_key:
                self._json({"ok": False, "error": "还没有 API key。本机的 Ollama / vLLM "
                                                  "也要随便填一个非空值。"}, 400)
                return
            t0 = time.time()
            ok, msg = LLM(LLMSettings(api_key=effective_key, base_url=effective_base,
                                      model=effective_model, timeout=60)).health()
            ms = int((time.time() - t0) * 1000)
            if not ok:
                self._json({"ok": False, "verified": False, "ms": ms,
                            "hint": "可以点「跳过验证直接保存」，或检查 base URL / 模型名 / key / 网络。",
                            "error": f"验证失败：{msg}"}, 400)
                return
            verified, reply = True, msg

        res = apply_llm_settings(api_key=api_key or None, base_url=base_url or None,
                                 model=model or None, persist=persist)
        parts = ["已更新 " + "、".join(res["applied"]) if res["applied"]
                 else "三项都没填，配置未改动"]
        if verified:
            parts.append(f"真实调用验证通过（模型回复：{reply}）")
        parts.append(f"已写入 {ENV_FILE}" if res["wrote"]
                     else ("仅本次运行生效，未落盘" if res["applied"] else ""))
        self._json(self._llm_state({
            "ok": True, "verified": verified, "reply": reply, "ms": ms,
            "applied": res["applied"], "persisted": res["wrote"],
            "warning": res["warning"],
            "message": "；".join(p for p in parts if p),
        }))

    def _settings_test(self) -> None:
        """按表单里的值真实调一次模型，不落盘、不改当前配置。"""
        if not self._is_local():
            self._json({"ok": False,
                        "error": "出于安全考虑，只有从本机（127.0.0.1）打开页面才能测试连接。"}, 403)
            return
        payload = self._read_body()
        base_url = str(payload.get("base_url") or "").strip().rstrip("/") or SETTINGS.llm.base_url
        model = str(payload.get("model") or "").strip() or SETTINGS.llm.model
        raw_key = payload.get("api_key")
        api_key = (raw_key.strip() if isinstance(raw_key, str) else "") or SETTINGS.llm.api_key
        if not api_key:
            self._json({"ok": False, "error": "还没有 API key，请先填入"}, 400)
            return
        t0 = time.time()
        ok, msg = LLM(LLMSettings(api_key=api_key, base_url=base_url, model=model,
                                  timeout=60)).health()
        ms = int((time.time() - t0) * 1000)
        if ok:
            self._json({"ok": True, "reply": msg, "ms": ms, "base_url": base_url,
                        "model": model})
        else:
            self._json({"ok": False, "error": msg, "ms": ms, "base_url": base_url,
                        "model": model}, 400)

    # ------------------------------------------------------------------ #
    # 附件与 OCR 设置（侧栏「⚙️ 设置」的第二个分页：🖼 附件与 OCR）
    #
    # 与 LLM 设置同一套规矩：key 只回显掩码、只允许本机改、保存即落盘并原地生效。
    # 区别是 OCR 的「验证」会真的发一张测试图（消耗一次免费额度，所以是可选动作）。
    # ------------------------------------------------------------------ #
    def _ocr_state(self, extra: dict | None = None) -> dict:
        from . import attachments as attach_mod
        from . import ocr as ocr_mod

        st = Store(SETTINGS.crawl.db_path)
        try:
            stats = st.stats()
        except Exception:
            stats = {}
        st.close()
        a = attach_mod.AttachmentSettings.from_env()
        dstat = attach_mod.dir_stats(a.dir)
        state = {
            "provider": ocr_mod.SETTINGS.provider,
            "accurate": ocr_mod.SETTINGS.accurate,
            "configured": ocr_mod.SETTINGS.configured,
            "label": ocr_mod.SETTINGS.describe() if ocr_mod.SETTINGS.configured else "",
            "api_key_set": bool(ocr_mod.SETTINGS.api_key),
            "api_key_masked": ocr_mod.mask(ocr_mod.SETTINGS.api_key),
            "secret_key_set": bool(ocr_mod.SETTINGS.secret_key),
            "secret_key_masked": ocr_mod.mask(ocr_mod.SETTINGS.secret_key),
            "endpoint": ocr_mod.SETTINGS.endpoint,
            "env_file": str(ENV_FILE),
            "writable": self._is_local(),
            "shadowed": sorted(env_file_shadowed_keys() & set(OCR_ENV_KEYS)),
            "attach_dir": dstat["dir"],
            "attach_stat": {"files": dstat["files"], "bytes": dstat["bytes"],
                            "human": dstat["human"]},
            "attachments": stats.get("attachments", 0),
            "attachments_with_text": stats.get("attachments_with_text", 0),
            "attach_enabled": a.enabled,
            "attach_max_mb": a.max_bytes_per_file // 1048576,
            "attach_max_files": a.max_files_per_article,
            "supported": len(__import__("harness.docparse", fromlist=["x"])
                             .supported_extensions()),
        }
        state.update(extra or {})
        return state

    def _ocr_settings_get(self) -> None:
        self._json(self._ocr_state())

    def _ocr_settings_save(self) -> None:
        if not self._is_local():
            self._json({"ok": False, "writable": False,
                        "error": "出于安全考虑，只有从本机（127.0.0.1）打开页面才能改设置。"}, 403)
            return
        from . import ocr as ocr_mod
        from .config import apply_ocr_settings

        payload = self._read_body()
        if not payload:
            self._json({"ok": False, "error": "请求体为空或不是合法 JSON"}, 400)
            return
        provider = str(payload.get("provider") or "").strip().lower() or None
        api_key = payload.get("api_key")
        secret = payload.get("secret_key")
        api_key = api_key.strip() if isinstance(api_key, str) else ""
        secret = secret.strip() if isinstance(secret, str) else ""
        accurate = payload.get("accurate")
        accurate = bool(accurate) if accurate is not None else None
        verify = bool(payload.get("verify", True))
        persist = bool(payload.get("persist", True))

        eff_key = api_key or ocr_mod.SETTINGS.api_key
        eff_secret = secret or ocr_mod.SETTINGS.secret_key
        eff_provider = provider or ocr_mod.SETTINGS.provider

        if verify and eff_provider == "baidu":
            if not (eff_key and eff_secret):
                self._json({"ok": False,
                            "error": "百度 OCR 需要 API Key 和 Secret Key 两个值都填。"}, 400)
                return
            probe = ocr_mod.OCRSettings(provider="baidu", api_key=eff_key,
                                        secret_key=eff_secret,
                                        accurate=bool(accurate) if accurate is not None
                                        else ocr_mod.SETTINGS.accurate)
            ok, msg = ocr_mod.health(probe)
            if not ok:
                self._json({"ok": False, "verified": False,
                            "hint": "确认这对 AK/SK 来自同一个百度智能云应用，"
                                    "并且开通了「通用文字识别」。也可以不勾选验证直接保存。",
                            "error": msg}, 400)
                return
            verified, reply = True, msg
        else:
            verified, reply = False, ""

        res = apply_ocr_settings(provider=provider, api_key=api_key or None,
                                 secret_key=secret or None, accurate=accurate,
                                 persist=persist)
        parts = []
        if res["applied"]:
            parts.append("已更新 " + "、".join(res["applied"]))
        else:
            parts.append("没有填写新值，配置未改动")
        if verified:
            parts.append(reply)
        parts.append(f"已写入 {ENV_FILE}" if res["wrote"] else "仅本次运行生效，未落盘")
        self._json(self._ocr_state({
            "ok": True, "verified": verified, "reply": reply,
            "applied": res["applied"], "persisted": res["wrote"],
            "warning": res["warning"],
            "message": "；".join(p for p in parts if p),
        }))

    def _ocr_settings_test(self) -> None:
        if not self._is_local():
            self._json({"ok": False,
                        "error": "出于安全考虑，只有从本机（127.0.0.1）打开页面才能测试。"}, 403)
            return
        from . import ocr as ocr_mod

        payload = self._read_body()
        api_key = payload.get("api_key")
        secret = payload.get("secret_key")
        api_key = (api_key.strip() if isinstance(api_key, str) else "") or ocr_mod.SETTINGS.api_key
        secret = (secret.strip() if isinstance(secret, str) else "") or ocr_mod.SETTINGS.secret_key
        accurate = payload.get("accurate")
        probe = ocr_mod.OCRSettings(
            provider="baidu", api_key=api_key, secret_key=secret,
            accurate=bool(accurate) if accurate is not None else ocr_mod.SETTINGS.accurate)
        if not probe.configured:
            self._json({"ok": False, "error": "还没填 API Key / Secret Key"}, 400)
            return
        ok, msg = ocr_mod.health(probe)
        self._json({"ok": ok, "message": msg} if ok else {"ok": False, "error": msg},
                   200 if ok else 400)

    def _ocr_settings_clear(self) -> None:
        if not self._is_local():
            self._json({"ok": False, "error": "只有从本机打开页面才能清除凭据。"}, 403)
            return
        from .config import clear_ocr_settings

        res = clear_ocr_settings()
        self._json(self._ocr_state({"ok": True, "warning": res["warning"],
                                    "message": "已清除 OCR 凭据"}))

    # ------------------------------------------------------------------ #
    # 登录墙设置（侧栏「⚙️ 设置」的第三个分页：🔐 账号与登录）
    #
    # 和 LLM / OCR 两页同一套规矩：只允许本机改、密码只回显掩码。
    # 区别有两点：
    #   ① 账号密码**不写 .env**，只落 `.auth/credentials.json`（已 gitignore、
    #      权限收紧到当前用户）；.env 里只放「自动登录 / 验证码 OCR」这些开关。
    #   ② 保存时默认**真的登一次**（要走学校 CAS），所以"测试"与"保存"是同一件事；
    #      OCR 认不出验证码时会把图带回来，让用户在弹窗里手填一次。
    # ------------------------------------------------------------------ #
    def _auth_state(self, extra: dict | None = None) -> dict:
        from . import auth as auth_mod

        sess = auth_mod.AuthSession()
        st = auth_mod.SETTINGS
        state = {
            "credentials": auth_mod.credentials_state(),
            "session": auth_mod.session_state(sess),
            "settings": {
                "auto_login": st.auto_login,
                "ocr_captcha": st.ocr_captcha,
                "captcha_rounds": st.captcha_rounds,
                "service": st.service or auth_mod.DEFAULT_SERVICE,
                "service_custom": bool(st.service),
                "captcha_url": st.captcha_url,
            },
            "ocr_configured": _ocr_on(),
            "cas_base": auth_mod.CAS_BASE,
            "default_service": auth_mod.DEFAULT_SERVICE,
            "env_file": str(ENV_FILE),
            "writable": self._is_local(),
            "shadowed": sorted(env_file_shadowed_keys() & set(AUTH_ENV_KEYS)),
        }
        state.update(extra or {})
        return state

    def _auth_settings_get(self) -> None:
        self._json(self._auth_state())

    def _auth_settings_save(self) -> None:
        if not self._is_local():
            self._json({"ok": False, "writable": False,
                        "error": "出于安全考虑，只有从本机（127.0.0.1）打开页面才能填账号。"}, 403)
            return
        from . import auth as auth_mod
        from .config import apply_auth_settings

        payload = self._read_body()
        if not payload:
            self._json({"ok": False, "error": "请求体为空或不是合法 JSON"}, 400)
            return
        username = str(payload.get("username") or "").strip()
        raw_pw = payload.get("password")
        password = raw_pw.strip() if isinstance(raw_pw, str) else ""
        save_password = bool(payload.get("save_password", True))
        verify = bool(payload.get("verify", True))
        persist = bool(payload.get("persist", True))
        auto_login = payload.get("auto_login")
        ocr_captcha = payload.get("ocr_captcha")
        rounds = payload.get("captcha_rounds")
        service = payload.get("service")
        captcha_url = payload.get("captcha_url")
        try:
            rounds_val = None if rounds in (None, "") else int(rounds)
        except (TypeError, ValueError):
            rounds_val = None

        res = apply_auth_settings(
            auto_login=None if auto_login is None else bool(auto_login),
            ocr_captcha=None if ocr_captcha is None else bool(ocr_captcha),
            captcha_rounds=rounds_val,
            service=None if service is None else str(service),
            captcha_url=None if captcha_url is None else str(captcha_url),
            persist=persist,
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
            self._json(self._auth_state({**base, "verified": False,
                                         "message": "；".join(p for p in parts if p)}))
            return

        if not (eff_user and eff_pw):
            self._json(self._auth_state({
                **base, "verified": False,
                "error": "要真登一次得有账号和密码：填好再点「保存并登录」，"
                         "或者取消勾选验证只保存设置。",
                "message": "；".join(p for p in parts if p) or "设置已保存"}), 200)
            return

        out = self._do_login(eff_user, eff_pw, auth_mod.SETTINGS.service)
        if out.get("need_captcha"):
            self._json(self._auth_state({**base, **out}), 200)
            return
        if not out.get("ok"):
            self._json(self._auth_state({
                **base, "verified": False, "error": out.get("error"),
                "hint": out.get("hint", ""),
                "message": "；".join(p for p in parts if p)}), 200)
            return
        parts.append(out.get("message", "登录成功"))
        self._json(self._auth_state({**base, "verified": True, **out,
                                     "message": "；".join(p for p in parts if p)}))

    def _do_login(self, user: str, pw: str, service: str = "") -> dict:
        """真登一次。OCR 认不出验证码时把图 + 待续 token 带回去让人填。"""
        from . import auth as auth_mod

        sess = auth_mod.AuthSession()
        target = service or auth_mod.SETTINGS.service or auth_mod.DEFAULT_SERVICE
        form, captcha_text, cap_err = auth_mod.begin_login(sess, target)
        if not form.ok:
            return {"ok": False, "error": form.error or "打不开登录页",
                    "hint": "检查网络，或确认 AUTH_SERVICE / 默认融合门户是不是可达。"}
        if any(b in ("slider", "sms", "2fa") for b in form.blockers):
            return {"ok": False,
                    "error": "登录页要求 " + "、".join(form.blockers) + "，脚本过不去",
                    "hint": "这种站点请改用浏览器 Cookie 导入（python -m harness.cli login --cookie）。"}
        if form.captcha_field and not captcha_text:
            token = _stash_login(sess, form, user)
            ch = form.challenge
            return {"ok": False, "need_captcha": True, "token": token,
                    "captcha_field": form.captcha_field,
                    "captcha_image": ch.data_url() if ch else "",
                    "error": "验证码 OCR 没认出来：" + (cap_err or "原因不明"),
                    "hint": "照着下面的图填一次（填完直接登录），或换一张再试。"}
        res = sess.submit_login(form, user, pw, captcha_text)
        return self._login_payload(sess, res)

    @staticmethod
    def _login_payload(sess, res) -> dict:
        if not res.ok:
            return {"ok": False, "error": res.message,
                    "captcha_seen": res.captcha_seen,
                    "captcha_text": res.captcha_text,
                    "captcha_rounds": res.captcha_rounds,
                    "cookies": res.cookies,
                    "hint": ("账号或密码不对？密码是统一身份认证的密码，不是教务系统单独设的。"
                             if not res.captcha_seen else
                             "验证码认错也有可能：可以换一张重试，或手填一次。")}
        try:
            sess.save_cookies()
        except OSError:
            pass
        extra = ""
        if res.captcha_text:
            extra = f"（验证码 OCR 认成「{res.captcha_text}」，第 {res.captcha_rounds} 张）"
        return {"ok": True, "verified": True, "cookies": res.cookies,
                "final_url": res.final_url, "need_captcha": False,
                "message": f"登录成功{extra}，会话已存到 .auth/，crawl 会带着它抓"}

    def _auth_settings_captcha(self) -> None:
        """OCR 认不出时，用人工填的验证码把这次登录做完。"""
        if not self._is_local():
            self._json({"ok": False, "error": "只有从本机打开页面才能登录。"}, 403)
            return
        from . import auth as auth_mod

        payload = self._read_body()
        token = str(payload.get("token") or "")
        text = str(payload.get("captcha") or "").strip()
        raw_pw = payload.get("password")
        password = raw_pw.strip() if isinstance(raw_pw, str) else ""
        if not text:
            self._json({"ok": False, "error": "验证码不能为空"}, 400)
            return
        entry = _pop_login(token)
        if entry is None:
            self._json({"ok": False,
                        "error": "这次登录已经过期（超过 5 分钟或已被用掉），请重新点「保存并登录」"},
                       400)
            return
        sess, form, user = entry
        pw = password or auth_mod.load_credentials()[1]
        if not pw:
            self._json({"ok": False, "error": "密码丢了，请重新填一次密码再登录"}, 400)
            return
        res = sess.submit_login(form, user, pw, text)
        out = self._login_payload(sess, res)
        if not out.get("ok") and res.captcha_seen:
            # 手填的也不对：再给一张新的验证码，别让用户重新走一遍全流程
            new_token = _stash_login(sess, form, user)
            out.update({"need_captcha": True, "token": new_token,
                        "captcha_image": res.captcha_data_url(),
                        "hint": "这个验证码不对，换一张再试。"})
        message = "验证码登录成功" if out.get("ok") else out.get("error", "登录失败")
        self._json(self._auth_state({**out, "message": message}),
                   200 if out.get("ok") or out.get("need_captcha") else 400)

    def _auth_settings_clear(self) -> None:
        if not self._is_local():
            self._json({"ok": False, "error": "只有从本机打开页面才能清除凭据。"}, 403)
            return
        from . import auth as auth_mod
        from .config import clear_auth_credentials

        res = clear_auth_credentials()
        self._json(self._auth_state({
            "ok": True, "removed": res["removed"],
            "message": "已清除保存的账号密码（cookie 会话仍在，要一并清就点「退出登录」）"
                       if res["removed"] else "本来就没有保存账号"}))

    def _auth_settings_logout(self) -> None:
        if not self._is_local():
            self._json({"ok": False, "error": "只有从本机打开页面才能清除会话。"}, 403)
            return
        from . import auth as auth_mod

        sess = auth_mod.AuthSession()
        n = sess.alive()
        sess.clear()
        self._json(self._auth_state({"ok": True,
                                     "message": f"已清除会话（{n} 个 cookie），"
                                                f"账号密码保留"}))

    def _attachment(self) -> None:
        """读一份附件的解析结果（卡片上「看解析出的正文」用）。"""
        q = self._query()
        st = Store(SETTINGS.crawl.db_path)
        try:
            if q.get("id"):
                row = st.get_attachment(int(q["id"]))
            elif q.get("article"):
                rows = st.get_attachments(int(q["article"]))
                row = rows[0] if rows else None
            else:
                row = None
        except (TypeError, ValueError):
            row = None
        st.close()
        if not row:
            self._json({"error": "not found"}, 404)
            return
        # 不把整份附件正文无脑吐给前端：默认 2 万字，够看且不会把页面卡死
        self._json({
            "id": row.get("id"), "article_id": row.get("article_id"),
            "url": row.get("url"), "filename": row.get("filename"),
            "kind": row.get("kind"), "bytes": row.get("bytes"),
            "stored": row.get("stored"), "parser": row.get("parser"),
            "note": row.get("note"), "error": row.get("error"),
            "tables": row.get("tables"), "images": row.get("images"),
            "ocr_used": row.get("ocr_used"), "ocr_chars": row.get("ocr_chars"),
            "chars": len(row.get("text") or ""),
            "text": (row.get("text") or "")[:20000],
            "truncated": len(row.get("text") or "") > 20000,
        })

    def _attachment_file(self) -> None:
        """把下载到 data/attachments/ 的文件本体发出去（本地预览/下载）。

        只允许发附件目录里的文件：路径先做 realpath 再判断前缀，
        防止 `../` 之类的路径穿越读到仓库里别的东西。
        """
        import mimetypes
        import urllib.parse as up
        from pathlib import Path

        from .attachments import ATTACH_DIR

        q = self._query()
        rel = up.unquote(q.get("stored") or q.get("path") or "")
        if not rel:
            self._json({"error": "缺少 stored 参数"}, 400)
            return
        base = ATTACH_DIR.resolve()
        # stored 存的是「相对项目根」的路径（data/attachments/2026/03/xxx.pdf），
        # 而这里要的是「相对附件目录」的路径，两种写法都接受。
        rel_norm = rel.replace("\\", "/").lstrip("/")
        prefix = "data/attachments/"
        if rel_norm.startswith(prefix):
            rel_norm = rel_norm[len(prefix):]
        target = (base / rel_norm).resolve() if not Path(rel_norm).is_absolute() \
            else Path(rel_norm).resolve()
        if target != base and base not in target.parents:
            self._json({"error": "越权路径"}, 403)
            return
        if not target.is_file():
            self._json({"error": "文件不存在（可能已被清理）"}, 404)
            return
        data = target.read_bytes()
        ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        ascii_name = target.name.encode("ascii", "ignore").decode() or "attachment"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header(
            "Content-Disposition",
            f"inline; filename=\"{ascii_name}\"; filename*=UTF-8''{up.quote(target.name)}")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    # ------------------------------------------------------------------ #
    # 计算器 API
    # ------------------------------------------------------------------ #
    @staticmethod
    def _calculator():
        """每次请求新建一个 Calculator。

        `harness.calc` 只依赖 `data/calc/*.json`，不碰 SQLite，构造一次很便宜
        （几毫秒）。刻意不做全局缓存，这样直接改数据文件、刷新页面就生效，
        不需要重启服务，调参时省事。
        """
        from .calc import Calculator

        return Calculator()

    def _calc_catalog(self) -> None:
        self._json(self._calculator().catalog())

    def _calc_activities_refresh(self) -> None:
        """「活动篮」页的『🔄 刷新联网』。

        抓《学生竞赛奖励办法》名录页与几个竞赛通知栏目，和内置名录对账，把结果
        缓存到 data/cache/，然后由前端重新拉一次 /api/calc/catalog 生效。
        抓取失败不算错误状态：返回 ok=False + 每个源的错误原因，页面继续用内置数据。
        """
        from .calc import online as calc_online

        payload = self._read_body()
        timeout = int(payload.get("timeout") or 12)
        timeout = max(4, min(timeout, 30))
        try:
            res = calc_online.refresh(timeout=timeout)
        except Exception as e:                     # noqa: BLE001 - 联网失败要能看懂
            self._json({"ok": False, "error": f"{type(e).__name__}: {e}"}, 200)
            return
        self._json({
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

    def _calc_evaluate(self) -> None:
        payload = self._read_body()
        if not payload:
            self._json({"error": "请求体不是合法 JSON"}, 400)
            return
        res = self._calculator().evaluate_dict(payload)
        self._json(res.as_dict())

    def _calc_target(self) -> None:
        q = self._query()
        try:
            target = float(q.get("gpa") or 0)
        except ValueError:
            target = 0.0
        scores = {}
        raw = q.get("scores") or ""
        if raw:
            try:
                scores = json.loads(raw)
            except json.JSONDecodeError:
                scores = {}
        self._json(self._calculator().target_for_course(
            q.get("major") or "", scores, target))

    # ------------------------------------------------------------------ #
    def _ask(self) -> None:
        """SSE：先推 trace 事件，最后推 answer + done。"""
        q = self._query()
        question = (q.get("q") or "").strip()
        rounds = int(q.get("rounds") or SETTINGS.agent_max_rounds)

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.send_header("Connection", "close")
        self.end_headers()

        def sse(event: str, data: dict) -> None:
            payload = f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
            self.wfile.write(payload.encode("utf-8"))
            self.wfile.flush()

        if not question:
            sse("answer", {"text": "问题为空", "error": "", "citations": ""})
            sse("done", {})
            return
        dry = (q.get("dry") or "").lower() in ("1", "true", "yes")
        if not SETTINGS.llm.configured and not dry:
            sse("answer", {"text": "", "error": "尚未配置 LLM API key：点左下「⚙️ 设置 → 🧠 模型」填入 "
                                                    "base URL / 模型名 / API key 即可（也可运行 "
                                                    "python -m harness.cli setup-key）。"
                                                    "想先看检索结果就勾上「仅检索验证」。",
                           "citations": ""})
            sse("done", {})
            return

        st = Store(SETTINGS.crawl.db_path)
        if st.count_articles() == 0:
            sse("answer", {"text": "", "error": "库内还没有语料，请先运行：python -m harness.cli crawl --scope narrow",
                           "citations": ""})
            sse("done", {})
            st.close()
            return

        llm = LLM(SETTINGS.llm)
        searcher = WebSearcher(SearchSettings.from_env())
        agent = Agent(st, llm, searcher, SETTINGS)

        labels = {
            "decompose": "① 意图分解", "retrieve": "② 检索", "retrieved": "   命中",
            "gaps": "④ 缺口检测", "evidence": "⑥ 证据聚合",
        }

        def trace(step: str, data: dict) -> None:
            label = labels.get(step, step)
            if step == "decompose":
                lines = [f"{label}：{len(data.get('subqueries', []))} 条子查询"]
                lines += [f"    [{x['scope']}] {x['query']}" for x in data.get("subqueries", [])]
                text = "\n".join(lines)
            elif step == "retrieve":
                text = f"{label} 第 {data.get('round')} 轮：" + "；".join(data.get("queries", []))
            elif step == "retrieved":
                text = f"{label} 第 {data.get('round')} 轮 +{data.get('new')}（累计 {data.get('total')}）"
            elif step == "gaps":
                miss = data.get("missing", [])
                text = f"{label}：" + ("证据已足够" if not miss else
                                      "补 " + "；".join(x["query"] for x in miss))
            elif step == "evidence":
                text = f"{label}：{data.get('count')} 条进入生成"
            elif step == "cards":
                st = data.get("stats", {}) or {}
                text = ("⑦ 卡片：活动 %s 张（命中已核验名录 %s）· 附件 %s 个 · 时间 %s 条"
                        % (st.get("activities", 0), st.get("matched", 0),
                           st.get("files", 0), st.get("times", 0)))
            else:
                text = f"{step}: {json.dumps(data, ensure_ascii=False)[:200]}"
            sse("trace", {"text": text})

        try:
            ans = agent.answer(question, max_rounds=rounds, trace=trace, dry_run=dry)
            if dry:
                body = ("### 仅检索验证（未调用 LLM）\n\n"
                        f"共检索到 **{len(ans.evidence)}** 条证据：\n\n"
                        + "\n".join(f"- [{e.n}] {e.title}（{e.pub_date or '无日期'}）"
                                    for e in ans.evidence))
                sse("answer", {"text": body, "error": "",
                               "citations": agent.build_citations(ans),
                               "usage": f"最终 Prompt {len(ans.prompt)} 字符（未送模型）"})
            else:
                sse("answer", {
                    "text": ans.text,
                    "error": ans.error,
                    "citations": agent.build_citations(ans),
                    "usage": llm.usage.line(),
                })
            # ⑦ 卡片：活动/赛事 + 附件 + 关键时间。单独一个事件推送，
            # 让前端先渲染正文再补卡片，长回答的首屏更快。
            if ans.cards:
                sse("cards", ans.cards)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            try:
                sse("answer", {"text": "", "error": f"{type(e).__name__}: {e}", "citations": ""})
            except Exception:
                pass
        finally:
            st.close()
            try:
                sse("done", {})
            except Exception:
                pass


def _port_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


def serve(host: str = "127.0.0.1", port: int = 8848, open_browser: bool = True) -> int:
    if not _port_free(host, port):
        print(f"端口 {port} 已被占用。换一个： python -m harness.cli web --port 8849", file=sys.stderr)
        return 2
    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.daemon_threads = True
    url = f"http://{host}:{port}/"
    print("=" * 70)
    print(f"SCAU Harness Web 界面已启动： {url}")
    print(f"  库文件   : {SETTINGS.crawl.db_path}")
    print(f"  LLM      : {SETTINGS.llm.model} ({'已配置' if SETTINGS.llm.configured else '未配置'})")
    print(f"  公网搜索 : {SearchSettings.from_env().provider}")
    print("  左侧栏切换：主页对话 / 绩点计算器（含四个子页）/ 数据口径说明")
    print("  Ctrl+C 停止")
    print("=" * 70)
    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
    finally:
        httpd.server_close()
    return 0
