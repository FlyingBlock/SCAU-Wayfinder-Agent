/* ===================== 主页对话：输入、SSE 订阅与卡片渲染 ===================== */
import { $, esc } from '../../shared/dom.js';
import { getJSON, requestJSON } from '../../shared/api.js';
import { n2s } from '../../shared/format.js';
import { toast } from '../../shared/toast.js';
import { on } from '../../shared/events.js';
import { currentView } from '../../router.js';
import { openSettings } from '../settings/index.js';
import { addToBasket, inBasket } from '../calc/state.js';

const CHAT_STATE = { busy:false };

/* 正文里只留 [n] 标号：标号点开是右侧「引用来源」栏里的那一条。
   没有拿到元数据（还没到 citations 事件 / 模型引了不存在的编号）时
   退化成不可点的数字，不硬编造链接。 */
function citeChip(n){
  const r = SOURCES.refs[String(n)];
  if(r && r.url)
    return `<a class="cite" data-cite="${esc(n)}" role="link" tabindex="0"
              title="${esc(r.title||'引用来源')}">[${esc(n)}]</a>`;
  /* 流式阶段正文里先冒出 [3]，但带标题/链接的来源列表要等最后的 answer 事件。
     先在右栏占个位，别让用户对着一个没有下文的 [3]。 */
  SOURCES.previewMark(n);
  return `<span class="cite miss" title="本次检索里没有第 ${esc(n)} 条来源">[${esc(n)}]</span>`;
}
/* 模型有时仍会把网址写进正文（prompt 已明确要求不写）。它们一律收进右栏，
   正文只留下已经出现的 [n] 标号，避免一屏乱糟糟的长链接。 */
