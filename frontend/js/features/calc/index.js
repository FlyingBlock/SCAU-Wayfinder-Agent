/* ===== 绩点 / 综测计算器：表单、订阅与渲染（不做分数/匹配计算） ===== */
import { $, $$, esc } from '../../shared/dom.js';
import { n2 } from '../../shared/format.js';
import { requestJSON } from '../../shared/api.js';
import { state, save, loadState, onBasketChanged } from './state.js';

let CAT = null;              // /api/calc/catalog
let MAJOR = null;            // 当前专业
let LAST = null;             // 最近一次 evaluate 结果
let TERM_FILTER = 0;         // 0 = 全部学期
let booted = false;

/* ============================== 网络 ============================== */
async function api(path, opts = {}){
  const method = (opts.method || 'GET').toUpperCase();
  let body;
  if(method !== 'GET' && opts.body){
    try{ body = JSON.parse(opts.body); }catch(e){ body = {}; }
  }
  const {status, data} = await requestJSON(path, {method, body});
  if(status >= 400) throw new Error(data.error || ('HTTP ' + status));
  return data;
}

/* ============================== 主计算 ============================== */
let evalTimer = null, evaluating = false, pendingEval = false;
function scheduleEval(delay){
  clearTimeout(evalTimer);
  evalTimer = setTimeout(runEval, delay==null?180:delay);
}
async function runEval(){
  if(evaluating){ pendingEval = true; return; }
  evaluating = true;
  try{
    const payload = {
      profile:{
        major_id: state.major_id, grade: state.grade,
        scores: state.scores, retakes: state.retakes,
        metrics: state.metrics,
        cohort_size: state.cohort_size, rank: state.rank
      },
      basket: state.basket
    };
    const d = await api('/api/calc/evaluate', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify(payload)
    });
    LAST = d;
    renderCourseGps(d);
    renderLive(d); renderBasket(d); renderGoals(d); renderScoreProgress(d);
    const warn = (d.warnings||[]).length;
    $('#pill-calc').innerHTML =
      `<span class="pill">${esc(MAJOR?MAJOR.name:'未选专业')}</span>` +
      `<span class="pill ${d.gpa.gpa>0?'ok':''}">绩点 ${n2(d.gpa.gpa,3)}</span>` +
      (Math.abs((d.gpa.gpa_no_retake||0)-(d.gpa.gpa||0))>1e-9
        ? `<span class="pill" title="综测评优口径：重修课程不纳入平均绩点">综测用绩点 ${n2(d.gpa.gpa_no_retake,3)}</span>` : '') +
      `<span class="pill ${d.comprehensive.total>0?'ok':''}">综测 ${n2(d.comprehensive.total,2)}</span>` +
      `<span class="pill">已获 ${n2(d.gpa.credits_earned,1)}/${n2(d.gpa.credits_total,1)} 学分</span>` +
      (warn?`<span class="pill warn">${warn} 条数据提示</span>`:'');
  }catch(e){
    $('#pill-calc').innerHTML = `<span class="pill err">计算失败：${esc(e.message)}</span>`;
  }finally{
    evaluating = false;
    if(pendingEval){ pendingEval = false; setTimeout(runEval, 30); }
  }
}

/* ============================== ① 成绩表 ============================== */
function buildMajorSelect(){
  const sel = $('#major');
  sel.innerHTML = '<option value="">— 请选择专业 —</option>' +
    CAT.majors.map(m=>`<option value="${esc(m.id)}">${esc(m.name)}（${esc(m.college)}）</option>`).join('');
  sel.value = state.major_id || '';
  sel.onchange = ()=>{
    state.major_id = sel.value;
    state.scores = {}; state.retakes = [];
    LAST = null;
    setMajor(); save(); renderCourses(); renderMetrics(); scheduleEval(60);
  };
}

