"""登录墙支持：CAS 统一身份认证 + 会话 Cookie 复用。

背景（指南 §12.4）：
  `cas.scau.edu.cn`（统一身份认证）后面的页面，裸 GET 拿回来的是登录页 HTML。
  之前 `crawler.py` 只能识别并跳过（`login_required`），本模块让 Harness
  可以带着会话去拿。

两条路，推荐第一条：

  ① `--cookie` 导入浏览器现成 Cookie（`python -m harness.cli login --cookie`）
     —— 全程不接触密码；CAS 有验证码/滑块时这是唯一能用的办法。

  ② 账号密码表单登录（`python -m harness.cli login` / Web 设置面板）
     —— 自动解析登录页的隐藏字段（execution / lt / _eventId）再提交，
        不写死任何参数名，所以对 CAS 4/5 和学校改造过的版本都尽量兼容。
        **登录页有图形验证码时自动下载验证码图，交给 OCR（百度）识别后填回去**，
        一次认错就换一张重试（`AUTH_CAPTCHA_ROUNDS`，默认 3 轮）。

Web 设置面板（⚙️ → 「🔐 账号与登录」）填的账号密码存到 `.auth/credentials.json`；
采集时一旦撞上登录墙，`Crawler` 会**自动**用这份凭据登录一次并重放请求
（`AUTH_AUTO_LOGIN=1`，默认开），不需要先手动 login。

设计边界（重要）：
  · 只用你自己的账号，访问你自己本来就能看到的页面。不提供批量拉他人数据的能力。
  · 凭据与 Cookie 写在 `.auth/`（已 gitignore），不写进 `.env`、不进日志。
  · 会话过期是常态，`AuthSession.message()` 会明确告诉你「过期了，重新登录」。
  · 验证码只在登录那一刻用一次，图片不入库、不落盘、不发给模型。

和采集层的关系：`Fetcher` 可以注入一个 `AuthSession`（见 `fetcher.py`），
注入后同一个 opener 读写 cookie jar，重定向全程带会话，登录态才跟得住。
"""
from __future__ import annotations

import base64
import http.cookiejar
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from .config import ROOT, getenv

# --------------------------------------------------------------------------- #
# 默认端点与落盘位置
# --------------------------------------------------------------------------- #
CAS_BASE = "https://cas.scau.edu.cn"
# 登录成功后 ticket 会回落到这个 service 上（融合门户是学校的主入口）
DEFAULT_SERVICE = "http://portal.scau.edu.cn/"

AUTH_DIR = ROOT / ".auth"


def auth_dir() -> Path:
    """登录态目录（`.auth/`，已 gitignore）。

    每次重算：这样测试里把 `auth_dir` 指到临时目录，就整体搬走了，
    不会碰到你真实的登录态。
    """
    return ROOT / ".auth"


def cookie_file() -> Path:
    return auth_dir() / "cookies.json"


def cred_file() -> Path:
    return auth_dir() / "credentials.json"


# 给 CLI 直接引用的常量（import 时算一次）。`AuthSession` 内部一律用
# `cookie_file()` 现算，所以两者不会漂移；改 `ROOT` 的只有测试，测试两边都改。
COOKIE_FILE = cookie_file()
CRED_FILE = cred_file()


# 连这些域名说明还停在认证流程里 = 没登录成功
AUTH_HOSTS = ("cas.scau.edu.cn", "sso.scau.edu.cn", "iap.scau.edu.cn")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# 需要人机交互时，脚本登录就该放弃，改走 Cookie 导入
# （滑块 / 短信 / 双因子仍然过不去；图形验证码现在能自己认了，见下面 captcha 部分）
BLOCKERS = {
    "slider": ("滑块", "滑动验证", "nc_1_n1z"),
    "sms": ("短信验证", "动态口令", "手机验证"),
    "2fa": ("双因子", "两步验证", "二次验证"),
}
# 单独列出来：验证码是可以自动过的，不再算「拦路虎」
CAPTCHA_NEEDLES = ("验证码", "图形验证码", "checkcode", "captcha", "verifycode")

FORM_RE = re.compile(r"<form\b[^>]*>", re.I)
ACTION_RE = re.compile(r'\baction\s*=\s*["\']([^"\']+)["\']', re.I)
INPUT_RE = re.compile(r"<input\b[^>]*>", re.I)
IMG_RE = re.compile(r"<img\b[^>]*>", re.I)
NAME_RE = re.compile(r'\bname\s*=\s*["\']([^"\']+)["\']', re.I)
VALUE_RE = re.compile(r'\bvalue\s*=\s*["\']([^"\']*)["\']', re.I)
TYPE_RE = re.compile(r'\btype\s*=\s*["\']([^"\']+)["\']', re.I)
SRC_RE = re.compile(r'\bsrc\s*=\s*["\']([^"\']+)["\']', re.I)
ATTR_RE = re.compile(r'([A-Za-z_:][-A-Za-z0-9_:.]*)\s*=\s*["\']([^"\']*)["\']')
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
SCRIPT_RE = re.compile(r"<script\b.*?</script>|<style\b.*?</style>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")

# 字段名不是固定的（CAS 用 execution，有的学校用 lt / _csrf / authenticity_token），
# 所以按「语义猜测」而不是写死。
USER_FIELD_HINTS = ("username", "user", "account", "loginname", "yhm", "uname", "zh")
PASS_FIELD_HINTS = ("password", "passwd", "pwd", "mm")
EVENT_FIELD_HINTS = ("_eventid", "eventid", "submit")
CAPTCHA_FIELD_HINTS = ("captcha", "checkcode", "verifycode", "verify_code", "vcode",
                       "authcode", "yzm", "validatecode", "randcode", "inputcode")
# 验证码图片「长得像验证码」的特征：属性值或 URL 里带这些词就优先选它
CAPTCHA_IMG_HINTS = CAPTCHA_FIELD_HINTS + ("captcha", "checkcode", "验证码", "randimage",
                                           "validate", "captchaimg", "codeimg", "imagecode")
