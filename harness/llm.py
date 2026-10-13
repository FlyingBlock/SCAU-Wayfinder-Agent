"""LLM 适配层：任何 OpenAI 兼容的 /chat/completions 端点。

默认 DeepSeek（中文强、便宜），也可指向 Ollama / vLLM / 通义 / 智谱等，
只要在 .env 里写 LLM_BASE_URL + LLM_MODEL + LLM_API_KEY。

关键点（对应指南 §8.6 的坑）：
  · 模型名/端点是**显式配置**的，不做任何“静默回退”，配错就报错，
    避免“以为在调用 A 实际在调用 B”。
  · 所有 JSON 输出都走 `complete_json`，带容错解析（模型常包 ```json 围栏）。
  · 记录每次调用的 token 用量，便于成本核算（指南 §10.5/§10.6）。
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from .config import LLMSettings

JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.S)


class LLMError(RuntimeError):
    pass


class LLMNotConfigured(LLMError):
    pass


@dataclass
class Usage:
    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    seconds: float = 0.0

    def add(self, prompt: int, completion: int, secs: float) -> None:
        self.calls += 1
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.seconds += secs

    def line(self) -> str:
        total = self.prompt_tokens + self.completion_tokens
        return (f"LLM 调用 {self.calls} 次｜prompt {self.prompt_tokens} + "
                f"completion {self.completion_tokens} = {total} tokens｜{self.seconds:.1f}s")


@dataclass
class LLM:
    settings: LLMSettings
    usage: Usage = field(default_factory=Usage)

    # ------------------------------------------------------------------ #
    @property
    def configured(self) -> bool:
        return bool(self.settings.api_key)

    def _payload(self, messages: list[dict], *, temperature: float | None,
                 max_tokens: int | None, json_mode: bool) -> dict:
        payload: dict = {
            "model": self.settings.model,
            "messages": messages,
            "temperature": self.settings.temperature if temperature is None else temperature,
            "max_tokens": max_tokens or self.settings.max_tokens,
            "stream": False,
        }
        if json_mode:
            # DeepSeek 与多数 OpenAI 兼容端点都支持；不支持时服务端会忽略或报错，
            # 因此调用方仍需容错解析。
            payload["response_format"] = {"type": "json_object"}
        return payload

    def chat(self, messages: list[dict], *, temperature: float | None = None,
             max_tokens: int | None = None, json_mode: bool = False,
             retries: int = 2) -> str:
        if not self.configured:
            raise LLMNotConfigured(
                "未配置 LLM API key。请在 harness/.env 里写入：\n"
                "  DEEPSEEK_API_KEY=sk-xxxx\n"
                "或运行： python -m harness.cli setup-key"
            )
        url = self.settings.base_url.rstrip("/") + "/chat/completions"
        body = json.dumps(self._payload(messages, temperature=temperature,
                                        max_tokens=max_tokens, json_mode=json_mode)).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.settings.api_key}",
            "Accept": "application/json",
        }

        last_err = ""
        for attempt in range(retries + 1):
            req = urllib.request.Request(url, data=body, headers=headers, method="POST")
            t0 = time.time()
            try:
                with urllib.request.urlopen(req, timeout=self.settings.timeout) as r:
                    data = json.loads(r.read().decode("utf-8", "ignore"))
                secs = time.time() - t0
                choices = data.get("choices") or []
                if not choices:
                    raise LLMError(f"响应没有 choices：{str(data)[:300]}")
                text = (choices[0].get("message") or {}).get("content") or ""
                u = data.get("usage") or {}
                self.usage.add(int(u.get("prompt_tokens") or 0),
                               int(u.get("completion_tokens") or 0), secs)
                return text
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", "ignore")[:400]
                last_err = f"HTTP {e.code}: {detail}"
                if e.code in (400, 401, 403, 404, 422):
                    break                      # 配置/鉴权问题，重试无意义
                time.sleep(1.5 * (attempt + 1))
            except urllib.error.URLError as e:
                last_err = f"网络错误: {e}"
                time.sleep(1.5 * (attempt + 1))
            except LLMError as e:
                last_err = str(e)
                time.sleep(1.0)
            except Exception as e:
                last_err = f"{type(e).__name__}: {e}"
                time.sleep(1.0)
        raise LLMError(f"LLM 调用失败（model={self.settings.model} url={url}）：{last_err}")

    # ------------------------------------------------------------------ #
    def complete(self, prompt: str, *, system: str = "", temperature: float | None = None,
                 max_tokens: int | None = None) -> str:
        msgs = ([{"role": "system", "content": system}] if system else []) + \
               [{"role": "user", "content": prompt}]
        return self.chat(msgs, temperature=temperature, max_tokens=max_tokens)

    def complete_json(self, prompt: str, *, system: str = "", temperature: float | None = 0.0,
                      max_tokens: int | None = None) -> object:
        """要一段 JSON，并尽最大努力解析出来。失败时抛 LLMError。"""
        raw = self.complete(prompt, system=system, temperature=temperature,
                            max_tokens=max_tokens)
        return extract_json(raw)

    def health(self) -> tuple[bool, str]:
        """真实调用一次，用于自检/前端状态灯。"""
        if not self.configured:
            return False, "未配置 API key"
        try:
            out = self.chat(
                [{"role": "user", "content": "只回复两个字：可用"}],
                max_tokens=16, temperature=0.0, retries=0,
            )
            return True, (out or "").strip()[:40]
        except Exception as e:
            return False, str(e)[:300]


def extract_json(raw: str) -> object:
    """从模型输出里抠出 JSON：直接解析 → 剥 ```围栏 → 截取首尾括号。"""
    if raw is None:
        raise LLMError("空响应")
    text = raw.strip()
    if not text:
        raise LLMError("空响应")

    for cand in (text, *(m.group(1).strip() for m in JSON_FENCE_RE.finditer(text))):
        try:
            return json.loads(cand)
        except Exception:
            pass
        for opener, closer in (("{", "}"), ("[", "]")):
            i, j = cand.find(opener), cand.rfind(closer)
            if 0 <= i < j:
                try:
                    return json.loads(cand[i: j + 1])
                except Exception:
                    continue
    raise LLMError(f"无法解析 JSON：{text[:300]}")
