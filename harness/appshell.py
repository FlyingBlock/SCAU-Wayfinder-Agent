"""单页应用外壳：左侧边栏 + 视图路由（取代原来的「多页面 + 顶部导航」）。

为什么要把首页和计算器合成一个页面：

- 原来 `/` 是问答复用页、`/calc` 是计算器整页、`/calc-docs` 又是一整页，
  三份 HTML 各自带一套 header/nav，互相跳转要重新加载；
- 现在只留一个页面：**左侧栏列出全部可切换的入口**，
  主页对话、绩点计算器、计算器的四个子页（我的成绩 / 门槛对照 / 活动篮 / 计算口径）
  都挂在这一个侧栏上，切换是纯前端显隐，不刷新、不丢状态。

本文件只负责「外壳」：CSS 变量、侧栏结构、设置弹窗容器、视图切换与 hash 路由。
具体视图由 `harness/app.py` 组装：

- 对话视图 —— 输入框固定在底部中间、模型输出在上方（`app.CHAT_VIEW_HTML`）
- 计算器视图 —— 四个子页 + 右侧实时结果（`calcpages.calc_view_html()`）
- 口径说明 —— 原 `/calc-docs` 的正文（`calcpages.docs_view_html()`）

路由（hash 形式，刷新后停在同一个视图；服务端的 `/calc`、`/calc-docs`
返回的是同一份页面，前端再按 hash 落到对应视图，老书签不失效）：

    #/chat          主页对话
    #/calc/scores   ① 我的成绩      #/calc/goals  ② 门槛对照
    #/calc/acts     ③ 活动篮        #/calc/rules  ④ 计算口径（含数据口径说明正文）
"""
from __future__ import annotations

