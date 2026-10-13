"""公网搜索适配器（指南 §8.1 步骤③）。

校内站点只覆盖「本校怎么组织、往年谁获奖」，赛事规则/含金量/最新时间表
往往只在公网。因此 harness 需要一条联网搜索通道。

支持四种后端，按可用性自动选择：
  ddg    —— DuckDuckGo Lite（默认，无需 key，实测中文结果质量好）
  bocha  —— 博查搜索（国内 API，需 BOCHA_API_KEY，最稳定）
  tavily —— Tavily（需 TAVILY_API_KEY）
  bing   —— 解析 Bing 结果页（无需 key，但本机实测结果相关度差，仅作备用）
  none   —— 关闭公网检索（仅用校内语料）

注意：ddg / bing 都是解析 HTML 结果页，页面结构变化就会失效；要长期稳定
建议配一个搜索 API key（provider=bocha 或 tavily）。
"""
from __future__ import annotations

import base64
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

from .config import SearchSettings
from .fetcher import _SSL_CTX, decode_bytes

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")

# --- DuckDuckGo Lite ---
DDG_LINK_RE = re.compile(
    r"<a[^>]+href=\"([^\"]+)\"[^>]*class=['\"]result-link['\"][^>]*>(.*?)</a>", re.I | re.S
)
DDG_SNIPPET_RE = re.compile(
    r"<td[^>]*class=['\"]result-snippet['\"][^>]*>(.*?)</td>", re.I | re.S
)

# --- Bing ---
BING_RESULT_RE = re.compile(
    r'<li class="b_algo".*?<h2>\s*<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>.*?</h2>(.*?)</li>',
    re.I | re.S,
)
BING_CITE_RE = re.compile(r'<div class="b_caption".*?<p[^>]*>(.*?)</p>', re.I | re.S)
BING_ANY_LINK_RE = re.compile(r'<h2>\s*<a[^>]+href="(https?://[^"]+)"[^>]*>(.*?)</a>', re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")


@dataclass
class WebResult:
    title: str
    url: str
    snippet: str = ""
    source: str = "web"


def _clean(fragment: str) -> str:
    import html as htmlmod

    text = TAG_RE.sub(" ", fragment or "")
    text = htmlmod.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _unwrap_bing(url: str) -> str:
    """Bing 有时给 /ck/a?...&u=a1aHR0cHM... 的跳转链接，解出真实地址。"""
    if "bing.com/ck/a" not in url:
        return url
    try:
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
        u = (q.get("u") or [""])[0]
        if u.startswith("a1"):
            pad = u[2:] + "=" * (-len(u[2:]) % 4)
            return base64.urlsafe_b64decode(pad).decode("utf-8", "ignore")
    except Exception:
        pass
    return url


def _unwrap_ddg(url: str) -> str:
    """DDG 给的是 //duckduckgo.com/l/?uddg=<urlencoded> 跳转，解出真实地址。"""
    if "duckduckgo.com/l/" not in url and not url.startswith("//duckduckgo"):
        return url if url.startswith("http") else "https:" + url
    full = url if url.startswith("http") else "https:" + url
    try:
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(full).query)
        return (q.get("uddg") or [url])[0]
    except Exception:
        return url


