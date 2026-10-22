# frontend/js/features/ — 功能模块

每个子目录是一个独立功能，由 `../main.js` 装配：

- `chat/`：对话与 SSE 订阅；`content.js` 负责正文/引用，`cards.js` 负责卡片；
- `calc/`：计算器；`activities.js` 负责活动篮列表（后端筛选），`state.js` 持有状态；
- `settings/`：设置弹窗。

模块之间通过 `shared/events.js` 或 `router.registerView()` 通信，不新增
`window.*` 全局。唯一的跨功能直接依赖是对话页入篮调用
`calc/state.js#addToBasket()`（共享同一份活动篮状态）；设置弹窗通过
`settings:open` 事件打开。新增功能时照此建目录，并补一份简短 README。
