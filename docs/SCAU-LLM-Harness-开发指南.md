# SCAU 站点群 LLM 检索 Harness 开发指南

> **目标**：从本工作区 `web.md` 列出的华南农业大学全部站点出发，结合公网搜索，构建一个能用自然语言回答学生发展问题的系统。
> **示例问题**：「生物专业可以参加什么竞赛？走什么发展路线？」
> **期望输出**：分路线（竞赛 / 保研考研 / 科研训练 / 就业 / 国际交流）的具体路径 + 每条路径的**校内依据**（通知、名单、讲座、公示）+ 关键时间节点 + 可点击链接 + 实例。
>
> 文档基于**本机实测**环境写成：`crawl4ai` 0.9.4（本地已克隆源码）、Python 3.12、Windows + DSH 沙箱。所有 crawl4ai API 均对照本地源码核对过，非文档推测。

---

## ⚙️ 实施状态（本指南已被实现，实现在 `harness/`）

> 本节由实现过程回填。**先读 `harness/README.md`**，那里有完整的用法、设计依据与已知限制。
> 下面是「本指南的计划」与「实际实现」的差异，以及实测中修正的结论。

| 项 | 指南原计划 | 实际实现 | 原因 |
|---|---|---|---|
| 抓取引擎 | crawl4ai + Playwright | **纯 `urllib` + `lxml`** | 沙箱内装不了 playwright；SCAU 全是静态 Webplus 页，不需要浏览器；实测抓一个列表页仅 **0.2 秒** |
| 中文检索 | FTS5 + `jieba` 预分词 | **FTS5 + 自写 bigram 切分** | 沙箱内装不了 jieba；bigram 免依赖且召回够用 |
| 检索排序 | BM25 | **OR 召回 + 词覆盖度/BM25 重排** | 纯 bigram 的 AND 召回不足、纯 OR 精度差，两段式才稳（见 README §4.2） |
| Web 框架 | FastAPI + 前端 | **标准库 `http.server` + 内嵌 HTML + SSE** | 装不了 fastapi；单用户够用，零构建 |
| LLM 抽取 | `LLMExtractionStrategy` | **未实现**（列为下一步） | 优先把「抓→存→检→答」全链路跑通 |
| 公网搜索 | 「联网搜索」 | **DuckDuckGo Lite 解析**（可切 bocha/tavily API） | `cn.bing.com` 被跳转百度、`www.bing.com` 返回结果与查询无关；实测 DDG Lite 中文质量最好 |

**另外两条实测修正**（与原文档结论不同）：

1. §3.4 说「装依赖请在沙箱外做」——**实际上本项目不需要装任何依赖**。
   本机自带 Python 已有 `lxml` / `python-docx` / `openpyxl`，
   加上只用标准库，因此在沙箱内可直接运行全部功能。
2. 单位换算：`web.md` 记录的规模（如生命科学学院通知公告 645 条 / 47 页）与实测一致，
   **但一个栏目抓 60 篇正文约需 3-5 分钟**（限速 0.8-1.5s）。按此估算，
   `--scope narrow`（42 栏目）约 30-60 分钟，`--scope p1`（165 栏目）需数小时。
   因此新增了 `recent_years`（默认 5 年）时间窗过滤，避免把时间耗在十年前的旧闻上。

---

## 目录

| 章节 | 内容 |
|---|---|
| 1 | 目标与最终形态 |
| 2 | 架构总览与数据流 |
| 3 | **环境与网络实测结论（重要，先读）** |
| 4 | 数据源层：把 `web.md` 变成机器可读种子 |
| 5 | 采集层：crawl4ai 抓 SCAU 站点群 |
| 6 | 解析与结构化层 |
| 7 | 存储与检索引擎 |
| 8 | 编排层：Agent 如何回答「发展路线」类问题 |
| 9 | 端到端示例：生物专业竞赛与发展路线 |
| 10 | 工程化、调度与成本控制 |
| 11 | 分阶段里程碑与验收标准 |
| 12 | 已知坑清单（本机实测 + web.md 记录） |
| 13 | 附录：crawl4ai 0.9.4 API 速查 |

---

## 1. 目标与最终形态

### 1.1 要解决的核心困难

「生物专业可以参加什么竞赛、走什么发展路线」这类问题，难点不在生成，而在**证据**：

1. **信息分散**：竞赛通知在创新创业学院、大创/挑战杯在团委、学科竞赛在本科生院与学院、保研政策在研究生院、招聘在就业网——横跨 10+ 个独立站点。
2. **站点技术形态统一但路径不统一**：全部是清华同方 Webplus CMS，列表页 `list.htm` / `list2.htm`…，正文页 `/年/月日/c栏目号a文章号/page.htm`，但栏目别名是中文拼音缩写，无法猜。
3. **时效性极强**：竞赛报名截止、推免时间表、宣讲会日期——过期信息等于错误信息。
4. **公网信息与校内信息必须交叉验证**：比如「全国大学生生命科学竞赛」的官方规则在公网，而「本校的报名组织方式、往届获奖、学分认定」只在校内站。

所以本 Harness 的本质是：**一个带白名单种子、定向爬取、结构化抽取、可溯源引用的 RAG + Agent 系统**，而不是「让 LLM 上网随便搜」。

### 1.2 交付形态建议（按投入排序）

| 形态 | 适用 | 说明 |
|---|---|---|
| **CLI（推荐起步）** | 自己用、快速迭代 | `python -m harness ask "生物专业能参加什么竞赛"` |
| 本地 Web（FastAPI + 简单前端） | 给同学用 | 复用同一套 core |
| 定时报告（每月生成 Markdown 简报） | 低维护 | 把「本月新竞赛通知」推给自己 |
| 对话式（接入任意 LLM 客户端） | 进阶 | 暴露为 MCP / function-calling 工具 |

**建议**：先把 CLI 做扎实，core 与 UI 分离，后面加界面只是薄壳。

---

## 2. 架构总览与数据流

```
┌──────────────────────────────────────────────────────────────────────┐
│  L0 种子层        web.md ──解析──▶ scau_bio_seed.yaml ──裁剪──▶ seeds.yaml │
│                   （人工核验过的 URL 清单，唯一真源）                    │
└──────────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼────────────────────────────────────┐
│  L1 采集层        crawl4ai AsyncWebCrawler                           │
│                   · 列表页发现 → 抽文章链接 + 标题 + 日期              │
│                   · 分页 list2..listN（读「尾页」而非猜）              │
│                   · 正文页抓取（并发受控、缓存、重试）                 │
│                   产物：raw_html / markdown / 元数据                   │
└──────────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼────────────────────────────────────┐
│  L2 解析层        URL 归一化 · 正文清洗 · 日期解析 · 按 a{ID} 去重      │
│                   CSS 抽取（免费）→ 必要时 LLM 抽取（贵）              │
└──────────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼────────────────────────────────────┐
│  L3 存储/索引层   SQLite（元数据）+ FTS5（中文分词）+ 可选向量          │
│                   文档表 · 栏目表 · 文章表 · 抽取字段表 · 抓取日志表     │
└──────────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼────────────────────────────────────┐
│  L4 检索层        混合检索：BM25(FTS5) + 向量 → RRF 融合               │
│                   元数据过滤：时间窗 · 学院 · 栏目类型 · 状态           │
└──────────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼────────────────────────────────────┐
│  L5 编排层        Query 分解 → 站内检索 + 公网搜索 → 缺口检测          │
│                   → 补检索（≤N 轮）→ 证据聚合 → 生成带引用答案          │
└──────────────────────────────────────────────────────────────────────┘
                                  │
┌─────────────────────────────────▼────────────────────────────────────┐
│  L6 输出层        分路线答案 + 引用 + 时效标注 + 「未能证实」声明        │
└──────────────────────────────────────────────────────────────────────┘
```

**关键设计原则**

- **种子白名单是唯一真源**：LLM 只从抓到的语料里找答案，不允许自由编造 URL。
- **列表页驱动，而非全站深爬**：SCAU 站点群体量巨大（媒体华农一个栏目就 460 页），`web.md` 已人工核验过入口，直接用清单最省算力。
- **两段式抽取**：CSS 能抽的绝不用 LLM；LLM 只做「从正文里判断这是不是竞赛、报名截止是什么时候」这类语义工作。
- **一切可溯源**：每条结论必须能回指到 `url + 标题 + 抓取时间`。

---

## 3. 环境与网络实测结论（重要，先读）

> 以下是**在这台机器、这个 DSH 沙箱里实际发生的事**，不是通用教程。先读这一节能省下几小时。

### 3.1 网络：GitHub 直连不通，镜像可用

| 目标 | TCP 443 | 结论 |
|---|---|---|
| `github.com` | ❌ 超时 | **直连不可用**（DNS 能解析，TCP 连不上） |
| `codeload.github.com` | ✅ | 可用，但需 OpenSSL 客户端 |
| `raw.githubusercontent.com` | ✅ | 可用 |
| `pypi.org` / `pypi.tuna.tsinghua.edu.cn` | ✅ | 可用（本机 pip 已配清华镜像） |
| `*..scau.edu.cn` | ✅ | **全校站点基本可达**（见 3.3） |
| `ghfast.top` / `gh-proxy.com` | ✅ | GitHub 代理，**实测可 clone** |

