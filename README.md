# SCAU 学生发展信息 LLM Harness

一个针对**华南农业大学站点群**的定向爬取 + 全文检索 + LLM 多轮编排问答系统。

问它「生物专业可以参加什么竞赛？走什么发展路线？」这类开放问题，它会：

1. 把问题**拆成多条可检索的子查询**（竞赛 / 大创 / 推免 / 考研 / 科研训练 / 就业 / 国际交流）
2. 在**已抓取的校内语料**里检索证据，同时在**公网**补充赛事规则、含金量、最新时间表
3. 让 LLM **判断证据是否足够**，不够就自动补检索（默认 2 轮）
4. 输出**分路线**的答案，每条结论都带 `[n]` 引用、发布时间、原文链接，并明确列出
   「**本次未能证实**」的项

核心原则：**证据可溯源**。每条结论都能回指到 `URL + 标题 + 发布时间`，
找不到就说找不到，不允许编造 URL / 日期 / 赛事名称。

---

## 1. 快速开始

### 第 0 步：获取代码

```bash
git clone https://github.com/FlyingBlock/SCAU-Wayfinder-Agent.git
cd SCAU-Wayfinder-Agent
```

环境要求：**Python 3.10+**。核心代码只用标准库（`urllib` / `sqlite3` / `http.server`），
`lxml` 是可选增强（正文抽取更准，缺失时自动退回正则）。**不需要 `pip install`。**

### 第 1 步：配置 LLM API key（必做）

```powershell
python -m harness.cli setup-key
```

它会把 key 安全地（不回显）读进来，**先做一次真实调用验证**，通过了才写入 `.env`。
申请地址：<https://platform.deepseek.com/api_keys>

> 想用别的模型（Ollama / vLLM / 通义 / 智谱）：先把 `.env.example` 复制成 `.env`，再设置
> `LLM_BASE_URL` / `LLM_MODEL` / `LLM_API_KEY` 即可，任何 OpenAI 兼容端点都能接。

### 第 2 步：抓取校内语料

```powershell
# 42 个高信号栏目（推荐起步，约 30-60 分钟）
python -m harness.cli crawl --scope narrow

# 更全：165 个 P1 栏目
python -m harness.cli crawl --scope p1

# 种子全量（349 条）
python -m harness.cli crawl --scope all
```

### 第 3 步：提问

```powershell
# 命令行
python -m harness.cli ask "生物专业可以参加什么竞赛？走什么发展路线？"

# 或者启动 Web 界面
python -m harness.cli web
# 然后浏览器打开 http://127.0.0.1:8848/
```

> 建议先跑一次自检，确认种子 / 数据库 / LLM 连通性都正常：
> ```powershell
> python -m harness.cli doctor
> ```
> 下文所有命令都假定**当前目录就是仓库根目录**（那个包含 `harness/` 包的目录）。

---

## 2. 命令一览

| 命令 | 作用 |
|---|---|
| `harness.cli setup-key` | 交互式配置并验证 LLM key |
| `harness.cli doctor` | 自检：种子 / 数据库 / LLM 连通性 / 公网搜索 |
| `harness.cli crawl --scope narrow\|p1\|p2\|all` | 抓取校内栏目群入库 |
| `harness.cli search "关键词"` | 只在已抓语料里检索（**不花 token**，用来调词和排错） |
| `harness.cli ask "问题" [--rounds N] [--json out.json]` | 多轮检索 + 带引用生成 |
| `harness.cli ask "问题" --dry-run` | **不调用 LLM**，只跑检索并打印证据与最终 Prompt |
| `harness.cli web [--port 8848]` | 启动 Web 界面 |
| `harness.maint audit` | 体检语料：登录墙 / 导航标题 / 空正文分布 |
| `harness.maint refetch` | 重新抓取可疑条目以修正标题与正文 |

常用参数：

```powershell
# 只抓某个栏目，便于调试
python -m harness.cli crawl --url https://life.scau.edu.cn/tzgg/list.htm --max-pages 3

# 抓取前清空库（谨慎）
python -m harness.cli crawl --scope narrow --reset

# 检索时限定时间窗与栏目类型
python -m harness.cli search "挑战杯" --since 2025-01-01 --top-k 20

# 不打印中间过程，并导出完整 JSON（含全部证据）
python -m harness.cli ask "保研条件" --quiet --json out/answer.json
```

---

## 3. 它是怎么工作的