function setMajor(){
  MAJOR = CAT.majors.find(m=>m.id===state.major_id) || null;
  if(!MAJOR){
    $('#major-note').innerHTML = '还没有选专业。选好之后会自动导入该专业培养方案里的全部课程。';
    return;
  }
  const g = MAJOR.credit_groups.map(x=>
    `<div class="tot"><span>${esc(x.name)}${x.counts_toward_ranking?'':' <span class="sub">（不计排名）</span>'}</span><b>${n2(x.credits,1)}</b></div>`
  ).join('');
  const off = MAJOR.group_credits_official || {};
  const offTxt = Object.entries(off).map(([k,v])=>`${esc(k)} ${n2(v,1)}`).join(' · ');
  const diffs = MAJOR.credits_official &&
                Math.abs(MAJOR.credits_listed - MAJOR.credits_official) > 0.5;
  $('#major-note').innerHTML =
    `<b>${esc(MAJOR.name)}</b> · ${esc(MAJOR.college)} · ${esc(MAJOR.degree)} · ${MAJOR.years} 年 · `
    + `课程 ${MAJOR.courses.length} 门，列表学分合计 <b>${n2(MAJOR.credits_listed,1)}</b>`
    + (MAJOR.credits_official
        ? `｜官方培养方案毕业总学分 <b>${n2(MAJOR.credits_official,1)}</b>`
        : '')
    + `<br><div style="margin-top:8px">${g}</div>`
    + (offTxt?`<div class="src" style="margin-top:6px">官方教学计划分类合计：${offTxt}</div>`:'')
    + `<div class="src" style="margin-top:6px">数据来源：${esc(MAJOR.source)}｜可信度：${esc(MAJOR.confidence)}</div>`
    + (diffs
        ? `<div class="note" style="margin-top:8px">两处学分不一致是正常的：官方总学分是<b>必须修满</b>的下限，
           而课程列表把可选的拓展/专业选修都列出来了（你不会全选）。
           <b>绩点的分母用的是「你实际填了成绩的课程」的学分</b>，所以两者不需要相等。
           要按自己的培养方案调整，改 <code>calcdata/majors.json</code> 即可，代码不用动。</div>`
        : '')
    + (MAJOR.confidence && MAJOR.confidence !== 'verified'
        ? `<div class="note" style="margin-top:8px">⚠️ 课程学分与开课学期标为「${esc(MAJOR.confidence)}」，用于规划估算。
           毕业总学分与学位信息已对照官方培养方案核验，但逐门课的学分请用教务系统核对。</div>`
        : '');
}

function renderCourses(){
  const tb = $('#course-table tbody');
  if(!MAJOR){ tb.innerHTML = '<tr><td colspan="7" style="color:var(--mut)">请先选择专业</td></tr>'; return; }
  const seen = new Set();
  const courses = MAJOR.courses.filter(c=>{
    if(TERM_FILTER && c.term!==TERM_FILTER) return false;
    if(seen.has(c.code)) return false;
    seen.add(c.code); return true;
  });
  const terms = Array.from(new Set(MAJOR.courses.map(c=>c.term))).sort((a,b)=>a-b);
  // 学期切换小工具塞在子标题里
  $('#term-label').textContent = TERM_FILTER
    ? (MAJOR.terms.find(t=>t.term===TERM_FILTER)||{}).label || ('第 '+TERM_FILTER+' 学期')
    : '全部学期';
  let html = '';
  let lastTerm = null;
  for(const c of courses){
    if(!TERM_FILTER && c.term!==lastTerm){
      lastTerm = c.term;
      const t = MAJOR.terms.find(x=>x.term===c.term);
      html += `<tr><td colspan="7" style="background:var(--soft);font-weight:600;font-size:12.5px;color:var(--mut)">`
            + `${esc(t?t.label:'未标注学期')} · 共 ${n2(t?t.credits:0,1)} 学分</td></tr>`;
    }
    const val = state.scores[c.code];
    const rk = state.retakes.includes(c.code);
    html += `<tr data-code="${esc(c.code)}">
      <td class="src">${esc(c.code)}</td>
      <td>${esc(c.name)}${c.counts_toward_gpa?'':' <span class="chip">不计绩点</span>'}
          ${c.counts_toward_ranking?'':' <span class="chip">不计排名</span>'}</td>
      <td class="num">${n2(c.credits,1)}</td>
      <td><span class="chip">${esc(c.kind)}</span></td>
      <td><input type="text" data-score="${esc(c.code)}" value="${esc(val==null?'':val)}"
                 placeholder="${c.assess==='五级制'?'优秀/良好':''}" style="width:88px"></td>
      <td style="text-align:center"><input type="checkbox" data-retake="${esc(c.code)}" ${rk?'checked':''}></td>
      <td class="gp">—</td>
    </tr>`;
  }
  tb.innerHTML = html || '<tr><td colspan="7" style="color:var(--mut)">该学期没有课程</td></tr>';

  $$('#course-table input[data-score]').forEach(inp=>{
    inp.oninput = ()=>{
      const code = inp.dataset.score, v = inp.value.trim();
      if(v==='') delete state.scores[code]; else state.scores[code] = v;
      const gpCell = inp.closest('tr').querySelector('.gp');
      gpCell.textContent = v === '' ? '—' : '…';
      save(); scheduleEval();
    };
  });
  $$('#course-table input[data-retake]').forEach(inp=>{
    inp.onchange = ()=>{
      const code = inp.dataset.retake;
      state.retakes = state.retakes.filter(x=>x!==code);
      if(inp.checked) state.retakes.push(code);
      save(); scheduleEval(60);
    };
  });
}

