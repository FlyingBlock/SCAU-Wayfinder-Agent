"""问答 API：一条 `/api/ask` SSE 流。

事件协议（前端只订阅这几个名字）：
  trace         ``{step, data}``：检索步骤的结构化数据
  answer_delta  正文增量
  answer_end    正文说完了（前端收光标）
  answer        最终正文 + 引用来源 + token 用量；dry 模式只带 evidence_count
  cards         活动 / 附件 / 关键时间卡片
  done          本次结束

事件名不能叫 `error`：EventSource 会把它当连接故障。已知错误码走 `answer`
事件的 `code`（empty_question / llm_not_configured / empty_corpus / no_result），
展示文案由前端映射；未知异常才带 `error` 文本。步骤编号与文案属于前端。

编排是同步的（Agent.answer 内部一边检索一边让模型流式输出），而生成器不能从
回调里 yield，所以这里用「工作线程 + 队列」把增量事件转成可迭代的 SSE 流。
"""
from __future__ import annotations

import queue
import threading
from typing import Iterator

from ..protocol.http import Request, Response, sse_response
from ..services import Services

#: 队列里的哨兵：结果对象与结束标记，避免和正常事件名冲突。
_RESULT = "__result__"
_DONE = "__done__"
_ERROR = "__error__"


def ask(req: Request, svc: Services) -> Response:
    question = (req.query.get("q") or "").strip()
    try:
        rounds = int(req.query.get("rounds") or svc.settings.agent_max_rounds)
    except ValueError:
        rounds = svc.settings.agent_max_rounds
    dry = (req.query.get("dry") or "").lower() in ("1", "true", "yes")
    return sse_response(_events(question, rounds, dry, svc))


def _events(question: str, rounds: int, dry: bool, svc: Services) -> Iterator[tuple[str, dict]]:
    if not question:
        yield "answer", {"code": "empty_question", "text": "", "error": "",
                         "citations": []}
        yield "done", {}
        return

    if not svc.settings.llm.configured and not dry:
        yield "answer", {"code": "llm_not_configured", "text": "",
                         "citations": [], "error": ""}
        yield "done", {}
        return

    store = svc.store()
    try:
        if store.count_articles() == 0:
            yield "answer", {"code": "empty_corpus", "text": "",
                             "citations": [], "error": ""}
            yield "done", {}
            return

        agent = svc.agent(store)
        llm = agent.llm
        q: queue.Queue = queue.Queue()

        def trace(step: str, data: dict) -> None:
            q.put(("trace", {"step": step, "data": data}))

        def delta(piece: str, final: bool = False) -> None:
            if piece:
                q.put(("answer_delta", {"text": piece}))
            if final:
                q.put(("answer_end", {}))

        def worker() -> None:
            try:
                q.put((_RESULT, agent.answer(
                    question, max_rounds=rounds, trace=trace,
                    dry_run=dry, on_delta=delta)))
            except BaseException as e:  # noqa: BLE001 - 交给生成器翻译
                q.put((_ERROR, e))
            finally:
                q.put((_DONE, None))

        threading.Thread(target=worker, daemon=True, name="ask-worker").start()

        result = None
        while True:
            kind, payload = q.get()
            if kind == _DONE:
                break
            if kind == _RESULT:
                result = payload
                continue
            if kind == _ERROR:
                raise payload
            yield kind, payload

        if result is None:
            yield "answer", {"code": "no_result", "text": "", "error": "",
                             "citations": []}
        elif dry:
            yield "answer", {
                "text": "",
                "dry": True,
                "evidence_count": len(result.evidence),
                "prompt_chars": len(result.prompt),
                "error": "",
                "citations": result.citations,
            }
        else:
            yield "answer", {
                "text": result.text,
                "error": result.error,
                "citations": result.citations,
                "usage": llm.usage.line(),
            }
        if result is not None and result.cards:
            yield "cards", result.cards
    except (BrokenPipeError, ConnectionResetError):
        raise
    except Exception as e:  # noqa: BLE001 - 流里报错要能看懂
        yield "answer", {"code": "unexpected_error", "text": "",
                         "error": f"{type(e).__name__}: {e}",
                         "citations": []}
    finally:
        store.close()
        yield "done", {}