```
L0 种子层   scau_bio_seed.yaml (349 条白名单) ──curate──▶ 42/165/349 个栏目
                                  │
L1 采集层   列表页 list.htm → 读「尾页」得 max_page → 抓前 N 页
            → 按 a{ID} 去重 → 按标题相关度+日期排序 → 抓正文
                                  │
L2 解析层   URL 归一化(强制 https) · 中文日期解析 · 正文清洗 · 附件链接
                                  │
L3 存储层   SQLite + FTS5（中文 bigram 分词）
                                  │
L4 检索层   OR 召回候选 → Python 侧按「词覆盖度 + BM25 + 学院加权」重排
                                  │
L5 编排层   意图分解 → 站内+公网检索 → 缺口检测 → 补检索(≤2轮) → 证据聚合
                                  │
L6 输出层   分路线答案 + 逐条 [n] 引用 + 时效标注 + 「本次未能证实」清单
```

### 目录结构

```
SCAU-Wayfinder-Agent/
├─ harness/                     Python 包（全部实现）
│  ├─ config.py     配置与 .env 加载（密钥优先级：环境变量 > .env）
│  ├─ seed.py       解析 seed/scau_bio_seed.yaml（自写的 flow-mapping 解析器）
│  ├─ curate.py     按问题意图裁剪栏目清单（narrow / p1 / p2）
│  ├─ fetcher.py    urllib 抓取：https 归一化 / 编码探测 / 限速 / 重试 / robots
│  ├─ parse.py      Webplus 列表页与正文页解析（不烧 token 的 CSS 式抽取）
│  ├─ store.py      SQLite + FTS5 + 中文 bigram 分词 + 两段式检索
│  ├─ llm.py        OpenAI 兼容 LLM 客户端（默认 DeepSeek）
│  ├─ websearch.py  公网搜索（ddg / bocha / tavily / bing）
│  ├─ prompts.py    全部 Prompt 模板，改这里就能改回答风格
│  ├─ agent.py      编排：分解 → 检索 → 缺口 → 补检索 → 生成
│  ├─ cli.py        命令行入口
│  ├─ web.py        Web 界面（标准库 http.server + SSE 流式输出）
│  └─ crawl.py      采集入口
├─ seed/
│  └─ scau_bio_seed.yaml        机器可读种子（10 分组 / 349 栏目）
├─ docs/                        设计与侦察文档（见 §8）
├─ 启动Harness.cmd              Windows 双击即开 Web 界面
├─ data/crawler.db              语料库（不入 git）
└─ .env                         密钥（不入 git）
```

---

## 4. 关键设计决策与实测依据

这一节记录**为什么这么做**，以及在本机实测中踩到的坑，改代码前值得先读。

### 4.1 为什么不用 crawl4ai，用纯标准库

指南原本设计用 crawl4ai + Playwright。实测后改成纯 `urllib` + `lxml`，原因：

| 事实 | 影响 |
|---|---|
| 本机沙箱内 `pip install` 必然失败（`tempfile.mkdtemp()` 建 0700 目录，沙箱令牌无写权限） | 装不了 playwright，crawl4ai 的浏览器路径不可用 |
| SCAU 站点群是**静态 HTML 的 Webplus CMS**，无 JS 渲染 | 不需要浏览器 |
| 实测 `urllib` 抓 `life.scau.edu.cn/tzgg/list.htm`：**0.2 秒**，17 条文章，47 页 | 比启动浏览器快两个数量级 |
| `lxml` 在本机自带 Python 中已安装 | 正文提取不用自己写 |

**结论**：对这类站点，浏览器自动化是纯粹的额外成本。本仓库不 vendor crawl4ai
源码（体积大且与本项目无关），将来遇到 JS 站点可自行接回。

### 4.2 为什么中文检索要自己切 bigram

FTS5 的 `unicode61` 分词器把连续汉字当成**一个 token**，所以：

```
文档：2026年推荐免试攻读研究生工作通知
查询：推免        → 匹配不到（"推免" 不是 "推荐免试" 的子串 token）
```

解法：写入时把汉字串切成 bigram（`推荐 荐免 免试 试攻 …`）并空格连接，
查询也做同样切分。于是「保研政策」→ `"保研" OR "研政" OR "政策"` 就能召回。

**但 OR 会带进噪声**：「竞赛 学分认定」的 OR 结果里，「家庭经济困难**认定**」
也会命中。因此检索做成两段式：

1. FTS5 用 OR 召回 150 条候选（保证召回）
2. Python 侧算「查询词覆盖率」+ BM25 + 学院加权重排（保证精度）

实测效果（125 篇语料时）：

