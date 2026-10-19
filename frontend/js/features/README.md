# frontend/js/features/ — 功能模块

每个子目录是一个独立功能，由 `../main.js` 装配：

- `chat/`：对话与 SSE 订阅；
- `calc/`：计算器表单、状态与渲染；
- `settings/`：设置弹窗。

模块之间通过 `shared/events.js` 或 `router.registerView()` 通信，不新增
`window.*` 全局。新增功能时照此建目录，并补一份简短 README。
