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

from ..core.config import CrawlSettings
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
from ..corpus.store import Store

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


def _attachments_default() -> bool:
    """默认是否抓附件：环境变量优先，默认开。"""
    import os

    val = (os.environ.get("ATTACH_ENABLED", "1") or "1").strip().lower()
    return val not in ("0", "false", "no", "off")


# 登录墙识别（指南 §12.4）：有些公开列表页里的正文链接会 302 到 CAS 登录，
# 实测 xtw.scau.edu.cn 的文章页就是这样——返回的是登录页 HTML，
# 若不拦截会被当成「内容很短的文章」入库，污染语料。
LOGIN_HOSTS = ("cas.scau.edu.cn", "portal.scau.edu.cn", "xxgk.scau.edu.cn",
               "iap.scau.edu.cn", "sso.scau.edu.cn")
LOGIN_PATH_HINTS = ("/lyuapserver/login", "/login", "/cas/login", "/authserver",
                    "service=", "ticket=")
# 正文里的登录页特征：有些登录墙**不改 URL**，直接原地返回登录页 HTML
# （不认出来就会被当成「很短的文章」入库，污染语料）
LOGIN_BODY_HINTS = ("lyuapserver", "cas.scau.edu.cn", "统一身份认证",
                    "统一认证登录", "yours-account-name", "请输入账号")


def looks_like_login(url: str) -> bool:
    if not url:
        return False
    low = url.lower()
    if any(h in low for h in LOGIN_HOSTS):
        return True
    return any(h in low for h in LOGIN_PATH_HINTS)


def looks_like_login_body(html: str) -> bool:
    """正文特征识别登录墙（只看开头一段，避免article 里引用到 CAS 链接就误判）。"""
    low = (html or "")[:6000].lower()
    return any(h.lower() in low for h in LOGIN_BODY_HINTS)


