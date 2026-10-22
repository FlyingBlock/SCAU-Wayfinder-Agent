"""附件解析、下载与 OCR 命令。"""
from __future__ import annotations

import argparse

import json
import re
import sys
from pathlib import Path

from ..core.config import ENV_FILE, OCR_ENV_KEYS, SETTINGS, env_file_shadowed_keys
from ..corpus.store import Store


def cmd_parse(args: argparse.Namespace) -> int:
    """解析本地文件：验证「附件里的信息能不能被抽出来」。"""
    from ..documents import docparse
    from ..documents import ocr as ocr_mod

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

    from ..documents import attachments as attach_mod
    from ..documents import ocr as ocr_mod
    from ..crawl.auth import AuthSession
    from ..crawl.fetcher import Fetcher

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
    print("下一步：python -m wayfinder ask \"…\"（附件正文已进检索）")
    st.close()
    return 0


def cmd_attachments(args: argparse.Namespace) -> int:
    """列出已下载的附件（含解析状态）。"""
    from ..documents import attachments as attach_mod

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
              "先跑：python -m wayfinder attach（或 crawl 时自动抓）")
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
    from ..documents import ocr as ocr_mod
    from ..settings.service import apply_ocr_settings, clear_ocr_settings

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
            print("先跑： python -m wayfinder ocr --api-key <AK> --secret-key <SK>")
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
    print("  python -m wayfinder ocr --api-key <AK> --secret-key <SK>")
    print("  python -m wayfinder ocr --test")
    print("  python -m wayfinder ocr --image 报名表截图.png")
    if args.test:
        ok, msg = ocr_mod.health()
        print(f"\n实测：{'✅ ' if ok else '❌ '}{msg}")
        return 0 if ok else 2
    return 0
