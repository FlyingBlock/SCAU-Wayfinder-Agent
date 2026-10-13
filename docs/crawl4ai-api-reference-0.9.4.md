# Crawl4AI API Reference — verified against local checkout

All facts verified by reading files in `D:\Documents\Desktop\SCAU\crawl4ai` (no network). Paths are relative to the repo root.
Anything I could not confirm is marked **NOT VERIFIED IN THIS CHECKOUT**.

---

## 1. VERSION

| Item | Value | Source |
|---|---|---|
| Version | **0.9.4** | `crawl4ai/__version__.py:4` (`__version__ = "0.9.4"`), also `pyproject.toml:92` (`version = {attr = "crawl4ai.__version__.__version__"}`) |
| Nightly | `__nightly_version__ = None` | `crawl4ai/__version__.py:7` |
| Git HEAD (short) | **`aadd82b`** | `.git/refs/heads/main` → `aadd82bebf989f1c36e1b557b8bb2b7c9dae393f` (`.git/HEAD` → `ref: refs/heads/main`) |
| Release date | 2026-09-23 (security release, "no breaking changes") | `CHANGELOG.md:8` |

Python requirement: **`requires-python = ">=3.10"`** — `pyproject.toml:10`. Classifiers list 3.10–3.13 (`pyproject.toml:51-59`).

Console scripts (`pyproject.toml:78-83`):

```
crawl4ai-download-models = "crawl4ai.model_loader:main"
crawl4ai-migrate         = "crawl4ai.migrations:main"
crawl4ai-setup           = "crawl4ai.install:post_install"
crawl4ai-doctor          = "crawl4ai.install:doctor"
crwl                     = "crawl4ai.cli:main"
```

---

## 2. INSTALL

`README.md:185-205` (authoritative, current):

```bash
pip install -U crawl4ai
crawl4ai-setup      # installs and sets up the browser
crawl4ai-doctor     # checks the installation

# if browser setup fails:
python -m playwright install --with-deps chromium

pip install crawl4ai --pre            # pre-release
pip install -e ".[all]"               # dev install (or `pip install -e .` for core only)
```

`docs/md_v2/core/installation.md:135-137`:

```bash
pip install -U crawl4ai          # stable
pip install crawl4ai --pre       # latest pre-release
pip install crawl4ai==0.9.4      # exact version
```

Extras from `pyproject.toml:61-76` (these are the only valid extras): `pdf`, `torch`, `transformer`, `cosine`, `sync`, `all`.

`crawl4ai-setup` actually runs, per `crawl4ai/install.py:131,160`:
`python -m playwright install --with-deps` **and** `python -m patchright install --with-deps` (undetected mode uses Patchright — `patchright>=1.49.0`, `pyproject.toml:25`).

Docker (`README.md:213-218`):

```bash
export CRAWL4AI_API_TOKEN="$(openssl rand -hex 32)"
docker run -d -p 11235:11235 --name crawl4ai --shm-size=1g \
  -e CRAWL4AI_API_TOKEN="$CRAWL4AI_API_TOKEN" \
  unclecode/crawl4ai:latest
```

**Stale doc warning:** `docs/md_v2/core/installation.md` is titled "Installation & Setup (2023 Edition)" and describes Docker as experimental with tags `unclecode/crawl4ai:basic` and port 11235 (`installation.md:101-110`). That section is obsolete; `docs/md_v2/core/self-hosting.md` is the current source. `docs/md_v2/basic/installation.md:15` says bare `playwright install`, which is not what `install.py` runs.

---

## 3. CORE CRAWLING API

### 3.1 `AsyncWebCrawler` — `crawl4ai/async_webcrawler.py:58`

```python
AsyncWebCrawler(
    crawler_strategy: AsyncCrawlerStrategy = None,
    config: BrowserConfig = None,
    base_directory: str = str(os.getenv("CRAWL4_AI_BASE_DIRECTORY", Path.home())),
    thread_safe: bool = False,
    logger: AsyncLoggerBase = None,
    **kwargs,
)
```
Source: `async_webcrawler.py:115-124` (the `base_directory` default literally spans lines 119-120). Default strategy is `AsyncPlaywrightCrawlerStrategy` (`:150`).

Lifecycle:

| Member | Signature | Source |
|---|---|---|
| `start()` | `async def start(self)` → returns `self`; auto-called by `__aenter__` | `:176-192`, `:205-206` |
| `close()` | `async def close(self)` | `:194-203`, `:208-209` |
| `__aenter__` / `__aexit__` | `async with AsyncWebCrawler(config=...) as crawler:` | `:205-209` |

`arun()` (`async_webcrawler.py:216-221`):

```python
async def arun(
    self,
    url: str,
    config: CrawlerRunConfig = None,
    **kwargs,
) -> CrawlResultContainer
```

- `url` accepts `http://`, `https://`, `file://`, `raw:` (`:243`).
- Auto-starts the browser if `not self.ready` (`:252-254`).
- If `config.cache_mode is None` it is forced to `CacheMode.ENABLED` (`:266-267`). Note `CrawlerRunConfig`'s own default is already `CacheMode.BYPASS`, so the effective default is BYPASS.
- **Returns `CrawlResultContainer`** (`:688`, `:705`, `:723`), a generic wrapper that proxies attribute access to the single `CrawlResult` (`crawl4ai/models.py:290-318`). So `result.markdown` works, and `result[0]` also works.
- Legacy kwarg style (`crawler.arun(url=..., word_count_threshold=200)`) is still accepted via `**kwargs` for backwards compatibility but the documented/recommended path is `config=CrawlerRunConfig(...)` (`:225-241`).
- If `config.deep_crawl_strategy` is set, `arun` is monkey-patched at `__init__` (`:170-171`) by `DeepCrawlDecorator` (`crawl4ai/deep_crawling/base_strategy.py:10-43`) and returns **`List[CrawlResult]`** (or an async generator when `stream=True`).

`arun_many()` (`async_webcrawler.py:987-1005`):

```python
async def arun_many(
    self,
    urls: List[str],
    config: Optional[Union[CrawlerRunConfig, List[CrawlerRunConfig]]] = None,
    dispatcher: Optional[BaseDispatcher] = None,
    **kwargs,
) -> RunManyReturn       # Union[CrawlResultContainer, AsyncGenerator[CrawlResult, None]]
```

- A list of `CrawlerRunConfig` is supported; each config may carry a `url_matcher` (matched via `BaseDispatcher.select_config` → `config.is_match(url)`, `async_dispatcher.py:101-125`).
- If `dispatcher is None` it builds `MemoryAdaptiveDispatcher(max_session_permit=semaphore_count, rate_limiter=RateLimiter(base_delay=(mean_delay, mean_delay + max_range), max_delay=60.0, max_retries=3))` (`async_webcrawler.py:1068-1080`).
- `stream=True` returns an async generator (`:1122-1133`); otherwise a list (`:1134-1140`).
- With a deep-crawl strategy the dispatcher is bypassed entirely (`:1040-1066`).

Canonical usage (from `docs/md_v2/core/installation.md:45-58` and `docs/md_v2/core/cache-modes.md:40-59`):

```python
import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

async def main():
    async with AsyncWebCrawler(config=BrowserConfig(headless=True)) as crawler:
        result = await crawler.arun(
            url="https://www.example.com",
            config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS),
        )
        print(result.markdown[:300])
        print(result.markdown.raw_markdown[:300])
        print(result.markdown.fit_markdown)

asyncio.run(main())
```

Streaming arun_many (`async_webcrawler.py:1031-1036`):

```python
async for result in await crawler.arun_many(
    urls=["https://example1.com", "https://example2.com"],
    config=CrawlerRunConfig(cache_mode=CacheMode.BYPASS, stream=True),
):
    print(result.url, len(result.markdown))
```

### 3.2 Result object — `CrawlResult` (`crawl4ai/models.py:130-164`)

```python
class CrawlResult(BaseModel):
    url: str
    html: str
    fit_html: Optional[str] = None
    success: bool
    cleaned_html: Optional[str] = None
    media: Dict[str, List[Dict]] = {}
    links: Dict[str, List[Dict]] = {}
    downloaded_files: Optional[List[str]] = None
    js_execution_result: Optional[Dict[str, Any]] = None
    screenshot: Optional[str] = None
    pdf: Optional[bytes] = None
    mhtml: Optional[str] = None
    _markdown: Optional[MarkdownGenerationResult] = PrivateAttr(default=None)  # exposed as .markdown
    extracted_content: Optional[str] = None
    metadata: Optional[dict] = None
    error_message: Optional[str] = None
    session_id: Optional[str] = None
    response_headers: Optional[dict] = None
    status_code: Optional[int] = None
    ssl_certificate: Optional[SSLCertificate] = None
    dispatch_result: Optional[DispatchResult] = None
    redirected_url: Optional[str] = None
    redirected_status_code: Optional[int] = None
    network_requests: Optional[List[Dict[str, Any]]] = None
    console_messages: Optional[List[Dict[str, Any]]] = None
    tables: List[Dict] = Field(default_factory=list)   # [{headers, rows, caption, summary}]
    head_fingerprint: Optional[str] = None
    cached_at: Optional[float] = None
    cache_status: Optional[str] = None   # "hit" | "hit_validated" | "hit_fallback" | "miss"
    crawl_stats: Optional[Dict[str, Any]] = None
```

Important behaviours:

