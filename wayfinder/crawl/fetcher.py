"""HTTP 抓取层：纯 urllib（沙箱内 curl/schannel 不可用，Python 自带 OpenSSL 正常）。

要点（指南 §3.2 / §5.7 / §12.2）：
  · 所有 URL 规范化成 https 再入队，避免 http↔https 互跳造成的“重复失败”
  · 显式跟随重定向并记录最终 URL（大量 list.htm → list.psp 的 301）
  · 中文站点编码混杂（utf-8 / gb18030），按 http header → meta → 探测 逐级判定
  · 限速 + 重试，保持礼貌抓取
"""
from __future__ import annotations

import gzip
import io
import random
import re
import ssl
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from dataclasses import dataclass, field

CHARSET_RE = re.compile(rb'charset\s*=\s*["\']?\s*([A-Za-z0-9_\-]+)', re.I)
META_RE = re.compile(
    rb'<meta[^>]+(?:http-equiv\s*=\s*["\']?content-type["\']?[^>]*content\s*=\s*["\'][^"\']*charset=([A-Za-z0-9_\-]+)'
    rb'|charset\s*=\s*["\']?([A-Za-z0-9_\-]+))',
    re.I,
)

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE


@dataclass
class FetchResult:
    url: str
    final_url: str = ""
    status: int = 0
    ok: bool = False
    text: str = ""
    encoding: str = ""
    error: str = ""
    elapsed: float = 0.0
    bytes: int = 0
    from_cache: bool = False
    content_type: str = ""

    @property
    def redirected(self) -> bool:
        return bool(self.final_url) and self.final_url != self.url


from ..core.urls import is_loopback, normalize_url


def is_scau(url: str) -> bool:
    """校内白名单（指南 §12.3-18：外链混排要过滤）。"""
    host = urllib.parse.urlsplit(url).netloc.lower().split(":")[0]
    return host == "scau.edu.cn" or host.endswith(".scau.edu.cn")


def decode_bytes(raw: bytes, content_type: str = "") -> tuple[str, str]:
    """按 header → meta → 编码探测 的顺序解码，中文站点不能只信 utf-8。"""
    candidates: list[str] = []
    if content_type:
        m = CHARSET_RE.search(content_type.encode("latin-1", "ignore"))
        if m:
            candidates.append(m.group(1).decode("latin-1"))
    head = raw[:4096]
    for m in META_RE.finditer(head):
        name = (m.group(1) or m.group(2) or b"").decode("latin-1", "ignore")
        if name:
            candidates.append(name)
    candidates += ["utf-8", "gb18030", "big5", "latin-1"]

    seen = set()
    for enc in candidates:
        enc = enc.strip().lower()
        if not enc or enc in seen:
            continue
        seen.add(enc)
        try:
            return raw.decode(enc), enc
        except (UnicodeDecodeError, LookupError):
            continue
    return raw.decode("utf-8", "ignore"), "utf-8(replace)"


def _decompress(raw: bytes, encoding: str) -> bytes:
    enc = (encoding or "").lower()
    try:
        if enc == "gzip":
            return gzip.decompress(raw)
        if enc == "deflate":
            try:
                return zlib.decompress(raw)
            except zlib.error:
                return zlib.decompress(raw, -zlib.MAX_WBITS)
        if enc == "br":
            try:
                import brotli  # type: ignore

                return brotli.decompress(raw)
            except Exception:
                return raw
    except Exception:
        return raw
    return raw


