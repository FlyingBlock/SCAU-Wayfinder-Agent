/* 计算器状态：localStorage 的唯一读写入口，对话页也通过这里加入活动篮。 */
import { emit, on } from '../../shared/events.js';

const LS_KEY = 'scau-calc-state-v1';

export const state = {
  major_id: '',
  grade: '',
  cohort_size: 0,
  rank: 0,
  scores: {},
  retakes: [],
  metrics: {},
  basket: [],
};

export function save() {
  try { localStorage.setItem(LS_KEY, JSON.stringify(state)); } catch (e) {}
}

export function loadState() {
  try {
    const raw = localStorage.getItem(LS_KEY);
    if (!raw) return;
    const saved = JSON.parse(raw);
    if (!saved || typeof saved !== 'object') return;
    Object.assign(state, saved);
    state.scores = state.scores && typeof state.scores === 'object' ? state.scores : {};
    state.metrics = state.metrics && typeof state.metrics === 'object' ? state.metrics : {};
    state.retakes = Array.isArray(state.retakes) ? state.retakes : [];
    state.basket = Array.isArray(state.basket) ? state.basket : [];
  } catch (e) {}
}

export function inBasket(activityId) {
  return state.basket.some(item => item.activity_id === activityId);
}

/** 加入活动篮；返回 false 表示已存在或参数非法。 */
export function addToBasket(item) {
  const id = item && item.activity_id;
  if (!id || inBasket(id)) return false;
  state.basket.push({
    activity_id: id,
    achieve: (item && item.achieve) || '',
    quantity: Math.max(1, parseInt((item && item.quantity) || 1, 10) || 1),
    name: (item && item.name) || '',
  });
  save();
  emit('basket:changed');
  return true;
}

export function onBasketChanged(fn) {
  return on('basket:changed', fn);
}

// 对话页可能在用户第一次进入计算器之前就入篮；模块加载时先把旧状态读进来，
// 避免用默认空对象覆盖已有成绩。
loadState();
