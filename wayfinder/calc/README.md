# wayfinder/calc/ — 计算引擎

绩点 / 综测 / 推免 / 门槛 / 活动篮。**纯计算**：不联网、不调模型、不碰 UI。

## 文件

| 文件 | 作用 |
|---|---|
| `model.py` | 数据模型（Major / Course / Rules / Goal / Activity…） |
| `loader.py` | 读 `calcdata/*.json`、校验、支持 `data/calc/` 本地覆盖 |
| `grade.py` | 百分制 / 五级制 → 绩点，平均学分绩点，目标分反推 |
| `metrics.py` | 只读指标推算（四六级、体测、志愿时长等） |
| `basket.py` | 活动篮：活动 × 名次 → 各通道加分 |
| `comprehensive.py` | 综测五分项、加分路由与上限 |
| `goals.py` | 13 条路线的门槛判定与课程分摊 |
| `engine.py` | Facade：`Calculator.catalog()` / `evaluate_dict()` / `target_for_course()` |
| `competitions.py` | 《学生竞赛奖励办法》名录 → 具体赛事与加分档位 |

`calc` 不联网。赛事名录的「刷新联网」在
[`wayfinder/integrations/competitions.py`](../integrations/README.md)，
只在用户主动点击时调用；它把结果写进缓存，calc 下次装载时读取。

## 数据驱动

代码里没有学校特有的数字。学校改细则只改 `calcdata/` 下的 JSON：

- `rules.json` 折算表、综测分项、加分路由、系数
- `majors.json` 培养方案
- `goals.json` 门槛
- `activities.json` 通用加分项
- `competitions.json` 赛事名录与档位

想在 `git pull` 时保留自己的版本，把同名文件放到 `data/calc/`（不进 git），
会按文件逐个覆盖内置数据。

## 校验

`python -m wayfinder calc` 会检查绩点折算表（逐分核对 `分数 ÷ 10 − 5`）、
综测分项、活动分值、名录展开等，并在页面上以警告形式提示。
