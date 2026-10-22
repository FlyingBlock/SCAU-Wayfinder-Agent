/* 活动篮视图：筛选、排序、卡片与赛事名录；通过 configureActivities 注入目录/网络。 */
import { $, $$, esc } from '../../shared/dom.js';
import { n2 } from '../../shared/format.js';
import { state, save } from './state.js';

let CTX = {
  getCatalog: () => null,
  setCatalog: () => {},
  api: async () => ({}),
  scheduleEval: () => {},
};

export function configureActivities(ctx){
  CTX = Object.assign(CTX, ctx || {});
}
const cat = () => CTX.getCatalog() || {};
let CURRENT = [];
let requestSeq = 0;

export const chanUnit = c => (cat() && cat().channel_units || {})[c] || '分';

// 把各通道得分渲染成「+X 分 / +Y 学分 / +Z 小时」，不混单位；
// 可按评分类别过滤（同一件事在综测和推免里分值不同，分开显示才不误导）。
function fmtChannels(obj, channels){
  const allow = new Set(channels || []);
  const parts = Object.entries(obj||{}).filter(([k,v])=>v && allow.has(k));
  if(!parts.length) return '<span class="pts zero">±0</span>';
  return parts.map(([k,v])=>{
    const neg = v < 0;
    return `${neg?'':'+'}${n2(v,2)} ${esc(chanUnit(k))}`
      +`<span class="src" style="display:inline"> ${esc(k)}</span>`;
  }).join('　');
}

export function fillFilters(){
  const cats = cat().categories||[], lvls = cat().levels||[];
  $('#f-cat').innerHTML = '<option value="">全部类别</option>' +
    cats.map(c=>`<option value="${esc(c)}">${esc(c)}</option>`).join('');
  $('#f-level').innerHTML = '<option value="">全部级别</option>' +
    lvls.map(c=>`<option value="${esc(c)}">${esc(c)}</option>`).join('');
  const apx = ((compMeta()||{}).appendix)||[];
  $('#f-appendix').innerHTML = '<option value="">全部附录</option>' +
    apx.filter(a=>a.count).map(a=>
      `<option value="${a.appendix}">附录${a.appendix} · ${esc(a.tier)} 类（${a.count} 项）</option>`).join('');
  ['#f-kind','#f-cat','#f-level','#f-appendix','#f-scored'].forEach(s=>$(s).onchange = renderActivities);
  $('#f-q').oninput = renderActivities;
}

// 综测/推免两套表各自的最高成就由后端 best_preview 算好，这里只读。
function actBestScore(act){
  const b = (act && act.best) || {};
  return {
    best: b.best || 0,
    bestAch: b.best_achieve || '',
    bestTuimian: b.best_tuimian || 0,
    bestAchTuimian: b.best_achieve_tuimian || '',
  };
}

/* ---------- 名录元信息 / 联网刷新 ---------- */
function compMeta(){ return (cat() && cat().competitions) || null; }
const actKind = a => a.list_kind || 'general';
const isComp = a => actKind(a)!=='general';

export function renderCompetitionHead(){
  const m = compMeta();
  if(!m){
    $('#comp-sub').textContent = '未加载到赛事名录';
    $('#comp-basis').innerHTML = '仓库自带的 <code>calcdata/competitions.json</code> 没读到，'+
      '下面只显示 <code>activities.json</code> 里的通用加分项。';
    $('#comp-sources').innerHTML = '';
    renderOnlinePanel();
    return;
  }
  const c = m.counts||{}, page = m.catalog_page||{}, online = m.online;
  $('#comp-sub').innerHTML = `内置 <b>${c.total||0}</b> 项具体赛事：`
    + `T 类 ${c.T||0} · A 类 ${c.A||0} · B 类 ${c.B||0}`
    + (c.online_added?` · <span style="color:var(--pri)">联网新增 ${c.online_added}</span>`:'');
  $('#comp-basis').innerHTML =
    `${esc(m.disclaimer||'')}<br>`
    + `名录页：<a href="${esc(page.url||'')}" target="_blank" rel="noopener">${esc(page.title||'')}</a>`
    + `（${esc(page.published||'')} 发布，${esc(page.site||'')}）<br>`
    + `加分档位依据：${esc(m.basis||'')}<br>`
    + `<b>怎么看卡片</b>：每张卡片标题旁是<b>名录序号</b>与<b>名录级别</b>（T/A/B 类），`
    + `下面「档位」写的是这个赛事用哪张加分表；卡片里的分数全部来自 `
    + `<code>calcdata/activities.json</code> 已核验的表格行，点「加入活动篮」即可实时累加。`;
  const links = (m.refresh_sources||[]).map(s=>
    `<div>· <a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title)}</a> `
    + `<span class="chip">${s.kind==='catalog'?'名录页':'通知栏目'}</span> ${esc(s.use||'')}</div>`).join('');
  $('#comp-sources').innerHTML =
    `<div>内置数据文件：<code>${esc(m.file||'')}</code>（更新于 ${esc(m.updated||'')}）</div>`
    + `<div style="margin-top:4px">「🔄 刷新联网」会按顺序抓这些页面：</div>${links}`
    + `<div style="margin-top:4px">联网结果缓存在 <code>data/cache/calc_competitions.json</code>`
    + `（不进 git）；断网或官网改版时自动回退到内置数据，计算器照常能用。</div>`;
  renderOnlinePanel();
}

