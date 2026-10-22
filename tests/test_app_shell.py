"""前端模块自测：外壳与 ES Module 装配是否自洽。

跑法：
    python tests/test_app_shell.py

检查项：
  · HTML 只做结构，入口只有 ``/assets/js/main.js`` 一个 ES Module；
  · 功能模块按 shared / router / chat / calc / settings 分层，且没有 window 全局；
  · 计算器不再自己算 GPA、活动最佳成就或通道评分表；
  · 外壳滚动与布局断点仍然正确；
  · 每份 JS 都能被 node 按 ES Module 解析。
"""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(errors="replace")           # type: ignore[union-attr]
    except (AttributeError, OSError, ValueError):
        pass

from wayfinder.qa import prompts                   # noqa: E402

FE = ROOT / "frontend"
JS = FE / "js"
FAILURES: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(("  ✓ " if cond else "  ✗ ") + msg)
    if not cond:
        FAILURES.append(msg)


def note(msg: str) -> None:
    print("  · " + msg)


def read(rel: str) -> str:
    return (FE / rel).read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
def test_assets_wiring() -> None:
    print("\n[装配] HTML 只做结构，唯一入口是 ES Module")
    page = read("index.html")
    check("<style>" not in page, "index.html 没有内联 <style>")
    check('<script type="module" src="/assets/js/main.js"></script>' in page,
          "入口只有 /assets/js/main.js，且声明 type=module")
    for old in ("/assets/js/core.js", "/assets/js/chat.js",
                "/assets/js/calc.js", "/assets/js/boot.js"):
        check(old not in page, f"不再加载旧经典脚本 {old}")
    check("view-docs" not in page and "docs.css" not in page,
          "废弃的 docs 视图与样式已删除")
    check(page.count('id="view-chat"') == 1 and page.count('id="view-calc"') == 1,
          "对话 / 计算器两个视图容器都在")
    for rel in (
        "js/main.js", "js/router.js",
        "js/shared/dom.js", "js/shared/api.js", "js/shared/events.js",
        "js/features/chat/index.js", "js/features/chat/content.js",
        "js/features/chat/cards.js", "js/features/calc/index.js",
        "js/features/calc/activities.js", "js/features/calc/state.js",
        "js/features/settings/index.js",
    ):
        check((FE / rel).is_file(), f"{rel} 存在")


def test_modules() -> None:
    print("\n[模块] 主程序只装配，功能只依赖 shared/router")
    main = read("js/main.js")
    check("registerView('chat'" in main and "registerView('calc'" in main,
          "main.js 只注册视图钩子")
    check("bindSettings();" in main and "chatBind();" in main
          and "startRouter();" in main,
          "main.js 只负责启动，不写业务逻辑")

    router = read("js/router.js")
    check("export function registerView" in router and "runHook" in router,
          "router 通过注册钩子调用视图，不认识 chat/calc 内部")
    check("window.__calc" not in router and "window.__chat" not in router,
          "router 不再摸 window 全局")

    chat = read("js/features/chat/index.js")
    cards = read("js/features/chat/cards.js")
    check("from '../../router.js'" in chat and "currentView" in chat,
          "chat 从 router 读取当前视图")
    check("addToBasket" in cards and "inBasket" in cards,
          "对话页通过 calc/state 加入活动篮（cards 模块）")
    check("scau-calc-state-v1" not in chat + cards,
          "对话页不再直接读写计算器 localStorage")
    check("function traceText" in chat and "traceText(d.step, d.data)" in chat,
          "后端结构化 trace 由前端格式化")

    calc = read("js/features/calc/index.js")
    activities = read("js/features/calc/activities.js")
    check("from './state.js'" in calc, "计算器复用 calc/state")
    check("effective_gp" in calc, "绩点列使用后端 effective_gp")
    for old in ("function gpOf", "updateGpColumn", "RUBRIC_BY_CHANNEL",
                "UNIT_BY_CHANNEL", "fillDemo"):
        check(old not in calc + activities, f"已删除前端业务计算：{old}")
    check("act.best" in activities, "活动最佳成就只读后端 act.best（activities 模块）")

    state = read("js/features/calc/state.js")
    check("scau-calc-state-v1" in state and "localStorage.setItem" in state,
          "localStorage 只在 calc/state 一处读写")
    check("addToBasket" in state and "emit('basket:changed'" in state,
          "入篮通过状态模块发事件")

    settings = read("js/features/settings/index.js")
    check("export function bindSettings" in settings, "设置模块自己绑定 DOM")
    check("window.__chat" not in settings and "window.__settings" not in settings,
          "设置模块不再通过 window 全局通知聊天页")


def test_noscroll() -> None:
    print("\n[滚动] 只有对话视图是内部滚动")
    router = read("js/router.js")
    m = re.search(r"classList\.toggle\('noscroll',\s*([^)]+?)\s*\)", router)
    expr = m.group(1).strip() if m else "?"
    check(expr == "VIEW === 'chat'", f"#appmain 只在对话视图锁滚动（现在是 {expr}）")
    check(".appmain.noscroll{overflow:hidden}" in read("css/shell.css"),
          "外壳 CSS 里确实有 .appmain.noscroll{overflow:hidden}")