/** 只渲染后端算好的绩点；重修封顶以 effective_gp 为准。 */
function renderCourseGps(d){
  if(!d || !d.gpa) return;
  const byCode = new Map((d.gpa.courses || []).map(c => [c.code, c]));
  $$('#course-table tbody tr[data-code]').forEach(tr => {
    const row = byCode.get(tr.dataset.code);
    const cell = tr.querySelector('.gp');
    if(!cell) return;
    if(!row || row.gp == null){
      cell.textContent = '—';
      cell.title = '';
      return;
    }
    const shown = row.effective_gp != null ? row.effective_gp : row.gp;
    cell.textContent = n2(shown, 2);
    cell.title = (row.effective_gp != null
      && Math.abs(row.effective_gp - row.gp) > 1e-9)
      ? `原始绩点 ${n2(row.gp, 2)}；按当前口径计入 ${n2(row.effective_gp, 2)}`
      : '';
  });
}

/* ============================== ① 其他指标 ============================== */
function renderMetrics(){
  const box = $('#metric-form');
  const form = (CAT.metrics||[]).filter(m=>m.fillable==='form' && m.kind==='number');
  box.innerHTML = form.map(m=>`
    <div class="fld">
      <label title="${esc(m.hint)}">${esc(m.label)}${m.unit?`（${esc(m.unit)}）`:''}</label>
      <input type="number" step="any" data-metric="${esc(m.key)}"
             value="${state.metrics[m.key]==null?'':esc(state.metrics[m.key])}"
             placeholder="${esc(m.hint||'')}">
    </div>`).join('') || '<div class="note">没有需要手填的指标。</div>';
  $$('#metric-form input[data-metric]').forEach(inp=>{
    inp.oninput = ()=>{
      const k = inp.dataset.metric, v = inp.value.trim();
      if(v==='') delete state.metrics[k]; else state.metrics[k] = parseFloat(v);
      save(); scheduleEval();
    };
  });
}

function renderScoreProgress(d){
  const total = d.gpa.credits_total || 0;
  const done = d.gpa.credits_graded || 0;
  const pct = total? Math.round(done/total*100) : 0;
  $('#score-progress').innerHTML =
    `已录成绩课程 ${d.gpa.courses.filter(c=>c.gp!=null).length} 门 · `
    + `计入绩点学分 ${n2(done,1)}/${n2(total,1)}（${pct}%）`
    + `<span class="src">　分母＝课程列表学分合计；官方毕业总学分见上方说明</span>`;
}

/* ============================== 右侧实时结果 ============================== */
function renderLive(d){
  // 第一次计算回来之前会被调用一次，这里必须能容忍 d 为空
  if(!d || !d.comprehensive){ $('#live').innerHTML = '<div class="note">正在计算…</div>'; return; }
  const c = d.comprehensive;
  const dims = (c.dimensions||[]).map(x=>`
    <div class="tot"><span>${esc(x.name)} <span class="sub" style="font-size:12px;color:var(--mut)">×${x.weight}</span></span>
      <b>${n2(x.contribution,2)}</b></div>
    <div class="bar"><i style="width:${Math.min(100,Math.max(0,x.raw))}%"></i></div>
    <div class="src" style="margin:2px 0 7px">得分 ${n2(x.raw,2)}${x.bonus?`（含活动加分 ${n2(x.bonus,2)}）`:''}${x.capped?' · 已封顶':''}</div>`).join('');
  const ct = Object.entries(d.basket.channel_totals||{});
  const chan = ct.length ? ct.map(([k,v])=>`<div class="tot"><span>${esc(k)}</span><b>${n2(v,2)}</b></div>`).join('')
                         : '<div class="note" style="margin:6px 0">活动篮还是空的。</div>';
  const goals = (d.overview||[]).map(g=>{
    const cls = g.status==='已达标'?'ok':(g.status==='未达标'?'err':'warn');
    return `<div class="tot"><span>${esc(g.name)}</span>
      <span class="pill ${cls}" style="font-size:11.5px">${esc(g.status)}</span></div>`;
  }).join('');
  $('#live').innerHTML = `
    <div class="tot"><span>平均学分绩点</span><b style="font-size:17px">${n2(d.gpa.gpa,3)}</b></div>
    <div class="tot"><span>保研用学业绩点</span><b>${n2(d.gpa.ranking_gpa,3)}</b></div>
    <div class="tot"><span>综测智育用平均绩点 <span class="src">不含重修</span></span><b>${n2(d.gpa.gpa_no_retake,3)}</b></div>
    <div class="tot"><span>加权平均分</span><b>${n2(d.gpa.avg_score,1)}</b></div>
    <div class="tot"><span>不及格课程</span><b>${d.gpa.failed_count} 门</b></div>
    <div class="tot big"><span>综测总分</span><b>${n2(c.total,2)}</b></div>
    <div class="src" style="margin-bottom:9px">${esc(c.formula_text||'')}</div>
    ${dims}
    ${c.direct_bonus?`<div class="tot"><span>直接加到总分的加分</span><b>${n2(c.direct_bonus,2)}</b></div>`:''}
    ${c.rank_percent_estimate!=null?`<div class="src">综测排名估算：前 ${n2(c.rank_percent_estimate,1)}%（粗估，非官方）</div>`:''}
    <h2 style="font-size:13px;margin:14px 0 6px;color:var(--mut)">活动篮加分</h2>
    ${chan}
    <h2 style="font-size:13px;margin:14px 0 6px;color:var(--mut)">路线状态</h2>
    ${goals || '<div class="note">还没有门槛数据。</div>'}
    ${(d.warnings&&d.warnings.length)?`<details style="margin-top:10px"><summary>${d.warnings.length} 条数据提示</summary>
      <div class="src">${d.warnings.map(esc).join('<br>')}</div></details>`:''}
  `;
}