**实测可用的 clone 命令**（本仓库就是这样拉下来的）：

```powershell
git -c http.sslBackend=openssl clone --depth 1 `
    https://ghfast.top/https://github.com/unclecode/crawl4ai.git crawl4ai
```

拉到后把远端归一化，日后想直连也能用：

```powershell
git -C crawl4ai remote set-url origin https://github.com/unclecode/crawl4ai.git
git -C crawl4ai remote add mirror https://ghfast.top/https://github.com/unclecode/crawl4ai.git
# 本机 `git fetch mirror` 才是能用的那个
```

### 3.2 TLS：Windows schannel 在沙箱内失效，用 OpenSSL

沙箱内的受限令牌拿不到 TLS 凭证，任何走 schannel 的客户端都会失败：

```
curl: (35) schannel: AcquireCredentialsHandle failed: SEC_E_NO_CREDENTIALS (0x8009030e)
```

**解决方案**（三条都可行，按偏好选）：

| 方式 | 命令 |
|---|---|
| **Python（推荐做抓取/下载）** | 用自带 Python，其 `ssl` 是 OpenSSL 3.5.8，正常 |
| **git** | 加 `-c http.sslBackend=openssl` |
| **curl** | 避免使用 Windows 自带 curl；必要时改用 Python |

本机自带 Python：

```
C:\Users\FlyingBlock\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe
```

### 3.3 SCAU 站点可达性实测

用 Python(OpenSSL) 探测 37 个代表性地址，结果：

- **35 个返回 HTTP 200**，包括主站列表页、全部分生物相关学院、本科生院、研究生院、科学研究院、学工部、团委、创新创业学院、就业网、招生网、图书馆。
- `vet.scau.edu.cn/tzgg/list.htm` **实际可访问**（301 → `list.psp` 后返回 200）——`web.md` 标注的「抓取失败」是当时工具不跟随跨协议跳转所致，**新方案不必放弃该栏目**。
- `xg.scau.edu.cn/xwdt/list.htm` 同样 301 → `list.psp`，可正常抓取。
- ❌ `cxcygl.scau.edu.cn`（学科竞赛管理系统）：TLS 握手被中断（`UNEXPECTED_EOF_WHILE_READING`），属登录态系统，跳过。
- ⚠️ `scholar.scau.edu.cn`（学术成果库）→ 302 跳 `cas.scau.edu.cn` 登录，需登录。
- ⚠️ `webplus.scau.edu.cn/_s83/main.psp`：返回 `IncompleteRead`，旧版页需容错读取。

**结论**：数据源质量很好，主要工作量在解析与治理，不在突破反爬。

### 3.4 Python 包安装：沙箱内装不了

沙箱内 `ensurepip` 与 `pip` 都会失败，根因是 **Python 的 `tempfile.mkdtemp()` 以 0700 权限建目录，沙箱令牌对它没有写权限**：

```
PermissionError: [Errno 13] Permission denied: '...\pip-unpack-xxxx\six-1.17.0-py2.py3-none-any.whl'
```

- `python -m venv .venv` → 失败于 `ensurepip`
- 绕过办法（已实测可行）：`python -m venv --without-pip .venv`，再把自带 Python 的 `pip` 与 `pip-*.dist-info` 复制进 `.venv\Lib\site-packages`
- 但**即使 pip 能启动，安装仍会因上述 temp 权限失败**

**因此：装依赖请在沙箱外的普通终端里做。**

```powershell
# 在普通 PowerShell（非 DSH 沙箱）里执行
cd D:\Documents\Desktop\SCAU
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -e .\crawl4ai          # 从本地源码装，避免拉 GitHub
.\.venv\Scripts\python.exe -m pip install typer rich pyyaml jieba pydantic httpx
.\.venv\Scripts\crawl4ai-setup                                  # 装 Playwright 浏览器
.\.venv\Scripts\crawl4ai-doctor                                 # 自检
```

> 若 `crawl4ai-setup` 失败，手动装浏览器：
> `python -m playwright install --with-deps chromium`

### 3.5 ⚠️ 工作区被清空的真实事故（务必设防）

**本次开发过程中确实发生了**：`D:\Documents\Desktop\SCAU` 下的文件在 **16:43–16:44** 被批量移入回收站，包括你原有的 `groupA_recon.md`、我克隆好的 `crawl4ai\`、以及各子任务产出的 `scau_bio_seed.yaml` / `scau_bio_seed.md` / `crawl4ai-api-reference-0.9.4.md`。回收站元数据可证（`$I` 记录里保存了原始路径与删除时间）：

```
$IPEKDEX.md      size=36361   deleted=2026-10-13 16:43  D:\Documents\Desktop\SCAU\groupA_recon.md
$IM51X1Z         size=38652364 deleted=2026-10-13 16:43  D:\Documents\Desktop\SCAU\crawl4ai
$INQ5BU2.yaml    size=76803   deleted=2026-10-13 16:43  D:\Documents\Desktop\SCAU\scau_bio_seed.yaml
```

三次批量删除的时间戳（16:43:21、16:44:53、16:47:21）与**在工作区内执行 `Remove-Item` 的时刻完全重合**，而每次被冲掉的都是「本次会话新增/改动过的全部文件」，并不只是被删的那一个。由此得到的经验规则（**已实测有效**）：

> **在这个工作区里不要执行任何删除操作。** 一次删除会连带把本次会话新增的所有文件一起冲进回收站。
> 需要清理时改用「覆盖写」或「改名」；真必须删，就把文件移到工作区**之外**，或干脆留着。

**当前状态**：上述文件均已从回收站恢复（见 §3.6），并已静置 45 秒、期间无任何删除操作，保持稳定。请把下面几条当作硬约束：

1. **绝不删除本工作区内的文件**（见上方结论）——这是最重要的一条。
2. **重要产物立刻做异地备份**：把 `harness\`、`data\crawler.db`、`seeds.yaml` 定期复制到工作区之外（网盘 / 另一个盘）。
3. **代码放进 git**：`git init` + 每次提交，回收站恢复比版本回滚麻烦得多。
4. **回收站是你的救命稻草**：文件不是永久删除，先查回收站再重做。
5. 若再次出现批量消失，**先停止一切写操作**，把回收站里的 `$R*` 条目复制回工作区（见 §3.6）。

### 3.6 事故恢复手册（可复用）

文件被删/消失时：

```powershell
# 1) 列出回收站里每一项的原始路径、大小、删除时间
$py = 'C:\Users\FlyingBlock\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
& $py -c @'
import os, struct, datetime
rb = os.path.join("D:\\", "$RECYCLE.BIN", "S-1-5-21-765924418-2016796670-3783286021-1001")
for n in sorted(os.listdir(rb)):
    if not n.startswith("$I"): continue
    b = open(os.path.join(rb, n), "rb").read()
    size = struct.unpack("<Q", b[8:16])[0]
    ft   = struct.unpack("<Q", b[16:24])[0]
    when = datetime.datetime(1601,1,1) + datetime.timedelta(microseconds=ft/10)
    path = b[24:].decode("utf-16-le", "ignore").rstrip("\x00")
    print("%-16s size=%-11d deleted=%s  %s" % (n, size, when.strftime("%Y-%m-%d %H:%M"), path))