- **`markdown` is a property, not a field.** It returns `StringCompatibleMarkdown` (`models.py:188-199`, `:277-286`) — a `str` subclass whose value is `raw_markdown`, with attribute pass-through. So both `len(result.markdown)` and `result.markdown.fit_markdown` work.
- **Deprecated / removed:** `result.markdown_v2` raises `AttributeError` (`models.py:208-225`); `result.fit_markdown` and `result.fit_html` raise `AttributeError` (`:227-245`). Use `result.markdown.fit_markdown` / `result.markdown.fit_html`.
- `links` is `{"internal": [...], "external": [...]}` of `Link` dicts with keys `href, text, title, base_domain, head_data, head_extraction_status, head_extraction_error, intrinsic_score, contextual_score, total_score` (`models.py:374-384`, `:398-400`).
- `media` is `{"images": [...], "videos": [...], "audios": [...], "tables": [...]}`; `MediaItem` keys `src, data, alt, desc, score, type, group_id, format, width` (`models.py:362-395`).
- `extracted_content` is a **JSON string** (set via `json.dumps(..., indent=4, default=str, ensure_ascii=False)` — `async_webcrawler.py:953-955`). Cache hits normalise `""`/`"[]"` back to `None` (`:334-338`).
- Populated: `status_code`, `redirected_url`, `redirected_status_code`, `response_headers`, `js_execution_result`, `ssl_certificate`, `network_requests`, `console_messages` are attached after `aprocess_html` at `async_webcrawler.py:493-503` (from `AsyncCrawlResponse`, `models.py:331-348`).
- Anti-bot: a result can be flipped to `success=False` with `error_message="Blocked by anti-bot protection: ..."` (`async_webcrawler.py:636-647`).

`MarkdownGenerationResult` (`crawl4ai/models.py:120-128`):

```python
class MarkdownGenerationResult(BaseModel):
    raw_markdown: str
    markdown_with_citations: str
    references_markdown: str
    fit_markdown: Optional[str] = None
    fit_html: Optional[str] = None
```

### 3.3 `CrawlerRunConfig` — `crawl4ai/async_configs.py:1447`, `__init__` at `:1705-1826`

Every parameter below is the **exact source default**. Constants: `MIN_WORD_THRESHOLD = 1`, `IMAGE_DESCRIPTION_MIN_WORD_THRESHOLD = 1`, `IMAGE_SCORE_THRESHOLD = 2`, `SCREENSHOT_HEIGHT_TRESHOLD = 10000`, `PAGE_TIMEOUT = 60000` (`crawl4ai/config.py:48-49`, `:95`, `:102-103`).

**Content processing**

| Param | Type | Default |
|---|---|---|
| `word_count_threshold` | `int` | `MIN_WORD_THRESHOLD` = **1** |
| `extraction_strategy` | `ExtractionStrategy` | `None` |
| `chunking_strategy` | `ChunkingStrategy` | `RegexChunking()` |
| `markdown_generator` | `MarkdownGenerationStrategy` | `DefaultMarkdownGenerator()` |
| `only_text` | `bool` | `False` |
| `css_selector` | `str` | `None` |
| `target_elements` | `List[str]` | `None` → `[]` |
| `excluded_tags` | `list` | `None` → `[]` |
| `excluded_selector` | `str` | `None` → `""` |
| `keep_data_attributes` | `bool` | `False` |
| `keep_attrs` | `list` | `None` → `[]` |
| `remove_forms` | `bool` | `False` |
| `prettiify` | `bool` | `False` |
| `parser_type` | `str` | `"lxml"` |
| `scraping_strategy` | `ContentScrapingStrategy` | `None` → `LXMLWebScrapingStrategy()` |

**Proxy / identity / SSL**

| Param | Default |
|---|---|
| `proxy_config` | `None` (accepts `ProxyConfig \| List[ProxyConfig] \| dict \| str \| "direct"`, normalised by `_normalize_proxy_config`, `:2059-2073`) |
| `proxy_rotation_strategy` | `None` |
| `proxy_session_id` / `proxy_session_ttl` / `proxy_session_auto_release` | `None` / `None` / `False` |
| `locale`, `timezone_id`, `geolocation` | `None` |
| `fetch_ssl_certificate` | `False` |

**Caching**

| Param | Default |
|---|---|
| `cache_mode` | **`CacheMode.BYPASS`** (`:1736`) |
| `session_id` | `None` |
| `bypass_cache`, `disable_cache`, `no_cache_read`, `no_cache_write` | `False` (deprecated legacy flags, converting via `_legacy_to_cache_mode`, `cache_context.py:95-117`) |
| `shared_data` | `None` |
| `check_cache_freshness` | `False` (Smart Cache) |
| `cache_validation_timeout` | `10.0` |

**Navigation / timing**

| Param | Default |
|---|---|
| `wait_until` | `"domcontentloaded"` |
| `page_timeout` | `PAGE_TIMEOUT` = `60000` (ms) |
| `wait_for` | `None` (`"css:..."` or `"js:..."`) |
| `wait_for_timeout` | `None` |
| `wait_for_images` | `False` |
| `delay_before_return_html` | `0.1` |
| `mean_delay` | `0.1` |
| `max_range` | `0.3` |
| `semaphore_count` | `5` |

**Page interaction**

`js_code: Union[str, List[str]] = None`, `js_code_before_wait = None`, `c4a_script = None` (compiled to `js_code`, `:2032-2033`, `:2075+`), `js_only = False`, `ignore_body_visibility = True`, `body_visibility_timeout = 30000` (validated positive number, raises `ValueError` otherwise — `:1893-1898`), `scan_full_page = False`, `scroll_delay = 0.2`, `max_scroll_steps = None`, `process_iframes = False`, `flatten_shadow_dom = False`, `remove_overlay_elements = False`, `remove_consent_popups = False`, `simulate_user = False`, `override_navigator = False`, `magic = False`, `adjust_viewport_to_content = False`.

**Media**

`screenshot = False`, `screenshot_wait_for = None`, `screenshot_height_threshold = SCREENSHOT_HEIGHT_TRESHOLD` = 10000, `force_viewport_screenshot = False`, `pdf = False`, `capture_mhtml = False`, `image_description_min_word_threshold = 1`, `image_score_threshold = 2`, `table_score_threshold = 7`, `table_extraction = None` → `DefaultTableExtraction(table_score_threshold=...)`, `exclude_external_images = False`, `exclude_all_images = False`.

**Links / domains**

`exclude_social_media_domains = None` → `SOCIAL_MEDIA_DOMAINS` (`config.py:75-85`), `exclude_external_links = False`, `exclude_social_media_links = False`, `exclude_domains = None` → `[]`, `exclude_internal_links = False`, `score_links = False`, `preserve_https_for_internal_links = False`.

**Debug / network capture**

`verbose = True`, `log_console = False`, `capture_network_requests = False`, `capture_console_messages = False`.

**Connection / misc**

`method = "GET"`, `stream = False`, `prefetch = False` (HTML+links only), `process_in_browser = False`, `url = None`, `base_url = None`, `check_robots_txt = False`, `user_agent = None`, `user_agent_mode = None`, `user_agent_generator_config = {}`, `deep_crawl_strategy = None`, `link_preview_config = None`, `virtual_scroll_config = None`, `url_matcher = None`, `match_mode = MatchMode.OR`, `experimental = None` → `{}`, `max_retries = 0`, `fallback_fetch_function = None`.

Class helpers: `set_defaults(**kwargs)` / `get_defaults()` / `reset_defaults(*names)` (`async_configs.py:75-113`); `to_dict()` (`:2219`), `dump()` (`:2203`), `load(data, provenance=None)` (`:2208`), `from_kwargs(kwargs, provenance=None)` (`:2187`), `clone(**kwargs)` (`:2320`), `is_match(url)`.

### 3.4 `CacheMode` — `crawl4ai/cache_context.py:4-20` (re-exported from `crawl4ai`)

```python
class CacheMode(Enum):
    ENABLED    = "enabled"      # read + write
    DISABLED   = "disabled"     # no caching at all
    READ_ONLY  = "read_only"    # read only, never write
    WRITE_ONLY = "write_only"   # write only, never read
    BYPASS     = "bypass"       # skip cache for this operation
```

Semantics from `CacheContext` (`cache_context.py:59-87`): `should_read()` is true only for `ENABLED`/`READ_ONLY`; `should_write()` only for `ENABLED`/`WRITE_ONLY`. Only `http://`, `https://`, `file://` are cacheable (`:53`); `raw:` never is.

### 3.5 `BrowserConfig` — `crawl4ai/async_configs.py:784`, `__init__` at `:896-947`

| Param | Type | Default |
|---|---|---|
| `browser_type` | `str` | `"chromium"` (also `"firefox"`, `"webkit"`) |
| `headless` | `bool` | `True` |
| `browser_mode` | `str` | `"dedicated"` (`"builtin"`, `"dedicated"`, `"cdp"`, `"docker"`, `"custom"`) |
| `use_managed_browser` | `bool` | `False` |
| `cdp_url` | `str` | `None` |
| `browser_context_id`, `target_id` | `str` | `None` |
| `cdp_cleanup_on_close` | `bool` | `False` |
| `cdp_close_delay` | `float` | `1.0` |
| `cache_cdp_connection` | `bool` | `False` |
| `create_isolated_context` | `bool` | `False` |
| `use_persistent_context` | `bool` | `False` (forces `use_managed_browser=True`, `:1043-1044`) |
| `user_data_dir` | `str` | `None` |
| `chrome_channel` / `channel` | `str` | `"chromium"` (both cleared to `""` for firefox/webkit, `:964-966`) |
| `proxy` | `str` | `None` — **deprecated**, emits `UserWarning` (`:967-969`) |
| `proxy_config` | `ProxyConfig \| dict` | `None` (preferred; `dict`/`str` → `ProxyConfig`) |
| `viewport_width` | `int` | `1080` |
| `viewport_height` | `int` | `600` |
| `viewport` | `dict` | `None` (overrides width/height, `:987-989`) |
| `device_scale_factor` | `float` | `1.0` |
| `accept_downloads` | `bool` | `False` |
| `downloads_path` | `str` | `None` |
| `storage_state` | `str \| dict` | `None` |
| `ignore_https_errors` | `bool` | `True` |
| `java_script_enabled` | `bool` | `True` |
| `sleep_on_close` | `bool` | `False` |
| `verbose` | `bool` | `True` |
| `cookies` | `list` | `None` → `[]` |
| `headers` | `dict` | `None` → `{}` (auto-adds `sec-ch-ua`, `:1024`) |
| `user_agent` | `str` | `"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/116.0.0.0 Safari/537.36"` |
| `user_agent_mode` | `str` | `""` (`"random"` triggers `ValidUAGenerator`, `:1016-1019`) |
| `user_agent_generator_config` | `dict` | `{}` |
| `text_mode` | `bool` | `False` |
| `light_mode` | `bool` | `False` |
| `extra_args` | `list` | `None` → `[]` |
| `debugging_port` | `int` | `9222` |
| `host` | `str` | `"localhost"` |
| `enable_stealth` | `bool` | `False` (raises `ValueError` when combined with `browser_mode="builtin"`, `:1047-1051`) |
| `avoid_ads` | `bool` | `False` |
| `avoid_css` | `bool` | `False` |
| `init_scripts` | `List[str]` | `None` → `[]` |
| `memory_saving_mode` | `bool` | `False` |
| `max_pages_before_recycle` | `int` | `0` (0 = disabled) |