| 查询 | 返回的 top 结果 |
|---|---|
| `推免 保研` | 推免工作细则、实施方案征求意见稿、推荐名单公示、递补通告 ✓ |
| `挑战杯 院内选拔` | 丁颖杯暨挑战杯院内选拔赛通知 ✓ |
| `生命科学竞赛 国家` | 第十届全国大学生生命科学竞赛广东省赛区决赛 ✓ |

### 4.3 列表页解析的三个坑（都实际踩到过）

1. **有些模板把 `标题 + 摘要` 一起包在 `<a>` 里**（如 `cxcyxy` 的 `timg-list` 模板），
   直接取锚文本会得到「标题 + 300 字摘要」。必须先找锚点内的 `<h3>/<h4>`。
2. **有些模板正文链接里只有图片**，标题在 `title` 属性里。
3. **不要用「锚点后 220 字符」当标题兜底** —— 会把同级节点的日期、摘要、
   下一篇标题一起吞进来（实测把 `2026-10-12 关于…` 整段当成了标题）。
   兜底文本必须在下一个 `<a>/<li>/<tr>` 处截断，并剥掉日期串。

### 4.4 公网搜索：默认 DuckDuckGo Lite

实测三种免 key 方案：

| 方案 | 结果 |
|---|---|
| `cn.bing.com/search` | ❌ 被重定向到百度 |
| `www.bing.com/search` | ⚠️ 200 但**返回结果与查询完全无关**（查生命科学竞赛返回 ChatGPT 教程） |
| `lite.duckduckgo.com/lite/` | ✅ **中文结果质量很好**，能直接返回赛事官网与报名截止时间 |

所以默认 `WEB_SEARCH_PROVIDER=ddg`，Bing 只作备用。要长期稳定建议配一个
搜索 API key（`bocha` 国内最稳，`tavily` 也行）：
```ini
WEB_SEARCH_PROVIDER=bocha
BOCHA_API_KEY=sk-xxx
```

### 4.5 两个必须拦截的「假页面」

1. **正文页 302 到统一身份认证**。实测 `xtw.scau.edu.cn/tzgg/list.htm` 的
   **列表页是公开的**，但点进任何一篇文章都会跳到
   `cas.scau.edu.cn/lyuapServer/login?service=...`。若不拦截，入库的就是
   登录页 HTML（标题为空、正文 38 字），语料里会混进垃圾。
   现在用 `looks_like_login()` 判定，记 `login_required` 并跳过，不反复重试。
2. **正文只有图片的页面**。生命科学学院「讲座报告」栏目的海报页、
   以及某些通知的正文就是一张图，`html_to_text` 只能拿到导航菜单
   （约 35 字）。这类记 `empty` 属正常，**不是抓取失败**——本系统没做 OCR。

### 4.6 成本控制

| 手段 | 效果 |
|---|---|
| 列表页/正文用正则+lxml 抽取，**不调用 LLM** | 采集阶段 token 消耗为 **0** |
| 只把 top-N 证据送进生成（默认 24 篇，每篇 900 字） | 单次问答约 2 万字符上下文 |
| 证据预算可调（`HARNESS_EVIDENCE_*`） | 想省钱就调小 |
| `temperature=0` | 稳定、可缓存 |

一次完整问答大致消耗 **20k prompt + 3k completion tokens**
（DeepSeek 约 ¥0.02～0.05/次，具体以官网计价为准）。
每次运行结束都会打印真实 token 用量。

### 4.7 合规与礼貌抓取

- 只抓**公开页面**，不碰登录墙系统（`cas` / `portal` / `cxcygl` / `jwxt` / `xgxt` …）
- 单站并发 ≤ 5，请求间隔 0.8～1.5 秒随机，避开白天高峰
- User-Agent 写明用途；`check_robots_txt` 默认开启（`--no-robots` 可关）
- 只抓 `*.scau.edu.cn` 白名单域名，自动过滤第三方外链
- 抓到的内容**仅供个人学习检索**，`data/` 不入 git

---

## 5. 已知限制（诚实清单）

1. **附件没有解析**。竞赛通知的关键信息常在 `.doc/.pdf/.xlsx` 附件里
   （指南 §6.3-17）。目前只**记录附件链接**并在正文里保留文件名，
   没有下载解析内容。`python-docx` / `openpyxl` 本机可用，
   PDF 需要额外装 `pypdf`（沙箱内装不了）。
2. **没有 OCR**。扫描件/海报型通知（正文就是一张图）抓不到文字，
   这类条目会记成 `empty`。生命科学学院「讲座报告」栏目基本属于这一类。
