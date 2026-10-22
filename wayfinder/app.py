"""组装根：本项目唯一创建服务、装配路由、启动传输层的地方。

- :func:`build_services`：把 ``Settings`` 交给 :class:`wayfinder.services.Services`；
- :func:`build_application`：把服务交给 ``api.registry`` 生成路由表；
- :func:`run_web`：启动 HTTP 传输层。

这里只做启动装配与启动信息统计，不写业务规则，也不拼 HTML。``main.py`` 只保留入口分发。
"""
from __future__ import annotations

from .api.registry import build_router
from .core.config import SETTINGS, Settings
from .protocol.http import Router
from .server.http import serve
from .services import Services


def build_services(settings: Settings | None = None) -> Services:
    """创建一次运行所需的服务容器；测试可传入自定义 Settings。"""
    return Services(settings or SETTINGS)


def build_application(settings: Settings | None = None) -> tuple[Services, Router]:
    """服务上下文 → (服务, 路由表)。"""
    services = build_services(settings)
    return services, build_router(services)


def run_web(host: str = "127.0.0.1", port: int = 8848,
            open_browser: bool = True, settings: Settings | None = None) -> int:
    """启动 Web 服务（静态前端 + JSON/SSE API）。"""
    services, router = build_application(settings)
    st = services.settings
    try:
        store = services.store()
        try:
            articles = store.count_articles()
        finally:
            store.close()
    except Exception:  # noqa: BLE001 - 库还没建时也能启动
        articles = 0
    print(f"  库文件   : {st.crawl.db_path}（{articles} 篇）")
    print(f"  LLM      : {st.llm.model} "
          f"({'已配置' if st.llm.configured else '未配置'})")
    print(f"  公网搜索 : {st.search.provider}")
    print(f"  接口     : {len(router.paths())} 条")
    return serve(router, host=host, port=port, open_browser=open_browser)
