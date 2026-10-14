"""对话卡片装配：把检索到的证据变成「活动 / 赛事 / 附件」卡片。

**为什么单独一层**

`harness.agent` 的产物是一段带 `[n]` 引用的长文。学生真正想在这个页面上做的事
却是「这个比赛我能不能报、加了算多少分、截止到哪天，一键丢进活动篮」。这些信息
散在几十条通知里，让模型自由发挥去编，既费 token 又不可信。

所以卡片**不由模型生成**：本模块从证据（标题/正文/发布时间/附件链接）里做确定性
抽取，再去 `calcdata` 里那张已核验的《学生竞赛奖励办法》名录与通用加分明细上匹配
档位，最后拼成前端可以直接渲染、可以「加入活动篮」的结构。一条原则：

    **分值和时间都只能来自证据或已核验数据；匹配不上就明说匹配不上。**

由此产生三种卡片：

- `activity`：具体活动/赛事。匹配上名录的带综测/推免两套加分与名录出处；
  匹配不上的照实展示（时间、主办、原文链接），并在卡上标「未匹配到已核验名录，
  暂不能计入活动篮」——宁可让用户去计算器里手工找，也不发明分值。
- `file`：附件（pdf/doc/xlsx…）。华农的竞赛通知常把报名表、赛程、名额表放在附件里，
  正文反而只有一句话，所以附件必须单独成卡。
- `time`：从通知里抽出的关键时间（报名截止/比赛时间/材料提交…），按日期排序。

这一层零 LLM 调用、零网络，纯函数，方便单测（见 `data/research/smoke_cards.py`）。
"""
from __future__ import annotations

import datetime
import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Iterable, Sequence

# --------------------------------------------------------------------------- #
# 常量
# --------------------------------------------------------------------------- #
MAX_ACTIVITIES = 6
MAX_FILES = 5
MAX_TIMES = 6
MAX_TOTAL = 14

# 通道属于哪套评分表（与 calc.basket.DEFAULT_CHANNEL_RUBRIC 同口径；
# 这里只用于展示分组，真正的分值来自 Basket 的折算）。
RUBRIC_BY_CHANNEL = {
    "德育加分": "综测", "智育加分": "综测", "体育加分": "综测",
    "美育加分": "综测", "劳育加分": "综测", "综测加分": "综测",
    "创新能力": "推免", "发展素养": "推免",
    "第二课堂": "学分", "创新创业学分": "学分", "志愿服务时长": "时长",
}
UNIT_BY_CHANNEL = {"第二课堂": "学分", "创新创业学分": "学分", "志愿服务时长": "小时"}

# 卡片左侧色条/徽标的语义（前端按 kind 取色）
KIND_ACTIVITY, KIND_FILE, KIND_TIME = "activity", "file", "time"

# 附件扩展名 → 展示用的类型标签
FILE_KINDS = {
    "pdf": "PDF", "doc": "Word", "docx": "Word", "xls": "Excel", "xlsx": "Excel",
    "ppt": "PPT", "pptx": "PPT", "zip": "压缩包", "rar": "压缩包",
    "csv": "表格", "txt": "文本",
}
FILE_EXT_RE = re.compile(r"\.(pdf|docx?|xlsx?|pptx?|zip|rar|csv|txt)(?:$|[?#])", re.I)

# --------------------------------------------------------------------------- #
# 一、文本小工具
# --------------------------------------------------------------------------- #
_PUNCT_RE = re.compile(r"[\s\u3000]+")
_QUOTE_RE = re.compile(r"[“”\"'‘’《》〈〉()（）\[\]【】·・,，.。、:：;；!！?？\-—－_/\\|&+]")

# 名称首部的机构/文号前缀：这些不是活动名的一部分
_ORG_PREFIX_RE = re.compile(
    r"^(?:关于|转发|印发|发布|通知|公示|"
    r"华南农业大学|华南农大|华农|"
    r"[\u4e00-\u9fff]{2,12}(?:学院|学部|系|部|处|办公室|中心|委员会|团委|党委|"
    r"学工部|研工部|教务处|图书馆|协会|学会|联盟))+"
)
# 「关于举办/开展/评选…」这类动词，剥掉机构名之后还在开头，也得去掉
_ACTION_PREFIX_RE = re.compile(
    r"^(?:关于)?(?:组织|举办|开展|举行|召开|评选|申报|推荐|征集|招募|选拔|受理|"
    r"做好|报送|上交|启动|开展|征订)+"
)
# 名称尾部的文书词
_TAIL_WORDS = (
    "的通知", "的公告", "的方案", "的实施办法", "的办法", "的细则", "的公示",
    "的说明", "的函", "通知", "公告", "公示", "方案", "办法", "细则", "名单",
    "结果", "安排", "实施方案", "（第一轮）", "(第一轮)",
)
# 活动全称之后的叙述性尾巴：「…的通知」剥掉之后，还会剩「报名工作」「评选工作」
# 这种词。只在这些词足够靠后（≥8 字，说明前面已经是一个像样的活动名）时才切，
# 并且要求切完还剩至少 6 字——否则宁可退回整条标题。
_TAIL_CUT_WORDS = ("报名工作", "申报工作", "评选工作", "推荐工作", "组织工作",
                   "报名", "启动", "结果", "名单", "安排", "时间", "地点",
                   "对象", "要求")

