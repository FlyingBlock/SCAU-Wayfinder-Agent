""" /api/ask 的卡片链路离线自测（不联网、不调模型、不碰真库）。

跑法：
    python tests/test_cards_api.py

这条测试回答的是一个具体问题：**「对话里真的会出现卡片吗？」**
做法：在临时目录里造一个 SQLite 库，塞三篇「长得像华农通知」的文章
（其中两篇带附件），把 `SETTINGS.crawl` 临时指向这个目录，起一个真的
HTTP 服务，然后用 `dry=1` 请求 `/api/ask`（dry 模式不调模型、不花钱），
检查 SSE 里有没有 `event: cards`，以及卡片内容对不对。
"""
from __future__ import annotations

import http.client
import json
import shutil
import socket
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(errors="replace")           # type: ignore[union-attr]
    except (AttributeError, OSError, ValueError):
        pass

from wayfinder.api.registry import build_router               # noqa: E402
from wayfinder.core.config import CrawlSettings, SETTINGS    # noqa: E402
from wayfinder.corpus.store import Store                      # noqa: E402
from wayfinder.server.http import ApplicationServer           # noqa: E402
from wayfinder.services import Services                       # noqa: E402

FAILURES: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(("  ✓ " if cond else "  ✗ ") + msg)
    if not cond:
        FAILURES.append(msg)


ARTICLES = [
    {
        "url": "https://cxcy.scau.edu.cn/2026/0220/c1a101/page.htm",
        "title": "关于举办2026年中国国际大学生创新大赛华南农业大学校赛的通知",
        "pub_date": "2026-02-20",
        "body": (
            "各学院、各位同学：为做好中国国际大学生创新大赛校赛组织工作，现将有关事项通知如下。"
            "一、参赛对象 全日制在校本科生、研究生均可报名，以团队形式参赛。"
            "二、时间安排 报名截止时间：2026年3月20日17:00。"
            "比赛时间：2026年4月10日，地点为第三教学楼。"
            "三、材料提交 请于2026年3月18日前提交项目计划书。"
            "四、奖项设置 设一等奖、二等奖、三等奖若干，获奖按《华南农业大学学生竞赛奖励办法》加分。"
            "附件：报名表、项目计划书模板。"
        ),
        "attachments": ["https://cxcy.scau.edu.cn/_upload/article/files/apply.docx",
                        "https://cxcy.scau.edu.cn/_upload/article/files/template.pdf"],
        "college": "创新创业学院",
        "topic": "competition",
    },
    {
        "url": "https://tw.scau.edu.cn/2026/0301/c2a202/page.htm",
        "title": "关于开展第十五届「挑战杯」广东大学生创业计划竞赛校内选拔的通知",
        "pub_date": "2026-03-01",
        "body": (
            "校团委决定开展第十五届「挑战杯」广东大学生创业计划竞赛校内选拔。"
            "报名截止时间：2026年10月30日。初赛时间：2026年11月15日。"
            "参赛项目须为原创，不得抄袭。详见附件：校内选拔报名表.zip"
        ),
        "attachments": ["https://tw.scau.edu.cn/_upload/article/files/tzb.zip"],
        "college": "校团委",
        "topic": "competition",
    },
    {
        "url": "https://jwc.scau.edu.cn/2026/0210/c3a303/page.htm",
        "title": "关于2026年秋季学期本科生选课工作的通知",
        "pub_date": "2026-02-10",
        "body": "选课时间：2026年2月20日至2月28日。请同学们登录教务系统选课，逾期不再受理。",
        "attachments": [],
        "college": "教务处",
        "topic": "academic",
    },
]


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def seed(db: Path) -> None:
    st = Store(db)
    for i, a in enumerate(ARTICLES):
        st.upsert_article(
            dedupe_key=f"test-{i}", site_id=None, url=a["url"], title=a["title"],
            body=a["body"], pub_date=a["pub_date"], attachments=a["attachments"],
            topic=a["topic"], college=a["college"], site_host="scau.edu.cn",
        )
    st.close()


def stream(port: int, path: str, timeout: float = 60.0) -> str:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=timeout)
    conn.request("GET", path)
    resp = conn.getresponse()
    data = resp.read().decode("utf-8", "replace")
    conn.close()
    return data


def sse_events(text: str) -> list[tuple[str, str]]:
    """把 SSE 文本拆成 [(event, data), …]。"""
    out: list[tuple[str, str]] = []
    event = "message"
    for line in text.splitlines():
        if line.startswith("event: "):
            event = line[7:].strip()
        elif line.startswith("data: "):
            out.append((event, line[6:]))
    return out


