/* ===================== ⚙️ 设置：模型 / OCR / 账号登录 ===================== */
import { $, $$, esc } from '../../shared/dom.js';
import { getJSON, postJSON } from '../../shared/api.js';
import { toast } from '../../shared/toast.js';
import { emit, on } from '../../shared/events.js';

function setMsg(html, kind){
  const el=$('#set-msg');
  if(!html){ el.className='msg hide'; el.innerHTML=''; return; }
  el.className='msg '+(kind||''); el.innerHTML=html;
}
function setBusy(on, what){
  $('#set-save').disabled=on; $('#set-test').disabled=on;
  if(on) setMsg('<span class="spin"></span> '+esc(what), '');
}
function openSettings(){
  $('#set-bd').classList.remove('hide');
  setMsg(''); ocrMsg(''); authMsg(''); authCaptcha(false);
  $('#set-base').value=''; $('#set-model').value=''; $('#set-key').value='';
  $('#set-presets').innerHTML='';
  $('#auth-pass').value='';
  setBusy(true,'正在读取当前配置…');
  loadOcrSettings();
  loadAuthSettings();
  getJSON('/api/settings/llm').then(d=>{
    setBusy(false);
    $('#set-base').value = d.base_url||'';
    $('#set-model').value = d.model||'';
    $('#set-key').value = '';
    $('#set-key').placeholder = d.api_key_set
      ? ('已保存 '+d.api_key_masked+'，留空表示不改动') : 'sk-… （必填）';
    $('#set-file').textContent = '写入 ' + (d.env_file||'.env');
    $('#set-presets').innerHTML = (d.presets||[]).map((p,i)=>
      `<button type="button" class="ghost" data-i="${i}" title="${esc(p.note||'')}">${esc(p.label)}</button>`).join('');
    $('#set-presets').querySelectorAll('button').forEach(b=>{
      b.onclick = ()=>{
        const p = d.presets[+b.dataset.i];
        $('#set-base').value = p.base_url; $('#set-model').value = p.model;
        setMsg('已填入 <b>'+esc(p.label)+'</b> 的端点与模型名，别忘了填 API key。','warn');
      };
    });
    if(d.writable===false){
      $('#set-save').disabled=true; $('#set-test').disabled=true;
      setMsg('当前不是从本机（127.0.0.1）访问的，为了不把 key 交出去，这里只能看不能改。','warn');
    }else if(d.shadowed && d.shadowed.length){
      setMsg('注意：系统环境变量里已经有 <b>'+esc(d.shadowed.join('、'))+
             '</b>，它的优先级高于 .env —— 这里保存本次运行会生效，'+
             '但重启后还是会被环境变量盖回去。','warn');
    }else if(!d.configured){
      setMsg('还没配置。填好三项后点「保存并验证」。','warn');
    }
    $('#set-base').focus();
  }).catch(e=>{ setBusy(false); setMsg('读取配置失败：'+esc(String(e)),'err'); });
}
function closeSettings(){ $('#set-bd').classList.add('hide'); }

