"""命令行入口。

在仓库根目录（含 `harness/` 包的那一层）执行：

    python -m harness.cli setup-key        # 交互式写入 DeepSeek API key 并验证
    python -m harness.cli crawl --scope narrow
    python -m harness.cli search "生化大赛 报名"
    python -m harness.cli ask "生物专业可以参加什么竞赛？走什么发展路线？"
    python -m harness.cli web              # 启动简陋 Web 界面
    python -m harness.cli doctor           # 自检
"""
from __future__ import annotations

import argparse
import getpass
import json
import sys
import time
from pathlib import Path

from .config import ROOT, SETTINGS, WORKSPACE
from .store import Store

ENV_FILE = ROOT / ".env"


# --------------------------------------------------------------------------- #
def _print_answer(ans) -> None:
    if ans.error:
        print("\n[生成失败] " + ans.error, file=sys.stderr)
    print("\n" + ans.text.strip())
    print("\n" + "─" * 78)
    print("引用来源：")
    from .agent import Agent

    ag = Agent.__new__(Agent)          # 仅复用格式化方法，不重新初始化依赖
    print(ag.build_citations(ans))
    print("─" * 78)
    print(f"证据 {len(ans.evidence)} 条｜子查询 {len(ans.subqueries)} 条｜"
          f"LLM {SETTINGS.llm.model}｜{ans.error and '（生成异常）' or ''}")


def _trace_printer(step: str, data: dict) -> None:
    labels = {
        "decompose": "① 意图分解",
        "retrieve": "② 检索",
        "retrieved": "   命中",
        "gaps": "④ 缺口检测",
        "evidence": "⑥ 证据聚合",
    }
    label = labels.get(step, step)
    if step == "decompose":
        print(f"{label}：{len(data.get('subqueries', []))} 条子查询", file=sys.stderr)
        for q in data.get("subqueries", []):
            print(f"    [{q['scope']:4}] {q['query']}  ← {q.get('why','')[:40]}", file=sys.stderr)
    elif step == "retrieve":
        for q in data.get("queries", []):
            print(f"{label} 第 {data.get('round')} 轮：{q}", file=sys.stderr)
    elif step == "retrieved":
        print(f"{label} 第 {data.get('round')} 轮新增 {data.get('new')} 条"
              f"（累计 {data.get('total')}）", file=sys.stderr)
    elif step == "gaps":
        miss = data.get("missing", [])
        print(f"{label}：{'证据已足够' if not miss else str(len(miss)) + ' 个缺口'}", file=sys.stderr)
        for q in miss:
            print(f"    ↻ [{q['scope']:4}] {q['query']}", file=sys.stderr)
    elif step == "evidence":
        print(f"{label}：{data.get('count')} 条进入生成", file=sys.stderr)


