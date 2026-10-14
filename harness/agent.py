"""编排层：Query 分解 → 站内/公网检索 → 缺口检测 → 补检索 → 带引用生成（指南 §8）。

与「一次检索 + 一次生成」的区别就在这里：
  · 开放问题先被拆成 4-8 条可检索的子查询（site / web 分流）
  · 每条子查询独立检索，去重后汇总
  · 让 LLM 判断证据是否足够，不足则生成新查询再补一轮（默认最多 2 轮）
  · 生成时把所有证据编号，要求逐句标注来源；无来源的必须写成「推测」
"""
from __future__ import annotations

import concurrent.futures as cf
import datetime
import re
from dataclasses import dataclass, field
from typing import Callable, Iterator

from . import prompts
from .config import SETTINGS, Settings
from .llm import LLM, LLMError, extract_json
from .store import Hit, Store
from .websearch import WebResult, WebSearcher

TraceFn = Callable[[str, dict], None]


@dataclass
class Evidence:
    n: int
    title: str
    url: str
    pub_date: str = ""
    snippet: str = ""
    source: str = "site"          # site | web
    article_id: int = 0
    topic: str = ""
    college: str = ""
    site_name: str = ""
    score: float = 0.0
    body: str = ""
    stale: bool = False
    #: 命中的附件（附件正文参与检索时记录，卡片层据此展示「这条信息来自哪个附件」）
    attach_hits: list[dict] = field(default_factory=list)

    @property
    def age_days(self) -> int | None:
        if not self.pub_date:
            return None
        try:
            d = datetime.date.fromisoformat(self.pub_date[:10])
        except ValueError:
            return None
        return (datetime.date.today() - d).days


@dataclass
class Answer:
    question: str
    text: str
    evidence: list[Evidence] = field(default_factory=list)
    subqueries: list[dict] = field(default_factory=list)
    rounds: int = 0
    trace: list[tuple[str, dict]] = field(default_factory=list)
    error: str = ""
    prompt: str = ""          # dry_run 时填充：真正会送进模型的上下文
    # 对话卡片（活动/赛事、附件、关键时间）。由 harness.cards 从证据里确定性抽取，
    # 不经模型生成——见 cards.py 的模块说明。
    cards: dict = field(default_factory=dict)


# --------------------------------------------------------------------------- #
def rrf_merge(rank_lists: list[list[int]], k: int = 60) -> list[tuple[int, float]]:
    """倒数排名融合（指南 §7.2）：多路子查询的排名结果合并排序。"""
    scores: dict[int, float] = {}
    for ranks in rank_lists:
        for i, doc_id in enumerate(ranks, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + i)
    return sorted(scores.items(), key=lambda kv: -kv[1])


_WEB_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
           "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")

# 公网原件往往是整页，用这些信号挑出真正有信息的段落
_INFO_HINTS = (
    "报名", "截止", "时间", "日期", "条件", "要求", "对象", "资格", "流程", "赛制",
    "奖项", "奖金", "组织", "主办", "承办", "联系", "费用", "名额", "名额",
    "初赛", "复赛", "决赛", "国赛", "省赛", "校赛", "评审", "材料", "提交",
    "推免", "保研", "学分", "绩点", "考试", "科目", "招生", "培养", "就业",
)
_DATE_IN_TEXT = re.compile(r"\d{4}\s*[-/年]\s*\d{1,2}")


