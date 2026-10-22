"""请求 / 响应 / 路由 / JSON / SSE 的共享协议原语。

这一层只描述“一次调用长什么样”，不负责监听端口、不读 socket、不碰业务。
`wayfinder/api/` 用它表达返回值，`wayfinder/server/` 用它把值写回连接。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Callable, Iterable


@dataclass
class Request:
    """一次协议请求；由具体传输层（当前是 http.server）填充。"""

    method: str
    path: str
    query: dict[str, str] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    body: dict = field(default_factory=dict)
    client_host: str = ""

    @property
    def local(self) -> bool:
        """请求是否来自本机（设置写接口的最小防线之一，不是认证）。"""
        return self.client_host in (
            "127.0.0.1", "::1", "localhost", "::ffff:127.0.0.1",
        )


@dataclass
class Response:
    """一次协议响应：普通 body 或 SSE 事件流，二者取其一。"""

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


def sse_response(events: Iterable[tuple[str, dict]]) -> Response:
    return Response(
        status=200,
        stream=events,
        content_type="text/event-stream; charset=utf-8",
        headers={"Cache-Control": "no-cache",
                 "X-Accel-Buffering": "no",
                 "Connection": "close"},
    )


HandlerFn = Callable[[Request], Response]


class Router:
    """精确路径路由表；不依赖传输层，server 与测试都可以直接使用。"""

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
