"""SCAU Wayfinder：校内公开信息检索与学业规划助手。

分层：core（配置/纯工具）→ crawl / corpus / documents / qa / calc / settings（领域能力）
→ api（协议适配）→ protocol（请求/响应原语）；server 只做传输。app.py 是唯一组装根，
main.py / cli.py 只做入口分发，命令实现在 commands/。
"""

__version__ = "0.2.0"