# 名称首部的资讯类前缀：「PDF 第十一届…」「【转载】…」
_INFO_PREFIX_RE = re.compile(
    r"^[\s\-—·|｜]*(?:[【\[（(]\s*(?:PDF|Word|Excel|PPT|附件|全文|转载|报名|提示|"
    r"文件|下载|原文|表格|汇总|收藏)\s*[】\]）)]|"
    r"(?:PDF|Word|Excel|PPT|DOCX?)\b[\s:：.、]*)+",
    re.I,
)
# 资讯/攻略类标题：这些不是「可以报名参加的活动」，要排除。
# 刻意不放「参加」：那是个中性动词，「关于组织参加第 X 届…竞赛的报名通知」
# 是正经通知，误伤它比漏掉一篇攻略文的代价大。
_GUIDE_WORDS = ("指南", "攻略", "盘点", "区别", "异同", "解析", "解读", "必看",
                "一文读懂", "怎么选", "有哪些", "汇总帖", "经验贴", "干货",
                "注意哪些", "如何准备", "备赛", "科普", "介绍", "收藏", "推荐阅读")

# 活动类型关键词：只有命中这些，(标题) 才有资格成为一张活动卡
KIND_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("竞赛", ("大赛", "竞赛", "比赛", "挑战杯", "锦标赛", "选拔赛", "联赛", "公开赛",
             "擂台赛", "奖赛", "赛事")),
    ("项目", ("大创", "创新创业训练计划", "立项", "申报项目", "科研训练", "攀登计划",
             "创新项目", "创业项目")),
    ("招募", ("招募", "招新", "征集", "征稿", "选拔", "纳新", "队员", "校队")),
    ("讲座", ("讲座", "报告会", "学术报告", "论坛", "沙龙", "工作坊", "分享会",
             "宣讲会", "培训", "研修", "研讨")),
    ("志愿服务", ("志愿", "义工", "支教", "社会实践", "三下乡", "公益")),
    ("文体", ("文体", "运动会", "球赛", "歌手", "艺术节", "文化节", "演讲", "辩论",
             "征文", "摄影", "微电影", "晚会")),
    ("奖学金", ("奖学金", "助学金", "荣誉称号", "评选", "评优", "先进")),
]

# 这些词出现说明是行政/教务流程，不是「可以参加的活动」
NEGATIVE_KEYWORDS = (
    "选课", "补考", "缓考", "成绩录入", "毕业资格", "学籍", "退学", "处分",
    "宿舍", "医保", "缴费", "注册报到", "教材", "调课", "停课", "放假",
    "值班", "考务", "监考", "考试安排", "岗位聘任", "职称", "招标",
)
# 需要额外佐证才收的弱词（如「培训」多半是教务培训）
WEAK_NEED = ("报名", "参赛", "竞赛", "大赛", "项目", "征集", "招募")
# 这些词出现在**标题**里就说明是「正在叫人报名」的通知（比正文里出现可靠得多：
# 攻略文正文里到处是「报名」「竞赛」，标题里不会写）
REGISTRATION_HINTS = ("报名", "参赛", "征集", "招募", "选拔", "申报", "征稿",
                      "纳新", "招新", "评选", "申请", "受理")


def strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "")


def normalize_name(name: str) -> str:
    """名称归一化：全角转半角、去空白标点、统一加号，用于匹配与去重。"""
    s = unicodedata.normalize("NFKC", str(name or ""))
    s = s.replace("＋", "+")
    s = _PUNCT_RE.sub("", s)
    s = _QUOTE_RE.sub("", s)
    return s.lower()


def activity_kind(text: str) -> str:
    """这条标题看起来是什么类型的活动（'' = 不像活动）。"""
    for kind, keys in KIND_KEYWORDS:
        if any(k in text for k in keys):
            return kind
    return ""


_BRACKET_PAIRS = {"「": "」", "『": "』", "“": "”", "‘": "’",
                  "《": "》", "（": "）", "(": ")", "[": "]", "【": "】"}


def _strip_bracket(text: str, window: int = 20) -> str:
    """去掉开头的一小段成对括号内容：「（第一轮）」「【转载】」。

    只认**成对**的：宁可留着「挑战杯」的引号，也不能把前半边的引号吃掉、
    留一个孤零零的 `」`（这样切出来的活动名是歪的）。
    """
    s = text.lstrip(" 　")
    if not s:
        return s
    open_ch = s[0]
    close_ch = _BRACKET_PAIRS.get(open_ch)
    if not close_ch:
        return s
    idx = s.find(close_ch, 1, window + 1)
    if idx < 0:
        return s
    # 剥掉这一对之后，紧跟其后的可能还有一个「配套被带走」的孤引号
    # （「第十五届「挑战杯」广东…」→ 剥完剩 `广东…」` 或 `挑战杯」广东…`），
    # 用不到就顺手清掉，别让它留在活动名里。
    return _drop_unpaired_brackets(s[idx + 1:].lstrip(" 　"))


_ALL_BRACKETS = set("".join(_BRACKET_PAIRS.keys()) + "".join(_BRACKET_PAIRS.values()))


def _drop_unpaired_brackets(text: str) -> str:
    """删掉**首尾**没成对的括号字符（成对的、出现在中间的都保留）。

    两种情况要分开处理：

    - `挑战杯」广东大学生创业计划竞赛校内选拔`：闭引号是「第十五届「挑战杯」
      」被剥前缀时留下的孤儿，在串首/串尾，删掉。
    - `全国大学生生命科学竞赛（创新创业类`：括号在串**尾**而且只有半边，
      这是网页标题被截断的痕迹，也删掉。

    中间的括号一律不动：`全国大学生生命科学竞赛（创新创业类）`这种完整名字
    必须原样显示。
    """
    if not text:
        return text
    for open_ch, close_ch in _BRACKET_PAIRS.items():
        if text.count(open_ch) < text.count(close_ch):
            text = text.strip(close_ch)
        elif text.count(close_ch) < text.count(open_ch):
            text = text.strip(open_ch)
    return text


