/* 展示格式化：纯函数，不含业务规则。 */
export const n2 = (v, d = 2) => (
  v == null || v === ''
    ? '—'
    : (Math.round(v * 100) / 100).toFixed(d).replace(/\.?0+$/, '') || '0'
);

export const n2s = (v, d = 2) => {
  const x = Math.round((v || 0) * 100) / 100;
  return (x === 0 ? '0' : String(x)).replace(/(\.\d*?)0+$/, '$1').replace(/\.$/, '');
};
