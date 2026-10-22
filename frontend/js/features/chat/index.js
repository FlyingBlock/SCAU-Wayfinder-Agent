/* ===================== 主页对话：输入、SSE 订阅与流式状态 ===================== */
import { $, esc } from '../../shared/dom.js';
import { getJSON } from '../../shared/api.js';
import { emit, on } from '../../shared/events.js';
import { currentView } from '../../router.js';
import {
  mdChat, SBOX, SOURCES, chatSourcesRender, chatSourcesToggle,
  sourcesInline, sourcesOpenPref, chatBindCites,
} from './content.js';
import { renderCards } from './cards.js';

const CHAT_STATE = { busy:false };

/** 后端只给错误码；用户可见文案由前端决定。 */
function answerErrorText(code){
  return ({
    empty_question: '问题不能为空。',
    llm_not_configured: '尚未配置 LLM API key。请在「设置 → 模型」填写，'
      + '或运行 python -m wayfinder setup-key；也可以先用「只检索」看结果。',
    empty_corpus: '库内还没有语料。请先运行：python -m wayfinder crawl --scope narrow',
    no_result: '这次生成没有返回结果，请稍后重试。',
  })[code] || '';
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
      if(lp) lp.onclick = () => emit('settings:open');
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
    const codeText = answerErrorText(d.code);
    a.body.innerHTML = (a.text ? mdChat(a.text, {streaming:false}) : '')
      + (codeText ? `<div class="err-line" style="color:var(--err)">${esc(codeText)}</div>` : '')
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
