# wayfinder/ — 后端包

后端只做「取值、计算、推送数据」，不生成任何 HTML/CSS/JS。

## 依赖方向

```
main.py ──► cli.py ──► app.py ──► api/ ──► settings/ calc/ qa/ documents/ crawl/ corpus/
                         │          │
                         │          └──► server/http.py（只提供 Request/Response/Router）
                         └──► services.py ──► 领域对象（Store/Calculator/LLM/Agent）
core/  ◄── 所有层（只有配置与路径）
```

- `core/`：最底层，只有配置与路径，不 import 其它子包。
- `app.py`：**唯一组装根**：`build_services()` → `build_router()` → `run_web()`。
- `services.py`：显式服务容器，API 通过它取依赖；API 不再 import 全局 `SETTINGS`。
- 领域层之间尽量单向：`qa → corpus / documents / crawl`，`crawl → corpus / documents`，
  `calc` 只读 `calcdata/` 与本地缓存，不联网；`integrations → calc / crawl`，
  领域层不反向依赖 `integrations/`。
- `api/` 只做参数解析、权限判断、调用用例与序列化；`server/` 不认识业务。

## 关键入口

| 文件 | 作用 |
|---|---|
| `app.py` | **组装根**：`build_services()` → `build_application()` → `run_web()` |
| `services.py` | `Services`：按 `Settings` 提供 Store / Calculator / LLM / Agent |
| `main.py` | 入口分发：只把命令交给 CLI / app，不 import 领域模块 |
| `cli.py` | 全部命令行子命令的实现 |
| `api/registry.py` | 路由表：新增接口只改这里 |
| `server/http.py` | 传输层：路由分发、静态资源、JSON/SSE |
| `integrations/competitions.py` | 赛事名录联网刷新（用户主动触发，不污染 calc） |

## 新增一个功能

1. 在合适的领域子包里写纯逻辑（不碰 HTTP）；
2. 需要外部联网/缓存时放 `integrations/`，不要污染纯计算域；
3. 在 `api/` 加一个薄处理函数 `fn(request, services) -> Response`；
4. 在 `api/registry.py` 注册；
5. 若需要界面，在 `frontend/js/features/<name>/` 写模块，并在 `main.js` 注册；
6. 在对应子包的 `README.md` 与 `tests/` 里补说明与离线测试。
