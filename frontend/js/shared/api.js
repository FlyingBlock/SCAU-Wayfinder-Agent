/* 统一 HTTP 客户端：功能模块不再各自写 fetch / 错误处理。 */
export async function requestJSON(path, {method = 'GET', body} = {}) {
  const init = {method};
  if (body !== undefined) {
    init.headers = {'Content-Type': 'application/json'};
    init.body = JSON.stringify(body);
  }
  const res = await fetch(path, init);
  let data = {};
  try { data = await res.json(); } catch (e) { /* 非 JSON 响应 */ }
  return {status: res.status, data: data || {}};
}

export async function getJSON(path) {
  const {status, data} = await requestJSON(path);
  if (status >= 400) throw new Error(data.error || `HTTP ${status}`);
  return data;
}

export async function postJSON(path, body) {
  return requestJSON(path, {method: 'POST', body: body || {}});
}