# --------------------------------------------------------------------------- #
# 外壳 CSS
#
# 变量沿用原来两套页面共有的那批名字（--fg/--mut/--bd/--bg/--soft/--acc …），
# 这样计算器与设置弹窗的既有样式嵌进来不用改一个字节。
# 另外补齐计算器用的 --okbg/--warnbg/--errbg/--pri，以及对话页要的
# --hover/--accbg（.pill 的色彩全靠它们）。
# --------------------------------------------------------------------------- #
SHELL_CSS = r"""
  :root{--fg:#1f2328;--mut:#656d76;--bd:#d0d7de;--bg:#ffffff;--soft:#f6f8fa;
        --hover:#eef1f4;--accbg:#eaf1fd;--accbd:#b6cffa;
        --acc:#0969da;--ok:#1a7f37;--warn:#9a6700;--err:#cf222e;--pri:#8250df;
        --okbg:#eaf7ee;--warnbg:#fdf6e3;--errbg:#fdeaea;--pribg:#f6f0ff;
        --sb:#f9fafb;--active:#e8eefc;--sw:248px}
  *{box-sizing:border-box}
  html,body{height:100%}
  body{margin:0;font:14.5px/1.6 -apple-system,"Segoe UI","Microsoft YaHei",sans-serif;
       color:var(--fg);background:var(--bg)}
  .plan{display:flex;height:100vh;overflow:hidden}
  .plan.hide{display:none!important}
  .hide{display:none!important}

  /* ============================ 左侧边栏 ============================ */
  .sidebar{width:var(--sw);flex:0 0 var(--sw);height:100%;background:var(--sb);
           border-right:1px solid var(--bd);display:flex;flex-direction:column;
           transition:width .18s ease,flex-basis .18s ease;overflow:hidden}
  .side-top{display:flex;align-items:center;gap:9px;padding:13px 14px 11px;
            border-bottom:1px solid var(--bd)}
  .menu-btn{flex:0 0 auto;width:30px;height:30px;padding:0;border:1px solid transparent;background:none;
            color:var(--mut);cursor:pointer;border-radius:7px;display:flex;align-items:center;
            justify-content:center;font-size:15px}
  .menu-btn:hover{background:var(--hover);color:var(--fg)}
  .brand{font-weight:650;font-size:14.5px;white-space:nowrap;flex:1;min-width:0;overflow:hidden;
         text-overflow:ellipsis}
  .side-nav{flex:1;overflow-y:auto;padding:9px 10px 14px}
  .nv-group{margin:10px 0 5px;padding:0 9px;font-size:11.5px;font-weight:700;color:var(--mut);
            letter-spacing:.06em;white-space:nowrap}
  .nv-group:first-child{margin-top:2px}
  .side-nav a{display:flex;align-items:center;gap:9px;padding:8px 9px;border-radius:8px;
              color:var(--fg);text-decoration:none;font-size:13.5px;margin:1px 0;cursor:pointer;
              white-space:nowrap;overflow:hidden}
  .side-nav a .ic{flex:0 0 20px;width:20px;text-align:center;font-size:14.5px}
  .side-nav a .lb{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis}
  .side-nav a:hover{background:var(--hover)}
  .side-nav a.on{background:var(--active);color:var(--acc);font-weight:650}
  .side-nav a.sub{padding-left:14px;font-size:13px}
  .side-nav a.sub .ic{width:16px;flex-basis:16px;font-size:11px;color:var(--mut);
                      font-family:ui-monospace,Consolas,monospace}
  .side-nav a.sub.on .ic{color:var(--acc)}
  .side-bot{border-top:1px solid var(--bd);padding:9px 10px;display:flex;flex-direction:column;gap:2px}
  .side-btn{display:flex;align-items:center;gap:9px;width:100%;text-align:left;background:none;
            border:0;color:var(--fg);padding:8px 9px;border-radius:8px;font:inherit;font-size:13.5px;
            cursor:pointer;white-space:nowrap}
  .side-btn:hover{background:var(--hover)}
  .side-btn .ic{flex:0 0 20px;text-align:center}
  .side-foot{padding:7px 15px 11px;font-size:11px;color:var(--mut);white-space:nowrap;
             border-top:1px solid var(--bd)}
  /* 收起态：只留图标 */
  .sidebar.closed{width:56px;flex-basis:56px}
  .sidebar.closed .brand,.sidebar.closed .nv-group,.sidebar.closed .side-nav a .lb,
  .sidebar.closed .side-btn .lb,.sidebar.closed .side-foot{display:none}
  .sidebar.closed .side-top{justify-content:center;padding:13px 0 11px}
  .sidebar.closed .side-nav a,.sidebar.closed .side-btn{justify-content:center;padding:8px 0}
  @media (max-width:820px){
    .sidebar{position:fixed;z-index:40;left:0;top:0;bottom:0;width:262px;flex-basis:262px;
             box-shadow:0 0 0 100vmax rgba(31,35,40,.35)}
    .sidebar.closed{width:262px;flex-basis:262px;
                    box-shadow:0 0 0 100vmax rgba(31,35,40,.35)}
    .sidebar.closed .brand,.sidebar.closed .nv-group,.sidebar.closed .side-nav a .lb,
    .sidebar.closed .side-btn .lb,.sidebar.closed .side-foot{display:revert}
    .sidebar.closed .side-top{justify-content:flex-start;padding:13px 14px 11px}
    .sidebar.closed .side-nav a,.sidebar.closed .side-btn{justify-content:flex-start;padding:8px 9px}
    .sidebar.closed .side-nav a.sub{padding-left:14px}
    .sidebar.mob-hide{transform:translateX(-100%);box-shadow:none}
  }
  .appmain{flex:1;min-width:0;min-height:0;overflow-y:auto;background:var(--soft)}
  .appmain.noscroll{overflow:hidden}
  .view{display:none}
  .view.on{display:block}
  .view.on.vflex{display:flex;flex-direction:column;height:100%}
  .vwrap{max-width:1000px;margin:0 auto;padding:20px}

  /* ============================ 主页对话 ============================ */
  /* 参考 chat.deepseek.com：输出在上方（可滚动），输入框固定在正文列底部中间。
     右边再挂一栏「引用来源」——正文里只留 [n] 标号，链接全部收在右栏。 */
  /* .chatview 铺满整个主区（不再把「正文 + 右栏」整块封在 820px 里居中）：
     正文列（.chat-inner / .composer .inner / .chat-top .pills，上限都是 760px）
     在「主区宽度 − 右栏」里居中，右栏则一直贴在主区最右边，也就是窗口最右边。
     所以宽屏上右栏占的是正文两侧本来就空着的留白，正文列一分宽度都没少；
     只有主区连「正文 800 + 右栏 248」都放不下时才改成浮层（见下面的 @media）。 */
  .chatview{width:100%;display:flex;height:100%;position:relative}
  .chat-main{flex:1;min-width:0;display:flex;flex-direction:column;height:100%}
  .chat-scroll{flex:1;min-height:0;overflow-y:auto;padding:26px 20px 8px}
  .chat-inner{max-width:760px;margin:0 auto}
  .chat-empty{padding:5vh 4px 22px;text-align:center;color:var(--mut)}
  .chat-empty h2{font-size:25px;color:var(--fg);margin:0 0 8px;font-weight:650}
  .chat-empty .sub2{font-size:13.5px;margin-bottom:20px}
  .chat-sugs{display:flex;gap:9px;flex-wrap:wrap;justify-content:center}
  .sug{border:1px solid var(--bd);background:var(--bg);border-radius:99px;padding:7px 14px;
       font-size:13px;color:var(--fg);cursor:pointer}
  .sug:hover{border-color:var(--accbd);background:var(--accbg);color:var(--acc)}
  .msgs{display:flex;flex-direction:column;gap:16px}
  .msg-u{display:flex;justify-content:flex-end}
  .msg-u .bub{background:var(--accbg);border:1px solid var(--accbd);border-radius:14px;
              padding:9px 14px;max-width:84%;white-space:pre-wrap;word-break:break-word}
  .msg-a{display:flex;gap:11px;align-items:flex-start}
  .av{flex:0 0 28px;width:28px;height:28px;border-radius:50%;background:var(--soft);
      border:1px solid var(--bd);display:flex;align-items:center;justify-content:center;font-size:15px}
  .ans{flex:1;min-width:0;padding-top:2px;overflow-wrap:break-word;word-break:break-word}
  .ans>*:first-child{margin-top:0}
  .ans h2,.ans h3{font-size:15.5px;margin:18px 0 6px;padding-bottom:5px;border-bottom:1px solid var(--bd)}
  .ans table{border-collapse:collapse;margin:10px 0;font-size:13.5px;display:block;overflow-x:auto}
  .ans th,.ans td{border:1px solid var(--bd);padding:6px 10px;text-align:left}
  .ans th{background:var(--soft)}
  .ans code{background:var(--soft);padding:1px 5px;border-radius:4px;font-size:12.5px}
  .ans a{color:var(--acc)}
  .ans .err-line{margin-top:10px}
  /* 正文里的 [n]：只留标号，链接点开是右栏那条来源 */
  a.cite{color:var(--acc);cursor:pointer;text-decoration:none;font-size:11.5px;
         padding:0 1px;vertical-align:super;line-height:1;font-family:ui-monospace,Consolas,monospace}
  a.cite:hover{text-decoration:underline;background:var(--accbg);border-radius:3px}
  a.cite.miss{color:var(--mut);text-decoration:none;cursor:default}
  /* 流式输出时的光标 */
  .cursor{display:inline-block;width:7px;height:1em;background:var(--acc);
          vertical-align:-2px;margin-left:1px;animation:blink 1s steps(2,start) infinite}
  @keyframes blink{to{visibility:hidden}}
  /* 正文里出现过的网址被收进右栏后留下的提示（点击展开右栏） */
  .ans .url-strip{font-size:12px;color:var(--mut);background:var(--soft);
                  border:1px dashed var(--bd);border-radius:7px;padding:5px 9px;margin:8px 0;cursor:pointer}
  .ans .url-strip b{color:var(--acc);font-weight:600}
  .chat-trace{margin-top:16px;font:12.5px/1.7 ui-monospace,Consolas,monospace;color:var(--mut);
              white-space:pre-wrap;background:var(--soft);border:1px solid var(--bd);
              border-radius:8px;padding:10px;max-height:210px;overflow:auto}
  .chat-trace summary{cursor:pointer;font-weight:600}

  /* ---------- 右侧「引用来源」栏 ---------- */
  .sources{flex:0 0 248px;width:248px;display:flex;flex-direction:column;min-height:0;
           border-left:1px solid var(--bd);background:var(--bg)}
  .sources-head{flex:0 0 auto;display:flex;align-items:center;gap:7px;padding:13px 12px 11px;
                border-bottom:1px solid var(--bd)}
  .sources-head .t{flex:1;min-width:0;font-weight:650;font-size:13.5px;white-space:nowrap;
                   overflow:hidden;text-overflow:ellipsis}
  .sources-head .n{font-weight:400;color:var(--mut);font-size:12px}
  .src-toggle{flex:0 0 auto;width:26px;height:26px;padding:0;border:1px solid transparent;
              background:none;color:var(--mut);border-radius:7px;cursor:pointer;font-size:13px;
              display:flex;align-items:center;justify-content:center}
  .src-toggle:hover{background:var(--hover);color:var(--fg)}
  .sources-body{flex:1;min-height:0;overflow-y:auto;padding:9px 11px}
  .sources-foot{flex:0 0 auto;border-top:1px solid var(--bd);padding:7px 11px;font-size:11px;
                color:var(--mut);line-height:1.5}
  .src-sec{margin:2px 0 8px;font-size:11.5px;font-weight:700;color:var(--mut);letter-spacing:.05em}
  .src-grp{margin:9px 0;display:flex;flex-direction:column;gap:5px}
  .src-item{border:1px solid var(--bd);border-left:3px solid var(--acc);border-radius:8px;
            padding:7px 9px;background:var(--bg);font-size:12.5px;line-height:1.5}
  .src-item.web{border-left-color:var(--pri)}
  .src-item.stale{border-left-color:var(--warn)}
  .src-item.hit{border-left-color:var(--ok)}
  .src-item.ghost{border-left-color:var(--bd);color:var(--mut)}
  .src-item .h{display:flex;gap:6px;align-items:baseline}
  .src-item .idx{flex:0 0 auto;font-weight:700;color:var(--acc);
                 font-family:ui-monospace,Consolas,monospace}
  .src-item .ti{flex:1;min-width:0;font-weight:600;word-break:break-word}
  .src-item .mt{color:var(--mut);font-size:11.5px;margin-top:3px;word-break:break-word}
  .src-item .lk{display:block;margin-top:4px;color:var(--acc);text-decoration:none;
                font-size:11.5px;word-break:break-all}
  .src-item .lk:hover{text-decoration:underline}
  .src-item .chips{display:flex;gap:4px;flex-wrap:wrap;margin-top:4px}
  .src-trace{margin:6px 0 0;padding:7px 8px;background:var(--soft);border:1px solid var(--bd);
             border-radius:7px;font:11.5px/1.6 ui-monospace,Consolas,monospace;color:var(--mut);
             white-space:pre-wrap;word-break:break-word;max-height:190px;overflow:auto}
  /* 检索命中列表里的 [n]：不画成链接，链接在右栏 */
  .ans .hit .src-n{margin-left:6px;color:var(--acc);font-size:11.5px;
                   font-family:ui-monospace,Consolas,monospace}
  .sources.closed{flex-basis:44px;width:44px}
  .sources.closed .sources-body,.sources.closed .sources-foot,.sources.closed .sources-head .t,
  .sources.closed .src-sec,.sources.closed .src-grp{display:none}
  .sources.closed .sources-head{flex-direction:column;gap:6px;padding:11px 0}
  .sources.closed .src-toggle{transform:rotate(180deg)}
  .sources.closed .sources-head .rlb{writing-mode:vertical-rl;font-size:11.5px;color:var(--mut);
                                     letter-spacing:.12em}
  .sources-head .rlb{display:none}
  .sources.closed .sources-head .rlb{display:block}
  /* 并排放不下时（主区 < 正文 800 + 右栏 248 = 1048px）：右栏改成浮在正文之上，不再占一列。
     主区宽度 = 窗口宽 − 左侧栏（展开 248 / 收起 56），所以这段按窗口宽写：
     左侧栏展开时窗口 ≤1295 就放不下了；左侧栏收起后少占 192px，窗口 ≥1104 仍然放得下。 */
  @media (max-width:1295px){
    .sources{position:absolute;right:0;top:0;bottom:0;z-index:20;width:266px;flex-basis:266px;
             border-left:1px solid var(--bd);box-shadow:-10px 0 26px rgba(31,35,40,.13)}
    .sources.closed{width:44px;flex-basis:44px;box-shadow:none}
  }
  /* 左侧栏收起时的补偿：这条选择器比上面那段更具体，会把浮层规则盖回「一列」，
     于是收起了左侧栏的窗口从 1104px 起右栏就照旧并排贴右。
     口径与对话脚本里的 sourcesInline()（门槛 1048px）一致。 */
  @media (min-width:1104px){
    .sidebar.closed ~ .appmain .sources{position:static;right:auto;top:auto;bottom:auto;z-index:auto;
             width:248px;flex-basis:248px;box-shadow:none}
    .sidebar.closed ~ .appmain .sources.closed{width:44px;flex-basis:44px}
  }
  /* ---------- 对话里的卡片（活动/赛事 · 附件 · 关键时间） ---------- */
  .cards-wrap{margin-top:16px}
  .cards-head{display:flex;align-items:center;gap:8px;font-size:13px;font-weight:650;
              color:var(--mut);padding-bottom:7px;border-bottom:1px solid var(--bd)}
  .cards-head .n{font-weight:400}
  .cards-grid{display:grid;gap:10px;margin-top:10px;
              grid-template-columns:repeat(auto-fill,minmax(300px,1fr))}
  .acard{border:1px solid var(--bd);border-left:3px solid var(--acc);border-radius:10px;
         padding:11px 13px;background:var(--bg);display:flex;flex-direction:column;gap:5px}
  .acard.file{border-left-color:var(--warn)}
  .acard.unmatched{border-left-color:var(--bd)}
  .acard .hd{display:flex;gap:7px;align-items:baseline;flex-wrap:wrap}
  .acard .nm{font-weight:650;word-break:break-word}
  .acard .meta{font-size:12.5px;color:var(--mut);line-height:1.55}
  .acard .meta b{color:var(--fg);font-weight:600}
  .acard .chips{display:flex;gap:5px;flex-wrap:wrap}
  .acard .scores{display:flex;flex-direction:column;gap:3px;font-size:12.5px}
  .acard .srow{display:flex;align-items:baseline;gap:6px}
  .acard .srow .lb{color:var(--mut);flex:0 0 62px}
  .acard .srow .ach{color:var(--fg);flex:1;min-width:0}
  .acard .foot{display:flex;align-items:center;gap:8px;margin-top:auto;
               padding-top:8px;border-top:1px dashed var(--bd);flex-wrap:wrap}
  .acard .foot .src{font-size:11.5px;color:var(--mut);flex:1;min-width:120px;
                    overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .acard .foot button{font-size:12.5px;padding:5px 12px;border-radius:7px}
  .acard .why{font-size:11.5px;color:var(--warn);background:var(--warnbg);
              border:1px solid #eeddaa;border-radius:7px;padding:6px 8px}
  .chipm{font-size:11.5px;padding:1px 7px;border-radius:99px;border:1px solid var(--bd);
         background:var(--soft);color:var(--mut);white-space:nowrap}
  .tierx{font-weight:700;font-size:11.5px;padding:1px 8px;border-radius:99px}
  .tierx.T{color:var(--err);border:1px solid #f3c0c0;background:var(--errbg)}
  .tierx.A{color:var(--warn);border:1px solid #eeddaa;background:var(--warnbg)}
  .tierx.B{color:var(--ok);border:1px solid #b7e0c2;background:var(--okbg)}
  .pill.mini{font-size:11.5px;padding:1px 8px}
  .cnt{display:inline-block;min-width:16px;padding:0 5px;border-radius:99px;
       background:var(--acc);color:#fff;font-size:11px;text-align:center}
  .toast{position:fixed;left:50%;transform:translateX(-50%);bottom:26px;z-index:80;
         background:var(--fg);color:#fff;border-radius:99px;padding:9px 18px;font-size:13px;
         box-shadow:0 6px 20px rgba(31,35,40,.28);opacity:0;transition:opacity .18s}
  .toast.on{opacity:1}
  .toast a{color:#9fc7ff;cursor:pointer;text-decoration:underline dotted;margin-left:6px}
  /* 附件解析正文弹窗（卡片上的「看解析正文」） */
  .acard .why.ok{color:var(--ok);background:var(--okbg);border-color:#b7e0c2}
  .acard .why .lnk,.att-hd .lnk{color:var(--acc);cursor:pointer;text-decoration:underline dotted}
  .acard .att-prev{max-height:74px;overflow:hidden;
                   -webkit-mask-image:linear-gradient(#000 60%,transparent);
                   mask-image:linear-gradient(#000 60%,transparent)}
  .att-modal{position:fixed;inset:0;z-index:70;background:rgba(31,35,40,.45);
             display:flex;justify-content:center;align-items:flex-start;padding:44px 16px;overflow:auto}
  .att-box{background:var(--bg);border:1px solid var(--bd);border-radius:12px;
           width:100%;max-width:760px;padding:16px 18px;box-shadow:0 14px 38px rgba(31,35,40,.22)}
  .att-hd{display:flex;gap:10px;align-items:baseline;margin-bottom:8px;flex-wrap:wrap}
  .att-text{white-space:pre-wrap;word-break:break-word;font:12.5px/1.75 ui-monospace,Consolas,monospace;
            background:var(--soft);border:1px solid var(--bd);border-radius:8px;
            padding:11px 13px;max-height:56vh;overflow:auto;margin:8px 0}
  .att-box .foot{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
  /* 底部输入条：主输入框居中、贴底、圆角 */
  .chat-top{padding:10px 20px 2px}
  .chat-top .pills{max-width:760px;margin:0 auto;justify-content:flex-end}
  .composer{padding:8px 20px 20px;background:linear-gradient(to top,var(--soft) 62%,transparent)}
  .composer .inner{max-width:760px;margin:0 auto}
  .cbox{display:flex;align-items:flex-end;gap:8px;background:var(--bg);border:1px solid var(--bd);
        border-radius:16px;padding:9px 9px 9px 15px;box-shadow:0 2px 10px rgba(31,35,40,.07)}
  .cbox:focus-within{border-color:var(--accbd);box-shadow:0 3px 14px rgba(9,105,218,.15)}
  .cbox textarea{flex:1;min-height:26px;max-height:190px;border:0;outline:0;resize:none;
                 font:inherit;line-height:1.55;padding:5px 0;background:transparent;color:var(--fg)}
  .send{flex:0 0 auto;width:34px;height:34px;border-radius:50%;padding:0;display:flex;
        align-items:center;justify-content:center;font-size:15px;line-height:1}
  .send:disabled{opacity:.4;cursor:not-allowed}
  .crow{display:flex;align-items:center;gap:12px;margin-top:8px;font-size:12.5px;color:var(--mut);
        flex-wrap:wrap;padding:0 5px}
  .crow label{display:flex;align-items:center;gap:4px;cursor:pointer}
  .crow select{font-size:12px;padding:1px 4px;border:1px solid var(--bd);border-radius:5px;
               background:var(--bg);color:var(--fg)}
  #find{background:none;border:0;padding:0;color:var(--acc);font:inherit;cursor:pointer;
        text-decoration:underline dotted}
  #find:disabled{color:var(--mut);cursor:not-allowed}
  .composer .ex{cursor:pointer;text-decoration:underline dotted}
  .composer .ex:hover{color:var(--acc)}

  /* ============================ 通用小件 ============================ */
  .pills{display:flex;gap:7px;flex-wrap:wrap;font-size:12.5px}
  .pill{background:var(--soft);border:1px solid var(--bd);border-radius:99px;padding:3px 11px;
        color:var(--mut)}
  .pill.ok{color:var(--ok);border-color:#b7e0c2;background:var(--okbg)}
  .pill.warn{color:var(--warn);border-color:#eeddaa;background:var(--warnbg)}
  .pill.err{color:var(--err);border-color:#f3c0c0;background:var(--errbg)}
  .pill.pri{color:var(--pri);border-color:#d8c7f5;background:var(--pribg)}
  .hit{border-top:1px solid var(--bd);padding:11px 0}
  .hit:first-of-type{border-top:0}
  .hit .t{font-weight:600}
  .hit .m{font-size:12.5px;color:var(--mut);margin:3px 0}
  .hit .s{font-size:13.5px;color:#424a53}
  .spin{display:inline-block;width:12px;height:12px;border:2px solid var(--bd);
        border-top-color:var(--acc);border-radius:50%;animation:r .8s linear infinite;vertical-align:-1px}
  @keyframes r{to{transform:rotate(360deg)}}
  .small{font-size:12.5px;color:var(--mut)}
  .mono{font-family:ui-monospace,Consolas,monospace}

  /* ============================ ⚙️ 设置弹窗 ============================ */
  .bd{position:fixed;inset:0;background:rgba(31,35,40,.45);z-index:50;overflow:auto;
      padding:52px 16px;display:flex;justify-content:center;align-items:flex-start}
  .modal{background:var(--bg);border:1px solid var(--bd);border-radius:12px;padding:20px 22px;
         width:100%;max-width:580px;box-shadow:0 14px 38px rgba(31,35,40,.22)}
  .modal h2{font-size:16px;margin:0 0 6px;font-weight:650}
  .modal .fld{margin-top:13px}
  .modal .fld label{display:block;font-size:12.5px;color:var(--mut);margin-bottom:4px}
  .modal input{width:100%;padding:8px 10px;border:1px solid var(--bd);border-radius:8px;font:inherit}
  .modal input:focus{outline:2px solid var(--accbd);outline-offset:-1px;border-color:var(--acc)}
  .presets{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px}
  .presets button{background:var(--soft);color:var(--fg);border:1px solid var(--bd);
                  border-radius:99px;padding:3px 10px;font-size:12.5px;font-weight:500}
  .msg{font-size:13px;margin-top:13px;padding:9px 11px;border-radius:8px;
       border:1px solid var(--bd);background:var(--soft);word-break:break-word}
  .msg.ok{color:var(--ok);border-color:#b7e0c2;background:var(--okbg)}
  .msg.err{color:var(--err);border-color:#f3c0c0;background:var(--errbg)}
  .msg.warn{color:var(--warn);border-color:#eeddaa;background:var(--warnbg)}
  .msg .lnk{color:var(--acc);cursor:pointer;text-decoration:underline dotted}
  .row{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
  .set-tabs{display:flex;gap:6px;margin-bottom:12px;border-bottom:1px solid var(--bd);
            padding-bottom:8px}
  .set-tabs button{background:transparent;color:var(--mut);border:1px solid transparent;
                   border-radius:99px;padding:4px 12px;font-size:13px;font-weight:600}
  .set-tabs button.on{background:var(--soft);color:var(--fg);border-color:var(--bd)}
  .modal select{width:100%;padding:8px 10px;border:1px solid var(--bd);border-radius:8px;
                font:inherit;background:var(--bg);color:var(--fg)}
  .modal .chk{display:flex;gap:8px;align-items:center;font-size:12.5px;color:var(--mut);
              margin-top:12px}
  .modal .chk input{width:auto}
  button{background:var(--acc);color:#fff;border:0;border-radius:8px;padding:8px 16px;font:inherit;
         font-weight:600;cursor:pointer}
  button.ghost{background:var(--bg);color:var(--fg);border:1px solid var(--bd);font-weight:500}
  button:disabled{opacity:.5;cursor:not-allowed}
"""