# --------------------------------------------------------------------------- #
def cmd_setup_key(args: argparse.Namespace) -> int:
    from .llm import LLM
    from .config import LLMSettings

    print("配置 LLM API key（写入 %s，该文件已在 .gitignore 中）" % ENV_FILE)
    print("申请地址：https://platform.deepseek.com/api_keys\n")
    if args.key:
        key = args.key.strip()
    else:
        key = getpass.getpass("粘贴 DeepSeek API key（输入不回显）: ").strip()
    if not key:
        print("未输入 key，已取消")
        return 1
    if not key.startswith("sk-"):
        print(f"提示：key 通常以 sk- 开头，你输入的是 {key[:6]}…，仍会保存。")

    base = args.base_url or "https://api.deepseek.com"
    model = args.model or "deepseek-chat"

    print(f"\n正在用 {model} @ {base} 做一次真实调用验证…")
    llm = LLM(LLMSettings(api_key=key, base_url=base, model=model, timeout=60))
    ok, msg = llm.health()
    if not ok:
        print("❌ 验证失败：" + msg)
        print("   未写入 .env。请检查 key / 网络 / 模型名后重试。")
        return 2
    print(f"✅ 验证通过（模型回复：{msg}）")

    lines: list[str] = []
    if ENV_FILE.is_file():
        lines = [ln for ln in ENV_FILE.read_text(encoding="utf-8").splitlines()
                 if not ln.strip().startswith(("DEEPSEEK_API_KEY", "LLM_API_KEY"))]
    lines.append(f"DEEPSEEK_API_KEY={key}")
    if base != "https://api.deepseek.com":
        lines.append(f"DEEPSEEK_BASE_URL={base}")
    if model != "deepseek-chat":
        lines.append(f"DEEPSEEK_MODEL={model}")
    ENV_FILE.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
    print(f"\n已写入 {ENV_FILE}")
    print("现在可以运行： python -m harness.cli ask \"生物专业可以参加什么竞赛？\"")
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    from .config import SearchSettings
    from .llm import LLM
    from .seed import collect_sites, load_seed, stats
    from .websearch import WebSearcher

    print("=" * 70)
    print("SCAU Harness 自检")
    print("=" * 70)
    print(f"工作区      : {WORKSPACE}")
    print(f"种子文件    : {SETTINGS.seed_file}  {'✓' if SETTINGS.seed_file.is_file() else '✗ 缺失'}")
    print(f"数据库      : {SETTINGS.crawl.db_path}  "
          f"{'✓' if SETTINGS.crawl.db_path.is_file() else '（尚未创建，先跑 crawl）'}")

    if SETTINGS.seed_file.is_file():
        groups = load_seed(SETTINGS.seed_file)
        sites = collect_sites(groups)
        print(f"种子内容    : {len(groups)} 分组 / {len(sites)} 个可抓取栏目")
        from .curate import NARROW_URLS, curated, missing_from_seed

        print(f"curated     : narrow={len(curated(groups,'narrow'))} "
              f"p1={len(curated(groups,'p1'))} p2={len(curated(groups,'p2'))}")
        miss = missing_from_seed(groups)
        print(f"narrow 自检 : {'✓ 全部 %d 条命中种子' % len(NARROW_URLS) if not miss else '✗ 未命中: ' + str(miss)}")

    if SETTINGS.crawl.db_path.is_file():
        st = Store(SETTINGS.crawl.db_path)
        s = st.stats()
        print(f"库内文章    : {s['articles']} 篇（带日期 {s['with_date']}）"
              f"｜栏目 {s['sites']}｜栏目级错误 {s['site_errors']}")
        st.close()

    print(f"\nLLM         : {SETTINGS.llm.model} @ {SETTINGS.llm.base_url}")
    print(f"凭据        : {'✓ 已配置' if SETTINGS.llm.configured else '✗ 未配置 → 运行 cli setup-key'}")
    if SETTINGS.llm.configured and not args.no_llm:
        llm = LLM(SETTINGS.llm)
        ok, msg = llm.health()
        print(f"连通性      : {'✅ ' + msg if ok else '❌ ' + msg}")

    searcher = WebSearcher(SearchSettings.from_env())
    print(f"公网搜索    : provider={searcher.provider} "
          f"{'（不需要 key）' if searcher.provider == 'bing' else ''}"
          f"{'（已关闭，仅用校内语料）' if not searcher.available else ''}")
    if args.test_web and searcher.available:
        t0 = time.time()
        res = searcher.search("全国大学生生命科学竞赛 官网", top_k=3)
        print(f"  实测 {len(res)} 条 / {time.time()-t0:.1f}s")
        for r in res:
            print(f"    {r.title[:50]} → {r.url[:70]}")
    print("=" * 70)
    return 0


