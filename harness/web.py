"""简陋但够用的 Web 界面：标准库 http.server + SSE 流式输出。

为什么不用 FastAPI：本机沙箱装不了包（指南 §3.4），而 http.server 足够
支撑单用户使用，且零依赖。前端是一个内嵌的 HTML 页面，无构建步骤。

路由：
  GET  /                    首页（内嵌 HTML/JS）
  GET  /api/status          库状态 + LLM/公网搜索配置灯
  GET  /api/search?q=&k=    纯检索（不花 token）
  GET  /api/article?id=     读某篇正文
  GET  /api/ask?q=&rounds=  提问，SSE 流式返回 trace + answer
"""
from __future__ import annotations

import json
import socket
import sys
import threading
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .agent import Agent
from .config import SETTINGS, SearchSettings
from .llm import LLM
from .store import Store
from .websearch import WebSearcher

PAGE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SCAU 学生发展信息 Harness</title>
<style>
  :root{--fg:#1f2328;--mut:#656d76;--bd:#d0d7de;--bg:#ffffff;--soft:#f6f8fa;
        --acc:#0969da;--ok:#1a7f37;--warn:#9a6700;--err:#cf222e}
  *{box-sizing:border-box}
  body{margin:0;font:15px/1.65 -apple-system,"Segoe UI","Microsoft YaHei",sans-serif;color:var(--fg);background:var(--soft)}
  header{background:var(--bg);border-bottom:1px solid var(--bd);padding:14px 22px;display:flex;
         align-items:center;gap:14px;flex-wrap:wrap;position:sticky;top:0;z-index:5}
  header h1{font-size:17px;margin:0;font-weight:650}
  .pills{display:flex;gap:8px;flex-wrap:wrap;margin-left:auto;font-size:12.5px}
  .pill{background:var(--soft);border:1px solid var(--bd);border-radius:99px;padding:3px 11px;color:var(--mut)}
  .pill.ok{color:var(--ok);border-color:#b7e0c2;background:#eaf7ee}
  .pill.warn{color:var(--warn);border-color:#eeddaa;background:#fdf6e3}
  .pill.err{color:var(--err);border-color:#f3c0c0;background:#fdeaea}
  main{max-width:960px;margin:0 auto;padding:22px}
  .card{background:var(--bg);border:1px solid var(--bd);border-radius:10px;padding:18px;margin-bottom:16px}
  textarea{width:100%;min-height:74px;padding:11px;border:1px solid var(--bd);border-radius:8px;
           font:inherit;resize:vertical}
  .row{display:flex;gap:10px;align-items:center;margin-top:11px;flex-wrap:wrap}
  button{background:var(--acc);color:#fff;border:0;border-radius:8px;padding:9px 18px;font:inherit;
         font-weight:600;cursor:pointer}
  button.ghost{background:var(--bg);color:var(--fg);border:1px solid var(--bd);font-weight:500}
  button:disabled{opacity:.5;cursor:not-allowed}
  .ex{font-size:13px;color:var(--mut);cursor:pointer;text-decoration:underline dotted}
  .ex:hover{color:var(--acc)}
  #trace{font:12.5px/1.7 ui-monospace,Consolas,monospace;color:var(--mut);white-space:pre-wrap;
         background:var(--soft);border:1px solid var(--bd);border-radius:8px;padding:11px;
         max-height:230px;overflow:auto;margin-top:14px}
  #answer{white-space:pre-wrap;word-wrap:break-word;margin-top:6px}
  #answer h2,#answer h3{font-size:16px;margin:20px 0 7px;padding-bottom:5px;border-bottom:1px solid var(--bd)}
  #answer h2:first-child{margin-top:0}
  #answer table{border-collapse:collapse;margin:10px 0;font-size:14px;display:block;overflow-x:auto}
  #answer th,#answer td{border:1px solid var(--bd);padding:6px 10px;text-align:left}
  #answer th{background:var(--soft)}
  #answer code{background:var(--soft);padding:1px 5px;border-radius:4px;font-size:13px}
  #answer a{color:var(--acc)}
  #refs{margin-top:18px;padding-top:14px;border-top:1px solid var(--bd);font-size:13px;color:var(--mut)}
  #refs div{margin:5px 0;word-break:break-all}
  .hit{border-top:1px solid var(--bd);padding:11px 0}
  .hit:first-child{border-top:0}
  .hit .t{font-weight:600}
  .hit .m{font-size:12.5px;color:var(--mut);margin:3px 0}
  .hit .s{font-size:13.5px;color:#424a53}
  details summary{cursor:pointer;font-weight:600;color:var(--mut)}
  .spin{display:inline-block;width:12px;height:12px;border:2px solid var(--bd);
        border-top-color:var(--acc);border-radius:50%;animation:r .8s linear infinite;vertical-align:-1px}
  @keyframes r{to{transform:rotate(360deg)}}
</style>
</head>
<body>
<header>
  <h1>🌾 SCAU 学生发展信息 Harness</h1>
  <div class="pills" id="pills"><span class="pill">加载中…</span></div>
</header>
<main>
  <div class="card">
    <textarea id="q" placeholder="例：生物专业可以参加什么竞赛？走什么发展路线？"></textarea>
    <div class="row">
      <button id="go">提问</button>
      <button class="ghost" id="find">只检索不生成</button>
      <label style="font-size:13.5px;color:var(--mut)">补检索轮数
        <select id="rounds"><option>1</option><option selected>2</option><option>3</option></select>
      </label>
      <label style="font-size:13.5px;color:var(--mut)">
        <input type="checkbox" id="dry"> 仅检索验证（不调用 LLM，不花 token）
      </label>
      <span style="margin-left:auto"></span>
      <span class="ex" data-q="生物专业可以参加什么竞赛？走什么发展路线？">生物专业竞赛与发展路线</span>
      <span class="ex" data-q="生物化学实验技能大赛怎么报名？往年什么时候办？">生化大赛怎么报名</span>
      <span class="ex" data-q="生命科学学院保研条件和时间线是什么？">保研条件与时间线</span>
      <span class="ex" data-q="大创项目什么时候申报？需要什么条件？">大创申报</span>
      <span class="ex" data-q="生物专业毕业后主要去哪就业？">生物就业去向</span>
    </div>
    <div id="trace" style="display:none"></div>
  </div>
  <div class="card" id="out" style="display:none">
    <div id="answer"></div>
    <div id="refs"></div>
  </div>
</main>
<script>
const $ = s => document.querySelector(s);
const esc = s => (s||"").replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

/* 极简 markdown 渲染：标题/粗体/表格/列表/链接/引用编号 */
function md(src){
  const lines = (src||"").split("\n"); let out=[], i=0, tbl=[];
  const inline = t => esc(t)
    .replace(/\[(\d+)\]/g,'<code>[$1]</code>')
    .replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>')
    .replace(/`([^`]+)`/g,'<code>$1</code>')
    .replace(/(https?:\/\/[^\s<)]+)/g,'<a href="$1" target="_blank" rel="noopener">$1</a>');
  const flushTbl = () => {
    if(!tbl.length) return;
    let html='<table>';
    tbl.forEach((r,idx)=>{
      if(/^\s*\|?[\s:\-|]+\|?\s*$/.test(r) && idx===1) return;
      const cells = r.replace(/^\s*\|/,'').replace(/\|\s*$/,'').split('|');
      const tag = idx===0?'th':'td';
      html += '<tr>'+cells.map(c=>`<${tag}>${inline(c.trim())}</${tag}>`).join('')+'</tr>';
    });
    out.push(html+'</table>'); tbl=[];
  };
  while(i<lines.length){
    const l = lines[i];
    if(/^\s*\|.*\|\s*$/.test(l)){ tbl.push(l); i++; continue; }
    flushTbl();
    if(/^###\s+/.test(l)) out.push('<h3>'+inline(l.replace(/^###\s+/,''))+'</h3>');
    else if(/^##\s+/.test(l)) out.push('<h2>'+inline(l.replace(/^##\s+/,''))+'</h2>');
    else if(/^#\s+/.test(l)) out.push('<h2>'+inline(l.replace(/^#\s+/,''))+'</h2>');
    else if(/^\s*[-*]\s+/.test(l)) out.push('<div style="margin:3px 0 3px 18px">• '+inline(l.replace(/^\s*[-*]\s+/,''))+'</div>');
    else if(l.trim()==='') out.push('');
    else out.push('<div>'+inline(l)+'</div>');
    i++;
  }
  flushTbl();
  return out.join('\n');
}

async function status(){
  try{
    const r = await fetch('/api/status'); const d = await r.json();
    const p=[];
    p.push(`<span class="pill ${d.articles?'ok':''}">语料 ${d.articles} 篇 / ${d.sites} 栏目</span>`);
    p.push(`<span class="pill ${d.llm_configured?'ok':'err'}">LLM ${d.llm_configured?d.llm_model:'未配置'}</span>`);
    p.push(`<span class="pill ${d.web_search==='none'?'warn':'ok'}">公网 ${d.web_search==='none'?'已关闭':d.web_search}</span>`);
    if(d.with_date) p.push(`<span class="pill">带日期 ${d.with_date}</span>`);
    if(d.last_crawl) p.push(`<span class="pill">最近抓取 ${d.last_crawl}</span>`);
    $('#pills').innerHTML = p.join('');
  }catch(e){ $('#pills').innerHTML = '<span class="pill err">状态读取失败</span>'; }
}

function logTrace(t){ const el=$('#trace'); el.style.display='block'; el.textContent += t+'\n'; el.scrollTop=el.scrollHeight; }

async function doSearch(){
  const q=$('#q').value.trim(); if(!q) return;
  $('#out').style.display='block'; $('#refs').innerHTML=''; $('#trace').style.display='none';
  $('#answer').innerHTML='<span class="spin"></span> 检索中…';
  const r = await fetch('/api/search?k=15&q='+encodeURIComponent(q));
  const d = await r.json();
  if(!d.hits || !d.hits.length){ $('#answer').innerHTML='没有命中。试试更短的关键词（2-6 字），或先跑抓取。'; return; }
  $('#answer').innerHTML = `<h2>检索命中 ${d.hits.length} 条（库内 ${d.total} 篇）</h2>` +
    d.hits.map(h=>`<div class="hit"><div class="t">${esc(h.title)}</div>
      <div class="m">${h.pub_date||'无日期'} · ${esc(h.college||h.site_name||'-')} · <a href="${h.url}" target="_blank" rel="noopener">原文</a></div>
      <div class="s">${esc(h.snippet)}</div></div>`).join('');
  $('#refs').innerHTML='';
}

function ask(){
  const q=$('#q').value.trim(); if(!q) return;
  const rounds=$('#rounds').value;
  const dry=$('#dry').checked ? '1':'0';
  $('#go').disabled=true; $('#find').disabled=true;
  $('#out').style.display='block'; $('#answer').innerHTML=''; $('#refs').innerHTML='';
  const tr=$('#trace'); tr.style.display='block'; tr.textContent='';
  logTrace((dry==='1'?'[仅检索验证] ':'')+'开始：'+q);
  const es = new EventSource('/api/ask?dry='+dry+'&rounds='+rounds+'&q='+encodeURIComponent(q));
  es.addEventListener('trace', e=>{ const d=JSON.parse(e.data); logTrace(d.text); });
  es.addEventListener('answer', e=>{
    const d=JSON.parse(e.data);
    $('#answer').innerHTML = md(d.text) + (d.error?`<div style="color:var(--err);margin-top:12px">生成异常：${esc(d.error)}</div>`:'');
    if(d.citations) $('#refs').innerHTML = '<strong>引用来源</strong><div>'+md(d.citations).replace(/\n/g,'')+'</div>';
    if(d.usage) logTrace(d.usage);
  });
  es.addEventListener('done', ()=>{ es.close(); $('#go').disabled=false; $('#find').disabled=false; status(); });
  es.onerror = ()=>{ es.close(); $('#go').disabled=false; $('#find').disabled=false; logTrace('连接中断'); };
}

document.querySelectorAll('.ex').forEach(el=>el.onclick=()=>{ $('#q').value=el.dataset.q; });
$('#go').onclick = ask;
$('#find').onclick = doSearch;
$('#q').addEventListener('keydown', e=>{ if(e.key==='Enter'&&(e.ctrlKey||e.metaKey)) ask(); });
status();
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    server_version = "SCAUHarness/0.1"
    protocol_version = "HTTP/1.1"

    # ------------------------------------------------------------------ #
    def log_message(self, fmt, *args):        # 安静一点，只保留错误
        if args and str(args[1] if len(args) > 1 else "").startswith(("4", "5")):
            sys.stderr.write("[web] " + fmt % args + "\n")

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code: int = 200) -> None:
        self._send(code, json.dumps(obj, ensure_ascii=False).encode("utf-8"),
                   "application/json; charset=utf-8")

    def _query(self) -> dict:
        q = urllib.parse.urlsplit(self.path).query
        return {k: v[0] for k, v in urllib.parse.parse_qs(q).items()}

    # ------------------------------------------------------------------ #
    def do_GET(self) -> None:                 # noqa: N802
        path = urllib.parse.urlsplit(self.path).path
        try:
            if path in ("/", "/index.html"):
                self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
            elif path == "/api/status":
                self._status()
            elif path == "/api/search":
                self._search()
            elif path == "/api/article":
                self._article()
            elif path == "/api/ask":
                self._ask()
            elif path == "/favicon.ico":
                self._send(204, b"", "image/x-icon")
            else:
                self._json({"error": "not found"}, 404)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            try:
                self._json({"error": f"{type(e).__name__}: {e}"}, 500)
            except Exception:
                pass

    # ------------------------------------------------------------------ #
    def _status(self) -> None:
        st = Store(SETTINGS.crawl.db_path)
        s = st.stats()
        last = ""
        try:
            row = st.conn.execute("SELECT ts FROM crawl_log ORDER BY id DESC LIMIT 1").fetchone()
            last = row["ts"] if row else ""
        except Exception:
            pass
        st.close()
        self._json({
            "articles": s["articles"], "sites": s["sites"], "with_date": s["with_date"],
            "llm_configured": SETTINGS.llm.configured, "llm_model": SETTINGS.llm.model,
            "web_search": SearchSettings.from_env().provider, "last_crawl": last,
            "db": str(SETTINGS.crawl.db_path),
        })

    def _search(self) -> None:
        q = self._query()
        query = (q.get("q") or "").strip()
        k = min(int(q.get("k") or 12), 50)
        st = Store(SETTINGS.crawl.db_path)
        total = st.count_articles()
        hits = st.search(query, top_k=k, topic=q.get("topic") or None,
                         since=q.get("since") or None) if query else []
        st.close()
        self._json({
            "total": total,
            "hits": [
                {"id": h.article_id, "title": h.title, "url": h.url, "pub_date": h.pub_date,
                 "snippet": h.snippet, "college": h.college, "site_name": h.site_name,
                 "topic": h.topic, "score": round(h.score, 3)}
                for h in hits
            ],
        })

    def _article(self) -> None:
        q = self._query()
        st = Store(SETTINGS.crawl.db_path)
        art = st.get_article(int(q.get("id") or 0), max_chars=20000)
        st.close()
        self._json(art or {"error": "not found"})

    # ------------------------------------------------------------------ #
    def _ask(self) -> None:
        """SSE：先推 trace 事件，最后推 answer + done。"""
        q = self._query()
        question = (q.get("q") or "").strip()
        rounds = int(q.get("rounds") or SETTINGS.agent_max_rounds)

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.send_header("Connection", "close")
        self.end_headers()

        def sse(event: str, data: dict) -> None:
            payload = f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
            self.wfile.write(payload.encode("utf-8"))
            self.wfile.flush()

        if not question:
            sse("answer", {"text": "问题为空", "error": "", "citations": ""})
            sse("done", {})
            return
        dry = (q.get("dry") or "").lower() in ("1", "true", "yes")
        if not SETTINGS.llm.configured and not dry:
            sse("answer", {"text": "", "error": "尚未配置 LLM API key，请运行：python -m harness.cli setup-key"
                                                    "（或勾选「仅检索验证」先看检索结果）",
                           "citations": ""})
            sse("done", {})
            return

        st = Store(SETTINGS.crawl.db_path)
        if st.count_articles() == 0:
            sse("answer", {"text": "", "error": "库内还没有语料，请先运行：python -m harness.cli crawl --scope narrow",
                           "citations": ""})
            sse("done", {})
            st.close()
            return

        llm = LLM(SETTINGS.llm)
        searcher = WebSearcher(SearchSettings.from_env())
        agent = Agent(st, llm, searcher, SETTINGS)

        labels = {
            "decompose": "① 意图分解", "retrieve": "② 检索", "retrieved": "   命中",
            "gaps": "④ 缺口检测", "evidence": "⑥ 证据聚合",
        }

        def trace(step: str, data: dict) -> None:
            label = labels.get(step, step)
            if step == "decompose":
                lines = [f"{label}：{len(data.get('subqueries', []))} 条子查询"]
                lines += [f"    [{x['scope']}] {x['query']}" for x in data.get("subqueries", [])]
                text = "\n".join(lines)
            elif step == "retrieve":
                text = f"{label} 第 {data.get('round')} 轮：" + "；".join(data.get("queries", []))
            elif step == "retrieved":
                text = f"{label} 第 {data.get('round')} 轮 +{data.get('new')}（累计 {data.get('total')}）"
            elif step == "gaps":
                miss = data.get("missing", [])
                text = f"{label}：" + ("证据已足够" if not miss else
                                      "补 " + "；".join(x["query"] for x in miss))
            elif step == "evidence":
                text = f"{label}：{data.get('count')} 条进入生成"
            else:
                text = f"{step}: {json.dumps(data, ensure_ascii=False)[:200]}"
            sse("trace", {"text": text})

        try:
            ans = agent.answer(question, max_rounds=rounds, trace=trace, dry_run=dry)
            if dry:
                body = ("### 仅检索验证（未调用 LLM）\n\n"
                        f"共检索到 **{len(ans.evidence)}** 条证据：\n\n"
                        + "\n".join(f"- [{e.n}] {e.title}（{e.pub_date or '无日期'}）"
                                    for e in ans.evidence))
                sse("answer", {"text": body, "error": "",
                               "citations": agent.build_citations(ans),
                               "usage": f"最终 Prompt {len(ans.prompt)} 字符（未送模型）"})
            else:
                sse("answer", {
                    "text": ans.text,
                    "error": ans.error,
                    "citations": agent.build_citations(ans),
                    "usage": llm.usage.line(),
                })
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            try:
                sse("answer", {"text": "", "error": f"{type(e).__name__}: {e}", "citations": ""})
            except Exception:
                pass
        finally:
            st.close()
            try:
                sse("done", {})
            except Exception:
                pass


def _port_free(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


def serve(host: str = "127.0.0.1", port: int = 8848, open_browser: bool = True) -> int:
    if not _port_free(host, port):
        print(f"端口 {port} 已被占用。换一个： python -m harness.cli web --port 8849", file=sys.stderr)
        return 2
    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.daemon_threads = True
    url = f"http://{host}:{port}/"
    print("=" * 70)
    print(f"SCAU Harness Web 界面已启动： {url}")
    print(f"  库文件   : {SETTINGS.crawl.db_path}")
    print(f"  LLM      : {SETTINGS.llm.model} ({'已配置' if SETTINGS.llm.configured else '未配置'})")
    print(f"  公网搜索 : {SearchSettings.from_env().provider}")
    print("  Ctrl+C 停止")
    print("=" * 70)
    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
    finally:
        httpd.server_close()
    return 0