/* ---------- 设置弹窗的三个分页 ---------- */
function setTab(name){
  $$('#set-bd .set-tabs button').forEach(b=>b.classList.toggle('on', b.dataset.tab===name));
  const panes = {llm:'#set-pane-llm', ocr:'#set-pane-ocr', auth:'#set-pane-auth'};
  Object.entries(panes).forEach(([k,sel])=>{
    const el = $(sel); if(el) el.classList.toggle('hide', k!==name);
  });
  if(name==='ocr') loadOcrSettings();
  if(name==='auth') loadAuthSettings();
}
/* ---------- 附件与 OCR ---------- */
function ocrMsg(html, kind){
  const el=$('#ocr-msg'); if(!el) return;
  if(!html){ el.className='msg hide'; el.innerHTML=''; return; }
  el.className='msg '+(kind||''); el.innerHTML=html;
}
function ocrBusy(on){
  ['#ocr-save','#ocr-test','#ocr-clear'].forEach(s=>{ const el=$(s); if(el) el.disabled=on; });
}
function ocrPayload(){
  return {
    provider: $('#ocr-provider').value,
    api_key: $('#ocr-key').value,
    secret_key: $('#ocr-secret').value,
    accurate: $('#ocr-accurate').checked,
  };
}
function loadOcrSettings(){
  ocrBusy(true);
  getJSON('/api/settings/ocr').then(d=>{
    ocrBusy(false);
    $('#ocr-provider').value = d.provider || 'none';
    $('#ocr-accurate').checked = !!d.accurate;
    $('#ocr-key').value=''; $('#ocr-secret').value='';
    $('#ocr-key').placeholder = d.api_key_set
      ? ('已保存 '+d.api_key_masked+'，留空表示不改动') : 'API Key（AK）';
    $('#ocr-secret').placeholder = d.secret_key_set
      ? ('已保存 '+d.secret_key_masked+'，留空表示不改动') : 'Secret Key（SK）';
    $('#ocr-hint').textContent = d.label
      ? ('当前：' + d.label + '　申请地址 console.bce.baidu.com（开通「通用文字识别」）')
      : '未启用 OCR：附件里的文字照常解析，只有图片/扫描件里的字提取不到。';
    if(d.attach_dir) $('#ocr-dir').textContent = d.attach_dir;
    $('#ocr-astat').textContent = d.attach_stat
      ? ('附件目录：' + d.attach_stat.files + ' 个文件 / ' + d.attach_stat.human +
         '　已入库附件 ' + (d.attachments||0) + ' 个（有正文 ' + (d.attachments_with_text||0) + ' 个）')
      : '';
    if(d.writable===false){
      ['#ocr-save','#ocr-test','#ocr-clear'].forEach(s=>{ const el=$(s); if(el) el.disabled=true; });
      ocrMsg('当前不是从本机（127.0.0.1）访问的，只能看不能改。','warn');
    }else if(d.shadowed && d.shadowed.length){
      ocrMsg('系统环境变量里已有 <b>'+esc(d.shadowed.join('、'))+'</b>，优先级高于 .env。','warn');
    }
  }).catch(e=>{ ocrBusy(false); ocrMsg('读取 OCR 配置失败：'+esc(String(e)),'err'); });
}
async function saveOcr(verify){
  ocrBusy(true);
  ocrMsg('<span class="spin"></span> ' + (verify ? '正在用测试图真实调用 OCR…' : '正在保存…'));
  try{
    const r = await postSettings('/api/settings/ocr',
      Object.assign(ocrPayload(), {verify: verify, persist: true}));
    const d = r.d;
    ocrBusy(false);
    if(d.ok){
      ocrMsg('✅ ' + esc(d.message || '已保存') + (d.warning ? '<br>'+esc(d.warning) : ''),
             d.warning ? 'warn' : 'ok');
      $('#ocr-key').value=''; $('#ocr-secret').value='';
      loadOcrSettings();
      emit('status:refresh');
    }else{
      ocrMsg('❌ ' + esc(d.error || ('HTTP '+r.status)) +
             (d.hint ? '<br><span class="small">'+esc(d.hint)+'</span>' : ''), 'err');
    }
  }catch(e){ ocrBusy(false); ocrMsg('保存失败：'+esc(String(e)),'err'); }
}
async function testOcr(){
  ocrBusy(true); ocrMsg('<span class="spin"></span> 正在识别一张测试图…');
  try{
    const r = await postSettings('/api/settings/ocr/test', ocrPayload());
    const d = r.d; ocrBusy(false);
    if(d.ok) ocrMsg('✅ ' + esc(d.message),'ok');
    else ocrMsg('❌ ' + esc(d.error || ('HTTP '+r.status)),'err');
  }catch(e){ ocrBusy(false); ocrMsg('测试失败：'+esc(String(e)),'err'); }
}
async function clearOcr(){
  ocrBusy(true); ocrMsg('正在清除…');
  try{
    const r = await postSettings('/api/settings/ocr/clear', {});
    const d = r.d; ocrBusy(false);
    ocrMsg(d.ok ? '✅ 已清除 OCR 凭据' : ('❌ ' + esc(d.error||'清除失败')), d.ok?'ok':'err');
    loadOcrSettings();
  }catch(e){ ocrBusy(false); ocrMsg('清除失败：'+esc(String(e)),'err'); }
}

