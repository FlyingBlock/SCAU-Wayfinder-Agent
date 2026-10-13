"""解析层：Webplus 列表页 / 正文页 → 结构化条目（指南 §5.2、§6）。

三条站点规律（决定解析策略）：
  列表页：  /栏目别名/list.htm          分页 list2.htm … listN.htm
  正文页：  /年/月日/c栏目号a文章号/page.htm
  去重键：  a{文章号}（主站聚合页会把同一文章挂到多个栏目号下）

解析绝不猜页数：从列表页里的「尾页」链接读最大 N。
"""
from __future__ import annotations

import datetime
import html as htmlmod
import re
import urllib.parse
from dataclasses import dataclass, field

try:  # lxml 在本机自带；没有也能靠正则兜底
    from lxml import html as lxml_html  # type: ignore

    HAVE_LXML = True
except Exception:  # pragma: no cover
    HAVE_LXML = False

ARTICLE_ID_RE = re.compile(r"/c\d+a(\d+)/")
CONTENT_URL_RE = re.compile(
    r"(?:/\d{4}/\d{4}/c\d+a\d+/|/c\d+a\d+/|/info/\d+/\d+\.(?:htm|psp)$"
    r"|/(?:detail|content|article|show)[^/]*\.(?:htm|psp)$)",
    re.I,
)
LIST_NUM_RE = re.compile(r"list(\d+)\.(?:htm|psp)")
ANCHOR_RE = re.compile(r"<a\b([^>]*)>(.*?)</a>", re.I | re.S)
HREF_RE = re.compile(r"href\s*=\s*[\"']?([^\"'>\s]+)", re.I)
TITLE_ATTR_RE = re.compile(r"title\s*=\s*[\"']([^\"']{4,200})[\"']", re.I)
DATE_NEAR_RE = re.compile(r"\d{4}\s*[-/年\.]\s*\d{1,2}\s*[-/月\.]\s*\d{1,2}")
TAG_RE = re.compile(r"<[^>]+>")
SCRIPT_RE = re.compile(r"<(script|style|noscript)\b.*?</\1>", re.I | re.S)

DATE_PATTERNS = [
    re.compile(r"(\d{4})\s*[-/年\.]\s*(\d{1,2})\s*[-/月\.]\s*(\d{1,2})"),
    re.compile(r"(\d{4})\s*[-/年\.]\s*(\d{1,2})\s*月?"),
]
DATETIME_CJK = re.compile(r"(\d{4})年(\d{1,2})月(\d{1,2})日\s*(\d{1,2})?:?(\d{2})?")

# 正文容器候选（Webplus 各模板）
CONTENT_XPATHS = [
    "//div[contains(@class,'v_news_content')]",
    "//div[contains(@class,'content')]",
    "//div[contains(@class,'article')]",
    "//div[@id='content']",
    "//div[contains(@class,'wp_articlecontent')]",
    "//div[contains(@class,'news_content')]",
    "//form[contains(@name,'_newscontent_fromname')]",
]
TITLE_XPATHS = [
    "//h1",
    "//div[contains(@class,'title')]",
    "//td[contains(@class,'title')]",
    "//h2",
]
# <title> 兜底时用来切掉站点名的分隔符（注意：不要贪婪切分，
# 有些模板的 <title> 就是干净的文章标题，切了反而变成栏目名）
TITLE_SPLIT_RE = re.compile(r"\s*[-–—|·]\s*")
_TITLE_HINTS = ("关于", "通知", "公告", "公示", "名单", "结果", "办法", "细则", "方案",
                "申报", "评审", "举办", "开展", "工作", "评选", "要求", "安排", "大赛",
                "竞赛", "项目", "计划", "章程", "规定", "意见", "报告")
_SITE_WORDS = ("华南农业大学", "scau", "学院", "大学")
NOISE_PATTERNS = [
    re.compile(r"^\s*(上一条|下一条|上一篇|下一篇)[:：]?\s*$"),
    re.compile(r"^\s*(分享到|分享：|浏览次数|点击次数|访问量|字体[:：]?\s*大\s*中\s*小)\s*[:：]?\s*$"),
    re.compile(r"^\s*版权所有.*$"),
    re.compile(r"^\s*(返回顶部|关闭窗口|打印本页)\s*$"),
]

