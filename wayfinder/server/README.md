# wayfinder/server/ — HTTP 传输层

只负责「把字节收进来、把字节发出去」，不认识任何业务。

## 文件

| 文件 | 作用 |
|---|---|
| `http.py` | `Request` / `Response`、`Router`、`Handler`、`ApplicationServer`、`serve()` |

## 路由规则

| 路径 | 行为 |
|---|---|
| `/`、`/calc`、`/calc/<sub>`、`/calc-docs` | 返回 `frontend/index.html`（SPA 深链接不 404） |
| `/assets/<path>` | 返回 `frontend/<path>`（resolve 后做目录前缀校验） |
| 其它 | 查 `Router`，未命中返回 404 JSON |

## 响应类型

- `json_response(obj)`：标准 JSON，`no-store`；
- `sse_response(events)`：`text/event-stream`，逐条 `event:` + `data:` 并 flush；
- `file_response(path)`：静态文件；
- `Response(status, body, content_type, headers)`：自定义。

## 边界

- 业务错误由 API 层抛/返回；这里只兜底 500，避免连接悬挂。
- 静态文件只允许 `frontend/` 内的真实路径（防 `../` 穿越）。
- 不引入框架：标准库 `http.server` + `ThreadingHTTPServer` 足够单用户使用。
