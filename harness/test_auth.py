"""登录墙链路的离线自测（不需要真的学校账号）。

跑法：
    python harness/test_auth.py

它在本机起两个假站点：
  · 假 CAS（cas.scau.edu.cn 的角色）：返回带 execution 隐藏字段的登录表单，
    校验账号密码，**还能切换成「带图形验证码」的模式**（验证码图走
    `/lyuapServer/captcha`，每取一次换一张，服务端记着当前那张是什么），
    正确就 302 回 service 并种 session cookie。
  · 假业务站（portal 的角色）：没有 session cookie 就返回登录页，
    有就返回一个正常的栏目列表页 + 两篇文章。

然后验证这些事：
  ① 表单解析能抓到 execution，也能认出验证码字段与验证码图片；
  ② AuthSession.login 能登上去并持久化 cookie；
  ③ 用保存的 cookie 重新开一个会话，能读到登录墙后面的内容；
  ④ Crawler 带着这个会话能抓取并入库（这是最终目的）；
  ⑤ 没有会话时照旧跳过（对照组）；
  ⑥ 有验证码时：OCR 认对了能自动过；认错一次会**换一张**再试；一直认错就如实
     失败并把验证码图带回去（`need_captcha`）；没配 OCR 时明确说清楚而不是空转；
  ⑦ 人工兜底那条路：`begin_login` 拿到的表单可以被人填一次验证码接着登完，
     `/api/settings/auth` 也能把账号存下来并真登一次；
  ⑧ **Crawler 撞到登录墙时自己登录**（用 .auth/credentials.json 里的账号，
     验证码走 OCR），登完把文章抓进来。

验证码识别在测试里是**注入的假 OCR**（`auth.set_captcha_solver`），所以全程
不联网、不花百度额度，也不需要真账号。

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
import time
import urllib.parse
from dataclasses import replace
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

# 假 CAS 的「当前验证码」状态：取一次图换一个码，服务端记着，提交时校验
CAPTCHA = {"on": False, "code": "", "issued": 0, "seen": []}

LOGIN_PAGE = """<!DOCTYPE html><html><head><title>统一身份认证</title></head><body>
<form id="fm1" method="post" action="__ACTION__">
  <input type="hidden" name="execution" value="e1s1-abc123">
  <input type="hidden" name="lt" value="LT-99-demo">
  <input type="hidden" name="_eventId" value="submit">
  <input type="text" name="username" value="">
  <input type="password" name="password" value="">
</form></body></html>"""

LOGIN_PAGE_CAPTCHA = """<!DOCTYPE html><html><head><title>统一身份认证</title></head><body>
<form id="fm1" method="post" action="__ACTION__">
  <input type="hidden" name="execution" value="e1s1-abc123">
  <input type="hidden" name="lt" value="LT-99-demo">
  <input type="hidden" name="_eventId" value="submit">
  <input type="text" name="username" value="">
  <input type="password" name="password" value="">
  <input type="text" name="captcha" id="captcha" value="">
  <img id="captchaImg" src="/lyuapServer/captcha" alt="验证码"
       onclick="this.src='/lyuapServer/captcha?t='+Math.random()">
  <div class="errors">__ERROR__</div>
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

# 一张最小合法 PNG（假验证码图；测试里由注入的假 OCR 直接给出答案）
def _png() -> bytes:
    try:
        from harness.ocr import make_test_image

        return make_test_image("captcha")
    except Exception:                                    # noqa: BLE001
        return bytes.fromhex(
            "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
            "1f15c4890000000d4944415478da63f8cfc000000301010018dd8db0"
            "0000000049454e44ae426082")


PNG_1PX = _png()


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

    def _send_png(self, data: bytes):
        self.send_response(200)
        self.send_header("Content-Type", "image/png")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _has_session(self) -> bool:
        return "SCAUSESSION=ok" in (self.headers.get("Cookie") or "")

    def _login_html(self, action: str, error: str = "") -> str:
        if CAPTCHA["on"]:
            return LOGIN_PAGE_CAPTCHA.replace("__ACTION__", action).replace("__ERROR__", error)
        return LOGIN_PAGE.replace("__ACTION__", action)

    # ---- 路由 ---- #
    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path
        if path == "/lyuapServer/captcha":
            CAPTCHA["issued"] += 1
            # 每个「码」都换一张，模拟真实验证码的一次性
            CAPTCHA["code"] = "AB%02d" % (CAPTCHA["issued"] % 100)
            self._send_png(PNG_1PX)
            return
        if path.startswith("/lyuapServer/login"):
            svc = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get("service", [""])[0]
            if svc:            # 真 CAS 会把 service 写进表单 action，这里照做
                svc = urllib.parse.unquote(svc)
                action = self.path.split("?")[0] + "?service=" + urllib.parse.quote(svc, safe="")
            else:
                action = self.path.split("?")[0]
            self._send(200, self._login_html(action))
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
            self._send(200, self._login_html(self.path))
            return
        if CAPTCHA["on"]:
            got = form.get("captcha", [""])[0]
            CAPTCHA["seen"].append(got)
            if got != CAPTCHA["code"]:
                self._send(200, self._login_html(self.path, "验证码错误，请重新输入"))
                return
        if form.get("username", [""])[0] != USER or form.get("password", [""])[0] != PW:
            self._send(200, self._login_html(self.path, "用户名或密码错误"))
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


