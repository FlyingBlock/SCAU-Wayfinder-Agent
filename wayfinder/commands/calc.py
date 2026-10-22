"""绩点 / 综测 / 活动 / 门槛命令。"""
from __future__ import annotations

import argparse

import json
from pathlib import Path

from ..core.config import SETTINGS
from .common import _calc_basket, _calc_profile


def cmd_gpa(args: argparse.Namespace) -> int:
    from ..calc import Calculator

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
    from ..calc import Calculator

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
    from ..calc import Calculator

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
        best_info = calc.basket.best_preview(preview.get(act.id) or {})
        best = best_info["best"]
        best_ach = best_info["best_achieve"]
        best_tm = best_info["best_tuimian"]
        best_ach_tm = best_info["best_achieve_tuimian"]
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
    from ..integrations import competitions as competitions_integration

    print("=" * 74)
    print("刷新赛事名录（抓学校官网 → 与内置 calcdata/competitions.json 对账）")
    print("=" * 74)
    res = competitions_integration.refresh(
        timeout=int(getattr(args, "timeout", 12) or 12))
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
    from ..calc import Calculator

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
