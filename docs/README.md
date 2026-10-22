# docs/ — 设计与资料

这里放**背景资料与历史设计**，不是运行必需的。当前架构以根
[`README.md`](../README.md) 与各子包 README 为准。

| 文件 | 内容 |
|---|---|
| `FEATURES.md` | 功能一览与入口索引（从根 README 迁入，避免与远端 README 改动冲突） |
| `SCAU-LLM-Harness-开发指南.md` | 最初的系统设计指南（分层、抓取、检索、编排） |
| `web.md` | 校内站点栏目清单与抓取线索 |
| `crawl4ai-api-reference-0.9.4.md` | 外部抓取库的资料（当前实现不依赖它） |
| `groupA_recon.md` | 栏目侦察记录 |
| `archive/` | 历史进度记录，仅供追溯 |

## 阅读顺序

1. 根 [`README.md`](../README.md) — 启动与架构；
2. [`wayfinder/README.md`](../wayfinder/README.md) — 后端分层与依赖方向；
3. `wayfinder/*/README.md` — 各领域职责；
4. 本目录的指南 — 设计背景与取舍。
