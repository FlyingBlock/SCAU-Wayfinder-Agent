<p align="center">
  <img src="./assets/scau.jpg" width="800" alt="项目头图">
</p>

# SCAU Wayfinder

华南农业大学校内公开信息检索 + 学业规划助手。

它做两件事：

1. **问答**：抓校内公开通知入库 → 中文全文检索 → 拆子查询、站内 + 公网多轮检索 →
   带 `[n]` 引用的分路线回答；答案下面再确定性抽取**活动 / 附件 / 关键时间**卡片。
2. **计算**：绩点、综测、保研 / 考研 / 奖学金门槛、活动加分，全部离线、不花 token。

---

## 快速开始

在仓库根目录（含 `wayfinder/` 的那一层）执行：

```powershell
# 1) 抓一批校内语料（首次约 30-60 分钟；只用量计算器可跳过）
python -m wayfinder crawl --scope narrow

# 2) 启动 Web（自动打开 http://127.0.0.1:8848/）
python -m wayfinder web
```

Windows 也可以直接双击 **`Launch.cmd`**。

第一次使用建议先跑一次自检：

```powershell
python -m wayfinder doctor
```

配置模型（任意 OpenAI 兼容端点；计算器不需要）：

```powershell
python -m wayfinder setup-key
# 或：python -m wayfinder web → 左下角「⚙️ 设置 → 🧠 模型」
```

> 环境要求：Python 3.10+。核心只用标准库（`urllib` / `sqlite3` / `http.server` / `json`），
> 不需要 `pip install`；装了 `lxml` / `python-docx` 会自动用上，没有则退回内置解析器。

---

## 功能一览

| 能力 | 说明 | 入口 |
|---|---|---|
| 校内检索 | SQLite + FTS5，中文 bigram 分词 + 覆盖度重排 | `search` / `/api/search` |
| 多轮问答 | 意图分解 → 站内 + 公网检索 → 缺口补检索 → 带引用生成 | `ask` / `/api/ask` |
| 流式输出 | SSE 推 `trace` / `answer_delta` / `answer` / `cards` | `frontend/js/features/chat/` |
| 对话卡片 | 活动、附件、关键时间；分值来自已核验名录，不由模型生成 | `qa/cards.py` |
| 附件解析 | pdf / doc / docx / xls / xlsx / ppt / zip / 图片，42 种扩展名 | `documents/` |
| OCR | 百度智能云（可选），图片与扫描件提字 | `documents/ocr.py` |
| 登录墙 | CAS 表单登录 / Cookie 导入 / 验证码 OCR，凭据只落 `.auth/` | `crawl/auth.py` |
| 计算器 | 绩点 / 综测 / 推免 / 门槛 / 活动篮 / 赛事名录 | `calc/` + `frontend/js/features/calc/` |

---

## 架构

前后端彻底解耦：

```
frontend/  (纯静态 HTML/CSS/ES Modules)
    │  main.js 只装配；features/* 只做界面组织、用户事件、订阅 JSON / SSE
    ▼  HTTP + SSE
wayfinder/server/http.py     传输层：路由、静态资源、SSE 帧
    ▼
wayfinder/api/*              协议层：参数解析 → 用例调用 → JSON
    ▼
wayfinder/{crawl,corpus,documents,qa,calc,settings}/    领域层：计算与数据
    ▲
wayfinder/app.py             组装根：build_services → build_router → run_web
wayfinder/main.py            入口：只把命令转发给 CLI / app
```

三条硬约束：

1. **前端不计算**：分数、绩点、最佳成就、检索与匹配全部由后端返回；
   前端只渲染与订阅。GPA 列读 `effective_gp`，活动卡读 `best`，
   通道口径读 catalog。
2. **后端不拼界面**：Python 里不出现 HTML/CSS/JS；SSE 的 `trace` 只推
   `{step, data}`，中文步骤、文案、按钮和布局由 `frontend/` 负责。
3. **主程序只组装**：`wayfinder/app.py` 创建服务、装配路由、启动传输层；
   `wayfinder/main.py` 只做入口分发，业务命令在 `cli.py`，领域逻辑在子包。

---

## 目录结构

```
SCAU-Wayfinder-Agent/
├─ wayfinder/                 后端包（详见 wayfinder/README.md）
│  ├─ app.py                  组装根：服务容器 + 路由 + Web 启动
│  ├─ services.py             Services：按配置提供 Store/Calculator/LLM/Agent
│  ├─ main.py                 入口：只分发到 CLI / app
│  ├─ cli.py                  命令行入口
│  ├─ core/                   配置、路径、.env 读写
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
│     ├─ router.js            路由与视图切换
│     ├─ shared/              dom / api / events / format / toast
│     └─ features/            chat / calc / settings
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
| GET | `/api/calc/catalog` | 计算器全部静态数据 |
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
错误一律放在 `answer` 事件的 `error` 字段（事件名不能用 `error`，否则 EventSource 会当连接故障）。

静态资源：`/` 与 `/calc*` 返回 `frontend/index.html`；`/assets/**` 返回 `frontend/**`。

---

## 测试

全部离线（假站点 / 假 OpenAI 端点），不联网、不花 token：

```powershell
python tests/test_architecture.py # 依赖方向、组装根、前端职责边界
python tests/test_app_shell.py    # ES Module 装配、作用域样式、node 解析
python tests/test_api_smoke.py    # 全部只读接口 + evaluate + SSE + 404/403
python tests/test_cards_api.py    # 真起 HTTP 服务，验 /api/ask 的 SSE cards 事件
python tests/test_stream.py       # 流式增量 / 思维链截断 / 端点不支持 stream 的退路
python tests/test_auth.py         # CAS 登录、验证码、Cookie、采集自动登录、设置面板
```

---

## 配置与数据

- `.env`：模型 / 搜索 / OCR / 登录开关。复制 `.env.example` 后按需填写；界面保存也写这里。
- `.auth/`：Cookie 与（可选的）账号密码，已 gitignore，**不进日志、不发模型**。
- `calcdata/`：计算器全部学校数据，进 git；改数据不用改代码。
- `data/`：SQLite 库、附件、缓存，进 gitignore；可整体删除后重建。
- 环境变量前缀：`WAYFINDER_*`（兼容旧的 `HARNESS_*`）。

> 计算器数值是规划用的，不是学籍依据。请用本学院当年细则与教务系统培养方案核对。

---

## 延伸阅读

- [后端分层与依赖方向](wayfinder/README.md)
- 领域：[采集](wayfinder/crawl/README.md) · [存储检索](wayfinder/corpus/README.md) · [文档解析](wayfinder/documents/README.md) · [问答编排](wayfinder/qa/README.md) · [计算引擎](wayfinder/calc/README.md) · [设置服务](wayfinder/settings/README.md)
- 接口与传输：[API 层](wayfinder/api/README.md) · [HTTP 传输层](wayfinder/server/README.md) · [配置](wayfinder/core/README.md)
- 其它：[前端](frontend/README.md) · [测试](tests/README.md) · [计算器数据](calcdata/README.md) · [种子](seed/README.md) · [文档资料](docs/README.md)

---

## License

见 [LICENSE](LICENSE)。
