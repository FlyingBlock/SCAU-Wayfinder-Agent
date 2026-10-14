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
import contextlib
import getpass
import json
import re
import sys
import time
from pathlib import Path

from .config import (
    AUTH_ENV_KEYS,
    ENV_FILE,
    LLM_ENV_KEYS,
    LLM_LEGACY_KEYS,
    OCR_ENV_KEYS,
    SETTINGS,
    WORKSPACE,
    env_file_shadowed_keys,
)
from .store import Store


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
    from .config import LLMSettings, apply_llm_settings
    from .llm import LLM

    print("配置 LLM API key（写入 %s，该文件已在 .gitignore 中）" % ENV_FILE)
    print("申请地址：https://platform.deepseek.com/api_keys")
    print("（也可以开 Web 界面点右上角「⚙️ 设置」填，效果一样）\n")
    if args.key:
        key = args.key.strip()
    else:
        key = getpass.getpass("粘贴 API key（输入不回显）: ").strip()
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

    res = apply_llm_settings(api_key=key, base_url=base, model=model)
    if res["warning"]:
        print("⚠️ " + res["warning"])
    print(f"\n已写入 {ENV_FILE}（{'、'.join(res['applied'])}）")
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
    print(f"凭据        : {'✓ 已配置' if SETTINGS.llm.configured else '✗ 未配置 → cli setup-key 或 Web 界面「⚙️ 设置」'}")
    shadowed = env_file_shadowed_keys() & set(LLM_ENV_KEYS + LLM_LEGACY_KEYS)
    if shadowed:
        print(f"  ⚠️ 系统环境变量里有 {'、'.join(sorted(shadowed))}，优先级高于 .env"
              f"（改 .env 不会生效，除非先清掉环境变量）")
    if SETTINGS.llm.configured and not args.no_llm:
        llm = LLM(SETTINGS.llm)
        ok, msg = llm.health()
        print(f"连通性      : {'✅ ' + msg if ok else '❌ ' + msg}")

    searcher = WebSearcher(SearchSettings.from_env())
    print(f"公网搜索    : provider={searcher.provider} "
          f"{'（不需要 key）' if searcher.provider == 'bing' else ''}"
          f"{'（已关闭，仅用校内语料）' if not searcher.available else ''}")

    # 附件与 OCR：附件解析是本机能力（不需要 key），OCR 才需要百度凭据
    from . import attachments as _attach
    from . import docparse as _docparse
    from . import ocr as _ocr

    a = _attach.AttachmentSettings.from_env()
    dstat = _attach.dir_stats(a.dir)
    print(f"附件解析    : {'✓ 开' if a.enabled else '✗ 关（ATTACH_ENABLED=0）'}"
          f"｜支持 {len(_docparse.supported_extensions())} 种格式"
          f"｜存放 {dstat['dir']}（{dstat['files']} 个文件 / {dstat['human']}）")
    print(f"单文件上限  : {a.max_bytes_per_file // 1_000_000}MB，单篇最多 {a.max_files_per_article} 个"
          f"｜LibreOffice {'可用' if _docparse.libreoffice_available() else '不可用（用内置解析器）'}")
    print(f"OCR         : {_ocr.summary_line()}")
    shadowed_ocr = env_file_shadowed_keys() & set(OCR_ENV_KEYS)
    if shadowed_ocr:
        print(f"  ⚠️ 系统环境变量里有 {'、'.join(sorted(shadowed_ocr))}，优先级高于 .env")
    if args.test_ocr:
        ok, msg = _ocr.health()
        print(f"OCR 实测    : {'✅ ' if ok else '❌ '}{msg}")

    # 登录墙：有会话就能抓认证后面的栏目；只有账号密码时（撞墙会自动登录）也报出来
    from . import auth as _auth

    sess = _auth.AuthSession()
    _user, _pw = _auth.load_credentials()
    if sess.alive():
        print(f"登录会话    : ✓ {sess.alive()} 个有效 cookie（{_auth.COOKIE_FILE.name}）"
              f"，crawl 会带着它抓认证栏目")
    elif _auth.COOKIE_FILE.is_file():
        print("登录会话    : ⚠️ 有 cookie 文件但已全部过期 → python -m harness.cli login")
    else:
        print("登录会话    : ✗ 未登录（{0}）".format(_auth.login_hint()))
    if _user and _pw:
        print(f"账号凭据    : ✓ 已保存 {_auth.mask_username(_user)}"
              f"（{_auth.CRED_FILE.name}，仅当前用户可读、不进 git）")
    else:
        print("账号凭据    : ✗ 未保存（Web 设置面板「🔐 账号与登录」里填，"
              "撞到登录墙就能自动登录）")
    print(f"自动登录    : {_auth.SETTINGS.describe()}")
    if _auth.SETTINGS.ocr_captcha and not _ocr.SETTINGS.configured:
        print("              ⚠️ 开了验证码 OCR 但 OCR 没配置 → 遇到验证码只能手填，"
              "或改用 login --cookie")
    shadowed_auth = env_file_shadowed_keys() & set(AUTH_ENV_KEYS)
    if shadowed_auth:
        print(f"              ⚠️ 系统环境变量里有 {'、'.join(sorted(shadowed_auth))}，"
              f"优先级高于 .env")
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
    if args.no_attachments:
        argv += ["--no-attachments"]
    if getattr(args, "no_auto_login", False):
        argv += ["--no-auto-login"]
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
        print("尚未配置 LLM API key。\n两种填法： python -m harness.cli setup-key，"
              "或在 Web 界面点右上角「⚙️ 设置」\n"
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
                print(f"  📎 {f.get('file_name','')}（{f.get('file_kind','')}）{f.get('url','')}")
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

    if getattr(args, "refresh", False):
        rc = cmd_competitions_refresh(args)
        if rc != 0:
            return rc

    calc = Calculator()
    preview = calc.basket.preview_all()
    kind = getattr(args, "list", "all") or "all"
    counts = (calc.data.competitions or {}).get("counts") or {}
    print("=" * 74)
    print(f"可加分活动清单：共 {len(calc.activities)} 项"
          + (f"（其中具体赛事 {counts.get('total', 0)} 项："
             f"T {counts.get('T', 0)} / A {counts.get('A', 0)} / B {counts.get('B', 0)}"
             + (f"，联网新增 {counts['online_added']} 项" if counts.get("online_added") else "")
             + "）" if counts else ""))
    print("（下面列的是各项最高可能得分）")
    print("=" * 74)

    rows = []
    for act in calc.activities:
        if kind == "competition" and act.list_kind == "general":
            continue
        if kind == "general" and act.list_kind != "general":
            continue
        if args.category and act.category != args.category:
            continue
        if args.level and act.level != args.level:
            continue
        best, best_ach = 0.0, ""
        best_tm, best_ach_tm = 0.0, ""
        for ach, info in (preview.get(act.id) or {}).items():
            if info["total"] > best:
                best, best_ach = info["total"], ach
            if info.get("total_tuimian", 0) > best_tm:
                best_tm, best_ach_tm = info["total_tuimian"], ach
        if args.scored_only and best <= 0 and best_tm <= 0:
            continue
        rows.append((act, best, best_ach, best_tm, best_ach_tm))

    # 具体赛事按名录序号排（跟官方名录同序），通用加分项按分值排
    if kind == "competition":
        rows.sort(key=lambda r: (r[0].extra.get("appendix", 0),
                                 r[0].extra.get("seq", 0)))
    else:
        rows.sort(key=lambda r: -max(r[1], r[3]))

    for act, best, best_ach, best_tm, best_ach_tm in rows:
        flag = {"verified": "✓", "provisional": "~",
                "unverified": "?", "adjustable": "*"}.get(act.confidence, " ")
        ex = act.extra or {}
        head = ""
        if act.list_kind != "general" and ex.get("seq") is not None:
            head = f"#{ex['seq']} [{ex.get('tier', '')} 类·附录{ex.get('appendix', '')}] "
        print(f"\n[{flag}] {head}{act.name}")
        score = f"最高 综测 +{best:g} 分（{best_ach}）"
        if best_tm > 0:
            score += f"｜推免 +{best_tm:g} 分（{best_ach_tm}）"
        print(f"    类别 {act.category}｜级别 {act.level}｜{score}"
              + (f"｜档位 {ex.get('profile_label', '')}" if ex.get("profile_label") else "")
              + ("｜联网新增" if ex.get("online") else ""))
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


def cmd_competitions_refresh(args: argparse.Namespace) -> int:
    """联网刷新赛事名录（活动篮页面上那个「🔄 刷新联网」的命令行版本）。"""
    from .calc import online as calc_online

    print("=" * 74)
    print("刷新赛事名录（抓学校官网 → 与内置 calcdata/competitions.json 对账）")
    print("=" * 74)
    res = calc_online.refresh(timeout=int(getattr(args, "timeout", 12) or 12))
    for s in res.get("sources", []):
        mark = "✔" if s.get("ok") else "✘"
        print(f"  {mark} [{s.get('kind')}] {s.get('title')}"
              f"  HTTP {s.get('status')} · {s.get('items', 0)} 条"
              f" · {s.get('elapsed', 0)}s"
              + (f" · {s.get('error')}" if s.get("error") else ""))
    cnt = res.get("counts") or {}
    print(f"\n  名录：T {cnt.get('T', 0)} / A {cnt.get('A', 0)} / B {cnt.get('B', 0)}"
          f"（共 {cnt.get('catalog_total', 0)} 条）"
          + ("　⚠️ 未抓到名录页，沿用上次缓存" if not res.get("catalog_ok") else ""))
    d = res.get("diff") or {}
    if d.get("note"):
        print(f"  对账：{d['note']}")
    for key, label in (("added", "新增"), ("renamed", "改名"),
                       ("removed", "官方移除"), ("tier_changed", "级别变化")):
        items = d.get(key) or []
        for x in items[:10]:
            if key == "added":
                print(f"  ＋ 附录{x.get('appendix')} {x.get('tier')} 类 "
                      f"#{x.get('seq')} {x.get('name')}")
            elif key == "renamed":
                print(f"  ✎ #{x.get('seq')} {x.get('from')} → {x.get('to')}")
            elif key == "removed":
                print(f"  － 附录{x.get('appendix')} {x.get('tier')} 类 "
                      f"#{x.get('seq')} {x.get('name')}")
            else:
                print(f"  ⇄ {x.get('name')}：{x.get('from')} → {x.get('to')}")
        if len(items) > 10:
            print(f"     …{label}共 {len(items)} 项")
    clues = res.get("clues") or []
    if clues:
        print(f"\n  通知线索（还有哪些活动在报名，共 {len(clues)} 条，最新在前）：")
        for c in clues[:12]:
            print(f"    · {c.get('pub_date') or '日期未知'} {c.get('title')}"
                  + (f"　[对应名录：{c.get('matched_name')}]"
                     if c.get("matched_name") else "")
                  + f"\n      {c.get('url')}")
    print(f"\n  缓存：{res.get('cache_path')}")
    print("=" * 74)
    return 0 if res.get("ok") else 1


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
    comp = calc.data.competitions or {}
    if comp:
        c = comp.get("counts") or {}
        page = comp.get("catalog_page") or {}
        print(f"  具体赛事  : {c.get('total', 0)} 项"
              f"（T {c.get('T', 0)} / A {c.get('A', 0)} / B {c.get('B', 0)}）"
              f"，来自 {page.get('title', '')}")
        on = (comp.get("online") or {})
        if on:
            d = on.get("diff") or {}
            print(f"  联网刷新  : {on.get('fetched_at', '')}"
                  f"｜名录 {((on.get('counts') or {}).get('catalog_total', 0))} 条"
                  f"｜新增 {len(d.get('added') or [])}"
                  f"｜改名 {len(d.get('renamed') or [])}"
                  f"｜线索 {len(on.get('clues') or [])} 条")
        else:
            print("  联网刷新  : 还没刷新过（计算器页「活动篮」→🔄 刷新联网，"
                  "或 cli competitions）")
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
def cmd_login(args: argparse.Namespace) -> int:
    """拿到校内统一身份认证的会话（Cookie 导入 / 表单登录）。"""
    from . import auth as A

    print("=" * 74)
    print("SCAU 统一身份认证 · 会话")
    print("=" * 74)
    A.console_warn()

    if not args.service:
        args.service = A.DEFAULT_SERVICE
    sess = A.AuthSession()

    if args.forget:
        sess.clear()
        A.forget_credentials()
        print(f"\n✓ 已清除会话与本地凭据（{A.COOKIE_FILE.name} / {A.CRED_FILE.name}）")
        return 0

    # ---- ① Cookie 导入：不接触密码，CAS 有验证码时也是唯一可行的路 ---- #
    if args.cookie is not None:
        raw = args.cookie
        if raw == "-" or not raw.strip():
            print("\n从浏览器复制 Cookie：F12 → Network → 任意一个已登录请求 → "
                  "Request Headers → 整行 Cookie 的值")
            print("（整行粘贴，回车结束；也接受带 `Cookie: ` 前缀的写法）")
            raw = input("Cookie > ").strip()
        if not raw:
            print("✗ 没有拿到 Cookie", file=sys.stderr)
            return 1
        n = sess.set_cookie_header(raw, args.domain)
        saved = sess.save_cookies()
        print(f"\n✓ 已导入 {n} 个 cookie → {saved}")
        return _login_verify(sess, args.service)

    # ---- ② 表单登录（有验证码就自动 OCR） ---- #
    saved_user, saved_pw = A.load_credentials()
    user = args.user or saved_user
    pw = args.password or saved_pw
    if not user:
        user = input("学号 / 工号 > ").strip()
    if not pw:
        print("密码（不回显、不写日志；要留空直接回车则只用已保存的凭据）> ", end="", flush=True)
        pw = getpass.getpass("")
    if not user or not pw:
        print("✗ 账号或密码为空", file=sys.stderr)
        return 1

    settings = A.SETTINGS
    if args.no_captcha:
        from dataclasses import replace as _replace

        settings = _replace(settings, ocr_captcha=False)
    print(f"\n登录 {A.CAS_BASE}/lyuapServer/login   service={args.service}")
    print(f"  （{settings.describe()}）")
    res = sess.login(user, pw, service=args.service, settings=settings)
    print(res.debug())
    if not res.ok:
        if res.need_captcha and not args.no_captcha:
            print("\n验证码是图形验证码，OCR 没认出来。三条路：\n"
                  "  ① 配好百度 OCR：python -m harness.cli ocr --api-key <AK> --secret-key <SK>\n"
                  "  ② 再试一次（会换一张验证码）：python -m harness.cli login\n"
                  "  ③ 干脆不碰密码：python -m harness.cli login --cookie", file=sys.stderr)
        elif res.blockers:
            print(f"\n提示：登录页要求 {('、'.join(res.blockers))}，脚本过不去，"
                  "改用  python -m harness.cli login --cookie", file=sys.stderr)
        else:
            print("\n提示：账号密码要对（统一身份认证那套）；"
                  "如果登录页有滑块/短信验证，改用  python -m harness.cli login --cookie",
                  file=sys.stderr)
        return 1

    saved = sess.save_cookies()
    print(f"\n✓ 会话已保存 → {saved}（.auth/ 已 gitignore，别提交、别外发）")
    if not args.no_save:
        p = A.save_credentials(user, pw)
        print(f"✓ 凭据已保存 → {p}（仅当前用户可读；之后 crawl 撞到登录墙会自动用它登录；"
              f"不想要就 login --forget）")
    return _login_verify(sess, args.service)


def _login_verify(sess, service: str) -> int:
    """存完会话后顺手验证一次，别让「以为登录上了」拖到 crawl 阶段才发现。"""
    print(f"\n验证：GET {service}")
    info = sess.probe(service)
    if info["error"]:
        print(f"  ⚠️ 打不开：{info['error']}")
        return 1
    print(f"  {info['status']}  {info['final_url'][:100]}")
    print(f"  标题：{info['title'] or '(空)'}")
    if info["login_wall"]:
        print("  ✗ 仍然停在认证页 → 会话没生效（Cookie 过期 / 复制少了 / 账号没权限）")
        return 1
    print("  ✓ 已进入登录墙后面")
    return 0


def cmd_whoami(args: argparse.Namespace) -> int:
    """看一眼当前会话状态：有没有 cookie、过没过期、能不能进指定页面。"""
    from . import auth as A

    sess = A.AuthSession()
    print("=" * 74)
    print("当前会话状态")
    print("=" * 74)
    print(f"Cookie 文件 : {A.COOKIE_FILE}  " + ("✓ 存在" if A.COOKIE_FILE.is_file() else "✗ 不存在"))
    if A.COOKIE_FILE.is_file():
        with contextlib.suppress(Exception):
            meta = json.loads(A.COOKIE_FILE.read_text(encoding="utf-8"))
            print(f"保存时间   : {meta.get('saved_at', '?')}")
    print(f"有效 cookie : {sess.alive()} / {len(list(sess.jar))}（0 就说明得重新 login）")
    user, _ = A.load_credentials()
    if user:
        print(f"已存账号   : {user[:3]}***（凭据文件 {A.CRED_FILE.name}）")
    if args.verbose:
        for line in sess.cookie_summary():
            print(f"  · {line}")
    if args.url:
        info = sess.probe(args.url)
        print(f"\n访问 {args.url}")
        if info["error"]:
            print(f"  ✗ {info['error']}")
            return 1
        print(f"  {info['status']}  {info['final_url'][:100]}")
        print(f"  标题：{info['title'] or '(空)'}")
        print(f"  {'✗ 被弹回认证页（会话无效或该页需要更高权限）' if info['login_wall'] else '✓ 内容可读'}")
        return 1 if info["login_wall"] else 0
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    """带会话抓一个任意 URL 看内容（排查登录墙用）。"""
    from . import auth as A
    from .fetcher import Fetcher, normalize_url

    sess = A.AuthSession()
    if sess.alive() == 0:
        print("⚠️ 当前没有有效会话，先跑：python -m harness.cli login", file=sys.stderr)
    elif not args.no_auth:
        print(f"（带会话请求，有效 cookie {sess.alive()} 个）", file=sys.stderr)

    f = Fetcher(user_agent="scau-research-harness/1.0", auth_session=sess)
    res = f.fetch(normalize_url(args.url), check_robots=not args.no_robots,
                  use_auth=not args.no_auth, force=True)
    if not res.ok:
        print(f"✗ 抓取失败：{res.error}", file=sys.stderr)
        return 1
    print(f"{res.status}  {res.final_url}")
    if A.AuthSession().at_login(res.final_url or ""):
        print("⚠️ 最终落点是认证页 → 会话没生效（先 login，或该页需要更高权限）", file=sys.stderr)

    text = res.text
    if not args.html:
        from .auth import _text_title

        print(f"标题：{_text_title(text) or '(空)'}")
    if args.save:
        out = Path(args.save)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"✓ 已保存 {out}（{len(text)} 字）")
    elif args.html:
        sys.stdout.reconfigure(errors="replace")  # type: ignore[union-attr]
        print(text)
    else:
        plain = re.sub(r"<script\b.*?</script>|<style\b.*?</style>", " ", text,
                       flags=re.I | re.S)
        plain = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", plain)).strip()
        limit = args.limit or 1500
        print(f"\n{plain[:limit]}" + ("…" if len(plain) > limit else ""))
    return 0


