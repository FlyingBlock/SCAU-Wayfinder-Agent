"""绩点 / 德育 / 综测计算器的 Web 界面。

和 `harness/web.py` 是同一套做法：零依赖、前端内嵌、无构建步骤。放在单独文件里
是为了别把爬虫那套界面撑爆。

页面结构（三个 Tab）：

1. **我的成绩** —— 选专业自动导入课程，按学期录成绩；再填四六级、体测、
   志愿时长这些量化指标。
2. **门槛对照** —— 保研 / 考研 / 奖学金逐条门槛的通过情况，以及「要在毕业时
   拿到 X 绩点，剩下每门课要考多少分」的分摊表。
3. **活动篮** —— 全部可加分活动/竞赛/证书列出来，标上能拿多少分，勾进篮子后
   右侧实时累加。

所有计算都在 `harness.calc` 里做，前端只负责渲染，保证和 CLI 口径一致。
"""
from __future__ import annotations

CALC_PAGE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SCAU 绩点 / 德育 / 综测计算器</title>
<style>
  :root{--fg:#1f2328;--mut:#656d76;--bd:#d0d7de;--bg:#fff;--soft:#f6f8fa;
        --acc:#0969da;--ok:#1a7f37;--warn:#9a6700;--err:#cf222e;--okbg:#eaf7ee;
        --warnbg:#fdf6e3;--errbg:#fdeaea;--pri:#8250df}
  *{box-sizing:border-box}
  body{margin:0;font:14.5px/1.6 -apple-system,"Segoe UI","Microsoft YaHei",sans-serif;
       color:var(--fg);background:var(--soft)}
  header{background:var(--bg);border-bottom:1px solid var(--bd);padding:12px 20px;
         display:flex;align-items:center;gap:14px;flex-wrap:wrap;position:sticky;top:0;z-index:20}
  header h1{font-size:16.5px;margin:0;font-weight:650}
  nav a{font-size:13px;color:var(--acc);text-decoration:none;border:1px solid var(--bd);
        border-radius:99px;padding:3px 11px;background:var(--bg)}
  nav a:hover{background:var(--soft)}
  .pills{display:flex;gap:8px;flex-wrap:wrap;margin-left:auto;font-size:12.5px}
  .pill{background:var(--soft);border:1px solid var(--bd);border-radius:99px;padding:3px 11px;color:var(--mut)}
  .pill.ok{color:var(--ok);border-color:#b7e0c2;background:var(--okbg)}
  .pill.warn{color:var(--warn);border-color:#eeddaa;background:var(--warnbg)}
  .pill.err{color:var(--err);border-color:#f3c0c0;background:var(--errbg)}
  .pill.pri{color:var(--pri);border-color:#d8c7f5;background:#f6f0ff}
  .tabs{display:flex;gap:6px;padding:0 20px;background:var(--bg);border-bottom:1px solid var(--bd);
        position:sticky;top:56px;z-index:19;flex-wrap:wrap}
  .tabs button{background:none;border:0;border-bottom:2px solid transparent;padding:10px 14px;
               font:inherit;font-weight:600;color:var(--mut);cursor:pointer}
  .tabs button.on{color:var(--acc);border-bottom-color:var(--acc)}
  main{padding:18px 20px;max-width:1500px;margin:0 auto}
  .wrap{display:grid;grid-template-columns:minmax(0,1fr) 380px;gap:16px;align-items:start}
  @media (max-width:1100px){.wrap{grid-template-columns:1fr}}
  .card{background:var(--bg);border:1px solid var(--bd);border-radius:10px;padding:16px;margin-bottom:14px}
  .card h2{font-size:15px;margin:0 0 12px;font-weight:650;display:flex;align-items:center;gap:8px}
  .card h2 .sub{font-weight:400;font-size:12.5px;color:var(--mut)}
  select,input[type=number],input[type=text]{padding:6px 8px;border:1px solid var(--bd);
        border-radius:6px;font:inherit;background:var(--bg);color:var(--fg)}
  input[type=number]{width:78px}
  button{background:var(--acc);color:#fff;border:0;border-radius:7px;padding:7px 14px;
         font:inherit;font-weight:600;cursor:pointer}
  button.ghost{background:var(--bg);color:var(--fg);border:1px solid var(--bd);font-weight:500}
  button.mini{padding:3px 9px;font-size:12.5px;border-radius:6px}
  button:hover{filter:brightness(.96)}
  .row{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
  .grid{display:grid;gap:10px 14px;grid-template-columns:repeat(auto-fill,minmax(230px,1fr))}
  .fld{display:flex;flex-direction:column;gap:3px}
  .fld label{font-size:12.5px;color:var(--mut)}
  .fld input,.fld select{width:100%}
  table{border-collapse:collapse;width:100%;font-size:13.5px}
  th,td{border-bottom:1px solid var(--bd);padding:6px 8px;text-align:left;vertical-align:middle}
  th{background:var(--soft);font-weight:600;font-size:12.5px;color:var(--mut);
     position:sticky;top:0;z-index:1}
  td.num,th.num{text-align:right}
  .scroll{max-height:460px;overflow:auto;border:1px solid var(--bd);border-radius:8px}
  .termchip{display:inline-block;font-size:12px;padding:1px 7px;border-radius:99px;
            background:var(--soft);border:1px solid var(--bd);color:var(--mut)}
  .ach{display:flex;gap:5px;flex-wrap:wrap;margin-top:5px}
  .chip{font-size:12px;padding:2px 8px;border-radius:99px;border:1px solid var(--bd);
        background:var(--soft);color:var(--mut)}
  .chip.on{background:#eaf1fd;border-color:#b6cffa;color:var(--acc);font-weight:600}
  .act{border:1px solid var(--bd);border-radius:9px;padding:11px 13px;margin-bottom:9px;background:var(--bg)}
  .act .t{font-weight:600;display:flex;gap:8px;align-items:baseline;flex-wrap:wrap}
  .act .m{font-size:12.5px;color:var(--mut);margin-top:3px}
  .act .meta{font-size:12.5px;color:#424a53;margin-top:4px}
  .pts{font-family:ui-monospace,Consolas,monospace;color:var(--ok);font-weight:600}
  .pts.zero{color:var(--mut);font-weight:400}
  .basis{font-size:12px;color:var(--mut);margin-top:4px;border-left:3px solid var(--bd);padding-left:8px}
  .basket{position:sticky;top:110px}
  .bl{display:flex;gap:6px;align-items:center;padding:6px 0;border-bottom:1px solid var(--bd);font-size:13px}
  .bl .n{flex:1;min-width:0}
  .bl .n b{display:block;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .bl .n span{font-size:12px;color:var(--mut)}
  .tot{display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px dashed var(--bd)}
  .tot b{font-family:ui-monospace,Consolas,monospace}
  .tot.big{font-size:16px;font-weight:700;border-bottom:0;padding-top:9px}
  .note{font-size:12.5px;color:var(--mut);background:var(--soft);border:1px solid var(--bd);
        border-radius:8px;padding:9px 11px;margin-top:10px}
  .checks{width:100%;font-size:13px}
  .checks td{padding:5px 7px}
  .st{font-weight:600}
  .st.ok{color:var(--ok)}.st.no{color:var(--err)}.st.unk{color:var(--warn)}
  .bar{height:7px;background:var(--soft);border-radius:99px;overflow:hidden;border:1px solid var(--bd);margin-top:5px}
  .bar i{display:block;height:100%;background:var(--acc)}
  .hide{display:none!important}
  details summary{cursor:pointer;color:var(--mut);font-size:13px}
  .spin{display:inline-block;width:12px;height:12px;border:2px solid var(--bd);
        border-top-color:var(--acc);border-radius:50%;animation:r .8s linear infinite;vertical-align:-1px}
  @keyframes r{to{transform:rotate(360deg)}}
  .src{font-size:11.5px;color:#8b949e;word-break:break-all}
</style>
</head>
<body>
<header>
  <h1>📊 SCAU 绩点 / 德育 / 综测计算器</h1>
  <nav>
    <a href="/">← 回到信息检索</a>
    <a href="/calc-docs" target="_blank">数据口径说明</a>
  </nav>
  <div class="pills" id="pills"><span class="pill">加载中…</span></div>
</header>

<div class="tabs">
  <button data-tab="profile" class="on">① 我的成绩</button>
  <button data-tab="goals">② 门槛对照</button>
  <button data-tab="acts">③ 活动篮</button>
  <button data-tab="rules">④ 计算口径</button>
</div>

<main>
<div class="wrap">
  <div id="left">

    <!-- ================= ① 我的成绩 ================= -->
    <section id="tab-profile">
      <div class="card">
        <h2>专业与基本情况 <span class="sub">选专业后自动导入该专业培养方案里的全部课程</span></h2>
        <div class="grid">
          <div class="fld"><label>专业</label><select id="major"></select></div>
          <div class="fld"><label>入学年份</label>
            <input type="text" id="grade" placeholder="如 2024"></div>
          <div class="fld"><label>专业总人数（用于算排名百分位）</label>
            <input type="number" id="cohort" min="0" placeholder="如 120"></div>
          <div class="fld"><label>我的名次</label>
            <input type="number" id="rank" min="0" placeholder="如 15"></div>
        </div>
        <div class="note" id="major-note"></div>
      </div>

      <div class="card">
        <h2>成绩录入 <span class="sub">只填你已出分的课；百分制直接填分数，五级制填 优秀/良好/中等/及格</span></h2>
        <div class="row" style="margin-bottom:10px">
          <span class="termchip" id="term-label">全部学期</span>
          <button class="ghost mini" id="term-all">显示全部学期</button>
          <button class="ghost mini" id="fill-demo">填充示例成绩</button>
          <button class="ghost mini" id="clear-scores">清空成绩</button>
          <span style="margin-left:auto"></span>
          <span id="score-progress" class="sub" style="font-size:12.5px;color:var(--mut)"></span>
        </div>
        <div class="scroll"><table id="course-table">
          <thead><tr>
            <th style="width:78px">代码</th><th>课程</th><th class="num" style="width:56px">学分</th>
            <th style="width:70px">性质</th><th style="width:96px">成绩</th>
            <th style="width:64px">重修</th><th style="width:56px">绩点</th>
          </tr></thead>
          <tbody></tbody>
        </table></div>
      </div>

      <div class="card">
        <h2>其他指标 <span class="sub">不填的项按「数据缺失」处理，相关门槛会标成待补数据</span></h2>
        <div class="grid" id="metric-form"></div>
      </div>
    </section>

    <!-- ================= ② 门槛对照 ================= -->
    <section id="tab-goals" class="hide">
      <div class="card">
        <h2>路线总览 <span class="sub">保研 / 考研 / 奖学金分别要什么</span></h2>
        <div id="goal-overview"></div>
      </div>
      <div id="goal-cards"></div>
    </section>

    <!-- ================= ③ 活动篮 ================= -->
    <section id="tab-acts" class="hide">
      <div class="card">
        <h2>筛选</h2>
        <div class="row">
          <label class="sub" style="font-size:12.5px;color:var(--mut)">类别
            <select id="f-cat"><option value="">全部</option></select></label>
          <label class="sub" style="font-size:12.5px;color:var(--mut)">级别
            <select id="f-level"><option value="">全部</option></select></label>
          <label class="sub" style="font-size:12.5px;color:var(--mut)">只看有分数的
            <input type="checkbox" id="f-scored" checked></label>
          <input type="text" id="f-q" placeholder="搜活动名 / 关键词" style="min-width:190px">
          <span style="margin-left:auto"></span>
          <span id="act-count" class="sub" style="font-size:12.5px;color:var(--mut)"></span>
        </div>
      </div>
      <div id="act-list"></div>
    </section>

    <!-- ================= ④ 计算口径 ================= -->
    <section id="tab-rules" class="hide">
      <div id="rules-body"></div>
    </section>

  </div>

  <!-- ================= 右侧：实时结果 ================= -->
  <aside>
    <div class="card basket">
      <h2>实时结果 <span class="sub">改任何输入都会立刻重算</span></h2>
      <div id="live"></div>
    </div>
    <div class="card">
      <h2>活动篮 <span class="sub" id="basket-count">0 项</span></h2>
      <div id="basket-list"><div class="note">还没有添加活动。到「③ 活动篮」里挑。</div></div>
      <div class="row" style="margin-top:10px">
        <button class="ghost mini" id="basket-clear">清空活动篮</button>
        <button class="ghost mini" id="export">导出 JSON</button>
      </div>
    </div>
  </aside>
</div>
</main>

<script>
/* ============================== 基础设施 ============================== */
const $ = s => document.querySelector(s);
const $$ = s => Array.from(document.querySelectorAll(s));
const esc = s => String(s==null?'':s).replace(/[&<>"]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const n2 = (v,d=2) => (v==null||v==='')?'—':(Math.round(v*100)/100).toFixed(d).replace(/\.?0+$/,'') || '0';
const LS_KEY = 'scau-calc-state-v1';

let CAT = null;              // /api/calc/catalog
let MAJOR = null;            // 当前专业
let LAST = null;             // 最近一次 evaluate 结果
let TERM_FILTER = 0;         // 0 = 全部学期

const state = {
  major_id:'', grade:'', cohort_size:0, rank:0,
  scores:{}, retakes:[], metrics:{},
  basket:[]
};

function save(){ try{ localStorage.setItem(LS_KEY, JSON.stringify(state)); }catch(e){} }
function load(){
  try{
    const raw = localStorage.getItem(LS_KEY);
    if(raw) Object.assign(state, JSON.parse(raw));
  }catch(e){}
}

/* ============================== 网络 ============================== */
async function api(path, opts){
  const r = await fetch(path, opts);
  if(!r.ok) throw new Error('HTTP '+r.status);
  return r.json();
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
    renderLive(d); renderBasket(d); renderGoals(d); renderScoreProgress(d);
    const warn = (d.warnings||[]).length;
    $('#pills').innerHTML =
      `<span class="pill">${esc(MAJOR?MAJOR.name:'未选专业')}</span>` +
      `<span class="pill ${d.gpa.gpa>0?'ok':''}">绩点 ${n2(d.gpa.gpa,3)}</span>` +
      `<span class="pill ${d.comprehensive.total>0?'ok':''}">综测 ${n2(d.comprehensive.total,2)}</span>` +
      `<span class="pill">已获 ${n2(d.gpa.credits_earned,1)}/${n2(d.gpa.credits_total,1)} 学分</span>` +
      (warn?`<span class="pill warn">${warn} 条数据提示</span>`:'');
  }catch(e){
    $('#pills').innerHTML = `<span class="pill err">计算失败：${esc(e.message)}</span>`;
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
      gpCell.textContent = v==='' ? '—' : gpOf(v);
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
  updateGpColumn();
}

function gpOf(v){
  if(!CAT) return '—';
  const t = CAT.grade_table;
  for(const [lv,gp] of Object.entries(t.levels||{})){
    if(String(v)===lv || String(v).startsWith(lv)) return n2(gp,2);
  }
  const num = parseFloat(v);
  if(isNaN(num)) return '?';
  for(const b of t.bands){
    if(num>=b.lo && num<=b.hi){
      if(b.mode==='linear' && b.hi>b.lo){
        const r=(num-b.lo)/(b.hi-b.lo);
        return n2(Math.min(b.lp+r*(b.hp-b.lp), t.max_gp),2);
      }
      return n2(b.gp,2);
    }
  }
  return '0';
}
function updateGpColumn(){
  $$('#course-table tbody tr[data-code]').forEach(tr=>{
    const code = tr.dataset.code, v = state.scores[code];
    // 用双保险取值：万一某一行没有 .gp 单元格（模板改动、半渲染状态），
    // 直接抛异常会让整张成绩表看起来是坏的，不如跳过这一行。
    const cell = tr.querySelector('.gp') || (tr.children||[])[6];
    if(!cell) return;
    cell.textContent = (v==null||v==='')?'—':gpOf(v);
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
// 这些通道的单位是学分或小时，不能和「分」相加
const UNIT_BY_CHANNEL = {
  '第二课堂':'学分','创新创业学分':'学分','志愿服务时长':'小时'
};
const chanUnit = c => UNIT_BY_CHANNEL[c] || '分';
const RUBRIC_BY_CHANNEL = {
  '德育加分':'综测','智育加分':'综测','体育加分':'综测','美育加分':'综测',
  '劳育加分':'综测','综测加分':'综测','创新能力':'推免','发展素养':'推免',
  '第二课堂':'学分','创新创业学分':'学分','志愿服务时长':'时长'
};
const chanRubric = c => RUBRIC_BY_CHANNEL[c] || '';

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
  ['#f-cat','#f-level','#f-scored'].forEach(s=>$(s).onchange = renderActivities);
  $('#f-q').oninput = renderActivities;
}

function actScore(act, ach){
  const p = (act.preview||{})[ach];
  if(!p) return 0;
  return p.total;
}
// 返回综测与推免两套表各自的最高分，界面要分开显示，
// 因为同一件事（例如一篇 T2 论文）在两边是 8 分和 6 分。
function actBestScore(act){
  let best = 0, bestAch = '', bestTuimian = 0, bestAchTuimian = '';
  (act.achievements||[]).forEach(a=>{
    const p = (act.preview||{})[a];
    if(!p) return;
    if((p.total||0) > best){ best = p.total; bestAch = a; }
    if((p.total_tuimian||0) > bestTuimian){
      bestTuimian = p.total_tuimian; bestAchTuimian = a;
    }
  });
  return {best, bestAch, bestTuimian, bestAchTuimian};
}

function renderActivities(){
  const cat = $('#f-cat').value, lvl = $('#f-level').value;
  const q = $('#f-q').value.trim().toLowerCase();
  const onlyScored = $('#f-scored').checked;
  const list = (CAT.activities||[]).filter(a=>{
    if(cat && a.category!==cat) return false;
    if(lvl && a.level!==lvl) return false;
    const {best} = actBestScore(a);
    if(onlyScored && best<=0) return false;
    if(q){
      const hay = [a.name,a.category,a.level,a.organizer,a.note,a.eligibility,
                   (a.tags||[]).join(' '), Object.keys(a.channels||{}).join(' ')]
                   .join(' ').toLowerCase();
      if(!hay.includes(q)) return false;
    }
    return true;
  });
  $('#act-count').textContent = `共 ${list.length} 项 / 全部 ${CAT.activities.length} 项`;

  $('#act-list').innerHTML = list.map(a=>{
    const best = actBestScore(a);
    const hasZc = Object.keys(a.channels||{}).some(k=>chanRubric(k)==='综测');
    const hasTm = Object.keys(a.channels||{}).some(k=>chanRubric(k)==='推免');
    const chan = Object.entries(a.channels||{}).map(([k,v])=>{
      const neg = v < 0;
      return `<span class="chip">${esc(k)} ${neg?'':'基准 '}${n2(v,2)}${esc(chanUnit(k))}</span>`;
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
    return `<div class="act">
      <div class="t">${esc(a.name)}
        ${a.level?`<span class="chip">${esc(a.level)}</span>`:''}
        ${a.category?`<span class="chip">${esc(a.category)}</span>`:''}
        ${noChannel?`<span class="pill warn" style="font-size:11.5px">提示信息（不直接加分）</span>`
          : best.best>0?`<span class="pill ok" style="font-size:11.5px">综测最高 +${n2(best.best,2)} 分</span>`
          :`<span class="pill warn" style="font-size:11.5px">加分值未证实</span>`}
        ${best.bestTuimian>0?`<span class="pill pri" style="font-size:11.5px">推免最高 +${n2(best.bestTuimian,2)} 分</span>`:''}
        <span style="margin-left:auto"></span>
        ${noChannel?'':`<button class="mini ${added?'ghost':''}" data-add="${esc(a.id)}">${added?'已在篮中':'加入活动篮'}</button>`}
      </div>
      ${a.organizer?`<div class="m">主办：${esc(a.organizer)}</div>`:''}
      ${a.timing?`<div class="m">时间：${esc(a.timing)}</div>`:''}
      ${a.eligibility?`<div class="m">资格：${esc(a.eligibility)}</div>`:''}
      <div class="ach">${chan}</div>
      ${ach?`<div class="ach" style="align-items:stretch">${ach}</div>`:''}
      ${a.note?`<div class="meta">${esc(a.note)}</div>`:''}
      ${a.source?`<div class="basis">加分依据：${esc(a.source)}${a.confidence&&a.confidence!=='verified'?`（可信度：${esc(a.confidence)}）`:''}</div>`:''}
      ${a.url?`<div class="basis"><a href="${esc(a.url)}" target="_blank" rel="noopener">${esc(a.url)}</a></div>`:''}
    </div>`;
  }).join('') || '<div class="card"><div class="note">没有符合筛选条件的活动。</div></div>';

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

  $('#rules-body').innerHTML = `
  <div class="card"><h2>绩点折算表 <span class="sub">${esc(t.name)} · 上限 ${n2(t.max_gp,1)}</span></h2>
    <table><thead><tr><th style="width:150px">百分制分数</th><th class="num" style="width:150px">绩点</th><th>说明</th></tr></thead>
    <tbody>${bands}</tbody></table>
    <h2 style="font-size:13px;margin:14px 0 6px;color:var(--mut)">五级制折算</h2>
    <div class="ach">${lv}</div>
    <div class="note">
      不及格线 ${n2(t.fail_score,0)} 分。重修/补考口径：<b>${esc(t.retake_policy)}</b>，
      及格后封顶 ${n2(t.retake_cap,2)} 绩点；在成绩表里勾选「重修」即按此口径计算。<br>
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
  const holder = document.createElement('span');
  holder.className = 'row';
  holder.style.marginLeft = '8px';
  $('#term-all').onclick = ()=>{ TERM_FILTER = 0; renderCourses(); };
  $('#fill-demo').onclick = fillDemo;
  $('#clear-scores').onclick = ()=>{
    if(!confirm('清空所有已录成绩？')) return;
    state.scores = {}; state.retakes = []; save(); renderCourses(); scheduleEval(60);
  };
  $('#basket-clear').onclick = ()=>{ state.basket = []; save(); renderActivities(); scheduleEval(40); };
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
    b.onclick = ()=>{ TERM_FILTER = t.term; renderCourses(); };
    row.insertBefore(b, anchor);
  });
}

function fillDemo(){
  if(!MAJOR) return;
  // 只填大一大二已出分的课，分数是随机示例，避免和真实成绩混淆
  let seed = 20240901;
  const rnd = ()=>{ seed = (seed*1103515245+12345) % 2147483648; return seed/2147483648; };
  state.scores = {};
  MAJOR.courses.forEach(c=>{
    if(c.term>4 || c.term<1) return;
    if(c.assess==='五级制'){ state.scores[c.code]='良好'; return; }
    state.scores[c.code] = Math.round(72 + rnd()*24);
  });
  save(); renderCourses(); scheduleEval(60);
}

/* ============================== 启动 ============================== */
async function boot(){
  load();
  try{
    CAT = await api('/api/calc/catalog');
  }catch(e){
    $('#pills').innerHTML = `<span class="pill err">无法加载计算器数据：${esc(e.message)}<br>请确认 calcdata/ 下有 rules/majors/goals/activities.json</span>`;
    return;
  }
  buildMajorSelect();
  setMajor();
  renderCourses();
  renderMetrics();
  fillFilters();
  renderActivities();
  renderRules();
  bindTop();
  termButtons();
  await runEval();
}
boot();
</script>
</body>
</html>
"""


CALC_DOCS_PAGE = r"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>计算器数据口径说明</title>
<style>
 body{margin:0;font:14.5px/1.7 -apple-system,"Segoe UI","Microsoft YaHei",sans-serif;
      color:#1f2328;background:#f6f8fa}
 header{background:#fff;border-bottom:1px solid #d0d7de;padding:12px 20px;display:flex;
        gap:14px;align-items:center;position:sticky;top:0}
 header h1{font-size:16.5px;margin:0}
 header a{font-size:13px;color:#0969da;text-decoration:none;border:1px solid #d0d7de;
          border-radius:99px;padding:3px 11px;background:#fff}
 main{max-width:900px;margin:0 auto;padding:20px}
 .card{background:#fff;border:1px solid #d0d7de;border-radius:10px;padding:18px;margin-bottom:14px}
 h2{font-size:15px;margin:0 0 10px}
 h3{font-size:14px;margin:16px 0 6px;color:#656d76}
 code{background:#f6f8fa;padding:1px 5px;border-radius:4px;font-size:13px}
 pre{background:#f6f8fa;border:1px solid #d0d7de;border-radius:8px;padding:11px;
     overflow:auto;font-size:12.5px}
 table{border-collapse:collapse;width:100%;font-size:13.5px}
 th,td{border-bottom:1px solid #d0d7de;padding:6px 8px;text-align:left}
 th{background:#f6f8fa;font-size:12.5px;color:#656d76}
 .warn{background:#fdf6e3;border:1px solid #eeddaa;border-radius:8px;padding:11px;color:#9a6700}
</style></head><body>
<header><h1>📐 计算器数据口径说明</h1><a href="/calc">← 回到计算器</a><a href="/">信息检索</a></header>
<main>
<div class="card">
  <h2>为什么要写这一页</h2>
  <p>这个计算器的每一个数字都来自 <code>calcdata/</code> 下的四个 JSON 文件，代码里<b>不含任何学校特有的数字</b>。
  所以你可以直接打开那些文件核对、修改，改完刷新页面立刻生效。</p>
  <div class="warn"><b>重要：这些数值是规划用的，不是学籍依据。</b>
  培养方案的课程学分、综测的权重与加分表，各学院、各年份都可能不同。
  请务必用你自己的培养方案（教务系统「培养方案查询」）和本学院当年发布的实施细则核对后再依赖它做决策。
  每个数据点上都有 <code>confidence</code> 字段说明它的可信程度。</div>
</div>

<div class="card">
  <h2>四个数据文件分别管什么</h2>
  <table>
    <thead><tr><th style="width:190px">文件</th><th>内容</th></tr></thead>
    <tbody>
      <tr><td><code>rules.json</code></td><td>百分制→绩点的折算表、重修口径、综测各分项与权重、加分路由、级别/名次折算系数、出处清单</td></tr>
      <tr><td><code>majors.json</code></td><td>专业培养方案：学分构成、逐门课程的代码/名称/学分/开课学期/是否计绩点/是否计排名</td></tr>
      <tr><td><code>goals.json</code></td><td>保研、考研、各类奖学金的门槛：每一条写成 <code>{metric, op, value}</code></td></tr>
      <tr><td><code>activities.json</code></td><td>可加分活动与竞赛清单：类别、级别、主办方、加分通道与基准分、报名时间、加分依据出处</td></tr>
    </tbody>
  </table>
</div>

<div class="card">
  <h2>怎么算的</h2>
  <h3>1. 平均学分绩点</h3>
  <pre>一门课程的学分绩点 = 该课程的学分数 × 绩点数
平均学分绩点 = 全部学分绩点之和 ÷ 所修学分之和</pre>
  <p>绩点折算按官方原文（《华南农业大学本科学生学籍管理实施细则》华南农办〔2021〕68号
  第十二条）：<b>100 分 = 5.00 绩点，每 1 分 = 0.10 绩点，低于 60 分 = 0 绩点</b>，
  也就是 <code>绩点 = 分数 ÷ 20</code>（60 分 = 3.00、80 分 = 4.00、100 分 = 5.00）。
  不分档，也不是 4.0 制。五级制：优秀 4.50 / 良好 3.50 / 中等 2.50 / 及格 1.50 / 不及格 0。</p>
  <div class="warn"><b>原文有一处不自洽，请注意核对。</b>
  原文那句「100分折算为5.00绩点，99分折算为4.90绩点……依此类推」如果真按每分 0.10 一路降下去，
  60 分只剩 1.00 绩点——但那样 5.00 的满分就没有下限约束了。本工具采用「绩点 = 分数 ÷ 20」，
  这是 5 分制下最常见的读法。<b>如果你教务系统里 60 分显示的是 1.0 而不是 3.0，
  把 <code>calcdata/rules.json</code> 的 <code>gpa.bands</code> 改成你系统的实际值即可</b>，
  代码不用动。折算表逐分核对过（<code>data/research/check_grade_bands.py</code>）。</div>

  <p><b>哪些课计入绩点：</b>官方原文是「已选课程均参与学期学分绩点的计算」
  （《本科生选课管理规定》华南农办〔2016〕158号 第十一条；
  《本科通识教育选修课程管理规定》华南农办〔2023〕1号 第十六条同义），
  所以<b>通识选修、体育、实验课都计入平均学分绩点</b>，没有「只计必修课」的规定。
  工具里另有「保研用学业绩点」，那是按学院推免口径只算计入排名的课程——
  这两个数不一样是正常的。</p>

  <p><b>补考与重修：</b>官方原文「补考和重修成绩按考核实际分数记载并予以标注，
  成绩及格及以上的，其绩点折合为 1.00」（《本科课程考核管理规定》
  华南农办〔2021〕64号 第二十八条）。所以在成绩表里勾选「重修」，
  该课就按 1.00 绩点计入。<b>不及格的首修课程仍然按 0 绩点计入绩点</b>——
  这是惩罚也是提示：挂科对绩点的伤害是真实的，只有补考通过后才封顶到 1.00。</p>

  <h3>2. 综测总分</h3>
  <pre>综合测评总成绩 = 德育（20分）+ 智育（65分）+ 体育（5分）+ 美育（5分）+ 劳育（5分）</pre>
  <p>这是生命科学学院 2026 修订细则第五条的原文口径：<b>分值制</b>，不是「百分制 × 权重」。
  每个分项内部又分成「基础分」和「加分」，加分另有上限（细则叫「加分不超过 X 分」）：</p>
  <table>
    <thead><tr><th>分项</th><th>满分</th><th>基础分</th><th>加分上限</th><th>基础分怎么来</th></tr></thead>
    <tbody>
      <tr><td>德育</td><td>20</td><td>15（基础分10 + 班内互评5）</td><td>5</td><td>个人自评 + 班级互评，手填</td></tr>
      <tr><td>智育</td><td>65</td><td>55</td><td>10</td><td>本人绩点 ÷ 专业最高绩点 × 55，自动算</td></tr>
      <tr><td>体育</td><td>5</td><td>3</td><td>2</td><td>体测成绩折算，手填 0-3</td></tr>
      <tr><td>美育</td><td>5</td><td>3</td><td>2</td><td>班级在学年总结基础上评价，手填 0-3</td></tr>
      <tr><td>劳育</td><td>5</td><td>3</td><td>2</td><td>班级在学年总结基础上评价，手填 0-3</td></tr>
    </tbody>
  </table>
  <p>活动篮里的加分按 <code>comprehensive.bonus_routing</code> 路由：路由到某分项（如「德育加分」→德育）
  的会加到该分项的分项加分里，再受该分项的 <code>bonus_cap</code> 约束，超出会被截断并提示；
  路由到 <code>direct</code> 的（细则直接给综测总分的加分）直接加到总分；
  路由到 <code>none</code> 的（第二课堂学分、志愿服务时长、推免专用的创新能力/发展素养）不进综测总分。</p>
  <div class="warn"><b>为什么 <code>none</code> 必须显式写出来？</b>
  否则代码无法区分「细则没给这个通道」和「这个通道本来就不算综测」。
  早期版本漏了这一步，结果把「第二课堂 1.5 学分」当成「综测加 1.5 分」直接加到总分上，
  综测分虚高到 130 多。这个 bug 现在有回归测试守着（见 <code>data/research/smoke_calc.py</code> 第 2 节）。</div>

  <h3>3. 活动单次得分</h3>
  <pre>单次得分 = 通道基准分 × 等级系数 × 名次系数 × 份数</pre>
  <p>生命科学学院细则把每个等级的分值都写死了，所以清单里绝大多数活动是
  <code>discount: "none"</code>，分值直接来自细则表格的 <code>achieve_map</code>，
  系数不介入。只有细则没给全等级的活动（以及你自建的活动）才用
  <code>rules.json → discount.level_ratio</code> 的系数折算。</p>
  <p>清单里有一个「德育扣分项」活动，它的分值就是负数——用来模拟违纪、旷课、违规电器
  对综测的影响。加入篮子后能看到德育分被扣掉多少。</p>

  <h3>4. 门槛判定与课程分摊</h3>
  <p>门槛是纯数据：<code>{"metric":"cet4_score","op":">=","value":425}</code>。
  判定后如果卡在绩点上，就用</p>
  <pre>剩余课程所需平均绩点 = (目标绩点×总学分 − 已锁定绩点×学分) / 剩余学分</pre>
  <p>再用折算表反解成百分制分数，按学期列出「每门课至少要考多少分」，
  并给出难度评估。因为平均绩点只约束 Σ(绩点×学分)，所以还会算一个「偏科方案」：
  如果挑学分最大的几门课冲到 95 分，剩下的课需要多少分——这往往比「每门都考 99」现实得多。
  如果算出来超过折算表上限，会明确告诉你「即使全部满分也达不到」以及理论上限。</p>
</div>

<div class="card">
  <h2>confidence 字段的含义</h2>
  <table>
    <thead><tr><th style="width:210px">取值</th><th>含义</th></tr></thead>
    <tbody>
      <tr><td><code>verified</code></td><td>已对照官方原文核验，并在 <code>source</code> 里给了链接</td></tr>
      <tr><td><code>provisional</code></td><td>有公开依据，但没拿到原文逐条核对，属于通行口径</td></tr>
      <tr><td><code>provisional_adjustable</code></td><td>规划用近似值，<b>请自行替换</b></td></tr>
      <tr><td><code>unverified</code></td><td>只知道有这个活动，加分数值没找到依据（界面上标「加分值未证实」）</td></tr>
    </tbody>
  </table>
</div>

<div class="card">
  <h2>怎么把数据换成你自己学院的</h2>
  <ol>
    <li>打开教务系统的「培养方案查询」，把课程名、学分、学期抄进 <code>majors.json</code> 对应专业；</li>
    <li>改完记得把该专业的 <code>total_credits</code> 改成课程学分合计（校验器会提示不一致）；</li>
    <li>找到本学院当年的《综合素质测评实施细则》，把权重改到 <code>rules.json</code> 的
        <code>comprehensive.dimensions</code>，把加分明细填到 <code>activities.json</code>；</li>
    <li>把每一条的 <code>confidence</code> 从 <code>provisional</code> 改成 <code>verified</code>，
        并在 <code>source</code> 里写上文件标题和链接。</li>
  </ol>
  <p>改完刷新页面即可，无需改任何 Python 代码。</p>
</div>
</main></body></html>
"""
