# wayfinder/qa/ — 问答编排

把「问题」变成「带引用的答案 + 卡片」，是唯一会调用 LLM 的领域。

## 文件

| 文件 | 作用 |
|---|---|
| `prompts.py` | 全部系统提示词：角色、检索范围、引用纪律、输出结构 |
| `llm.py` | OpenAI 兼容客户端：`chat` / `stream_chat` / `health` / token 用量 |
| `agent.py` | 意图分解 → 站内 + 公网检索 → 缺口补检索 → 证据聚合 → 生成 |
| `cards.py` | 从证据确定性抽取活动 / 附件 / 关键时间，并匹配已核验名录 |
| `websearch.py` | 公网搜索适配器（ddg / bocha / tavily / bing / none） |

## 生成协议

`Agent.answer(question, max_rounds, trace, dry_run, on_delta)`：

- `trace(step, data)`：检索过程，步骤名 `decompose` / `retrieve` / `retrieved` / `gaps` / `evidence` / `cards`；
- `on_delta(piece, final)`：正文增量；`final=True` 的那次片段为空，表示正文结束；
- 返回 `Answer`：`text` / `citations` / `cards` / `error` / `evidence` / `subqueries` / `prompt`。

## 硬规则

- 卡片**不由模型生成**：分数和时间来自证据与 `calcdata/`，匹配不上就如实标注。
- 检索不到就不编 URL / 日期 / 赛事名；正文只留 `[n]`，链接由前端右栏统一展示。
- 采集与卡片装配都不调模型；只有最终生成调。
- 思维链模型被截断时先攒再决定发不发，预算不够就加预算重试（见 `test_stream.py`）。