# --------------------------------------------------------------------------- #
def cmd_parse(args: argparse.Namespace) -> int:
    """解析本地文件：验证「附件里的信息能不能被抽出来」。"""
    from . import docparse
    from . import ocr as ocr_mod

    if args.no_ocr:
        ocr_mod.SETTINGS.provider = "none"
    paths: list[Path] = []
    for raw in args.path:
        p = Path(raw)
        if p.is_dir():
            paths.extend(sorted(q for q in p.rglob("*") if q.is_file()))
        else:
            paths.append(p)
    if not paths:
        print("没有可解析的文件", file=sys.stderr)
        return 1

    if not ocr_mod.enabled():
        print(f"（{ocr_mod.summary_line()}；本次图片里的文字不会被提取）")

    outdir = Path(args.save) if args.save else None
    if outdir:
        outdir.mkdir(parents=True, exist_ok=True)
    failed = 0
    for p in paths:
        if not p.is_file():
            print(f"✗ {p}：文件不存在")
            failed += 1
            continue
        data = p.read_bytes()
        res = docparse.parse_bytes(data, p.name, use_ocr=not args.no_ocr)
        kind = res.kind or docparse.ext_of(p.name)
        flag = "✓" if res.text.strip() else ("!" if res.error or res.note else "?")
        print(f"\n{flag} {p.name}")
        print(f"   {len(data) // 1024}KB · .{kind} · 解析器 {res.parser or '-'} · {res.summary()}")
        if res.tables:
            print(f"   表格 {len(res.tables)} 张：" +
                  "、".join(f"{len(t)}行" for t in res.tables[:4]))
        if res.images:
            print(f"   内嵌图片 {len(res.images)} 张"
                  + (f"，OCR {res.ocr_used} 张（{res.ocr_chars} 字）" if res.ocr_used else ""))
        if res.error:
            print(f"   ✗ {res.error}")
            failed += 1
        if res.text.strip() and not args.quiet:
            limit = len(res.text) if args.full else args.chars
            body = res.text[:limit]
            print("   " + body.replace("\n", "\n   ")
                  + ("\n   …（还有 %d 字，用 --full 看全部）"
                     % (len(res.text) - limit) if len(res.text) > limit else ""))
        if outdir:
            out = outdir / (p.stem + ".txt")
            out.write_text(res.text, encoding="utf-8")
            print(f"   → 已写出 {out}")
    if outdir:
        print(f"\n共 {len(paths)} 个文件，失败 {failed} 个，输出目录 {outdir}")
    return 1 if failed == len(paths) else 0


