# wayfinder/ — 后端包

后端只做「取值、计算、推送数据」，不生成任何 HTML/CSS/JS。

## 依赖方向

```
main.py ──► cli.py ──► commands/* ──► app.py ──► api/ ──► services/ 领域层
                                             │
api/ ──┐                                     └──► protocol/http.py
       ├──► protocol/http.py（Request/Response/Router）
server/┘
core/  ◄── 所有层（配置、路径、纯工具）
```

- `core/`：最底层，只有配置、路径、URL 归一化等纯工具，不 import 其它子包。
- `app.py`：**唯一组装根**：`build_services()` → `build_router()` → `run_web()`。
- `cli.py`：只建 parser 和 dispatch；命令实现在 `commands/`，按功能分文件。
- `services.py`：显式服务容器，API 通过它取依赖；`Settings` 同时持有 LLM / 搜索 /
  采集 / OCR / 登录配置，`documents.ocr` 与 `crawl.auth` 的模块别名指向同一对象。
- `protocol/`：传输无关的请求、响应、路由原语；`api/` 与 `server/` 都依赖它，
  **互不依赖**。`server/` 只做 socket、静态托管与 SSE 字节输出。
- 领域层之间尽量单向：`qa → corpus / crawl`，`crawl → corpus / documents`，
  `documents → core`（URL 归一化不再反向 import crawl），
  `calc` 只读 `calcdata/` 与本地缓存，不联网；`integrations → calc / crawl`，
  领域层不反向依赖 `integrations/`。
- `api/` 只做参数解析、权限判断、调用用例与序列化；已知错误由前端按 `code` 映射，
  设置接口的“操作摘要”作为结果字段返回（前端只展示，不拼布局）。

## 关键入口

| 文件 | 作用 |
|---|---|
| `app.py` | **组装根**：`build_services()` → `build_application()` → `run_web()` |
| `services.py` | `Services`：Store / Calculator / Searcher / LLM / Agent / 附件目录 / 赛事刷新 |
| `main.py` | 入口分发：只把命令交给 CLI / app，不 import 领域模块 |
| `cli.py` | 只建 parser、分发到 `commands/` |
| `commands/` | 按功能拆开的 CLI 适配层（chat / crawl / documents / calc / settings / doctor） |
| `protocol/http.py` | 共享 Request / Response / Router / JSON / SSE 原语 |
| `api/registry.py` | 路由表：新增接口只改这里 |
| `server/http.py` | 传输层：socket、静态资源、SSE 字节输出；不 import api |
| `integrations/competitions.py` | 赛事名录联网刷新（用户主动触发，不污染 calc） |

## 新增一个功能

1. 在合适的领域子包里写纯逻辑（不碰 HTTP）；
2. 需要外部联网/缓存时放 `integrations/`，不要污染纯计算域；
3. 在 `api/` 加一个薄处理函数 `fn(request, services) -> Response`；
4. 在 `api/registry.py` 注册；
5. 若需要 CLI，在 `commands/<feature>.py` 写命令，由根 `cli.py` 分发；
6. 若需要界面，在 `frontend/js/features/<name>/` 写模块，并在 `main.js` 注册；
7. 在对应子包的 `README.md` 与 `tests/` 里补说明与离线测试。
