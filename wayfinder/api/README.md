# wayfinder/api/ — 协议适配层

把领域能力暴露成 JSON / SSE。**不含 UI、不拼 HTML**。

## 文件

| 文件 | 作用 |
|---|---|
| `registry.py` | 路由表装配（新增接口只改这里） |
| `chat.py` | `/api/ask` 的 SSE 流（结构化 trace / answer_delta / answer / cards / done） |
| `corpus.py` | 状态、检索、正文、附件、本地文件 |
| `calculator.py` | 计算器目录、求值、目标分、名录联网刷新 |
| `settings.py` | 模型 / OCR / 登录设置：只转发给 `settings/commands.py` |

## 处理函数契约

```python
def handler(request: Request, services: Services) -> Response
```

- 只做参数解析、权限判断、调用用例/领域层、序列化结果；
- 不直接开 socket，不写 `<script>`，不读环境变量（走 `services.settings`）；
- 设置类业务逻辑在 `settings/commands.py`，本层只传 `req.local` / `req.body`；
- 错误用 `error_response()` / 业务 JSON（如 `{"ok": False, "error": ...}`）；
- SSE 用 `sse_response(events)`，事件是 `(event_name, data_dict)` 序列；
  `trace` 只推 `{step, data}`，展示文案由前端生成。

## 新增接口

1. 在本目录新建或扩展一个模块；
2. 写 `fn(req, svc) -> Response`；
3. 在 `registry.build_router()` 注册；
4. 在根 README 的接口表补一行；
5. 需要测试就在 `tests/` 里起 `ApplicationServer` 打真实请求。
