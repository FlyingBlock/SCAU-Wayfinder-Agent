# frontend/ — 纯静态前端

单页应用，无构建步骤、无第三方库。**只负责界面组织与订阅**：不计算绩点、
不做业务匹配、不生成业务数据；分数、绩点、最佳成就和通道口径都由 `/api/*` 返回。
活动篮的筛选/排序也走后端 `/api/calc/activities`，浏览器只渲染结果。

## 入口与目录

```text
index.html                  # 只做结构，不写内联脚本
js/main.js                  # 入口：注册视图元数据、绑定事件、启动路由
js/router.js                # hash 路由 / 视图切换 / 侧栏；视图元数据由 feature 注册
js/shared/                  # dom / api / events / format / toast
js/features/chat/
  index.js                  # 输入、SSE 订阅、流式状态机
  content.js                # Markdown、[n] 引用、右侧来源栏
  cards.js                  # 活动 / 附件 / 时间卡片与入篮
js/features/calc/
  index.js                  # 表单、课程表、指标、门槛、口径页
  activities.js             # 活动篮：调用后端筛选/排序并渲染卡片
  state.js                  # 计算器状态与 localStorage 的唯一读写入口
js/features/settings/       # 设置弹窗（模型 / OCR / 登录）
css/shell.css               # 外壳、侧栏、对话、引用栏、设置弹窗
css/calc.css                # 计算器样式，限定在 #view-calc
```

## 边界约定

- 功能模块之间通过 `shared/events.js` 或 `router.registerView()` 通信：
  设置保存后发 `status:refresh`，对话页点设置发 `settings:open`；
  对话页入篮走 `features/calc/state.js` 的 `addToBasket()`，不直接写 localStorage。
- 计算器不再自己算绩点、最佳成就或通道评分表：
  - 绩点列读 `d.gpa.courses[].effective_gp`；
  - 活动卡读 `activity.best`；
  - 活动列表读 `/api/calc/activities`（后端筛选/排序）；
  - 通道单位/评分表读 catalog 的 `channel_units` / `channel_rubric`。
- `localStorage` 的 `scau-calc-state-v1` 只允许在 `features/calc/state.js` 出现。
- 后端 SSE 的 `trace` 事件是结构化 `{step, data}`，中文步骤文案在
  `features/chat/index.js` 的 `traceText()` 里生成；已知错误由 `{code}` 映射。

## 修改后

刷新页面即可（静态文件不缓存：服务端 `Cache-Control: no-store`）。
没有 watcher，也不需要重启后端。
