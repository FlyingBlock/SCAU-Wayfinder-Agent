"""设置写入命令（与 Web 设置面板复用 settings.commands）。"""
from __future__ import annotations

import argparse

import getpass

from ..core.config import ENV_FILE


def cmd_setup_key(args: argparse.Namespace) -> int:
    """CLI 版本走与 Web 相同的 settings.commands 用例。"""
    from ..app import build_services
    from ..settings import commands

    print("配置 LLM API key（写入 %s，该文件已在 .gitignore 中）" % ENV_FILE)
    print("申请地址：https://platform.deepseek.com/api_keys")
    print("（也可以启动 Web 后在设置面板填写，效果一样）\n")
    if args.key:
        key = args.key.strip()
    else:
        key = getpass.getpass("粘贴 API key（输入不回显）: ").strip()
    if not key:
        print("未输入 key，已取消")
        return 1
    if not key.startswith("sk-"):
        print(f"提示：key 通常以 sk- 开头，你输入的是 {key[:6]}…，仍会保存。")

    base = args.base_url or "https://api.deepseek.com"
    model = args.model or "deepseek-chat"
    print(f"\n正在用 {model} @ {base} 做一次真实调用验证…")
    body, status = commands.save_llm({
        "api_key": key, "base_url": base, "model": model,
        "verify": True, "persist": True,
    }, build_services(), local=True)
    if status != 200:
        print("❌ " + str(body.get("error") or "保存失败"))
        print("   未写入 .env。请检查 key / 网络 / 模型名后重试。")
        return 2
    if body.get("warning"):
        print("⚠️ " + body["warning"])
    print(f"\n{body.get('message') or '已保存'}")
    print(f"配置：{body.get('base_url')} / {body.get('model')}")
    print("现在可以运行： python -m wayfinder ask \"生物专业可以参加什么竞赛？\"")
    return 0