def clean_activity_name(title: str) -> str:
    """从通知标题里切出一个像样的活动名。

    华农的通知标题基本是这个形状：

        关于开展 2025 年华南农业大学「某某杯」大学生程序设计竞赛的通知
        华南农业大学关于组织申报 2026 年大学生创新创业训练计划项目的通知

    依次去掉机构前缀 → 动作动词（关于举办/组织申报…）→ 文书尾巴（的通知/的公示）
    → 年份与叙述性尾巴，剩下的就是活动名；切完太短（<6 字）说明切的不是活动名，
    退回原标题——**宁可显示一条长标题，也不要把活动名切残**。
    """
    raw = strip_tags(title or "").strip()
    s = raw
    s = re.sub(r"^[\s\-—·|｜]*", "", s)
    s = _INFO_PREFIX_RE.sub("", s)
    # 首部剥前缀要**反复做**：标题常常是「关于开展第十五届「挑战杯」…」，
    # 剥掉「关于」之后才露出「开展」和「第十五届」，一轮剥不干净。
    for _ in range(4):
        before = s
        s = _strip_bracket(s)                 # （第一轮）/【转载】
        s = _ORG_PREFIX_RE.sub("", s)         # 华南农业大学 / 某某学院
        s = re.sub(r"^(?:开展|举办|举行|组织|启动|参加)(?:参加)?"
                   r"第[\u4e00-\u9fff\d]{1,4}(?:届|次|期)", "", s)
        s = _INFO_PREFIX_RE.sub("", s)
        s = _ACTION_PREFIX_RE.sub("", s)      # 关于举办 / 组织申报 …
        s = re.sub(r"^[\s\-—·|｜「『【\[]*", "", s).strip()
        if s == before:
            break
    changed = True
    while changed:
        changed = False
        for tail in sorted(_TAIL_WORDS, key=len, reverse=True):
            if s.endswith(tail) and len(s) - len(tail) >= 6:
                s = s[: -len(tail)].rstrip(" 　的")
                changed = True
    # 期次/年份：只从**开头**剥（「2026年大学生创新创业…」）
    s = re.sub(r"^[（(]?\s*(?:第[\u4e00-\u9fff\d]{1,4}届|20\d\d\s*[-–—~至]?\s*(?:20\d\d)?\s*学年)"
               r"\s*[）)]?\s*", "", s)
    s = re.sub(r"^[（(]?\s*20\d\d\s*年\s*[）)]?\s*", "", s)
    s = re.sub(r"^\s*年\s*", "", s)
    # 叙述性尾巴：切在**最后一个**候选词上
    for w in _TAIL_CUT_WORDS:
        idx = s.rfind(w)
        if idx >= 8 and len(s) - idx >= 2 and idx >= 6:
            s = s[:idx].rstrip(" 　的：:")
    s = s.strip(" 　-—·：:，,。；;、「」『』【】[]《》（） ")
    s = re.sub(r"[.．·…]+$", "", s).strip()
    # 清掉「只剩半边」的引号：「…第十五届「挑战杯」…」被剥成
    # `挑战杯」广东…` 时，开引号是连着「第十五届」一起走的，留一个孤立的
    # 闭引号在名字里很难看。这里只删**不成对**的那种，成对的引号保持原样
    # （「牧野杯」这种带引号的名字要保留）。
    s = _drop_unpaired_brackets(s)
    # 网页标题里常有多余空格（「…竞赛 （创新创业类」「科学 探究类」）。
    # 中文里字之间的空格基本是抓取噪声，去掉；英文/数字之间的空格要保留。
    s = re.sub(r"\s*([（()）【】「」《》、，。：:])\s*", r"\1", s)
    s = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", s)
    # 只剩半边的引号（首尾那种已被上面的循环清掉，漏网的在这里兜一次底）。
    # 只处理引号，不碰括号：括号可能是有意义的赛道/届次/主办标记。
    for open_ch, close_ch in _BRACKET_PAIRS.items():
        if open_ch in "（([【":
            continue
        if s.count(open_ch) != s.count(close_ch):
            s = s.replace(open_ch, "").replace(close_ch, "")
    # 网页标题末尾的省略号
    s = re.sub(r"\s*[.．·…]+\s*$", "", s)
    s = re.sub(r"^[.．·…\s]+", "", s)
    s = re.sub(r"\s{2,}", " ", s).strip(" 　-—·：:，,。；;、")
    if len(s) < 6 or len(s) > 60:
        return raw
    return s


# --------------------------------------------------------------------------- #
# 二、关键信息抽取（时间 / 附件）
# --------------------------------------------------------------------------- #
_CN_DIGITS = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
              "六": 6, "七": 7, "八": 8, "九": 9}


def _cn_number(text: str) -> int | None:
    """把「十二」「二十」「三十一」这类中文数字转成整数（不含「〇/零」）。"""
    if not text:
        return None
    if text.isdigit():
        return int(text)
    if text in _CN_DIGITS:
        return _CN_DIGITS[text]
    if "十" in text:
        head, _, tail = text.partition("十")
        if head and head not in _CN_DIGITS:
            return None
        if tail and tail not in _CN_DIGITS:
            return None
        return (10 * (_CN_DIGITS[head] if head else 1)
                + (_CN_DIGITS[tail] if tail else 0))
    return None


