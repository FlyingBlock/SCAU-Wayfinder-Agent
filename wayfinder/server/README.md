# wayfinder/server/ — HTTP 传输层

只负责「把字节收进来、把字节发出去」，不认识业务，也不认识具体前端页面。

## 文件

| 文件 | 作用 |
|---|---|
| `http.py` | `Handler`、`ApplicationServer`、`serve()`、静态资源与 SSE 写出 |

`Request` / `Response` / `Router` 在 `wayfinder/protocol/http.py`：传输层和
`api/` 都依赖它，但 `server` 与 `api` 互不 import。

## 路由规则

| 路径 | 行为 |
|---|---|
| `/assets/<path>` | 返回 `frontend/<path>`（resolve 后做目录前缀校验） |
| `/api/<path>` | 查路由表，未命中 404 JSON |
| 其它无扩展名的 GET | 返回 `frontend/index.html`（通用 SPA 回退） |

传输层不认识 `/calc`、`/calc-docs` 这类具体页面；前端 hash 路由自己负责。
设置写接口（`POST /api/settings/*`）额外校验 `Origin` / `Sec-Fetch-Site` 与
`Content-Type: application/json`，降低本机浏览器被跨站请求利用的风险。

## 响应类型

- `protocol.json_response(obj)`：标准 JSON，`no-store`；
- `protocol.sse_response(events)`：`text/event-stream`，逐条 `event:` + `data:` 并 flush；
- `file_response(path)`：静态文件；
- `protocol.Response(status, body, content_type, headers)`：自定义。

## 边界

- 业务错误由 API 层返回；这里只兜底 500，避免连接悬挂。
- 静态文件只允许 `frontend/` 内的真实路径（防 `../` 穿越）。
- 不引入框架：标准库 `http.server` + `ThreadingHTTPServer` 足够单用户使用。
