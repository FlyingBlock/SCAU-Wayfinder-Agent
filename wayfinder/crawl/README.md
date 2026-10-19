# wayfinder/crawl/ — 采集域

从种子白名单出发，抓列表页与正文、处理登录墙、维护语料。

## 文件

| 文件 | 作用 |
|---|---|
| `seed.py` | 解析 `seed/scau_bio_seed.yaml`（自带 flow-mapping 解析器） |
| `curate.py` | 按范围裁剪栏目（`narrow` / `p1` / `p2`） |
| `fetcher.py` | `urllib` 抓取：URL 归一化、编码探测、限速、重试、robots |
| `parse.py` | Webplus 列表页 / 正文页解析、日期识别、导航标题判定 |
| `crawler.py` | 栏目 → 列表页 → 正文 → 入库；附件抓取；撞墙自动登录 |
| `auth.py` | CAS 表单登录、Cookie 导入、验证码 OCR、`.auth/` 凭据 |
| `crawl.py` | `python -m wayfinder crawl` 的命令实现 |
| `maint.py` | 语料体检 / 清理 / 重抓（`python -m wayfinder.crawl.maint`） |

## 边界

- 只用标准库抓取；采集阶段**不调用模型**。
- 只抓公开页面与本人有权访问的页面；滑块 / 短信 / 双因子不做绕过。
- 账号密码只落 `.auth/credentials.json`，不进 `.env`、不进日志。
- 抓取保持礼貌：默认 0.8s 间隔 + 抖动，单站并发 5。
