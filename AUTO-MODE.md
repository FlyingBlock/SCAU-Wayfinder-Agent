# ⚡ 全自动模式操作审计（dsh-model-fallback）

> 本文件由插件「全自动模式」自动写入：所有被自动允许的权限审批与自动应答的人工确认都会记录在此。
> 关闭方法：设置 → 全自动模式 → 关闭「启用全自动模式」。

| 时间 | 类型 | 内容 | 结果 |
| --- | --- | --- | --- |
| 2026-10-14T16:19:32.026Z | 权限审批 | 工具 pwsh — escalate sandbox to danger-full-access: 继续调试同一份离线自测脚本：这次打印假站点 CAS 重定向响应的原始 HTTP 头，确认 Set-Cookie 到底有没有发出来、格式对不对。需要 Python 在工作区写 __pycache__；只访问 127.0.0.1，不连学校站点。 | 已自动允许 |
| 2026-10-14T16:19:51.038Z | 权限审批 | 工具 pwsh — escalate sandbox to danger-full-access: 跑修好假站点后的同一份离线自测脚本，验证登录、Cookie 保存复用、带会话抓取入库整条链路。需要 Python 在工作区写临时测试库与 __pycache__，当前权限仍挡着这类写入。只访问 127.0.0.1，不连学校站点，不用真实账号… | 已自动允许 |
| 2026-10-14T16:20:06.770Z | 权限审批 | 工具 pwsh — escalate sandbox to danger-full-access: 继续调试离线自测：打印登录会话实际使用的 cookie 落盘路径与目录内容，定位「Cookie 没写进文件」的原因。需要 Python 在工作区写 __pycache__；只访问 127.0.0.1。 | 已自动允许 |
| 2026-10-14T16:20:25.303Z | 权限审批 | 工具 pwsh — escalate sandbox to danger-full-access: 跑离线自测脚本验证登录、Cookie 落盘复用、带会话抓取入库整条链路。需要 Python 在工作区写 __pycache__（当前权限仍挡着这类写入）；只访问 127.0.0.1，不连学校站点，不用真实账号。 | 已自动允许 |
| 2026-10-14T16:20:45.233Z | 权限审批 | 工具 pwsh — escalate sandbox to danger-full-access: 打印带会话直取列表页的返回内容，定位采集层为何解析不出条目。需要 Python 在工作区写 __pycache__；只访问 127.0.0.1。 | 已自动允许 |
| 2026-10-14T16:21:05.947Z | 权限审批 | 工具 pwsh — escalate sandbox to danger-full-access: 跑离线自测脚本验证登录、Cookie 落盘复用、带会话抓取入库整条链路。需要 Python 在工作区写 __pycache__（当前权限仍挡着这类写入）；只访问 127.0.0.1，不连学校站点，不用真实账号。 | 已自动允许 |
| 2026-10-14T16:21:22.285Z | 权限审批 | 工具 pwsh — escalate sandbox to danger-full-access: 跑离线自测脚本验证登录、Cookie 落盘复用、带会话抓取入库，以及无会话时正确判定登录墙。需要 Python 在工作区写 __pycache__；只访问 127.0.0.1，不连学校站点，不用真实账号。 | 已自动允许 |
| 2026-10-14T16:21:43.228Z | 权限审批 | 工具 pwsh — escalate sandbox to danger-full-access: 回归跑离线自测脚本，确认登录墙识别改造后整条链路仍然通过。需要 Python 在工作区写 __pycache__；只访问 127.0.0.1，不连学校站点，不用真实账号。 | 已自动允许 |
| 2026-10-14T16:21:54.288Z | 权限审批 | 工具 pwsh — escalate sandbox to danger-full-access: 跑离线自测回归，并冒烟测试新增的 login/whoami 命令能否正常启动（whoami 只读 .auth/ 状态）。需要 Python 在工作区写 __pycache__；只访问本机，不连学校站点。 | 已自动允许 |
| 2026-10-14T16:22:01.940Z | 权限审批 | 工具 pwsh — escalate sandbox to danger-full-access: 跑 doctor 自检确认新增的「登录会话」状态行不会破坏原有体检输出。需要 Python 在工作区写 __pycache__；不访问学校站点（--no-llm 且不实测公网）。 | 已自动允许 |
| 2026-10-14T16:22:40.811Z | 权限审批 | 工具 pwsh — escalate sandbox to danger-full-access: 回归跑离线自测并确认重构后的 cookie 路径常量与函数一致。需要 Python 在工作区写 __pycache__；只访问 127.0.0.1。 | 已自动允许 |
| 2026-10-14T16:23:00.516Z | 权限审批 | 工具 pwsh — escalate sandbox to danger-full-access: 最后一次回归跑离线自测脚本，确认 cookie 导入的 secure 属性调整后全部用例仍通过。需要 Python 在工作区写 __pycache__；只访问 127.0.0.1，不连学校站点。 | 已自动允许 |
| 2026-10-15T12:22:30.345Z | 权限审批 | 工具 pwsh — escalate sandbox to danger-full-access: 回归自测需要 Python 在工作区写 __pycache__ 与临时测试库，被文件沙箱挡住；测试只访问 127.0.0.1 的假端点，不连学校站点、不调用真实模型。 | 已自动允许 |
| 2026-10-15T12:30:13.194Z | 权限审批 | 工具 pwsh — escalate sandbox to danger-full-access: 这是纯视觉布局改动，需要在真实浏览器里截图确认「右栏贴在窗口最右侧、不占正文宽度」，而沙箱禁止浏览器所需的命名管道。 | 已自动允许 |
| 2026-10-15T12:30:32.301Z | 权限审批 | 工具 pwsh — escalate sandbox to danger-full-access: 继续用真实浏览器截图确认右栏在开屏默认状态（无 localStorage 偏好）下于 1290/1300 断点两侧的表现，沙箱仍禁止浏览器启动。 | 已自动允许 |
| 2026-10-15T12:31:19.197Z | 权限审批 | 工具 pwsh — escalate sandbox to danger-full-access: 需要真实浏览器报出主区/右栏的实际像素宽度，以确认并排与浮层的切换点；沙箱禁止浏览器启动。 | 已自动允许 |
| 2026-10-15T12:32:11.894Z | 权限审批 | 工具 pwsh — escalate sandbox to danger-full-access: 用真实浏览器复核改完的 sourcesInline() 与 CSS 断点是否一致，并刷新给用户看的布局截图；沙箱禁止浏览器启动。 | 已自动允许 |