# 侧栏导航：(hash, data-view, data-sub, 图标, 文字, 是否子项)
NAV_ITEMS: list[tuple[str, str, str, str, str, bool]] = [
    ("#/chat", "chat", "", "💬", "主页对话", False),
    ("#/calc/scores", "calc", "scores", "📊", "绩点计算器", False),
    ("#/calc/scores", "calc", "scores", "①", "我的成绩", True),
    ("#/calc/goals", "calc", "goals", "②", "门槛对照", True),
    ("#/calc/acts", "calc", "acts", "③", "活动篮", True),
    ("#/calc/rules", "calc", "rules", "④", "计算口径", True),
]


def nav_html() -> str:
    """侧栏导航（分组标签 + 各视图入口）。"""
    out: list[str] = ['<div class="nv-group">对话与计算</div>']
    for i, (href, view, sub, icon, label, is_sub) in enumerate(NAV_ITEMS):
        if i == 2:                       # 计算器的子页单独分一组
            out.append('<div class="nv-group">绩点计算器</div>')
        cls = ' class="sub"' if is_sub else ""
        out.append(
            f'<a href="{href}"{cls} data-view="{view}" data-sub="{sub}">'
            f'<span class="ic">{icon}</span><span class="lb">{label}</span></a>'
        )
    return "\n    ".join(out)


