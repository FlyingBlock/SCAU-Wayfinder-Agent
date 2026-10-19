# frontend/js/ — 前端模块

ES Module 入口是 `main.js`；只做装配与启动。

- `router.js`：hash 路由、视图切换、侧栏；通过 `registerView()` 回调功能模块。
- `shared/`：DOM、HTTP、事件总线、格式化、toast，均不持有业务状态。
- `features/chat/`：对话与 SSE 订阅，展示文案/引用栏/卡片由前端负责。
- `features/calc/`：计算器表单与渲染；`state.js` 是 localStorage 唯一入口。
- `features/settings/`：模型 / OCR / 登录设置弹窗。

新增功能时新建 `features/<name>/index.js`，在 `main.js` 里注册并绑定入口；
不要新增 `window.*` 全局，也不要从别的 feature 直接读写 DOM 状态。