def _condense(text: str, limit: int) -> str:
    """把长正文压到 limit 字符：**只挑有信息的段落**，不够再回填开头段落。

    公网原件（赛事官网、新闻页）里大量是导航、页脚、相关推荐。若按
    「靠前优先」截断，预算会被导航吃光，真正写「报名截止 2027-01-15」的
    那一段反而进不了上下文。
    """
    if not text:
        return ""
    if len(text) <= limit:
        return text
    paras = [p.strip() for p in text.split("\n") if p.strip()]
    if not paras:
        return text[:limit]

    scored: list[tuple[float, int, str]] = []
    for i, p in enumerate(paras):
        s = float(sum(1 for h in _INFO_HINTS if h in p))
        if _DATE_IN_TEXT.search(p):
            s += 1.5
        if len(p) < 8:                       # 过短的碎片（面包屑、单字行）
            s -= 0.5
        scored.append((s, i, p))

    informative = [t for t in scored if t[0] >= 1.0]
    informative.sort(key=lambda t: (-t[0], t[1]))

    picked: list[tuple[int, str]] = []
    used = 0
    for _, i, p in informative:
        if used + len(p) > limit:
            continue
        picked.append((i, p))
        used += len(p)
        if used >= limit * 0.9:
            break

    if used < limit * 0.5:                   # 信息段落太少 → 用开头段落回填
        for _, i, p in sorted(scored, key=lambda t: t[1]):
            if any(i == j for j, _ in picked):
                continue
            if used + len(p) > limit:
                continue
            picked.append((i, p))
            used += len(p)
            if used >= limit * 0.9:
                break

    if not picked:
        return text[:limit]
    picked.sort(key=lambda t: t[0])          # 恢复原文顺序
    return "\n".join(p for _, p in picked)