/* ---------- 🔐 账号与登录 ---------- */
let AUTH_CAP_TOKEN = '';
function authMsg(html, kind){
  const el=$('#auth-msg'); if(!el) return;
  if(!html){ el.className='msg hide'; el.innerHTML=''; return; }
  el.className='msg '+(kind||''); el.innerHTML=html;
}
function authBusy(on){
  ['#auth-save','#auth-save-only','#auth-clear','#auth-logout','#auth-cap-go','#auth-cap-retry']
    .forEach(s=>{ const el=$(s); if(el) el.disabled=on; });
}
function authCaptcha(show, dataUrl, token){
  const wrap = $('#auth-cap-wrap');
  if(!wrap) return;
  if(show){
    AUTH_CAP_TOKEN = token || '';
    if(dataUrl) $('#auth-cap-img').src = dataUrl;
    wrap.classList.remove('hide');
  }else{
    AUTH_CAP_TOKEN = '';
    wrap.classList.add('hide');
    $('#auth-cap-text').value = '';
  }
}
function authPayload(verify){
  return {
    username: $('#auth-user').value.trim(),
    password: $('#auth-pass').value,
    service: $('#auth-service').value.trim(),
    captcha_url: $('#auth-captcha-url').value.trim(),
    captcha_rounds: parseInt($('#auth-rounds').value || '3', 10) || 3,
    save_password: $('#auth-save-pw').checked,
    auto_login: $('#auth-auto').checked,
    ocr_captcha: $('#auth-ocr').checked,
    verify: verify, persist: true,
  };
}
function authFill(d){
  const c = d.credentials || {}, s = d.session || {}, g = d.settings || {};
  $('#auth-user').value = '';
  $('#auth-user').placeholder = c.username_set
    ? ('已保存 ' + c.username_masked + '，留空表示不改动') : '2023xxxxxxxx';
  // 密码框不清空：卡在「人工填验证码」那一步时，还要用它把登录做完
  $('#auth-pass').placeholder = c.password_set
    ? '已保存密码，留空表示不改动' : '统一身份认证密码';
  $('#auth-service').value = g.service || '';
  $('#auth-captcha-url').value = g.captcha_url || '';
  $('#auth-rounds').value = g.captcha_rounds || 3;
  $('#auth-auto').checked = !!g.auto_login;
  $('#auth-ocr').checked = !!g.ocr_captcha;
  $('#auth-save-pw').checked = true;
  $('#auth-ocr-hint').textContent = d.ocr_configured
    ? 'OCR 已配置，验证码可以直接自动识别。'
    : ('⚠️ 还没配 OCR（「🖼 附件与 OCR」分页）—— 没有它的话，遇到验证码只能在这里手填一次，'
       + '采集时也没法自动过。');
  const bits = [];
  if(s.cookies_alive) bits.push('会话有效：' + s.cookies_alive + ' 个 cookie');
  else if(s.cookie_file_exists) bits.push('会话已过期（cookie 文件在，但都失效了）');
  else bits.push('当前无会话');
  if(c.username_set) bits.push('已存账号 ' + c.username_masked + (c.saved_at ? '（' + c.saved_at + '）' : ''));
  bits.push('CAS ' + (d.cas_base || ''));
  $('#auth-stat').textContent = bits.join('　·　');
  $('#auth-file').textContent = '凭据文件 ' + ((c.file) || '.auth/credentials.json');
  if(d.writable === false){
    authBusy(true);
    authMsg('当前不是从本机（127.0.0.1）访问的，为了不把账号交出去，这里只能看不能改。','warn');
  }
}
function loadAuthSettings(){
  authBusy(true);
  getJSON('/api/settings/auth').then(d=>{
    authBusy(false);
    authFill(d);
    if(d.writable !== false && d.shadowed && d.shadowed.length){
      authMsg('系统环境变量里已有 <b>'+esc(d.shadowed.join('、'))+'</b>，优先级高于 .env。','warn');
    }
  }).catch(e=>{ authBusy(false); authMsg('读取登录配置失败：'+esc(String(e)),'err'); });
}
function authResultMessage(d){
  if(d.ok && d.verified) return '✅ ' + esc(d.message || '登录成功');
  if(d.need_captcha) return '';
  if(d.ok && !d.verified){
    return (d.error ? '⚠️ ' + esc(d.message || '') + '<br>' + esc(d.error)
                    : '✅ ' + esc(d.message || '已保存'));
  }
  return '❌ ' + esc(d.error || '登录失败');
}
async function saveAuth(verify){
  authBusy(true);
  authMsg('<span class="spin"></span> ' + (verify
    ? '正在真实登录统一身份认证（有验证码会自动识别）…' : '正在保存…'));
  try{
    const r = await postSettings('/api/settings/auth', authPayload(verify));
    const d = r.d;
    authBusy(false);
    authFill(d);
    if(d.need_captcha){
      authCaptcha(true, d.captcha_image || '', d.token || '');
      authMsg('🔎 ' + esc(d.error || 'OCR 没认出验证码') +
              (d.hint ? '<br><span class="small">' + esc(d.hint) + '</span>' : ''), 'warn');
      const t = $('#auth-cap-text'); if(t) t.focus();
      return;
    }
    authCaptcha(false);
    if(d.ok && (d.verified || !verify)){
      authMsg(authResultMessage(d) + (d.warning ? '<br>' + esc(d.warning) : ''),
              d.warning ? 'warn' : 'ok');
      $('#auth-pass').value = '';
      emit('status:refresh');
      if(d.verified) toast('✅ 已登录统一身份认证，采集会带着这个会话');
    }else{
      authMsg(authResultMessage(d) + (d.hint ? '<br><span class="small">'+esc(d.hint)+'</span>' : ''),
              'err');
    }
  }catch(e){ authBusy(false); authMsg('保存失败：'+esc(String(e)),'err'); }
}
async function submitCaptcha(retryOnly){
  const text = retryOnly ? '' : ($('#auth-cap-text').value || '').trim();
  if(!retryOnly && !text){ authMsg('先填一下图里的验证码。','warn'); return; }
  authBusy(true);
  authMsg('<span class="spin"></span> ' + (retryOnly ? '正在换一张验证码…' : '正在提交验证码…'));
  try{
    if(retryOnly){
      // 「换一张」= 重新走一次「保存并登录」，会重新拉一张新的验证码图
      const r = await postSettings('/api/settings/auth', authPayload(true));
      const d = r.d; authBusy(false); authFill(d);
      if(d.need_captcha){
        authCaptcha(true, d.captcha_image || '', d.token || '');
        authMsg('🔎 这是新的一张，照着填。','warn');
      }else if(d.ok && d.verified){
        authCaptcha(false); $('#auth-pass').value=''; authMsg('✅ ' + esc(d.message||'已登录'),'ok');
      }else{
        authCaptcha(false); authMsg('❌ ' + esc(d.error||d.message||'这次没成'),'err');
      }
      return;
    }
    const r = await postSettings('/api/settings/auth/captcha',
      {token: AUTH_CAP_TOKEN, captcha: text, password: $('#auth-pass').value});
    const d = r.d; authBusy(false); authFill(d);
    if(d.ok){
      authCaptcha(false); $('#auth-pass').value='';
      authMsg('✅ ' + esc(d.message||'已登录') +
              (d.warning ? '<br>'+esc(d.warning) : ''), d.warning?'warn':'ok');
      emit('status:refresh');
      toast('✅ 已登录统一身份认证，采集会带着这个会话');
    }else if(d.need_captcha){
      authCaptcha(true, d.captcha_image||'', d.token||'');
      authMsg('🔎 ' + esc(d.error||'验证码不对') +
              (d.hint ? '<br><span class="small">'+esc(d.hint)+'</span>' : ''), 'warn');
    }else{
      authCaptcha(false);
      authMsg('❌ ' + esc(d.error||'登录失败') +
              (d.hint ? '<br><span class="small">'+esc(d.hint)+'</span>' : ''), 'err');
    }
  }catch(e){ authBusy(false); authMsg('提交失败：'+esc(String(e)),'err'); }
}
async function clearAuth(){
  authBusy(true); authMsg('正在清除…');
  try{
    const r = await postSettings('/api/settings/auth/clear', {});
    const d = r.d; authBusy(false); authFill(d); authCaptcha(false);
    authMsg(d.ok ? '✅ ' + esc(d.message) : ('❌ ' + esc(d.error||'清除失败')), d.ok?'ok':'err');
  }catch(e){ authBusy(false); authMsg('清除失败：'+esc(String(e)),'err'); }
}
async function logoutAuth(){
  authBusy(true); authMsg('正在退出登录…');
  try{
    const r = await postSettings('/api/settings/auth/logout', {});
    const d = r.d; authBusy(false); authFill(d);
    authMsg(d.ok ? '✅ ' + esc(d.message) : ('❌ ' + esc(d.error||'失败')), d.ok?'ok':'err');
    emit('status:refresh');
  }catch(e){ authBusy(false); authMsg('失败：'+esc(String(e)),'err'); }
}

