# 功能一览

| 能力 | 说明 | 入口 |
|---|---|---|
| 校内检索 | SQLite + FTS5，中文 bigram 分词 + 覆盖度重排 | `search` / `/api/search` |
| 多轮问答 | 意图分解 → 站内 + 公网检索 → 缺口补检索 → 带引用生成 | `ask` / `/api/ask` |
| 流式输出 | SSE 推 `trace` / `answer_delta` / `answer` / `cards` | `frontend/js/features/chat/index.js` |
| 对话卡片 | 活动、附件、关键时间；分值来自已核验名录，不由模型生成 | `qa/cards.py` |
| 附件解析 | pdf / doc / docx / xls / xlsx / ppt / zip / 图片，42 种扩展名 | `documents/` |
| OCR | 百度智能云（可选），图片与扫描件提字 | `documents/ocr.py` |
| 登录墙 | CAS 表单登录 / Cookie 导入 / 验证码 OCR，凭据只落 `.auth/` | `crawl/auth.py` |
| 计算器 | 绩点 / 综测 / 推免 / 门槛 / 活动篮 / 赛事名录 | `calc/` + `frontend/js/features/calc/` |
| 活动列表 | 后端筛选/排序，前端只渲染 | `/api/calc/activities` |
