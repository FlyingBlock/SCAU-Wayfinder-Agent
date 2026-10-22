"""URL 归一化：纯函数，供采集、附件、问答等层共用。

放在 `core/` 是为了避免 `documents` 反向 import `crawl.fetcher`，
让领域之间保持单向依赖。
"""
from __future__ import annotations

import urllib.parse

#: 本机地址：不强制改 https（本地假服务器/自建服务多为纯 http）。
_LOOPBACK_HOSTS = ("localhost", "127.0.0.1", "::1", "0.0.0.0")


def is_loopback(url: str) -> bool:
    host = urllib.parse.urlsplit(url).netloc.split("@")[-1].split(":")[0].lower()
    return host in _LOOPBACK_HOSTS


def normalize_url(url: str, prefer_https: bool = True) -> str:
    """统一 https、去 fragment、去跟踪参数、小写域名；保留业务 query。"""
    if not url:
        return ""
    url = url.strip()
    if url.startswith("//"):
        url = "https:" + url
    p = urllib.parse.urlsplit(url)
    scheme = p.scheme.lower()
    if prefer_https and scheme in ("http", "https") and not is_loopback(url):
        scheme = "https"
    elif not scheme:
        scheme = "https"
    netloc = p.netloc.lower()
    if not netloc:
        return ""
    if p.query:
        keep = []
        for k, v in urllib.parse.parse_qsl(p.query, keep_blank_values=True):
            if k.lower() in ("utm_source", "utm_medium", "utm_campaign",
                             "utm_term", "spm", "_t"):
                continue
            keep.append((k, v))
        query = urllib.parse.urlencode(keep)
    else:
        query = ""
    path = p.path or "/"
    return urllib.parse.urlunsplit((scheme, netloc, path, query, ""))