CAPTCHA_URL_HINTS = ("captcha", "kaptcha", "checkcode", "verifycode", "vcode", "authcode",
                     "yzm", "randcode", "getcode", "codeimg", "validatecode", "captcha.jpg",
                     "captcha.png", "captcha.gif")
# 猜不到 <img> 时按这几个常见路径试一试（只在「已确认有验证码字段」时才试）
CAPTCHA_GUESS_PATHS = ("/lyuapServer/captcha", "/lyuapServer/kaptcha",
                       "/lyuapServer/verifyCode", "/captcha", "/kaptcha")


# --------------------------------------------------------------------------- #
# 自动登录 / 验证码 的运行时配置
#
# 和 OCR 那套一样：值写在 `.env`（非机密），保存后原地热更新，不用重启服务。
# 账号密码本身**不进 .env**，只落在 `.auth/credentials.json`。
# --------------------------------------------------------------------------- #
def _env_flag(name: str, default: bool) -> bool:
    raw = (getenv(name, "1" if default else "0") or "").strip().lower()
    return raw not in ("0", "false", "no", "off", "")


@dataclass
class AuthSettings:
    auto_login: bool = True        # 撞到登录墙时自动用保存的账号密码登录
    ocr_captcha: bool = True       # 登录页有验证码时用 OCR 识别
    captcha_rounds: int = 3        # 验证码认错时最多换几张图重试
    service: str = ""              # 登录后跳转的目标地址（空 = 融合门户）
    captcha_url: str = ""          # 验证码图片地址（页面上猜不到时手填）

    @classmethod
    def from_env(cls) -> "AuthSettings":
        try:
            rounds = int(getenv("AUTH_CAPTCHA_ROUNDS", "3") or 3)
        except ValueError:
            rounds = 3
        return cls(
            auto_login=_env_flag("AUTH_AUTO_LOGIN", True),
            ocr_captcha=_env_flag("AUTH_OCR_CAPTCHA", True),
            captcha_rounds=max(1, min(rounds, 8)),
            service=getenv("AUTH_SERVICE"),
            captcha_url=getenv("AUTH_CAPTCHA_URL"),
        )

    def describe(self) -> str:
        bits = [f"自动登录 {'开' if self.auto_login else '关'}",
                f"验证码 OCR {'开' if self.ocr_captcha else '关'}（最多 {self.captcha_rounds} 次）"]
        if self.service:
            bits.append(f"service={self.service}")
        return "，".join(bits)


# 进程内可热更新（Web 设置面板保存后立刻生效，不用重启）
SETTINGS = AuthSettings.from_env()


def refresh_settings() -> AuthSettings:
    global SETTINGS
    SETTINGS = AuthSettings.from_env()
    return SETTINGS


# --------------------------------------------------------------------------- #
@dataclass
class LoginResult:
    ok: bool = False
    message: str = ""
    final_url: str = ""
    cookies: int = 0
    saved: bool = False
    blockers: list[str] = field(default_factory=list)
    history: list[tuple[str, str, int]] = field(default_factory=list)   # (method, url, status)
    # ---- 验证码相关 ---- #
    captcha_seen: bool = False          # 登录页有验证码
    captcha_text: str = ""              # OCR 认出来并提交的值
    captcha_rounds: int = 0             # 一共试了几张验证码
    captcha_error: str = ""             # 认不出来的原因
    captcha_image: bytes = b""          # 认不出来时把图带回去，让人自己填
    captcha_mime: str = "image/png"
    captcha_field: str = ""
    user: str = ""                      # 本次用的账号（打码后给别人看）

    @property
    def need_captcha(self) -> bool:
        """登录没成、而手上正好有一张验证码图 → 交给人工看一眼就能接着登。

        OCR 什么都没认出来（图还在）算，OCR 认出来了但认错（登录还是失败）也算——
        两种情况人工都能补救，所以判据只看「有没有图」而不是「有没有认出来」。
        """
        return bool(self.captcha_seen and not self.ok and self.captcha_image)

    def captcha_data_url(self) -> str:
        if not self.captcha_image:
            return ""
        return (f"data:{self.captcha_mime or 'image/png'};base64,"
                + base64.b64encode(self.captcha_image).decode("ascii"))

    def debug(self) -> str:
        lines = [f"  {'✓' if self.ok else '✗'} {self.message}"]
        if self.user:
            lines.append(f"    账号     : {self.user}")
        if self.final_url:
            lines.append(f"    最终落在 : {self.final_url}")
        lines.append(f"    拿到 Cookie: {self.cookies} 个")
        if self.captcha_seen:
            detail = (f"认成「{self.captcha_text}」" if self.captcha_text
                      else f"未识别（{self.captcha_error or '原因不明'}）")
            lines.append(f"    验证码   : {detail}，共试 {self.captcha_rounds} 张")
        if self.blockers:
            lines.append(f"    拦路虎   : {'、'.join(self.blockers)}（脚本登录不可用，请用 --cookie）")
        for m, u, st in self.history[-8:]:
            lines.append(f"    {st:>3} {m:<4} {u[:110]}")
        return "\n".join(lines)


# --------------------------------------------------------------------------- #
# 验证码：找到它、取下来、认出来
# --------------------------------------------------------------------------- #
@dataclass
class CaptchaChallenge:
    """一次验证码挑战：填在哪个字段、图在哪、认出来是什么。"""

    field: str = ""
    image_url: str = ""
    image: bytes = b""
    mime: str = "image/png"
    source: str = ""                 # img | data-uri | manual
    text: str = ""
    error: str = ""
    prep: str = ""                   # 预处理说明（排错用）

    @property
    def has_image(self) -> bool:
        return bool(self.image)

    def data_url(self) -> str:
        if not self.image:
            return ""
        return (f"data:{self.mime or 'image/png'};base64,"
                + base64.b64encode(self.image).decode("ascii"))


