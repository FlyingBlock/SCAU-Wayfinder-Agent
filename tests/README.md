# tests/ — 离线自测

全部不联网、不花 token：假站点 / 假 OpenAI 端点 / 临时 SQLite 库。

## 运行

```powershell
python tests/test_architecture.py # 依赖方向、组装根、前端职责边界
python tests/test_app_shell.py    # ES Module 装配、作用域样式、node 解析
python tests/test_api_smoke.py    # 全部只读接口 + evaluate + SSE + 404/403
python tests/test_cards_api.py    # 真起 HTTP 服务，验 /api/ask 的 SSE cards 事件
python tests/test_stream.py       # 流式增量 / 思维链截断 / 不支持 stream 的退路
python tests/test_auth.py         # CAS 登录、验证码、Cookie、采集自动登录、设置面板
```

也可以一次跑完：`foreach ($f in Get-ChildItem tests\test_*.py) { python $f.FullName }`。

## 约定

- 临时数据放仓库根 `_test_tmp/`，测完删掉；不用系统临时目录（沙箱 ACL 可能拒绝）。
- 每个测试用 `Services(SETTINGS)`（或 `build_services(settings)`）构造依赖，
  不再直接改 `wayfinder.services.Services` 的默认全局。
- 起 HTTP 服务的测试：`ApplicationServer(("127.0.0.1", 0), build_router(Services(SETTINGS)))`，
  用随机端口，测完 `shutdown()`。
- 改全局配置（如 `SETTINGS.crawl`、`ENV_FILE`）的测试必须在 `finally` 里还原。
- 新增领域模块时优先补纯函数测试；跨层链路用 `test_cards_api.py` 的方式起真服务。
- 改前端结构时同步更新 `test_app_shell.py`，不要再用 `core.js` / `chat.js` / `calc.js` 旧路径。
