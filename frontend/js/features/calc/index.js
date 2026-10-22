/* ===== 绩点 / 综测计算器：表单、订阅与渲染（业务计分/匹配在后端） ===== */
import { $, $$, esc } from '../../shared/dom.js';
import { n2 } from '../../shared/format.js';
import { requestJSON } from '../../shared/api.js';
import { state, save, loadState, onBasketChanged } from './state.js';
import {
  chanUnit, configureActivities, fillFilters, refreshOnline,
  renderActivities, renderCompetitionHead,
} from './activities.js';

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
    CAT = await api('/api/calc/catalog?activities=0');
  }catch(e){
    booted = false;
    $('#pill-calc').innerHTML = `<span class="pill err">无法加载计算器数据：${esc(e.message)}<br>请确认 calcdata/ 下有 rules/majors/goals/activities.json</span>`;
    return;
  }
  configureActivities({getCatalog: () => CAT, setCatalog: c => { CAT = c; }, api, scheduleEval});
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