@dataclass
class LoginForm:
    """一次「打开登录页」的结果：够用来提交一次登录（也够人工补一次验证码）。"""

    hidden: dict[str, str] = field(default_factory=dict)
    action: str = ""
    html: str = ""
    page_url: str = ""
    service: str = ""               # 登录成功后要跳到的目标地址（验证用）
    user_field: str = "username"
    pass_field: str = "password"
    event_field: str = ""
    captcha_field: str = ""
    challenge: CaptchaChallenge | None = None
    blockers: list[str] = field(default_factory=list)
    error: str = ""

    @property
    def ok(self) -> bool:
        return bool(self.hidden) and not self.error

    @property
    def needs_captcha(self) -> bool:
        return bool(self.captcha_field)


def _tag_attrs(tag: str) -> dict[str, str]:
    return {m.group(1).lower(): m.group(2) for m in ATTR_RE.finditer(tag or "")}


def find_captcha_field(fields: dict[str, str] | None) -> str:
    """按语义找出验证码输入框的字段名（不写死）。"""
    for hint in CAPTCHA_FIELD_HINTS:
        for name in (fields or {}):
            if hint in str(name).lower():
                return str(name)
    return ""


def find_captcha_image(html: str, base_url: str, *, field: str = "",
                       override: str = "") -> CaptchaChallenge:
    """在登录页里找出验证码图片。

    顺序：① 设置里手填的地址（兜底，最可靠）→ ② 按 <img> 属性打分挑最像的那张
    → ③ `data:image/...` 内联图直接用。找不到就返回一个空 challenge，由调用方
    决定是报错还是继续（有些站的验证码是 JS 动态画的，脚本拿不到图）。
    """
    ch = CaptchaChallenge(field=field)
    if override:
        ch.image_url = override
        ch.source = "manual"
        return ch

    best: tuple[int, str] | None = None
    for m in IMG_RE.finditer(html or ""):
        attrs = _tag_attrs(m.group(0))
        src = (attrs.get("src") or "").strip()
        if not src:
            continue
        blob = " ".join(f"{k}={v}" for k, v in attrs.items()).lower()
        low_src = src.lower()
        score = 0
        if any(h in blob for h in CAPTCHA_IMG_HINTS):
            score += 3
        if any(h in low_src for h in CAPTCHA_URL_HINTS):
            score += 2
        if field and field.lower() in blob:
            score += 2
        if score and (best is None or score > best[0]):
            best = (score, src)
    if best is None:
        return ch

    src = best[1]
    if src.lower().startswith("data:image/"):
        head, _, payload = src.partition(",")
        ch.mime = (head[5:].split(";")[0] or "image/png").strip() or "image/png"
        try:
            ch.image = base64.b64decode(payload)
            ch.source = "data-uri"
        except Exception:                                     # noqa: BLE001
            ch.error = "内联验证码图解码失败"
        return ch
    ch.image_url = urllib.parse.urljoin(base_url or "", src.replace("&amp;", "&"))
    ch.source = "img"
    return ch


def _plausible_image(raw: bytes, ctype: str) -> bool:
    """判断一段响应到底是不是图片（有些站的验证码接口失败时返回 HTML）。"""
    if not raw or len(raw) > 512 * 1024:
        return False
    if ctype.startswith("image/"):
        return True
    return raw[:4] in (b"\x89PNG", b"\xff\xd8\xff\xe0", b"\xff\xd8\xff\xe1", b"GIF8", b"BM")


# 可注入的验证码求解器（测试用假 OCR，不联网）：solver(image_bytes, challenge) -> (text, error)
_CAPTCHA_SOLVER = None


def set_captcha_solver(fn) -> None:
    """替换验证码识别实现（测试注入假 OCR 用；传 None 恢复默认的百度 OCR）。"""
    global _CAPTCHA_SOLVER
    _CAPTCHA_SOLVER = fn


def captcha_solvable() -> bool:
    """现在到底有没有办法认验证码（注入了求解器，或者配了 OCR）。"""
    if _CAPTCHA_SOLVER is not None:
        return True
    try:
        from . import ocr as ocr_mod

        return bool(ocr_mod.SETTINGS.configured)
    except Exception:                                         # noqa: BLE001
        return False


def solve_captcha(data: bytes, challenge: CaptchaChallenge | None = None,
                  *, settings: AuthSettings | None = None) -> tuple[str, str]:
    """认一张验证码图。返回 (文本, 错误说明)。识别失败时文本为空串。"""
    if not data:
        return "", "没有拿到验证码图片"
    if _CAPTCHA_SOLVER is not None:
        try:
            out = _CAPTCHA_SOLVER(data, challenge)
        except Exception as e:                                # noqa: BLE001
            return "", f"验证码求解器异常：{type(e).__name__}: {e}"
        if isinstance(out, tuple):
            return str(out[0] or ""), str(out[1] if len(out) > 1 else "")
        return str(out or ""), ""
    try:
        from . import ocr as ocr_mod
    except Exception as e:                                    # noqa: BLE001
        return "", f"OCR 模块不可用：{type(e).__name__}"
    if not ocr_mod.SETTINGS.configured:
        return "", ("未配置 OCR，无法自动识别验证码（在设置面板「附件与 OCR」里填百度 "
                    "API Key / Secret Key），或改用浏览器 Cookie 导入")
    res = ocr_mod.recognize_captcha(data)
    if challenge is not None:
        challenge.prep = getattr(res, "engine", "") or ""
    if res.text:
        return res.text, ""
    return "", res.error or "OCR 没认出验证码里的字符"


def _looks_like_login(text: str) -> bool:
    low = (text or "").lower()
    return any(s in low for s in ("cas.scau.edu.cn", "lyuapserver", "统一身份认证",
                                  "统一认证", "please login", "用户登录"))


def _text_title(html: str) -> str:
    m = TITLE_RE.search(html or "")
    if m:
        return TAG_RE.sub("", m.group(1)).strip()[:80]
    plain = TAG_RE.sub(" ", SCRIPT_RE.sub(" ", html or ""))
    return re.sub(r"\s+", " ", plain).strip()[:80]


