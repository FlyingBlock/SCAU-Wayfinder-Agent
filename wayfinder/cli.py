"""命令行入口：只建 parser、分发命令；业务命令在 ``wayfinder.commands``。

各功能命令不再堆在本文件；领域依赖由命令模块或 ``Services`` 提供。
"""
from __future__ import annotations

import argparse
import sys

from .commands.calc import (
    cmd_activities,
    cmd_calc,
    cmd_competitions_refresh,
    cmd_gpa,
    cmd_goals,
)
from .commands.chat import cmd_ask, cmd_search, cmd_web
from .commands.crawl import cmd_crawl, cmd_fetch, cmd_login, cmd_whoami
from .commands.doctor import cmd_doctor
from .commands.documents import cmd_attach, cmd_attachments, cmd_ocr, cmd_parse
from .commands.settings import cmd_setup_key
from .core.config import SETTINGS


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="wayfinder", description="SCAU Wayfinder：校内公开信息检索与学业规划",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("setup-key", help="交互式配置 LLM key / 端点 / 模型（写入仓库根 .env）")
    p.add_argument("--key", help="直接传入 key（不回显输入时用）")
    p.add_argument("--base-url", help="OpenAI 兼容端点，默认 https://api.deepseek.com")
    p.add_argument("--model", help="模型名，默认 deepseek-chat")
    p.set_defaults(func=cmd_setup_key)

    p = sub.add_parser("doctor", help="自检环境/种子/数据库/LLM 连通性")
    p.add_argument("--no-llm", action="store_true", help="跳过 LLM 连通性测试")
    p.add_argument("--test-web", action="store_true", help="实测公网搜索")
    p.add_argument("--test-ocr", action="store_true", help="实测 OCR（会真的调一次接口）")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("crawl", help="按范围抓取 SCAU 栏目群")
    p.add_argument("--scope", default="narrow", choices=["narrow", "p1", "p2", "all"])
    p.add_argument("--url", action="append", help="额外指定栏目列表页（可多次）")
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--max-pages", type=int, default=0)
    p.add_argument("--max-articles", type=int, default=0)
    p.add_argument("--concurrency", type=int, default=0)
    p.add_argument("--no-robots", action="store_true")
    p.add_argument("--no-auth", action="store_true",
                   help="忽略 .auth/ 里的会话，按未登录状态抓（登录墙栏目仍会跳过）")
    p.add_argument("--no-auto-login", action="store_true",
                   help="撞到登录墙时不自动登录（默认会用已保存的账号自动登录，验证码走 OCR）")
    p.add_argument("--no-attachments", action="store_true",
                   help="不下载/解析附件（默认会抓，附件正文进检索）")
    p.add_argument("--reset", action="store_true")
    p.set_defaults(func=cmd_crawl)

    # ---------------- 登录墙（统一身份认证） ---------------- #
    p = sub.add_parser("login", help="登录统一身份认证（或导入浏览器 Cookie），存到 .auth/")
    p.add_argument("--user", help="学号/工号（不给就交互输入；不写进 shell 历史）")
    p.add_argument("--password", help="密码（不建议写在命令行；默认交互输入不回显）")
    p.add_argument("--cookie", nargs="?", const="-", metavar="COOKIE",
                   help="不用密码：直接导入浏览器复制的一整行 Cookie（不带值时交互粘贴）")
    p.add_argument("--domain", default="cas.scau.edu.cn",
                   help="--cookie 导入时归属的域，默认 cas.scau.edu.cn")
    p.add_argument("--service", default=None,
                   help="登录后跳转的目标地址，默认融合门户 http://portal.scau.edu.cn/")
    p.add_argument("--no-save", action="store_true", help="不把账号密码写进 .auth/credentials.json")
    p.add_argument("--no-captcha", action="store_true",
                   help="不尝试 OCR 识别验证码（遇到验证码直接报错，方便对照排查）")
    p.add_argument("--forget", action="store_true", help="清除已保存的会话与凭据")
    p.set_defaults(func=cmd_login)

    p = sub.add_parser("whoami", help="看当前会话状态（cookie 数 / 能否进某个页面）")
    p.add_argument("url", nargs="?", default="", help="顺便试着访问这个 URL")
    p.add_argument("-v", "--verbose", action="store_true", help="列出每个 cookie")
    p.set_defaults(func=cmd_whoami)

    p = sub.add_parser("fetch", help="带会话抓一个 URL（排查登录墙 / 取单页内容）")
    p.add_argument("url")
    p.add_argument("--save", help="把正文写到文件")
    p.add_argument("--html", action="store_true", help="输出原始 HTML 而不是正文摘要")
    p.add_argument("--limit", type=int, default=0, help="正文摘要长度上限")
    p.add_argument("--no-auth", action="store_true", help="不带会话请求（对照组）")
    p.add_argument("--no-robots", action="store_true")
    p.set_defaults(func=cmd_fetch)

    p = sub.add_parser("search", help="只在已抓语料里做全文检索（不调用 LLM）")
    p.add_argument("query")
    p.add_argument("--top-k", type=int, default=10)
    p.add_argument("--topic", default="")
    p.add_argument("--since", default="", help="ISO 日期，只返回此日期之后发布的")
    p.add_argument("--no-bio", action="store_true", help="不做生物相关学院加权")
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("ask", help="提问（多轮检索 + 带引用生成）")
    p.add_argument("question")
    p.add_argument("--rounds", type=int, default=None, help="缺口补检索轮数，默认取配置")
    p.add_argument("--quiet", action="store_true", help="不打印中间过程")
    p.add_argument("--json", help="把完整结果写到指定 JSON 文件")
    p.add_argument("--dry-run", action="store_true",
                   help="不调用 LLM，只跑检索并打印证据与最终 Prompt（省 token 排错用）")
    p.add_argument("--show-prompt", action="store_true", help="--dry-run 时打印完整 Prompt")
    p.set_defaults(func=cmd_ask)

    p = sub.add_parser("web", help="启动 Web 界面")
    p.add_argument("--host", default=SETTINGS.host)
    p.add_argument("--port", type=int, default=SETTINGS.port)
    p.add_argument("--no-open", action="store_true", help="不自动打开浏览器")
    p.set_defaults(func=cmd_web)

    # ---------------- 计算器（绩点 / 德育 / 综测） ---------------- #
    def _add_calc_inputs(sp):
        sp.add_argument("--major", choices=["biotech", "bioscience"],
                        default="biotech", help="专业：biotech=生物技术，bioscience=生物科学")
        sp.add_argument("--scores", help="成绩 JSON 文件：{\"课程代码\": 分数}")
        sp.add_argument("--score", action="append", metavar="代码=分数",
                        help="单门成绩，可重复；也支持五级制，如 --score G1201=优秀")
        sp.add_argument("--metric", action="append", metavar="指标=数值",
                        help="其他指标，如 --metric cet4_score=452 --metric pe_pass=1")
        sp.add_argument("--cohort", type=int, default=0, help="专业总人数（算排名百分位用）")
        sp.add_argument("--rank", type=int, default=0, help="我的名次")
        sp.add_argument("--activity", action="append", metavar="活动ID[:名次][x份数]",
                        help="加入活动篮，如 --activity biosci-competition:三等奖 "
                             "--activity volunteer-service:参与x3")

    p = sub.add_parser("gpa", help="算平均学分绩点（可带活动篮）")
    _add_calc_inputs(p)
    p.add_argument("-v", "--verbose", action="store_true", help="打印逐门课程明细")
    p.add_argument("--all", action="store_true", help="连同未出成绩的课一起打印")
    p.set_defaults(func=cmd_gpa)

    p = sub.add_parser("goals", help="对照保研/考研/奖学金门槛，并给出课程目标分")
    _add_calc_inputs(p)
    p.add_argument("-v", "--verbose", action="store_true",
                   help="打印每条门槛的说明、出处，以及逐门课程的目标分")
    p.add_argument("--all", action="store_true", help="连已达标项也打印")
    p.set_defaults(func=cmd_goals)

    p = sub.add_parser("activities", help="列出全部可加分活动与加分依据")
    p.add_argument("--category", default="", help="只看某个类别")
    p.add_argument("--level", default="", help="只看某个级别")
    p.add_argument("--scored-only", action="store_true", help="只看有分值依据的")
    p.add_argument("--list", choices=["competition", "general", "all"], default="all",
                   help="清单范围：competition=《学生竞赛奖励办法》名录里的具体赛事，"
                        "general=通用加分项，all=全部（默认）")
    p.add_argument("--refresh", action="store_true",
                   help="先联网刷新赛事名录（抓官网 → 与内置数据对账）再打印")
    p.add_argument("--timeout", type=int, default=12, help="联网刷新的单页超时秒数")
    p.set_defaults(func=cmd_activities)

    p = sub.add_parser("competitions",
                       help="刷新《学生竞赛奖励办法》赛事名录（联网抓官网并和内置数据对账）")
    p.add_argument("--timeout", type=int, default=12, help="单页超时秒数")
    p.set_defaults(func=cmd_competitions_refresh)

    p = sub.add_parser("calc", help="计算器数据自检：专业/课程/门槛/活动/口径")
    p.set_defaults(func=cmd_calc)

    # ---------------- 附件 / 文档解析 / OCR ---------------- #
    p = sub.add_parser("parse", help="解析本地文件（docx/xlsx/pdf/doc/xls/图片/压缩包…）并打印文本")
    p.add_argument("path", nargs="+", help="一个或多个文件路径")
    p.add_argument("--chars", type=int, default=1200, help="每个文件打印多少字符（默认 1200）")
    p.add_argument("--full", action="store_true", help="打印全部正文（可能很长）")
    p.add_argument("--no-ocr", action="store_true", help="跳过图片 OCR")
    p.add_argument("--save", help="把解析结果写到这个目录（每个文件一个 .txt）")
    p.add_argument("-q", "--quiet", action="store_true", help="只打印摘要行")
    p.set_defaults(func=cmd_parse)

    p = sub.add_parser("attach", help="下载并解析库内通知的附件（存到 data/attachments/）")
    p.add_argument("--limit", type=int, default=10, help="最多处理几篇通知（默认 10）")
    p.add_argument("--article", type=int, default=0, help="只处理这一篇文章的附件")
    p.add_argument("--all", action="store_true", help="连已经解析过的也重跑")
    p.add_argument("--force", action="store_true", help="忽略缓存，重新下载")
    p.add_argument("--no-ocr", action="store_true", help="本次不调用 OCR（图片里文字不提取）")
    p.add_argument("--max-files", type=int, default=0, help="覆盖单篇通知的附件数上限")
    p.set_defaults(func=cmd_attach)

    p = sub.add_parser("attachments", help="列出已下载的附件及其解析状态")
    p.add_argument("--article", type=int, default=0, help="只看某篇文章的附件")
    p.add_argument("--limit", type=int, default=40)
    p.add_argument("--search", default="", help="在附件正文里搜关键词")
    p.set_defaults(func=cmd_attachments)

    p = sub.add_parser("ocr", help="配置 / 测试 OCR（百度智能云），图片与扫描件靠它提字")
    p.add_argument("--api-key", help="百度 OCR 应用的 API Key")
    p.add_argument("--secret-key", help="百度 OCR 应用的 Secret Key")
    p.add_argument("--provider", choices=["baidu", "none"], help="OCR 服务商（none=关闭）")
    p.add_argument("--standard", action="store_true", help="用标准版（默认高精度版）")
    p.add_argument("--test", action="store_true", help="用一张测试图真实调一次接口")
    p.add_argument("--image", help="直接对这张图片做一次识别（验证效果）")
    p.add_argument("--clear", action="store_true", help="清除已保存的 OCR 凭据")
    p.add_argument("--no-verify", action="store_true", help="保存前不做真实调用验证")
    p.set_defaults(func=cmd_ocr)

    return ap


def _use_safe_console() -> None:
    """避免 Windows 本地控制台（cp936/GBK）因 ✓ ✗ 之类字符直接崩溃。

    只放宽编码错误策略，不强行改成 UTF-8：中文在 GBK 控制台上仍能正常显示，
    无法编码的符号退化成 '?'，而不是抛 UnicodeEncodeError 中断整个命令。
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")  # type: ignore[union-attr]
        except (AttributeError, OSError, ValueError):
            pass


def main(argv: list[str] | None = None) -> int:
    _use_safe_console()
    ap = build_parser()
    args = ap.parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except KeyboardInterrupt:
        print("\n已中断", file=sys.stderr)
        return 130
