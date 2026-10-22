"""问答 / 检索 / Web 启动命令。"""
from __future__ import annotations

import argparse

import sys

from ..core.config import SETTINGS
from ..corpus.store import Store
from .common import _print_answer, _trace_printer


def cmd_search(args: argparse.Namespace) -> int:
    st = Store(SETTINGS.crawl.db_path)
    hits = st.search(
        args.query, top_k=args.top_k, topic=args.topic or None,
        since=args.since or None, prefer_bio=not args.no_bio,
    )
    if not hits:
        print("没有命中。建议：确认已跑 crawl，或换用更短的关键词（2-6 字）。")
        return 1
    print(f"命中 {len(hits)} 条（库内共 {st.count_articles()} 篇）\n")
    for h in hits:
        tag = h.college or h.site_name or "-"
        print(f"[{h.article_id}] {h.title[:78]}")
        print(f"      {h.pub_date or '无日期'} · {tag} · {h.url}")
        print(f"      {h.snippet[:180]}")
        print()
    st.close()
    return 0


def cmd_ask(args: argparse.Namespace) -> int:
    from ..qa.agent import Agent
    from ..qa.llm import LLM
    from ..qa.websearch import WebSearcher
    from ..core.config import SearchSettings

    dry = bool(getattr(args, "dry_run", False))
    if not SETTINGS.llm.configured and not dry:
        print("尚未配置 LLM API key。\n两种填法： python -m wayfinder setup-key，"
              "或在 Web 界面点右上角「⚙️ 设置」\n"
              "（想先不花 token 验证抓取与检索，可加 --dry-run）", file=sys.stderr)
        return 2

    st = Store(SETTINGS.crawl.db_path)
    n = st.count_articles()
    if n == 0:
        print("库内还没有语料。请先运行： python -m wayfinder crawl --scope narrow", file=sys.stderr)
        return 2

    llm = LLM(SETTINGS.llm)
    searcher = WebSearcher(SearchSettings.from_env())
    if not searcher.available:
        print("[提示] 公网搜索已关闭，仅使用校内语料。\n", file=sys.stderr)

    agent = Agent(st, llm, searcher, SETTINGS)
    print(f"问题：{args.question}\n库内文章 {n} 篇｜模型 {SETTINGS.llm.model}｜"
          f"公网搜索 {searcher.provider}"
          f"{'｜DRY-RUN（不调用 LLM）' if dry else ''}\n", file=sys.stderr)
    ans = agent.answer(args.question, max_rounds=args.rounds,
                       trace=None if args.quiet else _trace_printer, dry_run=dry)

    if dry:
        print("=" * 78)
        print(f"DRY-RUN：检索到 {len(ans.evidence)} 条证据（未调用 LLM）\n")
        print(agent.build_citations(ans))
        cards = ans.cards or {}
        print("=" * 78)
        stats = cards.get("stats") or {}
        if stats.get("activities") or stats.get("files"):
            print(f"\n卡片：活动 {stats.get('activities', 0)} 张"
                  f"（命中已核验名录 {stats.get('matched', 0)}）"
                  f"｜附件 {stats.get('files', 0)} 个｜关键时间 {stats.get('times', 0)} 条")
            for a in (cards.get("activities") or []):
                sc = a.get("scores") or {}
                pts = []
                if sc.get("best_zongce"):
                    pts.append(f"综测 +{sc['best_zongce']:g}")
                if sc.get("best_tuimian"):
                    pts.append(f"推免 +{sc['best_tuimian']:g}")
                dl = next((t["date"] for t in (a.get("times") or [])
                           if t.get("is_deadline")), "")
                print(f"  · {a.get('name','')}"
                      f"{'｜' + '、'.join(pts) if pts else '｜（未匹配名录，无分值）'}"
                      f"{'｜截止 ' + dl if dl else ''}")
            for f in (cards.get("files") or []):
                print(f"  📎 {f.get('file_name','')}（{f.get('file_label', f.get('file_kind',''))}）{f.get('url','')}")
        if args.show_prompt:
            print("\n最终 Prompt（%d 字符）：\n" % len(ans.prompt))
            print(ans.prompt[:12000])
        else:
            print(f"\n最终 Prompt 共 {len(ans.prompt)} 字符（加 --show-prompt 可打印）")
        if args.json:
            Path(args.json).write_text(json.dumps({
                "question": ans.question, "answer": "",
                "subqueries": ans.subqueries, "error": "",
                "cards": cards,
                "evidence": [e.__dict__ for e in ans.evidence],
            }, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"已写出 JSON：{args.json}", file=sys.stderr)
        st.close()
        return 0

    _print_answer(ans)
    print(llm.usage.line(), file=sys.stderr)
    if args.json:
        Path(args.json).write_text(json.dumps({
            "question": ans.question,
            "answer": ans.text,
            "subqueries": ans.subqueries,
            "error": ans.error,
            "cards": ans.cards or {},
            "evidence": [e.__dict__ for e in ans.evidence],
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n已写出 JSON：{args.json}", file=sys.stderr)
    st.close()
    return 0 if not ans.error else 1


def cmd_web(args: argparse.Namespace) -> int:
    # Web 的装配在 app.py（组装根）；CLI 只负责把参数递过去。
    from ..app import run_web

    return run_web(host=args.host, port=args.port, open_browser=not args.no_open)