# --------------------------------------------------------------------------- #
# 外壳标记：侧栏 + 视图容器 + 设置弹窗
#
# 视图内容（对话页 / 计算器 / 口径说明）由 app.BUILD_PAGE() 用 {{...}} 填进来，
# 所以这里用 replace 而不是 format —— 视图里满地都是 `{`、`}`（CSS 与 JS 模板串）。
# --------------------------------------------------------------------------- #
SHELL_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SCAU 学生发展信息 Harness</title>
<style>
__SHELL_CSS__
</style>
</head>
<body>
<div class="plan" id="plan">

  <aside class="sidebar" id="sidebar">
    <div class="side-top">
      <button class="menu-btn" id="menu-btn" type="button" title="收起 / 展开侧边栏">☰</button>
      <div class="brand">🌾 SCAU Harness</div>
    </div>
    <nav class="side-nav" id="side-nav">
    __NAV__
    </nav>
    <div class="side-bot">
      <button type="button" class="side-btn" id="settings-btn"
              title="模型 / 附件与 OCR / 账号与登录">
        <span class="ic">⚙️</span><span class="lb">设置</span></button>
      <a class="side-btn" id="side-docs" href="#/calc/rules"
         title="计算器数据口径说明（④ 计算口径 里也有）">
        <span class="ic">📐</span><span class="lb">数据口径说明</span></a>
    </div>
    <div class="side-foot">华南农业大学 · 本地运行</div>
  </aside>

  <div class="appmain" id="appmain">
__VIEWS__
  </div>
</div>

