# calcdata/ — 计算器数据（进 git）

计算器的**全部学校数据**都在这里。代码里没有硬编码的折算表、权重或分值，
所以学校改细则时只改 JSON，不改 Python。

## 文件

| 文件 | 内容 |
|---|---|
| `rules.json` | 百分制→绩点折算表、重修口径、综测分项与上限、加分路由、级别/名次系数、出处 |
| `majors.json` | 专业培养方案：学分构成、逐门课程（代码/名称/学分/学期/是否计绩点/是否计排名） |
| `goals.json` | 13 条路线（保研/考研/奖学金）的门槛，每条 `{metric, op, value}` |
| `activities.json` | 通用加分项：类别、级别、主办、通道与基准分、报名时间、依据 |
| `competitions.json` | 具体赛事名录（T 84 / A 16 / B 10）与加分档位模板 |

## 约定

- 每个数据点带 `source`（出处，写到条款号）与 `confidence`
  （`verified` / `provisional` / `provisional_adjustable` / `unverified`）。
- 这些数值是**规划用**的，不是学籍依据；请用本学院当年细则核对。
- 想保留自己的版本又不想被 `git pull` 覆盖：把同名文件放到 `data/calc/`，
  会按文件逐个覆盖（`data/` 已在 `.gitignore`）。

## 校验

```powershell
python -m wayfinder calc
```

会逐分核对绩点折算表（`分数 ÷ 10 − 5`）、综测分项、活动分值、名录展开，
不一致会在 CLI 与计算器页面上报警告。
