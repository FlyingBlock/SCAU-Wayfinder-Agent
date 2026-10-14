"""单页应用装配：把「外壳 + 对话视图 + 计算器视图」拼成一份 HTML。

页面只有一份（`/`、`/calc`、`/calc-docs` 返回的都是它），
视图之间靠左侧栏 + hash 路由切换（见 `harness/appshell.py`）。

三块内容的来源：

| 视图 | 标记 | 脚本 |
|---|---|---|
| 外壳（左侧栏 / 路由 / 设置弹窗） | `appshell.SHELL_HTML` | `appshell.SHELL_JS` |
| 主页对话（输入框在底部中间、输出在上方） | 本文件的 `CHAT_VIEW_MARKUP` | `CHAT_JS` |
| 绩点计算器（四个子页） | `calcpages.calc_view_html()` | `calcpages.calc_view_js()` |

脚本按「外壳 → 对话 → 计算器」的顺序拼在一个 `<script>` 里。
计算器那一份被 IIFE 包住，只通过 `window.__calc.boot()` 暴露启动入口，
所以它内部的 `$` / `esc` / `state` 不会和外壳、对话页的全局名字打架，
前面的 `smoke_ui.py` 也就能直接把它当普通脚本跑。
"""
from __future__ import annotations

from . import appshell
from .calcpages import calc_view_html, calc_view_js, docs_view_html

# --------------------------------------------------------------------------- #
# 对话视图标记
#
# 布局对齐 chat.deepseek.com：
#   输出在上方（.chat-scroll 滚动），输入框贴在视图底部中间（.composer）。
# 状态徽标单独用一个 #pill-chat —— 计算器写自己的 #pill-calc，两边互不覆盖。
# --------------------------------------------------------------------------- #
CHAT_VIEW_MARKUP = r"""
  <section class="view on vflex" id="view-chat" data-flex="1">
    <div class="chatview">
      <div class="chat-top"><div class="pills" id="pill-chat"><span class="pill">加载中…</span></div></div>
      <div class="chat-scroll" id="chat-scroll">
        <div class="chat-inner">
          <div class="chat-empty" id="chat-empty">
            <h2>今天想了解点什么？</h2>
            <div class="sub2">华南农大校内通知与公开信息检索 · 带 [n] 引用 · 计算器在左侧栏</div>
            <div class="chat-sugs">
              <button class="sug" type="button" data-q="生物专业可以参加什么竞赛？走什么发展路线？">🧭 生物专业竞赛与发展路线</button>
              <button class="sug" type="button" data-q="生命科学学院保研条件和时间线是什么？">🎓 保研条件与时间线</button>
              <button class="sug" type="button" data-q="生物化学实验技能大赛怎么报名？往年什么时候办？">🧪 生化大赛怎么报名</button>
              <button class="sug" type="button" data-q="大创项目什么时候申报？需要什么条件？">💡 大创申报</button>
            </div>
          </div>
          <div class="msgs" id="msgs"></div>
        </div>
      </div>
      <div class="composer">
        <div class="inner">
          <div class="cbox">
            <textarea id="q" rows="1" placeholder="给 SCAU Harness 发送消息，例如：生物专业可以参加什么竞赛？"></textarea>
            <button class="send" id="go" title="发送（Enter）">➤</button>
          </div>
          <div class="crow">
            <button type="button" id="find">只检索不生成</button>
            <label>补检索轮数
              <select id="rounds"><option>1</option><option selected>2</option><option>3</option></select>
            </label>
            <label><input type="checkbox" id="dry"> 仅检索验证（不调模型，不花 token）</label>
            <span style="margin-left:auto"></span>
            <span class="ex" data-q="生物专业毕业后主要去哪就业？">生物就业去向</span>
            <span class="ex" data-q="推免需要哪些材料？">推免材料</span>
          </div>
        </div>
      </div>
    </div>
  </section>
"""