/* ============================== 活动篮列表 ============================== */
function renderBasket(d){
  $('#basket-count').textContent = state.basket.length + ' 项';  if(!state.basket.length){
    $('#basket-list').innerHTML = '<div class="note">还没有添加活动。到「③ 活动篮」里挑。</div>';
    return;
  }
  const lines = (d && d.basket.items) || [];
  $('#basket-list').innerHTML = state.basket.map((it,i)=>{
    const line = lines[i] || {};
    const ach = (it.achieve||line.achieve||'');
    const pts = line.total_points;
    const detail = (line.awards||[]).filter(a=>a.points)
      .map(a=>`${esc(a.channel)} +${n2(a.points,2)}${esc(chanUnit(a.channel))}`).join('，');
    return `<div class="bl">
      <div class="n"><b>${esc(it.name || line.name || it.activity_id)}</b>
        <span>${esc(ach)} × ${it.quantity} · <span class="pts ${pts?'':'zero'}">+${n2(pts,2)}</span></span>
        ${detail?`<span class="src">${detail}</span>`:''}</div>
      <button class="ghost mini" data-q="-${i}">−</button>
      <button class="ghost mini" data-q="+${i}">＋</button>
      <button class="ghost mini" data-q="x${i}">×</button>
    </div>`;
  }).join('');
  $$('#basket-list button[data-q]').forEach(b=>{
    b.onclick = ()=>{
      const op = b.dataset.q[0], i = parseInt(b.dataset.q.slice(1),10);
      if(op==='x') state.basket.splice(i,1);
      else if(op==='+') state.basket[i].quantity++;
      else state.basket[i].quantity = Math.max(1, state.basket[i].quantity-1);
      save(); scheduleEval(40);
    };
  });
}