def _cn_year(text: str) -> int | None:
    """「二〇二五」这种年份：逐位读，〇/零 当 0。"""
    s = text.replace("〇", "0").replace("零", "0")
    digits = []
    for ch in s:
        if ch.isdigit():
            digits.append(ch)
        elif ch in _CN_DIGITS:
            digits.append(str(_CN_DIGITS[ch]))
        else:
            return None
    return int("".join(digits)) if len(digits) == 4 else None


_DATE_PATTERNS = [
    # 2025年3月14日 / 2025-03-14 / 2025.3.14
    re.compile(r"(20\d\d)\s*[-/年.]\s*(\d{1,2})\s*[-/月.]\s*(\d{1,2})\s*日?"),
    # 3月14日 / 3月14号（无年份）
    re.compile(r"(?<!\d)(\d{1,2})\s*月\s*(\d{1,2})\s*[日号]"),
    # 二〇二五年三月十四日
    re.compile(r"([二〇零一二三四五六七八九]{4})\s*年\s*"
               r"([一二三四五六七八九十]{1,3})\s*月\s*"
               r"([一二三四五六七八九十]{1,3})\s*日"),
]


def parse_cn_date(text: str, today: datetime.date | None = None) -> datetime.date | None:
    """从中文文本里取第一个日期。缺年份时按「不早于今天」推断年份。"""
    today = today or datetime.date.today()
    s = str(text or "")
    m = _DATE_PATTERNS[0].search(s)
    if m:
        try:
            return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    m = _DATE_PATTERNS[2].search(s)
    if m:
        y = _cn_year(m.group(1))
        mo, d = _cn_number(m.group(2)), _cn_number(m.group(3))
        if y and mo and d:
            try:
                return datetime.date(y, mo, d)
            except ValueError:
                return None
    m = _DATE_PATTERNS[1].search(s)
    if m:
        mo, d = int(m.group(1)), int(m.group(2))
        if not (1 <= mo <= 12 and 1 <= d <= 31):
            return None
        year = today.year
        for _ in range(2):                     # 已经过去两个月 → 当作明年的安排
            try:
                cand = datetime.date(year, mo, d)
            except ValueError:
                return None
            if (cand - today).days >= -60:
                return cand
            year += 1
    return None


def find_dates(text: str, limit: int = 8) -> list[str]:
    """抽出文本里出现的所有日期（ISO 字符串，保序去重）。"""
    out: list[str] = []
    for m in _DATE_PATTERNS[0].finditer(text or ""):
        try:
            d = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            continue
        iso = d.isoformat()
        if iso not in out:
            out.append(iso)
        if len(out) >= limit:
            return out
    return out


# 时间标签：命中即认为这一处说的是时间，取标签词**后面**第一个日期。
#
# 刻意不放「时间」「日期」这种光杆词：正文里「报名截止时间」「材料提交时间」
# 到处都是，光杆词会把已经归好的条目再抢一遍，得到一堆错位的时间。
_TIME_LABELS: list[tuple[str, tuple[str, ...]]] = [
    ("报名截止", ("报名截止", "截止报名", "报名结束", "申报截止", "提交截止",
                  "材料截止", "受理截止", "报名时间截止", "截止日期", "截止时间")),
    ("材料提交", ("提交材料", "材料提交", "报送材料", "上交材料", "提交作品",
                  "作品提交", "交材料")),
    ("报名时间", ("报名时间", "报名日期", "开始报名", "网上报名", "报名通道",
                  "报名入口", "系统开放")),
    ("比赛时间", ("比赛时间", "竞赛时间", "初赛时间", "复赛时间", "决赛时间",
                  "比赛日期", "赛事时间", "答辩时间", "评审时间", "笔试时间")),
    ("举办时间", ("举办时间", "活动时间", "赛程安排", "日程安排")),
    ("宣讲培训", ("宣讲会", "培训时间", "讲座时间", "辅导时间")),
]
_LABEL_PRIORITY = {name: i for i, (name, _) in enumerate(_TIME_LABELS)}
_DATE_IN_LINE = re.compile(
    r"(20\d\d\s*[-/年.]\s*\d{1,2}\s*[-/月.]\s*\d{1,2}\s*日?|"
    r"(?<!\d)\d{1,2}\s*月\s*\d{1,2}\s*[日号])"
)
# 「截止类」词：这些词出现在标签附近时，把这个时间标成「要卡住的日期」，
# 卡片上会高亮（前端读 is_deadline）。
DEADLINE_HINTS = ("报名截止", "截止", "deadline", "报名结束")