Note the **docstring at `async_configs.py:868-869` claims a macOS Chrome/116 default user-agent**; the real default in the constructor (`:928-933`) is the Linux string above. `BrowserConfig` also has `from_kwargs()` (`:1053`), `to_dict()` (`:1068`), `clone()` (`:1116`), `dump()` (`:1130`), `load(data, provenance=None)` (`:1135`).

---

## 4. MARKDOWN GENERATION

### `DefaultMarkdownGenerator` — `crawl4ai/markdown_generation_strategy.py:55`, `__init__` at `:74-80`

```python
DefaultMarkdownGenerator(
    content_filter: Optional[RelevantContentFilter] = None,
    options: Optional[Dict[str, Any]] = None,
    content_source: str = "cleaned_html",     # "cleaned_html" | "raw_html" | "fit_html"
)
```

Public method:

```python
def generate_markdown(
    self,
    input_html: str,
    base_url: str = "",
    html2text_options: Optional[Dict[str, Any]] = None,
    options: Optional[Dict[str, Any]] = None,
    content_filter: Optional[RelevantContentFilter] = None,
    citations: bool = True,
    **kwargs,
) -> MarkdownGenerationResult
```
Source `:148-157`. Base class `MarkdownGenerationStrategy` is `:26`; `generate_markdown` is abstract (`:41-52`).

### What each markdown variant is

From the implementation (`:178-250`) and `docs/md_v2/core/markdown-generation.md:359-378`:

| Variant | Meaning |
|---|---|
| `raw_markdown` | Direct HTML→markdown via `CustomHTML2Text`, no filtering. Default `html2text` options: `body_width=0, ignore_emphasis=False, ignore_links=False, ignore_images=False, protect_links=False, single_line_break=True, mark_code=True, escape_snob=False` (`:181-190`). |
| `markdown_with_citations` | `raw_markdown` with every markdown link rewritten to `text⟨N⟩` (images `![text⟨N⟩]`); only produced when `citations=True` (`:219-227`). |
| `references_markdown` | `"\n\n## References\n\n"` + one `⟨N⟩ url - desc` line per unique URL, sorted by citation number (`:139-146`). |
| `fit_markdown` | `raw_markdown` recomputed over `fit_html`. Only non-empty **if a content filter is set** (either on the generator or passed to `generate_markdown`) — `:229-242`. |
| `fit_html` | The filter's output, re-wrapped as `<div>...</div>` per block (`:236-238`). |

### Content filters

| Class | Module / line | Constructor |
|---|---|---|
| `RelevantContentFilter` (ABC) | `crawl4ai/content_filter_strategy.py:34` | `__init__` at `:37` |
| `PruningContentFilter` | `crawl4ai/content_filter_strategy.py:542`, `__init__` `:564` | `(user_query=None, min_word_threshold=None, threshold_type="fixed", threshold=0.48, preserve_classes=None, preserve_tags=None)` — **emits `DeprecationWarning` on direct use** (`:591-600`) |
| `PruningContentFilterLXML` | `crawl4ai/content_filter_strategy_lxml.py:122`, `__init__` `:131` | `(user_query=None, min_word_threshold=None, threshold_type="fixed", threshold=0.48)` — **now the recommended/default pruning engine** |
| `BM25ContentFilter` | `crawl4ai/content_filter_strategy.py:382`, `__init__` `:404` | `(user_query=None, bm25_threshold=1.0, language="english", use_stemming=True)` |
| `LLMContentFilter` | `crawl4ai/content_filter_strategy.py:822`, `__init__` `:849` | `(llm_config=None, instruction=None, chunk_token_threshold=int(1e9), overlap_rate=0.1, word_token_rate=1.3, verbose=False, logger=None, ignore_cache=True, provider=DEFAULT_PROVIDER, api_token=None, base_url=None, api_base=None, extra_args=None)` |

`PruningContentFilterLXML` subclasses `PruningContentFilter` and is **byte-identical in output**, ~10× faster (`CHANGELOG.md:24-26`; `docs/md_v2/core/fit-markdown.md:3-18`).

Working snippet (`docs/md_v2/core/markdown-generation.md:329-346`, adapted):

```python
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.content_filter_strategy import PruningContentFilterLXML
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

config = CrawlerRunConfig(
    markdown_generator=DefaultMarkdownGenerator(
        content_filter=PruningContentFilterLXML(threshold=0.6),
        content_source="cleaned_html",
    )
)
async with AsyncWebCrawler() as crawler:
    result = await crawler.arun(url="https://example.com", config=config)
    md = result.markdown
    print(md.raw_markdown)
    print(md.fit_markdown)
```

BM25 (`docs/md_v2/core/fit-markdown.md:116-127`) and LLM (`docs/md_v2/core/markdown-generation.md:244-266`) filters follow the same `content_filter=` shape; `LLMContentFilter` needs `llm_config=LLMConfig(...)`.

**Gotcha:** `DefaultMarkdownGenerator` validates its class in `CrawlerRunConfig.__init__` and raises `ValueError` for a `dict`, with a hint that the JSON form must be `{"type": "<ClassName>", "params": {...}}` — `"params"` is required, `"options"` is not recognised (`async_configs.py:1977-1989`).

---

## 5. EXTRACTION STRATEGIES

All in `crawl4ai/extraction_strategy.py`, all re-exported from `crawl4ai/__init__.py:22-30`.

| Class | Line | Constructor (exact) |
|---|---|---|
| `ExtractionStrategy` (ABC) | `:86` | `(input_format: str = "markdown", **kwargs)` (`:91`) |
| `NoExtractionStrategy` | `:149` | — |
| `CosineStrategy` | `:172` | `(semantic_filter=None, word_count_threshold=10, max_dist=0.2, linkage_method="ward", top_k=3, model_name="sentence-transformers/all-MiniLM-L6-v2", sim_threshold=0.3, **kwargs)` (`:193-203`) |
| `LLMExtractionStrategy` | `:533` | see below (`:556-575`) |
| `JsonElementExtractionStrategy` (base) | `:1043` | `(schema: Dict[str, Any], **kwargs)` (`:1077`) |
| `JsonCssExtractionStrategy` | `:1989` | `(schema, **kwargs)`; forces `input_format="html"` (`:2011-2013`) |
| `JsonLxmlExtractionStrategy` | `:2051` | `(schema, **kwargs)`; extras `use_caching=True`, `optimize_common_patterns=True` (`:2052-2061`) |
| `JsonXPathExtractionStrategy` | `:2449` | `(schema, **kwargs)`; forces `input_format="html"` (`:2472-2474`) |
| `RegexExtractionStrategy` | `:2558` | `__init__` at `:2675` |

### 5.1 `LLMExtractionStrategy` (`:556-575`)

```python
LLMExtractionStrategy(
    llm_config: 'LLMConfig' = None,
    instruction: str = None,
    schema: Dict = None,
    extraction_type="schema",              # "schema" | "block"
    chunk_token_threshold=CHUNK_TOKEN_THRESHOLD,   # = 2**11 = 2048  (config.py:43)
    overlap_rate=OVERLAP_RATE,                     # = 0.1           (config.py:44)
    word_token_rate=WORD_TOKEN_RATE,               # = 1.3           (config.py:45)
    apply_chunking=True,
    input_format: str = "markdown",        # "markdown" | "html" | "fit_markdown"
    force_json_response=False,
    verbose=False,
    # Deprecated positional-compat args:
    provider: str = DEFAULT_PROVIDER,      # "openai/gpt-4o"
    api_token: Optional[str] = None,
    base_url: str = None,
    api_base: str = None,
    **kwargs,                              # extra_args read from kwargs: kwargs.get("extra_args", {})
)
```

- If `schema` is given, `extract_type` is forced to `"schema"` (`:610-611`).
- If `apply_chunking=False`, `chunk_token_threshold` is set to `1e9` (`:618-619`).
- **`provider` / `api_token` / `base_url` / `api_base` are deprecated**: assigning a non-default value raises `AttributeError` via `_UNWANTED_PROPS` / `__setattr__` (`:550-555`, `:630-639`). Set them on `LLMConfig` instead.
- `extra_args` is not a named parameter — it must be passed as a kwarg (`extra_args={...}`) and is read at `:617`.
- Token accounting: `self.usages` (list of `TokenUsage`) and `self.total_usage` (`:621-622`).

Snippet (`docs/md_v2/extraction/llm-strategies.md:104-123`):