class Fetcher:
    """带限速、重试、内存缓存与 robots 检查的抓取器。

    线程安全：内部用锁串行化“限速等待”，因此可在 ThreadPool 中共享。
    """

    def __init__(
        self,
        user_agent: str,
        timeout: int = 30,
        retries: int = 2,
        delay: float = 0.8,
        jitter: float = 0.7,
        cache_enabled: bool = True,
        auth_session=None,
    ) -> None:
        self.user_agent = user_agent
        self.timeout = timeout
        self.retries = retries
        self.delay = delay
        self.jitter = jitter
        self.cache_enabled = cache_enabled
        # 可选：登录会话（wayfinder.crawl.auth.AuthSession）。带会话时重定向全程有 cookie，
        # 登录墙后面的页面才拿得到（指南 §12.4）。
        self.auth = auth_session
        self._cache: dict[str, FetchResult] = {}
        self._bin_cache: dict[str, dict] = {}          # 附件二进制（按需，默认不缓存）
        self._last: dict[str, float] = {}          # 按域名限速
        self._lock = threading.Lock()
        self._robots: dict[str, set[str]] = {}
        self._robots_ok: dict[str, bool] = {}
        self.stats = {"requests": 0, "cache_hits": 0, "errors": 0, "bytes": 0,
                      "auth_requests": 0}

    # ---------- robots ----------
    def _robots_disallow(self, url: str) -> set[str]:
        p = urllib.parse.urlsplit(url)
        base = f"{p.scheme}://{p.netloc}"
        if base in self._robots:
            return self._robots[base]
        disallow: set[str] = set()
        try:
            with self._open(base + "/robots.txt", timeout=min(self.timeout, 12)) as r:
                raw = r.read()
            text = decode_bytes(raw, r.headers.get("Content-Type", ""))[0]
            applies = False
            for line in text.splitlines():
                line = line.split("#", 1)[0].strip()
                if not line or ":" not in line:
                    continue
                k, _, v = line.partition(":")
                k, v = k.strip().lower(), v.strip()
                if k == "user-agent":
                    applies = v == "*" or "scau-research" in v.lower()
                elif k == "disallow" and applies and v:
                    disallow.add(v)
            self._robots_ok[base] = True
        except Exception:
            self._robots_ok[base] = False      # 拿不到 robots 视为允许
        self._robots[base] = disallow
        return disallow

    def robots_allows(self, url: str) -> bool:
        p = urllib.parse.urlsplit(url)
        for pat in self._robots_disallow(url):
            if pat == "/":
                return False
            if p.path.startswith(pat):
                return False
        return True

    # ---------- core ----------
    def _throttle(self, url: str) -> None:
        host = urllib.parse.urlsplit(url).netloc
        with self._lock:
            now = time.time()
            wait = 0.0
            last = self._last.get(host, 0.0)
            gap = self.delay + random.uniform(0, self.jitter)
            if last and now - last < gap:
                wait = gap - (now - last)
            self._last[host] = now + wait
        if wait > 0:
            time.sleep(wait)

    def _open(self, url: str, timeout: int | None = None, use_auth: bool = False):
        t = timeout or self.timeout
        if use_auth and self.auth is not None:
            # 走会话的 opener：cookie 读写、重定向跟随都在同一个 jar 里完成
            self.stats["auth_requests"] += 1
            return self.auth.request(url, "GET", timeout=t)
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.6",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "close",
            },
        )
        return urllib.request.urlopen(req, timeout=t, context=_SSL_CTX)

    def fetch(self, url: str, check_robots: bool = True, *,
              use_auth: bool = False, force: bool = False) -> FetchResult:
        url = normalize_url(url)
        if not url:
            return FetchResult(url=url, error="empty_url")

        if not force and self.cache_enabled and url in self._cache:
            self.stats["cache_hits"] += 1
            cached = self._cache[url]
            return FetchResult(**{**cached.__dict__, "from_cache": True})

        # 带会话时不再看 robots：抓的是自己账号本来就能看的页面，
        # 而且登录态下 robots.txt 通常也取不到、判定没有意义。
        if check_robots and not use_auth and not self.robots_allows(url):
            return FetchResult(url=url, error="robots_disallow")

        last_err = ""
        for attempt in range(self.retries + 1):
            self._throttle(url)
            t0 = time.time()
            self.stats["requests"] += 1
            try:
                with self._open(url, use_auth=use_auth) as r:
                    raw = r.read()
                    raw = _decompress(raw, r.headers.get("Content-Encoding", ""))
                    ctype = r.headers.get("Content-Type", "")
                    text, enc = decode_bytes(raw, ctype)
                    res = FetchResult(
                        url=url,
                        final_url=r.geturl(),
                        status=getattr(r, "status", 200),
                        ok=True,
                        text=text,
                        encoding=enc,
                        elapsed=time.time() - t0,
                        bytes=len(raw),
                        content_type=ctype,
                    )
                    self.stats["bytes"] += len(raw)
                    if self.cache_enabled:
                        self._cache[url] = res
                    return res
            except urllib.error.HTTPError as e:
                last_err = f"http_{e.code}"
                if e.code in (404, 403, 401, 410):
                    break                      # 不重试
                if e.code in (429, 503, 502, 504):
                    time.sleep(1.5 * (attempt + 1))
            except urllib.error.URLError as e:
                last_err = f"urlerror_{type(e.reason).__name__}" if hasattr(e, "reason") else "urlerror"
            except Exception as e:              # 含 IncompleteRead / SSLError / timeout
                last_err = f"{type(e).__name__}"
                if "IncompleteRead" in type(e).__name__:
                    break                      # 旧版页 IncompleteRead：内容已部分拿到，重试无用
            if attempt < self.retries:
                time.sleep(0.6 * (attempt + 1))

        self.stats["errors"] += 1
        return FetchResult(url=url, error=last_err or "unknown", final_url=url)

    # ---------- 缓存 ----------
    def forget(self, url: str) -> None:
        """丢掉某个 URL 的内存缓存。

        登录墙场景要用：第一次拿回来的是登录页 HTML（被缓存了），
        自动登录成功之后必须真的重发一次请求，否则读到的还是那份登录页。
        """
        key = normalize_url(url) or url
        self._cache.pop(key, None)
        self._bin_cache.pop("bin:" + key, None)

    # ---------- 二进制下载（附件：pdf/docx/xlsx/图片…） ----------
    def fetch_bytes(self, url: str, *, max_bytes: int = 25_000_000,
                    check_robots: bool = False, use_auth: bool = False,
                    force: bool = False, binary_cache: bool = False) -> dict:
        """下载二进制内容，返回 dict（不抛异常）。

        `fetch()` 会把响应体当文本解码，附件必须先拿原始字节——PDF/Office 被
        utf-8 解一遍再解回来是不可逆的。这里独立一条路径：
          · Content-Length 超过 max_bytes 直接拒（省流量）
          · 流式累积，超过 max_bytes 立即中断（防止服务器不报长度）
          · 只按需缓存（附件默认不入内存缓存，一次抓取里靠 URL/sha1 去重）
          · 默认不查 robots：附件是文章正文里链出来的子资源，正文已经查过，
            再为每个附件拉一份 robots.txt 既慢又容易被误判（可显式打开）。
        """
        url = normalize_url(url)
        out = {"url": url, "ok": False, "data": b"", "error": "", "status": 0,
               "content_type": "", "content_disposition": "", "final_url": url,
               "bytes": 0, "elapsed": 0.0}
        if not url:
            out["error"] = "empty_url"
            return out
        key = "bin:" + url
        if binary_cache and not force and self.cache_enabled:
            hit = self._bin_cache.get(key)
            if hit is not None:
                self.stats["cache_hits"] += 1
                return dict(hit)
        if check_robots and not use_auth and not self.robots_allows(url):
            out["error"] = "robots_disallow"
            return out

        last_err = ""
        t0 = time.time()
        for attempt in range(self.retries + 1):
            self._throttle(url)
            self.stats["requests"] += 1
            try:
                with self._open(url, use_auth=use_auth) as r:
                    ctype = r.headers.get("Content-Type", "") or ""
                    cdisp = r.headers.get("Content-Disposition", "") or ""
                    try:
                        declared = int(r.headers.get("Content-Length") or 0)
                    except ValueError:
                        declared = 0
                    if declared and declared > max_bytes:
                        out["error"] = f"too_large({declared})"
                        return out
                    chunks: list[bytes] = []
                    got = 0
                    while True:
                        piece = r.read(65536)
                        if not piece:
                            break
                        got += len(piece)
                        if got > max_bytes:
                            out["error"] = f"too_large(>{max_bytes})"
                            return out
                        chunks.append(piece)
                    raw = b"".join(chunks)
                    raw = _decompress(raw, r.headers.get("Content-Encoding", ""))
                    out.update({
                        "ok": True, "data": raw, "status": getattr(r, "status", 200),
                        "content_type": ctype, "content_disposition": cdisp,
                        "final_url": r.geturl(), "bytes": len(raw),
                        "elapsed": time.time() - t0,
                    })
                    self.stats["bytes"] += len(raw)
                    if binary_cache and self.cache_enabled:
                        self._bin_cache[key] = dict(out)
                    return out
            except urllib.error.HTTPError as e:
                last_err = f"http_{e.code}"
                if e.code in (404, 403, 401, 410):
                    break
                if e.code in (429, 503, 502, 504):
                    time.sleep(1.5 * (attempt + 1))
            except urllib.error.URLError as e:
                last_err = f"urlerror_{type(e.reason).__name__}" if hasattr(e, "reason") else "urlerror"
            except Exception as e:                          # noqa: BLE001
                last_err = type(e).__name__
                if "IncompleteRead" in last_err:
                    break
            if attempt < self.retries:
                time.sleep(0.6 * (attempt + 1))
        self.stats["errors"] += 1
        out["error"] = last_err or "unknown"
        out["elapsed"] = time.time() - t0
        return out