def _post(url: str, payload: dict):
    import urllib.error
    import urllib.request

    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", "ignore")
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, {"error": raw[:200]}


def _get(url: str):
    import urllib.request

    with urllib.request.urlopen(url, timeout=30) as r:
        return r.status, json.loads(r.read().decode("utf-8"))


def main() -> int:
    global BASE
    # 临时工作目录放在仓库的 data/ 下（data/ 已在 .gitignore 里，跑完删掉）：
    # 系统临时目录在受限沙箱里不一定可写，项目内的目录则一定可写。
    root_tmp = ROOT / "data" / "_tmp_auth_test"
    shutil.rmtree(root_tmp, ignore_errors=True)
    root_tmp.mkdir(parents=True, exist_ok=True)
    tmp = root_tmp
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
        check("验证码不再算拦路虎", A._detect_blockers("<input name='captcha'>") == [],
              str(A._detect_blockers("<input name='captcha'>")))
        check("滑块仍然算拦路虎", A._detect_blockers("<div>请拖动滑块</div>") == ["slider"])
        ch_fields, _ = A._parse_form(LOGIN_PAGE_CAPTCHA.replace("__ACTION__", "/x"), BASE)
        check("认出验证码字段", A.find_captcha_field(ch_fields) == "captcha",
              A.find_captcha_field(ch_fields))
        check("页面里有验证码", A.has_captcha(LOGIN_PAGE_CAPTCHA, ch_fields))
        ch = A.find_captcha_image(LOGIN_PAGE_CAPTCHA, BASE + "/lyuapServer/login?service=x",
                                  field="captcha")
        check("找到验证码图片地址", ch.image_url.endswith("/lyuapServer/captcha"), ch.image_url)
        check("没有验证码的页面找不到图",
              not A.find_captcha_image(LOGIN_PAGE, BASE, field="").image_url)

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

        # ---- ⑤ 对照组：没有会话也没有账号 ---- #
        print("\n⑤ 没有会话时应当照旧跳过（对照组）")
        store2 = Store(tmp / "t2.db")
        crawler2 = Crawler(store2, SETTINGS.crawl, auth_session=None, check_robots=False)
        rep2 = crawler2.run([site])
        check("无会话 → 判为需登录并跳过",
              rep2.sites_ok == 0 and store2.count_articles() == 0
              and [e[1] for e in rep2.errors] == ["login_required"],
              f"ok={rep2.sites_ok} errors={[e[1] for e in rep2.errors]}")

        # ---- ⑥ 验证码：OCR 自动过 / 认错重试 / 认不出就如实失败 ---- #
        print("\n⑥ 图形验证码")
        from harness import ocr as ocr_mod

        CAPTCHA["on"] = True
        CAPTCHA["issued"] = 0
        CAPTCHA["seen"] = []
        good = lambda data, ch: (CAPTCHA["code"], "")     # noqa: E731  完美 OCR
        A.set_captcha_solver(good)
        cap_sess = A.AuthSession(cookie_path=tmp / "cap.json")
        res = cap_sess.login(USER, PW, service=list_url)
        check("有验证码也能自动登录", res.ok, res.message)
        check("回报用了验证码", res.captcha_seen and res.captcha_rounds == 1,
              f"seen={res.captcha_seen} rounds={res.captcha_rounds}")
        check("OCR 结果与提交值一致",
              bool(res.captcha_text) and CAPTCHA["seen"] and CAPTCHA["seen"][-1] == res.captcha_text,
              f"识别「{res.captcha_text}」提交 {CAPTCHA['seen'][-1:]}")
        check("登录后能读墙后页面", "期末考试通知" in cap_sess.get(list_url)[0])

        # 第一次认错 → 应当换一张验证码重试（rounds=2）
        state = {"n": 0}

        def bad_once(data, ch):
            state["n"] += 1
            return ("0000", "") if state["n"] == 1 else (CAPTCHA["code"], "")

        A.set_captcha_solver(bad_once)
        s2 = A.AuthSession(cookie_path=tmp / "cap2.json")
        res = s2.login(USER, PW, service=list_url,
                       settings=replace(A.SETTINGS, captcha_rounds=3))
        check("认错一次会换一张再来", res.ok and res.captcha_rounds == 2,
              f"ok={res.ok} rounds={res.captcha_rounds} 调了 {state['n']} 次 OCR")

        # 一直认错：如实失败，并把验证码图带回去（need_captcha）
        A.set_captcha_solver(lambda data, ch: ("0000", ""))
        s3 = A.AuthSession(cookie_path=tmp / "cap3.json")
        res = s3.login(USER, PW, service=list_url,
                       settings=replace(A.SETTINGS, captcha_rounds=2))
        check("一直认错就说认错（不假装成功）", not res.ok, res.message)
        check("试满了设定轮数", res.captcha_rounds == 2, str(res.captcha_rounds))
        check("把验证码图带回去让人手填",
              res.need_captcha and res.captcha_image.startswith(b"\x89PNG"),
              f"need={res.need_captcha} bytes={len(res.captcha_image)}")
        check("带回去的是 data URL", res.captcha_data_url().startswith("data:image/png;base64,"))

        # 没配 OCR：明确说清楚，而且不空转重试
        A.set_captcha_solver(None)
        _ocr_bak = ocr_mod.SETTINGS
        ocr_mod.SETTINGS = ocr_mod.OCRSettings(provider="none")
        try:
            s4 = A.AuthSession(cookie_path=tmp / "cap4.json")
            res = s4.login(USER, PW, service=list_url)
            check("没配 OCR 时不空转", not res.ok and res.captcha_rounds == 1,
                  f"ok={res.ok} rounds={res.captcha_rounds}")
            check("错误信息指向 OCR 配置", "OCR" in (res.captcha_error or ""),
                  res.captcha_error)
        finally:
            ocr_mod.SETTINGS = _ocr_bak

        # ---- ⑦ 人工兜底 + Web 设置面板 ---- #
        print("\n⑦ 人工填验证码 / Web 设置面板存账号")
        A.set_captcha_solver(lambda data, ch: ("", ""))       # 模拟 OCR 认不出
        s5 = A.AuthSession(cookie_path=tmp / "cap5.json")
        form, text, err = A.begin_login(s5, list_url)
        check("begin_login 把表单与验证码交出来",
              form.ok and form.captcha_field == "captcha" and not text,
              f"field={form.captcha_field} err={err}")
        check("验证码图已经下载", bool(form.challenge and form.challenge.image))
        out = s5.submit_login(form, USER, PW, CAPTCHA["code"])
        check("人工填对验证码能登完", out.ok, out.message)

        # 经 HTTP 走一遍设置面板那条路（真起 web.Handler）
        import harness.config as config_mod
        import harness.web as web_mod

        env_bak = (config_mod.ENV_FILE, web_mod.ENV_FILE)
        tmp_env = tmp / "auth.env"
        config_mod.ENV_FILE = web_mod.ENV_FILE = tmp_env
        A.set_captcha_solver(lambda data, ch: (CAPTCHA["code"], ""))
        A.save_credentials(USER, PW)          # 让 need_captcha 那条路有密码可用
        httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), web_mod.Handler)
        httpd.daemon_threads = True
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        wbase = f"http://127.0.0.1:{httpd.server_address[1]}"
        try:
            st, d = _post(wbase + "/api/settings/auth", {
                "username": USER, "password": PW, "verify": True, "persist": True,
                "auto_login": True, "ocr_captcha": True, "captcha_rounds": 3,
                "service": list_url, "captcha_url": "", "save_password": True})
            check("设置面板登录成功（HTTP 200 + verified）",
                  st == 200 and d.get("ok") and d.get("verified"), f"HTTP {st} {d.get('error')}")
            check("账号密码落盘（.auth/credentials.json）",
                  A.cred_file().is_file() and A.load_credentials()[0] == USER)
            check("会话 cookie 落盘", A.cookie_file().is_file() and A.AuthSession().alive() > 0)
            check("响应里不回显密码", PW not in json.dumps(d, ensure_ascii=False))
            check("账号是打码的", "***" in json.dumps(d.get("credentials") or {}, ensure_ascii=False))
            check("开关写进了 .env",
                  "AUTH_AUTO_LOGIN=1" in tmp_env.read_text(encoding="utf-8")
                  and "AUTH_OCR_CAPTCHA=1" in tmp_env.read_text(encoding="utf-8"))

            st, d = _get(wbase + "/api/settings/auth")
            check("读设置：拿到会话与凭据状态",
                  d.get("credentials", {}).get("username_set") and
                  d.get("session", {}).get("cookies_alive", 0) > 0, str(d.get("session")))

            # OCR 认不出 → 前端拿到图与 token → 人工填一次接着登
            A.set_captcha_solver(lambda data, ch: ("", ""))
            st, d = _post(wbase + "/api/settings/auth", {
                "username": USER, "password": PW, "verify": True, "persist": True,
                "auto_login": True, "ocr_captcha": True, "captcha_rounds": 1,
                "service": list_url, "captcha_url": "", "save_password": True})
            check("OCR 认不出时把验证码图交回前端",
                  d.get("need_captcha") is True and str(d.get("captcha_image", "")).startswith("data:image/"),
                  str(d.get("error")))
            token = d.get("token") or ""
            st, d = _post(wbase + "/api/settings/auth/captcha", {
                "token": token, "captcha": CAPTCHA["code"], "password": PW})
            check("人工填的验证码能把登录做完",
                  st == 200 and d.get("ok") and d.get("verified"), f"HTTP {st} {d.get('error')}")
            st, d = _post(wbase + "/api/settings/auth/captcha", {
                "token": token, "captcha": "1234"})
            check("token 一次性（用过就失效）",
                  st == 400 and "过期" in (d.get("error") or ""), str(d.get("error")))

            st, d = _post(wbase + "/api/settings/auth/logout", {})
            check("退出登录只清会话、保留账号",
                  d.get("ok") and d.get("session", {}).get("cookies_alive") == 0
                  and A.load_credentials()[0] == USER)
            st, d = _post(wbase + "/api/settings/auth/clear", {})
            check("清除凭据真的删掉了文件",
                  d.get("ok") and not A.cred_file().is_file(), str(d.get("message")))
        finally:
            httpd.shutdown()
            httpd.server_close()
            config_mod.ENV_FILE, web_mod.ENV_FILE = env_bak

        # ---- ⑧ 采集时撞到登录墙 → 自动登录 ---- #
        print("\n⑧ Crawler 撞到登录墙自动登录（账号 + OCR）")
        A.set_captcha_solver(lambda data, ch: (CAPTCHA["code"], ""))
        A.SETTINGS = replace(A.SETTINGS, auto_login=True, ocr_captcha=True, captcha_rounds=3)
        A.save_credentials(USER, PW)
        store3 = Store(tmp / "t3.db")
        bare = A.AuthSession(cookie_path=tmp / "auto.json")     # 故意一个 cookie 都没有
        check("起点确实没有会话", bare.alive() == 0)
        crawler3 = Crawler(store3, SETTINGS.crawl, auth_session=bare, check_robots=False)
        check("判定为「可以自动登录」", crawler3.can_auto_login())
        rep3 = crawler3.run([site])
        check("自动登录成功", crawler3.auto_login_report.get("ok") is True,
              str(crawler3.auto_login_report.get("message")))
        check("自动登录用上了 OCR 验证码",
              bool(crawler3.auto_login_report.get("captcha")),
              str(crawler3.auto_login_report.get("captcha")))
        check("登录后登录墙栏目抓取成功", rep3.sites_ok == 1 and store3.count_articles() >= 2,
              f"ok={rep3.sites_ok} 文章={store3.count_articles()}")
        check("只登一次（多线程不会重复刷 CAS）", crawler3._auto_login_state == "ok",
              crawler3._auto_login_state)

        # 关掉自动登录 → 退回「识别登录墙就跳过」
        store4 = Store(tmp / "t4.db")
        bare2 = A.AuthSession(cookie_path=tmp / "auto2.json")
        crawler4 = Crawler(store4, SETTINGS.crawl, auth_session=bare2,
                           check_robots=False, auto_login=False)
        rep4 = crawler4.run([site])
        check("--no-auto-login 时不登录、如实跳过",
              not crawler4.can_auto_login() and rep4.sites_ok == 0
              and store4.count_articles() == 0 and not crawler4.auto_login_report,
              f"ok={rep4.sites_ok} 文章={store4.count_articles()}")

        CAPTCHA["on"] = False
        A.set_captcha_solver(None)
        store.close()
        store2.close()
        store3.close()
        store4.close()
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