const RE_URL = /(https?:\/\/[^\s<>"'）】，。；、]+)/g;
function trimUrl(u){ return String(u||'').replace(/[.,;:!?)\]}>'"”’]+$/,''); }
function stripUrls(t){
  return String(t||'').replace(RE_URL, u=>{
    const clean = trimUrl(u);
    const tail = u.slice(clean.length);
    const n = SOURCES.refByUrl(clean) || SOURCES.previewUrl(clean);
    SOURCES.noteStripped(clean);          /* 按 URL 去重：整段重画时不会重复计数 */
    return (n ? '[' + n + ']' : '') + tail;
  });
}
/* 流式输出时，行尾那个「还没写完的网址」先别画进正文，
   否则每来一个字符都会在正文里闪一下半截链接（最后也会被收走）。 */
function trimTrailingUrl(t){
  return String(t||'').replace(/https?:\/\/[^\s<>"'）】，。；、]*$/,'');
}

/* 极简 markdown 渲染：标题/粗体/表格/列表/引用编号 */
function mdChat(src, opts){
  opts = opts || {};
  const streaming = !!opts.streaming;
  const useCites = opts.cites !== false;
  const body = streaming ? trimTrailingUrl(src) : (src||'');
  const lines = body.split("\n"); let out=[], i=0, tbl=[];
  const push = h => { if(out.length) out.push(''); out.push(h); };
  const inline = t => {
    let s = esc(t)
      .replace(/\[([^\]\n]{1,60})\]\(\s*(?:https?:\/\/|www\.)[^)\s]+\s*\)/g, '$1');
    if(opts.stripLinks !== false) s = stripUrls(s);
    if(useCites){
      s = s.replace(/\[\^?\d+(?:\]\[\^?\d+)*\]/g, m=>{
        const nums = m.match(/\d+/g) || [];
        return nums.map(citeChip).join('');
      });
    }
    return s
      .replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>')
      .replace(/`([^`]+)`/g,'<code>$1</code>')
      .replace(/(https?:\/\/[^\s<)]+)/g,'<a href="$1" target="_blank" rel="noopener">$1</a>');
  };
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
    if(/^###\s+/.test(l)) push('<h3>'+inline(l.replace(/^###\s+/,''))+'</h3>');
    else if(/^##\s+/.test(l)) push('<h2>'+inline(l.replace(/^##\s+/,''))+'</h2>');
    else if(/^#\s+/.test(l)) push('<h2>'+inline(l.replace(/^#\s+/,''))+'</h2>');
    else if(/^\s*[-*]\s+/.test(l)) push('<div style="margin:3px 0 3px 18px">• '+inline(l.replace(/^\s*[-*]\s+/,''))+'</div>');
    else if(l.trim()==='') out.push('');
    else push('<div>'+inline(l)+'</div>');
    i++;
  }
  flushTbl();
  return out.join('\n');
}

/* ------------------------------------------------------------------ *
 * 右侧「引用来源」栏
 *
 * 后端在两处给出可点的来源：
 *   · /api/ask 的 `answer.citations` —— 本次回答引用的全部证据（带编号）；
 *   · /api/search 的 `hits` —— 「只检索不生成」时命中的那些文章。
 * 正文里只画 [n]；所有 URL 都进这一栏。
 * ------------------------------------------------------------------ */
const SOURCES = {
  refs:{}, preview:{}, hits:[], trace:'', usage:'',
  stripped:0, kind:'', max:0, open:true,
  reset(){ this.refs={}; this.preview={}; this._pv={}; this._seen={}; this.hits=[];
           this.trace=''; this.usage=''; this.stripped=0; this.kind=''; this.max=0;
           this._sig=''; this._stripNote=false; },
  /* 正文里出现过的裸网址（按 URL 去重 —— 流式阶段整段会重画很多次） */
  noteStripped(url){
    if(!this._seen) this._seen = {};
    if(this._seen[url]) return;
    this._seen[url] = true;
    this.stripped++;
  },
  /* 完整列表（后端给的，带标题/日期/来源） */
  setList(list){
    const map = {};
    (list||[]).forEach(r=>{ if(r && r.n != null) map[String(r.n)] = r; });
    this.refs = map;
    this.max = 0;
    Object.keys(map).forEach(k=>{ this.max = Math.max(this.max, +k || 0); });
    this.kind = 'answer';
    /* 正式列表到了：把流式阶段的占位（[n] 但还没有详情）删掉，
       但正文里出现的裸网址（loose）保留在列表里。 */
    const rest = {};
    Object.keys(this.preview).forEach(k=>{
      const keep = this._pv && this._pv[k];
      if(keep) rest[k] = true;
    });
    this.preview = rest;
    this._sig = '';                       /* 强制重画一次 */
  },
  /* 兼容极简写法 "[1] 标题 — https://…"（老客户端 / 手工 SSE 测试） */
  setText(text){
    const map = {};
    String(text||'').split("\n").forEach(line=>{
      const m = /^\s*\[(\d+)\]\s*(.*)$/.exec(line);
      if(!m) return;
      const rest = m[2];
      const um = /(https?:\/\/\S+)/.exec(rest);
      map[m[1]] = {
        n:+m[1], url: um ? trimUrl(um[1]) : '',
        title: rest.replace(/(https?:\/\/\S+)/,'').replace(/\s*[—-]\s*$/,'').trim(),
        pub_date:'', source:'site', tag:'校内', stale:false,
      };
    });
    this.refs = map;
    this.max = Object.keys(map).reduce((a,k)=>Math.max(a, +k||0), 0);
    this.kind = 'answer';
  },
  /* 流式阶段：正文里先冒出 [3]，但详细来源要等 citations 事件。
     正文里出现的裸网址（模型没听话时）也在这里占一个号，等 citations
     到了再按网址替换成真实编号。 */
  previewMark(n){
    const k = String(n);
    this.preview[k] = true;
    this.max = Math.max(this.max, +k || 0);
  },
  refByUrl(url){
    const t = trimUrl(url);
    const hit = Object.values(this.refs).find(r=>r.url && trimUrl(r.url) === t);
    return hit ? hit.n : 0;
  },
  previewUrl(url){
    if(!this._pv) this._pv = {};
    if(this.kind === 'search') return 0;
    if(this._pv[url]) return this._pv[url];
    const n = (this.max || Object.keys(this.preview).length) + 1;
    this.max = n;
    this._pv[url] = n;
    this.refs[String(n)] = {n:n, url:url, title:'模型在正文里给出的链接', pub_date:'',
                            source:'', tag:'', stale:false, loose:true};
    return n;
  },
};
const srcEsc = esc;
function SBOX(){ return $('#sources-body'); }
function srcItemHtml(r, cls){
  const ti = r && r.title ? srcEsc(r.title) : (r && r.url ? srcEsc(r.url) : '（未命名来源）');
  const chips = [];
  if(r && r.pub_date) chips.push(`<span class="chipm">${srcEsc(r.pub_date)}</span>`);
  if(r && r.tag) chips.push(`<span class="chipm">${srcEsc(r.tag)}</span>`);
  if(r && r.stale) chips.push(`<span class="chipm" style="color:var(--warn)">⚠️可能已过期</span>`);
  if(r && r.loose) chips.push('<span class="chipm">正文里的直链</span>');
  return `<div class="src-item ${esc((cls||'') + (r && r.stale ? ' stale' : ''))}">
    <div class="h">${r && r.n != null ? `<span class="idx">[${srcEsc(r.n)}]</span>` : ''}
      <span class="ti">${ti}</span></div>
    ${chips.length ? `<div class="chips">${chips.join('')}</div>` : ''}
    ${r && r.url ? `<a class="lk" href="${esc(r.url)}" target="_blank"
                       rel="noopener">${srcEsc(shortUrl(r.url))} ↗</a>` : ''}
  </div>`;
}
function shortUrl(u){
  const s = String(u||'');
  return s.length > 96 ? s.slice(0,60) + '…' + s.slice(-30) : s;
}
function chatSourcesRender(){
  const box = SBOX();
  if(!box) return;
  const refs = Object.values(SOURCES.refs).sort((a,b)=>(a.n||0)-(b.n||0));
  const previewIds = Object.keys(SOURCES.preview).map(Number).sort((a,b)=>a-b);
  const hits = SOURCES.hits || [];
  /* 流式输出时每来一段正文都会调到这里（几百次），内容没变就别重画 ——
     否则既浪费，又会把用户正在右栏里选中的文字弄丢。 */
  const sig = [refs.map(r=>r.n + (r.url||'') + (r.title||'')).join(','),
               previewIds.join(','), hits.map(h=>h.n + h.url).join(','),
               SOURCES.trace.length, SOURCES.stripped].join('|');
  if(sig === SOURCES._sig && box.innerHTML) return;
  SOURCES._sig = sig;

  const secs = [];
  if(refs.length)
    secs.push(`<div class="src-grp"><div class="src-sec">本次回答引用 ${refs.length} 条</div>`
      + refs.map(r=>srcItemHtml(r, r.source === 'web' ? 'web' : '')).join('') + '</div>');
  if(previewIds.length)
    secs.push(`<div class="src-grp"><div class="src-sec">正文中已引用</div>`
      + previewIds.map(n=>`<div class="src-item ghost"><div class="h">
          <span class="idx">[${esc(n)}]</span><span class="ti">来源详情读取中…</span></div></div>`)
        .join('') + '</div>');
  if(hits.length)
    secs.push(`<div class="src-grp"><div class="src-sec">检索命中 ${hits.length} 条</div>`
      + hits.map(h=>srcItemHtml(Object.assign({}, h, {
          tag: h.college || h.site_name || '',
        }), 'hit')).join('') + '</div>');
  if(SOURCES.stripped && !SOURCES._stripNote){
    SOURCES._stripNote = true;
    secs.push(`<div class="src-item ghost">模型在正文里写了 ${SOURCES.stripped} 个网址，
      已按界面口径收进本栏（正文只留 [n]）。</div>`);
  }
  if(SOURCES.trace)
    secs.push(`<details class="src-grp" open><summary class="src-sec"
        style="cursor:pointer">检索过程</summary>
      <pre class="src-trace">${srcEsc(SOURCES.trace)}</pre></details>`);
  if(!secs.length)
    secs.push('<div class="src-item ghost">还没有检索结果 —— 提一个问题，找到的资料链接会全部列在这里。</div>');
  box.innerHTML = secs.join('');
  const n = $('#sources-count');
  if(n) n.textContent = '· ' + (refs.length || hits.length || 0) + ' 条';
}
function chatSourcesToggle(open){
  const el = $('#sources'); if(!el) return;
  SOURCES.open = (open === undefined) ? !SOURCES.open : !!open;
  el.classList.toggle('closed', !SOURCES.open);
  try{ localStorage.setItem('scau-src', SOURCES.open ? '1' : '0'); }catch(e){}
}
/* 右栏能不能并排摆在正文右边（而不是浮在正文上）：
   可用宽度 = 窗口宽 − 左侧栏（>820px 时它占一列：展开 248 / 收起 56；更窄时它本身是浮层），
   够放「正文列 760 + 正文两侧内边距 40 + 右栏 248 = 1048px」才并排。
   这就是 shell.css 里那两段 @media（1295 / 1104）的算法，改一边得改另一边。 */
function sourcesInline(){
  let w = 0;
  try{
    const vw = window.innerWidth || 0;
    let sw = 0;
    if(vw > 820) sw = $('#sidebar').getBoundingClientRect().width || 0;
    w = vw - sw;
  }catch(e){ w = 0; }
  /* 量不到宽度（假 DOM）时按宽屏处理：右栏默认展开，跟以前一样 */
  return !w || w >= 1048;
}
function sourcesOpenPref(){
  try{
    const saved = localStorage.getItem('scau-src');
    if(saved !== null) return saved !== '0';
  }catch(e){}
  /* 没存过偏好时按可用宽度给默认值：并排放不下时右栏是浮层，默认展开会盖住正文，
     所以默认收起，点标题栏或 [n] 再展开；宽屏下右栏是正文旁边的一列，默认展开。 */
  return sourcesInline();
}
/* 点正文里的 [n] → 展开右栏并滚到那一条 */
function chatCiteJump(n){
  chatSourcesToggle(true);
  const box = $('#sources-body'); if(!box) return;
  const items = Array.from(box.querySelectorAll('.src-item'));
  const hit = items.find(el=>{
    const idx = el.querySelector('.idx');
    return idx && idx.textContent === '[' + n + ']';
  });
  if(hit && hit.scrollIntoView) hit.scrollIntoView({block:'center'});
}
/* 每次重画正文之后重新接上 [n] 的点击（innerHTML 会把旧监听器一起丢掉） */
function chatBindCites(scope, ans){
  if(!ans) return;
  ans.querySelectorAll('a.cite[data-cite]').forEach(a=>{
    if(a._citeBound) return;
    a._citeBound = true;
    const n = a.dataset.cite;
    a.onclick = e=>{ e.preventDefault(); chatCiteJump(n); };
    a.onkeydown = e=>{ if(e.key === 'Enter' || e.key === ' '){ e.preventDefault(); chatCiteJump(n); } };
  });
}

function chatPills(){
  getJSON('/api/status').then(d=>{
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
  /* 并排放不下时右栏是浮层：切走对话视图就把它收起来，免得下次回到对话页盖着正文；
     宽屏下右栏是正文旁边的一列，用户收起/展开的选择要留住，别替他改。 */
  if(currentView() !== 'chat' && !sourcesInline()
     && !$('#sources').classList.contains('closed'))
    chatSourcesToggle(false);
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
    + '<div class="body"></div><div class="cards-wrap"></div>'
    + '</div>';
  box.appendChild(el);
  chatScrollDown();
  const ans = el.querySelector('.ans');
  return {root:el, ans:ans, wait:ans.querySelector('.wait'), body:ans.querySelector('.body'),
          cards:el.querySelector('.cards-wrap')};
}

/* ------------------------------------------------------------------ *
 * 卡片渲染：活动 / 赛事、附件、关键时间
 *
 * 卡片数据全部由后端 wayfinder/qa/cards.py 从证据与已核验名录里抽出来
 * （分数与时间都不是模型编的）。这里只负责画，以及把「加入活动篮」
 * 接到计算器的同一份 localStorage 状态上。
 * ------------------------------------------------------------------ */
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
    const {data:d} = await requestJSON('/api/attachment?id='+encodeURIComponent(id));
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
/* 活动篮的唯一状态在 features/calc/state.js；对话页只调用它，不碰存储格式。 */
function addCardToBasket(btn){
  const id = btn.dataset.add, name = btn.dataset.name || '';
  if(!addToBasket({activity_id:id, name:name, quantity:1})) return;
  btn.disabled = true; btn.classList.add('ghost'); btn.textContent = '✓ 已在活动篮';
  toast('已加入活动篮：<b>'+esc(name||id)+'</b>'
        + '<a href="#/calc/acts">去计算器看加分 →</a>');
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
  /* 检索过程不再塞进回答正文下方（那里只放答案），改到右侧「引用来源」栏底部，
     收在一个可折叠的「检索过程」里。 */
  SOURCES.trace += (SOURCES.trace ? '\n' : '') + text;
  chatSourcesRender();
}
function chatBusy(on){
  CHAT_STATE.busy = on;
  const go = $('#go'), find = $('#find');
  if(go){ go.disabled = on; go.textContent = on ? '■' : '➤'; }
  if(find) find.disabled = on;
}

/* 流式输出：正文每变一次就整段重渲染一遍 markdown。
   代价是 O(长度) 的字符串处理，所以按 60ms 节流 —— 用户看到的是「一个字一个字
   往外蹦」，而不是页面卡顿。 */
const STREAM = {
  raf:0, dirty:false,
  paint(a){
    if(!a || !a.body) return;
    this.dirty = false;
    a.body.innerHTML = mdChat(a.text, {streaming:a.streaming}) +
      (a.streaming ? '<span class="cursor"></span>' : '');
    chatBindCites(a.ans, a.body);
    chatScrollDown();
  },
  schedule(a){
    if(!a || !a.body) return;
    this.dirty = true;
    if(a._raf) return;
    a._raf = setTimeout(()=>{ a._raf = 0; if(this.dirty) this.paint(a); }, 60);
  },
};

async function chatSearch(){
  const t = $('#q'); if(!t) return;
  const q = t.value.trim(); if(!q || CHAT_STATE.busy) return;
  chatUser(q); t.value=''; chatResize(); chatSync();
  SOURCES.reset(); SOURCES.kind = 'search'; chatSourcesRender();
  const a = chatAnswer();
  a.streaming = false; a.citesOn = false;
  if(a.wait) a.wait.innerHTML = '<span class="spin"></span> 检索中…';
  try{
    const d = await getJSON('/api/search?k=15&q='+encodeURIComponent(q));
    if(a.wait) a.wait.remove();
    if(!d.hits || !d.hits.length){
      a.body.innerHTML = '没有命中。试试更短的关键词（2-6 字），或先跑抓取。';
    }else{
      /* 命中列表里只留标题/日期/栏目，链接进右栏（正文不再出现长 URL） */
      SOURCES.hits = d.hits.map((h, i)=>Object.assign({n:i+1}, h));
      a.body.innerHTML = `<h2>检索命中 ${d.hits.length} 条（库内 ${d.total} 篇）</h2>`
        + d.hits.map((h,i)=>`<div class="hit"><div class="t">${esc(h.title)}
            <span class="src-n">[${i+1}]</span></div>
            <div class="m">${esc(h.pub_date||'无日期')} · ${esc(h.college||h.site_name||'-')}
              · 链接见右侧「引用来源」栏</div>
            <div class="s">${esc(h.snippet)}</div></div>`).join('');
      chatSourcesRender();
    }
  }catch(e){
    if(a.wait) a.wait.remove();
    a.body.innerHTML = '<div class="err-line" style="color:var(--err)">检索失败：'+esc(String(e))+'</div>';
  }
  chatScrollDown();
}

/** 把后端结构化 trace 变成检索过程文案；展示顺序与措辞属于前端。 */
function traceText(step, data){
  const labels = {
    decompose: '① 意图分解', retrieve: '② 检索', retrieved: '   命中',
    gaps: '④ 缺口检测', evidence: '⑥ 证据聚合',
  };
  data = data || {};
  if(step === 'decompose'){
    const lines = [`${labels[step]}：${(data.subqueries||[]).length} 条子查询`];
    (data.subqueries||[]).forEach(x=>lines.push(`    [${x.scope}] ${x.query}`));
    return lines.join('\n');
  }
  if(step === 'retrieve')
    return `${labels[step]} 第 ${data.round} 轮：${(data.queries||[]).join('；')}`;
  if(step === 'retrieved')
    return `${labels[step]} 第 ${data.round} 轮 +${data.new}（累计 ${data.total}）`;
  if(step === 'gaps'){
    const missing = data.missing || [];
    return `${labels[step]}：` + (missing.length
      ? '补 ' + missing.map(x=>x.query).join('；') : '证据已足够');
  }
  if(step === 'evidence') return `${labels[step]}：${data.count} 条进入生成`;
  if(step === 'cards'){
    const st = data.stats || {};
    return `⑦ 卡片：活动 ${st.activities||0} 张（命中已核验名录 ${st.matched||0}）`
      + ` · 附件 ${st.files||0} 个 · 时间 ${st.times||0} 条`;
  }
  return step;
}

function chatAsk(){
  const t = $('#q'); if(!t) return;
  const q = t.value.trim(); if(!q || CHAT_STATE.busy) return;
  const rounds = ($('#rounds')||{}).value || '2';
  const dry = ($('#dry') && $('#dry').checked) ? '1' : '0';
  chatBusy(true);
  chatUser(q); t.value=''; chatResize(); chatSync();
  SOURCES.reset(); chatSourcesRender();
  const a = chatAnswer();
  a.text = ''; a.streaming = true; a.citesOn = false; a._t0 = Date.now();
  if(a.wait) a.wait.innerHTML = '<span class="spin"></span> ' +
    (dry==='1' ? '仅检索验证（不调用模型）…' : '正在拆解问题、检索语料与公网…');
  chatLog(a, (dry==='1'?'[仅检索验证] ':'') + '开始：' + q);
  const es = new EventSource('/api/ask?dry='+dry+'&rounds='+rounds+'&q='+encodeURIComponent(q));
  es.addEventListener('trace', e=>{
    try{
      const d = JSON.parse(e.data);
      chatLog(a, traceText(d.step, d.data));
    }catch(err){}
  });
  es.addEventListener('cards', e=>{
    let d = {}; try{ d = JSON.parse(e.data); }catch(err){}
    a.cardData = d;
    renderCards(a, d);
    chatScrollDown();
  });
  /* 流式正文：每来一段就重画一次 */
  es.addEventListener('answer_delta', e=>{
    let d = {}; try{ d = JSON.parse(e.data); }catch(err){}
    if(!d.text) return;
    if(a.wait) a.wait.remove();
    if(!a._firstAt) a._firstAt = Date.now() - a._t0;
    a.streaming = true; a.text += d.text;
    chatSourcesRender();           /* 正文里新出现的 [n] 先在右栏占位 */
    STREAM.schedule(a);
  });
  es.addEventListener('answer_end', ()=>{
    a.streaming = false;
    if(a._raf){ clearTimeout(a._raf); a._raf = 0; }
    STREAM.paint(a);
  });
  es.addEventListener('answer', e=>{
    let d = {}; try{ d = JSON.parse(e.data); }catch(err){}
    if(a.wait) a.wait.remove();
    a.streaming = false;
    if(a._raf){ clearTimeout(a._raf); a._raf = 0; }
    /* answer 事件的 text 是后端手里那份权威正文：流式增量万一丢包（或中途退回了
       非流式重试），这里以它为准把正文对齐一次，避免显示的内容比引用来源少一截。 */
    if(d.text) a.text = d.text;
    if(d.dry){
      a.text = `### 仅检索验证（未调用 LLM）\n\n`
        + `共检索到 **${d.evidence_count || 0}** 条证据，链接在「引用来源」栏；`
        + `正文只保留 [n] 标号。\n\n`
        + `想判断检索质量，看来源栏的标题/日期/来源即可；`
        + `想连线看证据原文，点来源栏每条的链接。`;
    }
    /* citations 现在有两种形态：结构化数组（新）与纯文本（兼容老客户端） */
    if(Array.isArray(d.citations)){
      if(d.citations.length) SOURCES.setList(d.citations);
    }else if(typeof d.citations === 'string' && d.citations){
      SOURCES.setText(d.citations);
    }
    a.citesOn = true;
    a.body.innerHTML = mdChat(a.text, {streaming:false})
      + (d.error ? `<div class="err-line" style="color:var(--err)">生成异常：${esc(d.error)}</div>` : '');
    chatBindCites(a.ans, a.body);
    a.firstMs = a._firstAt || 0;
    if(d.usage){
      chatLog(a, d.usage);
      SOURCES.usage = d.usage;
    }
    if(d.text) chatLog(a, '正文 ' + d.text.length + ' 字符'
      + (a.firstMs ? ' · 首字 ' + a.firstMs + ' ms（流式）' : '（非流式）'));
    chatSourcesRender();
    if(a.cardData) renderCards(a, a.cardData);
    chatScrollDown();
    /* 留一份「这条回答刚落地的右栏」快照：下一条问题一来右栏就 reset 了，
       测试（tests/test_cards_api.py）事后读不到，只能当场记一份。 */
    SOURCES.lastAnswer = {html: (SBOX() ? SBOX().innerHTML : ''),
                          refs: Object.keys(SOURCES.refs).length,
                          stripped: SOURCES.stripped, firstMs: a.firstMs,
                          text: a.text || ''};
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
  const st = $('#sources-toggle');
  if(st) st.onclick = ()=> chatSourcesToggle();
  chatSourcesToggle(sourcesOpenPref());
  chatSourcesRender();
  chatSync();
  chatPills();
}

/* 设置保存后只发事件，对话页自己刷新状态，不反向依赖设置模块。 */
on('status:refresh', chatPills);

export { chatBind, chatSync, chatResize, chatPills, mdChat, renderCards };