```python
import os
from pydantic import BaseModel
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode, LLMConfig, LLMExtractionStrategy

class Product(BaseModel):
    name: str
    price: str

llm_strategy = LLMExtractionStrategy(
    llm_config=LLMConfig(provider="openai/gpt-4o-mini", api_token=os.getenv("OPENAI_API_KEY")),
    schema=Product.model_json_schema(),
    extraction_type="schema",
    instruction="Extract all product objects with 'name' and 'price' from the content.",
    chunk_token_threshold=1000,
    overlap_rate=0.0,
    apply_chunking=True,
    input_format="markdown",   # or "html", "fit_markdown"
    extra_args={"temperature": 0.0, "max_tokens": 800},
)

config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, extraction_strategy=llm_strategy)
async with AsyncWebCrawler() as crawler:
    result = await crawler.arun(url="https://example.com", config=config)
```

### 5.2 `JsonCssExtractionStrategy` — schema format

Schema keys documented at `docs/md_v2/extraction/no-llm-strategies.md:93-98`: `name`, `baseSelector`, `fields[]`; each field has `name`, `selector`, `type` (`text`, `attribute`, `html`, `regex`, …), and optional `transform`, `default`, `attribute`, `pattern`, `source` (sibling data, implemented by `_resolve_source`, `extraction_strategy.py:2036-2049`, using the `+selector` syntax).

```python
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode, JsonCssExtractionStrategy

schema = {
    "name": "Crypto Prices",
    "baseSelector": "div.crypto-row",
    "fields": [
        {"name": "coin_name", "selector": "h2.coin-name", "type": "text"},
        {"name": "price",     "selector": "span.coin-price", "type": "text"},
    ],
}
config = CrawlerRunConfig(
    cache_mode=CacheMode.BYPASS,
    extraction_strategy=JsonCssExtractionStrategy(schema, verbose=True),
)
async with AsyncWebCrawler(verbose=True) as crawler:
    result = await crawler.arun(url="https://example.com/crypto-prices", config=config)
    data = json.loads(result.extracted_content)
```
(verbatim shape from `docs/md_v2/extraction/no-llm-strategies.md:37-90`)

### 5.3 `generate_schema` (`extraction_strategy.py:1692-1705`)

```python
JsonElementExtractionStrategy.generate_schema(
    html: str = None,
    schema_type: str = "CSS",          # "CSS" | "XPATH"
    query: str = None,
    target_json_example: str = None,
    llm_config: 'LLMConfig' = create_llm_config(),
    provider: str = None,              # legacy
    api_token: str = None,             # legacy
    url: Union[str, List[str]] = None,
    validate: bool = True,
    max_refinements: int = 3,
    usage: 'TokenUsage' = None,
    **kwargs,
) -> dict
```

- It is a `@staticmethod` on the base class, so `JsonCssExtractionStrategy.generate_schema(...)` and `JsonXPathExtractionStrategy.generate_schema(...)` both work. Pass `llm_config=LLMConfig(provider=..., api_token=...)`.
- Despite the docstring saying "Defaults to False (zero overhead)" at `:1720`, the actual default is **`validate=True`** (`:1701`). `docs/md_v2/extraction/no-llm-strategies.md:743` also says validation is on by default.
- An async twin `agenerate_schema` exists and is what the sync wrapper calls (`:1740-1751`).

Usage (`docs/md_v2/extraction/no-llm-strategies.md:723-738`):

```python
css_schema = JsonCssExtractionStrategy.generate_schema(
    html, schema_type="css",
    llm_config=LLMConfig(provider="openai/gpt-4o", api_token="your-openai-token"),
)
xpath_schema = JsonXPathExtractionStrategy.generate_schema(
    html, schema_type="xpath",
    llm_config=LLMConfig(provider="ollama/llama3.3", api_token=None),
)
strategy = JsonCssExtractionStrategy(css_schema)
```

### 5.4 `CosineStrategy` — deprecated?

**Not formally deprecated in this checkout.** There is no `DeprecationWarning` and no deprecation note in `extraction_strategy.py:172-440`; it is exported in `crawl4ai/__init__.py:25,166` and documented as a normal strategy in `docs/md_v2/extraction/clustring-strategies.md`. **However** its heavy dependencies (`sklearn`, `torch`, `sentence-transformers`) are lazily imported inside the class (`extraction_strategy.py:300`, `:351`) and are only available with the `cosine`, `torch`, or `all` extras (`pyproject.toml:63-65`), so a core install will fail at extract time. Treat it as optional-extra-gated, not deprecated.

```python
from crawl4ai import CosineStrategy
strategy = CosineStrategy(
    semantic_filter="product reviews",
    word_count_threshold=10,
    sim_threshold=0.3,
)
```
(`docs/md_v2/extraction/clustring-strategies.md:17-32`; note that doc passes `extraction_strategy=` directly to `arun()`, which only works through the legacy `**kwargs` path — prefer `CrawlerRunConfig(extraction_strategy=strategy)`.)

---

## 6. DEEP CRAWLING

Module `crawl4ai/deep_crawling/`, re-exported from `crawl4ai/__init__.py:58-79` and `crawl4ai/deep_crawling/__init__.py`.

### `DeepCrawlStrategy` (ABC) — `crawl4ai/deep_crawling/base_strategy.py:45`

```python
async def arun(
    self,
    start_url: str,
    crawler: AsyncWebCrawler,
    config: Optional[CrawlerRunConfig] = None,
) -> RunManyReturn
```
Source `:82-105`. Returns an async generator when `config.stream` is true, else `await self._arun_batch(...)`. Also `__call__(start_url, crawler, config)` (`:107-108`), abstract `shutdown()`, `can_process_url(url, depth)`, `link_discovery(...)`.

### `BFSDeepCrawlStrategy` — `crawl4ai/deep_crawling/bfs_strategy.py:16`, `__init__` `:25-39`

```python
BFSDeepCrawlStrategy(
    max_depth: int,                                  # required, positional
    filter_chain: FilterChain = FilterChain(),
    url_scorer: Optional[URLScorer] = None,
    include_external: bool = False,
    score_threshold: float = -infinity,
    max_pages: int = infinity,
    logger: Optional[logging.Logger] = None,
    resume_state: Optional[Dict[str, Any]] = None,
    on_state_change: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
    should_cancel: Optional[Callable[[], Union[bool, Awaitable[bool]]]] = None,
)
```

Methods: `can_process_url(url, depth)` (`:62`, depth 0 bypasses the filter chain), `cancel()` (`:84`), `cancelled` property (`:94`), `shutdown()` (`:407`), `export_state()` (`:414`). Sets `result.metadata["depth"]`, `result.metadata["parent_url"]` and (when scored) `result.metadata["score"]` (`:261-264`, `:200-203`).

### `DFSDeepCrawlStrategy` — `crawl4ai/deep_crawling/dfs_strategy.py:10`

```python
class DFSDeepCrawlStrategy(BFSDeepCrawlStrategy):
    def __init__(self, *args, **kwargs):   # same params as BFS
```
Source `:20-22`. Same rules/filters/scorers, stack-based walk, own `_dfs_seen` dedupe set.

### `BestFirstCrawlingStrategy` — `crawl4ai/deep_crawling/bff_strategy.py:22`, `__init__` `:36-50`

Identical signature to `BFSDeepCrawlStrategy` (same 10 parameters, same defaults). Uses a priority queue; `score_threshold` is accepted but `docs/md_v2/core/deep-crawling.md:463` says it is not needed because pages are already processed highest-score-first.

### Filters — `crawl4ai/deep_crawling/filters.py`

| Class | Line | Constructor |
|---|---|---|
| `URLFilter` (ABC) | `:40` | `(name: str = None)` (`:45`); abstract `apply(url) -> bool` (`:58`) |
| `FilterStats` | `:20` | dataclass with `total_urls`, `passed_urls`, `rejected_urls` properties (`:27-37`) |
| `FilterChain` | `:69` | `(filters: List[URLFilter] = None)` (`:74`); `add_filter(filter_)` returns self (`:86`); `async apply(url)` runs sync filters eagerly and awaits async ones concurrently, rejecting if any returns False (`:91-116`) |
| `URLPatternFilter` | `:119` | `(patterns: Union[str, Pattern, List[...]], use_glob: bool = True, reverse: bool = False)` (`:141-146`) |
| `ContentTypeFilter` | `:259` | `(allowed_types: Union[str, List[str]], check_extension: bool = True, ext_map: Dict[str, str] = _MIME_MAP)` (`:384-389`) — **extension-based, not HTTP `Content-Type`** |
| `DomainFilter` | `:425` | `(allowed_domains: Union[str, List[str]] = None, blocked_domains: Union[str, List[str]] = None)` (`:433-437`) |
| `ContentRelevanceFilter` | `:502` | `(query: Union[str, List[str]], threshold: float, k1: float = 1.2, b: float = 0.75, avgdl: int = 1000)` (`:507-514`) — note `threshold` is **required**; `async apply` |
| `SEOFilter` | `:581` | `(threshold: float = 0.65, keywords: List[str] = None, weights: Dict[str, float] = None)` (`:597-602`); `async apply` |

Any other filter class in this file: none beyond the above.

### Scorers — `crawl4ai/deep_crawling/scorers.py`

| Class | Line | Constructor |
|---|---|---|
| `URLScorer` (ABC) | `:63` | `(weight: float = 1.0)` (`:66`) |
| `CompositeScorer` | `:91` | `(scorers: List[URLScorer], normalize: bool = True)` (`:94`) |
| `KeywordRelevanceScorer` | `:160` | `(keywords: List[str], weight: float = 1.0, case_sensitive: bool = False)` (`:163`) |
| `PathDepthScorer` | `:190` | `(optimal_depth: int = 3, weight: float = 1.0)` (`:193`) |
| `ContentTypeScorer` | `:247` | `(type_weights: Dict[str, float], weight: float = 1.0)` (`:250`) |
| `FreshnessScorer` | `:332` | `(weight: float = 1.0, current_year: int = 2024)` (`:335`) |
| `DomainAuthorityScorer` | `:414` | `(domain_weights: Dict[str, float], default_weight: float = 0.5, weight: float = 1.0)` (`:417-422`) |

