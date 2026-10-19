"""按「问题意图」裁剪的栏目清单（指南 §4.4）。

种子文件是「全站白名单」（349 条），但一次抓 282 个栏目既慢又混入大量噪声。
这里给出人工挑选的高信号栏目集，用于第一轮跑通全链路：

  narrow —— 直接回答「生物专业能参加什么竞赛 / 走什么发展路线」的最小集
  p1     —— narrow + 其余 P1 分组里的通知公告类栏目
  p2     —— 再加科研/国际交流
  all    —— 种子全量（可能 349 条）

`curated()` 的返回顺序即抓取优先级：列表越靠前越先抓。
"""
from __future__ import annotations

from .seed import Group, Site, collect_sites

# --------------------------------------------------------------------------- #
# narrow：约 40 个栏目 —— 每条都直接对应一类「发展路线」的证据源
# --------------------------------------------------------------------------- #
NARROW_URLS: list[str] = [
    # ── 生命科学学院（生物专业的本院，最核心） ──────────────────────────────
    "https://life.scau.edu.cn/tzgg/list.htm",          # 通知公告 645 条/47 页
    "https://life.scau.edu.cn/xydt/list.htm",          # 学院动态
    "https://life.scau.edu.cn/jzbg/list.htm",          # 讲座报告
    "https://life.scau.edu.cn/xsdt/list.htm",          # 学术动态
    "https://life.scau.edu.cn/bksgz/list.htm",         # 本科生工作
    "https://life.scau.edu.cn/yjsgz/list.htm",         # 研究生工作
    "https://life.scau.edu.cn/10117/list.htm",         # 招生就业·就业情况
    "https://life.scau.edu.cn/yjszs/list.htm",         # 招生就业·研究生招生
    "https://life.scau.edu.cn/bkzs/list.htm",          # 招生就业·本科招生
    # 生物化学实验技能大赛（本院招牌赛事：现届 + 历届存档 = 时间线与获奖实例）
    "https://life.scau.edu.cn/deswjw2026n/list.htm",
    "https://life.scau.edu.cn/dessjw2025n/list.htm",
    "https://life.scau.edu.cn/dessjw2024n/list.htm",
    "https://life.scau.edu.cn/desejw2023n/list.htm",
    "https://life.scau.edu.cn/desyjw2022n/list.htm",
    "https://life.scau.edu.cn/desjw2021n/list.htm",
    "https://life.scau.edu.cn/dsjjw2020n/list.htm",
    "https://life.scau.edu.cn/dsbjw2019n/list.htm",
    "https://life.scau.edu.cn/dsqjw2018n/list.htm",
    "https://life.scau.edu.cn/wjds/list.htm",          # 往届大赛

    # ── 创新创业学院（大创 / 挑战杯 / 国创） ────────────────────────────────
    "https://cxcyxy.scau.edu.cn/4449/list.htm",        # 通知公告
    "https://cxcyxy.scau.edu.cn/4439/list.htm",        # 双创赛事
    "https://cxcyxy.scau.edu.cn/4457/list.htm",        # 国创大赛
    "https://cxcyxy.scau.edu.cn/4458/list.htm",        # 挑战杯
    "https://cxcyxy.scau.edu.cn/18824/list.htm",       # 大创项目
    "https://cxcyxy.scau.edu.cn/4438/list.htm",        # 双创项目
    "https://cxcyxy.scau.edu.cn/sccg/list.htm",        # 双创成果
    "https://cxcyxy.scau.edu.cn/18828/list.htm",       # 人物风采（实例）
    "https://cxcyxy.scau.edu.cn/18829/list.htm",       # 优秀项目（实例）

    # ── 校团委（挑战杯 / 攀登计划 / 科技活动） ──────────────────────────────
    "https://xtw.scau.edu.cn/tzgg/list.htm",
    "https://xtw.scau.edu.cn/kjcx/list.htm",
    "https://xtw.scau.edu.cn/pdjh/list.htm",
    "https://xtw.scau.edu.cn/tzb/list.htm",
    "https://xtw.scau.edu.cn/cqc/list.htm",
    "https://xtw.scau.edu.cn/zlxz/list.htm",

    # ── 本科生院（竞赛学分认定 / 实践教学 / 推免资格） ──────────────────────
    "https://jwc.scau.edu.cn/5113/list.htm",           # 教务公告
    "https://jwc.scau.edu.cn/5138/list.htm",           # 实践教学科
    "https://jwc.scau.edu.cn/5135/list.htm",           # 学籍科
    "https://jwc.scau.edu.cn/5110/list.htm",           # 办事指南
    "https://jwc.scau.edu.cn/5109/list.htm",           # 管理文件

    # ── 研究生院与研招（推免 / 考研） ───────────────────────────────────────
    "https://yjsy.scau.edu.cn/208/list.htm",           # 通知公告
    "https://yjsy.scau.edu.cn/156/list.htm",           # 创新工程
    "https://yzb.scau.edu.cn/",                        # 研究生招生
]

# p1 追加：其余 P1 分组里的通知/动态类栏目（用关键字匹配栏目名）
P1_EXTRA_NAME_HINTS = ("通知公告", "通知", "公告", "学院动态", "新闻", "学工动态",
                       "就业", "招聘", "教务公告", "科研动态", "学术")

# p2 追加：科研与国际交流
P2_EXTRA_SITES = ("kyy.scau.edu.cn", "fao.scau.edu.cn", "gdic.scau.edu.cn",
                  "nxy.scau.edu.cn", "vet.scau.edu.cn", "spxy.scau.edu.cn",
                  "dongke.scau.edu.cn", "lf.scau.edu.cn", "hyxy.scau.edu.cn",
                  "zhxy.scau.edu.cn")


def _by_url(sites: list[Site]) -> dict[str, Site]:
    return {s.url: s for s in sites}


def curated(groups: list[Group], scope: str = "narrow") -> list[Site]:
    """返回按优先级排序的站点列表。scope ∈ {narrow, p1, p2, all}。"""
    scope = (scope or "narrow").lower()
    if scope == "all":
        sites = collect_sites(groups, include_single_page=False)
        return sorted(sites, key=lambda s: (s.priority, s.url))

    all_sites = collect_sites(groups, include_single_page=scope in ("narrow", "p1"))
    index = _by_url(all_sites)
    ordered: list[Site] = []
    seen: set[str] = set()

    def push(site: Site | None) -> None:
        if site is not None and site.url not in seen:
            seen.add(site.url)
            ordered.append(site)

    if scope == "narrow":
        for url in NARROW_URLS:
            push(index.get(url))
        return ordered

    # p1 / p2：先放 narrow，再补其余 P1 通知类栏目
    for url in NARROW_URLS:
        push(index.get(url))
    for s in all_sites:
        if s.group_id == "competition_and_innovation":
            push(s)
    for s in all_sites:
        if s.priority == 1 and any(h in (s.name or "") for h in P1_EXTRA_NAME_HINTS):
            push(s)
    if scope == "p2":
        for s in all_sites:
            if s.site in P2_EXTRA_SITES or s.priority == 2:
                push(s)
    return ordered


def missing_from_seed(groups: list[Group]) -> list[str]:
    """自检：NARROW_URLS 是否都能在种子里找到（防止手写 URL 打错）。"""
    known = {s.url for s in collect_sites(groups, include_single_page=True)}
    return [u for u in NARROW_URLS if u not in known]
