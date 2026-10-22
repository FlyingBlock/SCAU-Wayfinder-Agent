<p align="center">
  <img src="./assets/scau.jpg" width="800" alt="项目头图">
</p>

# SCAU Wayfinder

这是一个公开信息检索 + 学业规划助手。
搭配作者正在做的一个学校各官网信息轮询工具食用效果更佳

## 它能做什么

1. **帮你搜寻资料**：能抓取网上资料 + 校内公开通知或者需登录才能查询到的信息，包括解析.doc/.docx/.xlsx/.pdf等等常用文档格式、图片格式的附件，能把触手伸到普通AI伸不到的地方，用最新最权威的资料，回答你关于赛事信息的疑惑，为你规划成长路径。**活动 / 附件 / 关键时间**以卡片形式呈现。
2. **绩点计算器**：绩点、综测、保研 / 考研 / 奖学金门槛、活动加分，全部离线、不花 token，给你清晰数据
3. **信息看板**：直观告诉你想保研/拿奖学金要怎么做

---

## 快速开始

在仓库根目录（含 `wayfinder/` 的那一层）执行。环境要求 Python 3.10+，
核心只用标准库，不需要 `pip install`。

最简启动（已有语料库时）：

```powershell
python -m wayfinder web
```

首次使用按顺序执行：

```powershell
python -m wayfinder doctor                     # 1) 自检（可选）
python -m wayfinder crawl --scope narrow       # 2) 抓一批校内语料（约 30-60 分钟；只用量计算器可跳过）
python -m wayfinder web                        # 3) 启动 Web，自动打开 http://127.0.0.1:8848/
```

Windows 也可以直接双击 **`Launch.cmd`**。

配置模型（任意 OpenAI 兼容端点；计算器不需要）：

```powershell
python -m wayfinder setup-key
# 或：python -m wayfinder web → 左下角「⚙️ 设置 → 🧠 模型」
```

> 可选增强：`lxml`（HTML 解析）、`openpyxl`（xlsx）、`Pillow`（图片预处理）。
> 不装也能跑，缺失时会退回内置解析器/降级，不会阻塞启动。

---

## 架构

前后端通过 HTTP / SSE 通信，依赖方向如下：

```
frontend/  (纯静态 HTML/CSS/ES Modules)
    │  main.js 只装配；features/* 只做界面组织、用户事件、订阅 JSON / SSE
    ▼  HTTP + SSE
wayfinder/server/http.py     传输层：socket、静态资源、SSE 帧
    ▼
wayfinder/protocol/http.py   共享协议原语：Request / Response / Router
    ▲
wayfinder/api/*              协议层：参数解析 → 用例调用 → JSON / SSE
    ▼
wayfinder/services.py        服务容器 → 领域层：crawl / corpus / documents / qa / calc / settings
    ▲
wayfinder/app.py             组装根：build_services → build_router → run_web
wayfinder/main.py            入口：只把命令交给 cli
wayfinder/cli.py             只建 parser、分发到 commands/
wayfinder/commands/*         按功能拆开的 CLI 适配层
```

三条硬约束：

1. **前端不计算业务结果**：分数、绩点、最佳成就、活动筛选/排序全部由后端
   返回；前端只渲染与订阅。GPA 列读 `effective_gp`，活动卡读 `best`，
   活动列表读 `/api/calc/activities`，通道口径读 catalog。
2. **后端不拼界面**：Python 里不出现 HTML/CSS/JS；SSE 的 `trace` 只推
   `{step, data}`，已知错误推 `{code}`，中文步骤、文案、按钮和布局由
   `frontend/` 负责。设置接口的“操作摘要”字段仍是协议数据，前端只负责展示。
3. **主程序只组装**：`wayfinder/app.py` 创建服务、装配路由、启动传输层；
   `wayfinder/main.py` 只做入口分发；`wayfinder/cli.py` 只建 parser 和 dispatch；
   业务命令在 `wayfinder/commands/`，领域逻辑在子包。

---

## 目录结构