function renderOnlinePanel(){
  const m = compMeta(), box = $('#comp-online'), st = $('#refresh-status');
  if(!m || !m.online){
    st.innerHTML = '还没有联网刷新过。点「🔄 刷新联网」抓一次官网，'
      + '就能看到内置名录有没有更新、以及最近还有哪些赛事在报名。';
    box.innerHTML = '';
    return;
  }
  const o = m.online, d = o.diff||{}, cnt = o.counts||{};
  const okN = (o.sources||[]).filter(s=>s.ok).length, allN = (o.sources||[]).length;
  st.innerHTML = `最近一次联网刷新：<b>${esc(o.fetched_at||'')}</b>`
    + ` · 抓取成功 ${okN}/${allN} 个页面`
    + ` · 名录 ${cnt.catalog_total||0} 条`
    + ((d.added||[]).length?` · <span style="color:var(--pri)">新增 ${d.added.length}</span>`:'')
    + ` · 通知线索 ${cnt.clues||0} 条`;

  const srcRows = (o.sources||[]).map(s=>{
    const cls = s.ok?'ok-line':'err-line';
    const mark = s.ok?'✔':'✘';
    return `<div class="${cls}">${mark} ${esc(s.title)} `
      + `<span class="src">HTTP ${s.status||'—'}${s.items?` · ${s.items} 条`:''}`
      + `${s.elapsed?` · ${s.elapsed}s`:''}${s.error?` · ${esc(s.error)}`:''}</span></div>`;
  }).join('');

  let diffHtml = '';
  const dl = (arr, label, fmt)=> (arr&&arr.length)
    ? `<div class="diffitem"><b>${label} ${arr.length} 项</b>${arr.slice(0,12).map(fmt).join('')}` +
      `${arr.length>12?`<div class="src">…还有 ${arr.length-12} 项</div>`:''}</div>` : '';
  if(d.ok){
    const none = !((d.added||[]).length||(d.removed||[]).length||(d.renamed||[]).length||(d.tier_changed||[]).length);
    diffHtml = none
      ? `<div class="ok-line">✔ 与官方名录逐条比对：完全一致，暂无更新。</div>`
      : `<div class="diffitem"><b>官方名录有变化</b>（联网为准，内置数据可能已过期）</div>`;
  }else{
    diffHtml = `<div class="err-line">✘ 名录页没抓成功${d.note?`：${esc(d.note)}`:''}</div>`;
  }
  diffHtml += dl(d.added, '新增赛事', x=>
      `<div>＋ 附录${x.appendix} ${esc(x.tier)} 类 #${x.seq} ${esc(x.name)}</div>`)
    + dl(d.renamed, '改名', x=>
      `<div>✎ #${x.seq} ${esc(x.from)} → <b>${esc(x.to)}</b></div>`)
    + dl(d.removed, '官方已移除', x=>
      `<div>－ 附录${x.appendix} ${esc(x.tier)} 类 #${x.seq} ${esc(x.name)}</div>`)
    + dl(d.tier_changed, '级别变化', x=>
      `<div>⇄ ${esc(x.name)}：${esc(x.from)} → <b>${esc(x.to)}</b></div>`);

  const clues = o.clues||[];
  const matched = clues.filter(c=>c.matched_name), others = clues.filter(c=>!c.matched_name);
  const clueCard = c=>`<div class="clue">
      <div class="ct"><a href="${esc(c.url)}" target="_blank" rel="noopener">${esc(c.title)}</a></div>
      <div class="cm">${c.pub_date?`${esc(c.pub_date)} · `:''}${esc(c.source||'')}
        ${c.matched_name?` · <span class="chip">对应名录赛事：${esc(c.matched_name)}</span>`:''}</div>
    </div>`;
  const clueHtml = clues.length
    ? `<div style="margin-top:10px"><b>联网发现的赛事线索</b>
        <span class="src">（通知栏目里抓到的，用来回答「还有哪些其他活动」；
        只有名录里的赛事才有加分档位，线索本身不直接加分）</span></div>`
      + (others.length?`<div class="src" style="margin:6px 0 4px">还没进名录 / 名录外的活动（${others.length} 条，按发布时间倒序）：</div>`
          + others.slice(0,15).map(clueCard).join(''):'')
      + (matched.length?`<details style="margin-top:6px"><summary>已对应到名录赛事的通知（${matched.length} 条）</summary>`
          + matched.slice(0,20).map(clueCard).join('') + `</details>`:'')
    : '';

  box.innerHTML = `<details open style="margin-top:10px"><summary>联网刷新结果</summary>
      <div style="margin-top:6px">${srcRows}</div>
      <div style="margin-top:8px">${diffHtml}</div>
      ${clueHtml}
    </details>`;
}

