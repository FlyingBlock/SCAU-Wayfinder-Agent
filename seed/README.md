# seed/ — 栏目种子白名单

`scau_bio_seed.yaml` 是采集的入口清单：分组、栏目名、列表页 URL、站点、主题、优先级。
抓取只会访问这里列出的栏目（以及正文里的附件链接）。

## 结构

```yaml
groups:
  - id: life
    name: 生命科学学院
    sites:
      - name: 通知公告
        url: https://life.scau.edu.cn/tzgg/list.htm
        site: life.scau.edu.cn
        topic: academic
        priority: 1
        status: ok
```

## 范围

`python -m wayfinder crawl --scope ...`：

| scope | 含义 |
|---|---|
| `narrow` | 42 个高信号栏目（推荐起步） |
| `p1` | 165 个 P1 栏目 |
| `p2` | 218 个栏目 |
| `all` | 种子全量 |

`crawl --url <列表页>` 可临时只抓一个栏目，调试用。

## 新增栏目

1. 在对应分组下加一条（`url` 必须是列表页，不是正文页）；
2. `python -m wayfinder doctor` 会检查种子数量与 `narrow` 命中；
3. 先用 `crawl --url ... --max-pages 2` 验证解析是否正常。
