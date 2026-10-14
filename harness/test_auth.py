"""登录墙链路的离线自测（不需要真的学校账号）。

跑法：
    python harness/test_auth.py

它在本机起两个假站点：
  · 假 CAS（cas.scau.edu.cn 的角色）：返回带 execution 隐藏字段的登录表单，
    校验账号密码，正确就 302 回 service 并种 session cookie。
  · 假业务站（portal 的角色）：没有 session cookie 就返回登录页，
    有就返回一个正常的栏目列表页 + 两篇文章。

然后验证四件事：
  ① 表单解析能抓到 execution；
  ② AuthSession.login 能登上去并持久化 cookie；
  ③ 用保存的 cookie 重新开一个会话，能读到登录墙后面的内容；
  ④ Crawler 带着这个会话能抓取并入库（这是最终目的）。

全程走 127.0.0.1，不碰外网、不碰你真实的 .auth/。
"""
from __future__ import annotations

import http.server
import json
import shutil
import socket
import sys
import tempfile
import threading
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Windows 本地控制台是 GBK，✓/✗ 会直接把整个命令打崩，先放宽编码策略
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(errors="replace")           # type: ignore[union-attr]
    except (AttributeError, OSError, ValueError):
        pass

from harness import auth as A                    # noqa: E402
from harness.config import SETTINGS              # noqa: E402
from harness.crawler import Crawler              # noqa: E402
from harness.seed import Site                    # noqa: E402
from harness.store import Store                  # noqa: E402

USER, PW = "2023123456", "hunter2-demo"
BASE = ""          # main() 里填成假站点的 http://127.0.0.1:PORT

LOGIN_PAGE = """<!DOCTYPE html><html><head><title>统一身份认证</title></head><body>
<form id="fm1" method="post" action="__ACTION__">
  <input type="hidden" name="execution" value="e1s1-abc123">
  <input type="hidden" name="lt" value="LT-99-demo">
  <input type="hidden" name="_eventId" value="submit">
  <input type="text" name="username" value="">
  <input type="password" name="password" value="">
</form></body></html>"""

WALL = """<!DOCTYPE html><html><head><title>统一身份认证</title></head><body>
<form id="fm1" method="post" action="/lyuapServer/login?service={svc}">
  <input type="hidden" name="execution" value="e1s1-abc123">
  <input type="text" name="username"><input type="password" name="password">
</form></body></html>"""

LIST_PAGE = """<!DOCTYPE html><html><head><title>通知公告</title></head><body>
<div class="list"><ul>
 <li><a href="/2026/0101/c1a101/page.htm" title="关于做好本学期期末考试工作的通知">期末考试通知</a><span>2026-01-01</span></li>
 <li><a href="/2026/0102/c1a102/page.htm" title="2026年优秀学生奖学金评审结果公示">奖学金公示</a><span>2026-01-02</span></li>
</ul></div></body></html>"""