/* ============================== ② 门槛对照 ============================== */
function renderGoals(d){
  if(!d || !d.overview){
    $('#goal-overview').innerHTML = '<div class="note">正在计算…</div>';
    $('#goal-cards').innerHTML = '';
    return;
  }
  const ov = (d.overview||[]).map(g=>{
    const cls = g.status==='已达标'?'ok':(g.status==='未达标'?'err':'warn');
    return `<tr>
      <td><b>${esc(g.name)}</b>${g.quota?`<div class="src">${esc(g.quota)}</div>`:''}</td>
      <td><span class="st ${cls}">${esc(g.status)}</span></td>
      <td>${g.amount?esc(g.amount):'—'}</td>
      <td>${g.blocking.length?g.blocking.map(esc).join('<br>'):(g.unknown.length?'待补：'+g.unknown.map(esc).join('、'):'全部满足')}</td>
    </tr>`;
  }).join('');
  $('#goal-overview').innerHTML = `<table>
    <thead><tr><th>路线</th><th style="width:80px">状态</th><th style="width:120px">名额/金额</th><th>卡在哪</th></tr></thead>
    <tbody>${ov || '<tr><td colspan="4">没有门槛数据</td></tr>'}</tbody></table>`;

  $('#goal-cards').innerHTML = (d.goals||[]).map(g=>{
    const cls = g.hard_passed===true?'ok':(g.hard_passed===false?'no':'unk');
    const txt = g.hard_passed===true?'硬性门槛全部满足':(g.hard_passed===false?'有硬性门槛未达标':'部分数据未填，无法判定');
    const rows = g.checks.map(c=>{
      const mark = c.passed===true?'✅':(c.passed===false?(c.hard?'❌':'⚠️'):'❓');
      const mx = c.actual==null?'—':n2(c.actual,3);
      return `<tr>
        <td style="width:22px">${mark}</td>
        <td>${esc(c.label)}${c.hard?'':' <span class="chip">加分项</span>'}
          ${c.note?`<div class="src">${esc(c.note)}</div>`:''}</td>
        <td class="num" style="width:110px">${mx}</td>
        <td class="num" style="width:110px">${esc(c.op)} ${n2(c.required,3)}</td>
        <td style="width:80px">${c.gap?`<span class="st no">差 ${n2(c.gap,2)}</span>`:''}</td>
        <td style="width:120px">${c.metric_source?`<span class="src">${esc(c.metric_source)}</span>`:''}</td>
      </tr>`;
    }).join('');

    const bds = Object.entries(g.breakdowns||{}).map(([k,b])=>`
      <div class="note">
        <b>要在毕业时达到 ${esc(k)} 的绩点，剩下怎么考</b><br>
        ${esc(b.message)}<br>
        <span class="src">已锁定 ${n2(b.remaining_credits?0:0,1)}</span>
        ${b.per_course && b.per_course.length ? renderBreakdown(b.per_course) : ''}
      </div>`).join('');

    return `<div class="card">
      <h2>${esc(g.name)} <span class="sub">${g.kind==='scholarship'?'奖学金':'升学路线'}</span>
        <span class="pill ${cls==='ok'?'ok':(cls==='no'?'err':'warn')}" style="margin-left:auto">${esc(txt)}</span></h2>
      ${g.summary?`<div class="note">${esc(g.summary)}</div>`:''}
      <table class="checks"><tbody>${rows}</tbody></table>
      ${bds}
      <div class="src" style="margin-top:9px">
        ${g.quota?`名额/比例：${esc(g.quota)}　`:''}${g.amount?`金额：${esc(g.amount)}　`:''}
        ${g.source?`出处：${esc(g.source)}`:''}
        ${g.confidence&&g.confidence!=='verified'?`　<span style="color:var(--warn)">可信度：${esc(g.confidence)}</span>`:''}
      </div>
    </div>`;
  }).join('') || '<div class="card"><div class="note">还没有配置门槛数据（calcdata/goals.json）。</div></div>';
}

function renderBreakdown(perCourse){
  const byTerm = {};
  perCourse.forEach(c=>{ (byTerm[c.term]=byTerm[c.term]||[]).push(c); });
  return Object.keys(byTerm).sort((a,b)=>a-b).map(t=>{
    const list = byTerm[t];
    return `<div style="margin-top:6px"><span class="termchip">第 ${esc(t)} 学期（${list.length} 门）</span>
      <table style="margin-top:4px"><thead><tr><th>课程</th><th class="num">学分</th><th class="num">目标分</th></tr></thead>
      <tbody>${list.map(c=>`<tr><td>${esc(c.name)}</td>
        <td class="num">${n2(c.credits,1)}</td>
        <td class="num"><b>${n2(c.required_score,1)}</b></td></tr>`).join('')}</tbody></table></div>`;
  }).join('');
}

/* ============================== ③ 活动篮 ============================== */
// 通道单位与评分表由后端 catalog 提供（来自 rules.json），前端不再硬编码。
const chanUnit = c => (CAT && CAT.channel_units || {})[c] || '分';
const chanRubric = c => (CAT && CAT.channel_rubric || {})[c] || '';

// 把各通道得分渲染成「+X 分 / +Y 学分 / +Z 小时」，不混单位；
// 可按评分类别过滤（同一件事在综测和推免里分值不同，分开显示才不误导）。
function fmtChannels(obj, rubric){
  const parts = Object.entries(obj||{}).filter(([k,v])=>
    v && (!rubric || chanRubric(k)===rubric));
  if(!parts.length) return '<span class="pts zero">±0</span>';
  return parts.map(([k,v])=>{
    const neg = v < 0;
    return `${neg?'':'+'}${n2(v,2)} ${esc(chanUnit(k))}`
      +`<span class="src" style="display:inline"> ${esc(k)}</span>`;
  }).join('　');
}