'@
```

```powershell
# 2) 恢复：只能「复制」回来，不能 move —— $RECYCLE.BIN 在工作区之外，
#    沙箱拒绝从那里删除/移动，但允许读；写目标在工作区内，允许。
& $py -c @'
import shutil
rb  = r"D:\$RECYCLE.BIN\S-1-5-21-765924418-2016796670-3783286021-1001"
dst = r"D:\Documents\Desktop\SCAU"
shutil.copy2(rb + r"\$RPEKDEX.md", dst + r"\groupA_recon.md")      # 文件：copy2
shutil.copytree(rb + r"\$RM51X1Z", dst + r"\crawl4ai", dirs_exist_ok=True)  # 目录：copytree
'@
```

> 目录恢复可能因个别文件权限失败（实测 `.git/objects/pack/*.idx` 读不了）。对仓库而言**直接重新 clone 更省事**。

---

## 4. 数据源层：把 `web.md` 变成机器可读种子

### 4.1 `web.md` 的结构

它是一份人工核验过的站点总览（4118 行），结构规整，非常适合程序化解析：

- 章节：`## 0..13`，其中 §2 教学单位、§3 机关部处、§8 招生就业校友、§9 专题网站最关键。
- 表格：`| 栏目名称 | 列表页 URL | 说明 |`，URL 有绝对形式也有「前缀 + 相对路径」形式。
- 状态记号：`✅` 可访问 / `⚠️` 结构特殊（需登录、JS、跨协议）/ `❌` 失败 / `未确认`。

**解析要点**：

1. 表格里常写「前缀 `https://life.scau.edu.cn`」+ 单元格给 `/tzgg/list.htm` → 必须拼接成绝对 URL。
2. 行内可能混入说明文字，要用正则提取真正的 URL。
3. 同一 URL 可能在多章节重复出现 → 按 URL 去重，但保留 topic 标签。
4. 状态记号要映射成枚举，供后续「是否抓取」决策。

### 4.2 种子清单格式

本工作区已经有一份生成好的、可直接使用的种子文件：**`scau_bio_seed.yaml`**（76 KB，10 个分组、390+ 条站点，约 60 条 excluded）。格式如下：

```yaml
meta:
  source: web.md
  note: "所有 URL 逐字取自 web.md"
groups:
  - id: competition_and_innovation
    name: "创新创业与学科竞赛"
    priority: 1                     # 1 最高
    why: "生物专业学生参加国创、挑战杯、生化大赛等赛事的通知、立项与成果都在这几个入口发布。"
    sites:
      - name: "创新创业学院—双创赛事"
        url: "https://cxcyxy.scau.edu.cn/4439/list.htm"
        site: "cxcyxy.scau.edu.cn"
        status: ok                  # ok | unverified | broken | login_required
        kind: list                  # list | single_page | system
        topic: competition          # competition | academic | student_affairs | career
                                    # | research | college | admissions | general
        volume: "…"                 # 可选：条数/页数，用于估算规模
excluded:
  - {url_or_pattern: "https://cas.scau.edu.cn", reason: "登录墙（统一身份认证）"}
```

10 个分组：`competition_and_innovation`、`undergraduate_academic`、`graduate`、`student_affairs_and_youth_league`、`career`、`research_and_grants`、`colleges_bio`、`admissions`、`schoolwide_news_and_notices`、`library_and_resources`。

### 4.3 若要从 `web.md` 重新生成种子

```python
# src/harness/seeds.py
"""把 web.md 的表格解析成种子清单。"""
import re
from pathlib import Path

URL_RE = re.compile(r"https?://[^\s|`)\]]+")
PREFIX_RE = re.compile(r"前缀\s*`?(https?://[^\s`]+)`?")
STATUS_MAP = {"✅": "ok", "❌": "broken", "未确认": "unverified", "⚠️": "unverified"}


def parse_webmd(path: Path) -> list[dict]:
    """按行扫描表格行，抽取 (名称, URL, 状态)。"""
    out, prefix, section = [], None, None
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("## "):
            section = line[3:].strip()
            prefix = None
            continue
        m = PREFIX_RE.search(line)
        if m:
            prefix = m.group(1).rstrip("/")
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2 or set(cells[0]) <= set("-: "):
            continue                      # 表头分隔行
        name, cell = cells[0], cells[1]
        urls = URL_RE.findall(cell)
        if not urls and prefix and cell.startswith("/"):
            urls = [prefix + cell]        # 「前缀 + 相对路径」拼接
        for url in urls:
            status = next((v for k, v in STATUS_MAP.items() if k in line), "unverified")
            out.append({"name": name, "url": url, "status": status, "section": section})
    # 去重，保留首次出现的 section
    seen, uniq = set(), []
    for r in out:
        if r["url"] not in seen:
            seen.add(r["url"])
            uniq.append(r)
    return uniq
```

> **注意**：解析结果**必须人工抽查**。这份清单是系统的地基，一条错 URL 会带来持续的无效抓取。本工作区的 `scau_bio_seed.yaml` 已经过逐条比对（349 条 site url 在 `web.md` 中 100% 字面命中），优先直接用它。

### 4.4 针对「生物专业」问题的种子裁剪策略

不要一上来就抓 390 个栏目。先按**问题意图**分层：

| 优先级 | 分组 | 理由 |
|---|---|---|
| **P1** | `competition_and_innovation`、`colleges_bio`（生命科学学院为核心） | 直接回答「能参加什么竞赛」 |
| **P1** | `undergraduate_academic`、`graduate` | 保研/考研/学分认定的政策源 |
| **P1** | `student_affairs_and_youth_league`、`career` | 团委科技活动、就业质量年报 |
| **P2** | `research_and_grants` | 科研训练、进实验室、讲座 |
| **P3** | `admissions`、`schoolwide_news_and_notices`、`library_and_resources` | 背景信息 |

**关键提示**：`colleges_bio` 里最值钱的不是「学院新闻」，而是这些栏目——

- `https://life.scau.edu.cn/shds/list.htm` 生物化学实验技能大赛（**校级招牌赛事**）
- `https://life.scau.edu.cn/deswjw2026n/list.htm` 及历届 `dessjw2025n` / `dessjw2024n` …（**历届存档 = 现成的时间线与获奖实例**）
- `https://life.scau.edu.cn/jzbg/list.htm` 讲座报告
- `https://life.scau.edu.cn/tzgg/list.htm` 通知公告（645 条 / 47 页）
- 各学院 `zsjy` / `jy` / `sx` 等招生就业栏目（含升学名单）

---

## 5. 采集层：crawl4ai 抓 SCAU 站点群

### 5.1 为什么用 crawl4ai

- 输出**为 LLM 准备的 Markdown**（自带正文提取、去噪）。
- 支持 `JsonCssExtractionStrategy`（免费结构化，适合列表页）与 `LLMExtractionStrategy`（语义抽取）。
- 有 `arun_many` + `MemoryAdaptiveDispatcher` + `RateLimiter`（**礼貌抓取**，对校方站点很重要）。
- 有缓存（`CacheMode`），增量更新成本低。
- 支持 hook（登录流、加 cookie），应对将来需要登录的栏目。

本地源码在 `D:\Documents\Desktop\SCAU\crawl4ai`（v0.9.4，HEAD `aadd82b`），API 速查见 §13 与 `crawl4ai-api-reference-0.9.4.md`。

### 5.2 Webplus 站点的三条规律（决定抓取策略）

```
列表页：  https://life.scau.edu.cn/tzgg/list.htm
分页：    …/tzgg/list2.htm → list3.htm → … → listN.htm
正文页：  https://life.scau.edu.cn/2026/1013/c19097a448632/page.htm
                        └──┬──┘ └─┬─┘ └──┬──┘
                         年月日  栏目号  文章号  ← 去重键是 a448632
```

- **旧版**：`/数字栏目号/list.htm`，正文可能以 `.psp` 结尾。
- **多模板集群（主站特有）**：`/_s数字/`（站点区）、`/_t数字/`（模板区）。
- **分页不要猜页数**：抓 `list.htm` 后从「尾页」链接读出最大 N。

### 5.3 第一步：抓列表页并抽出文章条目（CSS，不烧 token）

```python
# src/harness/crawler.py
import json
from urllib.parse import urljoin

from crawl4ai import (
    AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode,
    JsonCssExtractionStrategy,
)

# Webplus 列表页通用结构：ul.list > li，内含 <a href> 与日期
LIST_SCHEMA = {
    "name": "WebplusList",
    "baseSelector": "ul.list li, ul.news_list li, div.list li",
    "fields": [
        {"name": "title", "selector": "a", "type": "text"},
        {"name": "href",  "selector": "a", "type": "attribute", "attribute": "href"},
        {"name": "date",  "selector": "span, .date, .news_date", "type": "text"},
    ],
}

BROWSER = BrowserConfig(
    headless=True,
    viewport_width=1280,
    viewport_height=800,
    # 对校方站点保持诚实的 UA，不伪装成随机浏览器
    user_agent="SCAU-Research-Harness/0.1 (+contact: your-mail@example.com)",
    light_mode=True,
)

def list_config(page_url: str) -> CrawlerRunConfig:
    return CrawlerRunConfig(
        cache_mode=CacheMode.ENABLED,          # 增量抓取靠它
        extraction_strategy=JsonCssExtractionStrategy(LIST_SCHEMA),
        page_timeout=45_000,
        wait_until="domcontentloaded",
        exclude_external_links=True,
        verbose=False,
    )

async def fetch_list(crawler: AsyncWebCrawler, page_url: str) -> list[dict]:
    result = await crawler.arun(url=page_url, config=list_config(page_url))
    if not result.success:
        return []
    items = json.loads(result.extracted_content or "[]")
    for it in items:
        it["url"] = urljoin(page_url, it.get("href") or "")
        it["from_list"] = page_url
    return [it for it in items if it["url"].startswith(("http://", "https://"))]
```

> **容错**：`baseSelector` 覆盖不到所有模板。先在 5–10 个代表性站点上跑，看抽出的条数是否与 `web.md` 记录的「条数/页数」吻合；不吻合就补选择器，**不要**急着上 LLM。

### 5.4 第二步：确定分页上限

```python
# 从列表页 HTML 里找「尾页」的最大 listN.htm
import re
from urllib.parse import urljoin

PAGE_RE = re.compile(r"list(\d+)\.htm")

def max_page(html: str, list_url: str) -> int:
    nums = [int(n) for n in PAGE_RE.findall(html)]
    return max(nums) if nums else 1

def page_urls(list_url: str, n: int) -> list[str]:
    base = list_url[:-len("list.htm")]           # …/tzgg/
    return [list_url] + [f"{base}list{i}.htm" for i in range(2, n + 1)]
```

**限额策略**：超大栏目必须截断，否则第一次跑就要几小时。

| 栏目 | 规模 | 建议 |
|---|---|---|
| 主站 媒体华农 `/17864/list.htm` | 460 页 | 只抓最近 5 页 |
| 宣传部 媒体华农 `/380/list.htm` | 92 页 | 只抓最近 5 页 |
| 研究生院 通知公告 `/208/list.htm` | 105 页 | 最近 10 页 + 按关键词过滤 |
| 科学研究院 通知公告 `/tzgg/list.htm` | 129 页 | 最近 10 页 |
| 生命科学学院 通知公告 `/tzgg/list.htm` | 47 页 | 全抓（核心源） |
| 创新创业学院 各赛事栏目 | 小 | 全抓 |

```python
MAX_PAGES = {
    "www.scau.edu.cn/17864": 5,
    "xcb.scau.edu.cn/380": 5,
    "yjsy.scau.edu.cn/208": 10,
    "kyy.scau.edu.cn/tzgg": 10,
}
DEFAULT_MAX_PAGES = 20
```

### 5.5 第三步：抓正文并去重

```python
# 去重键：URL 里的 a{文章号}；没有则退回规范化 URL
import re
from urllib.parse import urlsplit, urlunsplit

ARTICLE_ID = re.compile(r"/c\d+a(\d+)/")
NUM_COL    = re.compile(r"/(\d{3,6})/list\d*\.htm$")

def dedupe_key(url: str) -> str:
    m = ARTICLE_ID.search(url)
    if m:
        return "a" + m.group(1)          # ★ 主站聚合页会把同一文章挂到多个栏目号下
    return normalize_url(url)

def normalize_url(url: str) -> str:
    """统一 https、去 fragment、去常见跟踪参数、目录补斜杠。"""
    p = urlsplit(url)
    scheme = "https" if p.scheme in ("http", "https") else p.scheme
    path = p.path or "/"
    return urlunsplit((scheme, p.netloc.lower(), path, "", ""))
```

正文抓取配置：

```python
from crawl4ai import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy_lxml import PruningContentFilterLXML

def article_config() -> CrawlerRunConfig:
    return CrawlerRunConfig(
        cache_mode=CacheMode.ENABLED,
        markdown_generator=DefaultMarkdownGenerator(
            # LXML 版比旧 PruningContentFilter 快约 10 倍，参数一致（旧版已废弃）
            content_filter=PruningContentFilterLXML(threshold=0.48),
            content_source="cleaned_html",
        ),
        # Webplus 正文通常在这些容器里；留空则用整页
        target_elements=["div.content", "div.article", "div.v_news_content"],
        excluded_tags=["script", "style", "nav", "footer", "header"],
        page_timeout=45_000,
        word_count_threshold=15,
        verbose=False,
    )
```

### 5.6 并发与礼貌抓取（重要）

对学校站点**务必限速**。用 `SemaphoreDispatcher` + `RateLimiter` 更可控：

```python
from crawl4ai import AsyncWebCrawler, MemoryAdaptiveDispatcher, RateLimiter

async def crawl_articles(urls: list[str]) -> list:
    dispatcher = MemoryAdaptiveDispatcher(
        memory_threshold_percent=80.0,
        max_session_permit=6,                     # 单站并发别太高
        rate_limiter=RateLimiter(
            base_delay=(1.0, 2.5),                # 每次请求随机延迟 1~2.5s
            max_delay=30.0,
            max_retries=3,                        # 429/503 自动退避
        ),
    )
    async with AsyncWebCrawler(config=BROWSER) as crawler:
        return await crawler.arun_many(
            urls, config=article_config(), dispatcher=dispatcher
        )
```

同时：

- `CrawlerRunConfig(check_robots_txt=True)` 可开启 robots 检查（首次跑建议开着）。
- 抓取是**低频批任务**（每天/每周一次），不是实时查询。把「采集」与「问答」彻底解耦。

### 5.7 跨协议跳转的处理

SCAU 大量页面在 `http`/`https` 之间互跳，`list.htm` 有时 301 到 `list.psp`。策略：

1. 所有 URL 一律**规范化成 https** 再入队。
2. 抓取结果里读 `result.redirected_url`，若落到 `list.psp` 则把该 `psp` 地址回写进栏目表，下次直接用。
3. 若仍失败，改抓旧版路由 `/_s{站点ID}/{栏目}/list.psp`（`web.md` §10.3 有站点 ID 对照表）。
4. **别把一次失败当永久失效**——实测兽医学院、学工部的「抓取失败」在新方案下都成功了。

---

## 6. 解析与结构化层

### 6.1 从正文抽出结构化字段

两条路，先用免费的：

**A. CSS 抽取（优先）**——正文里的固定结构，如讲座信息表：

```python
LECTURE_SCHEMA = {
    "name": "Lecture",
    "baseSelector": "div.v_news_content",
    "fields": [
        {"name": "title",    "selector": "h1, .title", "type": "text"},
        {"name": "body",     "selector": "div", "type": "html"},
        {"name": "pub_date", "selector": ".info, .date", "type": "text"},
    ],
}
```

**B. LLM 抽取（语义判断）**——只对「疑似竞赛/项目/政策」的文档跑，省 token：

```python
# src/harness/extract.py
from crawl4ai import LLMConfig, LLMExtractionStrategy

COMPETITION_SCHEMA = {
    "type": "object",
    "properties": {
        "is_competition": {"type": "boolean"},
        "name":           {"type": "string"},     # 赛事名称
        "level":          {"type": "string"},     # 国家级/省级/校级/院级
        "organizer":      {"type": "string"},
        "eligible":       {"type": "string"},     # 面向对象/专业限制
        "signup_deadline":{"type": "string"},     # 报名截止（尽量 ISO 日期）
        "event_time":     {"type": "string"},
        "requirements":   {"type": "string"},
        "awards":         {"type": "string"},
        "contact":        {"type": "string"},
    },
    "required": ["is_competition", "name"],
}

def competition_strategy() -> LLMExtractionStrategy:
    return LLMExtractionStrategy(
        llm_config=LLMConfig(
            provider="deepseek/deepseek-chat",        # 便宜、中文强
            api_token="env:DEEPSEEK_API_KEY",         # 见 §10.2 密钥管理
        ),
        schema=COMPETITION_SCHEMA,
        extraction_type="schema",
        instruction=(
            "从这篇华南农业大学的网页正文中判断它是否在讲一个学生可参加的竞赛/大赛/"
            "创新创业项目。若是，抽取赛事名称、级别、主办方、面向对象（是否限制专业）、"
            "报名截止时间、举办时间、参赛要求、奖项、联系方式。"
            "日期尽量转成 YYYY-MM-DD；文中没有的字段留空，不要编造。"
        ),
        input_format="fit_markdown",                  # 用过滤后的正文省 token
        chunk_token_threshold=4096,
        apply_chunking=True,
        extra_args={"temperature": 0.0, "max_tokens": 1200},
    )
```

> ⚠️ **API 陷阱**：`LLMExtractionStrategy` 的 `provider` / `api_token` 参数**已废弃**，传非默认值会抛 `AttributeError`；必须放进 `LLMConfig`。`extra_args` 也不是声明参数，靠 `**kwargs` 传入。

### 6.2 日期解析（中文页面）

```python
import re, datetime

_DATE_PATTERNS = [
    (re.compile(r"(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})"), (1, 2, 3)),
    (re.compile(r"(\d{4})[-/年](\d{1,2})月?"),            (1, 2, None)),
]

def parse_cn_date(text: str) -> datetime.date | None:
    if not text:
        return None
    t = text.strip().replace("　", " ")
    for rx, (y, m, d) in _DATE_PATTERNS:
        mo = rx.search(t)
        if mo:
            year = int(mo.group(y)); month = int(mo.group(m)); day = int(mo.group(d)) if d else 1
            try:
                return datetime.date(year, month, day)
            except ValueError:
                continue
    return None
```

**时效性是本系统的生命线**：所有进入答案的条目都必须带 `pub_date` 与 `crawled_at`，输出时标注「信息时间」，过期条目自动降权或标注「已过期，请以官网为准」。

### 6.3 正文清洗要点

- 去掉 Webplus 常见的「上一条/下一条」「分享到」「浏览次数」样板文字。
- 保留正文内的**附件链接**（`.doc/.pdf/.xlsx`）——竞赛通知的关键信息（报名表、时间表）常在附件里，正文里只写「详见附件」。**附件应单独抓取并解析**（`pypdf` / `python-docx`）。
- 图片型通知（扫描件）：本文档未做 OCR，如需可后续加 `PaddleOCR`。校纪委首页就是纯图站，此类站点优先级低。

---

## 7. 存储与检索引擎

### 7.1 起步方案：SQLite + FTS5（推荐）

零运维、单文件、够用。中文检索用 FTS5 + `jieba` 预分词。

```sql
-- data/schema.sql
CREATE TABLE IF NOT EXISTS site (           -- 站点/栏目
  id           INTEGER PRIMARY KEY,
  group_id     TEXT NOT NULL,
  name         TEXT NOT NULL,
  list_url     TEXT NOT NULL UNIQUE,
  site         TEXT,                        -- 域名
  topic        TEXT,
  status       TEXT,                        -- ok/unverified/broken/login_required
  max_page     INTEGER,                     -- 实测页数上限
  last_crawl   TEXT
);

CREATE TABLE IF NOT EXISTS article (
  id           INTEGER PRIMARY KEY,
  dedupe_key   TEXT NOT NULL UNIQUE,        -- 'a{文章号}' 或规范化 URL
  site_id      INTEGER REFERENCES site(id),
  url          TEXT NOT NULL,
  title        TEXT,
  pub_date     TEXT,                        -- ISO
  author       TEXT,
  markdown     TEXT,                        -- 正文 markdown
  fit_markdown TEXT,                        -- 过滤后正文
  attachments  TEXT,                        -- JSON 数组
  crawled_at   TEXT NOT NULL,
  http_status  INTEGER,
  content_hash TEXT                         -- 正文指纹，用于判断是否更新
);

CREATE TABLE IF NOT EXISTS field (          -- LLM/CSS 抽出的结构化字段
  article_id   INTEGER REFERENCES article(id),
  key          TEXT,
  value        TEXT,
  confidence   REAL,
  model        TEXT,
  PRIMARY KEY (article_id, key)
);

CREATE TABLE IF NOT EXISTS crawl_log (
  id         INTEGER PRIMARY KEY,
  url        TEXT,
  status     TEXT,        -- ok | http_error | blocked | redirect_loop | empty
  http_code  INTEGER,
  bytes      INTEGER,
  ms         INTEGER,
  error      TEXT,
  ts         TEXT NOT NULL
);

-- 全文索引（contentless 不行，需要回表取正文；用普通 FTS5 表）
CREATE VIRTUAL TABLE IF NOT EXISTS article_fts USING fts5(
  title, body, tokenize='unicode61'
);
```

写入时对 `title`/`body` 用 `jieba` 切词后以空格连接（FTS5 的 `unicode61` 对中文按字切分，效果一般；也可直接用 `trigram` 或换成 `simple` + 预分词）。

### 7.2 进阶方案：混合检索

数量级参考：若抓 390 个栏目 × 平均 20 页 × 20 条 ≈ **15 万篇**。这个量级：

- **FTS5 完全够用**（毫秒级）。
- 加向量检索能提升「同义表达」召回（如「推免」vs「保研」），但不是必需。

```python
# src/harness/retrieve.py —— RRF 融合（倒数排名融合）
def rrf_merge(rank_lists: list[list[int]], k: int = 60) -> list[tuple[int, float]]:
    scores: dict[int, float] = {}
    for ranks in rank_lists:
        for i, doc_id in enumerate(ranks, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + i)
    return sorted(scores.items(), key=lambda kv: -kv[1])
```

**元数据过滤比向量更重要**：把「近 2 年」「生命科学学院相关」「topic=competition」作为硬过滤条件，往往比调模型有效得多。

### 7.3 索引字段建议

对每条文章，除了正文，额外索引这些**机器可用信号**，Agent 会大量用到：

| 字段 | 来源 | 用途 |
|---|---|---|
| `topic` | 种子分组 | 限定检索范围 |
| `college` | 域名的学院映射 | 「我们学院的」 |
| `pub_date` | 解析 | 时效过滤、排序 |
| `is_competition` / `level` | LLM 抽取 | 「国家级竞赛有哪些」 |
| `signup_deadline` | LLM 抽取 | 「最近能报名的」 |
| `attachments` | 页面解析 | 提醒用户看附件 |

---

## 8. 编排层：Agent 如何回答「发展路线」类问题

这是整个系统的智力核心。不要做成「一次检索 + 一次生成」，要做成**多轮检索 + 缺口驱动**。

### 8.1 处理流程

```
用户问题
  │
  ├─① 意图分解（LLM）：把开放问题拆成可检索的子问题
  │     「生物专业能参加什么竞赛、走什么发展路线」
  │       → 子查询 A: 生命科学学院/农学院 学生可参加的竞赛与大赛
  │       → 子查询 B: 创新创业学院 大创/国创/挑战杯 报名与时间
  │       → 子查询 C: 本科生院 竞赛学分认定/推免加分政策
  │       → 子查询 D: 研究生院 推免/保研时间线与条件
  │       → 子查询 E: 学院 升学名单/就业质量/优秀校友
  │       → 子查询 F: （公网）全国大学生生命科学竞赛 iGEM 等规则与含金量
  │
  ├─② 站内检索：每个子查询 → FTS5/混合检索 → top-k 证据（带 url+日期）
  │
  ├─③ 公网检索：对「规则/含金量/往年赛题」类子查询走联网搜索
  │
  ├─④ 缺口检测（LLM）：现有证据能否支撑回答？列出缺口
  │       例：「知道有生化大赛，但不知道 2026 年是否还在报名」
  │
  ├─⑤ 补检索：针对缺口生成新查询，回到 ②（最多 N 轮，N=2~3）
  │
  ├─⑥ 证据聚合与去重：按 (url) 与 (事件+时间) 去重，冲突信息并列呈现
  │
  └─⑦ 生成：分路线答案 + 每句带引用 + 时效标注 + 明确「未证实」项
```

### 8.2 核心原则

1. **只许引用检索到的内容**。生成时把所有证据编号（`[1] [2] …`），要求模型逐句标注来源；没有来源支撑的结论必须显式标为「推测」。
2. **时效优先**。同一赛事有多届通知时，取最新的；过期项标注「（2024 年信息，2026 年请以最新通知为准）」。
3. **区分「能参加」与「参加过」**。前者看通知的面向对象，后者看往届名单/新闻。两者都呈现，但分别标注。
4. **主动承认不知道**。问「2027 年推免政策」时，如果库里只有 2025 年文件，必须说清而不是让模型编。

### 8.3 Prompt 模板

```python
# src/harness/prompts.py

DECOMPOSE = """你是华南农业大学的信息检索助手。
把用户的问题拆成 3-7 个可用关键词检索的独立子查询，覆盖以下维度（按需取舍）：
竞赛与赛事、创新创业项目、保研/推免政策、考研与升学、科研训练与实验室、就业与实习、国际交流。
每个子查询给出：query（中文关键词短语）、scope（site|web）、reason（为什么需要）。
只输出 JSON 数组，不要解释。

用户问题：{question}
"""

ANSWER = """你在为华南农业大学的学生回答发展路径问题。只能使用下面提供的「证据」，
严禁使用证据之外的事实，严禁编造 URL、日期、赛事名称。

【证据】（每条含编号、标题、URL、发布时间、正文节选）
{evidence}

【公网证据】
{web_evidence}

【用户问题】{question}

按以下要求回答：

1. **先给结论概览**：3-5 条要点，说明这个专业主要有哪些方向。
2. **分路线展开**，每条路线包含：
   - 路线名称与适合人群
   - **具体要做什么**（逐年/逐学期的时间线）
   - **校内依据**：引用编号 + 链接 + 发布时间
   - **实例**：往届获奖、名单、讲座、公示等（有则给，无则写「未找到实例」）
   - **关键时间节点**：报名/评审/公示时间（不确定就写「以官网通知为准」）
3. **时效声明**：对每条依据标注其信息时间；超过 18 个月的标「⚠️ 可能已过期」。
4. **未证实清单**：如果某个常见方向在证据里找不到支撑，明确列出「本次未能从校内信息中证实 X」。
5. 引用格式：`[n]`，并在末尾给出 `[n] 标题 — URL（发布时间）` 列表。

用中文回答，结构清晰，不要空话套话。
"""
```

### 8.4 工具定义（若接入 function-calling 客户端）

```python
TOOLS = [
    {
        "name": "search_scau",
        "description": "在已抓取的华南农业大学站点语料中做全文检索，返回带 URL 与发布时间的片段。",
        "parameters": {
            "type": "object",
            "properties": {
                "query":  {"type": "string", "description": "中文关键词，建议 2-6 个词"},
                "topic":  {"type": "string",
                           "enum": ["competition", "academic", "student_affairs",
                                    "career", "research", "college", "admissions", "general"]},
                "since":  {"type": "string", "description": "ISO 日期，只返回此日期之后发布的"},
                "college":{"type": "string", "description": "限定学院，如 life / nxy"},
                "top_k":  {"type": "integer", "default": 8},
            },
            "required": ["query"],
        },
    },
    {
        "name": "search_web",
        "description": "联网搜索公网信息（赛事官方规则、含金量、时间安排等校内没有的内容）。",
        "parameters": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "read_article",
        "description": "读取某篇文章的完整正文（当检索片段不足时使用）。",
        "parameters": {
            "type": "object",
            "properties": {"article_id": {"type": "integer"}},
            "required": ["article_id"],
        },
    },
]
```

### 8.5 关键实现片段

```python
# src/harness/agent.py
import json
from dataclasses import dataclass

@dataclass
class Evidence:
    id: int
    title: str
    url: str
    pub_date: str | None
    snippet: str
    source: str          # "site" | "web"

class HarnessAgent:
    def __init__(self, llm, store, searcher, web_search):
        self.llm, self.store, self.searcher, self.web_search = llm, store, searcher, web_search

    async def answer(self, question: str, max_rounds: int = 2) -> str:
        subqueries = await self._decompose(question)
        evidence: list[Evidence] = []
        seen: set[str] = set()
        missing: list[str] = [sq["query"] for sq in subqueries]

        for _ in range(max_rounds + 1):
            if not missing:
                break
            newly: list[Evidence] = []
            for q in missing:
                scope = self._scope_of(subqueries, q)
                hits = (self.searcher.search(q, top_k=8) if scope == "site"
                        else await self.web_search(q, top_k=5))
                for h in hits:
                    if h.url not in seen:
                        seen.add(h.url)
                        h.id = len(evidence) + len(newly) + 1
                        newly.append(h)
            evidence.extend(newly)
            # 缺口检测：还有哪些子问题没有足够证据
            missing = await self._find_gaps(question, subqueries, evidence)

        return await self._generate(question, evidence)

    async def _decompose(self, question: str) -> list[dict]:
        raw = await self.llm.complete(DECOMPOSE.format(question=question))
        return json.loads(_extract_json(raw))

    async def _find_gaps(self, question, subqueries, evidence) -> list[str]:
        if not evidence:
            return [sq["query"] for sq in subqueries]
        prompt = GAP_PROMPT.format(question=question, evidence=_digest(evidence))
        raw = await self.llm.complete(prompt)
        return json.loads(_extract_json(raw)).get("missing_queries", [])[:3]

    async def _generate(self, question: str, evidence: list[Evidence]) -> str:
        site = "\n\n".join(_fmt(e) for e in evidence if e.source == "site")
        web  = "\n\n".join(_fmt(e) for e in evidence if e.source == "web")
        return await self.llm.complete(
            ANSWER.format(question=question, evidence=site or "（无）", web_evidence=web or "（无）")
        )
```

### 8.6 LLM 选型建议

| 用途 | 建议 | 理由 |
|---|---|---|
| 意图分解 / 缺口检测 / 生成 | `deepseek/deepseek-chat` | 中文强、便宜；crawl4ai 已内置 `deepseek` 前缀 |
| 批量结构化抽取 | 同上，`temperature=0.0` | 量最大，成本敏感 |
| 需要更强推理时 | 换更强的模型，仅用于最终生成 | 只跑一次 |

`LLMConfig` 支持 OpenAI 兼容端点，本地/自建模型直接指 `base_url`：

```python
LLMConfig(provider="openai/local-model", api_token="sk-local",
          base_url="http://localhost:8000/v1")
```

> ⚠️ **陷阱**：`provider` 前缀不在内置列表里时会**静默回退**到 `openai/gpt-4o` + `OPENAI_API_KEY`，不报错。写错模型名你会以为在调用 A 实际在调用 B。已内置前缀：`openai` `anthropic` `gemini` `groq` `deepseek` `ollama` `bedrock`。

---

## 9. 端到端示例：生物专业竞赛与发展路线

### 9.1 这个问题的路线图（先人工建骨架，再让系统填内容）

| 路线 | 校内信息源（种子） | 公网补充 |
|---|---|---|
| **学科竞赛** | 生命科学学院 `shds`（生化大赛）、历届 `des*jw20*n`、`jzbg`；创新创业学院 `4439`/`4457`/`4458` | 全国大学生生命科学竞赛、iGEM、挑战杯、互联网+ 的官方规则与时间 |
| **创新创业项目** | 创新创业学院 `18824`（大创）、`4455`、`scsj`、`sccg` | 国家级大学生创新创业训练计划要求 |
| **科研训练** | 生命科学学院 `jzbg`/`xsdt`、`10057`（师资）、`10101`（科研平台）；科学研究院 `kypt`/`sbjyszdsys` | 本科生进实验室的通行做法 |
| **保研/推免** | 研究生院 `156`（创新工程）、`208`；本科生院 `5113`；各学院推免通知 | 推免政策通用条件 |
| **考研** | 研究生招生 `yzb`；各学院 `yjszs` | 学科评估、院校选择 |
| **就业** | 就业创业信息网 `jyzx` 各 module、就业质量年报 | 生物行业岗位与薪资 |
| **国际交流** | 国际交流处 `fao`；都柏林学院 `gdic`；农学院英文站 | 交换项目、留学路径 |

### 9.2 一次完整问答的期望输出（节选示意）

```markdown
## 结论概览
生物类专业（生命科学学院 / 生物技术 / 生物科学）学生的可走路径主要有 5 条：
学科竞赛 → 科研训练 → 推免升学 → 考研 → 就业。其中「生化大赛」是本院最直接的入口…

## 路线 1：生物化学实验技能大赛（校级 → 省级/国家级）
- **适合人群**：大一~大三，想积累实验与团队经历
- **要做什么**
  - 大一下：关注学院 `shds` 栏目，先在实验室跟做
  - 大二上：组队报名院赛
  - 大二下~大三：以院赛成绩冲击省赛/国赛
- **校内依据**
  - 第二十五届（2026）赛事通知 [3] https://life.scau.edu.cn/deswjw2026n/list.htm（2026-xx-xx）
  - 往届存档（第 18~24 届）[4]…[9]
- **实例**：往届获奖名单见 [7]（2024 年）…
- **关键时间**：每年 x 月发布通知，x 月院赛（以官网为准）
- ⚠️ 2026 年最新通知的报名截止未在抓取范围内确认，请查 [3]

## 路线 3：推免（保研）
…（含研究生院创新工程、学院推免细则、时间线）

## 本次未能证实
- 「iGEM 校队」：校内语料中未找到 SCAU iGEM 队伍的招募或获奖记录 [公网可查]
- 「竞赛学分认定细则」：本科生院相关文件未检索到原文，需登录教务系统查看

## 引用
[3] 第二十五届生物化学实验技能大赛通知 — https://... （2026-03-12）
[4] …
```

### 9.3 建议的验收问题集（做评估用）

准备 15–20 个问题，覆盖：

1. 生物专业可以参加什么竞赛？走什么发展路线？（主问题）
2. 生化大赛怎么报名？往年什么时候办？
3. 大创项目什么时候申报？需要什么条件？
4. 生命科学学院保研率大概多少？条件是什么？
5. 有哪些和生物相关的国家级竞赛？
6. 学院有哪些实验室可以进？怎么联系导师？
7. 生物专业毕业后主要去哪就业？
8. 有没有和生物相关的国际交流项目？
9. 挑战杯/互联网+ 校赛什么时候？
10. 竞赛获奖能加学分吗？

**评估指标**：引用准确率（引用能支撑结论）、时效正确率、覆盖率（是否漏掉明显路线）、幻觉率（编造 URL/日期/赛事）。

---

## 10. 工程化、调度与成本控制

### 10.1 目录结构

```
D:\Documents\Desktop\SCAU\
├─ web.md                            # 站点清单（已有，唯一真源）
├─ scau_bio_seed.yaml                # 机器可读种子（已有）
├─ groupA_recon.md                   # 早期侦察报告（已有）
├─ crawl4ai\                         # 上游源码（已有，便于查 API / 打补丁）
├─ crawl4ai-api-reference-0.9.4.md   # API 速查（已有）
└─ harness\                          # ← 新建
   ├─ pyproject.toml
   ├─ .env                           # 密钥（勿入库）
   ├─ config/
   │  ├─ seeds.yaml                  # 由 scau_bio_seed.yaml 裁剪
   │  └─ settings.yaml               # 限额、并发、模型
   ├─ src/harness/
   │  ├─ __init__.py
   │  ├─ config.py                   # pydantic 配置加载
   │  ├─ seeds.py                    # web.md / seeds.yaml 解析
   │  ├─ crawler.py                  # crawl4ai 封装
   │  ├─ extract.py                  # CSS + LLM 抽取
   │  ├─ normalize.py                # URL/日期/正文清洗 + 去重
   │  ├─ store.py                    # SQLite 读写
   │  ├─ index.py                    # FTS5 / 向量索引
   │  ├─ retrieve.py                 # 混合检索
   │  ├─ search_web.py               # 公网搜索适配器
   │  ├─ agent.py                    # 编排
   │  ├─ prompts.py
   │  └─ cli.py                      # typer 入口
   ├─ data/
   │  ├─ crawler.db
   │  ├─ cache/                      # crawl4ai 缓存
   │  └─ raw/                        # 原始 HTML 存档（可选，便于回溯）
   └─ tests/
```

### 10.2 密钥与配置

```ini
# .env  （加入 .gitignore！）
DEEPSEEK_API_KEY=sk-xxxxxxxx
# 若用 OpenAI 兼容端点
# OPENAI_API_KEY=sk-local
# OPENAI_BASE_URL=http://localhost:8000/v1
```

`LLMConfig` 的 token 支持 `env:NAME` 语法，避免密钥硬编码：

```python
LLMConfig(provider="deepseek/deepseek-chat", api_token="env:DEEPSEEK_API_KEY")
```

### 10.3 增量更新

```python
# 只抓「新出现的文章」，靠 crawl4ai 缓存 + 库内去重双保险
async def incremental_update(store, crawler, site):
    pages = await discover_pages(crawler, site)          # 从尾页倒着抓
    new = []
    for item in pages:
        if store.has(dedupe_key(item["url"])):
            continue
        new.append(item["url"])
        if len(new) >= 50:                               # 单栏目单次上限
            break
    results = await crawl_articles(new)
    store.upsert_many(results)
```

**判重与判更新**：

- `dedupe_key` 已存在 → 跳过（除非 `content_hash` 变化，说明文章被编辑）。
- 用正文 SHA-256 做 `content_hash`，变化时更新并记入变更日志。

### 10.4 调度

Windows 计划任务，每天凌晨跑一次增量：

```powershell
$action  = New-ScheduledTaskAction -Execute 'D:\Documents\Desktop\SCAU\.venv\Scripts\python.exe' `
                                   -Argument '-m harness sync --incremental' `
                                   -WorkingDirectory 'D:\Documents\Desktop\SCAU\harness'
$trigger = New-ScheduledTaskTrigger -Daily -At 3am
Register-ScheduledTask -TaskName 'SCAU-Harness-Sync' -Action $action -Trigger $trigger
```

> **建议**：把「采集」和「问答」分成两个命令。问答要快（秒级），采集可以慢（小时级）。

### 10.5 可观测性

必须有 `crawl_log` 表，并输出每次同步的摘要：

```
同步完成：栏目 118/124 ok，新增文章 1,842，更新 23，失败 6
失败明细：vet.scau.edu.cn/tzgg → 200(list.psp 重定向，已回写)
          cxcygl.scau.edu.cn → TLS 失败（登录系统，已加入 skip 名单）
总耗时 41m12s，LLM 抽取调用 486 次，token 约 1.2M
```

失败要做到**分类归因**，而不是笼统「失败」：`http_error` / `redirect_loop` / `blocked` / `login_required` / `empty` / `parse_fail`。空栏目是正常的，不要当故障。

### 10.6 成本控制

| 手段 | 效果 |
|---|---|
| CSS 优先，LLM 兜底 | 省掉 80%+ 抽取调用 |
| `input_format="fit_markdown"` | 正文 token 降 50–70% |
| 关键词预筛（含「大赛/竞赛/申报/报名」才送 LLM） | 再降一个量级 |
| `apply_chunking=True` + 合理 `chunk_token_threshold` | 长文不爆 token |
| 抽取结果落库，永不重复抽 | 增量成本≈0 |
| `temperature=0` | 稳定 + 可缓存 |

### 10.7 合规与礼貌抓取

- **只抓公开页面**，不碰 §11.2 的登录墙系统（`cxcygl`、`xgxt`、`jwxt`、`portal`、`cas`…）。
- **限速**：单站并发 ≤ 6，请求间隔 1–2.5s，避开白天高峰。
- **标识身份**：User-Agent 写明用途与联系方式。
- **尊重 robots**：开启 `check_robots_txt`。
- **不重发**：抓到的内容仅作个人学习/研究检索，不要再公开发布原文；对外输出以摘要 + 引用链接为主。
- **数据本地化**：`data/` 不入 git，避免误传校内数据。

---

## 11. 分阶段里程碑与验收标准

| 阶段 | 目标 | 验收标准 | 预估 |
|---|---|---|---|
| **M0 环境** | venv + crawl4ai + Playwright 装好 | `crawl4ai-doctor` 通过；能抓通 1 个 SCAU 列表页 | 0.5 天 |
| **M1 种子** | `seeds.yaml` 定稿 | 抽查 30 条 URL，任意一条可 200；分组与 topic 正确 | 0.5 天 |
| **M2 采集** | 跑通 P1 分组（约 60 栏目） | 入库 ≥ 8,000 篇文章；列表条数与 `web.md` 记录吻合 | 2–3 天 |
| **M3 索引** | FTS5 检索可用 | 用「生化大赛」检索能召回对应通知，且带日期 | 1 天 |
| **M4 抽取** | 竞赛字段结构化 | 抽 200 篇人工抽查，`name`/`signup_deadline` 准确率 > 85% | 2 天 |
| **M5 问答（单轮）** | CLI 能回答主问题 | 输出含至少 3 条路线、每条 ≥ 2 条有效引用、无编造 URL | 2 天 |
| **M6 多轮 + 公网** | 缺口驱动补检索 | 验收问题集 20 题，引用准确率 > 90%，幻觉率 < 5% | 3 天 |
| **M7 增量与调度** | 每日自动更新 | 连续 3 天无人值守成功；失败有归因 | 1 天 |
| **M8 加固** | 备份 + 文档 | 数据异地备份脚本；README；恢复演练一次 | 1 天 |

**先做 M2 的「最窄可用集」**：只用 P1 分组里约 15 个栏目（生命科学学院 + 创新创业学院 + 本科生院 + 研究生院），跑通全链路，再扩量。**不要一开始就抓 390 个栏目。**

---

## 12. 已知坑清单（本机实测 + web.md 记录）

### 12.1 Webplus 站点规律类

1. **分页是 `listN.htm`**，不是 `?page=N`；末页从列表页「尾页」链接读，**别猜**。
2. **必须按 `a{文章号}` 去重**：主站聚合页会把同一文章挂到多个栏目号下（`c17646` / `c17859` / `c1300`）。只按 URL 去重会重复入库。
3. **别名入口与数字栏目互为副本**：`/xxyw/list.htm` 与 `/17646/list.htm` 同内容 → 去重键取文章号。
4. **每页条数不一**：主站 10 或 14 条，学院站常见 20 条，宣传部理论动态 50 条，兽医学院社会服务 30 条。估算规模时要按栏目取值。
5. **栏目聚合页会渲染别的栏目**：如 `cfb /xxgk/list.htm` 实际渲染 `/bszn/list.htm`。仍按文章号去重。
6. **正文页规律**：`/年/月日/c栏目号a文章号/page.htm`；旧版同形或 `.psp`。

### 12.2 网络与跳转类

7. **`http`↔`https` 互跳很常见**：统一规范化成 https 再入队，否则大量「重复失败」。
8. **`list.htm` 可能 301 到 `list.psp`**：实测 `vet.scau.edu.cn/tzgg` 与 `xg.scau.edu.cn/xwdt` 都这样，**内容是抓得到的**。读 `result.redirected_url` 并回写栏目表。
9. **`web.md` 里标「抓取失败」的栏目值得重试**：那份文档是旧工具（不跟随跨协议跳转）的结论。
10. **裸根不可用的站点**：财务处要用 `https://cwc.scau.edu.cn/main.psp`；本科生院部分 `.htm` 在 https 下命中 scheme 跳转，改用 `/_s124/xxx/list.psp`。
11. **旧版入口** `https://webplus.scau.edu.cn/_s{站点ID}/main.psp` 是最可靠的兜底路由（站点 ID 对照见 `web.md` §10.3）。
12. **旧域名仍在服务**：`dwbgs`↔`dzbgs`、`cme`↔`cmce`、`kjc`↔`kyy`、`metc`↔`inc` → 需按站点合并去重。
13. **页面内大量 `http://` 绝对链接**：解析出的文章链接要重新规范化。

### 12.3 内容与解析类

14. **`javascript:void(0)` 栏目**：农学院生物信息平台、保卫处反诈专栏、校长信箱入口等**不是 URL**，别当链接抓。
15. **模板报错残留**：`gdic.scau.edu.cn` 页面含 `[an error occurred while processing this directive]`，解析要容错。
16. **纯图站**：校纪委 `jiwei` 首页只返回一张图片，`/index.htm` 404；改从 `/_t181/` 旧版栏目进入（优先级低）。
17. **关键信息常在附件里**：竞赛通知正文常写「详见附件」，**必须抓 `.doc/.pdf/.xlsx` 并解析**，否则会漏掉报名表和截止时间。
18. **外链混排**：媒体/学术栏目常挂第三方外链（外媒、微信公众号、360eol），入库前按 `*.scau.edu.cn` 白名单过滤。
19. **空栏目 ≠ 故障**：`tyb /xwhd`、`art /2530`、`cie /zsjz`、`dongke /tzgg`、`cfb /xsjz|/kyjz` 等实测为空，抓到 0 条正常。
20. **已失效入口不必重试**：`life /life_en/`、`gcxy /gcxyen/`、`art /arten/`、`yy /yyen`、`vet /veten/`、`lf /lfen/`、`nxy /_t1378/main.htm` 等。

### 12.4 登录墙（不要碰）

21. `portal` / `cas` / `xxgk` / `mail` / `oa` / `service` / 网站群后台 `login.jsp`
22. §11.2 全部业务系统子域：`jwxt`/`jwzf`、`kyglxt`、`xgxt`、**`cxcygl`（学科竞赛管理系统）**、`jxpj`、`pay`、`vpn`、`zp`/`hr2`、`labsra`、`mis2`、`asset`、`tybtcxt`、`acm`…
23. **`cxcygl.scau.edu.cn` 实测 TLS 握手被中断**，属登录系统，直接加入 skip 名单。
24. **`scholar.scau.edu.cn` 302 跳 CAS 登录**，需登录。
25. 主站 `/1390/list.htm`（通知公告·科研类）跳 `cas` 登录 → 跳过或降权。

### 12.5 crawl4ai 0.9.4 特有坑

26. **`CrawlerRunConfig` 的 `cache_mode` 默认是 `CacheMode.BYPASS`**（不是 ENABLED）。要做增量必须显式写 `CacheMode.ENABLED`。
27. **`word_count_threshold` 默认是 `1`**（文档里写的 ~200 是错的）。太短的内容也会入库，需要自己卡。
28. **`PruningContentFilter` 已废弃**（会发 `DeprecationWarning`），改用 `PruningContentFilterLXML`（同参数、输出一致、快约 10×）。
29. **`LLMExtractionStrategy(provider=…, api_token=…)` 传值会抛 `AttributeError`** → 放进 `LLMConfig`。
30. **`result.markdown` 是 `str` 子类**，不是对象；`result.markdown.fit_markdown` 才拿过滤后正文。`result.markdown_v2` / `result.fit_markdown` 已移除，会 `AttributeError`。
31. **设了 `deep_crawl_strategy` 时 `arun()` 返回 `List[CrawlResult]`**，否则返回 `CrawlResultContainer`（属性透传到单个结果）。返回类型会变，别写死。
32. **未知 LLM provider 前缀静默回退到 `openai/gpt-4o`**，不报错 —— 模型名写错很难发现。
33. **`generate_schema` 的 `validate` 默认是 `True`**（docstring 说 False），每轮验证都会额外花 LLM 调用。
34. **`on_user_agent_updated` 是死 hook**：`set_hook` 接受但永不触发。
35. **Docker 0.9.x 加固后**：不设 `CRAWL4AI_API_TOKEN` 且非 loopback 绑定时会拒绝启动；`js_code`/`cookies`/`deep_crawl_strategy` 等在请求体里会被 **HTTP 400** 拒绝（只接受声明式选项）。

### 12.6 本机环境类

36. **GitHub 直连不通** → 用 `ghfast.top` 镜像 + `git -c http.sslBackend=openssl`。
37. **schannel TLS 在沙箱内失效** → 网络操作走 Python(OpenSSL)。
38. **沙箱内 pip 装不了包**（`mkdtemp` 0700 权限）→ 在沙箱外安装。
39. **⚠️ 工作区可能被批量清空** → 见 §3.5，务必异地备份。这不是理论风险，本次已发生一次。

---

## 13. 附录：crawl4ai 0.9.4 API 速查

完整版见 **`crawl4ai-api-reference-0.9.4.md`**（69 KB，逐条对照本地源码，含 file:line 引用）。以下是写代码最常用的部分。

### 13.1 最小可用示例

```python
import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

async def main():
    async with AsyncWebCrawler(config=BrowserConfig(headless=True)) as crawler:
        r = await crawler.arun(
            url="https://life.scau.edu.cn/tzgg/list.htm",
            config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS),
        )
        print(r.success, r.status_code)
        print(r.markdown.raw_markdown[:500])
        print(r.markdown.fit_markdown)          # 需配了 content_filter 才有
        print(len(r.links["internal"]), "internal links")

asyncio.run(main())
```

### 13.2 导入速查

```python
from crawl4ai import (
    AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode,
    CrawlResult, CrawlResultContainer,
    DefaultMarkdownGenerator,
    LLMConfig, LLMExtractionStrategy,
    JsonCssExtractionStrategy, JsonXPathExtractionStrategy, RegexExtractionStrategy,
    MemoryAdaptiveDispatcher, SemaphoreDispatcher, RateLimiter, CrawlerMonitor,
    BFSDeepCrawlStrategy, DFSDeepCrawlStrategy, BestFirstCrawlingStrategy,
    FilterChain, URLPatternFilter, DomainFilter, ContentTypeFilter, SEOFilter,
    AdaptiveCrawler, AdaptiveConfig,
)
from crawl4ai.content_filter_strategy_lxml import PruningContentFilterLXML
from crawl4ai.content_filter_strategy import BM25ContentFilter, LLMContentFilter
from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer, PathDepthScorer
```

### 13.3 `CrawlResult` 常用字段

| 字段 | 说明 |
|---|---|
| `success` / `status_code` / `error_message` | 成败与错误 |
| `html` / `cleaned_html` | 原始 / 清洗后 HTML |
| `markdown` | **`str` 子类**，值等于 `raw_markdown`；属性透传 |
| `markdown.fit_markdown` / `.markdown_with_citations` / `.references_markdown` | 过滤后正文 / 带引用 / 参考文献 |
| `extracted_content` | 抽取结果的 **JSON 字符串** |
| `links` | `{"internal": [...], "external": [...]}` |
| `media` | `{"images", "videos", "audios", "tables"}` |
| `metadata` / `tables` | 元数据 / 表格 |
| `redirected_url` / `redirected_status_code` | **处理跨协议跳转时必读** |
| `screenshot` / `pdf` / `mhtml` | 截图 / PDF / MHTML |
| `cache_status` | `hit` / `hit_validated` / `hit_fallback` / `miss` |
| `network_requests` / `console_messages` | 需在 config 里开启采集 |

### 13.4 `CacheMode`

`ENABLED` / `DISABLED` / `READ_ONLY` / `WRITE_ONLY` / `BYPASS`（**config 默认值**）

### 13.5 深爬（用于没在 `web.md` 里列出的新站点自动发现）

```python
from crawl4ai import BFSDeepCrawlStrategy, FilterChain, URLPatternFilter, DomainFilter

config = CrawlerRunConfig(
    deep_crawl_strategy=BFSDeepCrawlStrategy(
        max_depth=2, max_pages=50, include_external=False,
        filter_chain=FilterChain([
            DomainFilter(allowed_domains=["life.scau.edu.cn"]),
            URLPatternFilter(patterns=["*list*.htm*"]),
        ]),
    )
)
results = await crawler.arun(url="https://life.scau.edu.cn/", config=config)  # 返回 List[CrawlResult]
for r in results:
    print(r.url, r.metadata.get("depth"))
```

> 用途：`web.md` 会过时。深爬适合**发现新栏目**，但不适合首轮全量抓取（容易失控）。

### 13.6 CLI

```bash
crwl https://life.scau.edu.cn/tzgg/list.htm -o markdown
crwl https://life.scau.edu.cn/ --deep-crawl bfs --max-pages 30
crwl https://life.scau.edu.cn/tzgg/list.htm -q "这个页面有哪些竞赛通知"
crawl4ai-doctor          # 自检（注意：不是 crwl doctor）
```

### 13.7 Docker 自托管 API（可选，多进程共享浏览器时有用）

```bash
export CRAWL4AI_API_TOKEN=$(python -c "import secrets;print(secrets.token_hex(32))")
docker run -d -p 11235:11235 --name crawl4ai --shm-size=1g \
  -e CRAWL4AI_API_TOKEN="$CRAWL4AI_API_TOKEN" unclecode/crawl4ai:latest
curl -s http://localhost:11235/health
```

主要端点：`/md` `/html` `/crawl` `/crawl/stream` `/llm/{url}` `/screenshot` `/pdf` `/schema` `/health` `/metrics` `/playground` `/dashboard`，异步任务 `/crawl/job` `/llm/job`。

> 本机 Docker 未验证；单机单进程用**库模式更简单**。Docker 0.9.x 请求体只接受声明式参数，`js_code`、`cookies` 等会被 400 拒绝。

---

## 附：本工作区已有资产

| 文件 | 内容 |
|---|---|
| `web.md` | SCAU 全站群清单（4118 行，人工核验，唯一真源） |
| `scau_bio_seed.yaml` | 机器可读种子（10 分组、390+ 站点、~60 excluded，URL 逐字取自 `web.md`） |
| `scau_bio_seed.md` | 同上的可读版（含分组说明） |
| `groupA_recon.md` | 5 个学院的深度侦察报告（含实测状态与文章前缀） |
| `crawl4ai\` | 上游源码 v0.9.4（HEAD `aadd82b`），可查 API、可打补丁 |
| `crawl4ai-api-reference-0.9.4.md` | 逐条对照源码的 API 速查（69 KB） |

**下一步就一件事**：在沙箱外的终端建好环境（§3.4），然后从 M2 的「最窄可用集」开始——只抓生命科学学院 + 创新创业学院 + 本科生院 + 研究生院这 4 个站的 P1 栏目，跑通「抓取 → 入库 → 检索 → 回答」全链路。跑通了再扩量。
