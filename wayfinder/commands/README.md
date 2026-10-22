# wayfinder/commands/ — CLI 命令适配层

根 `cli.py` 只建 parser 和 dispatch；具体命令按功能拆在这里，避免再把
1384 行的 `cli.py` 长回去。

| 文件 | 作用 |
|---|---|
| `common.py` | 共享格式化、成绩单/活动篮参数解析 |
| `chat.py` | search / ask / web |
| `crawl.py` | crawl / login / whoami / fetch |
| `documents.py` | parse / attach / attachments / ocr |
| `calc.py` | gpa / goals / activities / competitions / calc |
| `settings.py` | setup-key |
| `doctor.py` | 跨功能自检 |

新增命令：在这里加函数，在 `cli.py` 的 `build_parser()` 里注册；命令只做
CLI 展示与参数适配，领域逻辑仍放对应子包。
