"""架构边界自测：依赖方向、组装根与前后端职责。

跑法：
    python tests/test_architecture.py

这些检查不验业务数值，只防止重构后边界重新腐化：
  · API 不 import 全局 SETTINGS；
  · main.py 只做入口分发；
  · calc 只读本地数据，不 import crawl / 网络模块；
  · server 不 import api；
  · 前端业务计算与 localStorage 只在 calc/state 一处；
  · app.build_services 会使用传入的 Settings。
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Windows 默认控制台是 GBK；架构测试自己也会打印 ✓/✗，先放宽错误策略。
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(errors="replace")           # type: ignore[union-attr]
    except (AttributeError, OSError, ValueError):
        pass

from wayfinder.app import build_services          # noqa: E402
from wayfinder.calc import Calculator             # noqa: E402
from wayfinder.core.config import SETTINGS, Settings  # noqa: E402

FAILURES: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(("  ✓ " if cond else "  ✗ ") + msg)
    if not cond:
        FAILURES.append(msg)


def module_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            out.add(node.module or "")
        elif isinstance(node, ast.Import):
            out.update(alias.name for alias in node.names)
    return out


def sources(sub: str) -> list[Path]:
    return sorted((ROOT / "wayfinder" / sub).rglob("*.py"))


def test_api_has_no_global_settings() -> None:
    print("\n[API] 协议层只依赖 Services")
    for path in sources("api"):
        text = path.read_text(encoding="utf-8")
        check("SETTINGS" not in text,
              f"{path.relative_to(ROOT)} 不 import/读取全局 SETTINGS")


def test_main_is_thin() -> None:
    print("\n[入口] main.py / cli.py 只分发")
    text = (ROOT / "wayfinder" / "main.py").read_text(encoding="utf-8")
    for forbidden in ("from .calc", "from .qa", "from .corpus",
                      "from .server", "from .api"):
        check(forbidden not in text, f"main.py 不直接装配 {forbidden}")

    cli = (ROOT / "wayfinder" / "cli.py").read_text(encoding="utf-8")
    for forbidden in ("from .calc", "from .qa", "from .corpus",
                      "from .documents", "from .crawl"):
        check(forbidden not in cli, f"cli.py 不直接装配 {forbidden}")
    check(len(cli.splitlines()) < 300, "cli.py 只保留 parser/分发（< 300 行）")
    for name in ("common", "chat", "crawl", "documents", "calc", "settings", "doctor"):
        check((ROOT / "wayfinder" / "commands" / f"{name}.py").is_file(),
              f"命令模块 commands/{name}.py 存在")


def test_transport_direction() -> None:
    print("\n[依赖] api / server 只共享 protocol，不互相依赖")
    for path in sources("api"):
        text = path.read_text(encoding="utf-8")
        check("from ..server" not in text and "import ..server" not in text,
              f"{path.relative_to(ROOT)} 不 import server")
    for path in sources("server"):
        text = path.read_text(encoding="utf-8")
        check("from ..api" not in text and "import ..api" not in text,
              f"{path.relative_to(ROOT)} 不 import api")


def test_documents_stay_one_way() -> None:
    print("\n[领域] documents 不反向依赖 crawl")
    for path in sources("documents"):
        text = path.read_text(encoding="utf-8")
        check("from ..crawl" not in text and "import ..crawl" not in text,
              f"{path.relative_to(ROOT)} 不 import crawl")


def test_settings_are_injected() -> None:
    print("\n[配置] OCR / 登录配置进入 Settings，模块别名指向同一对象")
    from wayfinder.crawl import auth as auth_mod
    from wayfinder.documents import ocr as ocr_mod

    check(hasattr(SETTINGS, "ocr") and hasattr(SETTINGS, "auth"),
          "Settings 提供 ocr / auth 配置")
    check(ocr_mod.SETTINGS is SETTINGS.ocr,
          "documents.ocr.SETTINGS 与 Settings.ocr 是同一对象")
    check(auth_mod.SETTINGS is SETTINGS.auth,
          "crawl.auth.SETTINGS 与 Settings.auth 是同一对象")
    services = build_services(Settings())
    check(hasattr(services, "attachment_dir"), "Services 暴露附件目录")
    check(hasattr(services, "refresh_competitions"), "Services 暴露赛事刷新用例")


def test_calc_is_pure() -> None:
    print("\n[calc] 纯计算域不联网")
    for path in sources("calc"):
        text = path.read_text(encoding="utf-8")
        for forbidden in ("from ..crawl", "import urllib", "import http",
                          "import socket", "from ..integrations"):
            check(forbidden not in text,
                  f"{path.relative_to(ROOT)} 不含 {forbidden}")


def test_server_does_not_import_api() -> None:
    print("\n[server] 传输层不认识协议层")
    for path in sources("server"):
        text = path.read_text(encoding="utf-8")
        check("from ..api" not in text and "import ..api" not in text,
              f"{path.relative_to(ROOT)} 不 import api")


def test_frontend_ownership() -> None:
    print("\n[前端] 计算与存储只在 calc/state")
    calc = (ROOT / "frontend/js/features/calc/index.js").read_text(encoding="utf-8")
    activities = (ROOT / "frontend/js/features/calc/activities.js").read_text(encoding="utf-8")
    chat = (ROOT / "frontend/js/features/chat/index.js").read_text(encoding="utf-8")
    state = (ROOT / "frontend/js/features/calc/state.js").read_text(encoding="utf-8")
    main = (ROOT / "frontend/js/main.js").read_text(encoding="utf-8")
    check("localStorage" not in calc, "calc/index.js 不直接读写 localStorage")
    check("scau-calc-state-v1" not in chat, "chat 不碰计算器存储格式")
    check("scau-calc-state-v1" in state and "localStorage" in state,
          "calc/state.js 是唯一存储入口")
    for old in ("function gpOf", "RUBRIC_BY_CHANNEL", "UNIT_BY_CHANNEL",
                "fillDemo"):
        check(old not in calc, f"前端不再计算 {old}")
    check("effective_gp" in calc, "绩点列使用后端 effective_gp")
    check("act.best" in activities, "活动卡使用后端 best")
    check("fetch(" not in main and "api/" not in main,
          "main.js 不直接调接口")


def test_composition_root() -> None:
    print("\n[组装] build_services 使用传入配置")
    settings = Settings()
    services = build_services(settings)
    check(services.settings is settings, "Services.settings 就是传入的 Settings")
    check(services.store.__self__ is services, "store() 是容器方法")


def test_catalog_contract() -> None:
    print("\n[契约] 后端把前端需要的最终数据一次给出")
    cat = Calculator().catalog()
    check("channel_rubric" in cat and "channel_units" in cat,
          "catalog 提供通道评分表与单位")
    activities = cat.get("activities") or []
    check(bool(activities) and all("best" in a for a in activities),
          "每个活动都带 best_preview 结果")
    major = (cat.get("majors") or [{}])[0]
    course = next((c for c in major.get("courses", [])
                   if c.get("counts_toward_gpa")), None)
    check(course is not None, "培养方案里有计绩点课程")
    result = Calculator().evaluate_dict({
        "profile": {"major_id": major.get("id"), "scores": {course["code"]: 80},
                    "retakes": [course["code"]]},
        "basket": [],
    }).as_dict()
    row = next(r for r in result["gpa"]["courses"] if r["code"] == course["code"])
    check(row["effective_gp"] == 1.0 and row["gp"] == 3.0,
          "重修课同时返回原始绩点与封顶后的 effective_gp")


def main() -> int:
    print("=" * 74)
    print("架构边界自测")
    print("=" * 74)
    test_api_has_no_global_settings()
    test_main_is_thin()
    test_transport_direction()
    test_documents_stay_one_way()
    test_settings_are_injected()
    test_calc_is_pure()
    test_server_does_not_import_api()
    test_frontend_ownership()
    test_composition_root()
    test_catalog_contract()
    print("\n" + "=" * 74)
    if FAILURES:
        print(f"❌ {len(FAILURES)} 项未通过")
        return 1
    print("✅ 全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
