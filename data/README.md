# data/ — 运行时数据（不进 git）

整目录已在 `.gitignore` 中，可删除后重建：

- `crawler.db`：文章、站点、附件与 FTS 索引；
- `attachments/<年>/<月>/`：下载的附件本体；
- `cache/`：赛事名录联网缓存、OCR token 等短生命周期数据；
- `calc/`：可选的 `calcdata/*.json` 本地覆盖。

这里不放源码或需要提交的数据；要进 git 的学校数据在 `../calcdata/`。
