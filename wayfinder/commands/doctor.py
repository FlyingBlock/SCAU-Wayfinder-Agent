"""自检命令：跨功能检查种子、库、计算器、LLM、OCR 与登录。"""
from __future__ import annotations

import argparse

import sys

from ..core.config import (
    AUTH_ENV_KEYS,
    LLM_ENV_KEYS,
    LLM_LEGACY_KEYS,
    OCR_ENV_KEYS,
    ROOT,
    SETTINGS,
    env_file_shadowed_keys,
)
from ..corpus.store import Store


def cmd_doctor(args: argparse.Namespace) -> int:
    from ..core.config import SearchSettings
    from ..qa.llm import LLM
    from ..crawl.seed import collect_sites, load_seed, stats
    from ..qa.websearch import WebSearcher

    print("=" * 70)
    print("SCAU Wayfinder 自检")
    print("=" * 70)
    print(f"仓库根      : {ROOT}")
    print(f"种子文件    : {SETTINGS.seed_file}  {'✓' if SETTINGS.seed_file.is_file() else '✗ 缺失'}")
    print(f"数据库      : {SETTINGS.crawl.db_path}  "
          f"{'✓' if SETTINGS.crawl.db_path.is_file() else '（尚未创建，先跑 crawl）'}")

    if SETTINGS.seed_file.is_file():
        groups = load_seed(SETTINGS.seed_file)
        sites = collect_sites(groups)
        print(f"种子内容    : {len(groups)} 分组 / {len(sites)} 个可抓取栏目")
        from ..crawl.curate import NARROW_URLS, curated, missing_from_seed

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
        from ..calc import Calculator

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
    from ..documents import attachments as _attach
    from ..documents import docparse as _docparse
    from ..documents import ocr as _ocr

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
    from ..crawl import auth as _auth

    sess = _auth.AuthSession()
    _user, _pw = _auth.load_credentials()
    if sess.alive():
        print(f"登录会话    : ✓ {sess.alive()} 个有效 cookie（{_auth.COOKIE_FILE.name}）"
              f"，crawl 会带着它抓认证栏目")
    elif _auth.COOKIE_FILE.is_file():
        print("登录会话    : ⚠️ 有 cookie 文件但已全部过期 → python -m wayfinder login")
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