def main() -> int:
    print("=" * 74)
    print("对话卡片链路自测（/api/ask → SSE cards 事件）")
    print("=" * 74)

    tmp = ROOT / "_test_tmp" / "cards"
    shutil.rmtree(tmp, ignore_errors=True)
    # 每个「数据目录」里库名固定是 crawler.db（CrawlSettings.db_path 就是这么拼的）
    seed_dir = tmp / "seed"
    seed_dir.mkdir(parents=True, exist_ok=True)
    db = seed_dir / "crawler.db"
    original_crawl = SETTINGS.crawl
    httpd = None
    try:
        seed(db)
        SETTINGS.crawl = CrawlSettings(data_dir=seed_dir)
        port = free_port()
        httpd = ApplicationServer(("127.0.0.1", port),
                                  build_router(Services(settings=SETTINGS)))
        threading.Thread(target=httpd.serve_forever, daemon=True).start()

        # ---- 1. 页面里带着卡片相关的样式与脚本 ----
        print("\n[1] 单页应用里带上卡片渲染")
        page = "\n".join(stream(port, path) for path in (
            "/", "/assets/css/shell.css",
            "/assets/js/main.js", "/assets/js/features/chat/index.js",
            "/assets/js/features/chat/content.js", "/assets/js/features/chat/cards.js",
            "/assets/js/features/calc/index.js", "/assets/js/features/calc/activities.js",
            "/assets/js/shared/toast.js"))
        for probe, what in [("cards-wrap", "卡片容器"), ("class=\"acard", "卡片样式"),
                            ("renderCards", "卡片渲染函数"),
                            ("添加到活动篮", "入篮按钮文案"),
                            ("toast", "轻提示")]:
            check(probe in page, f"页面含{what}（{probe}）")

        # ---- 2. dry 模式问答：SSE 里要有 cards 事件 ----
        print("\n[2] /api/ask（dry=1，不调模型）")
        q = "/api/ask?dry=1&rounds=0&q=" + "%E7%94%9F%E7%89%A9%E4%B8%93%E4%B8%9A%E5%8F%AF%E4%BB%A5%E5%8F%82%E5%8A%A0%E4%BB%80%E4%B9%88%E7%AB%9E%E8%B5%9B"
        raw = stream(port, q)
        events = sse_events(raw)
        kinds = [e for e, _ in events]
        check("trace" in kinds, "SSE 里有 trace 事件（检索过程）")
        check("answer" in kinds, "SSE 里有 answer 事件")
        check("cards" in kinds, "SSE 里有 cards 事件 ← 卡片就是这样送到前端的")
        check(any(e == "trace" and json.loads(d).get("step") == "cards"
                  for e, d in events),
              "trace 里有结构化 cards 步骤")

        cards = {}
        for e, d in events:
            if e == "cards":
                cards = json.loads(d)
        acts = cards.get("activities") or []
        files = cards.get("files") or []
        times = cards.get("times") or []
        print("    活动：" + "、".join(a.get("name", "") for a in acts))
        print("    附件：" + "、".join(f.get("file_name", "") for f in files))
        print("    时间：" + "；".join(f"{t.get('label')}={t.get('date')}" for t in times))
        check(bool(acts), f"卡片里有活动（{len(acts)} 张）")
        check(bool(files), f"卡片里有附件（{len(files)} 个）")
        check(any(t.get("is_deadline") for t in times), "时间卡片里标出了截止类日期")

        # ---- 3. 卡片内容对不对 ----
        print("\n[3] 卡片内容")
        names = " ".join(a.get("name", "") for a in acts)
        check("创新大赛" in names or "挑战杯" in names, "抽出了赛事类活动")
        check(not any("选课" in a.get("name", "") for a in acts),
              "教务选课通知没有混进活动卡")
        matched = [a for a in acts if a.get("in_registry")]
        check(bool(matched), f"有 {len(matched)} 张卡对上了已核验名录（可入活动篮）")
        for a in matched:
            check(bool(a.get("id")) and bool(a.get("basket_ready")),
                  f"「{a.get('name')}」带 activity_id={a.get('id')}，可直接入篮")
            sc = a.get("scores") or {}
            check((sc.get("best_zongce") or 0) + (sc.get("best_tuimian") or 0) > 0,
                  f"「{a.get('name')}」带综测/推免分值")
        for a in acts:
            if not a.get("in_registry"):
                check(not a.get("basket_ready") and bool(a.get("registry_note")),
                      f"未匹配名录的「{a.get('name')}」如实标注、不给假分值")
        check(any(f.get("file_label") in ("Word", "PDF", "压缩包") for f in files),
              "附件卡带文件类型标签")
        check(all((f.get("source") or {}).get("n") for f in files),
              "附件卡能回溯到证据编号")

        # ---- 4. 库里没有语料时的降级 ----
        print("\n[4] 无证据时的降级行为")
        empty_dir = tmp / "empty"
        empty_dir.mkdir(exist_ok=True)
        Store(empty_dir / "crawler.db").close()
        SETTINGS.crawl = CrawlSettings(data_dir=empty_dir)
        raw2 = stream(port, "/api/ask?dry=1&q=abc")
        check("answer" in [e for e, _ in sse_events(raw2)],
              "库里没有语料时仍返回 answer 事件（提示先抓取），不抛 500")
        SETTINGS.crawl = CrawlSettings(data_dir=seed_dir)
    finally:
        SETTINGS.crawl = original_crawl
        if httpd is not None:
            httpd.shutdown()
            httpd.server_close()
        shutil.rmtree(tmp, ignore_errors=True)

    print("\n" + "=" * 74)
    if FAILURES:
        print(f"失败 {len(FAILURES)} 项：")
        for f in FAILURES:
            print("  - " + f)
        return 1
    print("全部通过 ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