class Agent:
    def __init__(self, store: Store, llm: LLM, searcher: WebSearcher | None = None,
                 settings: Settings | None = None) -> None:
        self.store = store
        self.llm = llm
        self.searcher = searcher
        self.s = settings or SETTINGS

    # ------------------------------------------------------------------ #
    def answer(self, question: str, *, max_rounds: int | None = None,
               trace: TraceFn | None = None, dry_run: bool = False) -> Answer:
        return self.answer_iter(question, max_rounds=max_rounds, trace=trace, dry_run=dry_run)

    def answer_iter(self, question: str, *, max_rounds: int | None = None,
                    trace: TraceFn | None = None, dry_run: bool = False) -> Answer:
        """同步执行完整流程（带上限保护）。trace 回调用于前端展示中间步骤。

        dry_run=True 时：跳过所有 LLM 调用（分解用确定性兜底、缺口检测跳过），
        只跑到证据聚合为止，并把最终 prompt 放进 Answer.prompt。
        用于「不花 token 验证抓取与检索是否靠谱」。
        """
        rounds = 0 if dry_run else (self.s.agent_max_rounds if max_rounds is None else max_rounds)
        tr = trace or (lambda step, data: None)

        # ① 意图分解
        if dry_run or not self.llm.configured:
            subqueries = self.fallback_subqueries(question)
        else:
            subqueries = self._decompose(question)
        tr("decompose", {"subqueries": subqueries})
        if not subqueries:
            subqueries = [{"query": question, "scope": "site", "why": "兜底"}]

        evidence: list[Evidence] = []
        seen: set[str] = set()
        tried: list[str] = [sq["query"] for sq in subqueries]
        pending = list(subqueries)

        for rnd in range(rounds + 1):
            if not pending:
                break
            tr("retrieve", {"round": rnd + 1, "queries": [q["query"] for q in pending]})
            found = self._retrieve(pending, question)
            new_count = 0
            for ev in found:
                key = ev.url
                if key in seen:
                    continue
                seen.add(key)
                evidence.append(ev)
                new_count += 1
            tr("retrieved", {"round": rnd + 1, "new": new_count, "total": len(evidence)})

            if rnd >= rounds:
                break
            pending = self._find_gaps(question, evidence, tried)
            tried.extend(q["query"] for q in pending)
            tr("gaps", {"round": rnd + 1, "missing": pending})

        # 编号（生成前的最终顺序：校内优先，按分数/时效）
        self._rank_and_budget(evidence)
        tr("evidence", {"count": len(evidence)})

        # ⑧ 卡片装配（无模型、无网络；失败不影响答题）
        cards = self._build_cards(evidence)
        tr("cards", {"stats": cards.get("stats", {})})

        if dry_run:
            prompt = self.build_prompt(question, evidence)
            return Answer(question=question, text="", evidence=evidence,
                          subqueries=subqueries, rounds=0, prompt=prompt,
                          cards=cards)

        # ⑥⑦ 生成
        try:
            text = self._generate(question, evidence)
        except LLMError as e:
            return Answer(question=question, text="", evidence=evidence,
                          subqueries=subqueries, rounds=rounds, error=str(e),
                          cards=cards)
        return Answer(question=question, text=text, evidence=evidence,
                      subqueries=subqueries, rounds=rounds, cards=cards)

    def _build_cards(self, evidence: list[Evidence]) -> dict:
        """把证据整理成对话卡片（活动/赛事、附件、关键时间）。

        刻意不让它抛异常：卡片是「加分项」，抽不出来也不该让整个问答失败。
        装配前已经把附件名从库里取过一次，所以这里把 store 一起传进去。
        """
        try:
            from . import cards as cards_mod

            return cards_mod.build_cards(evidence, store=self.store).as_dict()
        except Exception as e:                     # noqa: BLE001
            return {"activities": [], "files": [], "times": [],
                    "stats": {"error": f"{type(e).__name__}: {e}"}}

    # ------------------------------------------------------------------ #
    def _decompose(self, question: str) -> list[dict]:
        try:
            raw = self.llm.complete_json(
                prompts.DECOMPOSE.format(question=question),
                system=prompts.SYSTEM, temperature=0.2, max_tokens=1100,
            )
        except LLMError:
            return []
        items = raw if isinstance(raw, list) else (raw.get("subqueries") if isinstance(raw, dict) else [])
        out: list[dict] = []
        for it in items or []:
            if not isinstance(it, dict):
                continue
            q = str(it.get("query") or "").strip()
            if len(q) < 2:
                continue
            scope = "web" if str(it.get("scope", "site")).lower().startswith("web") else "site"
            out.append({"query": q, "scope": scope, "why": str(it.get("why") or "")[:80]})
        return out[:8]

    def _retrieve(self, queries: list[dict], question: str) -> list[Evidence]:
        """并行跑所有子查询（站内 + 公网），再按 RRF + 分数排序汇总。"""
        site_q = [q for q in queries if q["scope"] == "site"]
        web_q = [q for q in queries if q["scope"] == "web"]
        results: list[Evidence] = []
        rank_lists: list[list[int]] = []
        pool: dict[int, Evidence] = {}

        def run_site(q: dict) -> list[Hit]:
            try:
                return self.store.search(q["query"], top_k=self.s.agent_top_k, prefer_bio=True)
            except Exception:
                return []

        if site_q:
            with cf.ThreadPoolExecutor(max_workers=min(6, len(site_q))) as ex:
                per_query = list(ex.map(run_site, site_q))
            attach_ranks: list[int] = []
            for q, hits in zip(site_q, per_query):
                ranks = []
                for h in hits:
                    ev = pool.get(h.article_id)
                    if ev is None:
                        ev = Evidence(
                            n=0, title=h.title, url=h.url, pub_date=h.pub_date,
                            snippet=h.snippet, source="site", article_id=h.article_id,
                            topic=h.topic, college=h.college, site_name=h.site_name,
                            score=h.score,
                        )
                        pool[h.article_id] = ev
                    else:
                        ev.score = max(ev.score, h.score)
                    ranks.append(h.article_id)
                rank_lists.append(ranks)
                # 附件正文命中：把命中的附件所归属的文章顶上（华农的报名表/赛程/名额
                # 表大多只在附件里，正文里那句「详见附件」是检索不到关键信息的）
                try:
                    for a in self.store.search_attachments(q["query"], top_k=4):
                        aid = int(a.get("article_id") or 0)
                        if not aid:
                            continue
                        attach_ranks.append(aid)
                        ev = pool.get(aid)
                        if ev is None:
                            ev = Evidence(
                                n=0, title=a.get("title") or "", url=a.get("article_url") or "",
                                pub_date=a.get("pub_date") or "", snippet=a.get("snippet") or "",
                                source="site", article_id=aid, topic=a.get("topic") or "",
                                college=a.get("college") or "", score=0.0,
                            )
                            pool[aid] = ev
                        ev.attach_hits.append({
                            "attachment_id": int(a.get("attachment_id") or 0),
                            "filename": a.get("filename") or "",
                            "stored": a.get("stored") or "",
                            "kind": a.get("kind") or "",
                            "snippet": a.get("snippet") or "",
                        })
                        ev.score = max(ev.score, 2.0)
                except Exception:
                    pass
            if attach_ranks:
                rank_lists.append(attach_ranks)
            merged = rrf_merge(rank_lists) if rank_lists else []
            order = [doc_id for doc_id, _ in merged]
            for doc_id, rrf in merged:
                pool[doc_id].score += rrf * 10
            # 未进入合并（不应发生）的兜底
            for doc_id in pool:
                if doc_id not in order:
                    order.append(doc_id)
            results.extend(pool[d] for d in order)

        # 公网
        if web_q and self.searcher and self.searcher.available:
            def run_web(q: dict) -> list[WebResult]:
                try:
                    return self.searcher.search(q["query"], top_k=4)
                except Exception:
                    return []

            with cf.ThreadPoolExecutor(max_workers=min(4, len(web_q))) as ex:
                for hits in ex.map(run_web, web_q):
                    for w in hits:
                        results.append(Evidence(
                            n=0, title=w.title, url=w.url, snippet=w.snippet,
                            source="web", score=0.2,
                        ))
        return results

    # ------------------------------------------------------------------ #
    def _find_gaps(self, question: str, evidence: list[Evidence], tried: list[str]) -> list[dict]:
        if not evidence:
            return []
        digest = "\n".join(
            f"- [{e.source}] {e.title[:70]}（{e.pub_date or '无日期'}）" for e in evidence[:28]
        )
        try:
            raw = self.llm.complete_json(
                prompts.GAP.format(question=question, evidence_digest=digest,
                                   tried="、".join(tried[:16])),
                system=prompts.SYSTEM, temperature=0.0, max_tokens=800,
            )
        except LLMError:
            return []
        if isinstance(raw, dict) and raw.get("sufficient") is True:
            return []
        items = (raw or {}).get("missing") if isinstance(raw, dict) else None
        out: list[dict] = []
        for it in (items or [])[:3]:
            if not isinstance(it, dict):
                continue
            q = str(it.get("query") or "").strip()
            if len(q) < 2 or q in tried:
                continue
            scope = "web" if str(it.get("scope", "site")).lower().startswith("web") else "site"
            out.append({"query": q, "scope": scope, "why": str(it.get("why") or "")[:80]})
        return out

    # ------------------------------------------------------------------ #
    def _rank_and_budget(self, evidence: list[Evidence]) -> None:
        """排序 + 去重 + 预算裁剪 + 补齐正文，并给最终证据编号。

        预算：正文总字符数（默认 ~26k 字符，约 15k tokens）。超预算时优先
        保留「有日期 + 校内 + 主题相关」的证据，并压缩每条正文长度。
        公网证据原来只有搜索结果摘要，这里会真正抓一次原页正文，
        否则模型只能看到一两句话，容易对赛事规则/时间给出含糊甚至错误的表述。
        """
        import os

        budget = int(os.environ.get("HARNESS_EVIDENCE_BUDGET", "26000") or 26000)
        per_doc = int(os.environ.get("HARNESS_EVIDENCE_CHARS", "900") or 900)
        web_chars = int(os.environ.get("HARNESS_WEB_CHARS", "1400") or 1400)
        max_web_fetch = int(os.environ.get("HARNESS_WEB_FETCH", "4") or 4)
        max_docs = int(os.environ.get("HARNESS_EVIDENCE_DOCS", "24") or 24)

        # 去重：同一 URL 只留分数最高的
        best: dict[str, Evidence] = {}
        for e in evidence:
            cur = best.get(e.url)
            if cur is None or e.score > cur.score:
                best[e.url] = e
        items = list(best.values())

        today = datetime.date.today()

        def rank(e: Evidence) -> tuple:
            fresh = 0
            if e.pub_date:
                try:
                    days = (today - datetime.date.fromisoformat(e.pub_date[:10])).days
                    fresh = 1 if days <= 730 else 0
                except ValueError:
                    fresh = 0
            return (
                0 if e.source == "site" else 1,     # 校内证据优先
                -fresh,
                -e.score,
            )

        items.sort(key=rank)
        items = items[:max_docs]

        # 补齐公网正文
        web_needing = [e for e in items if e.source == "web" and not e.body][:max_web_fetch]
        if web_needing:
            fetched = self._fetch_web_bodies(web_needing, web_chars)
            for e, body in zip(web_needing, fetched):
                if body:
                    e.body = body

        total = 0
        kept: list[Evidence] = []
        attach_budget = int(os.environ.get("HARNESS_ATTACH_CHARS", "1600") or 1600)
        for e in items:
            e.stale = bool(e.age_days is not None and e.age_days > 548)   # >18 个月
            if e.source == "site" and e.article_id and not e.body:
                art = self.store.get_article(e.article_id, max_chars=per_doc * 3)
                e.body = (art or {}).get("body") or e.snippet
            limit = web_chars if e.source == "web" else per_doc
            # 公网原件是整页，先抽含关键信息的段落，再截断
            text = (e.body or e.snippet or "")
            text = _condense(text, limit)
            # 附件正文：报名截止、赛程、名额、加分表几乎只在附件里，
            # 只把当前证据正文里没有的信息（附件本身）接在后面，预算单独算。
            if e.source == "site" and e.article_id and attach_budget > 0:
                extra = self._attachment_excerpt(e, attach_budget)
                if extra:
                    text = f"{text}\n\n【该通知附件的正文（系统已下载并解析）】\n{extra}"
            e.snippet = text
            if total + len(text) > budget and kept:
                continue
            total += len(text)
            kept.append(e)
        evidence[:] = kept
        for i, e in enumerate(evidence, 1):
            e.n = i

    def _attachment_excerpt(self, e: Evidence, limit: int) -> str:
        """取这篇文章附件的正文摘录（优先取与问题相关的段落由 _condense 负责）。"""
        try:
            raw = self.store.attachment_text_map(
                int(e.article_id), max_chars_each=max(600, limit // 2), max_total=limit * 2)
        except Exception:
            return ""
        if not raw.strip():
            return ""
        return _condense(raw, limit)

    def _fetch_web_bodies(self, evs: list[Evidence], limit: int) -> list[str]:
        """并行抓公网原始页面并抽正文（用独立 Fetcher 避免污染站点限速表）。"""
        from .fetcher import Fetcher
        from .parse import html_to_text

        try:
            f = Fetcher(user_agent=_WEB_UA, timeout=15, retries=0, delay=0.2, jitter=0.2)
        except Exception:
            return [""] * len(evs)

        def one(e: Evidence) -> str:
            try:
                res = f.fetch(e.url, check_robots=False)
                if not res.ok or not res.text:
                    return ""
                text = html_to_text(res.text)
                return text if len(text) > 120 else ""
            except Exception:
                return ""

        with cf.ThreadPoolExecutor(max_workers=min(4, len(evs))) as ex:
            return list(ex.map(one, evs))

    # ------------------------------------------------------------------ #
    @staticmethod
    def _fmt_site(e: Evidence) -> str:
        head = f"[{e.n}] {e.title}"
        meta = []
        if e.pub_date:
            meta.append(f"发布时间 {e.pub_date}")
        if e.college:
            meta.append(e.college)
        if e.site_name:
            meta.append(e.site_name)
        if e.stale:
            meta.append("⚠️可能已过期")
        line = head + ("（" + "；".join(meta) + "）" if meta else "")
        return f"{line}\nURL: {e.url}\n正文：{e.snippet}\n"

    @staticmethod
    def _fmt_web(e: Evidence) -> str:
        return f"[{e.n}] {e.title}\nURL: {e.url}\n摘要：{e.snippet}\n"

    def _generate(self, question: str, evidence: list[Evidence]) -> str:
        site = "\n".join(self._fmt_site(e) for e in evidence if e.source == "site")
        web = "\n".join(self._fmt_web(e) for e in evidence if e.source == "web")
        prompt = prompts.ANSWER.format(
            question=question,
            site_evidence=site or "（无）",
            web_evidence=web or "（无）",
            today=datetime.date.today().isoformat(),
        )
        return self.llm.complete(prompt, system=prompts.SYSTEM,
                                 temperature=0.3, max_tokens=4096)

    def build_prompt(self, question: str, evidence: list[Evidence]) -> str:
        """暴露给 --dry-run：不调用 LLM，只看真正会送进模型的上下文。"""
        site = "\n".join(self._fmt_site(e) for e in evidence if e.source == "site")
        web = "\n".join(self._fmt_web(e) for e in evidence if e.source == "web")
        return prompts.ANSWER.format(
            question=question, site_evidence=site or "（无）",
            web_evidence=web or "（无）", today=datetime.date.today().isoformat(),
        )

    @staticmethod
    def fallback_subqueries(question: str) -> list[dict]:
        """没有 LLM 时的确定性分解：用关键词把问题映射到几类子查询。

        这样 `ask --dry-run` 与「未配置 key 时的检索兜底」都仍然可用。
        """
        dims = [
            ("竞赛", "site", "生命科学学院 大学生 竞赛 通知"),
            ("大赛", "site", "学科竞赛 大赛 报名"),
            ("创新", "site", "创新创业 大创 项目 申报"),
            ("挑战杯", "site", "挑战杯 课外学术科技作品"),
            ("推免", "site", "推免 免试 攻读 研究生"),
            ("保研", "site", "推免 工作 细则 实施方案"),
            ("考研", "site", "研究生 招生 复试"),
            ("科研", "site", "科研训练 实验室 本科生"),
            ("就业", "site", "就业 招聘 毕业生"),
            ("国际", "site", "国际交流 交换 留学"),
            ("学分", "site", "竞赛 学分 认定 奖励"),
            ("奖", "site", "奖学金 评选 公示"),
        ]
        qs: list[dict] = []
        for kw, scope, query in dims:
            if kw in question:
                qs.append({"query": query, "scope": scope, "why": f"问题提到「{kw}」"})
        if not qs:                            # 完全没命中就按通用维度铺开
            qs = [
                {"query": "竞赛 大赛 报名 通知", "scope": "site", "why": "通用竞赛维度"},
                {"query": "推免 研究生 推荐", "scope": "site", "why": "通用升学维度"},
                {"query": "创新创业 项目 申报", "scope": "site", "why": "通用双创维度"},
            ]
        # 补公网查询，用于拿赛事规则/含金量。
        # 必须带「大学生」限定词：否则「生物竞赛」会被搜成中学生物奥赛，
        # 返回一堆与高校学生发展无关的结果（实测踩过）。
        qs.append({"query": "全国大学生 生命科学竞赛 报名时间 参赛条件", "scope": "web",
                   "why": "国家级赛事官方安排"})
        qs.append({"query": "大学生 创新创业 挑战杯 互联网+ 时间 含金量", "scope": "web",
                   "why": "双创赛事规则与时间表"})
        return qs[:8]

    # ------------------------------------------------------------------ #
    def build_citations(self, answer: Answer) -> str:
        lines = []
        for e in answer.evidence:
            tag = "公网" if e.source == "web" else (e.college or e.site_name or "校内")
            date = f"（{e.pub_date}）" if e.pub_date else ""
            stale = " ⚠️可能已过期" if e.stale else ""
            lines.append(f"[{e.n}] {e.title} — {e.url}{date} · {tag}{stale}")
        return "\n".join(lines)
