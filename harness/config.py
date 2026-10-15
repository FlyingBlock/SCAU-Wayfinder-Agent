"""配置与密钥加载。

密钥优先级：真实环境变量 > harness/.env > 工作区根 .env。
这样既能在沙箱内跑，也能把 key 留在不入库的 .env 里。

Web 界面的「⚙️ 设置」调用的就是本模块的 `apply_llm_settings()`：它把界面上填的
base URL / 模型名 / API key 同时应用到**当前进程**（改完立即生效，不用重启）和
仓库根的 `.env`（下次启动仍然生效）。CLI 的 `setup-key` 走的是同一条路径，
两个入口不会写出两种格式的 .env。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# harness/ 目录（本文件位于 harness/harness/config.py）
PKG_DIR = Path(__file__).resolve().parent
ROOT = PKG_DIR.parent                 # 仓库根：...\harness
WORKSPACE = ROOT.parent               # 仓库的上级目录（旧布局里的 ...\SCAU，clone 后可能不存在）

# 界面上「保存」写入的文件（已在 .gitignore 中）。旧布局里 harness/ 就是仓库根，
# 所以它同时也等于 WORKSPACE/.env。
ENV_FILE = ROOT / ".env"

# 我们统一使用的三个变量名（通用 OpenAI 兼容写法）
LLM_ENV_KEYS = ("LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL")
# 历史名字：写新配置时清掉，避免 .env 里同时躺着两套 key 互相打架
LLM_LEGACY_KEYS = ("DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL")

# 设置界面里的「常见端点」，点一下就把 base URL / 模型名填进去（key 仍需自填）
LLM_PRESETS = (
    {"label": "DeepSeek", "base_url": "https://api.deepseek.com",
     "model": "deepseek-chat", "note": "默认；key 在 platform.deepseek.com"},
    {"label": "OpenAI", "base_url": "https://api.openai.com/v1",
     "model": "gpt-4o-mini", "note": ""},
    {"label": "智谱 GLM", "base_url": "https://open.bigmodel.cn/api/paas/v4",
     "model": "glm-4-plus", "note": ""},
    {"label": "通义千问", "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
     "model": "qwen-plus", "note": ""},
    {"label": "Kimi", "base_url": "https://api.moonshot.cn/v1",
     "model": "moonshot-v1-8k", "note": ""},
    {"label": "Ollama（本机）", "base_url": "http://localhost:11434/v1",
     "model": "qwen2.5:14b", "note": "本机模型，key 随便填一个非空值"},
    {"label": "vLLM（本机）", "base_url": "http://localhost:8000/v1",
     "model": "Qwen/Qwen2.5-14B-Instruct", "note": "key 随便填一个非空值"},
)

# OCR（图片 / 扫描件里的文字）相关变量。和 LLM 那三项一样，界面上填的会写进 .env，
# 走同一套 read_env_file / write_env_file，两个入口不会写出两种格式。
OCR_ENV_KEYS = ("OCR_PROVIDER", "BAIDU_OCR_API_KEY", "BAIDU_OCR_SECRET_KEY",
                "OCR_ACCURATE", "BAIDU_OCR_ENDPOINT")

# 登录墙 / 自动登录相关变量。**只有非机密的行为开关放这里**：
# 账号密码永远不进 .env，只落在 .auth/credentials.json（已在 .gitignore）。
AUTH_ENV_KEYS = ("AUTH_AUTO_LOGIN", "AUTH_OCR_CAPTCHA", "AUTH_CAPTCHA_ROUNDS",
                 "AUTH_SERVICE", "AUTH_CAPTCHA_URL")


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


# 读 .env **之前**的真实进程环境。之后用它判断「.env 里的值到底有没有被
# 外部环境变量挡住」——`_load_dotenv` 只在变量不存在时才写，所以此刻就在
# 环境里的键，说明外面（shell / 系统属性 / 计划任务）有更高优先级的同名变量。
_ENVIRON_BEFORE_DOTENV = dict(os.environ)

# 先加载工作区根，再加载 harness/（后者优先，但都不覆盖已有变量）
_load_dotenv(WORKSPACE / ".env")
_load_dotenv(ROOT / ".env")


def getenv(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


# --------------------------------------------------------------------------- #
# .env 读写：Web 设置界面与 CLI setup-key 共用，保证两边写出同一种格式
# --------------------------------------------------------------------------- #
def read_env_file(env_file: Path | None = None) -> dict[str, str]:
    """读 .env 的键值对（忽略注释、空行和没有 = 的行）。文件不存在返回 {}。"""
    path = env_file or ENV_FILE
    if not path.is_file():
        return {}
    try:
        text = path.read_text(encoding="utf-8-sig")
    except OSError:
        return {}
    out: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        if key:
            out[key] = val.strip().strip('"').strip("'")
    return out


def write_env_file(updates: dict[str, str], *, remove_keys: tuple[str, ...] = (),
                   env_file: Path | None = None) -> Path:
    """把 updates 合并进 .env：保留注释与其它配置，只替换同名键，缺的追加到末尾。

    刻意做「按行合并」而不是整文件重写 —— 用户自己在 .env 里写的注释和
    WEB_SEARCH_PROVIDER 之类的设置不应该被设置界面抹掉。
    """
    path = env_file or ENV_FILE
    lines: list[str] = []
    if path.is_file():
        lines = path.read_text(encoding="utf-8-sig").splitlines()
    drop = {k.upper() for k in remove_keys}
    pending = {k: str(v) for k, v in updates.items()}
    out: list[str] = []
    for raw in lines:
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            key = line.split("=", 1)[0].strip()
            if key.upper() in drop:
                continue
            if key in pending:
                out.append(f"{key}={pending.pop(key)}")
                continue
        out.append(raw)
    if pending:
        if out and out[-1].strip():
            out.append("")
        out.append("# ---- 由设置界面 / cli setup-key 写入 ----")
        out.extend(f"{k}={v}" for k, v in pending.items())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(out).strip() + "\n", encoding="utf-8")
    return path


def env_file_shadowed_keys(env_file: Path | None = None, *,
                           environ: dict[str, str] | None = None) -> set[str]:
    """找出「写在 .env 里、但被外部环境变量盖住」的键。

    这类键改了 .env 也不会生效（下次启动仍然用环境变量里的值），必须提示用户，
    否则会以为设置没保存成功。

    默认拿进程读 .env **之前**的环境快照做比较，而不是当前的 os.environ ——
    设置界面把新值写进 os.environ 之后，用当前值比较会让这个警告凭空消失，
    但重启后外部变量照样赢。`environ` 参数用于测试。
    """
    env = _ENVIRON_BEFORE_DOTENV if environ is None else environ
    return {k for k, v in read_env_file(env_file).items()
            if k in env and str(env[k]).strip() != v.strip()}


@dataclass
class LLMSettings:
    api_key: str = ""
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-chat"
    temperature: float = 0.0
    # 单次生成的上限。思维链模型（deepseek-flash / deepseek-reasoner 等）会先用
    # reasoning_content 思考、再写正文，预算给小了会只拿到空正文；4096 实测不够，
    # 8192 仍可能被截断（agent._generate 会据此翻倍重试）。想固定更大就直接设
    # LLM_MAX_TOKENS。
    max_tokens: int = 8192
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
            max_tokens=int(getenv("LLM_MAX_TOKENS", "8192") or 8192),
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


# --------------------------------------------------------------------------- #
def apply_llm_settings(*, api_key: str | None = None, base_url: str | None = None,
                       model: str | None = None, persist: bool = True,
                       env_file: Path | None = None) -> dict:
    """把一份 LLM 配置应用到当前进程，并按需落盘到 .env。

    参数为 None 或空字符串表示「不改动这一项」（界面上留空即沿用现有 key）。
    `SETTINGS.llm` 是**原地修改**的：其它模块持有的是同一个对象，改完下一个
    请求就用新配置，不需要重启 Web 服务。

    返回 `{"settings", "applied", "wrote", "warning"}`，交给调用方拼提示。
    永不抛异常（写盘失败只作为 warning 返回），因为「本次运行生效」比落盘更重要。
    """
    llm = SETTINGS.llm
    updates: dict[str, str] = {}

    if base_url:
        clean = base_url.strip().rstrip("/")
        if clean:
            llm.base_url = clean
            updates["LLM_BASE_URL"] = clean
    if model:
        clean = model.strip()
        if clean:
            llm.model = clean
            updates["LLM_MODEL"] = clean
    if api_key:
        clean = api_key.strip()
        if clean:
            llm.api_key = clean
            updates["LLM_API_KEY"] = clean

    # 同步进 os.environ：.env 只在变量不存在时才写入，直接改环境变量可以保证
    # 之后任何走 getenv()/from_env() 的代码路径（doctor、别的子进程）看到新值。
    for key, val in updates.items():
        os.environ[key] = val

    warning = ""
    wrote = False
    if updates and persist:
        try:
            write_env_file(updates, remove_keys=LLM_LEGACY_KEYS, env_file=env_file)
            wrote = True
        except OSError as e:
            warning = f"配置已在本次运行中生效，但写入 .env 失败：{e}"

    return {"settings": llm, "applied": sorted(updates), "wrote": wrote,
            "warning": warning}


# --------------------------------------------------------------------------- #
def apply_ocr_settings(*, provider: str | None = None, api_key: str | None = None,
                       secret_key: str | None = None, accurate: bool | None = None,
                       persist: bool = True, env_file: Path | None = None) -> dict:
    """把一份 OCR 配置应用到当前进程并按需落盘。与 `apply_llm_settings` 同构。

    留空（None）表示「沿用现在的值」——界面上不会回显 secret，不能要求重填。
    `harness.ocr.SETTINGS` 是原地替换的，改完下一个附件解析就用新配置。
    """
    updates: dict[str, str] = {}
    if provider is not None and provider.strip():
        p = provider.strip().lower()
        if p in ("baidu", "none", "off", "disabled", ""):
            updates["OCR_PROVIDER"] = "none" if p in ("none", "off", "disabled", "") else p
    if api_key is not None and api_key.strip():
        updates["BAIDU_OCR_API_KEY"] = api_key.strip()
    if secret_key is not None and secret_key.strip():
        updates["BAIDU_OCR_SECRET_KEY"] = secret_key.strip()
    if accurate is not None:
        updates["OCR_ACCURATE"] = "1" if accurate else "0"

    for key, val in updates.items():
        os.environ[key] = val

    warning = ""
    wrote = False
    if updates and persist:
        try:
            write_env_file(updates, env_file=env_file)
            wrote = True
        except OSError as e:
            warning = f"OCR 配置已在本次运行中生效，但写入 .env 失败：{e}"

    # 让 harness.ocr.SETTINGS 原地更新（不重新 import 模块，避免循环依赖问题）
    settings = None
    try:
        from . import ocr as ocr_mod

        settings = ocr_mod.refresh_settings()
    except Exception as e:                                    # noqa: BLE001
        warning = warning or f"{type(e).__name__}: {e}"

    return {"settings": settings, "applied": sorted(updates), "wrote": wrote,
            "warning": warning}


def clear_ocr_settings(*, persist: bool = True, env_file: Path | None = None) -> dict:
    """清掉 OCR 凭据（界面上「清除」按钮用）。"""
    for key in ("BAIDU_OCR_API_KEY", "BAIDU_OCR_SECRET_KEY"):
        os.environ.pop(key, None)
    os.environ["OCR_PROVIDER"] = "none"
    updates = {"OCR_PROVIDER": "none", "BAIDU_OCR_API_KEY": "", "BAIDU_OCR_SECRET_KEY": ""}
    warning = ""
    wrote = False
    if persist:
        try:
            write_env_file(updates, env_file=env_file)
            wrote = True
        except OSError as e:
            warning = f"清除只对本次运行生效，写入 .env 失败：{e}"
    settings = None
    try:
        from . import ocr as ocr_mod

        settings = ocr_mod.refresh_settings()
    except Exception as e:                                    # noqa: BLE001
        warning = warning or f"{type(e).__name__}: {e}"
    return {"settings": settings, "applied": sorted(updates), "wrote": wrote,
            "warning": warning}


# --------------------------------------------------------------------------- #
# 登录墙 / 自动登录的**行为开关**（账号密码另有 .auth/credentials.json，见 harness/auth.py）
# --------------------------------------------------------------------------- #
def apply_auth_settings(*, auto_login: bool | None = None, ocr_captcha: bool | None = None,
                        captcha_rounds: int | None = None, service: str | None = None,
                        captcha_url: str | None = None, persist: bool = True,
                        env_file: Path | None = None) -> dict:
    """把一份「登录行为」配置应用到当前进程并按需落盘 `.env`。

    与 `apply_llm_settings` / `apply_ocr_settings` 同构。区别是这几个开关**总是全量写**：
    界面上复选框的状态就是用户的意思，不像 key 那样存在「留空=不改动」的语义。
    字符串项（service / captcha_url）留空表示清掉。
    返回 `{"settings", "applied", "wrote", "warning"}`，永不抛异常。
    """
    updates: dict[str, str] = {}
    if auto_login is not None:
        updates["AUTH_AUTO_LOGIN"] = "1" if auto_login else "0"
    if ocr_captcha is not None:
        updates["AUTH_OCR_CAPTCHA"] = "1" if ocr_captcha else "0"
    if captcha_rounds is not None:
        updates["AUTH_CAPTCHA_ROUNDS"] = str(max(1, min(int(captcha_rounds), 8)))
    if service is not None:
        updates["AUTH_SERVICE"] = service.strip()
    if captcha_url is not None:
        updates["AUTH_CAPTCHA_URL"] = captcha_url.strip()

    for key, val in updates.items():
        os.environ[key] = val

    warning = ""
    wrote = False
    if updates and persist:
        try:
            write_env_file(updates, env_file=env_file)
            wrote = True
        except OSError as e:
            warning = f"登录配置已在本次运行中生效，但写入 .env 失败：{e}"

    settings = None
    try:
        from . import auth as auth_mod

        settings = auth_mod.refresh_settings()
    except Exception as e:                                    # noqa: BLE001
        warning = warning or f"{type(e).__name__}: {e}"
    return {"settings": settings, "applied": sorted(updates), "wrote": wrote,
            "warning": warning}


def clear_auth_credentials() -> dict:
    """清掉保存的账号密码（`.auth/credentials.json`）。开关本身保留。"""
    from . import auth as auth_mod

    existed = auth_mod.forget_credentials()
    return {"removed": existed, "state": auth_mod.credentials_state()}
