/* 路由与外壳：只负责视图切换、侧栏和 hash 路由，不认识聊天/计算器内部。 */
import { $, $$ } from './shared/dom.js';

const SUBS = {scores: 'tab-profile', goals: 'tab-goals', acts: 'tab-acts', rules: 'tab-rules'};
const SUB_KEY = {'tab-profile': 'scores', 'tab-goals': 'goals', 'tab-acts': 'acts', 'tab-rules': 'rules'};
const TITLES = {chat: '主页对话', calc: '绩点 / 综测计算器'};

let VIEW = 'chat';
let SUB = 'scores';
const hooks = new Map();

/** 功能模块注册视图钩子：{boot, sync}，由 main.js 在启动时调用。 */
export function registerView(name, hook) {
  hooks.set(name, hook || {});
}
export function currentView() {
  return VIEW;
}
function runHook(name, method) {
  const hook = hooks.get(name);
  if (!hook || typeof hook[method] !== 'function') return;
  try { hook[method](); } catch (e) { console.error(`[view:${name}.${method}]`, e); }
}

function setSidebar(open) {
  const sb = $('#sidebar');
  if (!sb) return;
  sb.classList.toggle('closed', !open);
  try { localStorage.setItem('scau-side', open ? '1' : '0'); } catch (e) {}
}
function sidebarOpen() {
  try { return localStorage.getItem('scau-side') !== '0'; } catch (e) { return true; }
}
function renderSub() {
  const label = $('#sub-label');
  const on = SUB_KEY[SUB] || (SUBS[SUB] ? SUB : 'scores');
  if (label) label.textContent = '绩点 / 综测计算器 · ' + (({
    scores: '① 我的成绩', goals: '② 门槛对照', acts: '③ 活动篮', rules: '④ 计算口径',
  })[on] || '我的成绩');
}
function applySub() {
  Object.entries(SUBS).forEach(([key, id]) => {
    const el = $('#' + id);
    if (el) el.classList.toggle('hide', key !== SUB);
  });
  $$('#side-nav a.sub').forEach(a => a.classList.toggle(
    'on', a.dataset.sub === SUB && a.dataset.view === 'calc'));
  renderSub();
}

export function nav(view, sub) {
  VIEW = TITLES[view] ? view : 'chat';
  if (VIEW === 'calc' && SUBS[sub]) SUB = sub;
  $$('#side-nav a[data-view]').forEach(a => a.classList.toggle('on', a.dataset.view === VIEW));
  $$('.view').forEach(v => {
    const on = v.id === 'view-' + VIEW;
    v.classList.toggle('on', on);
    if (on && v.dataset.flex === '1') v.classList.add('vflex');
  });
  /* 对话视图内部滚动；计算器是普通长页面，交给 #appmain。 */
  const main = $('#appmain');
  if (main) main.classList.toggle('noscroll', VIEW === 'chat');
  if (VIEW === 'calc') {
    applySub();
    runHook('calc', 'boot');
  }
  if (VIEW === 'chat') runHook('chat', 'sync');
  document.title = (TITLES[VIEW] || '') + ' · SCAU Wayfinder · 学生发展信息助手';
  window.scrollTo(0, 0);
  if (main) main.scrollTop = 0;
}

export function hashNav(hash) {
  if ((hash || '').indexOf('#/calc') === 0) {
    const parts = hash.split('/');
    return nav('calc', parts[2] || 'scores');
  }
  return nav('chat');
}

export function go(view, sub) {
  location.hash = view === 'calc' ? '#/calc/' + (sub || 'scores') : '#/chat';
}

/** 启动外壳：绑定侧栏/快捷问题/hashchange，并按当前 URL 落到视图。 */
export function startRouter() {
  const menu = $('#menu-btn');
  if (menu) menu.onclick = () => setSidebar($('#sidebar').classList.contains('closed'));
  setSidebar(sidebarOpen());

  $$('#side-nav a[data-view]').forEach(a => {
    a.onclick = e => {
      if (a.dataset.view === 'calc') {
        e.preventDefault();
        go('calc', a.dataset.sub);
      }
    };
  });
  const docs = $('#side-docs');
  if (docs) docs.onclick = e => { e.preventDefault(); go('calc', 'rules'); };
  $$('.sug, .ex').forEach(el => {
    el.onclick = () => {
      const q = $('#q');
      if (!q) return;
      q.value = el.dataset.q || '';
      q.dispatchEvent(new Event('input'));
      q.focus();
    };
  });

  window.addEventListener('hashchange', () => hashNav(location.hash));
  if (location.hash) return hashNav(location.hash);

  const path = location.pathname.replace(/\/+$/, '');
  if (path === '/calc-docs') return hashNav('#/calc/rules');
  if (path === '/calc' || path.indexOf('/calc/') === 0) {
    const sub = path.split('/')[2] || 'scores';
    return hashNav('#/calc/' + (SUBS[sub] ? sub : 'scores'));
  }
  return hashNav('#/chat');
}