# 纯导航/栏目名，被当成文章标题时一律丢弃。
# 实测来源：某些模板的正文链接里只有图片，标题兜底逻辑会把相邻的导航文字
# 抓成标题，于是库里出现「发展动态」「联系我们」这种条目（不是文章）。
NAV_TITLES = {
    "发展动态", "联系我们", "首页", "更多", "更多>>", "学院新闻", "通知公告", "新闻中心",
    "学院概况", "师资队伍", "科学研究", "人才培养", "党建工作", "学生工作", "招生就业",
    "学术动态", "讲座报告", "学院动态", "媒体报道", "资料下载", "信息公开", "友情链接",
    "学校主页", "组织机构", "学科建设", "科研平台", "实验中心", "校友之窗", "下载专区",
    "党建动态", "团学工作", "就业信息", "本科生教育", "研究生教育", "继续教育",
    "关于我们", "部门简介", "岗位职责", "政策法规", "服务指南", "表格下载", "在线留言",
}
NAV_TITLE_RE = re.compile(r"^[\s>»\-—•·|]+|[\s>»\-—•·|]+$")


def is_nav_title(title: str) -> bool:
    t = NAV_TITLE_RE.sub("", title or "").strip()
    if not t:
        return True
    if t in NAV_TITLES:
        return True
    # 「更多>>」「发展动态 更多」这类拼接
    for nav in NAV_TITLES:
        if t == nav or (len(t) <= len(nav) + 6 and nav in t):
            stripped = t.replace(nav, "").strip(" >»-—•·|")
            if not stripped:
                return True
    return False

# 值得送去 LLM 做结构化抽取的关键词（指南 §10.6 成本控制：先免费预筛）
KEYWORD_HINTS = (
    "竞赛", "大赛", "比赛", "赛区", "选拔", "报名", "申报", "立项", "结题",
    "推免", "保研", "免试", "研究生", "招生", "复试", "调剂",
    "奖学金", "评审", "公示", "名单", "评选", "学分", "成绩",
    "创新", "创业", "大创", "挑战杯", "国创", "项目", "训练计划",
    "讲座", "报告", "论坛", "学术", "交流", "留学", "交换", "国际",
    "招聘", "就业", "实习", "宣讲", "双选", "岗位", "毕业生",
    "培养方案", "转专业", "辅修", "学位", "毕业",
)


# --------------------------------------------------------------------------- #
# 正文清洗
# --------------------------------------------------------------------------- #
def strip_tags(fragment: str) -> str:
    fragment = SCRIPT_RE.sub(" ", fragment)
    fragment = re.sub(r"<br\s*/?>", "\n", fragment, flags=re.I)
    fragment = re.sub(r"</(p|div|li|tr|h[1-6]|table|section)\s*>", "\n", fragment, flags=re.I)
    fragment = TAG_RE.sub("", fragment)
    fragment = htmlmod.unescape(fragment)
    lines = []
    for ln in fragment.replace("\xa0", " ").replace("\u3000", " ").splitlines():
        ln = re.sub(r"[ \t]+", " ", ln).strip()
        if not ln:
            continue
        if any(p.match(ln) for p in NOISE_PATTERNS):
            continue
        lines.append(ln)
    # 折叠连续空行
    out, prev_blank = [], False
    for ln in lines:
        blank = not ln
        if blank and prev_blank:
            continue
        out.append(ln)
        prev_blank = blank
    return "\n".join(out).strip()


def html_to_text(raw: str) -> str:
    """正文 HTML → 纯文本，优先 lxml，失败退回正则。"""
    if HAVE_LXML:
        try:
            doc = lxml_html.fromstring(raw)
            for bad in doc.xpath("//script|//style|//noscript"):
                bad.getparent().remove(bad)
            for bad in doc.xpath("//nav|//footer|//header"):
                bad.getparent().remove(bad)
            text = doc.text_content()
            text = htmlmod.unescape(text)
            lines = []
            for ln in text.replace("\xa0", " ").splitlines():
                s = re.sub(r"[ \t]+", " ", ln).strip()
                if s and not any(p.match(s) for p in NOISE_PATTERNS):
                    lines.append(s)
            return "\n".join(lines).strip()
        except Exception:
            pass
    return strip_tags(raw)


# --------------------------------------------------------------------------- #
# 日期
# --------------------------------------------------------------------------- #
def parse_cn_date(text: str | None) -> datetime.date | None:
    if not text:
        return None
    t = text.strip().replace("　", " ")
    for rx, has_day in ((DATE_PATTERNS[0], True), (DATE_PATTERNS[1], False)):
        m = rx.search(t)
        if m:
            y, mo = int(m.group(1)), int(m.group(2))
            d = int(m.group(3)) if has_day and m.lastindex and m.lastindex >= 3 else 1
            try:
                return datetime.date(y, mo, d)
            except ValueError:
                continue
    return None


def date_from_url(url: str) -> datetime.date | None:
    """正文页 URL 自带日期：/2026/1013/c19097a448632/page.htm → 2026-10-13。"""
    m = re.search(r"/(\d{4})/(\d{2})(\d{2})/", url)
    if m:
        try:
            return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None


