"""命令行入口。

在仓库根目录（含 `harness/` 包的那一层）执行：

    python -m harness.cli setup-key        # 交互式写入 DeepSeek API key 并验证
    python -m harness.cli crawl --scope narrow
    python -m harness.cli search "生化大赛 报名"
    python -m harness.cli ask "生物专业可以参加什么竞赛？走什么发展路线？"
    python -m harness.cli web              # 启动 Web 界面（含计算器页面）
    python -m harness.cli doctor           # 自检

计算器（不花 token、不联网，只读 data/calc/*.json）：

    python -m harness.cli calc                            # 数据自检
    python -m harness.cli gpa --score C3001=88 --score B2001=76
    python -m harness.cli gpa --scores my.json -v --all
    python -m harness.cli goals --scores my.json --cohort 120 --rank 18
    python -m harness.cli goals --scores my.json --activity biosci-competition:三等奖
    python -m harness.cli activities --category 学科竞赛
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

    # 计算器数据自检：它不依赖网络与数据库，坏了要第一时间知道
    try:
        from .calc import Calculator

        calc = Calculator()
        n_courses = sum(len(m.courses) for m in calc.majors)
        print(f"计算器      : ✓ {len(calc.majors)} 专业 / {n_courses} 门课 / "
              f"{len(calc.goals)} 条门槛 / {len(calc.activities)} 项活动")
        if calc.data.warnings:
            for w in calc.data.warnings:
                print(f"  ⚠️ {w}")
    except Exception as e:
        print(f"计算器      : ✗ 数据装载失败 {type(e).__name__}: {e}")
        print("              仓库自带的数据在 calcdata/；"
              "本地覆盖放 data/calc/")

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
# 计算器（绩点 / 德育 / 综测）
# --------------------------------------------------------------------------- #
def _calc_profile(args: argparse.Namespace):
    """把 CLI 参数变成 Profile。成绩可以传 JSON 文件或 `课程代码=分数` 列表。"""
    from .calc import Profile

    scores: dict[str, object] = {}
    if getattr(args, "scores", None):
        scores.update(json.loads(Path(args.scores).read_text(encoding="utf-8")))
    for item in (getattr(args, "score", None) or []):
        if "=" in item:
            code, _, val = item.partition("=")
            val = val.strip()
            try:
                scores[code.strip()] = float(val)
            except ValueError:
                scores[code.strip()] = val      # 五级制，如 G1201=优秀
    metrics: dict[str, float] = {}
    for item in (getattr(args, "metric", None) or []):
        if "=" in item:
            key, _, val = item.partition("=")
            try:
                metrics[key.strip()] = float(val)
            except ValueError:
                pass
    return Profile(
        major_id=getattr(args, "major", "") or "",
        scores=scores, metrics=metrics,
        cohort_size=int(getattr(args, "cohort", 0) or 0),
        rank=int(getattr(args, "rank", 0) or 0),
    )


def _calc_basket(args: argparse.Namespace):
    from .calc import BasketItem

    items = []
    for raw in (getattr(args, "activity", None) or []):
        # 形式：活动ID[:名次][x份数]
        qty = 1
        if "x" in raw:
            raw, _, q = raw.rpartition("x")
            try:
                qty = max(1, int(q))
            except ValueError:
                qty = 1
        aid, _, achieve = raw.partition(":")
        items.append(BasketItem(activity_id=aid.strip(), achieve=achieve.strip(),
                                quantity=qty))
    return items


def cmd_gpa(args: argparse.Namespace) -> int:
    from .calc import Calculator

    calc = Calculator()
    res = calc.evaluate(_calc_profile(args), _calc_basket(args))
    g = res.gpa

    print("=" * 74)
    print(f"专业：{res.major.name if res.major else '（未指定，用 --major 指定）'}")
    print("=" * 74)
    print(f"  平均学分绩点      : {g.gpa:.4f}")
    print(f"  保研用学业绩点    : {g.ranking_gpa:.4f}"
          f"（{g.ranking_credits:g} 学分计入排名）")
    print(f"  加权平均分        : {g.avg_score:.2f}")
    # 这里的分母是「培养方案文件里列出的所有课程」的学分合计，可能大于官方
    # 毕业总学分——因为选修课都列进去了，而一个学生不会全选。所以标签写清楚，
    # 免得和毕业门槛的 160 学分混淆。
    print(f"  已获学分 / 列表学分: {g.credits_earned:g} / {g.credits_total:g}"
          f"（{g.progress * 100:.1f}%）")
    print(f"  计入绩点学分      : {g.credits_graded:g}，未出成绩 {g.credits_remaining:g}")
    print(f"  不及格课程        : {len(g.failed)} 门")
    if g.gpa_from_retakes:
        print(f"  重修/补考课程      : {g.gpa_from_retakes} 门（已按封顶口径计入）")

    if args.verbose:
        print("\n课程明细：")
        print(f"  {'代码':<8}{'课程':<30}{'学分':>6}{'成绩':>8}{'绩点':>8}{'计入':>6}")
        for c in g.courses:
            if c.gp is None and not args.all:
                continue
            mark = "是" if c.counted else "否"
            egp = "—" if c.effective_gp is None else f"{c.effective_gp:.2f}"
            if c.raw is None:
                raw_txt = "—"
            elif isinstance(c.raw, float) and abs(c.raw - round(c.raw)) < 1e-9:
                raw_txt = str(int(round(c.raw)))
            else:
                raw_txt = str(c.raw)
            print(f"  {c.code:<8}{c.name[:28]:<30}{c.credits:>6g}"
                  f"{raw_txt:>8}{egp:>8}{mark:>6}"
                  + (f"   {c.note}" if c.note else ""))
    print("=" * 74)
    return 0


def cmd_goals(args: argparse.Namespace) -> int:
    from .calc import Calculator

    calc = Calculator()
    res = calc.evaluate(_calc_profile(args), _calc_basket(args))
    d = res.as_dict()

    print("=" * 74)
    print(f"门槛对照｜绩点 {d['gpa']['gpa']:.4f}｜综测 {d['comprehensive']['total']:.2f}"
          f"｜已获学分 {d['gpa']['credits_earned']:g}/{d['gpa']['credits_total']:g}")
    print("=" * 74)

    for g in d["goals"]:
        status = ("✅ 已达标" if g["hard_passed"] is True else
                  "❌ 未达标" if g["hard_passed"] is False else "❓ 待补数据")
        if not args.all and g["hard_passed"] is True:
            continue
        print(f"\n【{g['name']}】{status}")
        if g["summary"]:
            print(f"  {g['summary']}")
        for c in g["checks"]:
            mark = ("✅" if c["passed"] is True else
                    "❌" if c["passed"] is False else "❓")
            if c["passed"] is True and not args.all:
                continue
            actual = "未填" if c["actual"] is None else f"{c['actual']:g}"
            line = (f"  {mark} {c['label']}：{actual} / 要求 {c['op']} "
                    f"{c['required']:g}")
            if c["gap"]:
                line += f"   ← 还差 {c['gap']:g}"
            print(line)
            if c["note"] and args.verbose:
                print(f"        说明：{c['note']}")
            if c["source"] and args.verbose:
                print(f"        出处：{c['source']}")
        for key, bd in (g["breakdowns"] or {}).items():
            print(f"\n  ── 要在毕业时达到 {key} 的绩点 ──")
            print(f"     {bd['message']}")
            if bd.get("difficulty_note"):
                print(f"     {bd['difficulty_note']}")
            if args.verbose and bd["per_course"]:
                print(f"     剩余 {len(bd['per_course'])} 门课，"
                      f"每门至少 {bd['required_remaining_score']:g} 分：")
                for pc in bd["per_course"]:
                    print(f"       [{pc['term']:>2}] {pc['name'][:26]:<28}"
                          f"{pc['credits']:>5g} 学分 → {pc['required_score']:g} 分")
    print("\n" + "=" * 74)
    return 0


def cmd_activities(args: argparse.Namespace) -> int:
    from .calc import Calculator

    calc = Calculator()
    preview = calc.basket.preview_all()
    print("=" * 74)
    print(f"可加分活动清单：共 {len(calc.activities)} 项"
          f"（下面列的是各项最高可能得分）")
    print("=" * 74)

    rows = []
    for act in calc.activities:
        if args.category and act.category != args.category:
            continue
        if args.level and act.level != args.level:
            continue
        best, best_ach = 0.0, ""
        for ach, info in (preview.get(act.id) or {}).items():
            if info["total"] > best:
                best, best_ach = info["total"], ach
        if args.scored_only and best <= 0:
            continue
        rows.append((act, best, best_ach))

    for act, best, best_ach in sorted(rows, key=lambda r: -r[1]):
        flag = {"verified": "✓", "provisional": "~",
                "unverified": "?", "adjustable": "*"}.get(act.confidence, " ")
        print(f"\n[{flag}] {act.name}")
        print(f"    类别 {act.category}｜级别 {act.level}"
              f"｜最高 +{best:g} 分（{best_ach}）")
        if act.organizer:
            print(f"    主办：{act.organizer}")
        if act.timing:
            print(f"    时间：{act.timing}")
        if act.url:
            print(f"    入口：{act.url}")
        if act.source:
            print(f"    依据：{act.source}")
        print(f"    加入活动篮： --activity {act.id}:{best_ach or '参与'}")
    print("\n" + "-" * 74)
    print("可信度标记：✓ 已核验分值  ~ 有依据未逐条核验  ? 加分值未证实  * 估算值")
    print("=" * 74)
    return 0


def cmd_calc(args: argparse.Namespace) -> int:
    """打印计算器的数据自检与口径摘要。"""
    from .calc import Calculator

    calc = Calculator()
    g = calc.rules.gpa
    print("=" * 74)
    print("计算器数据自检")
    print("=" * 74)
    print(f"  专业      : {', '.join(m.name + '(' + m.id + ')' for m in calc.majors)}")
    print(f"  课程      : " + "；".join(
        f"{m.name} {len(m.courses)} 门/{m.total_credits:g} 学分" for m in calc.majors))
    print(f"  门槛      : {len(calc.goals)} 条路线（"
          + "、".join(g2.name for g2 in calc.goals[:4])
          + ("…）" if len(calc.goals) > 4 else "）"))
    print(f"  活动      : {len(calc.activities)} 项")
    print(f"  绩点折算  : {g.name}，上限 {g.max_gp:g}，"
          f"{len(g.bands)} 个区间，不及格线 {g.fail_score:g}")
    print(f"  重修口径  : {g.retake_policy}，封顶 {g.retake_cap:g} 绩点")
    dims = calc.rules.comprehensive.get("dimensions") or []
    print("  综测构成  : " + " + ".join(
        f"{d.get('name')}({d.get('cap'):g}分, 加分上限{d.get('bonus_cap'):g})"
        for d in dims))
    print("  加分通道  : " + ", ".join(
        calc.rules.comprehensive.get("channel_metrics") or {}))
    routing = calc.rules.comprehensive.get("bonus_routing") or {}
    print("  进综测的分项通道: " + ", ".join(
        f"{k}→{v}" for k, v in routing.items() if v not in ("none",)))
    print("  不进综测的通道  : " + ", ".join(
        k for k, v in routing.items() if v == "none"))
    if calc.data.warnings:
        print("\n  ⚠️ 数据校验警告：")
        for w in calc.data.warnings:
            print("     - " + w)
    else:
        print("\n  ✅ 计算器数据校验通过，无警告")

    dirs = calc.data.meta.get("dirs") or {}
    if dirs:
        from pathlib import Path as _P

        override = [k for k, v in dirs.items()
                    if "data" in _P(v).parts and "calc" in _P(v).parts]
        print(f"\n  数据目录  : {'calcdata/（仓库自带，进 git）'}")
        if override:
            print(f"  本地覆盖  : data/calc/ 覆盖了 {len(override)}/"
                  f"{len(dirs)} 个文件（"
                  + "、".join(sorted(override)) + "）")
    print("=" * 74)
    return 0


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

    # ---------------- 计算器（绩点 / 德育 / 综测） ---------------- #
    def _add_calc_inputs(sp):
        sp.add_argument("--major", choices=["biotech", "bioscience"],
                        default="biotech", help="专业：biotech=生物技术，bioscience=生物科学")
        sp.add_argument("--scores", help="成绩 JSON 文件：{\"课程代码\": 分数}")
        sp.add_argument("--score", action="append", metavar="代码=分数",
                        help="单门成绩，可重复；也支持五级制，如 --score G1201=优秀")
        sp.add_argument("--metric", action="append", metavar="指标=数值",
                        help="其他指标，如 --metric cet4_score=452 --metric pe_pass=1")
        sp.add_argument("--cohort", type=int, default=0, help="专业总人数（算排名百分位用）")
        sp.add_argument("--rank", type=int, default=0, help="我的名次")
        sp.add_argument("--activity", action="append", metavar="活动ID[:名次][x份数]",
                        help="加入活动篮，如 --activity biosci-competition:三等奖 "
                             "--activity volunteer-service:参与x3")

    p = sub.add_parser("gpa", help="算平均学分绩点（可带活动篮）")
    _add_calc_inputs(p)
    p.add_argument("-v", "--verbose", action="store_true", help="打印逐门课程明细")
    p.add_argument("--all", action="store_true", help="连同未出成绩的课一起打印")
    p.set_defaults(func=cmd_gpa)

    p = sub.add_parser("goals", help="对照保研/考研/奖学金门槛，并给出课程目标分")
    _add_calc_inputs(p)
    p.add_argument("-v", "--verbose", action="store_true",
                   help="打印每条门槛的说明、出处，以及逐门课程的目标分")
    p.add_argument("--all", action="store_true", help="连已达标项也打印")
    p.set_defaults(func=cmd_goals)

    p = sub.add_parser("activities", help="列出全部可加分活动与加分依据")
    p.add_argument("--category", default="", help="只看某个类别")
    p.add_argument("--level", default="", help="只看某个级别")
    p.add_argument("--scored-only", action="store_true", help="只看有分值依据的")
    p.set_defaults(func=cmd_activities)

    p = sub.add_parser("calc", help="计算器数据自检：专业/课程/门槛/活动/口径")
    p.set_defaults(func=cmd_calc)

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