def _detect_blockers(html: str) -> list[str]:
    """找出「脚本过不去」的人机校验（滑块 / 短信 / 双因子）。

    图形验证码**不再**算拦路虎：它会被自动下载 + OCR 识别 + 填回表单，
    所以另有 `has_captcha()` 单独判断。
    """
    low = (html or "").lower()
    found = []
    for name, needles in BLOCKERS.items():
        if any(n.lower() in low for n in needles):
            found.append(name)
    return found


def has_captcha(html: str, fields: dict[str, str] | None = None) -> bool:
    """登录页有没有图形验证码（看表单字段名，也看页面文案与图片特征）。"""
    if fields and find_captcha_field(fields):
        return True
    low = (html or "").lower()
    return any(n.lower() in low for n in CAPTCHA_NEEDLES)


# --------------------------------------------------------------------------- #
SSL_CTX = None


def _ssl_context():
    """优先用 certifi 的根证书（Windows 上 Python 自带的常常不全）。"""
    global SSL_CTX
    if SSL_CTX is not None:
        return SSL_CTX
    import ssl

    try:
        import certifi  # type: ignore

        SSL_CTX = ssl.create_default_context(cafile=certifi.where())
    except Exception:
        SSL_CTX = ssl.create_default_context()
        # 校内站点证书链经常不完整；校验失败时退一步，但仅限本会话
        SSL_CTX.check_hostname = False
        SSL_CTX.verify_mode = ssl.CERT_NONE
    return SSL_CTX