# --------------------------------------------------------------------------- #
# 列表页
# --------------------------------------------------------------------------- #
@dataclass
class ListItem:
    title: str
    url: str
    date_text: str = ""
    pub_date: datetime.date | None = None
    summary: str = ""

    @property
    def dedupe_key(self) -> str:
        return dedupe_key(self.url)


@dataclass
class ParsedList:
    items: list[ListItem] = field(default_factory=list)
    max_page: int = 1
    list_pattern: str = ""        # listN.htm 还是 listN.psp
    base_dir: str = ""


def dedupe_key(url: str) -> str:
    """a{文章号} 优先，否则退回规范化 URL。"""
    m = ARTICLE_ID_RE.search(url)
    if m:
        return "a" + m.group(1)
    return urllib.parse.urlsplit(url).path.rstrip("/") or url


def parse_list(html: str, page_url: str) -> ParsedList:
    out = ParsedList()
    # 基目录：…/tzgg/list.htm → …/tzgg/
    if re.search(r"list\d*\.(?:htm|psp)$", page_url):
        out.base_dir = page_url[: page_url.rfind("/") + 1]
        m = re.search(r"(list\d*\.(?:htm|psp))$", page_url)
        out.list_pattern = m.group(1) if m else "list.htm"
    else:
        out.base_dir = page_url if page_url.endswith("/") else page_url + "/"
        out.list_pattern = "list.htm"

    # 最大页码（从「尾页」等链接读出，不猜）
    nums = [int(n) for n in LIST_NUM_RE.findall(html)]
    out.max_page = max(nums) if nums else 1

    seen: set[str] = set()
    for m in ANCHOR_RE.finditer(html):
        attrs, inner = m.group(1), m.group(2)
        hm = HREF_RE.search(attrs)
        if not hm:
            continue
        href = htmlmod.unescape(hm.group(1).strip())
        if not href or href.startswith(("javascript:", "mailto:", "#", "tel:")):
            continue
        full = urllib.parse.urljoin(page_url, href)
        full = urllib.parse.urlsplit(full)._replace(fragment="").geturl()
        if not urllib.parse.urlsplit(full).path.endswith((".htm", ".psp", ".html")):
            continue
        if CONTENT_URL_RE.search(urllib.parse.urlsplit(full).path) is None:
            continue                       # 丢掉导航 / 栏目链接，只留正文页
        key = dedupe_key(full)
        if key in seen:
            continue

        # 标题优先序：title 属性 → 锚点内的标题元素(h3/h4/.title) → 锚文本 → 紧邻文本。
        # 不要用“锚点后 220 字符”当兜底：那会把同级的日期/摘要/下一篇标题一起吞进来。
        # 也不能直接取锚文本：有些模板把 <h3>标题</h3><p>摘要</p> 一起包在 <a> 里。
        title = ""
        tm = TITLE_ATTR_RE.search(attrs)
        if tm:
            title = htmlmod.unescape(tm.group(1)).strip()
        if len(title) < 4:
            hm2 = re.search(r"<(h[1-4]|strong)\b[^>]*>(.*?)</\1>", inner, re.I | re.S)
            if hm2:
                title = re.sub(r"\s+", " ", strip_tags(hm2.group(2))).strip()
        if len(title) < 4:
            title = re.sub(r"\s+", " ", strip_tags(inner)).strip()
        if len(title) < 4:
            nxt = html[m.end(): m.end() + 160]
            cut = re.search(r"<a\b|<li\b|<tr\b|</ul|<div\b", nxt, re.I)
            if cut:
                nxt = nxt[: cut.start()]
            title = re.sub(r"\s+", " ", strip_tags(nxt)).strip()
            title = DATE_NEAR_RE.sub(" ", title)          # 兜底文本里常混入日期
        title = re.sub(r"\s+", " ", title).strip()
        title = re.sub(r"^\d{4}\s*[-/年\.]\s*\d{1,2}\s*[-/月\.]\s*\d{1,2}\s*", "", title).strip()
        if len(title) > 120:
            title = title[:120].rstrip() + "…"
        if len(title) < 4 or is_nav_title(title):
            continue
        seen.add(key)

        # 日期：锚点后的兄弟节点（news_meta / date）→ 前文
        tail = html[m.end(): m.end() + 240]
        head = html[max(0, m.start() - 160): m.start()]
        date_text = ""
        for blob in (tail, head):
            dm = DATE_NEAR_RE.search(blob)
            if dm:
                date_text = dm.group(0)
                break
        out.items.append(
            ListItem(
                title=title,
                url=full,
                date_text=date_text,
                pub_date=parse_cn_date(date_text) or date_from_url(full),
            )
        )
    return out


