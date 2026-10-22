# frontend/js/ — 前端模块

ES Module 入口是 `main.js`；只做装配与启动。

- `router.js`：hash 路由、视图切换、侧栏；视图标题/子页由 `registerView()` 注册，
  router 不再维护计算器页签表。
- `shared/`：DOM、HTTP、事件总线、格式化、toast，均不持有业务状态。
- `features/chat/`：`index.js` 订阅 SSE；`content.js` 渲染正文/引用；`cards.js` 渲染卡片。
- `features/calc/`：`index.js` 负责表单/结果；`activities.js` 负责活动篮列表
  （后端筛选/排序）；`state.js` 是 localStorage 唯一入口。
- `features/settings/`：模型 / OCR / 登录设置弹窗；通过 `settings:open` 事件被打开。

新增功能时新建 `features/<name>/index.js`，在 `main.js` 里注册并绑定入口；
不要新增 `window.*` 全局，也不要从别的 feature 直接读写 DOM 状态。
