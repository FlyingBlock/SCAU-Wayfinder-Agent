# frontend/js/features/chat/ — 对话

负责对话页的输入、SSE 订阅、Markdown/引用来源栏与卡片渲染。

- `chatBind()` 绑定输入框、发送/只检索按钮、引用栏开合；
- `chatAsk()` 订阅 `/api/ask` 的 `trace` / `answer_delta` / `answer_end` /
  `answer` / `cards` / `done`；
- `traceText()` 把后端的 `{step, data}` 翻成界面文案；
- 卡片里的「加入活动篮」调用 `../calc/state.js` 的 `addToBasket()`，不直接写 localStorage。

后端只推送数据和事件，不负责这里的排版/文案。
