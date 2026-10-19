# frontend/js/shared/ — 共享基础设施

只放与业务无关的小工具：

- `dom.js`：`$` / `$$` / `esc`。
- `api.js`：`requestJSON` / `getJSON` / `postJSON`，统一 fetch 与错误处理。
- `events.js`：`on` / `emit`，功能模块之间的唯一通信方式。
- `format.js`：数字展示格式化。
- `toast.js`：底部轻提示。

这里不 import 任何 feature，也不读写业务状态。