def test_calc_css() -> None:
    print("\n[样式] 计算器样式作用域隔离")
    calc = read("css/calc.css")
    check("#view-calc .wrap{display:grid" in calc, "计算器 .wrap 两栏网格生效")
    check("#view-calc .scroll{max-height:460px" in calc, "成绩表格滚动容器 .scroll 在")
    check("@media (max-width:1100px)" in calc, "@media 整块保留")
    stray = []
    for line in calc.splitlines():
        s = line.strip()
        if not s.endswith("{") or s.startswith(("@", "#view-calc", "/*", "*")):
            continue
        stray.append(s)
    check(not stray, f"计算器样式没有无作用域的规则：{stray[:4]}")


def test_load_order() -> None:
    print("\n[启动] 模块装配顺序与事件订阅")
    main = read("js/main.js")
    for token in ("registerView('chat'", "registerView('calc'",
                  "bindSettings();", "chatBind();", "startRouter();"):
        check(token in main, f"main.js 含启动步骤 {token}")
    chat = read("js/features/chat/index.js")
    content = read("js/features/chat/content.js")
    check("answer_delta" in chat and "answer_end" in chat,
          "对话脚本订阅流式事件（answer_delta / answer_end）")
    check("stripUrls" in content and "data-cite=" in content,
          "正文网址收进右栏、[n] 渲染成可点标号（content 模块）")
    check("on('status:refresh'" in chat,
          "设置保存后通过事件刷新状态，不反向依赖设置模块")
    check("function sourcesInline()" in content and "w >= 1048" in content,
          "右栏开合按 1048px 口径判断（content 模块）")


def test_layout() -> None:
    print("\n[布局] 对话视图：正文 + 右侧「引用来源」栏")
    page = read("index.html")
    shell = read("css/shell.css")
    for frag, why in (
        ('class="chat-main"', "正文与输入框放在 .chat-main 里"),
        ('class="sources" id="sources"', "右栏 .sources 存在且带 id"),
        ('id="sources-body"', "右栏有内容容器"),
        ('id="sources-toggle"', "右栏有收起/展开按钮"),
        ('id="sources-count"', "右栏标题带条数"),
    ):
        check(frag in page, why)
    check(".chatview{width:100%" in shell and ".chatview{max-width" not in shell,
          "对话区铺满主区")
    check(".chat-inner{max-width:760px" in shell
          and ".composer .inner{max-width:760px" in shell
          and ".sources{flex:0 0 248px" in shell,
          "正文列 760px、右栏 248px")
    check("@media (max-width:1295px)" in shell
          and ".sources{position:absolute" in shell,
          "放不下时右栏改成浮层")
    check("@media (min-width:1104px)" in shell
          and ".sidebar.closed ~ .appmain .sources{position:static" in shell,
          "左侧栏收起后右栏从 1104px 起并排贴右")


def test_module_imports() -> None:
    print("\n[依赖] 每个相对 import 都能落到真实文件")
    for path in sorted(JS.rglob("*.js")):
        source = path.read_text(encoding="utf-8")
        for spec in re.findall(r"from\s+['\"]([^'\"]+)['\"]", source):
            if not spec.startswith("."):
                continue
            target = (path.parent / spec).resolve()
            if target.suffix != ".js":
                target = target.with_suffix(".js")
            check(target.is_file(),
                  f"{path.relative_to(FE).as_posix()} → {spec}")


def test_js_syntax() -> None:
    print("\n[语法] 每份 JS 都能按 ES Module 解析")
    node = shutil.which("node")
    if not node:
        note("PATH 里没有 node，跳过（不影响其它检查）")
        return
    for path in sorted(JS.rglob("*.js")):
        source = path.read_text(encoding="utf-8")
        proc = subprocess.run([node, "--input-type=module", "--check"],
                              input=source, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=60)
        rel = path.relative_to(FE).as_posix()
        check(proc.returncode == 0,
              f"{rel} ES Module 解析通过"
              + ("" if proc.returncode == 0 else "：" + (proc.stderr or "")[:200]))


def test_prompts() -> None:
    print("\n[口径] 提示词仍要求正文不写网址")
    check("## 引用" not in prompts.ANSWER, "不再要求模型输出文末「## 引用」清单")
    check("不要出现网址" in prompts.ANSWER, "明确要求正文不写网址")


def main() -> int:
    print("=" * 74)
    print("前端模块自测（不起服务 / 不联网）")
    print("=" * 74)
    test_assets_wiring()
    test_modules()
    test_noscroll()
    test_calc_css()
    test_load_order()
    test_layout()
    test_prompts()
    test_module_imports()
    test_js_syntax()
    print("\n" + "=" * 74)
    if FAILURES:
        print(f"❌ {len(FAILURES)} 项未通过")
        return 1
    print("✅ 全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
