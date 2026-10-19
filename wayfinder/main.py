"""入口分发：主程序只决定「交给 CLI 还是交给组装根」。

真正的依赖创建、路由装配与 Web 启动在 :mod:`wayfinder.app`；
业务命令在 :mod:`wayfinder.cli`。这里刻意不 import 领域模块。
"""
from __future__ import annotations

import sys


def run_web(host: str = "127.0.0.1", port: int = 8848,
            open_browser: bool = True) -> int:
    """兼容旧入口：转发到组装根。"""
    from .app import run_web as _run_web

    return _run_web(host=host, port=port, open_browser=open_browser)


def main(argv: list[str] | None = None) -> int:
    """命令分发。业务命令全部在 `cli.py`，这里只做入口。"""
    from .cli import main as cli_main

    return cli_main(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
