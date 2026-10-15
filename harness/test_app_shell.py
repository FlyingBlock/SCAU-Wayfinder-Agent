"""单页应用装配自测：外壳 + 对话 + 计算器拼出来的那一份 HTML 是否自洽。

跑法：
    python harness/test_app_shell.py

为什么单独有这一条：`data/research/smoke_ui.py` 会用假 DOM 把整页 JS 跑一遍，
但它在跑之前自己先调了 `nav()` / `chatAsk()`，于是**加载期的接线**从来没被测到。
下面三个 bug 就是这么漏过去的：

1. `BOOT_JS` 没拼进页面 → 主页的发送键、Enter、示例问题、「只检索不生成」全都没有
   监听器：页面看着正常，点了没反应；
2. `hashNav(location.hash)` 没在加载时调 → 直接开 `/calc` 或在 `#/calc/...` 上刷新
   会停在对话视图，侧栏高亮也对不上；
3. `#appmain` 的 `noscroll` 判断写反了 → 计算器与口径说明这类普通长页面被锁住，
   鼠标滚轮怎么转都不动。

这一条只做「装配层」的确定性断言：不起服务、不联网、不依赖浏览器。
整页 JS 真正跑起来的行为仍然由 `data/research/smoke_ui.py` 覆盖。
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

from harness import app as APP                  # noqa: E402
from harness import calcpages                   # noqa: E402
from harness import prompts                     # noqa: E402
from harness.appshell import SHELL_JS           # noqa: E402

FAILURES: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(("  ✓ " if cond else "  ✗ ") + msg)
    if not cond:
        FAILURES.append(msg)


def note(msg: str) -> None:
    print("  · " + msg)


# --------------------------------------------------------------------------- #
# 装配：三段脚本 + 启动段拼成同一个 <script>
# --------------------------------------------------------------------------- #
def test_assembly() -> None:
    print("\n[装配] 三段脚本拼成一段，启动段排在最后")
    scripts = APP.view_scripts()
    page = APP.build_page()

    check(page.count("<script>\n") == 1 and page.count("\n</script>") == 1,
          "整页只有一段 <script> 元素（外壳 / 对话 / 计算器 / 启动拼在一起）")
    check("chatBind();" in APP.BOOT_JS and "hashNav(location.hash);" in APP.BOOT_JS,
          "BOOT_JS 里同时有 chatBind() 与 hashNav(location.hash)")
    check(APP.BOOT_JS in scripts, "BOOT_JS 已经拼进页面脚本")
    check(scripts.rstrip().endswith(APP.BOOT_JS.rstrip()),
          "BOOT_JS 排在整段脚本最后 —— 那时 window.__chat / __calc 才刚定义好")
    check(APP.BOOT_JS in page, "启动段出现在最终页面里")

    # 启动段是靠函数声明直接叫到它们的；换成「后面才赋值的 const 箭头函数」就废了
    check(re.search(r"function hashNav\(", SHELL_JS) is not None
          and re.search(r"function chatBind\(", APP.CHAT_JS) is not None,
          "hashNav / chatBind 都是函数声明，启动段叫得到")


# --------------------------------------------------------------------------- #
# 滚动：只有对话视图锁 #appmain，计算器 / 口径说明放它自己滚
# --------------------------------------------------------------------------- #
def test_noscroll() -> None:
    print("\n[滚动] 只有对话视图是内部滚动")
    m = re.search(r"classList\.toggle\('noscroll',\s*([^)]+?)\s*\)", SHELL_JS)
    expr = m.group(1).strip() if m else "?"
    check(expr == "VIEW === 'chat'",
          f"#appmain 只在对话视图锁滚动（现在是 {expr}）—— 反过来计算器就滚不动了")

    check('data-flex="1"' in APP.CHAT_VIEW_MARKUP,
          "对话视图标了 data-flex=1，.vflex 撑满高度、.chat-scroll 自己滚")
    check(".appmain.noscroll{overflow:hidden}" in APP.appshell.SHELL_CSS,
          "外壳 CSS 里确实有 .appmain.noscroll{overflow:hidden}")

    calc_html, docs_html = calcpages.calc_view_html(), calcpages.docs_view_html()
    for name, html in (("计算器", calc_html), ("口径说明", docs_html)):
        check("data-flex" not in html,
              f"{name}视图不标 data-flex（它要靠 #appmain 滚，不是内部滚动）")


# --------------------------------------------------------------------------- #
# 样式：计算器的 <style> 必须内联，且限定在 #view-calc 里
# --------------------------------------------------------------------------- #
def test_calc_css() -> None:
    print("\n[样式] 计算器样式内联且作用域隔离")
    calc_html = calcpages.calc_view_html()

    check("#view-calc .wrap{display:grid" in calc_html,
          "计算器样式已内联（.wrap 两栏网格生效）")
    check("#view-calc .scroll{max-height:460px" in calc_html,
          "成绩表格的滚动容器 .scroll 也在")
    check("@media (max-width:1100px){\n#view-calc .wrap{grid-template-columns:1fr}\n}"
          in calc_html,
          "@media 整块保留、里面的规则加了前缀（没被按 } 拦腰截断）")

    if "<style>" not in calc_html or "</style>" not in calc_html:
        check(False, "计算器视图里没有 <style> 段，规则级检查做不了")
        return

    i = calc_html.index("<style>") + len("<style>")
    rules = calcpages._css_rules(calc_html[i:calc_html.index("</style>", i)])
    stray = [sel for sel, _ in rules if not (sel.startswith("#view-calc") or sel.startswith("@"))]
    check(not stray, f"计算器样式没有无作用域的规则：{stray}")
    at_rules = {sel.split()[0].lower() for sel, _ in rules if sel.startswith("@")}
    check(at_rules <= {"@media", "@supports", "@keyframes"},
          f"计算器样式里的 at-rule 只有能安全保留的那几种：{sorted(at_rules)}")

    check("#view-docs .card{" in calcpages.docs_view_html(),
          "口径说明的样式仍然限定在 #view-docs")
    # 反向：原整页样式如果原样塞进来，一定会带出这些全局选择器
    for leak in ("\n.wrap{", "\n.card{", "\n.tabs{", "\nbutton{", "\ntable{"):
        check(leak not in calc_html, f"没有原样漏出全局规则 {leak.strip()!r}")


def test_scope_css() -> None:
    print("\n[样式] _scope_css 的 at-rule / 分页选择器行为")
    scoped = calcpages._scope_css(
        "@media (max-width:600px){.a{color:red} .b{color:blue}}\n"
        "@keyframes k{to{opacity:1}}\n"
        "html,body{margin:0}\n"
        "p, body{padding:0}\n"
        ":root{--x:1}\n",
        "#x")
    check("@media (max-width:600px){\n#x .a{color:red}\n#x .b{color:blue}\n}" in scoped,
          "@media 里的每条规则各自加了前缀")
    check("@keyframes k{to{opacity:1}}" in scoped,
          "@keyframes 原样保留（里面的 to/0% 不能加前缀）")
    check("html" not in scoped and ":root" not in scoped,
          "html / :root 这类页面级规则被整条丢掉")
    check("#x p{padding:0}" in scoped,
          "分页选择器里混着 body 时只丢掉那一个，其余照常加前缀")
    check(calcpages._scope_css("", "#x") == "", "空输入不炸")


# --------------------------------------------------------------------------- #
# 语法：整段脚本必须能被 JS 引擎解析（一段脚本语法错，整页就全死）
# --------------------------------------------------------------------------- #
def test_js_syntax() -> None:
    print("\n[语法] 整段脚本能被 node 解析")
    node = shutil.which("node")
    if not node:
        note("PATH 里没有 node，跳过（不影响其它检查）")
        return
    # 临时文件落在工作区根目录，不用系统临时目录：沙箱里那边的 ACL 会拒绝写
    path = ROOT / "_app_shell_syntax_check.js"
    try:
        path.write_text(APP.view_scripts(), encoding="utf-8")
    except OSError as exc:
        note(f"写不了临时文件（{exc}），跳过")
        return
    try:
        proc = subprocess.run([node, "--check", str(path)],
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=60)
        check(proc.returncode == 0,
              "node --check 通过" + ("" if proc.returncode == 0
                                     else "：" + (proc.stderr or "")[:300]))
    finally:
        try:
            path.unlink()
        except OSError:
            pass


def test_chat_sources_layout() -> None:
    print("\n[布局] 对话视图：正文 + 右侧「引用来源」栏")
    markup = APP.CHAT_VIEW_MARKUP
    for frag, why in (
        ('class="chat-main"', "正文与输入框放在 .chat-main 里（右栏不跟它们抢宽度）"),
        ('class="sources" id="sources"', "右栏 .sources 存在且带 id（脚本按 id 开关它）"),
        ('id="sources-body"', "右栏有内容容器"),
        ('id="sources-toggle"', "右栏有收起/展开按钮"),
        ('id="sources-count"', "右栏标题带条数"),
    ):
        check(frag in markup, why)
    check(".chatview{max-width:820px" in APP.appshell.SHELL_CSS
          and ".sources{flex:0 0 248px" in APP.appshell.SHELL_CSS,
          "外壳 CSS 里 .chatview 是 flex 容器、.sources 是 248px 的右栏")
    check("@media (max-width:1240px)" in APP.appshell.SHELL_CSS
          and ".sources{position:absolute" in APP.appshell.SHELL_CSS,
          "窄屏下右栏改成浮层（不挤占正文宽度）")
    # 正文里只留 [n]，网址交给右栏：这两条是本次改动的核心口径
    check("stripUrls" in APP.CHAT_JS and "data-cite=" in APP.CHAT_JS,
          "对话脚本会把正文网址收进右栏、把 [n] 渲染成可点标号")
    check("answer_delta" in APP.CHAT_JS and "answer_end" in APP.CHAT_JS,
          "对话脚本监听流式事件（answer_delta / answer_end）")
    # 提示词里不能再要求模型在文末列引用（那份列表现在由右栏负责）
    check("## 引用" not in prompts.ANSWER,
          "提示词不再要求模型输出文末「## 引用」清单")
    check("不要出现网址" in prompts.ANSWER,
          "提示词明确要求正文不写网址")


def main() -> int:
    print("=" * 74)
    print("单页应用装配自测（不起服务 / 不联网）")
    print("=" * 74)
    test_assembly()
    test_noscroll()
    test_calc_css()
    test_scope_css()
    test_chat_sources_layout()
    test_js_syntax()
    print("\n" + "=" * 74)
    if FAILURES:
        print(f"❌ {len(FAILURES)} 项未通过")
        return 1
    print("✅ 全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
