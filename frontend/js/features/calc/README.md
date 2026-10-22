# frontend/js/features/calc/ — 计算器

负责表单、事件绑定与结果渲染，**不做业务计分或业务匹配**；这些都在
`wayfinder/calc/` 与 `/api/calc/*`。

- `state.js`：`state`、`save`、`loadState`、`addToBasket`、`inBasket`，
  是 `localStorage['scau-calc-state-v1']` 的唯一读写入口；
- `index.js`：课程表 / 指标 / 门槛 / 口径页；调用
  `/api/calc/catalog`、`/api/calc/evaluate`；
- `activities.js`：活动篮列表；筛选/排序调用 `/api/calc/activities`，
  卡片里的“加入活动篮”只改本地状态并发事件；
- 绩点列直接渲染 `d.gpa.courses[].effective_gp`；
- 活动最高分直接读 `activity.best`；
- 通道单位/评分表直接读 catalog 的 `channel_units` / `channel_rubric`，
  通道分组读后端返回的 `channel_groups`。

新增计算口径时改后端 `calc/` 或 `calcdata/`，不要在前端补算。
