"""流式生成的单元测试：不联网、不花 token，用一个假的 OpenAI 兼容端点验证。

跑法：
    python tests/test_stream.py

为什么值得单独有这一条：流式这条路有两个「只在真实调用里才会翻车」的坑，
`node --check` 与页面自测都覆盖不到：

1. **缓冲语义**：思维链模型（deepseek-reasoner 这类）会先把 max_tokens 花在
   `reasoning_content` 上，轮到正文时预算已经用完 —— 这时必须先攒着再决定发不发。
   如果边收边发，用户就会先看到一段作废的正文，然后被重来一遍覆盖掉。
2. **退路**：端点不支持 `stream: true` 时（有些自建网关直接回 400），
   必须自动退回非流式，而不是把页面的「正在生成」永远挂在那里。

这里用一个进程内的 http.server 假装成 OpenAI 端点，把上面两条都跑一遍。
"""
from __future__ import annotations

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(errors="replace")           # type: ignore[union-attr]
    except (AttributeError, OSError, ValueError):
        pass

from wayfinder.qa.agent import Agent, Evidence          # noqa: E402
from wayfinder.core.config import LLMSettings            # noqa: E402
from wayfinder.qa.llm import LLM, LLMError              # noqa: E402

FAILURES: list[str] = []
#: 端点行为由这个开关决定：done = 正常流；length = 思维链吃光预算；nostream = 不支持流
MODE = {"value": "done"}