function setPayload(){
  return {
    base_url: $('#set-base').value.trim(),
    model: $('#set-model').value.trim(),
    api_key: $('#set-key').value,
  };
}
async function postSettings(path, payload){
  const {status, data} = await postJSON(path, payload);
  return {status, d: data || {}};
}
function bindForceSave(){
  const f = $('#set-force');
  if(f) f.onclick = ()=> saveSettings(false);
}
async function saveSettings(verify){
  setBusy(true, verify ? '正在用这套配置做一次真实调用验证…' : '正在保存…');
  try{
    const r = await postSettings('/api/settings/llm',
      Object.assign(setPayload(), {verify: verify, persist: true}));
    const d = r.d;
    setBusy(false);
    if(d.ok){
      setMsg('✅ ' + esc(d.message || '已保存') +
             (d.warning ? '<br>' + esc(d.warning) : ''), d.warning ? 'warn' : 'ok');
      $('#set-key').value='';
      if(d.api_key_set) $('#set-key').placeholder = '已保存 '+d.api_key_masked+'，留空表示不改动';
      emit('status:refresh');
    }else{
      setMsg('❌ ' + esc(d.error || ('HTTP '+r.status)) +
             (d.hint ? '<br><span class="small">'+esc(d.hint)+'</span>' : '') +
             (verify ? '<br><span class="lnk" id="set-force">跳过验证，仍然保存</span>' : ''), 'err');
      bindForceSave();
    }
  }catch(e){ setBusy(false); setMsg('保存失败：'+esc(String(e)),'err'); }
}
async function testSettings(){
  setBusy(true,'正在真实调用一次该端点…');
  try{
    const r = await postSettings('/api/settings/llm/test', setPayload());
    const d = r.d;
    setBusy(false);
    if(d.ok){
      setMsg('✅ 连接成功：<b>'+esc(d.model)+'</b> 回复「'+esc(d.reply)+'」（'+d.ms+' ms）','ok');
    }else{
      setMsg('❌ 连接失败：'+esc(d.error || ('HTTP '+r.status)) +
             (d.ms ? '（'+d.ms+' ms）' : ''), 'err');
    }
  }catch(e){ setBusy(false); setMsg('测试失败：'+esc(String(e)),'err'); }
}

