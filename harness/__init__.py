"""SCAU 站点群 LLM 检索 Harness.

一个针对华南农业大学站点群的定向爬取 + 结构化检索 + LLM 编排问答系统。

设计目标（见 docs/SCAU-LLM-Harness-开发指南.md）：
  L0 种子层   web.md / scau_bio_seed.yaml  → 白名单 URL
  L1 采集层   Webplus 列表页发现 + 正文抓取
  L2 解析层   URL 归一化 / 日期解析 / a{ID} 去重 / 正文清洗
  L3 存储层   SQLite + FTS5（中文 bigram 分词）
  L4 检索层   全文检索 + 元数据过滤
  L5 编排层   意图分解 → 检索 → 缺口补检索 → 证据聚合
  L6 输出层   分路线答案 + 逐条引用 + 时效标注 + 未证实声明

纯标准库实现（仅可选依赖 lxml / python-docx），因此在本机沙箱内
无需 pip 安装即可直接运行。
"""

__version__ = "0.1.0"
