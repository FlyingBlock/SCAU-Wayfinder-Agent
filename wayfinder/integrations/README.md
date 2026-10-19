# wayfinder/integrations/ — 外部数据集成

会联网、会写缓存，但不属于纯计算域；只在用户主动点击「刷新联网」时调用。

- `competitions.py`：抓取学校竞赛名录页与通知栏目，和内置
  `calcdata/competitions.json` 对账，缓存到 `data/cache/calc_competitions.json`。
  失败时保留上次成功结果，不阻断计算器离线使用。

`wayfinder.calc` 只读本地数据；需要联网刷新时由 API / CLI 调本目录。
