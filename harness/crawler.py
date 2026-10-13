"""采集层：列表页发现 → 正文抓取 → 解析入库（指南 §5.3–§5.5）。

设计取舍：
  · 用 ThreadPool（而非 asyncio）因为 urllib 是阻塞的、站点是 IO 密集；
    单站并发受 Fetcher 的 per-host 限速保护，保持礼貌抓取。
  · 每个栏目：抓列表首页 → 读「尾页」得 max_page → 抓前 N 页 → 收集正文链接
    → 按标题相关度+日期排序 → 截断到单栏目上限 → 抓正文 → 去重入库。
  · 已入库的 dedupe_key 直接跳过，因此重复跑同一批栏目成本很低（增量）。
"""
from __future__ import annotations

import datetime
import re
import sys
import threading
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

from .config import CrawlSettings
from .curate import curated
from .fetcher import Fetcher, is_scau, normalize_url
from .parse import (
    KEYWORD_HINTS,
    ListItem,
    dedupe_key,
    page_urls,
    parse_article,
    parse_list,
)
from .seed import Group, Site, college_of, load_seed
from .store import Store

ProgressFn = Callable[[str], None]


@dataclass
class CrawlReport:
    sites_total: int = 0
    sites_ok: int = 0
    sites_failed: int = 0
    list_pages: int = 0
    articles_seen: int = 0
    articles_new: int = 0
    articles_updated: int = 0
    articles_skipped: int = 0
    articles_failed: int = 0
    started: str = ""
    finished: str = ""
    errors: list[tuple[str, str]] = field(default_factory=list)
    per_site: list[tuple[str, int]] = field(default_factory=list)

    def summary(self) -> str:
        secs = 0.0
        try:
            t0 = datetime.datetime.fromisoformat(self.started)
            t1 = datetime.datetime.fromisoformat(self.finished)
            secs = (t1 - t0).total_seconds()
        except Exception:
            pass
        return (
            f"栏目 {self.sites_ok}/{self.sites_total} ok（失败 {self.sites_failed}）｜"
            f"列表页 {self.list_pages}｜发现文章 {self.articles_seen}｜"
            f"新增 {self.articles_new}｜更新 {self.articles_updated}｜"
            f"跳过(已存在) {self.articles_skipped}｜正文失败 {self.articles_failed}｜"
            f"耗时 {secs/60:.1f} 分钟"
        )


def relevance(title: str) -> int:
    """标题命中关键词数，用于决定单栏目内的抓取优先级。"""
    return sum(1 for k in KEYWORD_HINTS if k in title)


# 登录墙识别（指南 §12.4）：有些公开列表页里的正文链接会 302 到 CAS 登录，
# 实测 xtw.scau.edu.cn 的文章页就是这样——返回的是登录页 HTML，
# 若不拦截会被当成「内容很短的文章」入库，污染语料。
LOGIN_HOSTS = ("cas.scau.edu.cn", "portal.scau.edu.cn", "xxgk.scau.edu.cn",
               "iap.scau.edu.cn", "sso.scau.edu.cn")
LOGIN_PATH_HINTS = ("/lyuapserver/login", "/login", "/cas/login", "/authserver",
                    "service=", "ticket=")


def looks_like_login(url: str) -> bool:
    if not url:
        return False
    low = url.lower()
    if any(h in low for h in LOGIN_HOSTS):
        return True
    return any(h in low for h in LOGIN_PATH_HINTS)


