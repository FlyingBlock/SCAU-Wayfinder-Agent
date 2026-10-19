# wayfinder/settings/ — 设置服务

模型 / OCR / 登录配置的校验、落盘与「不用重启就生效」。

## 文件

| 文件 | 作用 |
|---|---|
| `commands.py` | 用例层：权限、校验、真实调用验证、落盘、登录编排，返回 `(dict, status)` |
| `service.py` | 底层：`apply_*_settings()`、`*_state()`、登录动作与待续验证码 |

## 三类配置的统一规矩

1. **留空 = 沿用当前值**（key 不回显，不能要求用户重填）；
2. 先原地更新当前进程（传入的 `Settings.llm` / OCR / AUTH 设置对象），再按需合并写 `.env`；
3. 写盘失败只作为 `warning` 返回，不阻断「本次运行已生效」。

API 层的 `api/settings.py` 只转发 `commands.*`；CLI 也复用同一组用例，
不再各自维护一套校验/验证流程。

## 登录

- 账号密码**只落** `.auth/credentials.json`，不写 `.env`。
- `do_login()` 走 CAS；OCR 认不出验证码时返回 `need_captcha` + 图 + 一次性 token。
- `complete_captcha()` 用人工填的验证码续登；token 5 分钟过期、用一次即失效。
- 设置面板与 CLI 的 `login` 共用 `crawl/auth.py`，不会出现两套行为。

## 安全

- 改配置只允许本机请求（`Request.local`）；非本机返回 403。
- 响应里 key 只回显掩码，密码永不回显。
- 环境变量优先级高于 `.env` 时，`*_state()` 会返回 `shadowed` 让界面提示用户。
