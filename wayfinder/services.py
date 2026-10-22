"""进程级服务容器：只负责按配置提供领域依赖。

由 :func:`wayfinder.app.build_services` 构造，API 层通过它取得 Store、
Calculator、Searcher、LLM、Agent、附件目录与赛事刷新用例，而不是各自
import 全局 ``SETTINGS``。OCR/登录配置在 ``Settings.ocr`` / ``Settings.auth``。

Store 仍然按请求创建：SQLite 连接不能跨线程共享，且采集写入后下一次请求
应立即看到新数据。其余对象默认是轻量工厂，测试可以替换成假实现。
"""
from __future__ import annotations

from typing import Callable

from .calc import Calculator
from .core.config import LLMSettings, Settings
from .corpus.store import Store
from .qa.agent import Agent
from .qa.llm import LLM
from .qa.websearch import WebSearcher

StoreFactory = Callable[[], Store]
CalculatorFactory = Callable[[], Calculator]
SearcherFactory = Callable[[], WebSearcher]
LLMFactory = Callable[[LLMSettings | None], LLM]
AgentFactory = Callable[[Store], Agent]


class Services:
    """一次进程运行所需的全部依赖入口。

    ``settings`` 是唯一配置源；API 层不应再 import ``core.config.SETTINGS``。
    工厂参数用于测试或多实例部署，默认工厂只依赖传入的 ``settings``。
    """

    def __init__(
        self,
        settings: Settings,
        *,
        store_factory: StoreFactory | None = None,
        calculator_factory: CalculatorFactory | None = None,
        searcher_factory: SearcherFactory | None = None,
        llm_factory: LLMFactory | None = None,
        agent_factory: AgentFactory | None = None,
    ) -> None:
        self.settings = settings
        self._store_factory = store_factory or (lambda: Store(settings.crawl.db_path))
        self._calculator_factory = calculator_factory or Calculator
        self._searcher_factory = searcher_factory or (
            lambda: WebSearcher(settings.search)
        )
        self._llm_factory = llm_factory or (
            lambda override=None: LLM(override or settings.llm)
        )
        self._agent_factory = agent_factory

    def store(self) -> Store:
        """每个请求新建连接：SQLite 连接不跨线程共享。"""
        return self._store_factory()

    def calculator(self) -> Calculator:
        """计算器构造很便宜（只读 JSON），改数据后下一次请求即生效。"""
        return self._calculator_factory()

    def searcher(self) -> WebSearcher:
        return self._searcher_factory()

    def llm_client(self, settings: LLMSettings | None = None) -> LLM:
        """LLM 客户端。可传入临时配置用于「测试连接」，不影响当前设置。"""
        return self._llm_factory(settings)

    def llm(self) -> LLM:
        return self.llm_client()

    def agent(self, store: Store) -> Agent:
        if self._agent_factory is not None:
            return self._agent_factory(store)
        return Agent(store, self.llm(), self.searcher(), self.settings)

    def attachment_dir(self):
        """附件落盘目录；API 只通过容器取路径，不直接 import documents。"""
        from .documents.attachments import ATTACH_DIR

        return ATTACH_DIR

    def refresh_competitions(self, *, timeout: int = 12) -> dict:
        """联网刷新赛事名录，并让问答卡片缓存失效。"""
        from .integrations import competitions

        res = competitions.refresh(timeout=timeout)
        from .qa import cards

        cards.reset_cache()
        return res
