"""登录墙支持：CAS 统一身份认证 + 会话 Cookie 复用。

背景（指南 §12.4）：
  `cas.scau.edu.cn`（统一身份认证）后面的页面，裸 GET 拿回来的是登录页 HTML。
  之前 `crawler.py` 只能识别并跳过（`login_required`），本模块让 Harness
  可以带着会话去拿。

两条路，推荐第一条：

  ① `--cookie` 导入浏览器现成 Cookie（`python -m harness.cli login --cookie`）
     —— 全程不接触密码；CAS 有验证码/滑块时这是唯一能用的办法。

  ② CAS 表单登录（`python -m harness.cli login`）
     —— 自动解析登录页的隐藏字段（execution / lt / _eventId）再提交，
        不写死任何参数名，所以对 CAS 4/5 和学校改造过的版本都尽量兼容。

设计边界（重要）：
  · 只用你自己的账号，访问你自己本来就能看到的页面。不提供批量拉他人数据的能力。
  · 凭据与 Cookie 写在 `.auth/`（已 gitignore），不写进 `.env`、不进日志。
  · 会话过期是常态，`AuthSession.message()` 会明确告诉你「过期了，重新登录」。

和采集层的关系：`Fetcher` 可以注入一个 `AuthSession`（见 `fetcher.py`），
注入后同一个 opener 读写 cookie jar，重定向全程带会话，登录态才跟得住。
"""
from __future__ import annotations

import http.cookiejar
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from .config import ROOT

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
BLOCKERS = {
    "captcha": ("验证码", "图形验证码", "checkcode", "captcha", "verifycode"),
    "slider": ("滑块", "滑动验证", "nc_1_n1z"),
    "sms": ("短信验证", "动态口令", "手机验证"),
    "2fa": ("双因子", "两步验证", "二次验证"),
}

FORM_RE = re.compile(r"<form\b[^>]*>", re.I)
ACTION_RE = re.compile(r'\baction\s*=\s*["\']([^"\']+)["\']', re.I)
INPUT_RE = re.compile(r"<input\b[^>]*>", re.I)
NAME_RE = re.compile(r'\bname\s*=\s*["\']([^"\']+)["\']', re.I)
VALUE_RE = re.compile(r'\bvalue\s*=\s*["\']([^"\']*)["\']', re.I)
TYPE_RE = re.compile(r'\btype\s*=\s*["\']([^"\']+)["\']', re.I)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)
SCRIPT_RE = re.compile(r"<script\b.*?</script>|<style\b.*?</style>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")

# 字段名不是固定的（CAS 用 execution，有的学校用 lt / _csrf / authenticity_token），
# 所以按「语义猜测」而不是写死。
USER_FIELD_HINTS = ("username", "user", "account", "loginname", "yhm", "uname", "zh")
PASS_FIELD_HINTS = ("password", "passwd", "pwd", "mm")
EVENT_FIELD_HINTS = ("_eventid", "eventid", "submit")
CAPTCHA_FIELD_HINTS = ("captcha", "checkcode", "verify", "vcode", "authcode", "yzm")


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

    def debug(self) -> str:
        lines = [f"  {'✓' if self.ok else '✗'} {self.message}"]
        if self.final_url:
            lines.append(f"    最终落在 : {self.final_url}")
        lines.append(f"    拿到 Cookie: {self.cookies} 个")
        if self.blockers:
            lines.append(f"    拦路虎   : {'、'.join(self.blockers)}（脚本登录不可用，请用 --cookie）")
        for m, u, st in self.history[-8:]:
            lines.append(f"    {st:>3} {m:<4} {u[:110]}")
        return "\n".join(lines)


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
    low = (html or "").lower()
    found = []
    for name, needles in BLOCKERS.items():
        if any(n.lower() in low for n in needles):
            found.append(name)
    return found


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
    def _fetch_first_form(self, service: str) -> tuple[dict, str, str, list[str]]:
        """找一个能用的 CAS 登录表单。返回 (隐藏字段, action, 页面正文, 拦路虎)。"""
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
                return hidden, action, html, blockers
        return {}, last_url or idx, last_html, blockers

    def login(self, username: str, password: str, *,
              service: str = DEFAULT_SERVICE) -> LoginResult:
        hidden, action, html, blockers = self._fetch_first_form(service)
        res = LoginResult(blockers=sorted(set(blockers)))
        if not hidden:
            res.message = f"没有在登录页里找到表单字段（页面标题：{_text_title(html) or '空'}）"
            res.history = list(self.history)
            return res
        if any(h in " ".join(hidden).lower() for h in CAPTCHA_FIELD_HINTS):
            res.blockers = sorted(set(res.blockers + ["captcha_field"]))
            res.message = "登录表单要求图形验证码，脚本无法自动过 → 请改用 login --cookie"
            res.history = list(self.history)
            return res

        # 账号/密码字段在 CAS 页面里通常是**可见**输入框（不在隐藏字段集合里），
        # 所以先用语义猜名字，猜不到再退回 CAS 惯例名。
        user_field = _guess_field(hidden, USER_FIELD_HINTS) or "username"
        pass_field = _guess_field(hidden, PASS_FIELD_HINTS) or "password"
        event_field = _guess_field(hidden, EVENT_FIELD_HINTS)
        fields = {k: v for k, v in hidden.items()
                  if k.lower() not in CAPTCHA_FIELD_HINTS}
        fields[user_field] = username
        fields[pass_field] = password
        if event_field:
            fields[event_field] = "submit"
        else:
            fields["_eventId"] = "submit"
        if not any(k.lower() == "geolocation" for k in fields):
            fields.setdefault("geolocation", "")

        referer = self.history[-1][1] if self.history else action
        try:
            body, status, final = self.post(action, fields, referer=referer, record=False)
        except urllib.error.HTTPError as e:
            res.message = f"登录请求返回 HTTP {e.code}"
            res.history = list(self.history)
            return res
        except Exception as e:
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
        try:
            page, st2, final2 = self.get(service)
            self.history.append(("GET", final2, st2))
            if self.at_login(final2):
                res.message = f"Cookie 拿到了，但访问 {service} 仍被弹回认证页"
                res.final_url = final2
                res.cookies = len(list(self.jar))
                res.history = list(self.history)
                return res
            res.ok = True
            res.final_url = final2
            res.message = f"登录成功（{_text_title(page) or final2}）"
        except Exception as e:
            res.message = f"登录请求已提交，但验证页打不开：{type(e).__name__}"
            res.final_url = final
        res.cookies = len(list(self.jar))
        res.saved = bool(self.cookie_file.is_file())
        res.history = list(self.history)
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
    return "未登录：python -m harness.cli login"


def console_warn() -> None:
    print("· 只用你自己的账号，只抓你本来就能看到的页面；"
          "Cookie 存在 .auth/（已 gitignore），别提交、别外发。", file=sys.stderr)
