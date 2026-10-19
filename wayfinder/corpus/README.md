# wayfinder/corpus/ — 语料存储与检索

SQLite + FTS5，负责「文章 / 站点 / 附件」的落库与全文检索。

## 文件

| 文件 | 作用 |
|---|---|
| `store.py` | 建表、写入、两段式检索、附件索引、统计 |

## 关键设计

- **中文 bigram 分词**：FTS5 的 `unicode61` 会把连续汉字当一个 token，
  所以入库前把中日韩字符切成二字组；查询同样切分。
- **两段式检索**：先用 `OR` 保证召回，再在 Python 侧按
  「查询词覆盖率 + BM25 + 学院/主题加权」重排。
- **附件独立 FTS**：命中附件正文时，把附件所属通知顶上来
  （通知正文往往只有「详见附件」）。
- 连接不跨线程共享：每个请求新建 `Store`，用完 `close()`。

## 对外接口

`Store.search()`、`get_article()`、`get_attachment()`、`upsert_article()`、
`upsert_attachment()`、`stats()`。写入只由采集 / 附件层调用；API 层只读。