@dataclass
class WebSearcher:
    settings: SearchSettings
    usage: dict = field(default_factory=lambda: {"calls": 0, "results": 0, "errors": 0})

    @property
    def provider(self) -> str:
        return (self.settings.provider or "none").lower()

    @property
    def available(self) -> bool:
        return self.provider != "none"

    # ------------------------------------------------------------------ #
    def search(self, query: str, top_k: int | None = None) -> list[WebResult]:
        q = (query or "").strip()
        if not q or not self.available:
            return []
        k = top_k or self.settings.top_k
        self.usage["calls"] += 1
        out: list[WebResult] = []
        try:
            if self.provider == "bocha":
                out = self._bocha(q, k)
            elif self.provider == "tavily":
                out = self._tavily(q, k)
            elif self.provider == "bing":
                out = self._bing(q, k)
            else:
                out = self._ddg(q, k)
        except Exception:
            self.usage["errors"] += 1
            out = []
        # ddg/bing 是 HTML 解析，主通道失败时互备一次
        if not out and self.provider in ("ddg", "bing"):
            try:
                out = self._bing(q, k) if self.provider == "ddg" else self._ddg(q, k)
            except Exception:
                out = []
        self.usage["results"] += len(out)
        return out[:k]

    # ------------------------------------------------------------------ #
    def _ddg(self, query: str, k: int) -> list[WebResult]:
        url = "https://lite.duckduckgo.com/lite/?" + urllib.parse.urlencode(
            {"q": query, "kl": "cn-zh"}
        )
        req = urllib.request.Request(url, headers={
            "User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9",
        })
        with urllib.request.urlopen(req, timeout=self.settings.timeout, context=_SSL_CTX) as r:
            raw = r.read()
            html, _ = decode_bytes(raw, r.headers.get("Content-Type", ""))

        links = DDG_LINK_RE.findall(html)
        snippets = DDG_SNIPPET_RE.findall(html)
        out: list[WebResult] = []
        for i, (href, title) in enumerate(links[: max(k * 2, 10)]):
            real = _unwrap_ddg(href)
            if not real.startswith("http"):
                continue
            out.append(WebResult(
                title=_clean(title),
                url=real,
                snippet=_clean(snippets[i]) if i < len(snippets) else "",
            ))
        return out

    # ------------------------------------------------------------------ #
    def _bing(self, query: str, k: int) -> list[WebResult]:
        url = "https://cn.bing.com/search?" + urllib.parse.urlencode(
            {"q": query, "setlang": "zh-CN", "count": str(max(k, 10))}
        )
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/122.0 Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9",
        })
        with urllib.request.urlopen(req, timeout=self.settings.timeout, context=_SSL_CTX) as r:
            raw = r.read()
            html, _ = decode_bytes(raw, r.headers.get("Content-Type", ""))

        results: list[WebResult] = []
        for m in BING_RESULT_RE.finditer(html):
            href = _unwrap_bing(m.group(1))
            if not href.startswith("http"):
                continue
            snippet = ""
            cm = BING_CITE_RE.search(m.group(3))
            if cm:
                snippet = _clean(cm.group(1))
            if not snippet:
                snippet = _clean(m.group(3))[:300]
            results.append(WebResult(title=_clean(m.group(2)), url=href, snippet=snippet))
        if not results:                      # 结构变化时退一步：只抓标题+链接
            for m in BING_ANY_LINK_RE.finditer(html):
                href = _unwrap_bing(m.group(1))
                if href.startswith("http"):
                    results.append(WebResult(title=_clean(m.group(2)), url=href, snippet=""))
        return results

    def _bocha(self, query: str, k: int) -> list[WebResult]:
        url = (self.settings.base_url or "https://api.bochaai.com") + "/v1/web-search"
        body = json.dumps({"query": query, "count": k, "summary": True}).encode()
        req = urllib.request.Request(url, data=body, headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.settings.api_key}",
        })
        with urllib.request.urlopen(req, timeout=self.settings.timeout, context=_SSL_CTX) as r:
            data = json.loads(r.read().decode("utf-8", "ignore"))
        pages = (((data.get("data") or {}).get("webPages") or {}).get("value")) or []
        out = []
        for p in pages[:k]:
            out.append(WebResult(
                title=p.get("name", ""),
                url=p.get("url", ""),
                snippet=(p.get("summary") or p.get("snippet") or "")[:400],
            ))
        return out

    def _tavily(self, query: str, k: int) -> list[WebResult]:
        url = (self.settings.base_url or "https://api.tavily.com") + "/search"
        body = json.dumps({
            "api_key": self.settings.api_key,
            "query": query,
            "max_results": k,
            "search_depth": "basic",
        }).encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=self.settings.timeout, context=_SSL_CTX) as r:
            data = json.loads(r.read().decode("utf-8", "ignore"))
        return [
            WebResult(title=x.get("title", ""), url=x.get("url", ""),
                      snippet=(x.get("content") or "")[:400])
            for x in (data.get("results") or [])[:k]
        ]