def cmd_attach(args: argparse.Namespace) -> int:
    """下载并解析库内通知的附件。"""
    import json as jsonmod

    from . import attachments as attach_mod
    from . import ocr as ocr_mod
    from .auth import AuthSession
    from .fetcher import Fetcher

    st = Store(SETTINGS.crawl.db_path)
    s = attach_mod.AttachmentSettings.from_env()
    if args.max_files:
        s.max_files_per_article = args.max_files
    if args.no_ocr:
        s.ocr = False

    session = AuthSession()
    if session.alive() == 0:
        session = None
    fetcher = Fetcher(user_agent=SETTINGS.crawl.user_agent, timeout=s.timeout,
                      retries=SETTINGS.crawl.retries, delay=SETTINGS.crawl.delay,
                      auth_session=session)

    if args.article:
        art = st.get_article(int(args.article), max_chars=1) or {}
        urls = art.get("attachments") or []
        if isinstance(urls, str):
            try:
                urls = jsonmod.loads(urls or "[]")
            except jsonmod.JSONDecodeError:
                urls = []
        targets = [{"id": int(args.article), "title": art.get("title") or "", "attachments": urls}]
    else:
        fn = st.articles_with_attachments if args.all else st.articles_with_unparsed_attachments
        targets = fn(limit=int(args.limit))

    if not targets:
        print("没有需要处理的附件（都解析过了；要重跑加 --all）")
        st.close()
        return 0

    print(f"附件目录    : {s.dir}")
    print(f"OCR         : {ocr_mod.summary_line()}")
    print(f"待处理通知  : {len(targets)} 篇\n")

    totals = {"files": 0, "with_text": 0, "bytes": 0, "ocr": 0, "failed": 0}
    for i, row in enumerate(targets, 1):
        urls = row.get("attachments") or []
        if isinstance(urls, str):
            try:
                urls = jsonmod.loads(urls or "[]")
            except jsonmod.JSONDecodeError:
                urls = []
        if not urls:
            continue
        print(f"[{i}/{len(targets)}] {str(row.get('title') or '')[:52]}")
        res = attach_mod.process_article(st, fetcher, int(row["id"]), urls,
                                         settings=s, force=args.force,
                                         progress=lambda m: print(m, flush=True))
        for a in st.get_attachments(int(row["id"])):
            mark = "✓" if (a.get("text") or "").strip() else ("✗" if a.get("error") else "·")
            print(f"    {mark} {str(a.get('filename') or '')[:40]:<42}"
                  f"{(a.get('bytes') or 0) // 1024:>6}KB  {str(a.get('parser') or '-'):<16}"
                  f"{len(a.get('text') or '') :>7} 字"
                  + (f"  OCR{a['ocr_used']}张" if a.get("ocr_used") else "")
                  + (f"  {str(a.get('error'))[:40]}" if a.get("error") else ""))
        totals["files"] += res["files"]
        totals["with_text"] += res["with_text"]
        totals["bytes"] += res["bytes"]
        totals["ocr"] += res["ocr"]
        totals["failed"] += len([e for e in res["errors"] if e and not e.startswith("skip:")])

    print("\n" + "=" * 70)
    print(f"附件 {totals['files']} 个｜解析出正文 {totals['with_text']} 个｜"
          f"失败 {totals['failed']} 个｜OCR {totals['ocr']} 张｜"
          f"共 {attach_mod.human_size(totals['bytes'])}")
    dstat = attach_mod.dir_stats(s.dir)
    print(f"附件目录占用：{dstat['files']} 个文件 / {dstat['human']}（{dstat['dir']}）")
    print("下一步：python -m harness.cli ask \"…\"（附件正文已进检索）")
    st.close()
    return 0


