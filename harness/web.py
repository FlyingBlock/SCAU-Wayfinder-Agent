"""简陋但够用的 Web 界面：标准库 http.server + SSE 流式输出。

为什么不用 FastAPI：本机沙箱装不了包（指南 §3.4），而 http.server 足够
支撑单用户使用，且零依赖。前端是内嵌的 HTML 页面，无构建步骤。

路由：
  GET  /                    首页（内嵌 HTML/JS，含「⚙️ 设置」弹窗）
  GET  /calc                绩点/综测计算器页面
  GET  /calc-docs           计算器数据口径说明
  GET  /api/status          库状态 + LLM/公网搜索配置灯
  GET  /api/search?q=&k=    纯检索（不花 token）
  GET  /api/article?id=     读某篇正文
  GET  /api/ask?q=&rounds=  提问，SSE 流式返回 trace + answer
  GET  /api/settings/llm    读当前 LLM 配置（key 只回显掩码）
  POST /api/settings/llm    保存 base URL / 模型名 / API key（可先真实调用验证）
  POST /api/settings/llm/test 只测试连通性，不保存
  GET  /api/calc/catalog    计算器全部静态数据（专业/课程/规则/门槛/活动）
  POST /api/calc/evaluate   提交成绩单 + 活动篮，返回完整计算结果
  GET  /api/calc/target     反推：达到目标绩点时剩余课程需要的分数
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
from .calcpages import CALC_DOCS_PAGE, CALC_PAGE
from .config import (
    ENV_FILE,
    LLM_ENV_KEYS,
    LLM_LEGACY_KEYS,
    LLM_PRESETS,
    SETTINGS,
    LLMSettings,
    SearchSettings,
    apply_llm_settings,
    env_file_shadowed_keys,
)
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
  nav.nav{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
  nav.nav a,nav.nav button{font-size:13px;color:var(--acc);text-decoration:none;border:1px solid var(--bd);
            border-radius:99px;padding:3px 11px;background:var(--bg);font-weight:500;cursor:pointer}
  nav.nav a:hover,nav.nav button:hover{background:var(--soft)}
  nav.nav button.set{border-color:#b6cffa;background:#eaf1fd}
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
  /* ---- 设置弹窗 ---- */
  .hide{display:none!important}
  .bd{position:fixed;inset:0;background:rgba(31,35,40,.45);z-index:50;overflow:auto;
      padding:52px 16px;display:flex;justify-content:center;align-items:flex-start}
  .modal{background:var(--bg);border:1px solid var(--bd);border-radius:12px;padding:20px 22px;
         width:100%;max-width:580px;box-shadow:0 14px 38px rgba(31,35,40,.22)}
  .modal h2{font-size:16px;margin:0 0 6px;font-weight:650}
  .modal .fld{margin-top:13px}
  .modal .fld label{display:block;font-size:12.5px;color:var(--mut);margin-bottom:4px}
  .modal input{width:100%;padding:8px 10px;border:1px solid var(--bd);border-radius:8px;font:inherit}
  .modal input:focus{outline:2px solid #b6cffa;outline-offset:-1px;border-color:var(--acc)}
  .presets{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px}
  .presets button{background:var(--soft);color:var(--fg);border:1px solid var(--bd);
                  border-radius:99px;padding:3px 10px;font-size:12.5px;font-weight:500}
  .msg{font-size:13px;margin-top:13px;padding:9px 11px;border-radius:8px;
       border:1px solid var(--bd);background:var(--soft);word-break:break-word}
  .msg.ok{color:var(--ok);border-color:#b7e0c2;background:#eaf7ee}
  .msg.err{color:var(--err);border-color:#f3c0c0;background:#fdeaea}
  .msg.warn{color:var(--warn);border-color:#eeddaa;background:#fdf6e3}
  .msg .lnk{color:var(--acc);cursor:pointer;text-decoration:underline dotted}
  .small{font-size:12.5px;color:var(--mut)}
  .mono{font-family:ui-monospace,Consolas,monospace}
</style>
</head>
<body>
<header>
  <h1>🌾 SCAU 学生发展信息 Harness</h1>
  <nav class="nav">
    <a href="/calc">📊 绩点 / 综测计算器</a>
    <button type="button" class="set" id="settings-btn" title="OpenAI 兼容端点：base URL / 模型名 / API key">⚙️ 设置</button>
  </nav>
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

<!-- ===================== ⚙️ LLM 设置 ===================== -->
<div class="bd hide" id="set-bd">
  <div class="modal" role="dialog" aria-modal="true" aria-labelledby="set-title">
    <h2 id="set-title">⚙️ 模型设置</h2>
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
  </div>
</div>

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
    p.push(`<span class="pill llm ${d.llm_configured?'ok':'err'}" style="cursor:pointer"
             title="点这里改 base URL / 模型名 / API key（${esc(d.llm_base_url||'')}）"
             >LLM ${d.llm_configured?esc(d.llm_model):'未配置 ⚙️'}</span>`);
    p.push(`<span class="pill ${d.web_search==='none'?'warn':'ok'}">公网 ${d.web_search==='none'?'已关闭':d.web_search}</span>`);
    if(d.with_date) p.push(`<span class="pill">带日期 ${d.with_date}</span>`);
    if(d.last_crawl) p.push(`<span class="pill">最近抓取 ${d.last_crawl}</span>`);
    $('#pills').innerHTML = p.join('');
    const lp=$('#pills .pill.llm'); if(lp) lp.onclick = openSettings;
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
  setMsg('');
  $('#set-base').value=''; $('#set-model').value=''; $('#set-key').value='';
  $('#set-presets').innerHTML='';
  setBusy(true,'正在读取当前配置…');
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

function setPayload(){
  return {
    base_url: $('#set-base').value.trim(),
    model: $('#set-model').value.trim(),
    api_key: $('#set-key').value,
  };
}
async function postSettings(path, payload){
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
    // 注意别把返回值解构成 status —— 那会遮蔽上面的全局 status() 函数
    const r = await postSettings('/api/settings/llm',
      Object.assign(setPayload(), {verify: verify, persist: true}));
    const d = r.d;
    setBusy(false);
    if(d.ok){
      setMsg('✅ ' + esc(d.message || '已保存') +
             (d.warning ? '<br>' + esc(d.warning) : ''), d.warning ? 'warn' : 'ok');
      $('#set-key').value='';
      if(d.api_key_set) $('#set-key').placeholder = '已保存 '+d.api_key_masked+'，留空表示不改动';
      status();
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
$('#set-bd').onclick = e=>{ if(e.target === $('#set-bd')) closeSettings(); };
document.addEventListener('keydown', e=>{ if(e.key==='Escape') closeSettings(); });
// /?settings=1 可以直接把设置弹窗打开（计算器页的「模型设置」链接指到这里）
if(new URLSearchParams(location.search).get('settings')) openSettings();

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

    def _read_body(self) -> dict:
        """读 POST body 并解析成 dict。"""
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8", "ignore") or "{}")
        except json.JSONDecodeError:
            return {}
        return data if isinstance(data, dict) else {}

    # ------------------------------------------------------------------ #
    def do_GET(self) -> None:                 # noqa: N802
        path = urllib.parse.urlsplit(self.path).path
        try:
            if path in ("/", "/index.html"):
                self._send(200, PAGE.encode("utf-8"), "text/html; charset=utf-8")
            elif path in ("/calc", "/calc/"):
                self._send(200, CALC_PAGE.encode("utf-8"), "text/html; charset=utf-8")
            elif path in ("/calc-docs", "/calc-docs/"):
                self._send(200, CALC_DOCS_PAGE.encode("utf-8"),
                           "text/html; charset=utf-8")
            elif path == "/api/status":
                self._status()
            elif path == "/api/search":
                self._search()
            elif path == "/api/article":
                self._article()
            elif path == "/api/ask":
                self._ask()
            elif path == "/api/settings/llm":
                self._settings_get()
            elif path == "/api/calc/catalog":
                self._calc_catalog()
            elif path == "/api/calc/target":
                self._calc_target()
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

    def do_POST(self) -> None:                # noqa: N802
        path = urllib.parse.urlsplit(self.path).path
        try:
            if path == "/api/calc/evaluate":
                self._calc_evaluate()
            elif path == "/api/settings/llm":
                self._settings_save()
            elif path == "/api/settings/llm/test":
                self._settings_test()
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
            "llm_base_url": SETTINGS.llm.base_url,
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
    # LLM 设置（首页右上角「⚙️ 设置」）
    #
    # 界面上填的三项就是 .env 里的 LLM_BASE_URL / LLM_MODEL / LLM_API_KEY；
    # 保存时既落盘（下次启动仍生效）又原地更新 SETTINGS.llm（不用重启服务）。
    # ------------------------------------------------------------------ #
    @staticmethod
    def _mask_key(key: str) -> str:
        """key 只回显头尾，整条 key 不出现在响应里。"""
        if not key:
            return ""
        if len(key) <= 10:
            return key[:2] + "*" * max(len(key) - 2, 0)
        return f"{key[:6]}…{key[-4:]}"

    def _is_local(self) -> bool:
        """改配置只允许本机请求：`--host 0.0.0.0` 暴露到局域网时别让人改 key。"""
        try:
            host = (self.client_address or ("",))[0]
        except Exception:
            host = ""
        return host in ("127.0.0.1", "::1", "localhost", "::ffff:127.0.0.1")

    def _llm_state(self, extra: dict | None = None) -> dict:
        llm = SETTINGS.llm
        state = {
            "base_url": llm.base_url,
            "model": llm.model,
            "configured": llm.configured,
            "api_key_set": bool(llm.api_key),
            "api_key_masked": self._mask_key(llm.api_key),
            "env_file": str(ENV_FILE),
            "env_file_exists": ENV_FILE.is_file(),
            "writable": self._is_local(),
            "shadowed": sorted(env_file_shadowed_keys() & set(LLM_ENV_KEYS + LLM_LEGACY_KEYS)),
            "presets": [dict(p) for p in LLM_PRESETS],
        }
        state.update(extra or {})
        return state

    def _settings_get(self) -> None:
        self._json(self._llm_state())

    def _settings_save(self) -> None:
        if not self._is_local():
            self._json({"ok": False, "writable": False,
                        "error": "出于安全考虑，只有从本机（127.0.0.1）打开页面才能改设置。"}, 403)
            return
        payload = self._read_body()
        if not payload:
            self._json({"ok": False, "error": "请求体为空或不是合法 JSON"}, 400)
            return

        base_url = str(payload.get("base_url") or "").strip()
        model = str(payload.get("model") or "").strip()
        raw_key = payload.get("api_key")
        api_key = raw_key.strip() if isinstance(raw_key, str) else ""
        verify = bool(payload.get("verify", True))
        persist = bool(payload.get("persist", True))

        if base_url and not base_url.lower().startswith(("http://", "https://")):
            self._json({"ok": False, "error": "base URL 要以 http:// 或 https:// 开头"}, 400)
            return

        # 留空的项表示「沿用现在的值」（key 不回显，所以不能要求重填）
        effective_key = api_key or SETTINGS.llm.api_key
        effective_base = base_url.rstrip("/") or SETTINGS.llm.base_url
        effective_model = model or SETTINGS.llm.model

        verified, reply, ms = False, "", 0
        if verify:
            if not effective_key:
                self._json({"ok": False, "error": "还没有 API key。本机的 Ollama / vLLM "
                                                  "也要随便填一个非空值。"}, 400)
                return
            t0 = time.time()
            ok, msg = LLM(LLMSettings(api_key=effective_key, base_url=effective_base,
                                      model=effective_model, timeout=60)).health()
            ms = int((time.time() - t0) * 1000)
            if not ok:
                self._json({"ok": False, "verified": False, "ms": ms,
                            "hint": "可以点「跳过验证直接保存」，或检查 base URL / 模型名 / key / 网络。",
                            "error": f"验证失败：{msg}"}, 400)
                return
            verified, reply = True, msg

        res = apply_llm_settings(api_key=api_key or None, base_url=base_url or None,
                                 model=model or None, persist=persist)
        parts = ["已更新 " + "、".join(res["applied"]) if res["applied"]
                 else "三项都没填，配置未改动"]
        if verified:
            parts.append(f"真实调用验证通过（模型回复：{reply}）")
        parts.append(f"已写入 {ENV_FILE}" if res["wrote"]
                     else ("仅本次运行生效，未落盘" if res["applied"] else ""))
        self._json(self._llm_state({
            "ok": True, "verified": verified, "reply": reply, "ms": ms,
            "applied": res["applied"], "persisted": res["wrote"],
            "warning": res["warning"],
            "message": "；".join(p for p in parts if p),
        }))

    def _settings_test(self) -> None:
        """按表单里的值真实调一次模型，不落盘、不改当前配置。"""
        if not self._is_local():
            self._json({"ok": False,
                        "error": "出于安全考虑，只有从本机（127.0.0.1）打开页面才能测试连接。"}, 403)
            return
        payload = self._read_body()
        base_url = str(payload.get("base_url") or "").strip().rstrip("/") or SETTINGS.llm.base_url
        model = str(payload.get("model") or "").strip() or SETTINGS.llm.model
        raw_key = payload.get("api_key")
        api_key = (raw_key.strip() if isinstance(raw_key, str) else "") or SETTINGS.llm.api_key
        if not api_key:
            self._json({"ok": False, "error": "还没有 API key，请先填入"}, 400)
            return
        t0 = time.time()
        ok, msg = LLM(LLMSettings(api_key=api_key, base_url=base_url, model=model,
                                  timeout=60)).health()
        ms = int((time.time() - t0) * 1000)
        if ok:
            self._json({"ok": True, "reply": msg, "ms": ms, "base_url": base_url,
                        "model": model})
        else:
            self._json({"ok": False, "error": msg, "ms": ms, "base_url": base_url,
                        "model": model}, 400)

    # ------------------------------------------------------------------ #
    # 计算器 API
    # ------------------------------------------------------------------ #
    @staticmethod
    def _calculator():
        """每次请求新建一个 Calculator。

        `harness.calc` 只依赖 `data/calc/*.json`，不碰 SQLite，构造一次很便宜
        （几毫秒）。刻意不做全局缓存，这样直接改数据文件、刷新页面就生效，
        不需要重启服务，调参时省事。
        """
        from .calc import Calculator

        return Calculator()

    def _calc_catalog(self) -> None:
        self._json(self._calculator().catalog())

    def _calc_evaluate(self) -> None:
        payload = self._read_body()
        if not payload:
            self._json({"error": "请求体不是合法 JSON"}, 400)
            return
        res = self._calculator().evaluate_dict(payload)
        self._json(res.as_dict())

    def _calc_target(self) -> None:
        q = self._query()
        try:
            target = float(q.get("gpa") or 0)
        except ValueError:
            target = 0.0
        scores = {}
        raw = q.get("scores") or ""
        if raw:
            try:
                scores = json.loads(raw)
            except json.JSONDecodeError:
                scores = {}
        self._json(self._calculator().target_for_course(
            q.get("major") or "", scores, target))

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
            sse("answer", {"text": "", "error": "尚未配置 LLM API key：点右上角「⚙️ 设置」填入 "
                                                    "base URL / 模型名 / API key 即可（也可运行 "
                                                    "python -m harness.cli setup-key）。"
                                                    "想先看检索结果就勾上「仅检索验证」。",
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