export async function refreshOnline(){
  const btn = $('#refresh-online'), st = $('#refresh-status');
  const old = btn.textContent;
  btn.disabled = true; btn.textContent = '联网抓取中…';
  st.innerHTML = '<span class="spin"></span> 正在抓取学校官网（名录页 + 竞赛通知栏目），请稍等…';
  try{
    const r = await CTX.api('/api/calc/activities/refresh', {
      method:'POST', headers:{'Content-Type':'application/json'}, body:'{}'});
    CTX.setCatalog(await CTX.api('/api/calc/catalog?activities=0'));
    fillFilters(); renderCompetitionHead(); renderActivities();
    const c = r.counts||{}, d = r.diff||{};
    if(r.ok){
      st.innerHTML = `<span class="ok-line">✔ 联网刷新完成（${esc(r.fetched_at||'')}）：`
        + `名录 ${c.catalog_total||0} 条`
        + ((d.added||[]).length?`，<b>官方新增 ${d.added.length} 项</b>`:'')
        + ((d.renamed||[]).length?`，改名 ${d.renamed.length} 项`:'')
        + `，通知线索 ${c.clues||0} 条</span>`;
    }else{
      st.innerHTML = '<span class="err-line">✘ 自动刷新没抓到可用数据，仍用内置数据。'
        + '常见原因：不在校园网 / 官网改版 / 代理阻断。可以展开下面的结果看每个源的报错。</span>';
    }
  }catch(e){
    st.innerHTML = `<span class="err-line">✘ 刷新失败：${esc(e.message)}（内置数据不受影响）</span>`;
  }finally{
    btn.disabled = false; btn.textContent = old;
  }
}