<!-- ===================== ⚙️ 设置：模型 + 附件/OCR ===================== -->
<div class="bd hide" id="set-bd">
  <div class="modal" role="dialog" aria-modal="true" aria-labelledby="set-title">
    <div class="set-tabs">
      <button type="button" class="on" data-tab="llm">🧠 模型</button>
      <button type="button" data-tab="ocr">🖼 附件与 OCR</button>
      <button type="button" data-tab="auth">🔐 账号与登录</button>
    </div>

    <section id="set-pane-llm">
    <h2 id="set-title">🧠 模型设置</h2>
    <div class="small">任何 <b>OpenAI 兼容</b>端点都能接：填 base URL、模型名、API key。
      保存后立即生效，同时写入仓库根的 <span class="mono">.env</span>（下次启动仍然有效）。</div>

    <div class="presets" id="set-presets"></div>

    <div class="fld">
      <label for="set-base">Base URL（OpenAI 兼容端点，不含 /chat/completions）</label>
      <input id="set-base" type="text" spellcheck="false" autocomplete="off"
             placeholder="https://api.deepseek.com">
    </div>
    <div class="fld">
      <label for="set-model">模型名称</label>
      <input id="set-model" type="text" spellcheck="false" autocomplete="off"
             placeholder="deepseek-chat">
    </div>
    <div class="fld">
      <label for="set-key">API Key</label>
      <input id="set-key" type="password" spellcheck="false" autocomplete="new-password"
             placeholder="sk-…">
    </div>

    <div class="msg hide" id="set-msg"></div>

    <div class="row" style="margin-top:14px">
      <button id="set-save">保存并验证</button>
      <button class="ghost" id="set-test">测试连接</button>
      <button class="ghost" id="set-close">关闭</button>
      <span class="small" id="set-file" style="margin-left:auto"></span>
    </div>
    <div class="small" style="margin-top:10px">
      命令行等价写法：<span class="mono">python -m harness.cli setup-key</span>
    </div>
    </section>

    <section id="set-pane-ocr" class="hide">
    <h2>🖼 附件与 OCR</h2>
    <div class="small">通知的 <span class="mono">.pdf / .doc / .docx / .xls / .xlsx / .ppt / 压缩包</span>
      会被自动下载到项目内的 <span class="mono" id="ocr-dir">data/attachments/</span> 并抽出正文与表格，
      正文参与检索与回答。图片、扫描件里的文字需要 OCR —— 填百度智能云的
      <b>API Key / Secret Key</b>（要开通「通用文字识别」）即可，不填则跳过图片文字。</div>

    <div class="fld">
      <label for="ocr-provider">OCR 服务商</label>
      <select id="ocr-provider">
        <option value="none">不启用（图片里的文字不提取）</option>
        <option value="baidu">百度智能云 OCR</option>
      </select>
    </div>
    <div class="fld">
      <label for="ocr-key">百度 OCR API Key（AK）</label>
      <input id="ocr-key" type="password" spellcheck="false" autocomplete="new-password"
             placeholder="控制台「应用列表」里的 API Key">
    </div>
    <div class="fld">
      <label for="ocr-secret">百度 OCR Secret Key（SK）</label>
      <input id="ocr-secret" type="password" spellcheck="false" autocomplete="new-password"
             placeholder="与 AK 成对出现">
    </div>
    <label class="chk"><input type="checkbox" id="ocr-accurate" checked>
      用高精度版（<span class="mono">accurate_basic</span>，免费额度更少但更准）</label>
    <div class="small" id="ocr-hint" style="margin-top:6px"></div>
    <div class="small" id="ocr-astat" style="margin-top:6px"></div>

    <div class="msg hide" id="ocr-msg"></div>

    <div class="row" style="margin-top:14px">
      <button id="ocr-save">保存并验证</button>
      <button class="ghost" id="ocr-test">测试识别</button>
      <button class="ghost" id="ocr-clear">清除凭据</button>
      <button class="ghost" id="ocr-close">关闭</button>
    </div>
    <div class="small" style="margin-top:10px">
      命令行等价写法：<span class="mono">python -m harness.cli ocr --api-key … --secret-key …</span>
      ｜ 重新解析已有附件：<span class="mono">python -m harness.cli attach --all</span>
    </div>
    </section>

    <section id="set-pane-auth" class="hide">
    <h2>🔐 账号与登录</h2>
    <div class="small">校内有一部分栏目在<b>统一身份认证</b>（CAS）后面。在这里填一次学号与密码，
      之后抓取撞到登录墙会<b>自动登录</b>；登录页有图形验证码时，脚本会把验证码图下载下来交给
      <b>OCR</b> 识别再填回去，认错就换一张重试。<br>
      凭据只落在本机 <span class="mono">.auth/</span>（已 gitignore、权限收紧到当前用户），
      <b>不进 <span class="mono">.env</span>、不进日志、不发模型</b>。
      滑块 / 短信 / 双因子这类交互式验证脚本过不去，那种站点请用 Cookie 导入。</div>

    <div class="fld">
      <label for="auth-user">学号 / 工号</label>
      <input id="auth-user" type="text" spellcheck="false" autocomplete="username"
             placeholder="2023xxxxxxxx">
    </div>
    <div class="fld">
      <label for="auth-pass">统一身份认证密码</label>
      <input id="auth-pass" type="password" spellcheck="false" autocomplete="new-password"
             placeholder="留空表示不改动已保存的密码">
    </div>
    <div class="fld">
      <label for="auth-service">登录后跳转的目标地址（service，一般不用改）</label>
      <input id="auth-service" type="text" spellcheck="false" autocomplete="off"
             placeholder="http://portal.scau.edu.cn/">
    </div>
    <div class="fld">
      <label for="auth-captcha-url">验证码图片地址（可选：登录页里自动找不到时才手填）</label>
      <input id="auth-captcha-url" type="text" spellcheck="false" autocomplete="off"
             placeholder="留空 = 自动在登录页里找">
    </div>
    <div class="fld" style="max-width:220px">
      <label for="auth-rounds">验证码最多换几张图重试</label>
      <input id="auth-rounds" type="number" min="1" max="8" step="1" value="3">
    </div>

    <label class="chk"><input type="checkbox" id="auth-save-pw" checked>
      把密码存到本地（不勾选则只在这次登录用，采集时没法自动登录）</label>
    <label class="chk"><input type="checkbox" id="auth-auto" checked>
      抓取撞到登录墙时自动登录（<span class="mono">AUTH_AUTO_LOGIN</span>）</label>
    <label class="chk"><input type="checkbox" id="auth-ocr" checked>
      验证码用 OCR 识别（<span class="mono">AUTH_OCR_CAPTCHA</span>，需要先配好 OCR）</label>
    <div class="small" id="auth-ocr-hint" style="margin-top:6px"></div>
    <div class="small" id="auth-stat" style="margin-top:6px"></div>

    <div class="msg hide" id="auth-msg"></div>

    <div class="hide" id="auth-cap-wrap"
         style="margin-top:12px;padding:10px;border:1px solid var(--bd);border-radius:8px">
      <div class="small">OCR 没认出这张验证码 —— 照着图填一次就能继续（不填也行，点「换一张」再让 OCR 试）：</div>
      <img id="auth-cap-img" alt="验证码" style="display:block;margin:8px 0;max-width:200px;
           border:1px solid var(--bd);border-radius:6px;background:#fff">
      <div class="row">
        <input id="auth-cap-text" type="text" spellcheck="false" autocomplete="off"
               placeholder="验证码" style="width:150px">
        <button id="auth-cap-go">提交验证码</button>
        <button class="ghost" id="auth-cap-retry">换一张</button>
      </div>
    </div>

    <div class="row" style="margin-top:14px">
      <button id="auth-save">保存并登录</button>
      <button class="ghost" id="auth-save-only">只保存，不登录</button>
      <button class="ghost" id="auth-clear">清除凭据</button>
      <button class="ghost" id="auth-logout">退出登录</button>
      <button class="ghost" id="auth-close">关闭</button>
    </div>
    <div class="row" style="margin-top:8px">
      <span class="small" id="auth-file" style="margin-left:0"></span>
    </div>
    <div class="small" style="margin-top:10px">
      命令行等价写法：<span class="mono">python -m harness.cli login</span>
      ｜ 不用密码（CAS 有滑块时用这个）：<span class="mono">python -m harness.cli login --cookie</span>
      ｜ 看当前会话：<span class="mono">python -m harness.cli whoami</span>
    </div>
    </section>
  </div>
</div>
<!-- ===================== 轻提示（加入活动篮 / 附件下载） ===================== -->
<div class="toast" id="toast"></div>
</body>
</html>
"""


def shell_html(nav: str, views_html: str) -> str:
    """把侧栏导航与各视图容器填进外壳。"""
    return (SHELL_HTML
            .replace("__SHELL_CSS__", SHELL_CSS)
            .replace("__NAV__", nav)
            .replace("__VIEWS__", views_html))


# --------------------------------------------------------------------------- #
# 外壳脚本：视图切换 + hash 路由 + 侧栏开合 + 示例问题
#
# 视图的真实渲染逻辑分在两个脚本里（对话页脚本、计算器脚本），它们都由
# app.BUILD_PAGE() 追加在外壳脚本**之后**，所以这里只做「切到哪个视图」，
# 需要某个视图自己的数据时才调用 window.__chat / window.__calc。
# --------------------------------------------------------------------------- #
SHELL_JS = r"""
/* ===================== 公共小工具 ===================== */
/* 外壳、对话页、计算器脚本最终拼进同一个 <script>，所以这几个名字只声明一次，放在最前面。
   （计算器那一份被 IIFE 包住，用的是它自己的 $ / esc，互不影响。） */