def extract_times(title: str, body: str, *, max_items: int = MAX_TIMES,
                  today: datetime.date | None = None) -> list[dict]:
    """从正文里抽「标签 + 日期」的时间点。

    做法很土但稳：找到标签词的位置，取它**后面 40 个字符内**的第一个日期。

    为什么按位置找而不是按行找：华农的通知正文抓下来常常整篇是一段（网页里
    本来就只有几个 `<p>`，清洗后换行所剩无几），按行扫描会一条都抽不到。按
    「标签 → 后面的日期」就与换行无关，也天然处理了「报名时间：3月1日至3月20日」
    （取标签后的第一个日期；想要截止日请以`报名截止`为标签，通知里一般会写两次）。
    """
    today = today or datetime.date.today()
    text = f"{title or ''}\n{body or ''}"
    found: dict[str, dict] = {}
    for label, keys in _TIME_LABELS:
        best: tuple[int, dict] | None = None
        for key in keys:
            for m in re.finditer(re.escape(key), text):
                tail = text[m.end(): m.end() + 40]
                dm = _DATE_IN_LINE.search(tail)
                if not dm:
                    continue
                d = parse_cn_date(dm.group(0), today)
                if d is None:
                    continue
                # 「截止」这个词在通知里到处都是（上一条的「报名截止」常常就在
                # 40 字之内），所以只有当窗口里没有别的标签词时才认它。
                ctx = text[max(0, m.start() - 30): m.end() + len(dm.group(0)) + 10]
                other_label = any(
                    k in ctx for lb, keys in _TIME_LABELS if lb != label for k in keys)
                cand = {
                    "label": label,
                    "date": d.isoformat(),
                    "text": text[m.start(): m.end() + len(dm.group(0))].strip()[:120],
                    "is_deadline": (label == "报名截止"
                                    or ("截止" in ctx and not other_label)),
                }
                if best is None or m.start() < best[0]:
                    best = (m.start(), cand)
                break                     # 同一个标签词只看第一次出现
        if best is not None:
            found[label] = best[1]
    items = sorted(found.values(),
                   key=lambda x: (_LABEL_PRIORITY.get(x["label"], 99), x["date"]))
    return items[:max_items]


def attachment_kind(url: str) -> str:
    m = FILE_EXT_RE.search(url or "")
    return m.group(1).lower() if m else ""


def _norm_url(url: str) -> str:
    """附件 URL 归一化（http/https、fragment、大小写域名），用于和库里的记录对齐。"""
    try:
        from .fetcher import normalize_url

        return normalize_url(url)
    except Exception:
        return url


def file_name(url: str) -> str:
    """从 URL 取一个能显示的文件名（已 URL 解码）。

    很多学校站点的附件名是一串 UUID（`207a49fc-4da8-…-cc248f2896ac.pdf`），
    按原样显示只会把卡片撑坏，这里把过长的 hash 风格文件名缩成 `前8位…后缀`。
    """
    import urllib.parse

    path = urllib.parse.urlsplit(url or "").path
    name = urllib.parse.unquote(path.rsplit("/", 1)[-1] or "")
    if not name:
        name = (url or "")[-40:]
    stem, dot, ext = name.rpartition(".")
    if dot and len(stem) > 28:
        hexish = sum(c.isdigit() or c.lower() in "abcdef-" for c in stem)
        if hexish >= len(stem) * 0.8:
            return f"{stem[:8]}…{dot}{ext}"
    if len(name) > 46:
        return f"{name[:20]}…{name[-20:]}"
    return name


# --------------------------------------------------------------------------- #
# 三、加分明细（复用计算器已核验的数据）
# --------------------------------------------------------------------------- #
@lru_cache(maxsize=1)
def _catalog() -> dict:
    """计算器的完整静态数据（含每个活动的档位预览）。

    刻意缓存：`calcdata/*.json` 有 150+ 活动，装载一次约几十毫秒，
    按消息调用会明显拖慢问答。数据是只读的，缓存安全。
    """
    from .calc import Calculator

    return Calculator().catalog()


def reset_cache() -> None:
    """数据文件改了（或测试里换了数据目录）之后清缓存。"""
    _catalog.cache_clear()


def _score_summary(activity: dict) -> dict:
    """把一个活动展开成「综测 / 推免最高能加多少、各档位分别多少」。"""
    preview: dict = activity.get("preview") or {}
    achieves: list[dict] = []
    best_zc = best_tm = 0.0
    for name, p in preview.items():
        per = p.get("channels") or {}
        zc = sum(v for ch, v in per.items()
                 if RUBRIC_BY_CHANNEL.get(ch) == "综测") or 0.0
        tm = sum(v for ch, v in per.items()
                 if RUBRIC_BY_CHANNEL.get(ch) == "推免") or 0.0
        other = {ch: v for ch, v in per.items()
                 if RUBRIC_BY_CHANNEL.get(ch) in ("学分", "时长") and v}
        achieves.append({
            "achieve": name,
            "zongce": round(zc, 2),
            "tuimian": round(tm, 2),
            "other": {ch: round(v, 2) for ch, v in other.items()},
        })
        best_zc = max(best_zc, zc)
        best_tm = max(best_tm, tm)
    achieves.sort(key=lambda x: (-(x["zongce"] + x["tuimian"]), x["achieve"]))
    return {"achieves": achieves[:6], "best_zongce": round(best_zc, 2),
            "best_tuimian": round(best_tm, 2)}


def _channel_names(activity: dict) -> dict:
    chans = list((activity.get("channels") or {}).keys())
    return {
        "zongce": [c for c in chans if RUBRIC_BY_CHANNEL.get(c) == "综测"],
        "tuimian": [c for c in chans if RUBRIC_BY_CHANNEL.get(c) == "推免"],
        "other": [c for c in chans if RUBRIC_BY_CHANNEL.get(c) in ("学分", "时长")],
    }


def _registry_keys(activity: dict) -> list[str]:
    ex = activity.get("extra") or {}
    keys = [activity.get("name") or "", ex.get("raw_name") or ""]
    keys += list(ex.get("aliases") or [])
    return [normalize_name(k) for k in keys if k]


# 同名赛事的不同赛道：「全国大学生生命科学竞赛」有科学探究类与创新创业类两条，
# 分值档位也不同。名称高度重合时，只有赛道关键词一致才算同一个赛事。
TRACK_KEYS = ("科学探究类", "创新创业类", "科学探究", "创新创业", "实践赛", "命题赛",
              "高职赛", "研究生组", "本科生组", "专业组", "非专业组", "创意组",
              "初创组", "成长组", "师生共创组", "公益组", "商业组")


