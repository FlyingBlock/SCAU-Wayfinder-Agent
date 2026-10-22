# wayfinder/protocol/ — 共享协议原语

`Request` / `Response` / `Router` / `HandlerFn` / `json_response` / `sse_response`。

`api/`（协议适配）与 `server/`（HTTP 传输）都依赖这里，但两者互不 import：
换传输层不用改 API，换 API 风格也不用改 socket 代码。真正的业务处理函数
仍住在 `wayfinder/api/`，这里只有数据结构与序列化辅助。