def cmd_crawl(args: argparse.Namespace) -> int:
    from .crawl import main as crawl_main

    argv = ["--scope", args.scope]
    for u in args.url or []:
        argv += ["--url", u]
    if args.limit:
        argv += ["--limit", str(args.limit)]
    if args.max_pages:
        argv += ["--max-pages", str(args.max_pages)]
    if args.max_articles:
        argv += ["--max-articles", str(args.max_articles)]
    if args.concurrency:
        argv += ["--concurrency", str(args.concurrency)]
    if args.no_robots:
        argv += ["--no-robots"]
    if args.reset:
        argv += ["--reset"]
    return crawl_main(argv)


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
    from .agent import Agent
    from .llm import LLM
    from .websearch import WebSearcher
    from .config import SearchSettings

    dry = bool(getattr(args, "dry_run", False))
    if not SETTINGS.llm.configured and not dry:
        print("尚未配置 LLM API key。\n请先运行： python -m harness.cli setup-key\n"
              "（想先不花 token 验证抓取与检索，可加 --dry-run）", file=sys.stderr)
        return 2

    st = Store(SETTINGS.crawl.db_path)
    n = st.count_articles()
    if n == 0:
        print("库内还没有语料。请先运行： python -m harness.cli crawl --scope narrow", file=sys.stderr)
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
        print("=" * 78)
        if args.show_prompt:
            print("\n最终 Prompt（%d 字符）：\n" % len(ans.prompt))
            print(ans.prompt[:12000])
        else:
            print(f"\n最终 Prompt 共 {len(ans.prompt)} 字符（加 --show-prompt 可打印）")
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
            "evidence": [e.__dict__ for e in ans.evidence],
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n已写出 JSON：{args.json}", file=sys.stderr)
    st.close()
    return 0 if not ans.error else 1
    if args.json:
        Path(args.json).write_text(json.dumps({
            "question": ans.question,
            "answer": ans.text,
            "subqueries": ans.subqueries,
            "error": ans.error,
            "evidence": [e.__dict__ for e in ans.evidence],
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n已写出 JSON：{args.json}", file=sys.stderr)
    st.close()
    return 0 if not ans.error else 1


def cmd_web(args: argparse.Namespace) -> int:
    from .web import serve

    return serve(host=args.host, port=args.port, open_browser=not args.no_open)


# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="harness", description="SCAU 站点群 LLM 检索 Harness",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("setup-key", help="交互式配置 LLM API key（写入 harness/.env）")
    p.add_argument("--key", help="直接传入 key（不回显输入时用）")
    p.add_argument("--base-url", help="OpenAI 兼容端点，默认 https://api.deepseek.com")
    p.add_argument("--model", help="模型名，默认 deepseek-chat")
    p.set_defaults(func=cmd_setup_key)

    p = sub.add_parser("doctor", help="自检环境/种子/数据库/LLM 连通性")
    p.add_argument("--no-llm", action="store_true", help="跳过 LLM 连通性测试")
    p.add_argument("--test-web", action="store_true", help="实测公网搜索")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("crawl", help="按范围抓取 SCAU 栏目群")
    p.add_argument("--scope", default="narrow", choices=["narrow", "p1", "p2", "all"])
    p.add_argument("--url", action="append", help="额外指定栏目列表页（可多次）")
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--max-pages", type=int, default=0)
    p.add_argument("--max-articles", type=int, default=0)
    p.add_argument("--concurrency", type=int, default=0)
    p.add_argument("--no-robots", action="store_true")
    p.add_argument("--reset", action="store_true")
    p.set_defaults(func=cmd_crawl)

    p = sub.add_parser("search", help="只在已抓语料里做全文检索（不调用 LLM）")
    p.add_argument("query")
    p.add_argument("--top-k", type=int, default=10)
    p.add_argument("--topic", default="")
    p.add_argument("--since", default="", help="ISO 日期，只返回此日期之后发布的")
    p.add_argument("--no-bio", action="store_true", help="不做生物相关学院加权")
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("ask", help="提问（多轮检索 + 带引用生成）")
    p.add_argument("question")
    p.add_argument("--rounds", type=int, default=None, help="缺口补检索轮数，默认取配置")
    p.add_argument("--quiet", action="store_true", help="不打印中间过程")
    p.add_argument("--json", help="把完整结果写到指定 JSON 文件")
    p.add_argument("--dry-run", action="store_true",
                   help="不调用 LLM，只跑检索并打印证据与最终 Prompt（省 token 排错用）")
    p.add_argument("--show-prompt", action="store_true", help="--dry-run 时打印完整 Prompt")
    p.set_defaults(func=cmd_ask)

    p = sub.add_parser("web", help="启动 Web 界面")
    p.add_argument("--host", default=SETTINGS.host)
    p.add_argument("--port", type=int, default=SETTINGS.port)
    p.add_argument("--no-open", action="store_true", help="不自动打开浏览器")
    p.set_defaults(func=cmd_web)

    return ap


def _use_safe_console() -> None:
    """避免 Windows 本地控制台（cp936/GBK）因 ✓ ✗ 之类字符直接崩溃。

    只放宽编码错误策略，不强行改成 UTF-8：中文在 GBK 控制台上仍能正常显示，
    无法编码的符号退化成 '?'，而不是抛 UnicodeEncodeError 中断整个命令。
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")  # type: ignore[union-attr]
        except (AttributeError, OSError, ValueError):
            pass


def main(argv: list[str] | None = None) -> int:
    _use_safe_console()
    ap = build_parser()
    args = ap.parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except KeyboardInterrupt:
        print("\n已中断", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