function fillFilters(){
  const cats = CAT.categories||[], lvls = CAT.levels||[];
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
function compMeta(){ return (CAT && CAT.competitions) || null; }
const actKind = a => a.list_kind || 'general';
const isComp = a => actKind(a)!=='general';

function renderCompetitionHead(){
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

async function refreshOnline(){
  const btn = $('#refresh-online'), st = $('#refresh-status');
  const old = btn.textContent;
  btn.disabled = true; btn.textContent = '联网抓取中…';
  st.innerHTML = '<span class="spin"></span> 正在抓取学校官网（名录页 + 竞赛通知栏目），请稍等…';
  try{
    const r = await api('/api/calc/activities/refresh', {
      method:'POST', headers:{'Content-Type':'application/json'}, body:'{}'});
    CAT = await api('/api/calc/catalog');
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
  const chan = comp
    ? [['计入综测', chanNames.filter(k=>chanRubric(k)==='综测')],
       ['计入推免', chanNames.filter(k=>chanRubric(k)==='推免')],
       ['学分/时长', chanNames.filter(k=>['学分','时长'].includes(chanRubric(k)))]]
      .filter(([,v])=>v.length)
      .map(([label,v])=>`<span class="chip">${label}：${v.join('、')}</span>`).join('')
    : chanNames.map(k=>{
        const neg = (a.channels[k]||0) < 0;
        return `<span class="chip">${esc(k)} ${neg?'':'基准 '}${n2(a.channels[k],2)}${esc(chanUnit(k))}</span>`;
      }).join('');
  const ach = (a.achievements||[]).map(x=>{
    const per = ((a.preview||{})[x]||{}).channels || {};
    const zc = fmtChannels(per, '综测');
    const tm = fmtChannels(per, '推免');
    const other = fmtChannels(per, '学分') + ' ' + fmtChannels(per, '时长');
    const pZc = Object.keys(per).some(k=>chanRubric(k)==='综测');
    const pTm = Object.keys(per).some(k=>chanRubric(k)==='推免');
    const pOther = Object.keys(per).some(k=>['学分','时长'].includes(chanRubric(k)));
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

function renderActivities(){
  const kind = $('#f-kind').value;
  const appendix = $('#f-appendix').value;
  const cat = $('#f-cat').value, lvl = $('#f-level').value;
  const q = $('#f-q').value.trim().toLowerCase();
  const onlyScored = $('#f-scored').checked;
  let list = (CAT.activities||[]).filter(a=>{
    const k = actKind(a);
    if(kind==='competition' && k==='general') return false;
    if(kind==='general' && k!=='general') return false;
    const ex = a.extra||{};
    if(appendix && String(ex.appendix||'')!==appendix) return false;
    if(cat && a.category!==cat) return false;
    if(lvl && a.level!==lvl) return false;
    const {best} = actBestScore(a);
    if(onlyScored && best<=0) return false;
    if(q){
      const hay = [a.name,a.category,a.level,a.organizer,a.note,a.eligibility,
                   ex.raw_name, ex.tier_label, ex.profile_label, ex.appendix_title,
                   (a.tags||[]).join(' '), Object.keys(a.channels||{}).join(' ')]
                   .join(' ').toLowerCase();
      if(!hay.includes(q)) return false;
    }
    return true;
  });
  // 具体赛事按「附录 + 名录序号」排（跟官方名录一个顺序），通用加分项排后面
  const idx = new Map((CAT.activities||[]).map((a,i)=>[a.id,i]));
  list = list.slice().sort((a,b)=>{
    const ca = isComp(a)?0:1, cb = isComp(b)?0:1;
    if(ca!==cb) return ca-cb;
    if(ca===0){
      const ea=a.extra||{}, eb=b.extra||{};
      return ((ea.appendix||0)-(eb.appendix||0)) || ((ea.seq||0)-(eb.seq||0));
    }
    return (idx.get(a.id)||0)-(idx.get(b.id)||0);
  });
  const compN = list.filter(isComp).length;
  $('#act-count').textContent = `共 ${list.length} 项`
    + (compN?`（具体赛事 ${compN}）`:'')
    + ` / 全部 ${CAT.activities.length} 项`;
  $('#act-list').innerHTML = list.map(activityCard).join('')
    || '<div class="card"><div class="note">没有符合筛选条件的活动。</div></div>';

  $$('#act-list button[data-add]').forEach(b=>{
    b.onclick = ()=>{
      const id = b.dataset.add;
      if(state.basket.some(x=>x.activity_id===id)) return;
      const act = CAT.activities.find(a=>a.id===id);
      const {bestAch} = actBestScore(act);
      state.basket.push({activity_id:id, achieve:bestAch||act.default_achieve||'', quantity:1, name:act.name});
      save(); scheduleEval(40);
    };
  });
}

/* ============================== ④ 计算口径 ============================== */
function renderRules(){
  const t = CAT.grade_table;
  const bands = t.bands.map(b=>{
    const val = b.mode==='linear' ? `${n2(b.lp,2)} → ${n2(b.hp,2)}（线性）` : n2(b.gp,2);
    return `<tr><td>${n2(b.lo,1)} – ${n2(b.hi,1)}</td><td class="num">${val}</td><td>${esc(b.note||'')}</td></tr>`;
  }).join('');
  const lv = Object.entries(t.levels||{}).map(([k,v])=>`<span class="chip">${esc(k)} = ${n2(v,2)}</span>`).join('');
  const dims = ((CAT.comprehensive||{}).dimensions||[]).map(d=>
    `<tr><td>${esc(d.name)}</td><td class="num">${d.weight}</td>
      <td>${d.source==='derived'?`由成绩单推算（${esc(d.derive)}）`:`手填指标 ${esc(d.metric)}`}</td>
      <td>${esc(d.note||'')}</td></tr>`).join('');
  const disc = CAT.discount && CAT.discount.level_ratio;
  const lvR = disc? Object.entries(disc.level_ratios||{}).map(([k,v])=>`<span class="chip">${esc(k)} ×${v}</span>`).join('') : '';
  const rkR = disc? Object.entries(disc.rank_ratios||{}).map(([k,v])=>`<span class="chip">${esc(k)} ×${v}</span>`).join('') : '';
  const srcs = (CAT.sources||[]).map(s=>`<li><a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title)}</a> —— ${esc(s.use)}</li>`).join('');
  const warns = (CAT.warnings||[]).map(esc).join('<br>');
  const cm = CAT.competitions || null;
  const compCard = !cm ? '' : `
  <div class="card"><h2>具体赛事名录 <span class="sub">活动篮里那 ${cm.counts.total} 张赛事卡片是怎么来的</span></h2>
    <div class="note">${esc(cm.disclaimer||'')}</div>
    <table><thead><tr><th style="width:90px">附录</th><th style="width:70px">级别</th>
      <th style="width:70px">数量</th><th>名录内容</th></tr></thead>
      <tbody>${(cm.appendix||[]).map(a=>`<tr>
        <td>附录${a.appendix}</td><td><span class="tier ${esc(a.tier)}">${esc(a.tier)} 类</span></td>
        <td class="num">${a.count}</td>
        <td>${esc(a.title)}<div class="src">${esc(a.subtitle)} · ${esc(a.organizer)}</div></td></tr>`).join('')}
      </tbody></table>
    <h2 style="font-size:13px;margin:14px 0 6px;color:var(--mut)">加分档位（每个赛事用哪张表）</h2>
    <table><thead><tr><th style="width:230px">档位</th><th style="width:200px">成果档位与分值（综测 / 推免）</th><th>说明</th></tr></thead>
    <tbody>${Object.entries(cm.profiles||{}).map(([k,p])=>`<tr>
      <td><b>${esc(p.label||k)}</b><div class="src">${esc(p.confidence||'')}</div></td>
      <td class="src">${Object.entries(p.achieve_map||{}).map(([ach,v])=>
          `${esc(ach)}：${typeof v==='object'?n2(v['综测'],2)+' / '+n2(v['推免'],2):n2(v,2)}`).join('<br>')}</td>
      <td class="src">${esc(p.note||'')}<br><b>分值出处</b>：${esc(p.source||'')}</td></tr>`).join('')}
    </tbody></table>
    <div class="note">
      <b>内置 vs 联网</b>：内置名录来自 <code>calcdata/competitions.json</code>，
      源头是 <a href="${esc((cm.catalog_page||{}).url||'')}" target="_blank" rel="noopener">${esc((cm.catalog_page||{}).title||'')}</a>
      （${esc((cm.catalog_page||{}).published||'')} 发布）。点「活动篮」页的「🔄 刷新联网」会重新抓这张名录页
      与几个竞赛通知栏目，逐条对账（新增 / 改名 / 级别变化 / 官方移除），结果缓存在
      <code>data/cache/calc_competitions.json</code>；联网失败或官网改版时自动回退到内置数据，
      <b>计算器不联网也能用</b>。<br>
      联网抓取清单：${(cm.refresh_sources||[]).map(s=>`<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title)}</a>`).join('、')}
    </div>
  </div>
`;

  $('#rules-body').innerHTML = `
  <div class="card"><h2>绩点折算表 <span class="sub">${esc(t.name)} · 上限 ${n2(t.max_gp,1)}</span></h2>
    <table><thead><tr><th style="width:150px">百分制分数</th><th class="num" style="width:150px">绩点</th><th>说明</th></tr></thead>
    <tbody>${bands}</tbody></table>
    <h2 style="font-size:13px;margin:14px 0 6px;color:var(--mut)">五级制折算</h2>
    <div class="ach">${lv}</div>
    <div class="note">
      不及格线 ${n2(t.fail_score,0)} 分。重修/补考有两套口径：<b>学籍 / 推免</b>按
      <b>${esc(t.retake_policy)}</b>——及格后封顶 ${n2(t.retake_cap,2)} 绩点并计入平均学分绩点；
      <b>综测智育</b>按华农党发〔2020〕38号 第六条（一）<b>不含重修</b>（整门不进平均绩点）。
      在成绩表里勾选「重修」后，两个数会分别按各自口径计算。<br>
      ${esc(t.note||'')}
    </div>
  </div>

  <div class="card"><h2>综测构成</h2>
    <table><thead><tr><th>分项</th><th class="num" style="width:70px">权重</th><th style="width:240px">怎么来</th><th>说明</th></tr></thead>
    <tbody>${dims}</tbody></table>
    <div class="note">${esc((CAT.comprehensive||{}).formula_text||'')}<br>
      活动篮里的加分按 <code>bonus_routing</code> 路由：加到某个分项的先乘该分项权重，
      路由到 <code>direct</code> 的直接加到总分。</div>
  </div>

  <div class="card"><h2>活动加分折算系数 <span class="sub">可调参数，不是学校规定值</span></h2>
    <h2 style="font-size:13px;margin:4px 0 6px;color:var(--mut)">级别系数</h2>
    <div class="ach">${lvR}</div>
    <h2 style="font-size:13px;margin:12px 0 6px;color:var(--mut)">名次系数</h2>
    <div class="ach">${rkR}</div>
    <div class="note">单次得分 = 基准分 × 级别系数 × 名次系数 × 份数。<br>
      若某份细则把分值写死了，把该活动的 <code>discount</code> 设为 <code>none</code> 即可跳过系数。</div>
  </div>

  ${compCard}

  <div class="card"><h2>数据口径与出处</h2>
    <ul>${srcs}</ul>
    ${(CAT.notes||[]).map(n=>`<div class="note">${esc(n)}</div>`).join('')}
    ${warns?`<div class="note" style="color:var(--warn)">数据校验提示：<br>${warns}</div>`:''}
  </div>`;
}

/* ============================== 事件绑定 ============================== */
function bindTop(){
  $$('.tabs button').forEach(b=>{
    b.onclick = ()=>{
      $$('.tabs button').forEach(x=>x.classList.remove('on'));
      b.classList.add('on');
      ['profile','goals','acts','rules'].forEach(t=>{
        $('#tab-'+t).classList.toggle('hide', t!==b.dataset.tab);
      });
    };
  });
  $('#grade').value = state.grade||'';
  $('#grade').oninput = ()=>{ state.grade = $('#grade').value.trim(); save(); };
  $('#cohort').value = state.cohort_size||'';
  $('#cohort').oninput = ()=>{ state.cohort_size = parseInt($('#cohort').value||'0',10)||0; save(); scheduleEval(); };
  $('#rank').value = state.rank||'';
  $('#rank').oninput = ()=>{ state.rank = parseInt($('#rank').value||'0',10)||0; save(); scheduleEval(); };

  // 学期筛选：把所有学期做成小按钮
  $('#term-all').onclick = ()=>{
    TERM_FILTER = 0; renderCourses();
    if(LAST) renderCourseGps(LAST);
  };
  $('#clear-scores').onclick = ()=>{
    if(!confirm('清空所有已录成绩？')) return;
    state.scores = {}; state.retakes = []; LAST = null; save(); renderCourses(); scheduleEval(60);
  };
  $('#basket-clear').onclick = ()=>{ state.basket = []; save(); renderActivities(); scheduleEval(40); };
  $('#refresh-online').onclick = refreshOnline;
  $('#export').onclick = ()=>{
    const blob = new Blob([JSON.stringify({state, result:LAST}, null, 2)], {type:'application/json'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = 'scau-calc.json'; a.click();
  };
}

function termButtons(){
  // 在课程卡片的按钮行里插入学期快捷筛选
  const row = $('#term-all').parentElement;
  const anchor = $('#term-all');
  MAJOR && MAJOR.terms.forEach(t=>{
    const b = document.createElement('button');
    b.className = 'ghost mini';
    b.textContent = '大'+Math.ceil(t.term/2)+(t.term%2?'上':'下');
    b.onclick = ()=>{
      TERM_FILTER = t.term; renderCourses();
      if(LAST) renderCourseGps(LAST);
    };
    row.insertBefore(b, anchor);
  });
}

/* ============================== 启动 ============================== */
export async function bootCalc(){
  if(booted) return;
  booted = true;
  loadState();
  try{
    CAT = await api('/api/calc/catalog');
  }catch(e){
    booted = false;
    $('#pill-calc').innerHTML = `<span class="pill err">无法加载计算器数据：${esc(e.message)}<br>请确认 calcdata/ 下有 rules/majors/goals/activities.json</span>`;
    return;
  }
  buildMajorSelect();
  setMajor();
  renderCourses();
  renderMetrics();
  fillFilters();
  renderCompetitionHead();
  renderActivities();
  renderRules();
  bindTop();
  termButtons();
  await runEval();
}

/* 对话页入篮后：状态模块发事件，计算器只负责重画/重算。 */
onBasketChanged(() => {
  if(!CAT) return;
  renderActivities();
  scheduleEval(30);
});