# --------------------------------------------------------------------------- #
# 对话视图脚本
#
# 与旧版首页的差别：
# - 结果不再是一次性的一块，而是「问题气泡 + 模型回答」追加进 #msgs；
# - 输入框改成 textarea，Enter 发送、Shift+Enter 换行，并按内容自动长高；
# - 检索/生成过程收进回答下方的 <details>，不抢正文位置；
# - 状态徽标写 #pill-chat（计算器写 #pill-calc）。
# --------------------------------------------------------------------------- #
CHAT_JS = r"""
/* ===================== 主页对话：底部输入 + 上方输出 ===================== */
/* $ / $$ / esc 由外壳脚本（appshell.SHELL_JS）统一声明 */
const CHAT_STATE = { busy:false };

/* 极简 markdown 渲染：标题/粗体/表格/列表/链接/引用编号 */
function mdChat(src){
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

function chatPills(){
  fetch('/api/status').then(r=>r.json()).then(d=>{
    const p=[];
    p.push(`<span class="pill ${d.articles?'ok':''}">语料 ${d.articles} 篇 / ${d.sites} 栏目</span>`);
    p.push(`<span class="pill llm ${d.llm_configured?'ok':'err'}" style="cursor:pointer"
             title="点这里改 base URL / 模型名 / API key（${esc(d.llm_base_url||'')}）"
             >LLM ${d.llm_configured?esc(d.llm_model):'未配置 ⚙️'}</span>`);
    p.push(`<span class="pill ${d.web_search==='none'?'warn':'ok'}">公网 ${d.web_search==='none'?'已关闭':esc(d.web_search)}</span>`);
    if(d.with_date) p.push(`<span class="pill">带日期 ${d.with_date}</span>`);
    if(d.last_crawl) p.push(`<span class="pill">最近抓取 ${esc(d.last_crawl)}</span>`);
    const box = $('#pill-chat');
    if(box){
      box.innerHTML = p.join('');
      const lp = box.querySelector('.pill.llm');
      if(lp) lp.onclick = openSettings;
    }
    const hint = $('#chat-hint');
    if(hint) hint.textContent = `库内 ${d.articles} 篇 · ${d.sites} 个栏目`
      + (d.llm_configured ? '' : ' · 还没配模型，点左侧「⚙️ 设置 → 🧠 模型」');
  }).catch(()=>{ const box=$('#pill-chat'); if(box) box.innerHTML='<span class="pill err">状态读取失败</span>'; });
}

/* ---- 输入框：自动长高 / 发送 / 清空 ---- */
function chatResize(){
  const t = $('#q'); if(!t) return;
  t.style.height = 'auto';
  t.style.height = Math.min(t.scrollHeight, 190) + 'px';
}
function chatSync(){
  const empty = $('#chat-empty');
  const msgs = $('#msgs');
  /* 对话一开始只有祝福页；发过一轮之后把它收起来 */
  if(empty) empty.style.display = (msgs && msgs.children.length) ? 'none' : '';
}
function chatScrollDown(){
  const s = $('#chat-scroll');
  if(s) s.scrollTop = s.scrollHeight;
}
function chatUser(text){
  const box = $('#msgs'); if(!box) return null;
  const el = document.createElement('div');
  el.className = 'msg-u';
  el.innerHTML = '<div class="bub">'+esc(text)+'</div>';
  box.appendChild(el);
  chatScrollDown();
  return el;
}
function chatAnswer(){
  const box = $('#msgs'); if(!box) return {};
  const el = document.createElement('div');
  el.className = 'msg-a';
  el.innerHTML = '<div class="av">🌾</div><div class="ans">'
    + '<div class="wait"><span class="spin"></span> 正在检索校内语料与公网…</div>'
    + '<div class="body"></div><div class="cards-wrap"></div><div class="chat-refs"></div>'
    + '<details class="chat-trace hide"><summary>检索过程</summary><div class="lines"></div></details>'
    + '</div>';
  box.appendChild(el);
  chatScrollDown();
  const ans = el.querySelector('.ans');
  return {root:el, ans:ans, wait:ans.querySelector('.wait'), body:ans.querySelector('.body'),
          cards:el.querySelector('.cards-wrap'),
          refs:el.querySelector('.chat-refs'), trace:el.querySelector('.chat-trace'),
          lines:el.querySelector('.lines')};
}

/* ------------------------------------------------------------------ *
 * 卡片渲染：活动 / 赛事、附件、关键时间
 *
 * 卡片数据全部由后端 harness/cards.py 从证据与已核验名录里抽出来
 * （分数与时间都不是模型编的）。这里只负责画，以及把「加入活动篮」
 * 接到计算器的同一份 localStorage 状态上。
 * ------------------------------------------------------------------ */
const RUBRIC_ORDER = { '综测':0, '推免':1, '学分':2, '时长':3 };
function n2s(v, d){
  const x = Math.round((v||0)*100)/100;
  return (x===0?'0':String(x)).replace(/(\.\d*?)0+$/,'$1').replace(/\.$/,'');
}
function fileIcon(kind){
  return ({PDF:'📕', Word:'📄', Excel:'📊', PPT:'📽', 压缩包:'🗜', 表格:'📊'})[kind] || '📎';
}
function timesLine(card){
  const ts = card.times || [];
  if(!ts.length) return card.timing ? esc(card.timing) : '';
  return ts.map(t=>{
    const hot = t.is_deadline ? ' style="color:var(--err);font-weight:600"' : '';
    return `<b${hot}>${esc(t.label)}</b> ${esc(t.date)}`;
  }).join(' · ');
}
function activityCard(c){
  const ex = (c.extra||{});
  const tier = ex.tier ? `<span class="tierx ${esc(ex.tier)}" title="${esc(ex.appendix_title||'')}">${esc(ex.tier_label||ex.tier+' 类')}</span>` : '';
  const chips = [];
  if(c.level) chips.push(`<span class="chipm">${esc(c.level)}</span>`);
  if(c.category) chips.push(`<span class="chipm">${esc(c.category)}</span>`);
  if(c.match_score) chips.push(`<span class="chipm" title="与已核验名录的匹配得分">匹配 ${n2s(c.match_score)}</span>`);
  const chans = c.channels || {};
  let scoreBlock = '';
  if(c.in_registry && (c.scores && (c.scores.achieves||[]).length)){
    const rows = (c.scores.achieves||[]).slice(0,3).map(a=>{
      const only = (a.zongce||a.tuimian) ? '' :
        (Object.keys(a.other||{}).map(k=>`${esc(k)} +${n2s(a.other[k])}`).join('，') || '—');
      return `<div class="srow"><span class="lb">${esc(a.achieve)}</span>
        <span class="ach">${a.zongce?`综测 <b class="pts">+${n2s(a.zongce)} 分</b>`:''}
          ${a.zongce&&a.tuimian?' · ':''}${a.tuimian?`推免 <b style="color:var(--pri)">+${n2s(a.tuimian)} 分</b>`:''}
          ${only?esc(only):''}</span></div>`;
    }).join('');
    const chanBits = []
      .concat((chans.zongce||[]).map(x=>'综测·'+x))
      .concat((chans.tuimian||[]).map(x=>'推免·'+x))
      .concat((chans.other||[]).map(x=>'学分/时长·'+x));
    scoreBlock = `<div class="scores">${rows}</div>
      ${chanBits.length?`<div class="meta">计入：${esc(chanBits.join('、'))}</div>`:''}
      <div class="meta">上述为该赛事细则里最高的几档，实际加分按你取得的名次折算${
        c.discount==='none'?'（此条细则直接给分值）':'（等级系数 × 名次系数）'}。</div>`;
  }
  const confidence = (c.confidence && c.confidence!=='verified')
    ? `<span class="chipm" title="数值可信度：${esc(c.confidence)}">可信度 ${esc(c.confidence)}</span>` : '';
  const src = c.source || {};
  const srcLabel = [src.college||src.site_name||(src.source==='web'?'公网':''), src.pub_date,
                    src.n?('['+src.n+']'):''].filter(Boolean).join(' · ');
  const ready = c.basket_ready && c.id;
  const added = ready && inBasket(c.id);
  const foot = ready
    ? `<button class="mini ${added?'ghost':''}" data-add="${esc(c.id)}"
         data-name="${esc(c.name)}" ${added?'disabled':''}>${added?'✓ 已在活动篮':'＋ 添加到活动篮'}</button>
       <span class="src">${esc(srcLabel)}</span>`
    : `<a class="src" href="${esc(src.url||'#')}" target="_blank" rel="noopener">看原文 ↗</a>
       <span class="src">${esc(srcLabel)}</span>`;
  return `<div class="acard ${c.in_registry?'':'unmatched'}" data-id="${esc(c.id||'')}">
    <div class="hd"><span class="nm">${esc(c.name)}</span>${tier}</div>
    <div class="chips">${chips.join('')}${confidence}</div>
    ${c.organizer?`<div class="meta">主办：${esc(c.organizer)}</div>`:''}
    ${timesLine(c)?`<div class="meta">时间：${timesLine(c)}</div>`:''}
    ${(c.eligibility&&c.in_registry)?`<div class="meta">资格：${esc(c.eligibility)}</div>`:''}
    ${scoreBlock}
    ${c.registry_note?`<div class="why">${esc(c.registry_note)}</div>`:''}
    <div class="foot">${foot}</div>
  </div>`;
}
function fileCard(f){
  const src = f.source || {};
  const srcLabel = [src.title?('来自：'+src.title):'', src.college||src.site_name||'',
                    src.pub_date, src.n?('['+src.n+']'):''].filter(Boolean).join(' · ');
  const dl = f.ext
    ? `<a class="mini" href="${esc(f.url)}" target="_blank" rel="noopener" download>⬇ 下载原文</a>`
    : `<a class="mini" href="${esc(src.url||f.url)}" target="_blank" rel="noopener">↗ 打开原文</a>`;
  const local = f.stored
    ? `<a class="mini ghost" href="/api/attachment/file?stored=${encodeURIComponent(f.stored)}"
         target="_blank" rel="noopener" title="项目内已下载的副本：${esc(f.stored)}">📁 本地副本</a>`
    : '';
  // 解析状态：已解析出正文时给出「看解析正文」，并把首段直接摊开——
  // 「报名截止写在哪」这个问题，用户不必下载 PDF 就能先看一眼。
  let parsed = '';
  if(f.parsed){
    const bits = [`已解析 ${f.parsed_chars} 字`];
    if(f.tables) bits.push(`${f.tables} 张表`);
    if(f.images) bits.push(`${f.images} 张图`);
    if(f.ocr_used) bits.push(`OCR ${f.ocr_used} 张`);
    if(f.parser) bits.push(f.parser);
    parsed = `<div class="why ok">✅ ${esc(bits.join(' · '))}
      <span class="lnk" data-att="${f.attachment_id}">看解析正文 →</span></div>
      ${f.preview?`<div class="meta att-prev">${esc(f.preview)}</div>`:''}`;
  }else if(f.parse_error){
    parsed = `<div class="why">解析失败：${esc(f.parse_error)}</div>`;
  }else if(f.parse_note){
    parsed = `<div class="why">${esc(f.parse_note)}</div>`;
  }
  return `<div class="acard file">
    <div class="hd"><span class="nm">${fileIcon(f.file_kind)} ${esc(f.file_name)}</span>
      <span class="chipm">${esc(f.file_kind)}</span>
      ${f.parsed?`<span class="chipm" title="附件正文已入库，参与检索与回答">已解析</span>`:''}</div>
    ${src.title?`<div class="meta">出处通知：${esc(src.title)}</div>`:''}
    ${parsed}
    ${f.note?`<div class="why">${esc(f.note)}</div>`:''}
    <div class="foot">${dl}${local}<span class="src">${esc(srcLabel)}</span></div>
  </div>`;
}
async function showAttachment(id, host){
  if(!id) return;
  host = host || document.body;
  const box = document.createElement('div');
  box.className = 'att-modal';
  box.innerHTML = '<div class="att-box"><div class="att-hd"><span class="spin"></span> '
    + '正在读取解析结果…</div></div>';
  host.appendChild(box);
  box.onclick = e=>{ if(e.target === box) box.remove(); };
  try{
    const r = await fetch('/api/attachment?id='+encodeURIComponent(id));
    const d = await r.json();
    if(d.error){
      box.querySelector('.att-box').innerHTML = '<div class="att-hd">✗ '+esc(d.error)+'</div>';
      return;
    }
    const bits = [];
    if(d.kind) bits.push(d.kind);
    if(d.bytes) bits.push(Math.round(d.bytes/1024)+'KB');
    if(d.parser) bits.push(d.parser);
    if(d.tables) bits.push(d.tables+' 张表');
    if(d.ocr_used) bits.push('OCR '+d.ocr_used+' 张（'+d.ocr_chars+' 字）');
    bits.push(d.chars+' 字');
    box.querySelector('.att-box').innerHTML =
      `<div class="att-hd"><b>${esc(d.filename||'附件')}</b>
         <span class="src">${esc(bits.join(' · '))}</span>
         <span class="lnk" data-x="1" style="margin-left:auto">关闭 ✕</span></div>
       ${d.note?`<div class="why">${esc(d.note)}</div>`:''}
       ${d.error?`<div class="why">解析失败：${esc(d.error)}</div>`:''}
       <pre class="att-text">${esc(d.text||'（没有解析出正文）')}${d.truncated?'\n\n…（已截断，完整内容见本地副本）':''}</pre>
       <div class="foot">
         <a class="mini" href="${esc(d.url||'#')}" target="_blank" rel="noopener">⬇ 下载原文</a>
         ${d.stored?`<a class="mini ghost" href="/api/attachment/file?stored=${encodeURIComponent(d.stored)}" target="_blank" rel="noopener">📁 本地副本</a>`:''}
       </div>`;
    box.querySelector('[data-x]').onclick = ()=> box.remove();
  }catch(e){
    box.querySelector('.att-box').innerHTML = '<div class="att-hd">✗ 读取失败：'+esc(String(e))+'</div>';
  }
}
function timeCard(t){
  return `<div class="acard file" style="border-left-color:var(--pri)">
    <div class="hd"><span class="nm">${t.is_deadline?'⏰ ':'🗓 '}${esc(t.label)}：${esc(t.date)}</span></div>
    ${t.activity?`<div class="meta">活动：${esc(t.activity)}</div>`:''}
    ${t.source_title?`<div class="meta">依据：${esc(t.source_title)}</div>`:''}
    <div class="foot">
      ${t.source_url?`<a class="src" href="${esc(t.source_url)}" target="_blank" rel="noopener">看通知 ↗</a>`:''}
      <span class="src">${t.source_n?('['+t.source_n+']'):''}</span></div>
  </div>`;
}
/* 「已在篮中」直接读计算器那份 localStorage 状态，两个页面永远一致 */
function inBasket(id){
  try{
    const raw = localStorage.getItem('scau-calc-state-v1');
    if(!raw) return false;
    const st = JSON.parse(raw);
    return (st.basket||[]).some(b=>b.activity_id===id);
  }catch(e){ return false; }
}
function addCardToBasket(btn){
  const id = btn.dataset.add, name = btn.dataset.name || '';
  let ok = false;
  if(window.__calc && window.__calc.addToBasket){
    ok = window.__calc.addToBasket({activity_id:id, name:name, quantity:1});
  }
  if(!ok){
    // 计算器还没加载过：自己写同一份状态，格式与 calcpages 的 state 完全一致
    try{
      const raw = localStorage.getItem('scau-calc-state-v1');
      const st = raw ? JSON.parse(raw) : {scores:{},retakes:[],metrics:{},basket:[]};
      st.basket = st.basket || [];
      if(!st.basket.some(b=>b.activity_id===id)){
        st.basket.push({activity_id:id, achieve:'', quantity:1, name:name});
        localStorage.setItem('scau-calc-state-v1', JSON.stringify(st));
        ok = true;
      }
    }catch(e){}
  }
  if(!ok) return;
  btn.disabled = true; btn.classList.add('ghost'); btn.textContent = '✓ 已在活动篮';
  toast('已加入活动篮：<b>'+esc(name||id)+'</b>'
        + '<a onclick="go(\'calc\',\'acts\')">去计算器看加分 →</a>');
}
function renderCards(a, cards){
  if(!a || !a.cards) return;
  const acts = (cards&&cards.activities)||[], files=(cards&&cards.files)||[],
        times=(cards&&cards.times)||[];
  if(!acts.length && !files.length && !times.length){
    a.cards.innerHTML = '';
    return;
  }
  const st = (cards&&cards.stats)||{};
  const head = `<div class="cards-head">🧩 卡片
    <span class="n">活动 ${acts.length}（其中 ${st.matched||0} 项对上了已核验名录）`
    + ` · 附件 ${files.length} · 关键时间 ${times.length}</span>
    <span style="margin-left:auto"></span>
    <span class="n">分数与时间来自证据与名录，不是模型生成的</span></div>`;
  a.cards.innerHTML = head + `<div class="cards-grid">`
    + acts.map(activityCard).join('') + files.map(fileCard).join('')
    + times.map(timeCard).join('') + `</div>`;
  a.cards.querySelectorAll('button[data-add]').forEach(b=>{
    b.onclick = ()=> addCardToBasket(b);
  });
  a.cards.querySelectorAll('[data-att]').forEach(el=>{
    el.onclick = ()=> showAttachment(el.dataset.att);
  });
}
function chatLog(a, text){
  if(!a.lines) return;
  a.lines.textContent += text + '\n';
  a.trace.classList.remove('hide');
  chatScrollDown();
}
function chatBusy(on){
  CHAT_STATE.busy = on;
  const go = $('#go'), find = $('#find');
  if(go){ go.disabled = on; go.textContent = on ? '■' : '➤'; }
  if(find) find.disabled = on;
}

async function chatSearch(){
  const t = $('#q'); if(!t) return;
  const q = t.value.trim(); if(!q || CHAT_STATE.busy) return;
  chatUser(q); t.value=''; chatResize(); chatSync();
  const a = chatAnswer();
  if(a.wait) a.wait.innerHTML = '<span class="spin"></span> 检索中…';
  try{
    const r = await fetch('/api/search?k=15&q='+encodeURIComponent(q));
    const d = await r.json();
    if(a.wait) a.wait.remove();
    if(!d.hits || !d.hits.length){
      a.body.innerHTML = '没有命中。试试更短的关键词（2-6 字），或先跑抓取。';
    }else{
      a.body.innerHTML = `<h2>检索命中 ${d.hits.length} 条（库内 ${d.total} 篇）</h2>` +
        d.hits.map(h=>`<div class="hit"><div class="t">${esc(h.title)}</div>
          <div class="m">${h.pub_date||'无日期'} · ${esc(h.college||h.site_name||'-')} · <a href="${h.url}" target="_blank" rel="noopener">原文</a></div>
          <div class="s">${esc(h.snippet)}</div></div>`).join('');
    }
  }catch(e){
    if(a.wait) a.wait.remove();
    a.body.innerHTML = '<div class="err-line" style="color:var(--err)">检索失败：'+esc(String(e))+'</div>';
  }
  chatScrollDown();
}

function chatAsk(){
  const t = $('#q'); if(!t) return;
  const q = t.value.trim(); if(!q || CHAT_STATE.busy) return;
  const rounds = ($('#rounds')||{}).value || '2';
  const dry = ($('#dry') && $('#dry').checked) ? '1' : '0';
  chatBusy(true);
  chatUser(q); t.value=''; chatResize(); chatSync();
  const a = chatAnswer();
  if(a.wait) a.wait.innerHTML = '<span class="spin"></span> ' +
    (dry==='1' ? '仅检索验证（不调用模型）…' : '正在拆解问题、检索语料与公网，然后生成答案…');
  chatLog(a, (dry==='1'?'[仅检索验证] ':'') + '开始：' + q);
  const es = new EventSource('/api/ask?dry='+dry+'&rounds='+rounds+'&q='+encodeURIComponent(q));
  es.addEventListener('trace', e=>{ try{ chatLog(a, JSON.parse(e.data).text); }catch(err){} });
  es.addEventListener('cards', e=>{
    let d = {}; try{ d = JSON.parse(e.data); }catch(err){}
    a.cardData = d;
    renderCards(a, d);
    chatScrollDown();
  });
  es.addEventListener('answer', e=>{
    let d = {}; try{ d = JSON.parse(e.data); }catch(err){}
    if(a.wait) a.wait.remove();
    a.body.innerHTML = mdChat(d.text)
      + (d.error ? `<div class="err-line" style="color:var(--err)">生成异常：${esc(d.error)}</div>` : '');
    if(d.citations) a.refs.innerHTML = '<strong>引用来源</strong><div>'+mdChat(d.citations).replace(/\n/g,'')+'</div>';
    if(d.usage) chatLog(a, d.usage);
    /* cards 事件可能先到（后端先推 answer 再推 cards，但 SSE 顺序在极端情况下
       会交错），这里兜一次 */
    if(a.cardData) renderCards(a, a.cardData);
    chatScrollDown();
  });
  es.addEventListener('done', ()=>{ es.close(); chatBusy(false); chatPills(); });
  es.onerror = ()=>{ es.close(); chatBusy(false); chatLog(a, '连接中断'); };
}

function chatBind(){
  const t = $('#q');
  if(t){
    t.addEventListener('input', chatResize);
    t.addEventListener('keydown', e=>{
      if(e.key === 'Enter' && !e.shiftKey){ e.preventDefault(); chatAsk(); }
    });
    t.focus();
    chatResize();
  }
  const go = $('#go'); if(go) go.onclick = chatAsk;
  const find = $('#find'); if(find) find.onclick = chatSearch;
  $$('.ex, .sug').forEach(el=>el.onclick = ()=>{
    const q = $('#q'); if(!q) return;
    q.value = el.dataset.q || ''; chatResize(); q.focus();
  });
  chatSync();
}

window.__chat = {ask: chatAsk, search: chatSearch, bind: chatBind, sync: chatSync,
                 resize: chatResize, status: chatPills, md: mdChat,
                 /* 卡片渲染单独暴露：假 DOM 冒烟测试（data/research/smoke_ui.py）
                    与后续「点历史回答里的卡片」都要用得到。 */
                 renderCards: renderCards, addCardToBasket: addCardToBasket,
                 inBasket: inBasket, toast: (typeof toast === 'function' ? toast : null)};
"""

# --------------------------------------------------------------------------- #
# 视图容器
# --------------------------------------------------------------------------- #
CHAT_VIEW_HTML = CHAT_VIEW_MARKUP


def views_html() -> str:
    """三个视图容器（对话 / 计算器 / 口径说明），供外壳填进 #appmain。"""
    return "\n".join([
        CHAT_VIEW_MARKUP,
        calc_view_html(),
        docs_view_html(),
    ])


def view_scripts() -> str:
    return "\n".join([appshell.SHELL_JS, CHAT_JS, calc_view_js()])


def build_page() -> str:
    """整站 HTML（外壳 + 三个视图 + 三段脚本）。"""
    views = views_html()
    scripts = view_scripts()
    head, _, tail = appshell.shell_html(appshell.nav_html(), views).rpartition("</body>")
    return head + "<script>\n" + scripts + "\n</script>\n</body>" + tail


# 兼容旧名字：以前调用方直接取一个整页常量
__all__ = ["build_page", "views_html", "view_scripts", "CHAT_VIEW_MARKUP"]