### Snippet (BFS + FilterChain) — `docs/snippets/deep_crawl/2.filters.py:138-156`

```python
from typing import List
from crawl4ai import (
    AsyncWebCrawler, CrawlerRunConfig, CrawlResult,
    BFSDeepCrawlStrategy, FilterChain, URLPatternFilter,
    ContentTypeFilter, DomainFilter,
)

combined_filter = FilterChain(filters=[
    URLPatternFilter(patterns=["*api*"]),
    ContentTypeFilter(allowed_types=["text/html"]),
    DomainFilter(allowed_domains=["docs.crawl4ai.com"]),
])

config = CrawlerRunConfig(
    deep_crawl_strategy=BFSDeepCrawlStrategy(
        max_depth=2, max_pages=10, include_external=False, filter_chain=combined_filter,
    ),
    verbose=False,
)

async with AsyncWebCrawler() as crawler:
    results: List[CrawlResult] = await crawler.arun(url="https://docs.crawl4ai.com", config=config)
    for r in results:
        print(r.url, r.metadata.get("depth", 0))
```

Best-first with a scorer (`docs/md_v2/core/deep-crawling.md:266-289`):

```python
from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer
from crawl4ai.deep_crawling import BestFirstCrawlingStrategy

scorer = KeywordRelevanceScorer(keywords=["crawl", "example", "async", "configuration"], weight=0.7)
config = CrawlerRunConfig(
    deep_crawl_strategy=BestFirstCrawlingStrategy(max_depth=2, url_scorer=scorer),
    stream=True,
)
async with AsyncWebCrawler() as crawler:
    async for result in await crawler.arun("https://example.com", config=config):
        print(result.metadata.get("score", 0), result.url)
```

---

## 7. ADAPTIVE CRAWLING

Module `crawl4ai/adaptive_crawler.py`. Exported from `crawl4ai/__init__.py:84-90`: `AdaptiveCrawler`, `AdaptiveConfig`, `CrawlState`, `CrawlStrategy`, `StatisticalStrategy`. **`EmbeddingStrategy` exists but is NOT exported at top level** — import it from `crawl4ai.adaptive_crawler`.

| Class | Line | Notes |
|---|---|---|
| `CrawlState` | `:27` | `@dataclass`; fields `crawled_urls`, `knowledge_base: List[CrawlResult]`, `pending_links`, `query`, `metrics`, `term_frequencies`, `document_frequencies`, `documents_with_terms`, `total_documents`, `new_terms_history`, `crawl_order`, embedding fields. `save(path)` (`:53`), `load(path)` classmethod (`:83`) |
| `AdaptiveConfig` | `:154` | `@dataclass`, see below |
| `CrawlStrategy` (ABC) | `:277` | `calculate_confidence`, `rank_links`, `should_stop`, `update_state` (`:281-296`) |
| `StatisticalStrategy` | `:301` | `__init__(self)` (`:304`) — the default; **no LLM or embeddings required** |
| `EmbeddingStrategy` | `:615` | `__init__(embedding_model=None, llm_config=None, query_llm_config=None)` (`:618`) — needs numpy/scikit-learn/shapely/alphashape |
| `AdaptiveCrawler` | `:1292` | `__init__(crawler=None, config=None, strategy=None)` (`:1295-1298`) |

`AdaptiveConfig` dataclass fields with defaults (`:156-227`): `confidence_threshold=0.7`, `max_depth=5`, `max_pages=20`, `top_k_links=3`, `min_gain_threshold=0.1`, `strategy="statistical"` (also `"embedding"`), `saturation_threshold=0.8`, `consistency_threshold=0.7`, `coverage_weight=0.4`, `consistency_weight=0.3`, `saturation_weight=0.3`, `relevance_weight=0.5`, `novelty_weight=0.3`, `authority_weight=0.2`, `save_state=False`, `state_path=None`, `embedding_model="sentence-transformers/all-MiniLM-L6-v2"`, `embedding_llm_config=None`, `query_llm_config=None`, `n_query_variations=10`, `coverage_threshold=0.85`, `alpha_shape_alpha=0.5`, plus ~15 `embedding_*` tuning fields. `validate()` asserts the weight groups each sum to 1 (`:229-256`).

`AdaptiveCrawler` public API:

```python
async def digest(start_url: str, query: str, resume_from: Optional[str] = None) -> CrawlState   # :1330-1333
confidence        -> float          # property, :1531
coverage_stats    -> Dict[str, Any] # property, :1538
is_sufficient     -> bool           # property, :1561
print_stats(detailed: bool = False) -> None                       # :1570
export_knowledge_base(filepath: Union[str, Path], format: str = "jsonl") -> None   # :1781
async def import_knowledge_base(filepath, format: str = "jsonl") -> None           # :1845
get_relevant_content(top_k: int = 5) -> List[Dict[str, Any]]                       # :1897
```

There is **no `ainit()`, `run()`, or `arun()`** on `AdaptiveCrawler` in this checkout — `digest()` is the entry point. `strategy` may be `"statistical"` or `"embedding"`; any other value raises `ValueError(f"Unknown strategy: {strategy_name}")` (`:1315-1328`).

Snippet (`docs/examples/adaptive_crawling/basic_usage.py:8-30,43,58`):

```python
import asyncio
from crawl4ai import AsyncWebCrawler, AdaptiveCrawler

async def main():
    async with AsyncWebCrawler(verbose=True) as crawler:
        adaptive = AdaptiveCrawler(crawler)          # statistical strategy by default
        # embedding variant: AdaptiveCrawler(crawler, AdaptiveConfig(strategy="embedding"))
        state = await adaptive.digest(
            start_url="https://docs.python.org/3/library/asyncio.html",
            query="async await context managers coroutines",
        )
        adaptive.print_stats(detailed=False)
        for page in adaptive.get_relevant_content(top_k=5):
            print(page["url"], page["score"])
        print(adaptive.confidence, len(state.crawled_urls))

asyncio.run(main())
```

Doc drift: `docs/md_v2/api/adaptive-crawler.md:8-12` omits the `strategy` parameter; `:143-147` omits the `format` parameter of `export_knowledge_base`.

---

## 8. HOOKS / SESSIONS / AUTH

### 8.1 Hook system

`self.hooks` dict is created in `AsyncPlaywrightCrawlerStrategy.__init__` — `crawl4ai/async_crawler_strategy.py:101-111`.

```python
def set_hook(self, hook_type: str, hook: Callable):     # :164-188
    if hook_type in self.hooks:
        self.hooks[hook_type] = hook
    else:
        raise ValueError(f"Invalid hook type: {hook_type}")

async def execute_hook(self, hook_type: str, *args, **kwargs):   # :190-208
    hook = self.hooks.get(hook_type)
    if hook:
        if asyncio.iscoroutinefunction(hook):
            return await hook(*args, **kwargs)
        return hook(*args, **kwargs)
    return args[0] if args else None
```

There is **no `HookType` enum and no `remove_hook`** in this checkout. The valid names are exactly the dict keys:

| Hook name | Invoked at | Arguments passed |
|---|---|---|
| `on_browser_created` | `:132-136` (in `start()`) | `(browser, context=..., )` |
| `on_page_context_created` | `:615` | `(page, context=context, config=config)` |
| `on_user_agent_updated` | **no call site found** | — |
| `on_execution_started` | `:1049` | `(page, context=context, config=config)` |
| `on_execution_ended` | `:1050` | `(page, context=context, config=config, result=execution_result)` |
| `before_goto` | `:725` | `(page, context=context, url=url, config=config)` |
| `after_goto` | `:802-804` | `(page, context=context, url=url, response=response, config=config)` |
| `before_retrieve_html` | `:1031` | `(page, context=context, config=config)` |
| `before_return_html` | `:1117-1119` | `(page=page, html=html, context=context, config=config)` — keyword-only call |

**Gotcha:** `on_user_agent_updated` is accepted by `set_hook` but never executed anywhere in `crawl4ai/async_crawler_strategy.py` (grep confirms only the dict entry at `:104` and the docstring at `:169`). Setting it is a silent no-op.

Also note the returned value of `execute_hook` is only used for `before_return_html` (`html = await self.execute_hook("before_return_html", ...)`, `:1117`); for the others the return value is discarded, so "return page/browser" in the docs is conventional, not required.

Docs say to attach via the strategy object (`docs/md_v2/advanced/hooks-auth.md:151-168`), which matches the source exactly:

```python
crawler = AsyncWebCrawler(config=browser_config)

async def on_page_context_created(page, context, **kwargs):
    await context.route("**", route_filter)
    await page.set_viewport_size({"width": 1080, "height": 600})
    return page

crawler.crawler_strategy.set_hook("on_page_context_created", on_page_context_created)
await crawler.start()
result = await crawler.arun(url, config=crawler_run_config)
```

`BrowserConfig` / `CrawlerRunConfig` have **no `hooks` field** in this checkout. The untrusted-config gate lists `"hook", "hooks"` among forbidden keys (`async_configs.py:239`). `hooks_to_string(hooks: dict) -> dict` (`crawl4ai/utils.py:3740-3783`) converts callables to source strings and is used only by the Docker client.

### 8.2 `session_id` reuse

- Field: `CrawlerRunConfig.session_id: str = None` (`async_configs.py:1737`). It is copied onto the result (`async_webcrawler.py:607`, `:700`).
- Passing `session_id=` as a direct `arun()` kwarg also works via the legacy `**kwargs` path, which is what `docs/md_v2/advanced/session-management.md` uses (`:24-27`).
- Sessions are auto-killed in this version: `kill_session()` logs *"Session auto-kill is enabled in the new version. No need to manually kill sessions."* (`async_crawler_strategy.py:147-162`).
- `shared_data: dict = None` on `CrawlerRunConfig` (`async_configs.py:1742`) is the documented channel for passing state between hook invocations (docstring `:1539`).