class AuthSession:
    """带 CookieJar 的 HTTP 会话。所有请求共用同一个 opener，重定向全程带 cookie。"""

    def __init__(self, *, user_agent: str = UA, timeout: int = 30,
                 cookie_path: Path | None = None, auto_load: bool = True) -> None:
        self.user_agent = user_agent
        self.timeout = timeout
        self.cookie_file = cookie_path or cookie_file()
        self.jar = http.cookiejar.CookieJar()
        self.history: list[tuple[str, str, int]] = []
        self._opener = self._build_opener()
        if auto_load:
            self.load_cookies()

    # ---------- opener ---------- #
    def _build_opener(self):
        handlers = [urllib.request.HTTPCookieProcessor(self.jar),
                    urllib.request.HTTPSHandler(context=_ssl_context())]
        return urllib.request.build_opener(*handlers)

    # ---------- 基础请求 ---------- #
    def _headers(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        h = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.6",
            "Connection": "close",
        }
        if extra:
            h.update(extra)
        return h

    def request(self, url: str, method: str = "GET", data: bytes | None = None,
                extra_headers: dict[str, str] | None = None,
                timeout: int | None = None, record: bool = True) -> urllib.response.addinfourl:
        """发一个请求。重定向由 urllib 自动跟随（并逐个写 cookie）。"""
        req = urllib.request.Request(url, data=data, method=method,
                                     headers=self._headers(extra_headers))
        resp = self._opener.open(req, timeout=timeout or self.timeout)
        if record:
            self.history.append((method, resp.geturl(), getattr(resp, "status", 200)))
        return resp

    def get(self, url: str, **kw) -> tuple[str, int, str]:
        """返回 (正文, 状态码, 最终 URL)。"""
        with self.request(url, "GET", **kw) as r:
            raw = r.read()
            ctype = r.headers.get("Content-Type", "")
            return self._decode(raw, ctype), getattr(r, "status", 200), r.geturl()

    def post(self, url: str, fields: dict[str, str], *, referer: str = "",
             **kw) -> tuple[str, int, str]:
        body = urllib.parse.urlencode(fields, encoding="utf-8").encode()
        extra = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": CAS_BASE,
        }
        if referer:
            extra["Referer"] = referer
        with self.request(url, "POST", body, extra_headers=extra, **kw) as r:
            raw = r.read()
            ctype = r.headers.get("Content-Type", "")
            return self._decode(raw, ctype), getattr(r, "status", 200), r.geturl()

    @staticmethod
    def _decode(raw: bytes, content_type: str = "") -> str:
        # 复用采集层的编码判定（header → meta → 探测），校内站点编码很杂
        from .fetcher import decode_bytes

        return decode_bytes(raw, content_type)[0]

    def get_bytes(self, url: str, *, referer: str = "",
                  extra_headers: dict[str, str] | None = None,
                  timeout: int | None = None) -> tuple[bytes, str, int, str]:
        """取二进制内容（验证码图片走这条）。返回 (字节, mime, 状态码, 最终 URL)。

        和 `get()` 分开是因为验证码图不能被当成文本解码一遍——PNG 解成 str 就废了。
        走同一个 opener，所以依赖登录页 cookie 的验证码接口也能拿到图。
        """
        extra = dict(extra_headers or {})
        extra.setdefault("Accept", "image/avif,image/webp,image/png,image/*,*/*;q=0.8")
        if referer:
            extra.setdefault("Referer", referer)
        with self.request(url, "GET", extra_headers=extra, timeout=timeout) as r:
            raw = r.read()
            ctype = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            return raw, ctype, getattr(r, "status", 200), r.geturl()

    @staticmethod
    def _cas_url(url: str) -> str:
        """service 参数里的空格要手动转成 %20，urllib 的 urlencode 会写成 '+'。"""
        return urllib.parse.quote_plus(url, safe="").replace("+", "%20")

    # ---------- 状态判断 ---------- #
    def cookie_summary(self) -> list[str]:
        out = []
        for c in self.jar:
            mark = "" if c.is_expired() else ("*" if not c.secure else "")
            out.append(f"{c.domain}{c.path} {c.name}{'（已过期）' if c.is_expired() else ''}{mark}")
        return out

    def alive(self) -> int:
        """未过期的 cookie 数量。0 表示肯定没登录态。"""
        return sum(1 for c in self.jar if not c.is_expired())

    def at_login(self, url: str) -> bool:
        low = (url or "").lower()
        return any(h in low for h in AUTH_HOSTS) or "login" in low or "cas" in low

    def clear(self) -> None:
        """清空会话（同时删掉落盘的 cookie 文件）。"""
        self.jar.clear()
        try:
            self.cookie_file.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass

    # ---------- Cookie 落盘 ---------- #
    def save_cookies(self) -> Path:
        self.cookie_file.parent.mkdir(parents=True, exist_ok=True)
        rows = []
        for c in self.jar:
            rows.append({
                "name": c.name, "value": c.value, "domain": c.domain, "path": c.path or "/",
                "secure": bool(c.secure), "expires": c.expires, "version": c.version,
            })
        self.cookie_file.write_text(
            json.dumps({"saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "user_agent": self.user_agent,
                        "cookies": rows}, ensure_ascii=False, indent=2),
            encoding="utf-8")
        _restrict(self.cookie_file)
        return self.cookie_file

    def load_cookies(self) -> int:
        if not self.cookie_file.is_file():
            return 0
        try:
            data = json.loads(self.cookie_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return 0
        n = 0
        for row in data.get("cookies") or []:
            try:
                self.jar.set_cookie(http.cookiejar.Cookie(
                    version=row.get("version", 0), name=row["name"], value=row["value"],
                    port=None, port_specified=False,
                    domain=row.get("domain") or "", domain_specified=True,
                    domain_initial_dot=str(row.get("domain") or "").startswith("."),
                    path=row.get("path") or "/", path_specified=True,
                    secure=bool(row.get("secure")), expires=row.get("expires"),
                    discard=False, comment=None, comment_url=None, rest={},
                ))
                n += 1
            except Exception:
                continue
        return n

    def set_cookie_header(self, raw: str, domain: str) -> int:
        """把浏览器复制的一整行 Cookie 头塞进 jar。`domain` 形如 cas.scau.edu.cn。"""
        raw = (raw or "").strip()
        # 容忍有人把「Cookie: xxx」前缀、换行、末尾分号一起复制进来
        raw = re.sub(r"^\s*cookie\s*:\s*", "", raw, flags=re.I)
        raw = raw.replace("\r", ";").replace("\n", ";")
        # 校内业务系统有 http 的（如 portal.scau.edu.cn），secure 不能一律置 True，
        # 否则这些 cookie 在 http 请求里根本不会被带上。
        host = domain.split(":")[0].lower()
        secure = not (host in ("localhost", "127.0.0.1") or re.match(r"^\d+\.\d+\.\d+\.\d+$", host))
        n = 0
        for part in raw.split(";"):
            if "=" not in part:
                continue
            k, _, v = part.partition("=")
            k, v = k.strip(), v.strip()
            if not k:
                continue
            self.jar.set_cookie(http.cookiejar.Cookie(
                version=0, name=k, value=v, port=None, port_specified=False,
                domain=domain, domain_specified=True,
                domain_initial_dot=domain.startswith("."),
                path="/", path_specified=True, secure=bool(secure), expires=None,
                discard=False, comment=None, comment_url=None, rest={},
            ))
            n += 1
        return n

    # ---------- CAS 登录 ---------- #
    def _fetch_first_form(self, service: str) -> tuple[dict, str, str, str, list[str]]:
        """找一个能用的 CAS 登录表单。

        返回 (字段, action, 页面正文, 页面最终 URL, 拦路虎)。字段里既有隐藏字段，
        也有账号/密码/验证码这些可见输入框（名字由 `_parse_form` 原样保留）。
        """
        idx = f"{CAS_BASE}/lyuapServer/login?service={self._cas_url(service)}"
        tries = [
            (idx, ""),
            (f"{CAS_BASE}/login?service={self._cas_url(service)}", ""),
            (f"{CAS_BASE}/lyuapServer/login", idx),
            (CAS_BASE + "/", ""),
        ]
        blockers: list[str] = []
        last_html, last_url = "", ""
        for url, referer in tries:
            try:
                html, status, final = self.get(url, extra_headers={"Referer": referer} if referer else None)
            except Exception as e:
                blockers.append(f"{type(e).__name__}@{urllib.parse.urlsplit(url).netloc}")
                continue
            last_html, last_url = html, final
            blockers += _detect_blockers(html)
            hidden, action = _parse_form(html, final)
            if hidden:
                return hidden, action, html, final, blockers
        return {}, last_url or idx, last_html, last_url or idx, blockers

    def open_login_form(self, service: str, *, settings: AuthSettings | None = None,
                        with_captcha: bool = True) -> LoginForm:
        """打开登录页并解析好表单（含验证码图，如果有）。

        单独拆出来是为了两条路共用：① 全自动登录（`login()`，验证码交给 OCR）；
        ② Web 面板上「OCR 认不出来 → 让人自己看着图填」的那条路。
        """
        s = settings or SETTINGS
        hidden, action, html, page_url, blockers = self._fetch_first_form(service)
        form = LoginForm(hidden=dict(hidden), action=action, html=html, page_url=page_url,
                         service=service, blockers=sorted(set(blockers)))
        if not hidden:
            form.error = f"没有在登录页里找到表单字段（页面标题：{_text_title(html) or '空'}）"
            return form
        # 账号/密码字段在 CAS 页面里通常是**可见**输入框（也会出现在字段集合里），
        # 所以先用语义猜名字，猜不到再退回 CAS 惯例名。
        form.user_field = _guess_field(hidden, USER_FIELD_HINTS) or "username"
        form.pass_field = _guess_field(hidden, PASS_FIELD_HINTS) or "password"
        form.event_field = _guess_field(hidden, EVENT_FIELD_HINTS)
        form.captcha_field = find_captcha_field(hidden)
        if not form.captcha_field or not with_captcha:
            return form

        ch = find_captcha_image(html, page_url or action, field=form.captcha_field,
                                override=s.captcha_url)
        if not ch.image and not ch.image_url and not ch.error:
            ch = self._guess_captcha_image(service, ch)
        if ch.image_url and not ch.image:
            ch = self._download_captcha(ch, referer=page_url or action)
        form.challenge = ch
        return form

    def _download_captcha(self, ch: CaptchaChallenge, *, referer: str) -> CaptchaChallenge:
        try:
            raw, ctype, status, _ = self.get_bytes(ch.image_url, referer=referer)
        except urllib.error.HTTPError as e:
            ch.error = f"取验证码图片失败：HTTP {e.code}"
            return ch
        except Exception as e:                                # noqa: BLE001
            ch.error = f"取验证码图片失败：{type(e).__name__}"
            return ch
        if not _plausible_image(raw, ctype):
            ch.error = (f"验证码地址返回的不是图片（HTTP {status}，"
                        f"{ctype or '类型未知'}，{len(raw)} 字节）")
            return ch
        ch.image = raw
        ch.mime = ctype or ch.mime or "image/png"
        return ch

    def _guess_captcha_image(self, service: str, ch: CaptchaChallenge) -> CaptchaChallenge:
        """页面上没有 <img> 时，按常见路径猜一猜验证码接口（最多几个，不是暴力枚举）。"""
        from urllib.parse import urlsplit

        base = ""
        for u in (CAS_BASE, self.history[-1][1] if self.history else ""):
            if u:
                p = urlsplit(u)
                base = f"{p.scheme}://{p.netloc}"
                break
        if not base:
            return ch
        for path in CAPTCHA_GUESS_PATHS:
            url = base + path
            try:
                raw, ctype, status, final = self.get_bytes(
                    url, referer=self.history[-1][1] if self.history else base)
            except Exception:                                 # noqa: BLE001
                continue
            if _plausible_image(raw, ctype):
                ch.image = raw
                ch.image_url = final or url
                ch.mime = ctype or "image/png"
                ch.source = "guessed"
                return ch
        ch.error = ch.error or "没在登录页里找到验证码图片（可在设置里手填验证码图片地址）"
        return ch

    def submit_login(self, form: LoginForm, username: str, password: str,
                     captcha_text: str = "") -> LoginResult:
        """按已解析好的表单提交一次登录，并验证真的进得去。"""
        res = LoginResult(blockers=list(form.blockers),
                          user=mask_username(username),
                          captcha_seen=bool(form.captcha_field),
                          captcha_field=form.captcha_field,
                          captcha_text=captcha_text)
        if form.challenge is not None and form.challenge.image:
            res.captcha_image = form.challenge.image
            res.captcha_mime = form.challenge.mime or "image/png"
        if not form.ok:
            res.message = form.error or "没有在登录页里找到表单字段"
            res.history = list(self.history)
            return res

        fields = {k: v for k, v in form.hidden.items()
                  if k.lower() not in CAPTCHA_FIELD_HINTS}
        fields[form.user_field] = username
        fields[form.pass_field] = password
        if form.event_field:
            fields[form.event_field] = "submit"
        else:
            fields.setdefault("_eventId", "submit")
        if form.captcha_field:
            fields[form.captcha_field] = captcha_text
        if not any(k.lower() == "geolocation" for k in fields):
            fields.setdefault("geolocation", "")

        referer = form.page_url or (self.history[-1][1] if self.history else form.action)
        try:
            body, status, final = self.post(form.action, fields, referer=referer, record=False)
        except urllib.error.HTTPError as e:
            res.message = f"登录请求返回 HTTP {e.code}"
            res.history = list(self.history)
            return res
        except Exception as e:                                # noqa: BLE001
            res.message = f"登录请求失败：{type(e).__name__}: {e}"
            res.history = list(self.history)
            return res
        self.history.append(("POST", final, status))

        if self.at_login(final) and "/login" in final:
            err = _scrape_error(body) or _text_title(body)
            res.message = f"提交后仍停在登录页：{err or '账号或密码不正确'}"
            res.history = list(self.history)
            return res

        # 再确认一次：能不能真的落到 service 页
        target = form.service or DEFAULT_SERVICE
        try:
            page, st2, final2 = self.get(target)
            self.history.append(("GET", final2, st2))
            if self.at_login(final2):
                res.message = f"Cookie 拿到了，但访问 {target} 仍被弹回认证页"
                res.final_url = final2
                res.cookies = len(list(self.jar))
                res.history = list(self.history)
                return res
            res.ok = True
            res.final_url = final2
            res.message = f"登录成功（{_text_title(page) or final2}）"
        except Exception as e:                                # noqa: BLE001
            res.message = f"登录请求已提交，但验证页打不开：{type(e).__name__}"
            res.final_url = final
        res.cookies = len(list(self.jar))
        res.saved = bool(self.cookie_file.is_file())
        res.history = list(self.history)
        return res

    def login(self, username: str, password: str, *,
              service: str = DEFAULT_SERVICE,
              settings: AuthSettings | None = None,
              on_captcha=None) -> LoginResult:
        """带验证码处理的完整登录。

        流程：打开登录页 → 有验证码就下载图 + OCR 识别 → 提交 → 成功即止；
        失败（验证码认错 / 会话过期）就**重新拉一张验证码**再试，最多
        `AUTH_CAPTCHA_ROUNDS` 轮。OCR 认不出来时不再空转，直接把验证码图带回去
        （`LoginResult.captcha_image`），让界面问人。

        `on_captcha(challenge)` 可注入：返回人工填的验证码文本（返回空则放弃）。
        """
        s = settings or SETTINGS
        rounds = max(1, s.captcha_rounds) if s.ocr_captcha else 1
        can_solve = captcha_solvable()
        res = LoginResult(user=mask_username(username))
        for attempt in range(1, rounds + 1):
            form, captcha_text, cap_err = begin_login(self, service, settings=s,
                                                      on_captcha=on_captcha)
            if not form.ok:
                res.message = form.error or "没有在登录页里找到表单字段"
                res.blockers = list(form.blockers)
                res.history = list(self.history)
                return res
            if any(b in ("slider", "sms", "2fa") for b in form.blockers):
                res.blockers = list(form.blockers)
                res.message = ("登录页要求 " + "、".join(form.blockers)
                               + "，脚本过不去 → 请用「导入浏览器 Cookie」")
                res.history = list(self.history)
                return res

            if form.captcha_field:
                ch = form.challenge or CaptchaChallenge(field=form.captcha_field)
                res.captcha_seen = True
                res.captcha_field = form.captcha_field
                res.captcha_rounds = attempt
                if ch.has_image:
                    res.captcha_image = ch.image
                    res.captcha_mime = ch.mime or "image/png"
                if not captcha_text:
                    res.captcha_error = cap_err or "OCR 没认出验证码"
                    res.message = f"验证码识别失败（第 {attempt} 张）：{res.captcha_error}"
                    res.history = list(self.history)
                    if not can_solve:
                        # 压根没有办法认验证码：换多少张都一样，别空转刷学校 CAS
                        return res
                    continue                          # 换一张验证码再试
                res.captcha_text = captcha_text

            out = self.submit_login(form, username, password, captcha_text)
            out.user = mask_username(username)
            out.captcha_rounds = attempt
            if out.ok:
                return out
            res = out
            if not form.captcha_field or attempt >= rounds:
                return res
            # 有验证码还可能只是认错了 → 重新拉一张再试
        return res

    # ---------- 验证 ---------- #
    def probe(self, url: str) -> dict:
        """访问一个 URL，回报「是否还在登录墙后面」和页面标题。"""
        out = {"url": url, "ok": False, "status": 0, "final_url": "", "title": "",
               "login_wall": False, "error": "", "bytes": 0}
        try:
            text, status, final = self.get(url)
        except urllib.error.HTTPError as e:
            out.update(status=e.code, error=f"http_{e.code}", final_url=url)
            return out
        except Exception as e:
            out.update(error=f"{type(e).__name__}: {e}", final_url=url)
            return out
        out.update(ok=True, status=status, final_url=final, title=_text_title(text),
                   bytes=len(text.encode("utf-8")))
        out["login_wall"] = self.at_login(final) or _looks_like_login(text[:4000])
        return out


# --------------------------------------------------------------------------- #
# 表单解析
# --------------------------------------------------------------------------- #
def _parse_form(html: str, base_url: str) -> tuple[dict[str, str], str]:
    """抽登录表单：优先带 password 的那个 form，否则取第一个。"""
    forms = []
    for m in FORM_RE.finditer(html or ""):
        start = m.start()
        end = html.find("</form>", start)
        body = html[start:end if end > 0 else len(html)]
        amps = ACTION_RE.search(m.group(0))
        action = urllib.parse.urljoin(base_url, amps.group(1)) if amps else base_url
        fields: dict[str, str] = {}
        has_pw = False
        for tag in INPUT_RE.finditer(body):
            t = tag.group(0)
            n = NAME_RE.search(t)
            if not n:
                continue
            name = n.group(1)
            typ = (TYPE_RE.search(t).group(1).lower() if TYPE_RE.search(t) else "text")
            if typ in ("submit", "button", "image", "reset", "file"):
                continue
            if typ == "password":
                has_pw = True
            v = VALUE_RE.search(t)
            fields[name] = v.group(1) if v else ""
        forms.append((has_pw, fields, action))
    if not forms:
        return {}, base_url
    for has_pw, fields, action in forms:
        if has_pw:
            return fields, action
    return forms[0][1], forms[0][2]


def _guess_field(fields: dict[str, str], hints: tuple[str, ...]) -> str:
    """按语义猜字段名（不写死 CAS 的参数名，兼容各校改造过的登录页）。"""
    for hint in hints:
        for orig in fields:
            if hint in orig.lower():
                return orig
    return ""


def _scrape_error(html: str) -> str:
    """从登录页里捞错误提示。CAS 通常放在 #msg / .errors / alert 里。"""
    for pat in (r'id=["\']msg["\'][^>]*>(.*?)<', r'class=["\'][^"\']*error[^"\']*["\'][^>]*>(.*?)<',
                r'id=["\']error["\'][^>]*>(.*?)<'):
        m = re.search(pat, html or "", re.I | re.S)
        if m:
            txt = TAG_RE.sub("", m.group(1)).strip()
            if txt:
                return txt[:120]
    return ""


# --------------------------------------------------------------------------- #
# 凭据落盘（.auth/credentials.json，尽量收紧权限）
# --------------------------------------------------------------------------- #
def _restrict(path: Path) -> None:
    """把文件权限收到「只有当前用户」。Windows 用 icacls，POSIX 用 chmod。

    失败不抛异常——收紧失败只是次优，不该让登录本身挂掉。
    """
    try:
        if os.name == "nt":
            import getpass
            import subprocess

            user = f"{os.environ.get('USERDOMAIN', '')}\\{getpass.getuser()}".lstrip("\\")
            subprocess.run(["icacls", str(path), "/inheritance:r",
                            "/grant:r", f"{user}:(R,W)"],
                           capture_output=True, timeout=15)
        else:
            os.chmod(path, 0o600)
    except Exception:
        pass


def save_credentials(username: str, password: str, path: Path | None = None) -> Path:
    p = path or cred_file()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"username": username, "password": password,
                             "saved_at": time.strftime("%Y-%m-%d %H:%M:%S")},
                            ensure_ascii=False, indent=2), encoding="utf-8")
    _restrict(p)
    return p