def cmd_attachments(args: argparse.Namespace) -> int:
    """列出已下载的附件（含解析状态）。"""
    from . import attachments as attach_mod

    st = Store(SETTINGS.crawl.db_path)
    if args.search:
        rows = st.search_attachments(args.search, top_k=int(args.limit))
        if not rows:
            print("附件正文里没有命中。")
        for r in rows:
            print(f"\n[{r['attachment_id']}] {r['filename']}  （分数 {r['score']:.1f}）")
            print(f"    所属通知：{r['title'][:60]}  {r['pub_date']}")
            print(f"    原文：{r['article_url']}")
            print(f"    片段：{r['snippet'][:200]}")
        st.close()
        return 0

    if args.article:
        rows = st.get_attachments(int(args.article))
        art = st.get_article(int(args.article), max_chars=1) or {}
        print(f"《{art.get('title') or args.article}》的附件：")
    else:
        with st._lock:                                     # noqa: SLF001 - 只读列表
            rows = [dict(r) for r in st.conn.execute(
                "SELECT * FROM attachment ORDER BY id DESC LIMIT ?",
                (int(args.limit),)).fetchall()]
    if not rows:
        print("还没有下载任何附件。"
              "先跑：python -m harness.cli attach（或 crawl 时自动抓）")
        st.close()
        return 0
    print(f"{'id':>5} {'格式':<6} {'大小':>8} {'字符':>8} {'OCR':>4}  存盘路径 / 错误")
    for a in rows:
        err = str(a.get("error") or "")
        print(f"{a['id']:>5} {str(a.get('kind') or '-'):<6} "
              f"{(a.get('bytes') or 0) // 1024:>6}KB {len(a.get('text') or ''):>8} "
              f"{a.get('ocr_used') or 0:>4}  {a.get('stored') or ''}"
              + (f"   ✗ {err[:40]}" if err and not err.startswith("skip:") else ""))
        if a.get("note"):
            print(f"{'':>5}  ↳ {str(a['note'])[:110]}")
    st.close()
    return 0