Multi-step login pattern (`docs/md_v2/advanced/session-management.md:14-37`, condensed):

```python
session_id = "my_session"
async with AsyncWebCrawler() as crawler:
    r1 = await crawler.arun(
        url="https://example.com/login",
        config=CrawlerRunConfig(
            session_id=session_id,
            js_code=[
                "document.querySelector('#user').value='me';",
                "document.querySelector('#pass').value='pw';",
                "document.querySelector('form').submit();",
            ],
            wait_for="css:.dashboard",
            cache_mode=CacheMode.BYPASS,
        ),
    )
    r2 = await crawler.arun(
        url="https://example.com/page2",
        config=CrawlerRunConfig(session_id=session_id, cache_mode=CacheMode.BYPASS),
    )
```
(`docs/md_v2/advanced/session-management.md:24-27` shows the `session_id=` kwarg form; wrapping in `CrawlerRunConfig` is the current recommended style.)

### 8.3 Auth patterns

- **`storage_state`** — `BrowserConfig.storage_state: Union[str, dict, None] = None` (`async_configs.py:921`). Tutorial: `docs/examples/storage_state_tutorial.md`.
- **Cookies on the context** — `BrowserConfig.cookies: list` (list of dicts with `name`/`value`/`url`) (`async_configs.py:926`, docstring `:863-865`); or via a hook `await context.add_cookies([...])` (`docs/md_v2/advanced/hooks-auth.md:88`).
- **Hook-based login** — see `docs/md_v2/advanced/hooks-auth.md:67-93`, which does the login inside `on_page_context_created` and comments out the actual `page.goto/fill/click` calls as a template.
- **Persistent identity** — `BrowserConfig(use_persistent_context=True, user_data_dir=...)` (`async_configs.py:909-910`, `:1043-1044`); `docs/md_v2/advanced/identity-based-crawling.md`.

---

## 9. LLM PROVIDERS

### `LLMConfig` — `crawl4ai/async_configs.py:2346`, `__init__` `:2347-2363`

```python
LLMConfig(
    provider: str = DEFAULT_PROVIDER,        # "openai/gpt-4o"  (config.py:7)
    api_token: Optional[str] = None,
    base_url: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    top_p: Optional[float] = None,
    frequency_penalty: Optional[float] = None,
    presence_penalty: Optional[float] = None,
    stop: Optional[List[str]] = None,
    n: Optional[int] = None,
    backoff_base_delay: Optional[int] = None,     # effective default 2
    backoff_max_attempts: Optional[int] = None,   # effective default 3
    backoff_exponential_factor: Optional[int] = None,  # effective default 2
    provenance: "Provenance" = None,              # defaults to Provenance.TRUSTED
)
```

Token resolution (`:2391-2408`):
1. `api_token` given and not prefixed `"env:"` → used as-is.
2. `api_token` starts with `"env:"` → `os.getenv(api_token[4:])`.
3. Otherwise the provider string is prefix-matched (in dict order) against `PROVIDER_MODELS_PREFIXES` and the matching env var is read.
4. If no prefix matches, **`provider` is silently rewritten to `openai/gpt-4o` and `api_token` becomes `os.getenv("OPENAI_API_KEY")`** (`:2406-2408`) — this is a real footgun.

Backing it is **LiteLLM** — `perform_completion_with_backoff` (`crawl4ai/utils.py:1785-1834`) calls `litellm.completion(provider, ..., api_key=api_token, base_url=base_url, **extra_args)` with `litellm.drop_params = True` (`:1820-1827`). So any LiteLLM-supported `provider/model` string is usable.

### Known provider prefixes and env vars

`PROVIDER_MODELS_PREFIXES` (`crawl4ai/config.py:32-40`) — these are the ones with automatic key resolution:

| Prefix | Env var |
|---|---|
| `ollama` | `"no-token-needed"` |
| `groq` | `GROQ_API_KEY` |
| `openai` | `OPENAI_API_KEY` |
| `anthropic` | `ANTHROPIC_API_KEY` |
| `gemini` | `GEMINI_API_KEY` |
| `deepseek` | `DEEPSEEK_API_KEY` |
| `bedrock` | `None` (AWS credential chain / SigV4, or explicit `api_token` for bearer) |

`PROVIDER_MODELS` (`config.py:11-31`) is a legacy explicit map with the same env vars, e.g. `"openai/gpt-4o-mini"`, `"openai/o3-mini"`, `"anthropic/claude-3-5-sonnet-20240620"`, `"gemini/gemini-2.0-flash"`, `"deepseek/deepseek-chat"`, `"ollama/llama3"`.

**`azure` is not present anywhere in `crawl4ai/`** — there is no azure prefix and no azure env var. LiteLLM supports an `azure/...` provider, but `LLMConfig(provider="azure/...")` will not auto-resolve a key; you must pass `api_token=` explicitly or you will silently fall through to OpenAI (see rule 4 above). **`azure` support: NOT VERIFIED IN THIS CHECKOUT.**

### OpenAI-compatible `base_url`

Yes — `LLMConfig(base_url=...)` is a first-class parameter (`async_configs.py:2351`) and is threaded straight into `litellm.completion(base_url=...)` (`utils.py:1825`; call site `extraction_strategy.py:685-695`). The deprecated `LLMContentFilter`/`LLMExtractionStrategy` shims map `api_base` → `base_url` too (`extraction_strategy.py:553`, `content_filter_strategy.py:871`).

```python
import os
from crawl4ai import LLMConfig, LLMExtractionStrategy

llm_config = LLMConfig(
    provider="openai/gpt-4o-mini",
    api_token=os.getenv("OPENAI_API_KEY"),
)
# OpenAI-compatible endpoint:
llm_config = LLMConfig(
    provider="openai/llama-3.1-8b",
    api_token="sk-local",
    base_url="http://localhost:8000/v1",
)
```
(`docs/md_v2/extraction/llm-strategies.md:26`, `:79`, `:114`.)

`LLMConfig` also exposes `to_dict()` (`:2439`), `from_kwargs(dict)` (`:2422`), `clone(**kwargs)` (`:2456`).

---

## 10. CLI (`crwl`)

Entry point: `crwl = "crawl4ai.cli:main"` (`pyproject.toml:83`). Root group is a `click.group` with `-h/--help` (`crawl4ai/cli.py:629-630`). The root command itself **is** the crawler (`@cli.command(name="")`, `:1571-1590`), and there is also an explicit `crwl crawl` subcommand (`:1014-1032`) with the same options.

### Root / `crwl crawl` options (identical sets — `:1015-1032` and `:1572-1589`)

| Flag | Type / choices | Default |
|---|---|---|
| `URL` | argument, required (`crwl crawl`); optional on root | — |
| `--example` | flag (root only) | `False` |
| `-B, --browser-config` | path to YAML/JSON | — |
| `-C, --crawler-config` | path to YAML/JSON | — |
| `-f, --filter-config` | path | — |
| `-e, --extraction-config` | path | — |
| `-j, --json-extract` | `is_flag=False, flag_value=""` (optional description) | `None` |
| `-s, --schema` | path to JSON schema | — |
| `-b, --browser` | `key1=value1,key2=value2` (parsed by `parse_key_values`, `:111`) | — |
| `-c, --crawler` | `key1=value1,key2=value2` | — |
| `-o, --output` | `all \| json \| markdown \| md \| markdown-fit \| md-fit` | `all` |
| `-O, --output-file` | path (root command only, `:1582` region) | stdout |
| `-bc, --bypass-cache` | flag | `True` |
| `-q, --question` | text | — |
| `-v, --verbose` | flag | `False` |
| `-p, --profile` | profile name | — |
| `--deep-crawl` | `bfs \| dfs \| best-first` | — |
| `--max-pages` | int | `10` |
| `--json-ensure-ascii / --no-json-ensure-ascii` | flag pair | from global config |

### Subcommands

| Command | Sub-subcommands / flags | Source |
|---|---|---|
| `crwl browser` | `status`; `start` (`-b/--browser-type` [chromium\|firefox], `-p/--port`=9222, `--headless/--no-headless`); `stop`; `view` (`-u/--url`); `restart` (`-b`, `-p`, `--headless/--no-headless`) | `:638-861` |
| `crwl cdp` | `-d/--user-data-dir`, `-P/--port`=9222, `-b/--browser-type`, `--headless`, `--incognito` | `:939-946` |
| `crwl crawl` | see table above | `:1014-1032` |
| `crwl examples` | — | `:1298-1299` |
| `crwl config` | `list`; `get KEY`; `set KEY VALUE` | `:1303-1375` |
| `crwl profiles` | `create NAME`; `list`; `delete NAME [--force/-f]` | `:1417-1487` |
| `crwl shrink PROFILE_NAME` | `--level` + `--dry-run/-n` | `:1517-1526` |
| `crwl cloud` | group imported from `crawl4ai.cloud` (`from crawl4ai.cloud import cloud_cmd`, `:38`; registered `:635`) | `crawl4ai/cloud/cli.py:72` |

**`crwl docker` and `crwl doctor` do not exist.** `crawl4ai-doctor` is a separate console script (`pyproject.toml:82`), and there is no Docker subcommand in `cli.py`.

Examples (`README.md:235-244`):

```bash
crwl https://news.ycombinator.com -o markdown
crwl https://docs.crawl4ai.com --deep-crawl bfs --max-pages 10
crwl https://www.example.com/products -q "Extract all product prices"
crwl https://example.com -o json -v --bypass-cache
crwl "https://www.infoq.com/ai-ml-data-eng/" -e docs/examples/cli/extract_css.yml -s docs/examples/cli/css_schema.json -o json
```

