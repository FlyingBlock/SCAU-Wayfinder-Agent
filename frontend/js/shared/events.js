/* 极简事件总线：功能模块之间只通过事件通信，不互相摸 window 全局。 */
const listeners = new Map();

export function on(name, fn) {
  if (!listeners.has(name)) listeners.set(name, new Set());
  listeners.get(name).add(fn);
  return () => listeners.get(name)?.delete(fn);
}

export function emit(name, detail) {
  for (const fn of [...(listeners.get(name) || [])]) {
    try { fn(detail); } catch (e) { console.error(`[events:${name}]`, e); }
  }
}
