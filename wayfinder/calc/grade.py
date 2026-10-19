"""绩点换算与平均学分绩点。

口径说明（写在界面上给学生看）：

    一门课程的学分绩点 = 该课程的学分数 × 绩点数
    平均学分绩点 = Σ(每门课绩点 × 该课学分) / Σ(学分)

其中百分制绩点按《华南农业大学本科学生学籍管理实施细则》（华南农办〔2021〕68号）
第十二条（一）折算：60 ≤ 分数 ≤ 100 时 **绩点 = 分数 ÷ 10 − 5**，
低于 60 分为 0 绩点（100 分 = 5.00、90 分 = 4.00、80 分 = 3.00、60 分 = 1.00）。
五级制：优秀 4.50 / 良好 3.50 / 中等 2.50 / 及格 1.50 / 不及格 0。
具体数值仍以 `calcdata/rules.json` 的 `gpa` 为准，这里只说明口径。

计入范围由培养方案里每门课的 `counts_toward_gpa` 决定，默认所有课都计。
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .model import Course, GradeTable, Profile


@dataclass
class CourseResult:
    code: str
    name: str
    credits: float
    group: str
    term: int
    kind: str
    # 原始成绩（可能是数字，也可能是"优/良/中/及格"）
    raw: object = None
    # 归一化后的百分制分数（五级制会折算）
    score: float | None = None
    # 折算表算出的原始绩点
    gp: float | None = None
    # 实际计入平均学分绩点的绩点：重修课会按 retake_cap 封顶，
    # 所以它可能小于 gp。界面上的「计入绩点」显示这个值。
    effective_gp: float | None = None
    counted: bool = False
    counted_in_ranking: bool = False
    passed: bool | None = None
    note: str = ""

    @property
    def is_graded(self) -> bool:
        return self.gp is not None

    def as_dict(self) -> dict:
        return {
            "code": self.code, "name": self.name, "credits": self.credits,
            "group": self.group, "term": self.term, "kind": self.kind,
            "raw": self.raw, "score": self.score, "gp": self.gp,
            "effective_gp": self.effective_gp,
            "counted": self.counted, "passed": self.passed, "note": self.note,
        }


@dataclass
class GPAResult:
    gpa: float = 0.0                 # 加权平均学分绩点
    avg_score: float = 0.0           # 加权平均分
    credits_total: float = 0.0       # 培养方案总学分
    credits_graded: float = 0.0      # 已出成绩且计入绩点的学分
    credits_earned: float = 0.0      # 已通过（含不计绩点的实践课）
    credits_remaining: float = 0.0   # 还没修（或没出分）且计入绩点的学分
    courses: list[CourseResult] = field(default_factory=list)
    failed: list[CourseResult] = field(default_factory=list)
    ranking_gpa: float = 0.0         # 只算计入排名的课程
    ranking_credits: float = 0.0
    gpa_from_retakes: int = 0        # 有多少门是补考/重修记录
    # 综测评优口径的平均学分绩点：剔除重修课程（华农党发〔2020〕38号
    # 第六条（一）「重修课程成绩不纳入平均绩点计算范围」）。
    # 它和 `gpa` 是两套口径，见 GradeTable.comprehensive_excludes_retakes。
    gpa_no_retake: float = 0.0
    credits_no_retake: float = 0.0
    # 智育基础分实际采用的那个绩点（按规则决定是否剔除重修）
    comprehensive_gpa: float = 0.0

    @property
    def progress(self) -> float:
        if self.credits_total <= 0:
            return 0.0
        return min(1.0, self.credits_earned / self.credits_total)

    def as_dict(self) -> dict:
        return {
            "gpa": round(self.gpa, 4),
            "avg_score": round(self.avg_score, 2),
            "credits_total": self.credits_total,
            "credits_graded": round(self.credits_graded, 2),
            "credits_earned": round(self.credits_earned, 2),
            "credits_remaining": round(self.credits_remaining, 2),
            "ranking_gpa": round(self.ranking_gpa, 4),
            "gpa_no_retake": round(self.gpa_no_retake, 4),
            "credits_no_retake": round(self.credits_no_retake, 2),
            "comprehensive_gpa": round(self.comprehensive_gpa, 4),
            "failed_count": len(self.failed),
            "progress": round(self.progress, 4),
            "courses": [c.as_dict() for c in self.courses],
        }


def _normalize(table: GradeTable, raw) -> tuple[float | None, float | None]:
    """把原始成绩归一化成 (百分制分数, 绩点)。无法识别时返回 (None, None)。"""
    if raw is None or raw == "":
        return None, None
    # 五级制
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            return None, None
        for level, gp in table.levels.items():
            if s == level or s.startswith(level):
                return None, gp
        try:
            num = float(s)
        except ValueError:
            return None, None
    else:
        try:
            num = float(raw)
        except (TypeError, ValueError):
            return None, None
    return num, table.score_to_gp(num)


def compute_gpa(courses: list[Course], profile: Profile,
                table: GradeTable) -> GPAResult:
    """按培养方案 + 学生成绩算平均学分绩点。"""
    res = GPAResult()
    res.credits_total = round(sum(c.credits for c in courses), 2)

    gp_x_credit = 0.0
    graded_credits = 0.0
    no_retake_gp_x_credit = 0.0      # 剔除重修后的 绩点×学分
    no_retake_credits = 0.0
    score_x_credit = 0.0
    score_credits = 0.0
    rk_gp_x_credit = 0.0
    rk_credits = 0.0

    for course in courses:
        row = CourseResult(
            code=course.code, name=course.name, credits=course.credits,
            group=course.group, term=course.term, kind=course.kind,
        )
        raw = profile.score_of(course.code)
        row.raw = raw
        score, gp = _normalize(table, raw)
        row.score, row.gp = score, gp

        if gp is None:
            # 没出成绩：整门课算「未修」
            if course.counts_toward_gpa:
                res.credits_remaining += course.credits
            row.note = "尚未出成绩"
            res.courses.append(row)
            continue

        # 补考 / 重修口径：学生标了 `retakes` 的课，按封顶绩点计入。
        # capped   —— 官方口径（默认）：及格及以上一律折合 1.00 绩点
        #            （学籍细则第十二条（三）：补考和重修成绩按实际分数记载
        #             并标注，成绩及格及以上的绩点均折合为 1.00）
        # actual   —— 按实得分算，不封顶
        # first    —— 整门课不计入绩点（综测评优口径才这么做，见下方
        #            no_retake 的算法；学校层面它只用于智育基础分）
        # 注意：这段必须在「出成绩」分支之后、且不能早退，
        # 否则重修课会被当成普通首修课按实得分计绩点（封顶失效）。
        is_retake = course.code in set(profile.retakes or ())
        effective_gp = gp
        count_gp = True
        if is_retake:
            if table.retake_policy == "capped":
                effective_gp = min(gp, table.retake_cap)
                row.note = f"重修/补考记录，按封顶 {table.retake_cap} 绩点计入"
                res.gpa_from_retakes += 1
            elif table.retake_policy == "actual":
                row.note = "重修/补考记录，按实得分计入"
                res.gpa_from_retakes += 1
            else:  # first：重修成绩既不进绩点也不进平均分
                count_gp = False
                row.note = "重修/补考记录，成绩不计入绩点"

        row.passed = score is None or score >= table.fail_score
        if not row.passed:
            row.note = (row.note + "；" if row.note else "") + "不及格"
            res.failed.append(row)
        row.effective_gp = effective_gp if count_gp else None

        if course.counts_toward_gpa and count_gp:
            row.counted = True
            graded_credits += course.credits
            gp_x_credit += effective_gp * course.credits
            # 综测评优口径另算一份、剔除重修课程的加权绩点：
            # 华农党发〔2020〕38号 第六条（一）「重修课程成绩不纳入平均绩点
            # 计算范围」，所以重修课整门不进这个平均，而不是按 1.00 计。
            if not is_retake:
                no_retake_credits += course.credits
                no_retake_gp_x_credit += gp * course.credits
            if score is not None:
                score_x_credit += score * course.credits
                score_credits += course.credits
        elif not course.counts_toward_gpa:
            row.note = (row.note + "；" if row.note else "") + "不计绩点"

        # 不及格的课拿不到学分，必须补考/重修通过后重算
        if row.passed:
            res.credits_earned += course.credits

        if course.counts_toward_ranking and course.counts_toward_gpa and count_gp:
            row.counted_in_ranking = True
            rk_gp_x_credit += effective_gp * course.credits
            rk_credits += course.credits

        res.courses.append(row)

    res.credits_graded = round(graded_credits, 2)
    res.gpa = gp_x_credit / graded_credits if graded_credits > 0 else 0.0
    res.credits_no_retake = round(no_retake_credits, 2)
    res.gpa_no_retake = (no_retake_gp_x_credit / no_retake_credits
                         if no_retake_credits > 0 else 0.0)
    res.comprehensive_gpa = (res.gpa_no_retake
                             if table.comprehensive_excludes_retakes else res.gpa)
    res.avg_score = score_x_credit / score_credits if score_credits > 0 else 0.0
    res.ranking_credits = round(rk_credits, 2)
    res.ranking_gpa = rk_gp_x_credit / rk_credits if rk_credits > 0 else 0.0
    res.credits_remaining = round(res.credits_remaining, 2)
    res.credits_earned = round(res.credits_earned, 2)
    res.credits_total = round(sum(c.credits for c in courses), 2)
    return res


# --------------------------------------------------------------------------- #
# 反推：要达到某个目标绩点，剩下的课需要考多少分
# --------------------------------------------------------------------------- #
@dataclass
class TargetBreakdown:
    """把「总绩点要达到 X」分摊到剩余课程。"""

    target_gpa: float = 0.0
    achievable: bool = True
    message: str = ""
    # 已修部分的贡献
    locked_gp_credits: float = 0.0     # 已修：绩点×学分 之和
    locked_credits: float = 0.0
    remaining_credits: float = 0.0
    # 结果
    required_remaining_gpa: float = 0.0     # 剩余课程需要达到的平均绩点
    required_remaining_score: float = 0.0   # 对应的百分制平均分
    max_possible_gpa: float = 0.0
    difficulty: str = ""                    # easy / normal / hard / extreme
    difficulty_note: str = ""
    # 每门剩余课的独立目标分（等权提升：每门都考同一分数）
    per_course: list[dict] = field(default_factory=list)
    # 按学分加权的增量方案
    weighted_plan: list[dict] = field(default_factory=list)


def target_breakdown(gpa_res: GPAResult, courses: list[Course],
                     table: GradeTable, target_gpa: float) -> TargetBreakdown:
    """给定目标平均学分绩点，反推剩余课程需要的分数。

    做法（可在界面上解释）：

    1. 已出成绩的课已经锁定，贡献 `Σ(绩点×学分)`；
    2. 毕业时 `目标绩点 × 总学分 = 已锁定贡献 + 剩余课程必须贡献的绩点×学分`；
    3. 于是 `剩余课程平均绩点 = 剩余必须贡献 / 剩余学分`；
    4. 再用折算表把绩点反解成百分制分数。

    若第 3 步超过折算表上限（即「剩下的课全考 100 也追不上」），
    标 `achievable = False` 并给出理论上限。
    """
    bd = TargetBreakdown(target_gpa=target_gpa)
    bd.locked_credits = gpa_res.credits_graded
    # 已修部分的 绩点×学分：必须用 effective_gp（重修课已封顶），
    # 否则这里会和 gpa_res.gpa 的口径不一致，反推出来的目标分是错的。
    locked = sum((c.effective_gp or 0.0) * c.credits
                 for c in gpa_res.courses if c.counted)
    bd.locked_gp_credits = locked

    remaining = [c for c in courses if c.counts_toward_gpa
                 and c.code not in {r.code for r in gpa_res.courses if r.is_graded}]
    bd.remaining_credits = round(sum(c.credits for c in remaining), 2)

    total_credits = gpa_res.credits_total
    if bd.remaining_credits <= 0:
        bd.achievable = gpa_res.gpa >= target_gpa - 1e-9
        bd.required_remaining_gpa = gpa_res.gpa
        bd.required_remaining_score = (
            _score_for_gpa(table, gpa_res.gpa) if gpa_res.credits_graded else 0.0
        )
        bd.max_possible_gpa = gpa_res.gpa
        bd.message = ("所有课程都已出成绩，总绩点已锁定为 %.3f。" % gpa_res.gpa
                      if bd.achievable else
                      "所有课程都已出成绩，总绩点已锁定为 %.3f，低于目标 %.3f。"
                      % (gpa_res.gpa, target_gpa))
        return bd

    needed_total = target_gpa * total_credits
    need_from_remaining = needed_total - locked
    req_gp = need_from_remaining / bd.remaining_credits

    max_possible = (locked + table.max_gp * bd.remaining_credits) / total_credits
    bd.max_possible_gpa = round(max_possible, 4)

    if req_gp <= 0:
        bd.required_remaining_gpa = 0.0
        bd.required_remaining_score = 0.0
        bd.message = ("已修课程的绩点已经够了：剩余课程只要全部通过（≥60 分），"
                      "毕业总绩点就会高于目标 %.2f。" % target_gpa)
    elif req_gp <= table.score_to_gp(table.fail_score):
        # 要求的平均绩点还没到「及格线对应的绩点」——也就是剩余课程全部及格即可
        bd.required_remaining_gpa = round(req_gp, 3)
        bd.required_remaining_score = float(table.fail_score)
        bd.message = ("已修课程攒下了足够的余量：剩余 %0.1f 学分只要全部及格"
                      "（≥%g 分）就能达到目标 %.2f。"
                      % (bd.remaining_credits, table.fail_score, target_gpa))
    elif req_gp > table.max_gp + 1e-9:
        bd.achievable = False
        bd.required_remaining_gpa = round(req_gp, 3)
        bd.required_remaining_score = 100.0
        bd.message = ("剩余 %0.1f 学分需要平均绩点 %0.2f，超过上限 %0.1f。"
                      "即使全部考满分，毕业总绩点最多 %0.3f，达不到 %.2f。"
                      % (bd.remaining_credits, req_gp, table.max_gp,
                         max_possible, target_gpa))
    else:
        bd.required_remaining_gpa = round(req_gp, 3)
        bd.required_remaining_score = _score_for_gpa(table, req_gp)
        bd.message = ("剩余 %0.1f 学分需要平均绩点 %0.2f，"
                      "折算成百分制约 %0.1f 分。"
                      % (bd.remaining_credits, req_gp, bd.required_remaining_score))

    # 每门课的目标（等分摊派：每门都考 required_remaining_score）
    for course in remaining:
        bd.per_course.append({
            "code": course.code, "name": course.name,
            "credits": course.credits, "term": course.term, "kind": course.kind,
            "group": course.group,
            "required_score": bd.required_remaining_score,
        })

    # 按学分加权的方案：把「需要补的绩点×学分」平均摊到每学分上，
    # 学分高的课要求就高一点（因为一门课的影响更大），反之亦然。
    # 这里给的是等价方案：每门课都要考到 required_remaining_score 才不会拖后腿；
    # 如果学生愿意偏科，可以按 credits 反比分配 —— 用 margin 表示可浮动空间。
    total_w = sum(c.credits for c in remaining) or 1.0
    for course in remaining:
        share = course.credits / total_w
        bd.weighted_plan.append({
            "code": course.code, "name": course.name,
            "credits": course.credits,
            "credit_share": round(share, 4),
            "required_score": bd.required_remaining_score,
        })

    _grade_difficulty(bd, table)
    return bd


def _grade_difficulty(bd: TargetBreakdown, table: GradeTable) -> None:
    """给目标打个难度标签，并说明「能不能偏科换空间」。

    一律要求「每门都考 99 分」在实际中做不到，但平均绩点只约束
    Σ(绩点×学分)，所以完全可以几门拉高、几门放低。这里算一下：
    如果挑学分最大的若干门考到高分，剩下的课需要考多少分才够，
    给学生一个更可执行的方案。
    """
    if not bd.achievable:
        bd.difficulty = "impossible"
        bd.difficulty_note = (
            "按当前已修成绩，这个目标在数学上就达不到；"
            "可以考虑换目标，或者确认已修课程的成绩是否录对了。")
        return

    score = bd.required_remaining_score
    if score <= 60:
        bd.difficulty = "easy"
        bd.difficulty_note = "余量充足：剩余课程只要不挂科就够。"
    elif score <= 70:
        bd.difficulty, bd.difficulty_note = "easy", "余量充足，正常发挥即可。"
    elif score <= 80:
        bd.difficulty, bd.difficulty_note = "normal", "需要保持中上水平。"
    elif score <= 88:
        bd.difficulty, bd.difficulty_note = "hard", "要求较高，需要明显提升。"
    else:
        bd.difficulty, bd.difficulty_note = "extreme", (
            "要求非常高，剩余课程接近每门都要考到 90 分以上。")

    # 偏科方案：把学分最大的若干门冲高，看其余课程需要多少分
    if bd.remaining_credits <= 0 or not bd.per_course:
        return
    if score <= 60:
        return          # 已经「不挂科就够」，不用再给偏科方案
    courses = sorted(bd.per_course, key=lambda c: -c["credits"])
    total_credits = bd.locked_credits + bd.remaining_credits
    need = bd.target_gpa * total_credits - bd.locked_gp_credits
    if need <= 0:
        bd.difficulty_note += " 剩余课程全部及格即可，不必额外冲高。"
        return

    # 取学分最大的前 1/3 门课假设考 95 分，其余课程平摊剩下的要求
    k = max(1, len(courses) // 3)
    high, rest = courses[:k], courses[k:]
    high_score = 95.0
    high_gp = table.score_to_gp(high_score)
    supplied = high_gp * sum(c["credits"] for c in high)
    rest_credits = sum(c["credits"] for c in rest)
    if rest_credits <= 0:
        return
    rest_gp = (need - supplied) / rest_credits
    if rest_gp <= 0:
        bd.difficulty_note += (
            f" 好消息：只要把学分最大的 {k} 门课冲到 {high_score:.0f} 分，"
            f"剩下的课全部及格就够了。")
    elif rest_gp <= table.max_gp:
        rest_score = table.gp_to_score(rest_gp)
        bd.difficulty_note += (
            f" 换一种打法：把学分最大的 {k} 门课冲到 {high_score:.0f} 分，"
            f"其余 {len(rest)} 门课平均考 {rest_score:.0f} 分即可。")
    else:
        bd.difficulty_note += (
            f" 即使把学分最大的 {k} 门课全部考到 {high_score:.0f} 分，"
            f"其余课程仍需超过满分，难度没有实质缓解。")


def _score_for_gpa(table: GradeTable, gp: float) -> float:
    return round(table.gp_to_score(gp), 1)


def gpa_to_score(table: GradeTable, gp: float) -> float:
    """便捷函数：绩点 → 达到该绩点所需的最低百分制分数。"""
    return _score_for_gpa(table, gp)