def load_credentials(path: Path | None = None) -> tuple[str, str]:
    p = path or cred_file()
    if not p.is_file():
        return "", ""
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "", ""
    return str(d.get("username") or ""), str(d.get("password") or "")


def forget_credentials(path: Path | None = None) -> bool:
    try:
        (path or cred_file()).unlink()
        return True
    except FileNotFoundError:
        return False
    except OSError:
        return False


def mask_username(user: str) -> str:
    """账号打码后再给人看：`2023123456` → `202***56`。日志与界面一律用这个。"""
    u = (user or "").strip()
    if not u:
        return ""
    if len(u) <= 4:
        return u[0] + "***"
    return f"{u[:3]}***{u[-2:]}"


def credentials_state() -> dict:
    """给设置面板看的凭据状态（**不回显密码**，账号也打码）。"""
    user, pw = load_credentials()
    p = cred_file()
    saved_at = ""
    if p.is_file():
        try:
            saved_at = str(json.loads(p.read_text(encoding="utf-8")).get("saved_at") or "")
        except (OSError, ValueError):
            saved_at = ""
    return {
        "username_set": bool(user),
        "username_masked": mask_username(user),
        "password_set": bool(pw),
        "saved_at": saved_at,
        "file": str(p),
        "file_exists": p.is_file(),
        "file_name": p.name,
    }


