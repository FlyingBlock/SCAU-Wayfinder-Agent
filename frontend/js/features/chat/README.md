# frontend/js/features/chat/ — 对话

负责对话页的输入、SSE 订阅、Markdown/引用来源栏与卡片渲染。

- `index.js`：`chatBind()` 绑定输入框/按钮，`chatAsk()` 订阅 `/api/ask`，
  `traceText()` 把后端的 `{step, data}` 翻成界面文案，已知错误码由
  `answerErrorText()` 映射；
- `content.js`：`mdChat()`、`SOURCES`、右侧来源栏、`[n]` 点击跳转；
- `cards.js`：活动 / 附件 / 时间卡片；入篮调用 `../calc/state.js` 的
  `addToBasket()`，不直接写 localStorage；
- 设置入口通过 `events.emit('settings:open')`，不直接 import 设置模块。

后端只推送数据和事件，不负责这里的排版/文案。