def page_urls(list_url: str, max_page: int) -> list[str]:
    """list.htm → list2.htm … listN.htm（保持原扩展名）。"""
    base_dir = list_url[: list_url.rfind("/") + 1]
    ext = "psp" if list_url.endswith(".psp") else "htm"
    urls = [list_url]
    for i in range(2, max_page + 1):
        urls.append(f"{base_dir}list{i}.{ext}")
    return urls


# --------------------------------------------------------------------------- #
# 正文页
# --------------------------------------------------------------------------- #
@dataclass
class ParsedArticle:
    title: str = ""
    body: str = ""
    pub_date: datetime.date | None = None
    author: str = ""
    attachments: list[str] = field(default_factory=list)
    is_noise: bool = False


def parse_article(html: str, url: str) -> ParsedArticle:
    art = ParsedArticle()
    if not html:
        art.is_noise = True
        return art

    title = ""
    body_html = ""

    # ① 先用 <title>：它几乎总是文章标题，而 XPath 容易先命中侧边栏/导航里的
    #    栏目名（实测 cxcyxy 的文章被读成「发展动态」）。
    m = re.search(r"<title>(.*?)</title>", html, re.I | re.S)
    if m:
        raw = strip_tags(m.group(1))
        parts = [p.strip() for p in TITLE_SPLIT_RE.split(raw) if p.strip()]
        if len(parts) <= 1:
            candidate = raw.strip()
        else:
            # 选最像文章标题的那一段：长度合适 + 命中「关于/通知/公示」等词
            def score(p: str) -> float:
                s = 0.0
                if 8 <= len(p) <= 60:
                    s += 2.0
                elif len(p) > 60:
                    s += 1.0
                if any(h in p for h in _TITLE_HINTS):
                    s += 1.5
                if any(w in p for w in _SITE_WORDS) and len(p) < 12:
                    s -= 1.0                      # 纯站点名
                return s
            best = max(parts, key=score)
            candidate = best if score(best) > 0 else raw.strip()
        candidate = re.sub(r"\s+", " ", candidate).strip()
        if 4 <= len(candidate) <= 200 and not is_nav_title(candidate):
            title = candidate

    # ② <title> 不可用时再退回 DOM
    if not title and HAVE_LXML:
        try:
            doc = lxml_html.fromstring(html)
            for xp in TITLE_XPATHS:
                for nd in doc.xpath(xp):
                    t = re.sub(r"\s+", " ", (nd.text_content() or "")).strip()
                    if 4 <= len(t) <= 200 and "上一条" not in t and not is_nav_title(t):
                        title = t
                        break
                if title:
                    break
            for xp in CONTENT_XPATHS:
                nodes = doc.xpath(xp)
                if nodes:
                    best = max(nodes, key=lambda n: len(n.text_content() or ""))
                    if len((best.text_content() or "").strip()) > 60:
                        body_html = lxml_html.tostring(best, encoding="unicode")
                        break
        except Exception:
            pass

    art.title = re.sub(r"\s+", " ", title).strip()

    body = html_to_text(body_html) if body_html else html_to_text(html)
    # 抠掉正文开头重复的标题行
    if art.title and body.startswith(art.title):
        body = body[len(art.title):].lstrip()
    art.body = body

    # 发布时间：优先正文里的“发布时间：/发布日期：”
    meta_blob = ""
    m = re.search(
        r"(?:发布(?:时间|日期)|发表时间|更新时间|时间)\s*[:：]?\s*(\d{4}\s*[-/年\.]\s*\d{1,2}\s*[-/月\.]\s*\d{1,2}(?:\s*\d{1,2}:\d{2})?)",
        html,
    )
    if m:
        meta_blob = m.group(1)
    art.pub_date = parse_cn_date(meta_blob) or date_from_url(url)

    m = re.search(r"(?:作者|来源|撰稿|供稿)\s*[:：]\s*([^\s<>\n]{2,20})", html)
    if m:
        art.author = strip_tags(m.group(1)).strip()

    # 附件（竞赛通知的关键信息常在附件里，指南 §6.3-17）
    for m in ANCHOR_RE.finditer(html):
        hm = HREF_RE.search(m.group(1))
        if not hm:
            continue
        href = htmlmod.unescape(hm.group(1).strip())
        if re.search(r"\.(pdf|docx?|xlsx?|pptx?|zip|rar)(\?|$)", href, re.I):
            full = urllib.parse.urljoin(url, href)
            if full not in art.attachments:
                art.attachments.append(full)

    if len(art.body) < 40:
        art.is_noise = True
    return art


def summarize_keywords(text: str, limit: int = 30) -> bool:
    """是否含值得做 LLM 抽取的关键词（免费预筛，省 token）。"""
    if not text:
        return False
    hits = sum(1 for k in KEYWORD_HINTS if k in text)
    return hits >= 1