const $ = s => document.querySelector(s);
const $$ = s => Array.from(document.querySelectorAll(s));
const esc = s => String(s==null?'':s).replace(/[&<>"]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

/* ===================== 视图切换与 hash 路由 ===================== */
const SUBS = { scores:'tab-profile', goals:'tab-goals', acts:'tab-acts', rules:'tab-rules' };
const SUB_KEY = { 'tab-profile':'scores', 'tab-goals':'goals', 'tab-acts':'acts', 'tab-rules':'rules' };
const TITLES = { chat:'主页对话', calc:'绩点 / 综测计算器', docs:'数据口径说明' };
let VIEW = 'chat', SUB = 'scores';

function setSidebar(open){
  const sb = $('#sidebar');
  sb.classList.toggle('closed', !open);
  try{ localStorage.setItem('scau-side', open ? '1' : '0'); }catch(e){}
}
function sidebarOpen(){
  try{ return localStorage.getItem('scau-side') !== '0'; }catch(e){ return true; }
}
function renderSub(){
  const label = $('#sub-label');
  const on = SUB_KEY[SUB] || (SUBS[SUB] ? SUB : 'scores');
  if(label) label.textContent = '绩点 / 综测计算器 · ' + (({
    scores:'① 我的成绩', goals:'② 门槛对照', acts:'③ 活动篮', rules:'④ 计算口径'
  })[on] || '我的成绩');
}
function applySub(){
  Object.entries(SUBS).forEach(([k,id])=>{
    const el = $('#'+id);
    if(el) el.classList.toggle('hide', k !== SUB);
  });
  $$('#side-nav a.sub').forEach(a=>a.classList.toggle('on', a.dataset.sub===SUB && a.dataset.view==='calc'));
  renderSub();
}
/* opts.callback：切换完成时执行。hashchange 回调里不能用它（此时 hash 已经改过了） */
function nav(view, sub, opts){
  opts = opts || {};
  VIEW = TITLES[view] ? view : 'chat';
  if(VIEW === 'calc' && SUBS[sub]) SUB = sub;
  $$('#side-nav a[data-view]').forEach(a=>a.classList.toggle('on', a.dataset.view===VIEW));
  $$('.view').forEach(v=>{
    const on = v.id === 'view-'+VIEW;
    v.classList.toggle('on', on);
    if(on && v.dataset.flex === '1') v.classList.add('vflex');
  });
  /* 只有对话视图是「内部滚动」：.chatview 撑满高度、.chat-scroll 自己滚，
     外壳这一层必须锁住，否则会多出一条滚动条；
     计算器与口径说明是普通长页面，靠 #appmain 滚 —— 锁住它们页面就滚不动了。 */
  const main = $('#appmain');
  if(main) main.classList.toggle('noscroll', VIEW === 'chat');
  if(VIEW === 'calc'){
    applySub();
    // 计算器首次进入才加载数据并计算（页面上还没有输入时不必算）
    if(window.__calc) try{ window.__calc.boot(); }catch(e){ console.error(e); }
  }
  if(VIEW === 'chat' && window.__chat) try{ window.__chat.sync(); }catch(e){}
  document.title = (TITLES[VIEW] || '') + ' · SCAU 学生发展信息 Harness';
  window.scrollTo(0, 0);
  if(main) main.scrollTop = 0;
}
function hashNav(h){
  if(h.indexOf('#/calc') === 0){
    const p = h.split('/');
    return nav('calc', p[2] || 'scores');
  }
  return nav('chat');
}
function go(view, sub){ location.hash = (view==='calc') ? ('#/calc/'+(sub||'scores')) : '#/chat'; }
window.addEventListener('hashchange', ()=>hashNav(location.hash));

/* ===================== 侧栏与设置 ===================== */
$('#menu-btn').onclick = ()=>{ setSidebar($('#sidebar').classList.contains('closed')); };
setSidebar(sidebarOpen());
$$('#side-nav a[data-view]').forEach(a=>{
  a.onclick = (e)=>{ if(a.dataset.view === 'calc') e.preventDefault(), go('calc', a.dataset.sub); };
});
$('#side-docs').onclick = (e)=>{ e.preventDefault(); go('calc','rules'); };
$$('.sug').forEach(el=>el.onclick = ()=>{
  const q = $('#q');
  if(q){ q.value = el.dataset.q || ''; if(window.__chat) window.__chat.resize(); q.focus(); }
});

/* ===================== 轻提示（底部气泡，2.6 秒后自己消失） ===================== */
let toastTimer = null;
function toast(html, ms){
  const el = $('#toast'); if(!el) return;
  el.innerHTML = html;
  el.classList.add('on');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(()=>el.classList.remove('on'), ms || 2600);
}
window.__toast = toast;

/* ===================== ⚙️ 设置：OpenAI 兼容端点 ===================== */
function setMsg(html, kind){
  const el=$('#set-msg');
  if(!html){ el.className='msg hide'; el.innerHTML=''; return; }
  el.className='msg '+(kind||''); el.innerHTML=html;
}
function setBusy(on, what){
  $('#set-save').disabled=on; $('#set-test').disabled=on;
  if(on) setMsg('<span class="spin"></span> '+esc(what), '');
}
function openSettings(){
  $('#set-bd').classList.remove('hide');
  setMsg(''); ocrMsg(''); authMsg(''); authCaptcha(false);
  $('#set-base').value=''; $('#set-model').value=''; $('#set-key').value='';
  $('#set-presets').innerHTML='';
  $('#auth-pass').value='';
  setBusy(true,'正在读取当前配置…');
  loadOcrSettings();
  loadAuthSettings();
  fetch('/api/settings/llm').then(r=>r.json()).then(d=>{
    setBusy(false);
    $('#set-base').value = d.base_url||'';
    $('#set-model').value = d.model||'';
    $('#set-key').value = '';
    $('#set-key').placeholder = d.api_key_set
      ? ('已保存 '+d.api_key_masked+'，留空表示不改动') : 'sk-… （必填）';
    $('#set-file').textContent = '写入 ' + (d.env_file||'.env');
    $('#set-presets').innerHTML = (d.presets||[]).map((p,i)=>
      `<button type="button" class="ghost" data-i="${i}" title="${esc(p.note||'')}">${esc(p.label)}</button>`).join('');
    $('#set-presets').querySelectorAll('button').forEach(b=>{
      b.onclick = ()=>{
        const p = d.presets[+b.dataset.i];
        $('#set-base').value = p.base_url; $('#set-model').value = p.model;
        setMsg('已填入 <b>'+esc(p.label)+'</b> 的端点与模型名，别忘了填 API key。','warn');
      };
    });
    if(d.writable===false){
      $('#set-save').disabled=true; $('#set-test').disabled=true;
      setMsg('当前不是从本机（127.0.0.1）访问的，为了不把 key 交出去，这里只能看不能改。','warn');
    }else if(d.shadowed && d.shadowed.length){
      setMsg('注意：系统环境变量里已经有 <b>'+esc(d.shadowed.join('、'))+
             '</b>，它的优先级高于 .env —— 这里保存本次运行会生效，'+
             '但重启后还是会被环境变量盖回去。','warn');
    }else if(!d.configured){
      setMsg('还没配置。填好三项后点「保存并验证」。','warn');
    }
    $('#set-base').focus();
  }).catch(e=>{ setBusy(false); setMsg('读取配置失败：'+esc(String(e)),'err'); });
}
function closeSettings(){ $('#set-bd').classList.add('hide'); }

/* ---------- 设置弹窗的三个分页 ---------- */
function setTab(name){
  $$('#set-bd .set-tabs button').forEach(b=>b.classList.toggle('on', b.dataset.tab===name));
  const panes = {llm:'#set-pane-llm', ocr:'#set-pane-ocr', auth:'#set-pane-auth'};
  Object.entries(panes).forEach(([k,sel])=>{
    const el = $(sel); if(el) el.classList.toggle('hide', k!==name);
  });
  if(name==='ocr') loadOcrSettings();
  if(name==='auth') loadAuthSettings();
}
$$('#set-bd .set-tabs button').forEach(b=>{ b.onclick = ()=> setTab(b.dataset.tab); });

/* ---------- 附件与 OCR ---------- */
function ocrMsg(html, kind){
  const el=$('#ocr-msg'); if(!el) return;
  if(!html){ el.className='msg hide'; el.innerHTML=''; return; }
  el.className='msg '+(kind||''); el.innerHTML=html;
}
function ocrBusy(on){
  ['#ocr-save','#ocr-test','#ocr-clear'].forEach(s=>{ const el=$(s); if(el) el.disabled=on; });
}
function ocrPayload(){
  return {
    provider: $('#ocr-provider').value,
    api_key: $('#ocr-key').value,
    secret_key: $('#ocr-secret').value,
    accurate: $('#ocr-accurate').checked,
  };
}
function loadOcrSettings(){
  ocrBusy(true);
  fetch('/api/settings/ocr').then(r=>r.json()).then(d=>{
    ocrBusy(false);
    $('#ocr-provider').value = d.provider || 'none';
    $('#ocr-accurate').checked = !!d.accurate;
    $('#ocr-key').value=''; $('#ocr-secret').value='';
    $('#ocr-key').placeholder = d.api_key_set
      ? ('已保存 '+d.api_key_masked+'，留空表示不改动') : 'API Key（AK）';
    $('#ocr-secret').placeholder = d.secret_key_set
      ? ('已保存 '+d.secret_key_masked+'，留空表示不改动') : 'Secret Key（SK）';
    $('#ocr-hint').textContent = d.label
      ? ('当前：' + d.label + '　申请地址 console.bce.baidu.com（开通「通用文字识别」）')
      : '未启用 OCR：附件里的文字照常解析，只有图片/扫描件里的字提取不到。';
    if(d.attach_dir) $('#ocr-dir').textContent = d.attach_dir;
    $('#ocr-astat').textContent = d.attach_stat
      ? ('附件目录：' + d.attach_stat.files + ' 个文件 / ' + d.attach_stat.human +
         '　已入库附件 ' + (d.attachments||0) + ' 个（有正文 ' + (d.attachments_with_text||0) + ' 个）')
      : '';
    if(d.writable===false){
      ['#ocr-save','#ocr-test','#ocr-clear'].forEach(s=>{ const el=$(s); if(el) el.disabled=true; });
      ocrMsg('当前不是从本机（127.0.0.1）访问的，只能看不能改。','warn');
    }else if(d.shadowed && d.shadowed.length){
      ocrMsg('系统环境变量里已有 <b>'+esc(d.shadowed.join('、'))+'</b>，优先级高于 .env。','warn');
    }
  }).catch(e=>{ ocrBusy(false); ocrMsg('读取 OCR 配置失败：'+esc(String(e)),'err'); });
}
async function saveOcr(verify){
  ocrBusy(true);
  ocrMsg('<span class="spin"></span> ' + (verify ? '正在用测试图真实调用 OCR…' : '正在保存…'));
  try{
    const r = await postSettings('/api/settings/ocr',
      Object.assign(ocrPayload(), {verify: verify, persist: true}));
    const d = r.d;
    ocrBusy(false);
    if(d.ok){
      ocrMsg('✅ ' + esc(d.message || '已保存') + (d.warning ? '<br>'+esc(d.warning) : ''),
             d.warning ? 'warn' : 'ok');
      $('#ocr-key').value=''; $('#ocr-secret').value='';
      loadOcrSettings();
      if(window.__chat) window.__chat.status();
    }else{
      ocrMsg('❌ ' + esc(d.error || ('HTTP '+r.status)) +
             (d.hint ? '<br><span class="small">'+esc(d.hint)+'</span>' : ''), 'err');
    }
  }catch(e){ ocrBusy(false); ocrMsg('保存失败：'+esc(String(e)),'err'); }
}
async function testOcr(){
  ocrBusy(true); ocrMsg('<span class="spin"></span> 正在识别一张测试图…');
  try{
    const r = await postSettings('/api/settings/ocr/test', ocrPayload());
    const d = r.d; ocrBusy(false);
    if(d.ok) ocrMsg('✅ ' + esc(d.message),'ok');
    else ocrMsg('❌ ' + esc(d.error || ('HTTP '+r.status)),'err');
  }catch(e){ ocrBusy(false); ocrMsg('测试失败：'+esc(String(e)),'err'); }
}
async function clearOcr(){
  ocrBusy(true); ocrMsg('正在清除…');
  try{
    const r = await postSettings('/api/settings/ocr/clear', {});
    const d = r.d; ocrBusy(false);
    ocrMsg(d.ok ? '✅ 已清除 OCR 凭据' : ('❌ ' + esc(d.error||'清除失败')), d.ok?'ok':'err');
    loadOcrSettings();
  }catch(e){ ocrBusy(false); ocrMsg('清除失败：'+esc(String(e)),'err'); }
}

/* ---------- 🔐 账号与登录 ---------- */
let AUTH_CAP_TOKEN = '';
function authMsg(html, kind){
  const el=$('#auth-msg'); if(!el) return;
  if(!html){ el.className='msg hide'; el.innerHTML=''; return; }
  el.className='msg '+(kind||''); el.innerHTML=html;
}
function authBusy(on){
  ['#auth-save','#auth-save-only','#auth-clear','#auth-logout','#auth-cap-go','#auth-cap-retry']
    .forEach(s=>{ const el=$(s); if(el) el.disabled=on; });
}
function authCaptcha(show, dataUrl, token){
  const wrap = $('#auth-cap-wrap');
  if(!wrap) return;
  if(show){
    AUTH_CAP_TOKEN = token || '';
    if(dataUrl) $('#auth-cap-img').src = dataUrl;
    wrap.classList.remove('hide');
  }else{
    AUTH_CAP_TOKEN = '';
    wrap.classList.add('hide');
    $('#auth-cap-text').value = '';
  }
}
function authPayload(verify){
  return {
    username: $('#auth-user').value.trim(),
    password: $('#auth-pass').value,
    service: $('#auth-service').value.trim(),
    captcha_url: $('#auth-captcha-url').value.trim(),
    captcha_rounds: parseInt($('#auth-rounds').value || '3', 10) || 3,
    save_password: $('#auth-save-pw').checked,
    auto_login: $('#auth-auto').checked,
    ocr_captcha: $('#auth-ocr').checked,
    verify: verify, persist: true,
  };
}
function authFill(d){
  const c = d.credentials || {}, s = d.session || {}, g = d.settings || {};
  $('#auth-user').value = '';
  $('#auth-user').placeholder = c.username_set
    ? ('已保存 ' + c.username_masked + '，留空表示不改动') : '2023xxxxxxxx';
  // 密码框不清空：卡在「人工填验证码」那一步时，还要用它把登录做完
  $('#auth-pass').placeholder = c.password_set
    ? '已保存密码，留空表示不改动' : '统一身份认证密码';
  $('#auth-service').value = g.service || '';
  $('#auth-captcha-url').value = g.captcha_url || '';
  $('#auth-rounds').value = g.captcha_rounds || 3;
  $('#auth-auto').checked = !!g.auto_login;
  $('#auth-ocr').checked = !!g.ocr_captcha;
  $('#auth-save-pw').checked = true;
  $('#auth-ocr-hint').textContent = d.ocr_configured
    ? 'OCR 已配置，验证码可以直接自动识别。'
    : ('⚠️ 还没配 OCR（「🖼 附件与 OCR」分页）—— 没有它的话，遇到验证码只能在这里手填一次，'
       + '采集时也没法自动过。');
  const bits = [];
  if(s.cookies_alive) bits.push('会话有效：' + s.cookies_alive + ' 个 cookie');
  else if(s.cookie_file_exists) bits.push('会话已过期（cookie 文件在，但都失效了）');
  else bits.push('当前无会话');
  if(c.username_set) bits.push('已存账号 ' + c.username_masked + (c.saved_at ? '（' + c.saved_at + '）' : ''));
  bits.push('CAS ' + (d.cas_base || ''));
  $('#auth-stat').textContent = bits.join('　·　');
  $('#auth-file').textContent = '凭据文件 ' + ((c.file) || '.auth/credentials.json');
  if(d.writable === false){
    authBusy(true);
    authMsg('当前不是从本机（127.0.0.1）访问的，为了不把账号交出去，这里只能看不能改。','warn');
  }
}
function loadAuthSettings(){
  authBusy(true);
  fetch('/api/settings/auth').then(r=>r.json()).then(d=>{
    authBusy(false);
    authFill(d);
    if(d.writable !== false && d.shadowed && d.shadowed.length){
      authMsg('系统环境变量里已有 <b>'+esc(d.shadowed.join('、'))+'</b>，优先级高于 .env。','warn');
    }
  }).catch(e=>{ authBusy(false); authMsg('读取登录配置失败：'+esc(String(e)),'err'); });
}
function authResultMessage(d){
  if(d.ok && d.verified) return '✅ ' + esc(d.message || '登录成功');
  if(d.need_captcha) return '';
  if(d.ok && !d.verified){
    return (d.error ? '⚠️ ' + esc(d.message || '') + '<br>' + esc(d.error)
                    : '✅ ' + esc(d.message || '已保存'));
  }
  return '❌ ' + esc(d.error || '登录失败');
}
async function saveAuth(verify){
  authBusy(true);
  authMsg('<span class="spin"></span> ' + (verify
    ? '正在真实登录统一身份认证（有验证码会自动识别）…' : '正在保存…'));
  try{
    const r = await postSettings('/api/settings/auth', authPayload(verify));
    const d = r.d;
    authBusy(false);
    authFill(d);
    if(d.need_captcha){
      authCaptcha(true, d.captcha_image || '', d.token || '');
      authMsg('🔎 ' + esc(d.error || 'OCR 没认出验证码') +
              (d.hint ? '<br><span class="small">' + esc(d.hint) + '</span>' : ''), 'warn');
      const t = $('#auth-cap-text'); if(t) t.focus();
      return;
    }
    authCaptcha(false);
    if(d.ok && (d.verified || !verify)){
      authMsg(authResultMessage(d) + (d.warning ? '<br>' + esc(d.warning) : ''),
              d.warning ? 'warn' : 'ok');
      $('#auth-pass').value = '';
      if(window.__chat) window.__chat.status();
      if(d.verified) toast('✅ 已登录统一身份认证，采集会带着这个会话');
    }else{
      authMsg(authResultMessage(d) + (d.hint ? '<br><span class="small">'+esc(d.hint)+'</span>' : ''),
              'err');
    }
  }catch(e){ authBusy(false); authMsg('保存失败：'+esc(String(e)),'err'); }
}
async function submitCaptcha(retryOnly){
  const text = retryOnly ? '' : ($('#auth-cap-text').value || '').trim();
  if(!retryOnly && !text){ authMsg('先填一下图里的验证码。','warn'); return; }
  authBusy(true);
  authMsg('<span class="spin"></span> ' + (retryOnly ? '正在换一张验证码…' : '正在提交验证码…'));
  try{
    if(retryOnly){
      // 「换一张」= 重新走一次「保存并登录」，会重新拉一张新的验证码图
      const r = await postSettings('/api/settings/auth', authPayload(true));
      const d = r.d; authBusy(false); authFill(d);
      if(d.need_captcha){
        authCaptcha(true, d.captcha_image || '', d.token || '');
        authMsg('🔎 这是新的一张，照着填。','warn');
      }else if(d.ok && d.verified){
        authCaptcha(false); $('#auth-pass').value=''; authMsg('✅ ' + esc(d.message||'已登录'),'ok');
      }else{
        authCaptcha(false); authMsg('❌ ' + esc(d.error||d.message||'这次没成'),'err');
      }
      return;
    }
    const r = await postSettings('/api/settings/auth/captcha',
      {token: AUTH_CAP_TOKEN, captcha: text, password: $('#auth-pass').value});
    const d = r.d; authBusy(false); authFill(d);
    if(d.ok){
      authCaptcha(false); $('#auth-pass').value='';
      authMsg('✅ ' + esc(d.message||'已登录') +
              (d.warning ? '<br>'+esc(d.warning) : ''), d.warning?'warn':'ok');
      if(window.__chat) window.__chat.status();
      toast('✅ 已登录统一身份认证，采集会带着这个会话');
    }else if(d.need_captcha){
      authCaptcha(true, d.captcha_image||'', d.token||'');
      authMsg('🔎 ' + esc(d.error||'验证码不对') +
              (d.hint ? '<br><span class="small">'+esc(d.hint)+'</span>' : ''), 'warn');
    }else{
      authCaptcha(false);
      authMsg('❌ ' + esc(d.error||'登录失败') +
              (d.hint ? '<br><span class="small">'+esc(d.hint)+'</span>' : ''), 'err');
    }
  }catch(e){ authBusy(false); authMsg('提交失败：'+esc(String(e)),'err'); }
}
async function clearAuth(){
  authBusy(true); authMsg('正在清除…');
  try{
    const r = await postSettings('/api/settings/auth/clear', {});
    const d = r.d; authBusy(false); authFill(d); authCaptcha(false);
    authMsg(d.ok ? '✅ ' + esc(d.message) : ('❌ ' + esc(d.error||'清除失败')), d.ok?'ok':'err');
  }catch(e){ authBusy(false); authMsg('清除失败：'+esc(String(e)),'err'); }
}
async function logoutAuth(){
  authBusy(true); authMsg('正在退出登录…');
  try{
    const r = await postSettings('/api/settings/auth/logout', {});
    const d = r.d; authBusy(false); authFill(d);
    authMsg(d.ok ? '✅ ' + esc(d.message) : ('❌ ' + esc(d.error||'失败')), d.ok?'ok':'err');
    if(window.__chat) window.__chat.status();
  }catch(e){ authBusy(false); authMsg('失败：'+esc(String(e)),'err'); }
}

function setPayload(){
  return {
    base_url: $('#set-base').value.trim(),
    model: $('#set-model').value.trim(),
    api_key: $('#set-key').value,
  };
}async function postSettings(path, payload){
  const r = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json'},
                               body: JSON.stringify(payload)});
  let d = {}; try{ d = await r.json(); }catch(e){}
  return {status:r.status, d:d||{}};
}
function bindForceSave(){
  const f = $('#set-force');
  if(f) f.onclick = ()=> saveSettings(false);
}
async function saveSettings(verify){
  setBusy(true, verify ? '正在用这套配置做一次真实调用验证…' : '正在保存…');
  try{
    const r = await postSettings('/api/settings/llm',
      Object.assign(setPayload(), {verify: verify, persist: true}));
    const d = r.d;
    setBusy(false);
    if(d.ok){
      setMsg('✅ ' + esc(d.message || '已保存') +
             (d.warning ? '<br>' + esc(d.warning) : ''), d.warning ? 'warn' : 'ok');
      $('#set-key').value='';
      if(d.api_key_set) $('#set-key').placeholder = '已保存 '+d.api_key_masked+'，留空表示不改动';
      if(window.__chat) window.__chat.status();
    }else{
      setMsg('❌ ' + esc(d.error || ('HTTP '+r.status)) +
             (d.hint ? '<br><span class="small">'+esc(d.hint)+'</span>' : '') +
             (verify ? '<br><span class="lnk" id="set-force">跳过验证，仍然保存</span>' : ''), 'err');
      bindForceSave();
    }
  }catch(e){ setBusy(false); setMsg('保存失败：'+esc(String(e)),'err'); }
}
async function testSettings(){
  setBusy(true,'正在真实调用一次该端点…');
  try{
    const r = await postSettings('/api/settings/llm/test', setPayload());
    const d = r.d;
    setBusy(false);
    if(d.ok){
      setMsg('✅ 连接成功：<b>'+esc(d.model)+'</b> 回复「'+esc(d.reply)+'」（'+d.ms+' ms）','ok');
    }else{
      setMsg('❌ 连接失败：'+esc(d.error || ('HTTP '+r.status)) +
             (d.ms ? '（'+d.ms+' ms）' : ''), 'err');
    }
  }catch(e){ setBusy(false); setMsg('测试失败：'+esc(String(e)),'err'); }
}

