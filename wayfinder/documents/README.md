# wayfinder/documents/ — 附件与文档解析

把通知里的附件变成可检索、可引用的文本：下载 → 解析 → OCR → 入库。

## 文件

| 文件 | 作用 |
|---|---|
| `attachments.py` | 附件发现 / 下载 / 去重 / 落盘 / 解析编排 / `data/attachments/` |
| `docparse.py` | 办公文件统一入口：docx/xlsx/pptx/pdf/doc/xls/rtf/zip/文本/图片 |
| `pdftext.py` | 纯标准库 PDF 文本抽取（xref、对象流、ToUnicode、变换链） |
| `ocr.py` | 百度智能云 OCR（可选）；未配置时安全降级 |

## 约定

- 全部本地解析，不需要 key；只有图片 / 扫描件依赖 OCR。
- 落盘路径：`data/attachments/<年>/<月>/<sha1前10位>_<文件名>`，按内容哈希去重。
- 解析结果写 `attachment` 表并建独立 FTS；检索命中时会回溯到所属通知。
- 解析失败要**如实写进 `note` / `error`**，不能假装成功。
- 单篇通知默认最多 6 个附件、单文件 25MB，可用 `ATTACH_*` 调整。

## 扩展格式

1. 在 `docparse.py` 的扩展名映射里注册；
2. 写一个 `_extract_xxx()`，返回统一的结果对象（正文 / 表格数 / 图片数 / note）；
3. 在 `tests/` 里加一个不联网的样本或自造样本。