```
SCAU-Wayfinder-Agent/
├─ wayfinder/                 后端包（详见 wayfinder/README.md）
│  ├─ app.py                  组装根：服务容器 + 路由 + Web 启动
│  ├─ services.py             Services：Store/Calculator/LLM/Agent/附件/赛事刷新
│  ├─ main.py                 入口：只分发到 CLI / app
│  ├─ cli.py                  只建 parser、分发到 commands/
│  ├─ commands/               按功能拆开的 CLI 适配层
│  ├─ protocol/               请求 / 响应 / 路由协议原语（api 与 server 共享）
│  ├─ core/                   配置、路径、URL 归一化、.env 读写
│  ├─ crawl/                  种子、抓取、解析、登录、维护
│  ├─ corpus/                 SQLite 存储与中文检索
│  ├─ documents/              附件下载、办公文件解析、PDF、OCR
│  ├─ qa/                     LLM 客户端、Prompt、Agent、卡片、公网搜索
│  ├─ calc/                   绩点 / 综测 / 门槛计算引擎（只读本地数据）
│  ├─ integrations/           赛事名录联网刷新（会联网、写缓存）
│  ├─ settings/               设置用例、校验、落盘、登录动作
│  ├─ api/                    JSON / SSE 薄适配层
│  └─ server/                 HTTP 传输层
├─ frontend/                  纯静态前端（ES Modules，无构建步骤）
│  ├─ index.html
│  ├─ css/                    shell / calc 两份作用域样式
│  └─ js/
│     ├─ main.js              模块装配入口
│     ├─ router.js            路由与视图切换（视图元数据由 feature 注册）
│     ├─ shared/              dom / api / events / format / toast
│     └─ features/            chat（index/content/cards）/ calc（index/activities/state）/ settings
├─ tests/                     离线自测（见 tests/README.md）
├─ calcdata/                  计算器数据（进 git）
├─ seed/                      栏目种子白名单
├─ docs/                      设计与资料（见 docs/README.md）
└─ data/                      运行时数据（内容不进 git：库、附件、缓存）
```

每个功能目录下都有独立的 `README.md`，说明职责、关键文件与扩展方式。

---

## 常用命令

```powershell
python -m wayfinder doctor                     # 自检：种子/库/计算器/LLM/OCR/登录
python -m wayfinder crawl --scope narrow       # 抓 42 个高信号栏目
python -m wayfinder crawl --scope p1           # 165 个栏目
python -m wayfinder search "挑战杯"             # 只检索，不花 token
python -m wayfinder ask "生物专业可以参加什么竞赛？"
python -m wayfinder ask "保研条件" --dry-run    # 只检索，打印证据与 Prompt
python -m wayfinder web --port 8848 --no-open  # 不自动开浏览器

python -m wayfinder calc                       # 计算器数据自检
python -m wayfinder gpa --score C3001=88
python -m wayfinder goals --scores my.json --cohort 120 --rank 18
python -m wayfinder activities --list competition

python -m wayfinder parse 报名表.xlsx 评审细则.pdf
python -m wayfinder attach --limit 20
python -m wayfinder attachments --search 报名截止
python -m wayfinder ocr --api-key <AK> --secret-key <SK>
python -m wayfinder login                      # 统一身份认证
```

完整参数：`python -m wayfinder <命令> --help`。

---

## HTTP 接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/status` | 库状态 + 模型 / 搜索 / OCR 配置灯 |
| GET | `/api/search?q=&k=` | 纯检索（不花 token） |
| GET | `/api/article?id=` | 读一篇正文 |
| GET | `/api/ask?q=&rounds=&dry=` | SSE 问答流 |
| GET | `/api/attachment?id=` | 附件解析结果 |
| GET | `/api/attachment/file?stored=` | 本地附件文件（仅限附件目录） |
| GET | `/api/calc/catalog` | 计算器静态数据（专业/规则/门槛/指标；`?activities=0` 首屏瘦身） |
| GET | `/api/calc/activities` | 活动篮列表（后端筛选/排序） |
| POST | `/api/calc/evaluate` | 成绩单 + 活动篮 → 完整结果 |
| GET | `/api/calc/target?gpa=&major=&scores=` | 课程目标分反推 |
| POST | `/api/calc/activities/refresh` | 联网刷新赛事名录 |
| GET/POST | `/api/settings/llm` | 模型设置 / 保存 |
| POST | `/api/settings/llm/test` | 测试连通性 |
| GET/POST | `/api/settings/ocr` | OCR 设置 / 保存 |
| POST | `/api/settings/ocr/test`・`/clear` | 测试 / 清除 |
| GET/POST | `/api/settings/auth` | 登录设置 / 保存并登录 |
| POST | `/api/settings/auth/captcha`・`/clear`・`/logout` | 人工验证码 / 清凭据 / 退出 |

