/* 轻提示：底部气泡，2.6 秒后自己消失。 */
import { $ } from './dom.js';

let toastTimer = null;

export function toast(html, ms) {
  const el = $('#toast');
  if (!el) return null;
  el.innerHTML = html;
  el.classList.add('on');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove('on'), ms || 2600);
  return el;
}
