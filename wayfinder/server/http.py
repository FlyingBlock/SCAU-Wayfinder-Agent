"""HTTP 传输层：路由分发、静态资源、JSON 与 SSE 帧格式。

这一层**不认识业务**：它只把 `Request` 交给注册好的处理函数，再把返回的
`Response` 写回 socket。业务处理函数住在 `wayfinder/api/`，界面住在 `frontend/`。

路由规则：
  · `GET /`、`/calc`、`/calc/<sub>`、`/calc-docs`  → `frontend/index.html`
    （单页应用的 hash 路由由前端负责，服务端只保证深链接不 404）
  · `GET /assets/<path>`                            → `frontend/<path>`
  · 其余路径查路由表                                  → `Response`
"""
from __future__ import annotations

import json
import mimetypes
import socket
import sys
import threading
import urllib.parse
import webbrowser
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable, Iterable

from ..core.config import ROOT

FRONTEND_DIR = ROOT / "frontend"

#: SPA 深链接：这些路径都返回同一份 index.html，由前端 hash 路由落到具体视图。
SPA_PATHS = ("/", "/index.html", "/calc", "/calc/", "/calc-docs", "/calc-docs/")


# --------------------------------------------------------------------------- #
# 请求 / 响应
# --------------------------------------------------------------------------- #
@dataclass
class Request:
    method: str
    path: str
    query: dict[str, str] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    body: dict = field(default_factory=dict)
    client_host: str = ""

    @property
    def local(self) -> bool:
        return self.client_host in ("127.0.0.1", "::1", "localhost", "::ffff:127.0.0.1")


@dataclass
class Response:
    status: int = 200
    body: bytes = b""
    content_type: str = "application/json; charset=utf-8"
    headers: dict[str, str] = field(default_factory=dict)
    #: SSE 事件流：(event, data) 序列；有它时忽略 body。
    stream: Iterable[tuple[str, dict]] | None = None


def json_response(obj, status: int = 200) -> Response:
    return Response(status=status,
                    body=json.dumps(obj, ensure_ascii=False).encode("utf-8"))


def error_response(message: str, status: int = 400, **extra) -> Response:
    payload = {"ok": False, "error": message}
    payload.update(extra)
    return json_response(payload, status)


def file_response(path: Path) -> Response:
    ctype = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    if ctype.startswith("text/") or ctype in ("application/javascript", "application/json"):
        ctype += "; charset=utf-8"
    return Response(status=200, body=path.read_bytes(), content_type=ctype)


def sse_response(events: Iterable[tuple[str, dict]]) -> Response:
    return Response(status=200, stream=events,
                    content_type="text/event-stream; charset=utf-8",
                    headers={"Cache-Control": "no-cache",
                             "X-Accel-Buffering": "no",
                             "Connection": "close"})


# --------------------------------------------------------------------------- #
# 路由表
# --------------------------------------------------------------------------- #
HandlerFn = Callable[[Request], Response]


class Router:
    """精确路径路由表。业务简单，不需要参数化路由。"""

    def __init__(self) -> None:
        self._routes: dict[tuple[str, str], HandlerFn] = {}

    def add(self, method: str, path: str, fn: HandlerFn) -> "Router":
        self._routes[(method.upper(), path)] = fn
        return self

    def get(self, path: str, fn: HandlerFn) -> "Router":
        return self.add("GET", path, fn)

    def post(self, path: str, fn: HandlerFn) -> "Router":
        return self.add("POST", path, fn)

    def match(self, method: str, path: str) -> HandlerFn | None:
        return self._routes.get((method.upper(), path))

    def paths(self) -> list[tuple[str, str]]:
        return sorted(self._routes)


# --------------------------------------------------------------------------- #
# 服务器
# --------------------------------------------------------------------------- #
class ApplicationServer(ThreadingHTTPServer):
    """携带路由表与前端的 HTTP 服务器。"""

    daemon_threads = True

    def __init__(self, address, router: Router, frontend_dir: Path = FRONTEND_DIR):
        super().__init__(address, Handler)
        self.router = router
        self.frontend_dir = Path(frontend_dir)