class FakeEndpoint(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):                            # 安静点
        pass

    def do_POST(self):                                    # noqa: N802
        length = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        if not body.get("stream"):
            self._json(self._nonstream_reply())
            return
        if MODE["value"] == "nostream":
            self._json({"error": {"message": "stream is not supported"}}, code=400)
            return
        self._stream()

    # ------------------------------------------------------------------ #
    def _nonstream_reply(self) -> dict:
        text = "非流式正文：这是退路生成的内容。"
        return {"choices": [{"message": {"content": text},
                             "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 11, "completion_tokens": 22}}

    def _json(self, obj, code: int = 200) -> None:
        data = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _stream(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()

        def frame(obj) -> None:
            self.wfile.write(f"data: {json.dumps(obj)}\n\n".encode("utf-8"))
            self.wfile.flush()

        if MODE["value"] == "length":
            # 思维链模型：思考占满预算，正文只吐了半句就被截断
            frame({"choices": [{"delta": {"reasoning_content": "让我想想…"}}]})
            frame({"choices": [{"delta": {"content": "半句正文"}}]})
            frame({"choices": [{"delta": {}, "finish_reason": "length"}]})
        elif MODE["value"] == "plain":
            # 普通对话模型：没有 reasoning_content，正文边生成边下发
            for piece in ("## 结论\n", "推免要求 GPA ≥ 3.20 [1]。\n", "\n末段。"):
                frame({"choices": [{"delta": {"content": piece}}]})
            frame({"choices": [{"delta": {}, "finish_reason": "stop"}]})
        else:
            frame({"choices": [{"delta": {"reasoning_content": "内部草稿不该显示"}}]})
            for piece in ("## 结论\n", "推免要求 GPA ≥ 3.20 [1]。\n", "\n末段。"):
                frame({"choices": [{"delta": {"content": piece}}]})
            frame({"choices": [{"delta": {}, "finish_reason": "stop"}],
                   "usage": {"prompt_tokens": 100, "completion_tokens": 20}})
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()


def check(cond: bool, msg: str) -> None:
    print(("  ✓ " if cond else "  ✗ ") + msg)
    if not cond:
        FAILURES.append(msg)


def start_server() -> tuple[ThreadingHTTPServer, str]:
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), FakeEndpoint)
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}"


def make_llm(base: str) -> LLM:
    return LLM(LLMSettings(api_key="sk-test", base_url=base, model="fake-model",
                           max_tokens=64, timeout=20))


def make_agent(llm: LLM) -> Agent:
    """只测「生成」这一段：store 传 None —— 流式生成不会碰它。"""
    return Agent(None, llm, None, type("S", (), {"llm": llm.settings})())


EVIDENCE = [Evidence(n=1, title="推免办法", url="https://x.scau.edu.cn/a.htm",
                     pub_date="2025-09-01", snippet="推免要求 GPA 3.20", source="site",
                     college="生科院")]


def collect(agent: Agent, llm: LLM) -> list[tuple[str, bool]]:
    calls: list[tuple[str, bool]] = []
    agent._generate_stream("推免要什么材料？", EVIDENCE,
                           lambda p, f=False: calls.append((p, f)))
    return calls


def test_stream_ok(base: str) -> None:
    print("\n[流式] 正常流：增量按序下发，思考过程不外泄")
    MODE["value"] = "done"
    llm = make_llm(base)
    calls = collect(make_agent(llm), llm)
    text = "".join(p for p, f in calls)
    check(len(calls) >= 3, f"正文分 {len(calls)} 次下发（>1 才算流式）")
    check(calls[-1] == ("", True), "最后一次是空片段 + final=True（前端据此收光标）")
    check(text.startswith("## 结论") and "GPA ≥ 3.20 [1]" in text,
          f"完整正文拼接正确：{text[:40]!r}…")
    check("内部草稿" not in text, "reasoning_content（思考过程）没有混进正文")
    check(not any(p and f for p, f in calls[:-1]), "只有最后一次带 final 标记")
    check(llm.usage.completion_tokens == 20,
          f"流式帧里的 usage 已计入（completion={llm.usage.completion_tokens}）")


def test_plain_model_is_live(base: str) -> None:
    print("\n[流式] 非思维链模型：不攒缓冲，来一段发一段（首字最快）")
    MODE["value"] = "plain"
    llm = make_llm(base)
    seen: list[str] = []

    def on_delta(piece: str, final: bool = False) -> None:
        seen.append(piece)
        if not final:                     # 拿到的第一段就应该已经有正文
            seen.append("<live>")

    agent = make_agent(llm)
    agent._generate_stream("推免要什么材料？", EVIDENCE, on_delta)
    # 第一段之后立刻标记：说明不是「全部收完才一次性吐出来」
    check(seen[1] == "<live>", "第一段正文是边收边发的（不是整段攒完再发）")
    check("".join(p for p in seen if p != "<live>").startswith("## 结论"),
          "拼起来仍然是完整正文")


def test_truncated_retries(base: str) -> None:
    print("\n[流式] 被截断：作废的增量一个都不发，改走非流式重来")
    MODE["value"] = "length"
    llm = make_llm(base)
    calls = collect(make_agent(llm), llm)
    text = "".join(p for p, f in calls)
    check(all(p != "半句正文" for p, _ in calls),
          "被截断的那半句没有下发（否则用户会先看到一段作废正文）")
    check(len(calls) == 1 and calls[0][1] is True,
          "退路：整段正文一次性下发 + final")
    check(text.startswith("非流式正文"), f"用的是非流式那条路：{text[:30]!r}")


def test_nostream_fallback(base: str) -> None:
    print("\n[流式] 端点不支持 stream：自动退回非流式，不把页面挂死")
    MODE["value"] = "nostream"
    llm = make_llm(base)
    calls = collect(make_agent(llm), llm)
    text = "".join(p for p, f in calls)
    check(text.startswith("非流式正文"), "拿到的是非流式生成的正文")
    check(calls[-1][1] is True, "仍然给出 final 标记，前端不会一直转圈")


def test_stream_chat_raises(base: str) -> None:
    print("\n[流式] stream_chat 自身不重试：出错就抛给调用方")
    MODE["value"] = "nostream"
    llm = make_llm(base)
    try:
        list(llm.stream_chat([{"role": "user", "content": "x"}]))
        check(False, "端点回 400 时应当抛 LLMError")
    except LLMError as e:
        check("400" in str(e), f"抛的是 LLMError 且带上状态码：{str(e)[:60]}")
    except Exception as e:                                # noqa: BLE001
        check(False, f"抛的是 {type(e).__name__}，应当是 LLMError：{e}")


def main() -> int:
    print("=" * 74)
    print("流式生成自测（假 OpenAI 端点，不联网、不花 token）")
    print("=" * 74)
    httpd, base = start_server()
    try:
        test_stream_ok(base)
        test_plain_model_is_live(base)
        test_truncated_retries(base)
        test_nostream_fallback(base)
        test_stream_chat_raises(base)
    finally:
        httpd.shutdown()
        httpd.server_close()
    print("\n" + "=" * 74)
    if FAILURES:
        print(f"❌ {len(FAILURES)} 项未通过")
        return 1
    print("✅ 全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