class Crawler:
    def __init__(
        self,
        store: Store,
        settings: CrawlSettings,
        *,
        progress: ProgressFn | None = None,
        check_robots: bool = True,
    ) -> None:
        self.store = store
        self.s = settings
        self.fetcher = Fetcher(
            user_agent=settings.user_agent,
            timeout=settings.timeout,
            retries=settings.retries,
            delay=settings.delay,
            jitter=settings.jitter,
        )
        self.progress = progress or (lambda msg: None)
        self.check_robots = check_robots
        self._print_lock = threading.Lock()

    # ------------------------------------------------------------------ #
    def _say(self, msg: str) -> None:
        with self._print_lock:
            self.progress(msg)

    # ------------------------------------------------------------------ #
    def discover(self, site: Site) -> tuple[list[ListItem], int, str]:
        """抓列表页并抽条目。返回 (items, max_page, final_url)。"""
        first = self.fetcher.fetch(site.url, check_robots=self.check_robots)
        if not first.ok:
            return [], 0, ""
        if looks_like_login(first.final_url or ""):
            return [], 0, first.final_url or ""     # 登录墙栏目：直接放弃，不反复重试
        parsed = parse_list(first.text, first.final_url or site.url)
        max_page = min(max(parsed.max_page, 1), self.s.max_pages_per_column)
        items = list(parsed.items)

        if max_page > 1:
            extra_urls = page_urls(first.final_url or site.url, max_page)[1:]
            with ThreadPoolExecutor(max_workers=min(self.s.concurrency, len(extra_urls))) as ex:
                futs = {ex.submit(self.fetcher.fetch, u, self.check_robots): u for u in extra_urls}
                for fut in as_completed(futs):
                    try:
                        res = fut.result()
                    except Exception:
                        continue
                    if not res.ok:
                        continue
                    p2 = parse_list(res.text, res.final_url or futs[fut])
                    items.extend(p2.items)

        # 去重（按 a{ID}）
        seen, uniq = set(), []
        for it in items:
            k = it.dedupe_key
            if k in seen:
                continue
            seen.add(k)
            uniq.append(it)
        return uniq, max_page, first.final_url or site.url

    # ------------------------------------------------------------------ #
    def _select(self, items: list[ListItem], site: Site) -> list[ListItem]:
        """同站过滤 + 时间窗过滤 + 相关度/日期排序 + 单栏目截断。"""
        host = urllib.parse.urlsplit(site.url).netloc.lower()
        cutoff = datetime.date.today() - datetime.timedelta(days=365 * max(self.s.recent_years, 1))
        keep: list[ListItem] = []
        for it in items:
            if not is_scau(it.url):          # 域名白名单（指南 §12.3-18）
                continue
            if urllib.parse.urlsplit(it.url).netloc.lower() != host:
                continue                     # 不跨站
            # 有时间就按时间窗过滤；没时间的（列表页没写日期）保守保留
            if it.pub_date and it.pub_date < cutoff:
                continue
            keep.append(it)

        fallback = datetime.date.today() - datetime.timedelta(days=365 * 4)
        keep.sort(
            key=lambda it: (
                -relevance(it.title),
                -(it.pub_date.toordinal() if it.pub_date else fallback.toordinal()),
            )
        )
        return keep[: self.s.max_articles_per_column]

    # ------------------------------------------------------------------ #
    def crawl_site(self, site: Site, report: CrawlReport) -> None:
        sid = self.store.upsert_site(site)
        items, max_page, final_url = self.discover(site)
        if looks_like_login(final_url) and not items:
            report.sites_failed += 1
            report.errors.append((site.url, "login_required"))
            self.store.upsert_site(site, error="login_required")
            self.store.log_crawl(site.url, "login_required", error="redirected_to_login")
            self._say(f"  ⊘ {site.name[:34]:<36} 需登录，已跳过")
            return
        if max_page == 0 and not items:
            report.sites_failed += 1
            report.errors.append((site.url, "list_unreachable"))
            self.store.upsert_site(site, error="list_unreachable")
            self.store.log_crawl(site.url, "list_fail", error="list_unreachable")
            self._say(f"  ✗ {site.name[:34]:<36} 列表页不可达")
            return

        report.sites_ok += 1
        report.list_pages += max_page
        self.store.upsert_site(site, max_page=max_page, final_url=final_url)
        if final_url != site.url:
            self.store.log_crawl(site.url, "redirect", error="", ms=0)

        chosen = self._select(items, site)
        report.articles_seen += len(chosen)
        host = urllib.parse.urlsplit(site.url).netloc.lower()

        todo: list[ListItem] = []
        for it in chosen:
            if self.store.has_article(it.dedupe_key):
                report.articles_skipped += 1
            else:
                todo.append(it)

        new_n = 0
        if todo:
            with ThreadPoolExecutor(max_workers=self.s.concurrency) as ex:
                futs = {ex.submit(self._fetch_one, it, site, host): it for it in todo}
                for fut in as_completed(futs):
                    it = futs[fut]
                    try:
                        ok, changed = fut.result()
                    except Exception as e:
                        ok, changed = False, False
                        self.store.log_crawl(it.url, "parse_fail", error=type(e).__name__)
                    if not ok:
                        report.articles_failed += 1
                    elif changed:
                        new_n += 1
                        report.articles_new += 1
                    else:
                        report.articles_updated += 1

        report.per_site.append((site.name or site.url, new_n))
        self._say(
            f"  ✓ {site.name[:34]:<36} 页{max_page:<3} 候选{len(chosen):<4} 新增{new_n:<4}"
            f" 跳过{len(chosen)-len(todo)}"
        )

    def _fetch_one(self, item: ListItem, site: Site, host: str) -> tuple[bool, bool]:
        res = self.fetcher.fetch(item.url, check_robots=self.check_robots)
        if not res.ok:
            self.store.log_crawl(item.url, "http_error", error=res.error, ms=int(res.elapsed * 1000))
            return False, False
        if looks_like_login(res.final_url or "") or looks_like_login(item.url):
            self.store.log_crawl(item.url, "login_required", http_code=res.status,
                                 error="redirected_to_login")
            return False, False
        art = parse_article(res.text, res.final_url or item.url)
        if art.is_noise or len(art.body) < self.s.min_body_chars:
            self.store.log_crawl(item.url, "empty", http_code=res.status, ms=int(res.elapsed * 1000))
            return False, False
        title = art.title or item.title
        pub = art.pub_date or item.pub_date
        _, changed = self.store.upsert_article(
            dedupe_key=item.dedupe_key,
            site_id=self.store.conn.execute(
                "SELECT id FROM site WHERE list_url=?", (site.url,)
            ).fetchone()["id"],
            url=item.url,
            title=title,
            body=art.body,
            pub_date=pub.isoformat() if pub else "",
            author=art.author,
            attachments=art.attachments,
            topic=site.topic,
            college=college_of(host),
            site_host=host,
            http_status=res.status,
            keywords=relevance(title),
        )
        self.store.log_crawl(item.url, "ok", http_code=res.status, nbytes=res.bytes,
                             ms=int(res.elapsed * 1000))
        return True, changed

    # ------------------------------------------------------------------ #
    def run(self, sites: Iterable[Site]) -> CrawlReport:
        sites = list(sites)
        report = CrawlReport(sites_total=len(sites), started=datetime.datetime.now().isoformat(timespec="seconds"))
        self._say(f"开始抓取 {len(sites)} 个栏目（并发 {self.s.concurrency}，单栏目上限 "
                  f"{self.s.max_pages_per_column} 页 / {self.s.max_articles_per_column} 篇）")
        for i, site in enumerate(sites, 1):
            self._say(f"[{i}/{len(sites)}] {site.site} {site.name[:40]}")
            try:
                self.crawl_site(site, report)
            except Exception as e:
                report.sites_failed += 1
                report.errors.append((site.url, f"{type(e).__name__}: {e}"))
                self._say(f"  ✗ {site.url} 异常 {type(e).__name__}: {e}")
        report.finished = datetime.datetime.now().isoformat(timespec="seconds")
        self._say("抓取完成：" + report.summary())
        return report


def load_scope(seed_path: Path, scope: str) -> list[Site]:
    groups = load_seed(seed_path)
    return curated(groups, scope)