def _tracks(text: str) -> set[str]:
    return {k for k in TRACK_KEYS if k in (text or "")}


def match_activity(name: str, *, threshold: float = 2.0) -> tuple[dict | None, float, str]:
    """把证据里的活动名匹配到已核验名录。

    返回 `(活动, 分数, 命中的键)`。匹配不上一律返回 None——
    「匹配不上」比「错配一个分值」安全得多。

    打分规则（都作用在归一化字符串上）：

    - 完全相等：3.0
    - 一方包含另一方：1.0 + 2.0 × (短串长 / 长串长)
      —— 包含关系越长越可信（「中国国际大学生创新大赛」⊂
      「关于举办中国国际大学生创新大赛校赛的通知」得分高，
      而「大学生创新创业训练计划」⊂「…创新大赛…」这种偶然片段得分低）
    - 赛事名出现在**标题开头**再加 0.5：通知标题几乎都以赛事全称开头
      （「关于举办<赛事全称>…」），而中间才出现的大多是别的东西的修饰语。
      这一条专门挡住「大学生创新创业训练计划」被「…创新大赛（含大创）…」
      这种长标题捞进去的情况。
    - 赛道加分/扣分：见 `TRACK_KEYS`
    """
    key = normalize_name(clean_activity_name(name) or name)
    if len(key) < 4:
        return None, 0.0, ""
    want_tracks = _tracks(name)
    best: tuple[dict | None, float, str] = (None, 0.0, "")
    for activity in _catalog().get("activities", []):
        for rk in _registry_keys(activity):
            if len(rk) < 4:
                continue
            if rk == key:
                return activity, 3.0, rk
            if rk in key or key in rk:
                score = 1.0 + 2.0 * (min(len(rk), len(key)) / max(len(rk), len(key)))
                if key.startswith(rk) or rk.startswith(key):
                    score += 0.5
                have_tracks = _tracks(activity.get("name") or "")
                if want_tracks or have_tracks:
                    if want_tracks & have_tracks:
                        score += 1.0
                    else:
                        score -= 0.5
                if score > best[1]:
                    best = (activity, score, rk)
    if best[1] >= threshold:
        return best
    return None, best[1], best[2]


def build_activity_card(name: str, *, kind: str = "", source: dict | None = None,
                        times: Sequence[dict] | None = None,
                        note: str = "") -> dict:
    """把「一个活动名」变成一张卡片（能匹配上名录的带分值）。"""
    source = dict(source or {})
    display = clean_activity_name(name) or strip_tags(name).strip()
    activity, score, hit = match_activity(display)
    timing_bits = [t["text"] for t in (times or []) if t.get("is_deadline")]
    if activity is None:
        return {
            "kind": KIND_ACTIVITY,
            "id": "",
            "name": display,
            "category": kind or "活动",
            "level": "",
            "organizer": "",
            "timing": "；".join(timing_bits[:1]),
            "times": list(times or []),
            "in_registry": False,
            "match_score": round(score, 2),
            "confidence": "unverified",
            "basket_ready": False,
            "registry_note": ("未在《学生竞赛奖励办法》名录与通用加分明细里匹配到同名条目，"
                              "暂不计入活动篮；如确属名录内赛事，可在计算器「③ 活动篮」里按名检索。"),
            "source": source,
            "note": note,
        }
    cats = _channel_names(activity)
    scores = _score_summary(activity)
    ex = activity.get("extra") or {}
    return {
        "kind": KIND_ACTIVITY,
        "id": activity.get("id") or "",
        "name": display,
        "registry_name": activity.get("name") or "",
        "category": activity.get("category") or (kind or "活动"),
        "level": activity.get("level") or "",
        "organizer": activity.get("organizer") or "",
        "timing": activity.get("timing") or "",
        "times": list(times or []),
        "eligibility": activity.get("eligibility") or "",
        "in_registry": True,
        "match_score": round(score, 2),
        "matched_key": hit,
        "list_kind": activity.get("list_kind") or "general",
        "channels": cats,
        "scores": scores,
        "discount": activity.get("discount") or "",
        "confidence": activity.get("confidence") or "",
        "source_text": activity.get("source") or "",
        "url": activity.get("url") or "",
        "tags": list(activity.get("tags") or []),
        "extra": {"seq": ex.get("seq"), "appendix": ex.get("appendix"),
                  "tier": ex.get("tier"), "tier_label": ex.get("tier_label"),
                  "profile_label": ex.get("profile_label"),
                  "appendix_title": ex.get("appendix_title"),
                  "online": bool(ex.get("online"))},
        "basket_ready": bool(activity.get("channels")),
        "registry_note": "",
        "source": source,
        "note": note,
    }


# --------------------------------------------------------------------------- #
# 四、主装配
# --------------------------------------------------------------------------- #
@dataclass
class CardSet:
    """一次问答产生的全部卡片。"""

    activities: list[dict] = field(default_factory=list)
    files: list[dict] = field(default_factory=list)
    times: list[dict] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {"activities": self.activities, "files": self.files,
                "times": self.times, "stats": self.stats}

    def __bool__(self) -> bool:
        return bool(self.activities or self.files or self.times)


def _title_candidates(title: str) -> list[str]:
    """一条标题可能切出的活动名候选（整条 + 切过的）。"""
    out = []
    cleaned = clean_activity_name(title)
    for cand in (cleaned, strip_tags(title or "").strip()):
        if cand and cand not in out:
            out.append(cand)
    return out


