/* 对话卡片：活动 / 赛事、附件、关键时间；只负责渲染与入篮。 */
import { esc } from '../../shared/dom.js';
import { requestJSON } from '../../shared/api.js';
import { n2s } from '../../shared/format.js';
import { toast } from '../../shared/toast.js';
import { addToBasket, inBasket } from '../calc/state.js';

/* ------------------------------------------------------------------ *
 * 卡片渲染：活动 / 赛事、附件、关键时间
 *
 * 卡片数据全部由后端 wayfinder/qa/cards.py 从证据与已核验名录里抽出来
 * （分数与时间都不是模型编的）。这里只负责画，以及把「加入活动篮」
 * 接到计算器的同一份 localStorage 状态上。
 * ------------------------------------------------------------------ */
function fileIcon(kind){
  return ({pdf:'📕', doc:'📄', docx:'📄', xls:'📊', xlsx:'📊',
           ppt:'📽', pptx:'📽', zip:'🗜', rar:'🗜', csv:'📊'})[kind] || '📎';
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
      <span class="chipm">${esc(f.file_label || f.file_kind)}</span>
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
export function renderCards(a, cards){
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
