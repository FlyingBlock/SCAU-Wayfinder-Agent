"""采集、登录、会话与单页抓取命令。"""
from __future__ import annotations

import argparse

import json
import re
import sys
from pathlib import Path

from ..core.config import SETTINGS
from ..corpus.store import Store


def cmd_crawl(args: argparse.Namespace) -> int:
    from ..crawl.crawl import main as crawl_main

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


def cmd_login(args: argparse.Namespace) -> int:
    """拿到校内统一身份认证的会话（Cookie 导入 / 表单登录）。"""
    from ..crawl import auth as A

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
                  "  ① 配好百度 OCR：python -m wayfinder ocr --api-key <AK> --secret-key <SK>\n"
                  "  ② 再试一次（会换一张验证码）：python -m wayfinder login\n"
                  "  ③ 干脆不碰密码：python -m wayfinder login --cookie", file=sys.stderr)
        elif res.blockers:
            print(f"\n提示：登录页要求 {('、'.join(res.blockers))}，脚本过不去，"
                  "改用  python -m wayfinder login --cookie", file=sys.stderr)
        else:
            print("\n提示：账号密码要对（统一身份认证那套）；"
                  "如果登录页有滑块/短信验证，改用  python -m wayfinder login --cookie",
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
    from ..crawl import auth as A

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
    from ..crawl import auth as A
    from ..crawl.fetcher import Fetcher, normalize_url

    sess = A.AuthSession()
    if sess.alive() == 0:
        print("⚠️ 当前没有有效会话，先跑：python -m wayfinder login", file=sys.stderr)
    elif not args.no_auth:
        print(f"（带会话请求，有效 cookie {sess.alive()} 个）", file=sys.stderr)

    f = Fetcher(user_agent="scau-research-wayfinder/1.0", auth_session=sess)
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
        from ..crawl.auth import _text_title

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