$('#settings-btn').onclick = openSettings;
$('#set-save').onclick = ()=> saveSettings(true);
$('#set-test').onclick = testSettings;
$('#set-close').onclick = closeSettings;
$('#ocr-save').onclick = ()=> saveOcr(true);
$('#ocr-test').onclick = testOcr;
$('#ocr-clear').onclick = clearOcr;
$('#ocr-close').onclick = closeSettings;
$('#auth-save').onclick = ()=> saveAuth(true);
$('#auth-save-only').onclick = ()=> saveAuth(false);
$('#auth-clear').onclick = clearAuth;
$('#auth-logout').onclick = logoutAuth;
$('#auth-close').onclick = closeSettings;
$('#auth-cap-go').onclick = ()=> submitCaptcha(false);
$('#auth-cap-retry').onclick = ()=> submitCaptcha(true);
$('#auth-cap-text').onkeydown = e=>{ if(e.key === 'Enter') submitCaptcha(false); };
$('#ocr-provider').onchange = ()=>{
  const on = $('#ocr-provider').value !== 'none';
  $('#ocr-key').disabled = !on; $('#ocr-secret').disabled = !on;
};
$('#set-bd').onclick = e=>{ if(e.target === $('#set-bd')) closeSettings(); };
document.addEventListener('keydown', e=>{ if(e.key==='Escape') closeSettings(); });
/* Settings（计算器页顶部的「⚙️ 设置」等入口）：window.__settings.open() */
window.__settings = {open: openSettings, close: closeSettings, tab: setTab};
"""