def cmd_ocr(args: argparse.Namespace) -> int:
    """配置 / 测试 OCR。"""
    from . import ocr as ocr_mod
    from .config import apply_ocr_settings, clear_ocr_settings

    if args.clear:
        res = clear_ocr_settings()
        print("已清除 OCR 凭据" + (f"（{ENV_FILE} 已更新）" if res["wrote"] else ""))
        if res["warning"]:
            print("⚠️ " + res["warning"])
        return 0

    if args.image:
        p = Path(args.image)
        if not p.is_file():
            print(f"✗ {p} 不存在", file=sys.stderr)
            return 1
        data = p.read_bytes()
        payload = ocr_mod.prepare_image(data, name=p.name)
        if payload.error:
            print(f"⚠️ 图片预处理：{payload.error}")
        if not ocr_mod.enabled():
            print("尚未配置 OCR。" + ocr_mod.summary_line())
            print("先跑： python -m harness.cli ocr --api-key <AK> --secret-key <SK>")
            return 2
        res = ocr_mod.recognize_image(payload.data or data, name=p.name)
        if res.error:
            print(f"✗ {res.error}", file=sys.stderr)
            return 1
        print(f"✓ {res.provider} {res.engine} · {res.ms}ms · {len(res.text)} 字")
        print(res.text)
        return 0

    changed = any([args.api_key, args.secret_key, args.provider, args.standard])
    if changed:
        verify = not args.no_verify
        api_key = (args.api_key or "").strip()
        secret = (args.secret_key or "").strip()
        provider = args.provider or ("baidu" if (api_key or secret) else None)
        if verify and provider == "baidu":
            probe = ocr_mod.OCRSettings(
                provider="baidu",
                api_key=api_key or ocr_mod.SETTINGS.api_key,
                secret_key=secret or ocr_mod.SETTINGS.secret_key,
                accurate=False if args.standard else ocr_mod.SETTINGS.accurate,
            )
            if not probe.configured:
                print("⚠️ API Key / Secret Key 不完整，跳过验证")
            else:
                print("正在用一张测试图真实调用百度 OCR…")
                ok, msg = ocr_mod.health(probe)
                print(("✅ " if ok else "❌ ") + msg)
                if not ok and not args.no_verify:
                    print("未保存。确认 key 有「通用文字识别」权限后重试，"
                          "或加 --no-verify 强制保存。")
                    return 2
        res = apply_ocr_settings(provider=provider, api_key=api_key or None,
                                 secret_key=secret or None,
                                 accurate=(False if args.standard else None))
        if res["warning"]:
            print("⚠️ " + res["warning"])
        print(f"已更新 {'、'.join(res['applied']) or '（无改动）'}"
              + (f" → {ENV_FILE}" if res["wrote"] else "（仅本次运行生效）"))
        shadowed = env_file_shadowed_keys() & set(OCR_ENV_KEYS)
        if shadowed:
            print(f"⚠️ 系统环境变量里有 {'、'.join(sorted(shadowed))}，"
                  f"优先级高于 .env，改了可能不生效")
        print(ocr_mod.summary_line())
        return 0

    print(ocr_mod.summary_line())
    print(f"凭据来源    : {ENV_FILE}")
    shadowed = env_file_shadowed_keys() & set(OCR_ENV_KEYS)
    if shadowed:
        print(f"⚠️ 被系统环境变量覆盖：{'、'.join(sorted(shadowed))}")
    print("\n申请地址：https://console.bce.baidu.com/ai/#/ai/ocr/overview/index")
    print("用法示例：")
    print("  python -m harness.cli ocr --api-key <AK> --secret-key <SK>")
    print("  python -m harness.cli ocr --test")
    print("  python -m harness.cli ocr --image 报名表截图.png")
    if args.test:
        ok, msg = ocr_mod.health()
        print(f"\n实测：{'✅ ' if ok else '❌ '}{msg}")
        return 0 if ok else 2
    return 0


# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="harness", description="SCAU 站点群 LLM 检索 Harness",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("setup-key", help="交互式配置 LLM key / 端点 / 模型（写入仓库根 .env）")
    p.add_argument("--key", help="直接传入 key（不回显输入时用）")
    p.add_argument("--base-url", help="OpenAI 兼容端点，默认 https://api.deepseek.com")
    p.add_argument("--model", help="模型名，默认 deepseek-chat")
    p.set_defaults(func=cmd_setup_key)

    p = sub.add_parser("doctor", help="自检环境/种子/数据库/LLM 连通性")
    p.add_argument("--no-llm", action="store_true", help="跳过 LLM 连通性测试")
    p.add_argument("--test-web", action="store_true", help="实测公网搜索")
    p.add_argument("--test-ocr", action="store_true", help="实测 OCR（会真的调一次接口）")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("crawl", help="按范围抓取 SCAU 栏目群")
    p.add_argument("--scope", default="narrow", choices=["narrow", "p1", "p2", "all"])
    p.add_argument("--url", action="append", help="额外指定栏目列表页（可多次）")
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--max-pages", type=int, default=0)
    p.add_argument("--max-articles", type=int, default=0)
    p.add_argument("--concurrency", type=int, default=0)
    p.add_argument("--no-robots", action="store_true")
    p.add_argument("--no-auth", action="store_true",
                   help="忽略 .auth/ 里的会话，按未登录状态抓（登录墙栏目仍会跳过）")
    p.add_argument("--no-auto-login", action="store_true",
                   help="撞到登录墙时不自动登录（默认会用已保存的账号自动登录，验证码走 OCR）")
    p.add_argument("--no-attachments", action="store_true",
                   help="不下载/解析附件（默认会抓，附件正文进检索）")
    p.add_argument("--reset", action="store_true")
    p.set_defaults(func=cmd_crawl)

    # ---------------- 登录墙（统一身份认证） ---------------- #
    p = sub.add_parser("login", help="登录统一身份认证（或导入浏览器 Cookie），存到 .auth/")
    p.add_argument("--user", help="学号/工号（不给就交互输入；不写进 shell 历史）")
    p.add_argument("--password", help="密码（不建议写在命令行；默认交互输入不回显）")
    p.add_argument("--cookie", nargs="?", const="-", metavar="COOKIE",
                   help="不用密码：直接导入浏览器复制的一整行 Cookie（不带值时交互粘贴）")
    p.add_argument("--domain", default="cas.scau.edu.cn",
                   help="--cookie 导入时归属的域，默认 cas.scau.edu.cn")
    p.add_argument("--service", default=None,
                   help="登录后跳转的目标地址，默认融合门户 http://portal.scau.edu.cn/")
    p.add_argument("--no-save", action="store_true", help="不把账号密码写进 .auth/credentials.json")
    p.add_argument("--no-captcha", action="store_true",
                   help="不尝试 OCR 识别验证码（遇到验证码直接报错，方便对照排查）")
    p.add_argument("--forget", action="store_true", help="清除已保存的会话与凭据")
    p.set_defaults(func=cmd_login)

    p = sub.add_parser("whoami", help="看当前会话状态（cookie 数 / 能否进某个页面）")
    p.add_argument("url", nargs="?", default="", help="顺便试着访问这个 URL")
    p.add_argument("-v", "--verbose", action="store_true", help="列出每个 cookie")
    p.set_defaults(func=cmd_whoami)

    p = sub.add_parser("fetch", help="带会话抓一个 URL（排查登录墙 / 取单页内容）")
    p.add_argument("url")
    p.add_argument("--save", help="把正文写到文件")
    p.add_argument("--html", action="store_true", help="输出原始 HTML 而不是正文摘要")
    p.add_argument("--limit", type=int, default=0, help="正文摘要长度上限")
    p.add_argument("--no-auth", action="store_true", help="不带会话请求（对照组）")
    p.add_argument("--no-robots", action="store_true")
    p.set_defaults(func=cmd_fetch)

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
    p.add_argument("--list", choices=["competition", "general", "all"], default="all",
                   help="清单范围：competition=《学生竞赛奖励办法》名录里的具体赛事，"
                        "general=通用加分项，all=全部（默认）")
    p.add_argument("--refresh", action="store_true",
                   help="先联网刷新赛事名录（抓官网 → 与内置数据对账）再打印")
    p.add_argument("--timeout", type=int, default=12, help="联网刷新的单页超时秒数")
    p.set_defaults(func=cmd_activities)

    p = sub.add_parser("competitions",
                       help="刷新《学生竞赛奖励办法》赛事名录（联网抓官网并和内置数据对账）")
    p.add_argument("--timeout", type=int, default=12, help="单页超时秒数")
    p.set_defaults(func=cmd_competitions_refresh)

    p = sub.add_parser("calc", help="计算器数据自检：专业/课程/门槛/活动/口径")
    p.set_defaults(func=cmd_calc)

    # ---------------- 附件 / 文档解析 / OCR ---------------- #
    p = sub.add_parser("parse", help="解析本地文件（docx/xlsx/pdf/doc/xls/图片/压缩包…）并打印文本")
    p.add_argument("path", nargs="+", help="一个或多个文件路径")
    p.add_argument("--chars", type=int, default=1200, help="每个文件打印多少字符（默认 1200）")
    p.add_argument("--full", action="store_true", help="打印全部正文（可能很长）")
    p.add_argument("--no-ocr", action="store_true", help="跳过图片 OCR")
    p.add_argument("--save", help="把解析结果写到这个目录（每个文件一个 .txt）")
    p.add_argument("-q", "--quiet", action="store_true", help="只打印摘要行")
    p.set_defaults(func=cmd_parse)

    p = sub.add_parser("attach", help="下载并解析库内通知的附件（存到 data/attachments/）")
    p.add_argument("--limit", type=int, default=10, help="最多处理几篇通知（默认 10）")
    p.add_argument("--article", type=int, default=0, help="只处理这一篇文章的附件")
    p.add_argument("--all", action="store_true", help="连已经解析过的也重跑")
    p.add_argument("--force", action="store_true", help="忽略缓存，重新下载")
    p.add_argument("--no-ocr", action="store_true", help="本次不调用 OCR（图片里文字不提取）")
    p.add_argument("--max-files", type=int, default=0, help="覆盖单篇通知的附件数上限")
    p.set_defaults(func=cmd_attach)

    p = sub.add_parser("attachments", help="列出已下载的附件及其解析状态")
    p.add_argument("--article", type=int, default=0, help="只看某篇文章的附件")
    p.add_argument("--limit", type=int, default=40)
    p.add_argument("--search", default="", help="在附件正文里搜关键词")
    p.set_defaults(func=cmd_attachments)

    p = sub.add_parser("ocr", help="配置 / 测试 OCR（百度智能云），图片与扫描件靠它提字")
    p.add_argument("--api-key", help="百度 OCR 应用的 API Key")
    p.add_argument("--secret-key", help="百度 OCR 应用的 Secret Key")
    p.add_argument("--provider", choices=["baidu", "none"], help="OCR 服务商（none=关闭）")
    p.add_argument("--standard", action="store_true", help="用标准版（默认高精度版）")
    p.add_argument("--test", action="store_true", help="用一张测试图真实调一次接口")
    p.add_argument("--image", help="直接对这张图片做一次识别（验证效果）")
    p.add_argument("--clear", action="store_true", help="清除已保存的 OCR 凭据")
    p.add_argument("--no-verify", action="store_true", help="保存前不做真实调用验证")
    p.set_defaults(func=cmd_ocr)

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
