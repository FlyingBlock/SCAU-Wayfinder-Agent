"""语料维护：清理「登录墙/导航标题/空正文」造成的脏数据。

背景（实测踩到）：有些公开列表页里的正文链接会 302 到统一身份认证
（`cas.scau.edu.cn/lyuapServer/login?...`）。早期版本会把返回的登录页
HTML 当成「正文很短的文章」入库，于是库里混进了一批标题为空、
正文只有几十字的条目。另外若某模板的正文链接只有图片，标题兜底逻辑
可能把相邻的导航文字（如「发展动态」）当成标题。

用法：
    python -m wayfinder.crawl.maint audit              # 只报告，不改动
    python -m wayfinder.crawl.maint purge --dry-run    # 预览会删掉什么
    python -m wayfinder.crawl.maint purge --yes        # 实际删除
    python -m wayfinder.crawl.maint refetch --limit 50 # 重新抓取可疑条目（修正标题/正文）
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..core.config import SETTINGS
from .fetcher import Fetcher
from .parse import is_nav_title, parse_article
from ..corpus.store import Store


def _suspect_ids(store: Store, max_chars: int = 120) -> list[dict]:
    """可疑条目：正文过短、标题为空，或标题是导航词（如「发展动态」）。

    最后一类容易被漏掉：它们的正文其实很长（是真实文章），
    只是旧版解析器把侧边栏的栏目名当成了标题。
    """
    with store._lock:
        rows = store.conn.execute(
            """SELECT id, url, title, char_count, body FROM article
               WHERE char_count < ? OR title IS NULL OR title = ''
               ORDER BY id""",
            (max_chars,),
        ).fetchall()
    out = [dict(r) for r in rows]
    seen = {r["id"] for r in out}
    with store._lock:
        navrows = store.conn.execute(
            "SELECT id, url, title, char_count, body FROM article ORDER BY id"
        ).fetchall()
    for r in navrows:
        d = dict(r)
        if d["id"] not in seen and is_nav_title(d["title"] or ""):
            out.append(d)
            seen.add(d["id"])
    return out


def cmd_audit(args: argparse.Namespace) -> int:
    store = Store(SETTINGS.crawl.db_path)
    print("库内统计：", store.stats())

    with store._lock:
        nav = [dict(r) for r in store.conn.execute(
            "SELECT id, title, url FROM article").fetchall()]
    nav_bad = [r for r in nav if is_nav_title(r["title"] or "")]
    short = _suspect_ids(store)
    empty_title = [r for r in nav if not (r["title"] or "").strip()]

    print(f"\n导航标题条目 : {len(nav_bad)}")
    for r in nav_bad[:10]:
        print(f"   [{r['id']}] {r['title']!r} {r['url'][:70]}")
    print(f"\n标题为空     : {len(empty_title)}")
    for r in empty_title[:10]:
        print(f"   [{r['id']}] {r['url'][:70]}")
    print(f"\n正文过短(<120字): {len(short)}")
    for r in short[:10]:
        print(f"   [{r['id']}] chars={r['char_count']:<5} {r['url'][:66]}")

    print("\n按栏目统计正文过短的分布：")
    with store._lock:
        for r in store.conn.execute(
            """SELECT s.name, s.site, COUNT(*) c FROM article a
               LEFT JOIN site s ON s.id=a.site_id
               WHERE a.char_count < 120 GROUP BY a.site_id ORDER BY c DESC LIMIT 12"""
        ):
            print(f"   {r['c']:>4}  {r['name'] or '?'} ({r['site'] or '?'})")
    store.close()
    return 0


def cmd_purge(args: argparse.Namespace) -> int:
    store = Store(SETTINGS.crawl.db_path)
    f = Fetcher(user_agent=SETTINGS.crawl.user_agent, timeout=15, retries=0, delay=0.2, jitter=0.2)
    suspects = _suspect_ids(store)
    print(f"检查 {len(suspects)} 条可疑记录（重新抓取以判断是否登录墙）…")

    from .crawler import looks_like_login

    kill: list[tuple[int, str, str]] = []      # (id, reason, url)
    for i, r in enumerate(suspects, 1):
        title = r["title"] or ""
        if is_nav_title(title) or not title.strip():
            kill.append((r["id"], "nav_or_empty_title", r["url"]))
            continue
        try:
            res = f.fetch(r["url"], check_robots=False)
            if looks_like_login(res.final_url or "") or looks_like_login(r["url"]):
                kill.append((r["id"], "login_wall", r["url"]))
            elif not res.ok:
                kill.append((r["id"], f"fetch_{res.error}", r["url"]))
        except Exception as e:
            kill.append((r["id"], f"err_{type(e).__name__}", r["url"]))
        if i % 25 == 0:
            print(f"   …{i}/{len(suspects)}")

    print(f"\n判定应删除 {len(kill)} 条：")
    from collections import Counter

    for reason, n in Counter(k[1] for k in kill).most_common():
        print(f"   {n:>5}  {reason}")

    if args.dry_run:
        print("\n（--dry-run，未改动数据库）示例：")
        for aid, reason, url in kill[:10]:
            print(f"   [{aid}] {reason:<22} {url[:66]}")
        store.close()
        return 0
    if not kill:
        store.close()
        return 0
    if not args.yes:
        print("\n未加 --yes，未删除。确认后重跑： python -m wayfinder.crawl.maint purge --yes")
        store.close()
        return 1

    ids = [k[0] for k in kill]
    with store._lock:
        for chunk in range(0, len(ids), 400):
            part = ids[chunk:chunk + 400]
            q = ",".join("?" * len(part))
            store.conn.execute(f"DELETE FROM article_fts WHERE rowid IN ({q})", part)
            store.conn.execute(f"DELETE FROM field WHERE article_id IN ({q})", part)
            store.conn.execute(f"DELETE FROM article WHERE id IN ({q})", part)
        store.conn.commit()
    print(f"\n已删除 {len(ids)} 条。现在：", store.stats())
    store.close()
    return 0


def cmd_refetch(args: argparse.Namespace) -> int:
    """重新抓取正文过短的条目，用修正后的解析器覆盖标题/正文。"""
    store = Store(SETTINGS.crawl.db_path)
    f = Fetcher(user_agent=SETTINGS.crawl.user_agent, timeout=20, retries=1, delay=0.5, jitter=0.4)
    from .crawler import looks_like_login

    suspects = _suspect_ids(store, max_chars=args.max_chars)[: args.limit]
    print(f"重新抓取 {len(suspects)} 条…")
    fixed = removed = still = 0
    for i, r in enumerate(suspects, 1):
        res = f.fetch(r["url"], check_robots=False)
        if not res.ok or looks_like_login(res.final_url or ""):
            with store._lock:
                store.conn.execute("DELETE FROM article_fts WHERE rowid=?", (r["id"],))
                store.conn.execute("DELETE FROM article WHERE id=?", (r["id"],))
                store.conn.commit()
            removed += 1
            continue
        art = parse_article(res.text, r["url"])
        if art.is_noise or not art.title or is_nav_title(art.title):
            with store._lock:
                store.conn.execute("DELETE FROM article_fts WHERE rowid=?", (r["id"],))
                store.conn.execute("DELETE FROM field WHERE article_id=?", (r["id"],))
                store.conn.execute("DELETE FROM article WHERE id=?", (r["id"],))
                store.conn.commit()
            removed += 1
            continue
        with store._lock:
            store.conn.execute(
                "UPDATE article SET title=?, body=?, char_count=?, pub_date=COALESCE(NULLIF(?,''),pub_date) WHERE id=?",
                (art.title, art.body, len(art.body),
                 art.pub_date.isoformat() if art.pub_date else "", r["id"]),
            )
            store.conn.execute("DELETE FROM article_fts WHERE rowid=?", (r["id"],))
            from ..corpus.store import tokenize_for_index

            store.conn.execute(
                "INSERT INTO article_fts (rowid,title,body) VALUES (?,?,?)",
                (r["id"], tokenize_for_index(art.title), tokenize_for_index(art.body)),
            )
            store.conn.commit()
        fixed += 1
        if i % 20 == 0:
            print(f"   …{i}/{len(suspects)}  修正 {fixed} 删除 {removed} 仍空 {still}")
        if args.remove_nav and is_nav_title(art.title):
            with store._lock:
                store.conn.execute("DELETE FROM article_fts WHERE rowid=?", (r["id"],))
                store.conn.execute("DELETE FROM article WHERE id=?", (r["id"],))
                store.conn.commit()
            removed += 1
    print(f"\n完成：修正 {fixed}｜删除(登录墙/仍空) {removed}｜仍无正文 {still}")
    print("现在：", store.stats())
    store.close()
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="wayfinder.crawl.maint", description="语料维护")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("audit", help="只报告脏数据分布")
    p.set_defaults(func=cmd_audit)

    p = sub.add_parser("purge", help="删除登录墙/导航标题/空正文条目")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--yes", action="store_true")
    p.set_defaults(func=cmd_purge)

    p = sub.add_parser("refetch", help="重新抓取可疑条目以修正标题与正文")
    p.add_argument("--limit", type=int, default=100)
    p.add_argument("--max-chars", type=int, default=120)
    p.add_argument("--remove-nav", action="store_true", help="标题是导航词时直接删除")
    p.set_defaults(func=cmd_refetch)

    args = ap.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