class Crawler:
    def __init__(
        self,
        store: Store,
        settings: CrawlSettings,
        *,
        progress: ProgressFn | None = None,
        check_robots: bool = True,
        auth_session=None,
        attachments: bool | None = None,
        attachment_settings=None,
        auto_login: bool | None = None,
    ) -> None:
        self.store = store
        self.s = settings
        # 登录会话（wayfinder.crawl.auth.AuthSession）：有它就能抓统一身份认证后面的栏目，
        # 没有就退化成原来的「识别登录墙 → 跳过」。
        self.auth = auth_session
        # 撞到登录墙时用 .auth/credentials.json 里的账号密码自动登一次（验证码走 OCR）。
        # 默认跟随 AUTH_AUTO_LOGIN；显式传 False 可关掉（照旧只跳过）。
        self.auto_login_enabled = auto_login
        self._login_lock = threading.Lock()
        self._auto_login_state = ""          # "" 未试 | "ok" | "failed"
        self.auto_login_report: dict = {}
        self.fetcher = Fetcher(
            user_agent=settings.user_agent,
            timeout=settings.timeout,
            retries=settings.retries,
            delay=settings.delay,
            jitter=settings.jitter,
            auth_session=auth_session,
        )
        self.progress = progress or (lambda msg: None)
        self.check_robots = check_robots
        self._print_lock = threading.Lock()
        # 附件下载与解析（可关：--no-attachments / ATTACH_ENABLED=0）
        self.attachment_settings = attachment_settings
        self.attachments_on = (attachments if attachments is not None
                               else _attachments_default())
        self.attachment_fetcher = None
        if self.attachments_on:
            from ..documents.attachments import AttachmentFetcher, AttachmentSettings

            self.attachment_settings = attachment_settings or AttachmentSettings.from_env()
            self.attachments_on = bool(self.attachment_settings.enabled)
            if self.attachments_on:
                self.attachment_fetcher = AttachmentFetcher(
                    self.fetcher, store, self.attachment_settings, progress=self._say)
        self.attach_report = {"files": 0, "with_text": 0, "written": 0, "bytes": 0,
                              "articles": 0, "ocr": 0}

    # ------------------------------------------------------------------ #
    @property
    def use_auth(self) -> bool:
        """会话里还有没过期的 cookie 才值得带认证发请求。"""
        return bool(self.auth is not None and self.auth.alive() > 0)

    def can_auto_login(self) -> bool:
        """能不能自动登录：会话在 + 开关开 + 真的存了账号密码。"""
        from . import auth as auth_mod

        if self.auth is None or self.auto_login_enabled is False:
            return False
        if not auth_mod.SETTINGS.auto_login:
            return False
        user, pw = auth_mod.load_credentials()
        return bool(user and pw)

    def try_auto_login(self, reason_url: str = "") -> bool:
        """撞到登录墙时的一次性自动登录。

        多个抓取线程可能同时撞墙，所以整段加锁：第一个进来的真的登一次，
        其余的等锁释放后直接读到结果，不会把学校 CAS 刷爆。
        """
        if not self.can_auto_login():
            return False
        from . import auth as auth_mod

        with self._login_lock:
            if self._auto_login_state == "ok":
                return True
            if self._auto_login_state == "failed":
                return False
            self._auto_login_state = "failed"          # 先按失败记账，成功再改写
            service = (reason_url or auth_mod.SETTINGS.service
                       or auth_mod.DEFAULT_SERVICE)
            res = auth_mod.auto_login(self.auth, service=service, progress=self._say)
            self.auto_login_report = {
                "ok": res.ok, "message": res.message,
                "captcha": res.captcha_text, "rounds": res.captcha_rounds,
                "captcha_error": res.captcha_error, "need_captcha": res.need_captcha,
            }
            self._auto_login_state = "ok" if res.ok else "failed"
            return res.ok

    # ------------------------------------------------------------------ #
    def _say(self, msg: str) -> None:
        with self._print_lock:
            self.progress(msg)

    # ------------------------------------------------------------------ #
    def discover(self, site: Site, _retried: bool = False) -> tuple[list[ListItem], int, str, bool, bool]:
        """抓列表页并抽条目。

        返回 (items, max_page, final_url, 会话已过期, 撞到登录墙)。
        """
        first = self.fetcher.fetch(site.url, check_robots=self.check_robots,
                                   use_auth=self.use_auth)
        if not first.ok:
            return [], 0, "", False, False
        if looks_like_login(first.final_url or "") or looks_like_login_body(first.text):
            if not self.use_auth and not _retried and self.try_auto_login(site.url):
                # 自动登录成功 → 带新会话把这一栏目重放一次（先丢掉那份登录页缓存）
                self.fetcher.forget(site.url)
                return self.discover(site, _retried=True)
            if self.use_auth:
                # 带了会话还被弹回认证页 → 会话过期了，不重试，直接如实上报
                return [], 0, first.final_url or "", True, True
            return [], 0, first.final_url or "", False, True   # 登录墙：放弃，不反复重试
        parsed = parse_list(first.text, first.final_url or site.url)
        max_page = min(max(parsed.max_page, 1), self.s.max_pages_per_column)
        items = list(parsed.items)

        if max_page > 1:
            extra_urls = page_urls(first.final_url or site.url, max_page)[1:]
            with ThreadPoolExecutor(max_workers=min(self.s.concurrency, len(extra_urls))) as ex:
                futs = {ex.submit(self.fetcher.fetch, u, self.check_robots,
                                  use_auth=self.use_auth): u for u in extra_urls}
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
        return uniq, max_page, first.final_url or site.url, False, False

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
        items, max_page, final_url, auth_expired, login_wall = self.discover(site)
        if auth_expired or (login_wall and not items):
            report.sites_failed += 1
            err = "auth_expired" if auth_expired else "login_required"
            report.errors.append((site.url, err))
            self.store.upsert_site(site, error=err)
            self.store.log_crawl(site.url, err,
                                 error="session_expired" if auth_expired else "redirected_to_login")
            if auth_expired:
                note = "会话已过期，请重新 login"
            elif self.auto_login_report.get("message"):
                note = f"需登录，自动登录没成（{self.auto_login_report['message'][:28]}）"
            elif self.can_auto_login():
                note = "需登录，已跳过"
            else:
                note = "需登录，已跳过（设置里填账号可自动登录）"
            self._say(f"  ⊘ {site.name[:34]:<36} {note}")
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
        res = self.fetcher.fetch(item.url, check_robots=self.check_robots,
                                 use_auth=self.use_auth)
        if not res.ok:
            self.store.log_crawl(item.url, "http_error", error=res.error, ms=int(res.elapsed * 1000))
            return False, False
        # 注意：带会话抓登录墙栏目时，正文 URL 本身可能就含 service=/ticket=，
        # 所以只看「最终落点」和正文特征是否仍是认证页，不拿 item.url 去判。
        if looks_like_login(res.final_url or "") or looks_like_login_body(res.text):
            # 正文页在墙后面（列表页公开、文章页要登录的栏目很常见）→ 自动登录后重取一次
            if not self.use_auth and self.try_auto_login(item.url):
                self.fetcher.forget(item.url)
                res = self.fetcher.fetch(item.url, check_robots=self.check_robots,
                                         use_auth=True, force=True)
                if not res.ok:
                    self.store.log_crawl(item.url, "http_error", error=res.error,
                                         ms=int(res.elapsed * 1000))
                    return False, False
                if looks_like_login(res.final_url or "") or looks_like_login_body(res.text):
                    self.store.log_crawl(item.url, "login_required", http_code=res.status,
                                         error="auto_login_insufficient")
                    return False, False
            else:
                err = "session_expired" if self.use_auth else "redirected_to_login"
                self.store.log_crawl(item.url, "login_required", http_code=res.status, error=err)
                return False, False
        art = parse_article(res.text, res.final_url or item.url)
        if art.is_noise or len(art.body) < self.s.min_body_chars:
            self.store.log_crawl(item.url, "empty", http_code=res.status, ms=int(res.elapsed * 1000))
            return False, False
        title = art.title or item.title
        pub = art.pub_date or item.pub_date
        aid, changed = self.store.upsert_article(
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
        # 附件：正文里往往只有一句「详见附件」，真正的报名截止/赛程/名额表
        # 都在 pdf/doc/xlsx 里。这里下载到 data/attachments/ 并抽文本入库，
        # 让检索与问答都能用上（失败不影响正文入库）。
        if self.attachment_fetcher is not None and art.attachments:
            self._process_attachments(aid, art.attachments)
        self.store.log_crawl(item.url, "ok", http_code=res.status, nbytes=res.bytes,
                             ms=int(res.elapsed * 1000))
        return True, changed

    def _process_attachments(self, article_id: int, urls: list[str]) -> None:
        from ..documents.attachments import persist

        try:
            items = self.attachment_fetcher.fetch_for_article(article_id, urls)
            written = persist(self.store, article_id, items)
            with self._print_lock:
                self.attach_report["articles"] += 1
                self.attach_report["files"] += len(items)
                self.attach_report["written"] += written
                self.attach_report["with_text"] += sum(1 for i in items if i.text.strip())
                self.attach_report["bytes"] += sum(i.bytes for i in items)
                self.attach_report["ocr"] += sum(i.ocr_used for i in items)
        except Exception as e:                       # noqa: BLE001 - 附件失败不该中断采集
            self.store.log_crawl(urls[0] if urls else "", "attach_fail",
                                 error=f"{type(e).__name__}: {e}")

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
        if self.auto_login_report:
            a = self.auto_login_report
            tail = f"，验证码 OCR 认成「{a['captcha']}」" if a.get("captcha") else ""
            self._say(f"自动登录：{'成功' if a.get('ok') else '失败'}"
                      f"（{a.get('message', '')}）{tail}")
        if self.attachment_fetcher is not None and self.attach_report["files"]:
            a = self.attach_report
            self._say(f"附件：{a['files']} 个（{a['with_text']} 个解析出正文"
                      f"{'，OCR ' + str(a['ocr']) + ' 张图' if a['ocr'] else ''}）"
                      f"来自 {a['articles']} 篇通知，共 "
                      f"{a['bytes'] / 1048576:.1f}MB")
        return report


def load_scope(seed_path: Path, scope: str) -> list[Site]:
    groups = load_seed(seed_path)
    return curated(groups, scope)