# --------------------------------------------------------------------------- #
# 会话状态 / 自动登录
# --------------------------------------------------------------------------- #
def session_state(sess: "AuthSession | None" = None) -> dict:
    """当前会话能进到什么程度（设置面板与 doctor 共用）。"""
    s = sess or AuthSession()
    expires = []
    for c in s.jar:
        if not c.is_expired() and c.expires:
            expires.append(float(c.expires))
    saved_at = ""
    if s.cookie_file.is_file():
        try:
            saved_at = str(json.loads(s.cookie_file.read_text(encoding="utf-8"))
                           .get("saved_at") or "")
        except (OSError, ValueError):
            saved_at = ""
    return {
        "cookie_file": str(s.cookie_file),
        "cookie_file_exists": s.cookie_file.is_file(),
        "cookies_alive": s.alive(),
        "cookies_total": len(list(s.jar)),
        "saved_at": saved_at,
        "expires_soonest": min(expires) if expires else 0,
        "service": SETTINGS.service or DEFAULT_SERVICE,
        "cas_base": CAS_BASE,
        "auto_login": SETTINGS.auto_login,
        "ocr_captcha": SETTINGS.ocr_captcha,
        "captcha_rounds": SETTINGS.captcha_rounds,
        "captcha_url": SETTINGS.captcha_url,
    }