def _score_candidate(ev, name: str, has_files: bool) -> float:
    score = 0.0
    if ev.source == "site":
        score += 1.0
    if any(k in name for k in ("大赛", "竞赛", "挑战杯", "比赛", "项目", "招募",
                               "征集", "评选", "奖学金")):
        score += 0.8
    if hasattr(ev, "age_days") and ev.age_days is not None:
        if ev.age_days <= 400:
            score += 0.7
        elif ev.age_days <= 730:
            score += 0.3
    if has_files:
        score += 0.4
    if any(k in name for k in ("讲座", "报告会", "沙龙", "培训")):
        score -= 0.2
    # 资讯/攻略类：模型与用户都不需要把它当「可报名的活动」看
    if any(k in name for k in _GUIDE_WORDS) or "?" in name or "？" in name:
        score -= 1.2
    return score


def _is_guide(title: str) -> bool:
    return (any(w in title for w in _GUIDE_WORDS)
            or "?" in title or "？" in title)


def _file_cards(evidence: Sequence[Any], store=None) -> tuple[list[dict], dict[int, bool]]:
    """从证据里收集附件，返回 (卡片, {证据序号: 是否带附件})。

    如果这份附件已经被下载解析过（`attachment` 表里有记录），卡片会带上
    「已解析出多少字 / 几张图 / 用了哪种解析器」，前端据此给出「看解析正文」，
    用户不用下载 PDF 就能确认「报名截止是不是写在附件里」。
    """
    cards: list[dict] = []
    by_n: dict[int, bool] = {}
    seen: set[str] = set()
    parsed: dict[str, dict] = {}
    if store is not None:
        ids = [int(getattr(ev, "article_id", 0) or 0) for ev in evidence]
        ids = [i for i in ids if i]
        if ids:
            try:
                grouped = store.attachments_for_articles(ids)
                for rows in grouped.values():
                    for r in rows:
                        if r.get("url"):
                            # 入库时是 http、卡片里的链接可能是 https（或反过来），
                            # 统一规范化后再查，否则同一份附件会对不上号。
                            parsed[_norm_url(str(r["url"]))] = r
            except Exception:
                parsed = {}
    for ev in evidence:
        urls: list[str] = []
        # ① 入库时抽好的附件（校内文章）
        if store is not None and getattr(ev, "article_id", 0):
            art = store.get_article(int(ev.article_id), max_chars=1) or {}
            vals = art.get("attachments")
            if isinstance(vals, str):
                try:
                    import json

                    vals = json.loads(vals or "[]")
                except Exception:
                    vals = []
            urls += [str(u) for u in (vals or []) if u]
        # ② 证据正文里出现的文件链接（公网页面里常见）
        text = f"{getattr(ev, 'snippet', '') or ''}\n{getattr(ev, 'body', '') or ''}"
        for m in re.finditer(r"https?://[^\s\"'<>）)】]+", text):
            u = m.group(0)
            if attachment_kind(u):
                urls.append(u)
        # ③ 证据 URL 本身就是文件
        if attachment_kind(getattr(ev, "url", "") or ""):
            urls.append(ev.url)
        has = False
        for u in urls:
            if u in seen:
                has = True
                continue
            seen.add(u)
            has = True
            ext = attachment_kind(u)
            row = parsed.get(_norm_url(u)) or {}
            card = {
                "kind": KIND_FILE,
                "url": u,
                "file_name": file_name(u),
                "file_kind": FILE_KINDS.get(ext, ext.upper() or "文件"),
                "ext": ext,
                "title": getattr(ev, "title", "") or "",
                "source": {
                    "n": getattr(ev, "n", 0),
                    "title": getattr(ev, "title", "") or "",
                    "url": getattr(ev, "url", "") or "",
                    "pub_date": getattr(ev, "pub_date", "") or "",
                    "source": getattr(ev, "source", "") or "",
                    "college": getattr(ev, "college", "") or "",
                },
            }
            if row:
                body = row.get("text") or ""
                card.update({
                    "attachment_id": int(row.get("id") or 0),
                    "parsed": bool(body.strip()),
                    "parsed_chars": len(body),
                    "parser": row.get("parser") or "",
                    "stored": row.get("stored") or "",
                    "local_bytes": int(row.get("bytes") or 0),
                    "tables": int(row.get("tables") or 0),
                    "images": int(row.get("images") or 0),
                    "ocr_used": int(row.get("ocr_used") or 0),
                    "parse_note": row.get("note") or "",
                    "parse_error": row.get("error") or "",
                    "preview": (body.strip()[:220] + "…") if len(body.strip()) > 220 else body.strip(),
                })
            cards.append(card)
        by_n[int(getattr(ev, "n", 0) or 0)] = has
    return cards, by_n