3. **有登录墙的栏目无法覆盖**。实测 `xtw.scau.edu.cn` 的文章页全部 302 到
   CAS 统一身份认证（列表页公开、正文页需登录），因此团委系统的文章拿不到；
   `cxcygl.scau.edu.cn`（学科竞赛管理系统）整站需登录，已跳过。
   这意味着「个人已报名了哪些竞赛」这类信息无法获取。
3. **就业创业信息网（jyzx）是第三方云研平台**，用 `?type_id=&menu_id=` 参数寻址，
   没有 `list.htm` 分页，当前解析器抓不到它的列表，需要单独写适配。
4. **`cxcygl.scau.edu.cn`（学科竞赛管理系统）是登录态系统**，TLS 握手被中断，跳过。
5. **公网搜索是 HTML 解析**（ddg/bing），对方改版就会失效；要稳定请配 API key。
6. **`narrow` 范围只有 42 个栏目**，覆盖核心但会漏掉部分学院的通知。
   问的问题越冷门，越应该先跑 `--scope p1` 或 `all`。
7. **增量更新还没做成定时任务**。重复跑 `crawl` 会跳过已入库的文章
   （按 `a{ID}` 去重 + `content_hash` 判断是否被编辑），所以手动重跑成本很低，
   但指南 §10.4 的 Windows 计划任务还没配。
8. **`refetch` 只能修标题/正文，不能修 `site.name`**。早期用 `--url` 抓的栏目
   在库里叫「(命令行指定)」；带上 `--url` 重跑一次同一批栏目即可刷新为种子里的名称。

---

## 6. 排错

| 症状 | 原因与解法 |
|---|---|
| `尚未配置 LLM API key` | 跑 `python -m harness.cli setup-key` |
| `HTTP 401 Authentication Fails` | key 错了或已失效，重新 `setup-key` |
| 检索没有命中 | 先 `harness.cli search "短词"` 确认库里有；关键词用 2-6 字，别用整句话 |
| 库内文章数为 0 | 还没抓，跑 `crawl --scope narrow` |
| 某栏目 0 篇 | 可能是空栏目（指南 §12.3-19，属正常），也可能模板不同；用 `--url` 单独抓并看日志 |
| 生成答案里有 `⚠️可能已过期` | 该证据发布时间超过 18 个月，属预期行为 |
| 端口被占用 | `harness.cli web --port 8849` |

抓取失败会写进 `crawl_log` 表，按 `http_error / empty / robots_disallow /
list_unreachable / parse_fail` 分类归因。查最近的失败：

```powershell
python -m harness.cli search "" # 不行，用下面这句
python -c "import sqlite3;d=sqlite3.connect(r'data\crawler.db');d.row_factory=sqlite3.Row;[print(r['status'],r['error'],r['url']) for r in d.execute('SELECT status,error,url FROM crawl_log WHERE status!=\"ok\" ORDER BY id DESC LIMIT 30')]"
```

---

## 7. 下一步可以做什么

按性价比排序：

1. **扩量**：`crawl --scope p1`（165 栏目）把其他学院的通知也纳入
2. **附件解析**：下载 `.docx/.xlsx` 抽正文（本机已有 `python-docx` / `openpyxl`）
3. **结构化字段**：对「疑似竞赛通知」的文档做 LLM 抽取
   （`is_competition / level / signup_deadline / eligible`），落进 `field` 表，
   之后就能直接回答「最近能报名的国家级竞赛有哪些」
4. **定时增量**：Windows 计划任务每天凌晨跑 `crawl --scope p1`
5. **评估集**：指南 §9.3 给了 20 个验收问题，可用来量化引用准确率与幻觉率
6. **向量检索**：同义表达召回（「推免」vs「保研」）目前靠 bigram 近似覆盖，
   数据量大了以后可以加 embedding 做混合检索

---

## 8. 相关文档

| 文件 | 说明 |
|---|---|
| [docs/SCAU-LLM-Harness-开发指南.md](docs/SCAU-LLM-Harness-开发指南.md) | 原始开发指南（架构、M 里程碑、坑清单） |
| [docs/web.md](docs/web.md) | SCAU 全站群清单（4118 行，人工核验，唯一真源） |
| [seed/scau_bio_seed.yaml](seed/scau_bio_seed.yaml) | 机器可读种子（10 分组 / 349 栏目） |
| [docs/groupA_recon.md](docs/groupA_recon.md) | 5 个学院的深度侦察报告 |
| [docs/crawl4ai-api-reference-0.9.4.md](docs/crawl4ai-api-reference-0.9.4.md) | crawl4ai 0.9.4 API 速查（若要接回浏览器方案） |

---

## 9. License

[MIT](LICENSE) © 2026 FlyingBlock
