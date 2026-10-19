"""把 `scau_bio_seed.yaml`（以及必要时 `web.md`）解析成机器可读种子。

本工作区的 `scau_bio_seed.yaml` 是人工核验过的产物，URL 逐字取自 `web.md`，
因此**优先直接用它**。该文件用的是内联 flow mapping 风格：

    - {name: "...", url: "...", site: "...", status: ok, kind: list, topic: competition}

所以这里不引入 PyYAML（沙箱内无法 pip 安装），而是写一个只针对该格式的
确定性解析器 —— 它必须能正确处理值里的中文括号、逗号、冒号与引号。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

GROUP_LINE = re.compile(r"^\s{2}-\s+id:\s*(\S+)\s*$")
FIELD_LINE = re.compile(r"^\s{4}(name|priority|why):\s*(.*)$")
SITE_LINE = re.compile(r"^\s{6}-\s*\{(.*)\}\s*$")

# 指南 §4.4 的分层裁剪：P1 优先跑通全链路，P2/L3 用于扩量
PRIORITY_GROUPS = {
    "p1": [
        "competition_and_innovation",
        "colleges_bio",
        "undergraduate_academic",
        "graduate",
        "student_affairs_and_youth_league",
        "career",
    ],
    "p2": [
        "competition_and_innovation",
        "colleges_bio",
        "undergraduate_academic",
        "graduate",
        "student_affairs_and_youth_league",
        "career",
        "research_and_grants",
    ],
    "all": None,
}

# 生物专业相关的核心学院与站点：用于 topic/college 打标与相关性加权
BIO_COLLEGE_HOSTS = {
    "life.scau.edu.cn": "生命科学学院",
    "nxy.scau.edu.cn": "农学院",
    "vet.scau.edu.cn": "兽医学院",
    "dongke.scau.edu.cn": "动物科学学院",
    "spxy.scau.edu.cn": "食品学院",
    "lf.scau.edu.cn": "林学与风景园林学院",
    "hyxy.scau.edu.cn": "海洋学院",
    "zhxy.scau.edu.cn": "资源环境学院",
    "hgxy.scau.edu.cn": "材料与能源学院",
    "xxxy.scau.edu.cn": "数学与信息学院",
    "cme.scau.edu.cn": "工程学院",
    "yjsy.scau.edu.cn": "研究生院",
    "jwc.scau.edu.cn": "本科生院",
    "xtw.scau.edu.cn": "校团委",
    "cxcyxy.scau.edu.cn": "创新创业学院",
    "kyy.scau.edu.cn": "科学研究院",
    "jyzx.scau.edu.cn": "就业创业信息网",
    "fao.scau.edu.cn": "国际交流处",
    "zsb.scau.edu.cn": "招生办",
}


@dataclass
class Site:
    name: str
    url: str
    site: str = ""
    status: str = "unverified"
    kind: str = "list"
    topic: str = "general"
    group_id: str = ""
    group_name: str = ""
    priority: int = 3

    @property
    def is_crawlable(self) -> bool:
        """登录墙 / 已失效入口不进抓取队列。"""
        if self.status in ("login_required", "broken"):
            return False
        if self.kind == "system":
            return False
        return self.url.startswith(("http://", "https://"))


@dataclass
class Group:
    id: str
    name: str = ""
    priority: int = 3
    why: str = ""
    sites: list[Site] = field(default_factory=list)


def _split_flow(text: str) -> list[str]:
    """按逗号切分 flow mapping，但忽略引号内与括号内的逗号。"""
    parts, buf, quote, depth = [], [], None, 0
    for ch in text:
        if quote:
            buf.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
            buf.append(ch)
        elif ch in "[{(":
            depth += 1
            buf.append(ch)
        elif ch in "]})":
            depth -= 1
            buf.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    if buf:
        parts.append("".join(buf).strip())
    return [p for p in parts if p]


def _parse_flow(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in _split_flow(text):
        if ":" not in part:
            continue
        key, _, val = part.partition(":")
        val = val.strip().strip('"').strip("'")
        out[key.strip()] = val
    return out


def load_seed(path: Path) -> list[Group]:
    """解析种子 YAML，返回分组列表（按文档顺序）。"""
    if not path.is_file():
        raise FileNotFoundError(f"种子文件不存在：{path}")

    groups: list[Group] = []
    cur: Group | None = None

    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue

        m = GROUP_LINE.match(line)
        if m:
            cur = Group(id=m.group(1))
            groups.append(cur)
            continue
        if cur is None:
            continue

        m = FIELD_LINE.match(line)
        if m:
            key, val = m.group(1), m.group(2).strip().strip('"').strip("'")
            if key == "name":
                cur.name = val
            elif key == "priority":
                try:
                    cur.priority = int(val)
                except ValueError:
                    pass
            elif key == "why":
                cur.why = val
            continue

        m = SITE_LINE.match(line)
        if m:
            d = _parse_flow(m.group(1))
            url = d.get("url", "")
            if not url:
                continue
            site = Site(
                name=d.get("name", ""),
                url=url,
                site=d.get("site", ""),
                status=d.get("status", "unverified"),
                kind=d.get("kind", "list"),
                topic=d.get("topic", "general"),
                group_id=cur.id,
                group_name=cur.name,
                priority=cur.priority,
            )
            cur.sites.append(site)
    return groups


def select_groups(groups: list[Group], scope: str = "p1") -> list[Group]:
    """按 scope（p1/p2/all）裁剪分组。未识别的 scope 视为 all。"""
    wanted = PRIORITY_GROUPS.get(scope.lower())
    if wanted is None:
        return groups
    return [g for g in groups if g.id in wanted]


def collect_sites(groups: list[Group], include_single_page: bool = True) -> list[Site]:
    """展平为站点列表并按 URL 去重（同一 URL 保留优先级更高的那条）。"""
    seen: dict[str, Site] = {}
    for g in groups:
        for s in g.sites:
            if not s.is_crawlable:
                continue
            if not include_single_page and s.kind == "single_page":
                continue
            prev = seen.get(s.url)
            if prev is None or s.priority < prev.priority:
                seen[s.url] = s
    return list(seen.values())


def college_of(host: str) -> str:
    h = (host or "").lower()
    for k, v in BIO_COLLEGE_HOSTS.items():
        if h == k or h.endswith("." + k):
            return v
    return ""


def stats(groups: list[Group]) -> str:
    lines = []
    for g in groups:
        n_ok = sum(1 for s in g.sites if s.is_crawlable)
        lines.append(f"  [P{g.priority}] {g.id:<38} {n_ok:>4}/{len(g.sites):<4} {g.name}")
    return "\n".join(lines)