def _activity_cards(evidence: Sequence[Any], store=None
                    ) -> tuple[list[dict], list[dict], dict[int, bool]]:
    """扫证据标题 → 活动卡片 + 时间卡片。"""
    files, files_by_n = _file_cards(evidence, store)
    raw: list[tuple[float, dict, list[dict]]] = []
    for ev in evidence:
        title = strip_tags(getattr(ev, "title", "") or "").strip()
        if not title:
            continue
        body = getattr(ev, "snippet", "") or ""
        if getattr(ev, "article_id", 0) and store is not None:
            art = store.get_article(int(ev.article_id), max_chars=4000) or {}
            body = (art.get("body") or "")[:4000] or body
        hay = title + "\n" + body
        if _is_guide(title):                 # 攻略/盘点/问答类：不是可报名的活动
            continue
        kind = activity_kind(title)
        if not kind:
            # 标题里没有活动类词，但通知确实在「叫人报名」时才收
            # （这条限制能把「参加竞赛要注意什么」这类文章挡在外面：
            #   它们的标题里到处是「竞赛」，但标题里不会出现「报名」）
            if not any(k in title for k in REGISTRATION_HINTS):
                continue
            kind = activity_kind(hay)
            if not kind:
                continue
        if any(k in title for k in NEGATIVE_KEYWORDS):
            continue
        if kind in ("讲座", "志愿服务") and not any(k in hay for k in WEAK_NEED):
            # 「培训」「志愿服务」这类词太泛，正文里也得有报名/招募佐证
            continue
        name = clean_activity_name(title)
        key = normalize_name(name)
        if len(key) < 5:
            continue
        # 同一活动常被两篇通知写到（原通知 + 补充/延期通知），标题措辞不同。
        # 所以去重键优先用「匹配到的名录条目 id」——它把「中国国际大学生创新大赛
        # 校赛」与「…校赛的补充通知」认成同一个活动；匹配不上时才退回名称归一化。
        probe, _, _ = match_activity(name)
        dedupe_key = f"id:{(probe or {}).get('id')}" if probe else f"name:{key}"
        times = extract_times(title, body)
        score = _score_candidate(ev, name, files_by_n.get(int(getattr(ev, "n", 0) or 0), False))
        card = build_activity_card(
            name, kind=kind,
            source={"n": getattr(ev, "n", 0), "title": title,
                    "url": getattr(ev, "url", "") or "",
                    "pub_date": getattr(ev, "pub_date", "") or "",
                    "source": getattr(ev, "source", "") or "",
                    "college": getattr(ev, "college", "") or "",
                    "site_name": getattr(ev, "site_name", "") or ""},
            times=times,
        )
        dup = next((i for i, (_, c, _) in enumerate(raw)
                    if c["_key"] == dedupe_key), None)
        card["_key"] = dedupe_key
        card["_score"] = round(score, 2)
        if dup is None:
            raw.append((score, card, times))
        elif score > raw[dup][0]:
            raw[dup] = (score, card, times)

    raw.sort(key=lambda t: (-t[0], t[1]["name"]))
    activities: list[dict] = []
    times: list[dict] = []
    seen_time: set[tuple[str, str]] = set()
    for _, card, tlist in raw[:MAX_ACTIVITIES]:
        for t in tlist:
            k = (t["label"], t["date"])
            if k in seen_time:
                continue
            seen_time.add(k)
            times.append({**t, "activity": card["name"],
                          "source_n": card["source"].get("n", 0),
                          "source_title": card["source"].get("title", ""),
                          "source_url": card["source"].get("url", "")})
        card.pop("_key", None)
        activities.append(card)

    # 校内文章没有附件链接、但正文提到「附件」时，给出提示卡
    for ev in evidence:
        if files_by_n.get(int(getattr(ev, "n", 0) or 0)):
            continue
        blob = f"{getattr(ev, 'title', '')}{getattr(ev, 'snippet', '') or ''}"
        if re.search(r"附件\s*[：:1-9]|见附件|详见附件", blob):
            files.append({
                "kind": KIND_FILE,
                "url": getattr(ev, "url", "") or "",
                "file_name": "（正文提到的附件，链接未在页面里出现）",
                "file_kind": "附件",
                "ext": "",
                "title": getattr(ev, "title", "") or "",
                "note": "通知正文提到附件，但抓到的页面里没有可直接下载的链接。"
                        "请打开原文查看附件。",
                "source": {
                    "n": getattr(ev, "n", 0),
                    "title": getattr(ev, "title", "") or "",
                    "url": getattr(ev, "url", "") or "",
                    "pub_date": getattr(ev, "pub_date", "") or "",
                    "source": getattr(ev, "source", "") or "",
                    "college": getattr(ev, "college", "") or "",
                },
            })
    # 附件按「有日期的、校内的」优先，去重后截断
    def fkey(c: dict) -> tuple:
        src = c.get("source") or {}
        return (0 if src.get("source") == "site" else 1,
                0 if src.get("pub_date") else 1,
                -int(src.get("n") or 0))
    files.sort(key=fkey)
    return activities, files[:MAX_FILES], times[:MAX_TIMES]


def build_cards(evidence: Iterable[Any], *, store=None,
                max_total: int = MAX_TOTAL) -> CardSet:
    """入口：证据 → 卡片集合。

    `evidence` 是 `harness.agent.Evidence` 序列（鸭子类型：只要有
    title/url/pub_date/snippet/source/n/article_id 即可，方便测试直接塞假对象）。
    """
    evs = list(evidence or [])
    activities, files, times = _activity_cards(evs, store)
    cards = activities + files
    if len(cards) > max_total:
        cards = cards[:max_total]
        keep = {id(c) for c in cards}
        activities = [c for c in activities if id(c) in keep]
        files = [c for c in files if id(c) in keep]
    stats = {
        "evidence": len(evs),
        "activities": len(activities),
        "files": len(files),
        "times": len(times),
        "matched": sum(1 for c in activities if c.get("in_registry")),
    }
    return CardSet(activities=activities, files=files, times=times, stats=stats)


def as_jobs(cards: CardSet) -> list[dict]:
    """给 SSE/JSON 用的扁平列表（前端按 kind 分组渲染）。"""
    return list(cards.activities) + list(cards.files)
