"""配置与密钥加载。

密钥优先级：真实环境变量 > harness/.env > 工作区根 .env。
这样既能在沙箱内跑，也能把 key 留在不入库的 .env 里。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# harness/ 目录（本文件位于 harness/harness/config.py）
PKG_DIR = Path(__file__).resolve().parent
ROOT = PKG_DIR.parent                 # 仓库根：...\harness
WORKSPACE = ROOT.parent               # 仓库的上级目录（旧布局里的 ...\SCAU，clone 后可能不存在）


def _first_existing(*candidates: Path) -> Path:
    """按顺序返回第一个存在的文件；都不存在时返回最后一个（便于报错与首次创建）。

    这样同一份代码既能在「仓库根 = harness/」的 clone 里跑（种子在 seed/），
    也能在旧的「工作区 + harness/ 子目录」布局里跑（种子在仓库上一级）。
    """
    for path in candidates:
        if path.is_file():
            return path
    return candidates[-1]


def _load_dotenv(path: Path) -> None:
    """极简 .env 解析，不覆盖已存在的真实环境变量。"""
    if not path.is_file():
        return
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError:
        return
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


# 先加载工作区根，再加载 harness/（后者优先，但都不覆盖已有变量）
_load_dotenv(WORKSPACE / ".env")
_load_dotenv(ROOT / ".env")


def getenv(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


@dataclass
class LLMSettings:
    api_key: str = ""
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    temperature: float = 0.0
    max_tokens: int = 4096
    timeout: int = 180

    @classmethod
    def from_env(cls) -> "LLMSettings":
        # 允许用任意 OpenAI 兼容端点：设 LLM_BASE_URL + LLM_MODEL + LLM_API_KEY
        key = getenv("LLM_API_KEY") or getenv("DEEPSEEK_API_KEY") or getenv("OPENAI_API_KEY")
        base = getenv("LLM_BASE_URL") or getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com"
        model = getenv("LLM_MODEL") or getenv("DEEPSEEK_MODEL") or "deepseek-chat"
        return cls(
            api_key=key,
            base_url=base.rstrip("/"),
            model=model,
            temperature=float(getenv("LLM_TEMPERATURE", "0") or 0),
            max_tokens=int(getenv("LLM_MAX_TOKENS", "4096") or 4096),
        )

    @property
    def configured(self) -> bool:
        return bool(self.api_key)


@dataclass
class SearchSettings:
    """公网搜索适配器配置。

    provider: ddg（默认，无需 key）| bocha | tavily | bing | none
    """
    provider: str = "ddg"
    api_key: str = ""
    base_url: str = ""
    timeout: int = 20
    top_k: int = 6

    @classmethod
    def from_env(cls) -> "SearchSettings":
        provider = (getenv("WEB_SEARCH_PROVIDER", "ddg") or "ddg").lower()
        key = getenv("TAVILY_API_KEY") or getenv("BOCHA_API_KEY") or getenv("SERPAPI_API_KEY") or getenv("WEB_SEARCH_API_KEY")
        if provider in ("none", "off", "disabled", ""):
            provider = "none"
        elif provider == "tavily" and not getenv("TAVILY_API_KEY"):
            provider = "none"
        elif provider == "bocha" and not getenv("BOCHA_API_KEY"):
            provider = "none"
        return cls(
            provider=provider,
            api_key=key,
            base_url=getenv("WEB_SEARCH_BASE_URL"),
            timeout=int(getenv("WEB_SEARCH_TIMEOUT", "20") or 20),
            top_k=int(getenv("WEB_SEARCH_TOP_K", "6") or 6),
        )


@dataclass
class CrawlSettings:
    data_dir: Path = field(default_factory=lambda: ROOT / "data")
    max_pages_per_column: int = 8          # 单栏目最多抓几页列表
    max_articles_per_column: int = 60       # 单栏目最多入库几篇
    concurrency: int = 5                   # 单站并发
    delay: float = 0.8                     # 每次请求间隔（秒），礼貌抓取
    jitter: float = 0.7
    timeout: int = 30
    retries: int = 2
    # 只抓最近 N 年的正文：竞赛报名/推免政策过期即失效，而「往届存档」类
    # 栏目动辄几十页，全抓会把时间耗在 2015 年的旧闻上（指南 §10.6 成本控制）。
    recent_years: int = 5
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "SCAU-Research-Harness/0.1 (personal academic retrieval; polite crawl)"
    )
    prefer_https: bool = True
    min_body_chars: int = 40               # 正文短于此视为无效

    @classmethod
    def from_env(cls) -> "CrawlSettings":
        s = cls()
        data = getenv("HARNESS_DATA_DIR")
        if data:
            s.data_dir = Path(data)
        s.max_pages_per_column = int(getenv("HARNESS_MAX_PAGES", str(s.max_pages_per_column)) or s.max_pages_per_column)
        s.max_articles_per_column = int(getenv("HARNESS_MAX_ARTICLES", str(s.max_articles_per_column)) or s.max_articles_per_column)
        s.concurrency = int(getenv("HARNESS_CONCURRENCY", str(s.concurrency)) or s.concurrency)
        s.recent_years = int(getenv("HARNESS_RECENT_YEARS", str(s.recent_years)) or s.recent_years)
        return s

    @property
    def db_path(self) -> Path:
        return self.data_dir / "crawler.db"


@dataclass
class Settings:
    llm: LLMSettings = field(default_factory=LLMSettings.from_env)
    search: SearchSettings = field(default_factory=SearchSettings.from_env)
    crawl: CrawlSettings = field(default_factory=CrawlSettings.from_env)
    seed_file: Path = field(default_factory=lambda: _first_existing(
        ROOT / "seed" / "scau_bio_seed.yaml",      # 本仓库布局
        ROOT / "scau_bio_seed.yaml",
        WORKSPACE / "scau_bio_seed.yaml",          # 旧工作区布局
    ))
    webmd_file: Path = field(default_factory=lambda: _first_existing(
        ROOT / "docs" / "web.md",                  # 本仓库布局
        ROOT / "web.md",
        WORKSPACE / "web.md",                      # 旧工作区布局
    ))
    agent_max_rounds: int = 2
    agent_top_k: int = 8
    host: str = "127.0.0.1"
    port: int = 8848

    @classmethod
    def load(cls) -> "Settings":
        s = cls()
        s.agent_max_rounds = int(getenv("HARNESS_AGENT_ROUNDS", "2") or 2)
        s.agent_top_k = int(getenv("HARNESS_TOP_K", "8") or 8)
        s.host = getenv("HARNESS_HOST", "127.0.0.1") or "127.0.0.1"
        s.port = int(getenv("HARNESS_PORT", "8848") or 8848)
        return s


SETTINGS = Settings.load()