class Handler(BaseHTTPRequestHandler):
    server_version = "SCAUWayfinder/0.2"
    protocol_version = "HTTP/1.1"

    # ------------------------------------------------------------------ #
    def log_message(self, fmt, *args):  # noqa: D401 - 安静一点，只保留错误
        text = str(args[1]) if len(args) > 1 else ""
        if text.startswith(("4", "5")):
            sys.stderr.write("[http] " + fmt % args + "\n")

    def _request(self) -> Request:
        parts = urllib.parse.urlsplit(self.path)
        query = {k: v[0] for k, v in urllib.parse.parse_qs(parts.query).items()}
        headers = {k.lower(): v for k, v in self.headers.items()}
        return Request(
            method=self.command,
            path=parts.path,
            query=query,
            headers=headers,
            body=self._read_body(),
            client_host=(self.client_address or ("",))[0],
        )

    def _read_body(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8", "ignore") or "{}")
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    # ------------------------------------------------------------------ #
    def do_GET(self) -> None:  # noqa: N802
        self._dispatch()

    def do_POST(self) -> None:  # noqa: N802
        self._dispatch()

    def _dispatch(self) -> None:
        try:
            req = self._request()
            response = self._route(req)
            self._write(req, response)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:  # noqa: BLE001 - 传输层兜底，避免连接悬挂
            try:
                self._write_json(500, {"error": f"{type(e).__name__}: {e}"})
            except Exception:
                pass

    def _route(self, req: Request) -> Response:
        if req.method == "GET":
            if req.path == "/favicon.ico":
                return Response(status=204, body=b"", content_type="image/x-icon")
            if req.path in SPA_PATHS or req.path.startswith("/calc/"):
                return self._static("index.html")
            if req.path.startswith("/assets/"):
                return self._static(req.path[len("/assets/"):])
        handler = self.server.router.match(req.method, req.path)
        if handler is None:
            return json_response({"error": "not found"}, 404)
        return handler(req)

    # ------------------------------------------------------------------ #
    def _static(self, rel: str) -> Response:
        """只允许发 frontend/ 目录内的文件（realpath 后判断前缀）。"""
        base = self.server.frontend_dir.resolve()
        target = (base / rel).resolve()
        if target != base and base not in target.parents:
            return json_response({"error": "越权路径"}, 403)
        if not target.is_file():
            return json_response({"error": "not found"}, 404)
        return file_response(target)

    # ------------------------------------------------------------------ #
    def _write(self, req: Request, response: Response) -> None:
        if response.stream is not None:
            self._write_sse(response)
            return
        self.send_response(response.status)
        self.send_header("Content-Type", response.content_type)
        self.send_header("Content-Length", str(len(response.body)))
        self.send_header("Cache-Control", "no-store")
        for key, val in response.headers.items():
            self.send_header(key, val)
        self.end_headers()
        if req.method != "HEAD":
            self.wfile.write(response.body)

    def _write_sse(self, response: Response) -> None:
        self.send_response(response.status)
        self.send_header("Content-Type", response.content_type)
        for key, val in response.headers.items():
            self.send_header(key, val)
        self.end_headers()
        for event, data in response.stream:
            payload = f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
            self.wfile.write(payload.encode("utf-8"))
            self.wfile.flush()

    def _write_json(self, status: int, obj) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)


# --------------------------------------------------------------------------- #
# 启动
# --------------------------------------------------------------------------- #
def port_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


def serve(router: Router, *, host: str = "127.0.0.1", port: int = 8848,
          open_browser: bool = True) -> int:
    """传输层入口：建服务器、打印地址、阻塞运行。"""
    if not port_free(host, port):
        print(f"端口 {port} 已被占用。换一个： python -m wayfinder web --port 8849",
              file=sys.stderr)
        return 2
    httpd = ApplicationServer((host, port), router)
    url = f"http://{host}:{port}/"
    print("=" * 70)
    print(f"SCAU Wayfinder 已启动： {url}")
    print("  Ctrl+C 停止")
    print("=" * 70)
    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
    finally:
        httpd.server_close()
    return 0