export { openSettings, closeSettings, setTab };

/** 由 main.js 调用：绑定设置弹窗的 DOM 事件。 */
export function bindSettings() {
  $$('#set-bd .set-tabs button').forEach(b => {
    b.onclick = () => setTab(b.dataset.tab);
  });
  const bind = (selector, handler) => {
    const el = $(selector);
    if (el) el.onclick = handler;
  };
  bind('#settings-btn', openSettings);
  bind('#set-save', () => saveSettings(true));
  bind('#set-test', testSettings);
  bind('#set-close', closeSettings);
  bind('#ocr-save', () => saveOcr(true));
  bind('#ocr-test', testOcr);
  bind('#ocr-clear', clearOcr);
  bind('#ocr-close', closeSettings);
  bind('#auth-save', () => saveAuth(true));
  bind('#auth-save-only', () => saveAuth(false));
  bind('#auth-clear', clearAuth);
  bind('#auth-logout', logoutAuth);
  bind('#auth-close', closeSettings);
  bind('#auth-cap-go', () => submitCaptcha(false));
  bind('#auth-cap-retry', () => submitCaptcha(true));
  const cap = $('#auth-cap-text');
  if (cap) cap.onkeydown = e => { if (e.key === 'Enter') submitCaptcha(false); };
  const provider = $('#ocr-provider');
  if (provider) provider.onchange = () => {
    const on = provider.value !== 'none';
    $('#ocr-key').disabled = !on;
    $('#ocr-secret').disabled = !on;
  };
  const bd = $('#set-bd');
  if (bd) bd.onclick = e => { if (e.target === bd) closeSettings(); };
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeSettings(); });
  on('settings:open', openSettings);
}