def auto_login(session: "AuthSession | None" = None, *, service: str = "",
               settings: AuthSettings | None = None,
               username: str = "", password: str = "",
               progress=None) -> LoginResult:
    """用账号密码自动登录（验证码走 OCR）。

    账号密码默认取 `.auth/credentials.json` 里保存的；显式传 `username`/`password`
    可用界面上刚填、还没落盘的那一份。

    采集时撞到登录墙会调它；CLI / Web 设置面板也可以主动调。
    成功会把 cookie 落盘，之后同一个 `AuthSession` 就是登录态。
    """
    s = settings or SETTINGS
    say = progress or (lambda msg: None)
    stored_user, stored_pw = load_credentials()
    user = username or stored_user
    pw = password or stored_pw
    if not user or not pw:
        return LoginResult(ok=False,
                           message="没有保存的账号密码（在设置面板「🔐 账号与登录」里填，"
                                   "或跑 python -m harness.cli login）")
    sess = session or default_session()
    target = service or s.service or DEFAULT_SERVICE
    say(f"  · 登录墙：用账号 {mask_username(user)} 自动登录 {CAS_BASE}")
    res = sess.login(user, pw, service=target, settings=s)
    if res.ok:
        res.saved = True
        try:
            sess.save_cookies()
        except OSError:
            pass
        extra = f"，验证码 OCR 认成「{res.captcha_text}」（试了 {res.captcha_rounds} 张）" \
            if res.captcha_text else ""
        say(f"  · 登录墙：自动登录成功，拿到 {res.cookies} 个 cookie{extra}")
    else:
        hint = "（可在设置面板手填验证码图片地址，或改用浏览器 Cookie 导入）" \
            if res.captcha_seen else ""
        say(f"  · 登录墙：自动登录失败 —— {res.message}{hint}")
    return res


def begin_login(session: "AuthSession", service: str, *,
                settings: AuthSettings | None = None, on_captcha=None
                ) -> tuple[LoginForm, str, str]:
    """打开登录页，并（如果有验证码）试一次自动识别。

    返回 `(form, captcha_text, error)`。调用方拿到 form 后：
      · `captcha_text` 非空 → 直接 `session.submit_login(form, u, p, captcha_text)`；
      · 为空但 `form.captcha_field` 非空 → 把 `form` 留着，让人照着验证码图填一次
        （Web 设置面板就是这么做的），或换一张重试。

    单独拆出来是为了「全自动」和「人工兜底」两条路共用同一套表单解析。
    """
    s = settings or SETTINGS
    form = session.open_login_form(service, settings=s)
    if not form.ok or not form.captcha_field:
        return form, "", ""
    ch = form.challenge or CaptchaChallenge(field=form.captcha_field)
    if not ch.has_image:
        return form, "", ch.error or "没能拿到验证码图片"
    if not s.ocr_captcha:
        return form, "", "设置里关掉了验证码 OCR"
    text, err = solve_captcha(ch.image, ch, settings=s)
    if not text and on_captcha is not None:
        text = str(on_captcha(ch) or "").strip()
    return form, text, ("" if text else (err or "OCR 没认出验证码"))


# --------------------------------------------------------------------------- #
# 给采集层用的默认会话（惰性、单例）
# --------------------------------------------------------------------------- #
_DEFAULT: AuthSession | None = None


def default_session() -> AuthSession:
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = AuthSession()
    return _DEFAULT


def login_hint() -> str:
    if cookie_file().is_file():
        return f"已保存会话 {cookie_file()}（过期就重新 login）"
    user, pw = load_credentials()
    if user and pw and SETTINGS.auto_login:
        return (f"未登录，但已保存账号 {mask_username(user)} → 采集时会自动登录"
                f"（python -m harness.cli login 也可以立刻登一次）")
    return "未登录：在 Web 设置面板「🔐 账号与登录」里填账号，或 python -m harness.cli login"


def console_warn() -> None:
    print("· 只用你自己的账号，只抓你本来就能看到的页面；"
          "Cookie 存在 .auth/（已 gitignore），别提交、别外发。", file=sys.stderr)
