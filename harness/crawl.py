"""采集入口：按 scope 抓取 SCAU 栏目群并入库。

用法（在工作区根 D:\\Documents\\Desktop\\SCAU 下执行）：
    python -m harness.crawl --scope narrow          # 42 个高信号栏目（推荐起步）
    python -m harness.crawl --scope p1              # 165 个栏目
    python -m harness.crawl --scope all             # 种子全量
    python -m harness.crawl --url https://life.scau.edu.cn/tzgg/list.htm
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from .config import SETTINGS
from .crawler import Crawler, load_scope
from .seed import Site, collect_sites, load_seed
from .store import Store


def resolve_urls(urls: list[str]) -> list[Site]:
    """给命令行传入的 URL 补上种子里的名称/主题/分组。

    不查种子的话这些栏目在报告和库里都会显示成「(命令行指定)」，
    既难读，也让 topic 过滤失效。
    """
    try:
        index = {s.url: s for s in collect_sites(load_seed(SETTINGS.seed_file),
                                                 include_single_page=True)}
    except Exception:
        index = {}

    out: list[Site] = []
    for u in urls:
        found = index.get(u)
        if found is not None:
            out.append(found)
        else:
            host = u.split("/")[2] if "//" in u else u
            out.append(Site(name=f"临时栏目 {u.rstrip('/').split('/')[-2] if '/' in u.rstrip('/') else host}",
                            url=u, site=host, kind="list", topic="general",
                            group_id="manual", group_name="命令行", priority=1))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="harness.crawl", description="SCAU 站点群定向采集")
    ap.add_argument("--scope", default="narrow", choices=["narrow", "p1", "p2", "all"],
                    help="抓取范围（默认 narrow：42 个高信号栏目）")
    ap.add_argument("--url", action="append", default=[],
                    help="直接指定栏目列表页 URL（可多次；与 --scope 叠加）")
    ap.add_argument("--limit", type=int, default=0, help="最多抓几个栏目（0=不限）")
    ap.add_argument("--max-pages", type=int, default=0, help="覆盖单栏目最大页数")
    ap.add_argument("--max-articles", type=int, default=0, help="覆盖单栏目最大文章数")
    ap.add_argument("--concurrency", type=int, default=0, help="覆盖并发数")
    ap.add_argument("--no-robots", action="store_true", help="跳过 robots.txt 检查")
    ap.add_argument("--no-auth", action="store_true",
                    help="忽略 .auth/ 里的登录会话，按未登录状态抓")
    ap.add_argument("--no-auto-login", action="store_true",
                    help="撞到登录墙时不自动登录（默认会用已保存的账号自动登录，验证码走 OCR）")
    ap.add_argument("--no-attachments", action="store_true",
                    help="不下载附件（默认会把 pdf/doc/xlsx 等附件抓到 data/attachments/ 并解析入库）")
    ap.add_argument("--attach-max-files", type=int, default=0,
                    help="覆盖单篇通知最多下载几个附件")
    ap.add_argument("--reset", action="store_true", help="抓取前清空库（谨慎：会丢弃已有语料）")
    args = ap.parse_args(argv)

    s = SETTINGS.crawl
    if args.max_pages:
        s.max_pages_per_column = args.max_pages
    if args.max_articles:
        s.max_articles_per_column = args.max_articles
    if args.concurrency:
        s.concurrency = args.concurrency

    store = Store(s.db_path)
    if args.reset:
        with store._lock:
            store.conn.executescript(
                "DELETE FROM article_fts; DELETE FROM article; DELETE FROM field; DELETE FROM crawl_log;"
            )
            store.conn.commit()
        print("已清空 article / fts / field / crawl_log")

    sites: list[Site] = [] if args.url else load_scope(SETTINGS.seed_file, args.scope)
    if args.url:
        sites.extend(resolve_urls(args.url))
    if args.limit:
        sites = sites[: args.limit]
    if not sites:
        print("没有可抓取的栏目")
        return 1

    print(f"种子={SETTINGS.seed_file.name}  scope={args.scope}  栏目数={len(sites)}  "
          f"库={s.db_path}  已有文章={store.count_articles()}")

    def progress(msg: str) -> None:
        print(msg, flush=True)

    t0 = time.time()
    # 有 .auth/ 会话就带着它抓：统一身份认证后面的栏目才拿得到（指南 §12.4）。
    # 没有 cookie 但存了账号密码时也照样建会话——Crawler 撞到登录墙会**自动登录**
    # （验证码交给 OCR），登完把 cookie 落盘，后续栏目直接复用。
    session = None
    if not args.no_auth:
        from . import auth as auth_mod

        session = auth_mod.AuthSession()
        user, pw = auth_mod.load_credentials()
        if session.alive():
            print(f"登录会话：{session.alive()} 个有效 cookie（{len(list(session.jar))} 个总计）"
                  f"，认证后的栏目会用它抓")
        elif user and pw and auth_mod.SETTINGS.auto_login:
            print(f"登录会话：无 cookie，但已保存账号 {auth_mod.mask_username(user)} → "
                  f"遇到登录墙会自动登录（{auth_mod.SETTINGS.describe()}）")
        else:
            print("登录会话：无（登录墙栏目会被跳过；要抓就先 "
                  "python -m harness.cli login，或在 Web 设置面板「🔐 账号与登录」里填账号）")
    crawler = Crawler(store, s, progress=progress, check_robots=not args.no_robots,
                      auth_session=session, attachments=not args.no_attachments,
                      auto_login=not args.no_auto_login)
    if args.attach_max_files and crawler.attachment_settings is not None:
        crawler.attachment_settings.max_files_per_article = args.attach_max_files
    if crawler.attachments_on:
        from . import docparse as docparse_mod
        from . import ocr as ocr_mod
        from .attachments import dir_stats

        astat = dir_stats(crawler.attachment_settings.dir)
        print(f"附件        : 开（{len(docparse_mod.supported_extensions())} 种格式，"
              f"上限 {crawler.attachment_settings.max_bytes_per_file // 1_000_000}MB/个，"
              f"单篇最多 {crawler.attachment_settings.max_files_per_article} 个）→ "
              f"{astat['dir']}（已有 {astat['files']} 个 / {astat['human']}）")
        print(f"OCR         : {ocr_mod.summary_line()}")
    else:
        print("附件        : 关（--no-attachments）")
    report = crawler.run(sites)

    print("\n" + "=" * 78)
    print(report.summary())
    print(f"库内文章总数：{store.count_articles()}")
    if report.errors:
        print("\n失败明细（前 25 条）：")
        for url, err in report.errors[:25]:
            print(f"  {err:<28} {url}")
    top = sorted(report.per_site, key=lambda kv: -kv[1])[:15]
    if top:
        print("\n产出最多的栏目：")
        for name, n in top:
            print(f"  {n:>5}  {name}")
    print(f"\n总耗时 {(time.time()-t0)/60:.1f} 分钟")
    store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