ARTICLE = """<!DOCTYPE html><html><head><title>{title}</title></head><body>
<div class="v_news_content"><p>{body}</p></div></body></html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):        # 静音
        pass

    # ---- 工具 ---- #
    def _send(self, code: int, body: str, *, location: str = "", cookie: str = ""):
        raw = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        if location:
            self.send_header("Location", location)
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        if raw:
            self.wfile.write(raw)

    def _has_session(self) -> bool:
        return "SCAUSESSION=ok" in (self.headers.get("Cookie") or "")

    # ---- 路由 ---- #
    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path
        if path.startswith("/lyuapServer/login"):
            svc = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get("service", [""])[0]
            if svc:            # 真 CAS 会把 service 写进表单 action，这里照做
                svc = urllib.parse.unquote(svc)
                action = self.path.split("?")[0] + "?service=" + urllib.parse.quote(svc, safe="")
            else:
                action = self.path.split("?")[0]
            self._send(200, LOGIN_PAGE.replace("__ACTION__", action))
            return
        if path == "/login-check":                     # 登录成功后 ticket 的落点
            ticket = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get("ticket", [""])[0]
            if not ticket:
                self._send(200, WALL.format(svc=""))
                return
            self._send(302, "", location=f"{BASE}/portal-list.htm",
                       cookie="SCAUSESSION=ok; Path=/")
            return
        if path == "/portal-list.htm":                 # 业务页面：需要会话
            if not self._has_session():
                self._send(200, WALL.format(svc="/portal-list.htm"))
                return
            html = LIST_PAGE.replace('href="/2026', f'href="{BASE}/2026')
            self._send(200, html)
            return
        if path.startswith("/2026/"):
            if not self._has_session():
                self._send(200, WALL.format(svc=path))
                return
            title = "关于做好本学期期末考试工作的通知" if "a101" in path else "2026年优秀学生奖学金评审结果公示"
            body = ("各学院、各有关单位：根据校历安排，现将本学期期末考试工作有关事项通知如下，"
                    "请各学院按期组织落实，做好考场编排、监考安排与学生通知工作。" * 3)
            self._send(200, ARTICLE.format(title=title, body=body))
            return
        self._send(404, "<html><title>404</title></html>")

    def do_POST(self):
        if not urllib.parse.urlsplit(self.path).path.startswith("/lyuapServer/login"):
            self._send(404, "<html><title>404</title></html>")
            return
        n = int(self.headers.get("Content-Length") or 0)
        form = urllib.parse.parse_qs(self.rfile.read(n).decode("utf-8"))
        svc = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get("service", [""])[0]
        if form.get("execution", [""])[0] != "e1s1-abc123":
            self._send(200, LOGIN_PAGE.replace("__ACTION__", self.path))
            return
        if form.get("username", [""])[0] != USER or form.get("password", [""])[0] != PW:
            self._send(200, LOGIN_PAGE.replace("__ACTION__", self.path))
            return
        # CAS 风格：302 回 service 并带 ticket，同时种会话 cookie
        target = svc or "/login-check"
        joiner = "&" if "?" in target else "?"
        self._send(302, "", location=f"{target}{joiner}ticket=ST-1-demo",
                   cookie="SCAUSESSION=ok; Path=/")


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main() -> int:
    global BASE
    tmp = Path(tempfile.mkdtemp(prefix="scau-auth-test-"))
    fails: list[str] = []

    def check(name: str, cond: bool, detail: str = "") -> None:
        print(f"  {'✓' if cond else '✗'} {name}" + (f"  （{detail}）" if detail else ""))
        if not cond:
            fails.append(name)

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = srv.server_port
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    BASE = f"http://127.0.0.1:{port}"

    # 把登录态目录、CAS 端点、默认 service 整体指到临时目录 + 本机假站，
    # 全程不碰你真实的 .auth/ 与学校站点
    A.ROOT = tmp
    A.auth_dir = lambda: tmp / ".auth"
    A.AUTH_DIR = tmp / ".auth"
    A.COOKIE_FILE = A.auth_dir() / "cookies.json"
    A.CRED_FILE = A.auth_dir() / "credentials.json"
    A.CAS_BASE = BASE
    A.DEFAULT_SERVICE = f"{BASE}/portal-list.htm"
    list_url = f"{BASE}/portal-list.htm"

    try:
        # ---- ① 表单解析 ---- #
        print("\n① 登录表单解析")
        hidden, action = A._parse_form(LOGIN_PAGE.replace("__ACTION__", "/x"), BASE)
        check("抓到隐藏字段 execution", hidden.get("execution") == "e1s1-abc123", str(hidden))
        check("解析出 form action", action.endswith("/x"), action)
        check("识别验证码存在", A._detect_blockers("<input name='captcha'>") == ["captcha"])

        # ---- ② CAS 表单登录 ---- #
        print("\n② CAS 表单登录（假站点）")
        import os

        # AUTH_TEST_DEBUG=1 时把提交的字段和落点打出来，排错用
        verbose = bool(os.environ.get("AUTH_TEST_DEBUG"))
        sess = A.AuthSession(cookie_path=A.COOKIE_FILE)
        if verbose:
            real_post = sess.post

            def spy(url, fields, **kw):
                print(f"  [debug] POST {url}\n  [debug] fields={fields}")
                out = real_post(url, fields, **kw)
                print(f"  [debug] → {out[1]} {out[2]}")
                return out

            sess.post = spy          # type: ignore[method-assign]
        res = sess.login(USER, PW, service=list_url)
        check("登录成功", res.ok, res.message)
        check("拿到 cookie", len(list(sess.jar)) > 0, f"{len(list(sess.jar))} 个")
        sess.save_cookies()          # 与 cli.cmd_login 的实际动作一致
        check("cookie 已落盘", A.COOKIE_FILE.is_file(), str(A.COOKIE_FILE))
        check("验证页判定为已进墙内", not sess.probe(list_url)["login_wall"])
        check("错误密码会被拒", not A.AuthSession(cookie_path=tmp / "no.json").login(USER, "wrong", service=list_url).ok)

        # ---- ③ Cookie 导入 + 断点复用 ---- #
        print("\n③ Cookie 导入 / 复用落盘的会话")
        sess2 = A.AuthSession(cookie_path=A.COOKIE_FILE)
        check("新会话自动读到落盘 cookie", sess2.alive() > 0, f"{sess2.alive()} 个有效")
        check("带 cookie 能读到墙后内容", "期末考试通知" in sess2.get(list_url)[0])

        manual = A.AuthSession(cookie_path=tmp / "manual.json")
        n = manual.set_cookie_header("Cookie: SCAUSESSION=ok; other=1", "127.0.0.1")
        check("Cookie 头导入解析", n == 2, f"{n} 个")
        check("导入的 cookie 能在 http 上生效", bool(manual.jar) and
              all(not c.secure for c in manual.jar))
        https_jar = A.AuthSession(cookie_path=tmp / "m2.json")
        https_jar.set_cookie_header("a=b", "cas.scau.edu.cn")
        check("https 域仍标记为 secure", all(c.secure for c in https_jar.jar))

        # ---- ④ 采集层（最终目的） ---- #
        print("\n④ Crawler 带会话抓取登录墙栏目")
        # 测试站点在 127.0.0.1:<随机端口> 上，而生产逻辑有两处会把它改坏：
        #   · is_scau 只放行 *.scau.edu.cn 的白名单；
        #   · normalize_url 统一走 https、并用默认端口。
        # 这两处在生产里都是对的（校内站点就是 443 + scau.edu.cn），
        # 所以只在本次进程内放开，不改动产品代码。
        from harness import crawler as crawler_mod
        from harness import fetcher as fetcher_mod

        crawler_mod.is_scau = lambda url: True
        _keep = lambda u, *a, **k: u                    # noqa: E731
        fetcher_mod.normalize_url = _keep
        crawler_mod.normalize_url = _keep

        db = tmp / "t.db"
        store = Store(db)
        site = Site(name="假通知公告", url=list_url, site=f"127.0.0.1:{port}",
                    kind="list", topic="academic")
        crawler = Crawler(store, SETTINGS.crawl, auth_session=sess2, check_robots=False)
        if verbose:
            raw = crawler.fetcher.fetch(list_url, check_robots=False, use_auth=True, force=True)
            print(f"  [debug] 带会话直取列表页 → {raw.status} {raw.final_url} "
                  f"长度={len(raw.text)}")
        items, max_page, final_url, auth_expired, login_wall = crawler.discover(site)
        check("列表页解析出条目", len(items) >= 2, f"{len(items)} 条")
        check("没被当成登录墙", not login_wall and not auth_expired)
        check("已带会话（use_auth）", crawler.use_auth)
        report = crawler.run([site])
        n_articles = store.count_articles()
        check("文章已入库", n_articles >= 2, f"{n_articles} 篇")
        check("栏目算成功", report.sites_ok == 1, f"ok={report.sites_ok} failed={report.sites_failed}")
        row = store.conn.execute("SELECT title, body FROM article LIMIT 1").fetchone()
        check("正文有内容", bool(row and len(row["body"]) > 50),
              (row["title"][:20] if row else "无"))

        print("\n⑤ 没有会话时应当照旧跳过（对照组）")
        store2 = Store(tmp / "t2.db")
        crawler2 = Crawler(store2, SETTINGS.crawl, auth_session=None, check_robots=False)
        rep2 = crawler2.run([site])
        check("无会话 → 判为需登录并跳过",
              rep2.sites_ok == 0 and store2.count_articles() == 0
              and [e[1] for e in rep2.errors] == ["login_required"],
              f"ok={rep2.sites_ok} errors={[e[1] for e in rep2.errors]}")
        store.close()
        store2.close()
    finally:
        srv.shutdown()
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n" + "=" * 60)
    if fails:
        print(f"✗ {len(fails)} 项失败：" + "、".join(fails))
        return 1
    print("✓ 全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