Global config file: `~/.crawl4ai/global.yml` (`crawl4ai/cli.py:46-57`; `docs/md_v2/core/cli.md:186`). Known keys come from `USER_SETTINGS` in `crawl4ai/config.py:110-155`: `DEFAULT_LLM_PROVIDER`, `DEFAULT_LLM_PROVIDER_TOKEN`, `VERBOSE`, `BROWSER_HEADLESS`, `BROWSER_TYPE`, `CACHE_MODE`, `USER_AGENT_MODE`, `JSON_ENSURE_ASCII`.

---

## 11. DOCKER / API SERVER

### Run

`README.md:213-227`:

```bash
export CRAWL4AI_API_TOKEN="$(openssl rand -hex 32)"
docker run -d -p 11235:11235 --name crawl4ai --shm-size=1g \
  -e CRAWL4AI_API_TOKEN="$CRAWL4AI_API_TOKEN" \
  unclecode/crawl4ai:latest

curl -s http://localhost:11235/md \
  -H "Authorization: Bearer $CRAWL4AI_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://news.ycombinator.com"}' | jq -r .markdown
```

`docs/md_v2/core/self-hosting.md:144-173` adds `--env-file .llm.env` for LLM support and notes ~10 s startup; `curl http://localhost:11235/health` needs no auth. Compose: `docker compose up -d` (or `IMAGE=unclecode/crawl4ai:latest docker compose up -d`, `INSTALL_TYPE=all docker compose up --build -d`, `ENABLE_GPU=true ...`) — `self-hosting.md:294-310`. Repo has `Dockerfile` and `docker-compose.yml` at the root.

### Endpoints — verified in source

From `deploy/docker/server.py` (the FastAPI app) and the two included routers:

| Method | Path | Source |
|---|---|---|
| GET | `/` → redirects to `/playground` | `server.py:331-333` |
| GET | `/monitor` → redirects to `/dashboard` | `server.py:339-341` |
| POST | `/token` | `server.py:585` |
| POST | `/config/dump` | `server.py:603` |
| POST | `/md` | `server.py:614` |
| POST | `/html` | `server.py:652` |
| GET | `/artifacts/{artifact_id}` | `server.py:701` |
| POST | `/screenshot` | `server.py:741` |
| POST | `/pdf` | `server.py:782` |
| POST | `/execute_js` (gated by `CRAWL4AI_EXECUTE_JS_ENABLED`) | `server.py:821`, `:875` |
| GET | `/llm/{url:path}` | `server.py:898` |
| GET | `/schema` | `server.py:917` |
| GET | `/hooks/info` | `server.py:924` |
| GET | `/health` (from `config["observability"]["health_check"]["endpoint"]`) | `server.py:945`; `deploy/docker/config.yml` |
| GET | `/metrics` (from `config["observability"]["prometheus"]["endpoint"]`) | `server.py:950` |
| POST | `/crawl` | `server.py:955` |
| POST | `/crawl/stream` | `server.py:1006` |
| GET | `/ask` | `server.py:1097` |
| POST | `/llm/job` (202) | `deploy/docker/job.py:68` |
| GET | `/llm/job/{task_id}` | `job.py:101` |
| POST | `/crawl/job` (202) | `job.py:114` |
| GET | `/crawl/job/{task_id}` | `job.py:141` |
| GET | `/monitor/health` | `deploy/docker/monitor_routes.py:15` |
| GET | `/monitor/requests` | `:26` |
| GET | `/monitor/browsers` | `:59` |
| GET | `/monitor/endpoints/stats` | `:88` |
| GET | `/monitor/timeline` | `:99` |
| GET | `/monitor/logs/janitor` | `:121` |
| GET | `/monitor/logs/errors` | `:136` |
| POST | `/monitor/actions/cleanup` (admin) | `:157` |
| POST | `/monitor/actions/kill_browser` (admin) | `:188` |
| POST | `/monitor/actions/restart_browser` (admin) | `:257` |
| POST | `/monitor/stats/reset` (admin) | `:340` |
| WS | `/monitor/ws` | `:354` |
| GET | `/playground` (StaticFiles mount) | `server.py:305-307` |
| GET | `/dashboard` (StaticFiles mount) | `server.py:315-317` |
| MCP | `/mcp/ws`, `/mcp/sse`, `/mcp/schema` | added at `server.py:1183` |

Routers are mounted at `server.py:533` (`init_job_router`) and `:541` (`monitor_router`). `deploy/docker/schemas.py` holds the request models.

### Token / env vars

- **`CRAWL4AI_API_TOKEN`** — the API token (`deploy/docker/server.py:108`, `:436`). Also settable as `config["security"]["api_token"]` in `config.yml` (same line).
- Without it the server binds loopback only and either auto-generates an ephemeral token (loopback session, `server.py:485-488`) or refuses to start when bound to a non-loopback address (`:476-478`).
- Hooks: `CRAWL4AI_HOOKS_ENABLED` (default `false`, `server.py:95`; 403 otherwise at `:738`).
- `CRAWL4AI_EXECUTE_JS_ENABLED` (default `false`, `server.py:98`; 403 at `:875`).
- `CRAWL4AI_CHROMIUM_SANDBOX` (default `false`, `server.py:105`).
- Egress: `CRAWL4AI_ALLOW_INTERNAL_URLS` (`deploy/docker/egress_broker.py:35`), `CRAWL4AI_ALLOW_INSECURE_TLS` (`:155`), `CRAWL4AI_UPSTREAM_PROXY` (`egress_proxy.py:51`).
- Artifacts: `CRAWL4AI_ARTIFACT_DIR`, `CRAWL4AI_MAX_ARTIFACT_BYTES` (50 MiB), `CRAWL4AI_ARTIFACT_QUOTA_BYTES` (2 GiB), `CRAWL4AI_ARTIFACT_TTL_SECONDS` (3600) — `deploy/docker/artifacts.py:24-27`.
- LLM: `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_TEMPERATURE`, and per-provider `<PROVIDER>_BASE_URL` / `<PROVIDER>_TEMPERATURE` — `deploy/docker/utils.py:130-316`.
- Redis: `REDIS_HOST`, `REDIS_PORT`, `REDIS_USERNAME`, `REDIS_PASSWORD` (`redis_config.py:15-36`); `SECRET_KEY` for JWT (`auth.py:51`).
- `CRAWL4_AI_BASE_DIRECTORY` is the **library** env var for the cache/base dir (`crawl4ai/async_webcrawler.py:120`).

### Declarative hooks (server)

`deploy/docker/hook_registry.py:161-189` — exactly five actions, all server-validated:

| Action | Hook point |
|---|---|
| `block_resources` | `on_page_context_created` |
| `add_cookies` | `on_page_context_created` |
| `set_headers` | `before_goto` |
| `scroll_to_bottom` | `before_retrieve_html` |
| `wait_for_timeout` | `before_retrieve_html` |

Max 10 actions per request (`docs/md_v2/core/self-hosting.md:595`). Call `GET /hooks/info` for schemas.

---

## 12. DISPATCHER / MEMORY

All in `crawl4ai/async_dispatcher.py`; `CrawlerMonitor` in `crawl4ai/components/crawler_monitor.py`. Exported from `crawl4ai/__init__.py:49-54` (`BaseDispatcher`, `MemoryAdaptiveDispatcher`, `SemaphoreDispatcher`, `RateLimiter`) and `:47` (`CrawlerMonitor`).

| Class | Line | Constructor (exact) | Purpose |
|---|---|---|---|
| `RateLimiter` | `async_dispatcher.py:28` | `(base_delay: Tuple[float, float] = (1.0, 3.0), max_delay: float = 60.0, max_retries: int = 3, rate_limit_codes: List[int] = None)` → `[429, 503]` | Per-domain adaptive delay: random delay in `base_delay` on first hit, exponential up to `max_delay`, retries on `rate_limit_codes`. `wait_if_needed(url)`, `update_delay(url, status_code)` (`:45`, `:65`) |
| `BaseDispatcher` (ABC) | `:89` | `(rate_limiter: Optional[RateLimiter] = None, monitor: Optional[CrawlerMonitor] = None)` | Shared `select_config(url, configs)` URL→config matching (`:101-125`); abstract `crawl_url` and `run_urls` |
| `MemoryAdaptiveDispatcher` | `:148` | `(memory_threshold_percent: float = 90.0, critical_threshold_percent: float = 95.0, recovery_threshold_percent: float = 85.0, check_interval: float = 1.0, max_session_permit: int = 20, fairness_timeout: float = 600.0, memory_wait_timeout: Optional[float] = 600.0, rate_limiter: Optional[RateLimiter] = None, monitor: Optional[CrawlerMonitor] = None)` | **Default dispatcher for `arun_many`**. Background task samples true process memory; enters memory-pressure mode above the threshold, throttles/reduces concurrency, recovers below the recovery threshold. Priority queue + fairness timeout for long-waiting URLs |
| `SemaphoreDispatcher` | `:639` | `(semaphore_count: int = 5, max_session_permit: int = 20, rate_limiter: Optional[RateLimiter] = None, monitor: Optional[CrawlerMonitor] = None)` | Fixed-concurrency dispatcher; simpler, no memory feedback |
| `CrawlerMonitor` | `components/crawler_monitor.py:382` | `(urls_total: int = 0, refresh_rate: float = 1.0, enable_ui: bool = True, max_width: int = 120)` | Rich/terminal live dashboard: per-task status, memory status (`NORMAL`/`PRESSURE`), queue stats, peak memory. `DisplayMode` enum (`DETAILED`/`AGGREGATED`) in `models.py:79-81`; `CrawlStats` dataclass (`models.py:47-77`) |

Usage (`docs/examples/dispatcher_example.py`; signature verified):

