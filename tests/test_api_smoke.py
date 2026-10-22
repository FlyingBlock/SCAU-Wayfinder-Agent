"""接口冒烟：真起 HTTP 服务，把所有只读接口与一条写接口打一遍。

跑法：
    python tests/test_api_smoke.py

不联网、不调模型：用空的临时库，`/api/ask` 用 `dry=1` 且库内无文章，
只会返回「请先抓取」的提示。目的不是验业务细节（那在各自的测试里），
而是保证重构后**路由、序列化、静态资源、错误码**仍然接得上。
"""
from __future__ import annotations

import http.client
import json
import shutil
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(errors="replace")           # type: ignore[union-attr]
    except (AttributeError, OSError, ValueError):
        pass

from wayfinder.api.registry import build_router               # noqa: E402
from wayfinder.core.config import CrawlSettings, SETTINGS    # noqa: E402
from wayfinder.server.http import ApplicationServer           # noqa: E402
from wayfinder.services import Services                       # noqa: E402

FAILURES: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(("  ✓ " if cond else "  ✗ ") + msg)
    if not cond:
        FAILURES.append(msg)


class Client:
    def __init__(self, port: int) -> None:
        self.port = port

    def _request(self, method: str, path: str, body: dict | None = None,
                 extra_headers: dict[str, str] | None = None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=60)
        payload = json.dumps(body).encode() if body is not None else None
        headers = {"Content-Type": "application/json"} if payload else {}
        headers.update(extra_headers or {})
        conn.request(method, path, body=payload, headers=headers)
        resp = conn.getresponse()
        raw = resp.read()
        ctype = resp.getheader("Content-Type") or ""
        conn.close()
        return resp.status, ctype, raw

    def get(self, path: str):
        return self._request("GET", path)

    def post(self, path: str, body: dict, headers: dict[str, str] | None = None):
        return self._request("POST", path, body, headers)


def main() -> int:
    print("=" * 74)
    print("接口冒烟（真 HTTP 服务 / 空临时库 / 不联网）")
    print("=" * 74)

    tmp = ROOT / "_test_tmp" / "api"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True, exist_ok=True)
    original = SETTINGS.crawl
    httpd = None
    try:
        SETTINGS.crawl = CrawlSettings(data_dir=tmp)
        httpd = ApplicationServer(("127.0.0.1", 0),
                                  build_router(Services(settings=SETTINGS)))
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        c = Client(httpd.server_address[1])

        print("\n[静态资源]")
        st, ctype, raw = c.get("/")
        check(st == 200 and "text/html" in ctype and b"SCAU Wayfinder" in raw,
              "GET / 返回单页应用")
        st, _, raw = c.get("/calc/acts")
        check(st == 200 and b'id="view-calc"' in raw, "深链接 /calc/acts 不 404")
        st, _, raw = c.get("/assets/js/main.js")
        check(st == 200 and b"registerView" in raw, "GET /assets/js/main.js")
        st, _, raw = c.get("/assets/css/calc.css")
        check(st == 200 and b"#view-calc" in raw, "GET /assets/css/calc.css")

        print("\n[只读 JSON 接口]")
        st, _, raw = c.get("/api/status")
        d = json.loads(raw)
        check(st == 200 and d.get("articles") == 0 and "llm_configured" in d,
              "GET /api/status")
        st, _, raw = c.get("/api/settings/llm")
        check(st == 200 and json.loads(raw).get("presets"), "GET /api/settings/llm")
        st, _, raw = c.get("/api/settings/ocr")
        check(st == 200 and "provider" in json.loads(raw), "GET /api/settings/ocr")
        st, _, raw = c.get("/api/settings/auth")
        d = json.loads(raw)
        check(st == 200 and "credentials" in d and "session" in d,
              "GET /api/settings/auth")
        st, _, raw = c.get("/api/calc/catalog")
        cat = json.loads(raw)
        check(st == 200 and len(cat.get("majors", [])) == 2
              and len(cat.get("activities", [])) > 100, "GET /api/calc/catalog")
        st, _, raw = c.get("/api/calc/catalog?activities=0")
        slim = json.loads(raw)
        check(st == 200 and "activities" not in slim and "majors" in slim,
              "GET /api/calc/catalog?activities=0（首屏瘦身）")
        st, _, raw = c.get("/api/calc/target?gpa=3.2&major=biotech")
        check(st == 200 and isinstance(json.loads(raw), dict), "GET /api/calc/target")
        st, _, raw = c.get("/api/calc/activities?kind=competition&scored=1")
        d = json.loads(raw)
        check(st == 200 and d.get("filtered", 0) > 0
              and d.get("filtered", 0) <= d.get("total", 0),
              "GET /api/calc/activities（后端筛选）")
        st, _, raw = c.get("/api/search?q=%E6%8C%91%E6%88%98%E6%9D%AF")
        d = json.loads(raw)
        check(st == 200 and d.get("total") == 0 and d.get("hits") == [],
              "GET /api/search（空库返回空列表）")

        print("\n[写接口]")
        st, _, raw = c.post("/api/calc/evaluate",
                            {"profile": {"major_id": "biotech", "scores": {}},
                             "basket": []})
        d = json.loads(raw)
        check(st == 200 and "gpa" in d and "comprehensive" in d,
              "POST /api/calc/evaluate")

        print("\n[SSE]")
        st, ctype, raw = c.get("/api/ask?dry=1&q=abc")
        text = raw.decode("utf-8", "replace")
        check(st == 200 and "text/event-stream" in ctype
              and "event: answer" in text and "event: done" in text,
              "/api/ask 无语料时仍以 SSE 返回 answer + done")

        print("\n[错误码]")
        st, _, _ = c.get("/api/not-exist")
        check(st == 404, "未知接口 404")
        st, _, _ = c.get("/assets/../.env")
        check(st == 403, "静态资源路径穿越 403")
        st, _, _ = c.post("/api/settings/llm", {"base_url": "ftp://x"})
        check(st == 400, "非法 base URL 400")
        st, _, _ = c.post("/api/settings/llm",
                          {"base_url": "https://evil.example"},
                          headers={"Origin": "https://evil.example"})
        check(st == 403, "跨站设置写请求 403")
    finally:
        SETTINGS.crawl = original
        if httpd is not None:
            httpd.shutdown()
            httpd.server_close()
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n" + "=" * 74)
    if FAILURES:
        print(f"❌ {len(FAILURES)} 项未通过")
        return 1
    print("✅ 全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