`/api/ask` 的 SSE 事件：`trace({step,data})` → （`answer_delta` → `answer_end`）* →
`answer` → `cards` → `done`。`trace` 只推结构化步骤，中文文案由前端 `traceText()` 生成；
`dry=1` 时 `answer` 带 `dry/evidence_count`，正文摘要在前端组装。
已知错误放在 `answer` 事件的 `code` 字段（`empty_question` / `llm_not_configured` /
`empty_corpus` / `no_result`），未知异常放 `error` 文本；事件名不能用 `error`，
否则 EventSource 会当连接故障。

静态资源：`/` 与任意无扩展名的 SPA 路径返回 `frontend/index.html`；`/assets/**` 返回 `frontend/**`。

---

## 测试

全部离线（假站点 / 假 OpenAI 端点），不联网、不花 token：

```powershell
python tests/test_architecture.py # 依赖图、组装根、Services 配置、前端职责
python tests/test_app_shell.py    # ES Module 装配、模块边界、node 解析（可选）
python tests/test_api_smoke.py    # 全部只读接口 + evaluate + activities + SSE + 403
python tests/test_cards_api.py    # 真起 HTTP 服务，验 /api/ask 的 SSE cards 事件
python tests/test_stream.py       # 流式增量 / 思维链截断 / 端点不支持 stream 的退路
python tests/test_auth.py         # CAS 登录、验证码、Cookie、采集自动登录、设置面板
```

测试只使用标准库；`test_app_shell.py` 若 PATH 里有 `node` 会额外做 JS 语法检查，
没有则跳过。所有测试都兼容 Windows GBK 控制台（`sys.stdout.reconfigure`）。

---

## 配置与数据

- `.env`：模型 / 搜索 / OCR / 登录开关。复制 `.env.example` 后按需填写；界面保存也写这里。
- `.auth/`：Cookie 与（可选的）账号密码，已 gitignore，**不进日志、不发模型**。
  设置写接口（`POST /api/settings/*`）只接受本机、同源且
  `Content-Type: application/json` 的请求；改 `base_url` 时必须同时提供该端点的 key。
- `calcdata/`：计算器全部学校数据，进 git；改数据不用改代码。
- `data/`：SQLite 库、附件、缓存，进 gitignore；可整体删除后重建。
- 环境变量前缀：`WAYFINDER_*`（兼容旧的 `HARNESS_*`）。

> 计算器数值是规划用的，不是学籍依据。请用本学院当年细则与教务系统培养方案核对。

---

## 延伸阅读

- [后端分层与依赖方向](wayfinder/README.md)
- 功能索引：[功能一览](docs/FEATURES.md)
- 领域：[采集](wayfinder/crawl/README.md) · [存储检索](wayfinder/corpus/README.md) · [文档解析](wayfinder/documents/README.md) · [问答编排](wayfinder/qa/README.md) · [计算引擎](wayfinder/calc/README.md) · [设置服务](wayfinder/settings/README.md)
- 接口与传输：[API 层](wayfinder/api/README.md) · [HTTP 传输层](wayfinder/server/README.md) · [协议原语](wayfinder/protocol/README.md) · [CLI 命令](wayfinder/commands/README.md) · [配置](wayfinder/core/README.md)
- 其它：[前端](frontend/README.md) · [测试](tests/README.md) · [计算器数据](calcdata/README.md) · [种子](seed/README.md) · [文档资料](docs/README.md)

---

## License

见 [LICENSE](LICENSE)。