```python
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, RateLimiter, CrawlerMonitor
from crawl4ai import MemoryAdaptiveDispatcher, SemaphoreDispatcher

async with AsyncWebCrawler() as crawler:
    dispatcher = MemoryAdaptiveDispatcher(
        memory_threshold_percent=80.0,
        max_session_permit=10,
        rate_limiter=RateLimiter(base_delay=(1.0, 2.0), max_delay=30.0, max_retries=3),
        monitor=CrawlerMonitor(urls_total=len(urls), enable_ui=True),
    )
    results = await crawler.arun_many(urls, config=CrawlerRunConfig(), dispatcher=dispatcher)
```

---

## 13. GOTCHAS

1. **`CacheMode.BYPASS` is the `CrawlerRunConfig` default**, not `ENABLED` — `async_configs.py:1736`. `arun()` only rewrites it to `ENABLED` when it is explicitly `None` (`async_webcrawler.py:266-267`). `docs/md_v2/core/cache-modes.md` never states this.
2. **The legacy cache-flag mapping table in `docs/md_v2/core/cache-modes.md:64-69` is wrong.** It maps `no_cache_read → CacheMode.READ_ONLY` and `no_cache_write → CacheMode.WRITE_ONLY`. The real mapping in `cache_context.py:107-116` is the opposite: `no_cache_read → WRITE_ONLY`, `no_cache_write → READ_ONLY`. `docs/md_v2/api/parameters.md:129-130` has the correct mapping.
3. **`word_count_threshold` default is `1`, not `~200`.** `docs/md_v2/api/parameters.md:88` and `docs/md_v2/core/browser-crawler-config.md:207,243,326` say ~200; source is `MIN_WORD_THRESHOLD = 1` (`crawl4ai/config.py:48`, used at `async_configs.py:1708`).
4. **`PruningContentFilter` is deprecated** and emits a `DeprecationWarning` on direct instantiation (`content_filter_strategy.py:591-600`; `CHANGELOG.md:30`; `docs/md_v2/core/fit-markdown.md:3-18`). `PruningContentFilterLXML` takes the same arguments and produces byte-identical output ~10× faster. Roadmap: `PruningContentFilter` will become an alias for the lxml engine.
5. **`BrowserConfig(proxy=...)` is deprecated** and warns (`async_configs.py:967-969`). If both `proxy` and `proxy_config` are given, `proxy_config` wins and `proxy` is nulled with a second warning (`:976-978`). Use `proxy_config=ProxyConfig(...)`.
6. **`markdown_v2`, `CrawlResult.fit_markdown`, `CrawlResult.fit_html` all raise `AttributeError`** with migration messages (`models.py:208-245`). Removed in v0.5 (`docs/md_v2/core/crawler-result.md:113,331`). Use `result.markdown.fit_markdown` / `.fit_html`.
7. **`result.markdown` is a `str` subclass, not a `MarkdownGenerationResult`.** `str(result.markdown)` and `len(result.markdown)` give `raw_markdown`; attribute access is proxied (`models.py:277-286`). `result.markdown.model_dump()` also works via `__getattr__`.
8. **`on_user_agent_updated` is a dead hook** — accepted by `set_hook` but never invoked (`async_crawler_strategy.py:104` only; no `execute_hook` call site). Setting it silently does nothing.
9. **`LLMExtractionStrategy(provider=..., api_token=...)` raises `AttributeError`.** Setting any of `provider`, `api_token`, `base_url`, `api_base` to a non-default value is blocked by `_UNWANTED_PROPS` / `__setattr__` (`extraction_strategy.py:550-555`, `:630-639`). Move them into `LLMConfig`. Same pattern in `LLMContentFilter` (`content_filter_strategy.py:842-847`).
10. **`extra_args` is not a declared parameter** of `LLMExtractionStrategy`; it is read out of `**kwargs` (`extraction_strategy.py:617`). Passing it positionally will not work.
11. **Unknown LLM provider prefixes silently fall back to `openai/gpt-4o` + `OPENAI_API_KEY`** (`async_configs.py:2399-2408`). There is no error — you just hit the wrong provider. `azure` is not in the prefix list.
12. **`generate_schema`'s docstring contradicts its signature** about `validate`: docstring says "Defaults to False (zero overhead)" (`extraction_strategy.py:1720`) but the default is `validate=True` (`:1701`), matching `docs/md_v2/extraction/no-llm-strategies.md:743`. Each validation round can cost extra LLM calls / tokens.
13. **`CosineStrategy` requires optional extras.** `sklearn`/`torch`/`sentence-transformers` are imported lazily inside the class (`extraction_strategy.py:300`, `:351`) and only ship with `crawl4ai[torch|transformer|cosine|all]` (`pyproject.toml:63-65`). A core install fails at extract time, not import time.
14. **`body_visibility_timeout` must be a positive number or `CrawlerRunConfig.__init__` raises `ValueError`** (`async_configs.py:1893-1898`).
15. **`enable_stealth` + `browser_mode="builtin"` raises `ValueError`** (`async_configs.py:1047-1051`).
16. **`DefaultMarkdownGenerator` cannot be passed as a JSON dict with an `options` key** — the serializer only understands `{"type": "...", "params": {...}}` and raises `ValueError` otherwise (`async_configs.py:1977-1989`).
17. **Docker server: without `CRAWL4AI_API_TOKEN` the published port answers with connection reset**, because the server binds the *container's* loopback. The same symptom appears during the ~10 s startup window (`docs/md_v2/core/self-hosting.md:11-14`, `:180-185`). Note `-e CRAWL4AI_API_TOKEN` without a value does not forward the host variable — use `-e CRAWL4AI_API_TOKEN="$CRAWL4AI_API_TOKEN"` (`self-hosting.md:139-140`).
18. **Docker 0.9.0 breaking changes** (`CHANGELOG.md:147-164`, `deploy/docker/MIGRATION.md`): auth on by default and loopback bind; JWT tokens must be re-issued via `POST /token`; request bodies accept declarative options only — `js_code`, `js_code_before_wait`, `c4a_script`, `proxy`/`proxy_config`, `extra_args`, `user_data_dir`, `cdp_url`, `cookies`, `headers`, `init_scripts`, `base_url`, `deep_crawl_strategy`, `simulate_user`, `magic`, `process_in_browser` and nested LLM config objects are rejected with HTTP 400; `hooks.code` removed in favour of the 5 declarative actions; `output_path` removed → artifact ids; LLM `base_url` removed from `/md`, `/llm`, `/llm/job`; monitor actions need an admin token; CORS deny-by-default; TLS verification on (escape hatches `CRAWL4AI_ALLOW_INSECURE_TLS=true`, `CRAWL4AI_ALLOW_INTERNAL_URLS=true`); Redis requires a password; timeouts from request bodies capped at 60 s (`CRAWL4AI_MAX_TIMEOUT_MS`, `MIGRATION.md:173`).
19. **`crawl4ai.docker_client.Crawl4aiDockerClient` still sends the removed `hooks: {"code": ..., "timeout": ...}` shape** (`crawl4ai/docker_client.py:92-104`). Against a hardened 0.9.x server, function-based hooks from the SDK no longer work — the docs say so explicitly at `docs/md_v2/core/self-hosting.md:1180-1184`.
20. **`/monitor` is not the dashboard.** `GET /monitor` 302-redirects to `/dashboard`; `/monitor/*` is the monitoring API namespace (`server.py:336-341`; `docs/md_v2/core/self-hosting.md:1498-1500`).
21. **Windows + `channel='chromium'`**: fixed in 0.9.1 — the default channel is no longer passed to Playwright, which previously crashed with `TargetClosedError` on Windows (`docs/md_v2/blog/releases/v0.9.1.md:14,52`).
22. **Windows Docker**: `docs/md_v2/deprecated/docker-deployment.md` (AMD64/ARM, `--shm-size=2gb`, tags `basic-amd64`/`basic-armv7`) is deprecated. Current guidance requires Docker ≥ 20.10.0 with `docker compose` v2.24+ and `--shm-size=1g` (`self-hosting.md:65`, `:151`). No Windows-specific caveat beyond that is stated in this checkout.
23. **`docs/md_v2/core/installation.md` is a 2023-era page** (obsolete Docker tags, "Local Server Mode (Legacy)") — do not use it for Docker. `README.md` and `docs/md_v2/core/self-hosting.md` are current.
24. **Docs use `arun(url=..., session_id=...)` / `extraction_strategy=...` direct kwargs** in several places (`docs/md_v2/advanced/session-management.md`, `docs/md_v2/extraction/clustring-strategies.md:26-29`). These only work through the backwards-compatibility `**kwargs` path; the recommended form is `CrawlerRunConfig(...)`.
25. **`arun()` with `deep_crawl_strategy` changes the return type** from `CrawlResultContainer` to `List[CrawlResult]` (or an async generator with `stream=True`) — `deep_crawling/base_strategy.py:19-42`. Code that assumes `.markdown` on the `arun` return value will break.
26. **`crawl4ai[all]` / `CosineStrategy` / `LLMContentFilter` with embeddings are heavy**: `docs/md_v2/core/self-hosting.md:1144` warns the `all` image is significantly larger and should only be used if you actually need those extras.
27. **`LLMTableExtraction` cost warning**: `docs/md_v2/core/table_extraction.md:75-131` warns it is expensive, recommends avoiding OpenAI/Anthropic for large tables, and says to use it only when `DefaultTableExtraction` fails on complex tables.
28. **0.9.4 is a security release**: three advisories fixed (SSRF via robots.txt fetch, SSRF + response disclosure via `link_preview_config`, untrusted-config gate bypass via dict-wrapper laundering). Self-hosters should upgrade (`CHANGELOG.md:8-27`). New `crawl4ai/egress_policy.py` holds a process-wide egress proxy for the library's own HTTP clients; a plain library caller sets nothing and sees no change.