/* ---------- 活动卡片 ---------- */
function activityCard(a){
  const best = actBestScore(a);
  const ex = a.extra||{};
  const comp = isComp(a);
  // 通用条目的通道基准分是有意义的（细则按基准分 × 系数算）；
  // 具体赛事走的是「档位绝对值」，基准分只是展示用，所以这里换成
  // 「计入综测 / 推免的哪些分项」，避免把基准分误读成能加的分。
  const chanNames = Object.keys(a.channels||{});
  const groups = a.channel_groups || {};
  const creditHours = (groups.credit || []).concat(groups.hours || []);
  const chan = comp
    ? [['计入综测', groups.zongce || []],
       ['计入推免', groups.tuimian || []],
       ['学分/时长', creditHours]]
      .filter(([,v])=>v.length)
      .map(([label,v])=>`<span class="chip">${label}：${v.join('、')}</span>`).join('')
    : chanNames.map(k=>{
        const neg = (a.channels[k]||0) < 0;
        return `<span class="chip">${esc(k)} ${neg?'':'基准 '}${n2(a.channels[k],2)}${esc(chanUnit(k))}</span>`;
      }).join('');
  const ach = (a.achievements||[]).map(x=>{
    const per = ((a.preview||{})[x]||{}).channels || {};
    const zc = fmtChannels(per, groups.zongce);
    const tm = fmtChannels(per, groups.tuimian);
    const other = fmtChannels(per, creditHours);
    const pZc = (groups.zongce || []).some(k=>per[k] != null);
    const pTm = (groups.tuimian || []).some(k=>per[k] != null);
    const pOther = creditHours.some(k=>per[k] != null);
    let body = '';
    if(pZc) body += `综测：${zc}`;
    if(pTm) body += `${body?'<br>':''}推免：${tm}`;
    if(pOther) body += `${body?'<br>':''}${other}`;
    const title = (pZc && pTm)
      ? '综测与推免是两套评分表，同一件事分值不同' : '';
    return `<span class="chip" ${title?`title="${title}"`:''}>${esc(x)}<br>${body}</span>`;
  }).join('');
  const added = state.basket.some(b=>b.activity_id===a.id);
  const noChannel = !Object.keys(a.channels||{}).length;
  const nameCode = comp && ex.seq!=null
    ? `<span class="seq" title="名录序号">#${ex.seq}</span>` : '';
  const tierChip = comp
    ? `<span class="tier ${esc(ex.tier||'')}" title="${esc(ex.appendix_title||'')}">${esc(ex.tier_label||'')}</span>`
    : '';
  const meta = comp
    ? `<div class="m">附录${ex.appendix||''} · ${esc(ex.appendix_title||'')}`
      + `${ex.raw_name && ex.raw_name!==a.name?`　名录原名：${esc(ex.raw_name)}`:''}</div>`
      + `<div class="m">加分档位：<b>${esc(ex.profile_label||ex.profile||'')}</b>`
      + `${ex.online?` · <span style="color:var(--pri)">联网新增（${esc(ex.confirmed_at||'')}）</span>`:''}</div>`
    : '';
  return `<div class="act ${comp?'comp':''} ${ex.online?'online':''}">
    <div class="t">${nameCode}${esc(a.name)}
      ${tierChip}
      ${a.level&&!comp?`<span class="chip">${esc(a.level)}</span>`:''}
      ${a.category&&!comp?`<span class="chip">${esc(a.category)}</span>`:''}
      ${noChannel?`<span class="pill warn" style="font-size:11.5px">提示信息（不直接加分）</span>`
        : best.best>0?`<span class="pill ok" style="font-size:11.5px">综测最高 +${n2(best.best,2)} 分</span>`
        :`<span class="pill warn" style="font-size:11.5px">加分值未证实</span>`}
      ${best.bestTuimian>0?`<span class="pill pri" style="font-size:11.5px">推免最高 +${n2(best.bestTuimian,2)} 分</span>`:''}
      <span style="margin-left:auto"></span>
      ${noChannel?'':`<button class="mini ${added?'ghost':''}" data-add="${esc(a.id)}">${added?'已在篮中':'加入活动篮'}</button>`}
    </div>
    ${meta}
    ${a.organizer?`<div class="m">主办：${esc(a.organizer)}</div>`:''}
    ${a.timing?`<div class="m">时间：${esc(a.timing)}</div>`:''}
    ${a.eligibility?`<div class="m">资格：${esc(a.eligibility)}</div>`:''}
    <div class="ach">${chan}</div>
    ${ach?`<div class="ach" style="align-items:stretch">${ach}</div>`:''}
    ${a.note?`<div class="meta">${esc(a.note)}</div>`:''}
    ${a.source?`<div class="basis">加分依据：${esc(a.source)}${a.confidence&&a.confidence!=='verified'?`（可信度：${esc(a.confidence)}）`:''}</div>`:''}
    ${a.url?`<div class="basis"><a href="${esc(a.url)}" target="_blank" rel="noopener">${esc(a.url)}</a></div>`:''}
  </div>`;
}

export async function renderActivities(){
  const seq = ++requestSeq;
  const params = new URLSearchParams({
    kind: $('#f-kind').value,
    appendix: $('#f-appendix').value,
    category: $('#f-cat').value,
    level: $('#f-level').value,
    q: $('#f-q').value.trim(),
    scored: $('#f-scored').checked ? '1' : '0',
  });
  let data;
  try{
    data = await CTX.api('/api/calc/activities?' + params.toString());
  }catch(e){
    if(seq === requestSeq)
      $('#act-list').innerHTML = `<div class="card"><div class="note">活动列表加载失败：${esc(e.message)}</div></div>`;
    return;
  }
  if(seq !== requestSeq) return;             // 过滤条件快速变化时只画最后一次
  CURRENT = data.items || [];
  const compN = CURRENT.filter(isComp).length;
  $('#act-count').textContent = `共 ${data.filtered} 项`
    + (compN?`（具体赛事 ${compN}）`:'')
    + ` / 全部 ${data.total} 项`;
  $('#act-list').innerHTML = CURRENT.map(activityCard).join('')
    || '<div class="card"><div class="note">没有符合筛选条件的活动。</div></div>';

  $$('#act-list button[data-add]').forEach(b=>{
    b.onclick = ()=>{
      const id = b.dataset.add;
      if(state.basket.some(x=>x.activity_id===id)) return;
      const act = CURRENT.find(a=>a.id===id);
      if(!act) return;
      const {bestAch} = actBestScore(act);
      state.basket.push({activity_id:id, achieve:bestAch||act.default_achieve||'', quantity:1, name:act.name});
      save(); CTX.scheduleEval(40);
    };
  });
}
