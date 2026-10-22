/* 对话内容渲染：Markdown、[n] 引用、右侧来源栏。 */
import { $, esc } from '../../shared/dom.js';

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
export function mdChat(src, opts){
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
export const SOURCES = {
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
export function SBOX(){ return $('#sources-body'); }
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
export function chatSourcesRender(){
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
export function chatSourcesToggle(open){
  const el = $('#sources'); if(!el) return;
  SOURCES.open = (open === undefined) ? !SOURCES.open : !!open;
  el.classList.toggle('closed', !SOURCES.open);
  try{ localStorage.setItem('scau-src', SOURCES.open ? '1' : '0'); }catch(e){}
}
/* 右栏能不能并排摆在正文右边（而不是浮在正文上）：
   可用宽度 = 窗口宽 − 左侧栏（>820px 时它占一列：展开 248 / 收起 56；更窄时它本身是浮层），
   够放「正文列 760 + 正文两侧内边距 40 + 右栏 248 = 1048px」才并排。
   这就是 shell.css 里那两段 @media（1295 / 1104）的算法，改一边得改另一边。 */
export function sourcesInline(){
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
export function sourcesOpenPref(){
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
export function chatBindCites(scope, ans){
  if(!ans) return;
  ans.querySelectorAll('a.cite[data-cite]').forEach(a=>{
    if(a._citeBound) return;
    a._citeBound = true;
    const n = a.dataset.cite;
    a.onclick = e=>{ e.preventDefault(); chatCiteJump(n); };
    a.onkeydown = e=>{ if(e.key === 'Enter' || e.key === ' '){ e.preventDefault(); chatCiteJump(n); } };
  });
}
