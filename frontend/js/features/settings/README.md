# frontend/js/features/settings/ — 设置弹窗

模型 / 附件与 OCR / 账号与登录三个分页的 UI 与请求绑定。

- `bindSettings()` 在 `main.js` 启动时绑定 DOM，并监听 `settings:open` 事件；
- 通过 `shared/api.js` 调用 `/api/settings/*`；
- 保存成功后只 `emit('status:refresh')`，由对话页自己刷新状态，
  不直接调用聊天模块；
- 密钥只以掩码显示，密码不回显。
