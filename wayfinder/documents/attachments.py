"""附件层：下载 → 落盘 → 解析 → 入库。

为什么单独一层：采集正文和解析附件是两种节奏的动作（正文要快、附件要重），
而且附件必须能单独重跑（`cli attach`）——通知正文没变、附件解析规则改了，
不该为此重抓整个栏目。

约定：

  · 下载的附件存放在**项目内的固定目录** `data/attachments/<年>/<月>/`，
    文件名是 `<sha1前10位>_<安全文件名>`。同一个 URL 内容相同就复用（按 URL
    与 sha1 双重去重），不会存两份。
  · 单文件、单篇通知、单次任务都有大小与数量上限（见 `AttachmentSettings`），
    默认只抓「值得解析的格式」（见 docparse.PARSEABLE_EXT），zip/rar 里的
    图片与 Office 文件会递归解析一层。
  · 解析出来的正文写进 `attachment` 表并建 FTS 索引，检索层会把它并进
    所属通知的证据里（`docparse` 只负责抽文本，不做入库）。
  · 登录墙后面的附件用同一个 `AuthSession` 抓（和正文一条路径）。
"""
from __future__ import annotations

import datetime
import hashlib
import json
import re
import threading
import time
import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path

from . import docparse
from ..core.config import ROOT, SETTINGS, getenv

#: 下载目录（项目内固定位置）
ATTACH_DIR = ROOT / "data" / "attachments"

#: 文件名里不能出现的字符（Windows 更严）
_BAD_NAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


@dataclass
class AttachmentSettings:
    enabled: bool = True
    dir: Path = field(default_factory=lambda: ATTACH_DIR)
    max_files_per_article: int = 6
    max_bytes_per_file: int = 25_000_000          # 25MB
    max_total_bytes: int = 120_000_000            # 单次任务上限
    timeout: int = 60
    delay: float = 0.5                            # 附件请求之间的间隔（礼貌抓取）
    ocr: bool = True                              # 允许对附件内图片做 OCR
    only_parseable: bool = True                   # 只下载「能解析」的格式
    min_new_chars: int = 20                       # 解析结果短于此不建索引（噪声）

    @classmethod
    def from_env(cls) -> "AttachmentSettings":
        s = cls()
        s.enabled = (getenv("ATTACH_ENABLED", "1") or "1").strip().lower() not in ("0", "false", "no")
        d = getenv("ATTACH_DIR")
        if d:
            s.dir = Path(d)
        s.max_files_per_article = int(getenv("ATTACH_MAX_FILES", str(s.max_files_per_article))
                                      or s.max_files_per_article)
        s.max_bytes_per_file = int(getenv("ATTACH_MAX_MB", "") or 0) * 1_000_000 \
            or s.max_bytes_per_file
        s.ocr = (getenv("ATTACH_OCR", "1") or "1").strip().lower() not in ("0", "false", "no")
        return s


# --------------------------------------------------------------------------- #
# 文件名与落盘
# --------------------------------------------------------------------------- #
def guess_filename(url: str, *, fallback: str = "attachment") -> str:
    """从 URL（或 Content-Disposition）猜一个显示文件名。"""
    path = urllib.parse.urlsplit(url or "").path
    name = urllib.parse.unquote(path.rsplit("/", 1)[-1] or "")
    name = _BAD_NAME.sub("_", name).strip(" .")
    if not name:
        name = fallback
    if len(name) > 120:
        stem, dot, ext = name.rpartition(".")
        name = (stem[:100] + (dot + ext if dot else "")) if dot else name[:120]
    return name


def safe_stem(name: str) -> str:
    """给「哈希_原名」里的原名部分做长度与字符约束。"""
    stem, dot, ext = name.rpartition(".")
    stem = _BAD_NAME.sub("_", stem or name).strip(" ._")
    ext = _BAD_NAME.sub("", ext or "").strip(" ._")[:8]
    return (stem[:60] or "attachment") + (("." + ext) if ext else "")


def kind_of(name: str, data: bytes = b"") -> str:
    ext = docparse.ext_of(name)
    if ext:
        return ext
    if docparse.is_image(name, data):
        return "png"
    fmt, _ = _sniff(data)
    return fmt or ""


def _norm_url(url: str) -> str:
    """URL 规范化（http→https、去 fragment），用于跨记录对齐同一份附件。"""
    try:
        from ..crawl.fetcher import normalize_url

        return normalize_url(url)
    except Exception:
        return url


def _sniff(data: bytes) -> tuple[str, str]:
    from .ocr import _sniff_image

    return _sniff_image(data or b"")


def store_path(sha1: str, name: str, *, when: datetime.datetime | None = None) -> Path:
    when = when or datetime.datetime.now()
    folder = ATTACH_DIR / f"{when.year:04d}" / f"{when.month:02d}"
    return folder / f"{sha1[:10]}_{safe_stem(name)}"


def save_bytes(data: bytes, name: str, *, root: Path | None = None,
               when: datetime.datetime | None = None) -> tuple[Path, bool]:
    """把附件写进 data/attachments。返回 (路径, 是否新建)。

    去重按**内容哈希**：同一份文件（哪怕通知里换了个附件名）只存一份，
    第二次直接复用第一次的落盘路径。同名不同内容也不会互相覆盖
    （文件名前缀就是哈希）。
    """
    digest = hashlib.sha1(data).hexdigest()
    base = (root or ATTACH_DIR) / f"{(when or datetime.datetime.now()).year:04d}" \
        / f"{(when or datetime.datetime.now()).month:02d}"
    # 已经存过同一内容？直接复用（保持最初那份的文件名）
    if base.is_dir():
        for existing in base.glob(f"{digest[:10]}_*"):
            if existing.is_file() and existing.stat().st_size == len(data):
                return existing, False
    path = base / f"{digest[:10]}_{safe_stem(name)}"
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    tmp.write_bytes(data)
    tmp.replace(path)
    return path, True


def rel_path(path: Path) -> str:
    """相对项目根的路径（存库用，换机器/换盘符也不会失效）。"""
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def abs_path(rel: str) -> Path:
    p = Path(rel)
    return p if p.is_absolute() else (ROOT / rel)


# --------------------------------------------------------------------------- #
# 单份附件的处理
# --------------------------------------------------------------------------- #
@dataclass
class FetchedAttachment:
    """一份附件从下载到解析的完整结果（落库前）。"""

    url: str = ""
    filename: str = ""
    kind: str = ""
    content_type: str = ""
    sha1: str = ""
    stored: str = ""                     # 相对路径
    bytes: int = 0
    text: str = ""
    parser: str = ""
    note: str = ""
    error: str = ""
    tables: int = 0
    images: int = 0
    ocr_used: int = 0
    ocr_chars: int = 0
    reused: bool = False                 # 内容之前就存过
    from_db: bool = False                # 直接复用了库里的解析结果
    ms: int = 0
    extra: dict = field(default_factory=dict)

    def as_row(self) -> dict:
        return {
            "url": self.url, "filename": self.filename, "kind": self.kind,
            "content_type": self.content_type, "sha1": self.sha1,
            "stored": self.stored, "bytes": self.bytes, "text": self.text,
            "parser": self.parser, "note": self.note, "error": self.error,
            "tables": self.tables, "images": self.images,
            "ocr_used": self.ocr_used, "ocr_chars": self.ocr_chars,
            "ms": self.ms,
        }


class AttachmentFetcher:
    """用 Fetcher 下载附件并解析。线程安全性由 Fetcher 自身保证。"""

    def __init__(self, fetcher, store=None, settings: AttachmentSettings | None = None,
                 *, progress=None) -> None:
        self.fetcher = fetcher
        self.store = store
        self.s = settings or AttachmentSettings.from_env()
        self.progress = progress
        self._lock = threading.Lock()
        self._total_bytes = 0
        self.stats = {"seen": 0, "downloaded": 0, "parsed": 0, "failed": 0,
                      "skipped": 0, "reused": 0, "ocr": 0}

    def _say(self, msg: str) -> None:
        if self.progress:
            try:
                self.progress(msg)
            except Exception:
                pass

    # ---- 下载 ----
    def fetch_one(self, url: str, *, article_id: int = 0, force: bool = False) -> FetchedAttachment:
        out = FetchedAttachment(url=url, filename=guess_filename(url))
        t0 = time.time()
        if not self.s.enabled:
            out.error = "附件下载已关闭（ATTACH_ENABLED=0）"
            return out
        if self.s.only_parseable and not docparse.is_parseable(out.filename):
            out.error = "skip:unparseable"
            return out
        with self._lock:
            if self._total_bytes > self.s.max_total_bytes:
                out.error = "skip:budget"
                return out
        # 库里已有同一 URL 且解析成功 → 直接复用（不重复下载）
        # URL 用规范化形式比对，否则 http/https 差异会让同一份附件被重复下载一遍。
        cached = None
        if self.store is not None and not force:
            try:
                cached = self.store.get_attachment_by_url(url) or \
                    self.store.get_attachment_by_url(_norm_url(url))
            except Exception:
                cached = None
        if cached and cached.get("text") and cached.get("stored") and \
                abs_path(str(cached["stored"])).is_file():
            out.from_db = True
            out.filename = str(cached.get("filename") or out.filename)
            out.kind = str(cached.get("kind") or docparse.ext_of(out.filename))
            out.sha1 = str(cached.get("sha1") or "")
            out.stored = str(cached.get("stored") or "")
            out.bytes = int(cached.get("bytes") or 0)
            out.text = str(cached.get("text") or "")
            out.parser = str(cached.get("parser") or "")
            out.note = str(cached.get("note") or "")
            out.tables = int(cached.get("tables") or 0)
            out.images = int(cached.get("images") or 0)
            out.ocr_used = int(cached.get("ocr_used") or 0)
            out.ocr_chars = int(cached.get("ocr_chars") or 0)
            self.stats["reused"] += 1
            out.ms = int((time.time() - t0) * 1000)
            return out

        res = self.fetcher.fetch_bytes(url, max_bytes=self.s.max_bytes_per_file,
                                       use_auth=self.fetcher.auth is not None,
                                       force=force)
        if not res.get("ok"):
            out.error = str(res.get("error") or "download_failed")
            self.stats["failed"] += 1
            return out
        data = res["data"]
        if not data:
            out.error = "empty"
            self.stats["failed"] += 1
            return out
        ctype = str(res.get("content_type") or "")
        cd = str(res.get("content_disposition") or "")
        m = re.search(r"filename\*?=(?:UTF-8''|\")?([^\";]+)", cd, re.I)
        if m:
            try:
                out.filename = urllib.parse.unquote(m.group(1)).strip().strip('"')
                out.filename = _BAD_NAME.sub("_", out.filename)
            except Exception:
                pass
        if not docparse.ext_of(out.filename):
            ext = _ext_from_content_type(ctype) or kind_of(out.filename, data)
            if ext:
                out.filename = f"{out.filename}.{ext}"
        out.kind = kind_of(out.filename, data)
        out.content_type = ctype
        out.sha1 = hashlib.sha1(data).hexdigest()
        out.bytes = len(data)
        with self._lock:
            self._total_bytes += out.bytes
        self.stats["downloaded"] += 1

        path, created = save_bytes(data, out.filename, root=self.s.dir)
        out.stored = rel_path(path)
        out.reused = not created

        if self.s.only_parseable and not docparse.is_parseable(out.filename) \
                and not docparse.is_image(out.filename, data):
            out.error = "skip:unparseable"
            out.ms = int((time.time() - t0) * 1000)
            return out

        parsed = docparse.parse_bytes(data, out.filename, use_ocr=self.s.ocr)
        out.text = parsed.text
        out.parser = parsed.parser
        out.note = parsed.note
        out.error = parsed.error
        out.tables = len(parsed.tables)
        out.images = len(parsed.images)
        out.ocr_used = parsed.ocr_used
        out.ocr_chars = parsed.ocr_chars
        if parsed.pages:
            out.extra["pages"] = parsed.pages
        if parsed.extra:
            out.extra.update({k: v for k, v in parsed.extra.items()
                              if isinstance(v, (str, int, float, bool))})
        self.stats["parsed"] += 1
        self.stats["ocr"] += parsed.ocr_used
        out.ms = int((time.time() - t0) * 1000)
        self._say(f"      └ 附件 {out.filename[:32]} {out.bytes // 1024}KB → "
                  f"{len(out.text)} 字符（{out.parser}）")
        return out

    # ---- 一篇通知的附件 ----
    def fetch_for_article(self, article_id: int, urls: list[str], *,
                          force: bool = False) -> list[FetchedAttachment]:
        out: list[FetchedAttachment] = []
        keep: list[str] = []
        for u in urls:
            if u and u not in keep:
                keep.append(u)
        for i, url in enumerate(keep[:self.s.max_files_per_article]):
            if i:
                time.sleep(self.s.delay)
            self.stats["seen"] += 1
            try:
                item = self.fetch_one(url, article_id=article_id, force=force)
            except Exception as e:                            # noqa: BLE001
                item = FetchedAttachment(url=url, filename=guess_filename(url),
                                         error=f"{type(e).__name__}: {e}")
                self.stats["failed"] += 1
            if item.error in ("skip:unparseable", "skip:budget"):
                self.stats["skipped"] += 1
            out.append(item)
        if len(keep) > self.s.max_files_per_article:
            self._say(f"      （该通知有 {len(keep)} 个附件，只取前 "
                      f"{self.s.max_files_per_article} 个）")
        return out


def _ext_from_content_type(ctype: str) -> str:
    ctype = (ctype or "").split(";")[0].strip().lower()
    return {
        "application/pdf": "pdf",
        "application/msword": "doc",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "application/vnd.ms-excel": "xls",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
        "application/vnd.ms-powerpoint": "ppt",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
        "application/zip": "zip",
        "application/x-zip-compressed": "zip",
        "application/x-rar-compressed": "rar",
        "text/plain": "txt",
        "text/csv": "csv",
        "text/html": "html",
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/gif": "gif",
        "image/bmp": "bmp",
        "image/tiff": "tiff",
        "image/webp": "webp",
    }.get(ctype, "")


# --------------------------------------------------------------------------- #
# 入库 + 检索文本
# --------------------------------------------------------------------------- #
def persist(store, article_id: int, items: list[FetchedAttachment]) -> int:
    """把解析结果写进 attachment 表。返回写入条数。"""
    n = 0
    for it in items:
        if it.error in ("skip:unparseable", "skip:budget") and not it.stored:
            continue
        row = it.as_row()
        row["extra"] = json.dumps(it.extra or {}, ensure_ascii=False)
        try:
            store.upsert_attachment(article_id=article_id, **row)
            n += 1
        except Exception:
            continue
    return n


def process_article(store, fetcher, article_id: int, urls: list[str], *,
                    settings: AttachmentSettings | None = None, force: bool = False,
                    progress=None) -> dict:
    """一篇通知的完整流程：下载 → 解析 → 入库。返回统计字典。"""
    af = AttachmentFetcher(fetcher, store, settings, progress=progress)
    items = af.fetch_for_article(article_id, urls, force=force)
    written = persist(store, article_id, items)
    ok = sum(1 for i in items if i.text.strip())
    return {"article_id": article_id, "files": len(items), "written": written,
            "with_text": ok, "bytes": sum(i.bytes for i in items),
            "ocr": sum(i.ocr_used for i in items),
            "errors": [i.error for i in items if i.error],
            "stats": af.stats}


# --------------------------------------------------------------------------- #
# 已有附件的批量重跑（cli attach）
# --------------------------------------------------------------------------- #
def pending_articles(store, *, limit: int = 20, missing_only: bool = True) -> list[dict]:
    """挑出「有附件但还没解析过」的文章（重跑用）。"""
    rows = store.articles_with_unparsed_attachments(limit=limit) if missing_only else \
        store.articles_with_attachments(limit=limit)
    return rows


def summarize(items: list[FetchedAttachment]) -> str:
    if not items:
        return "没有附件"
    ok = [i for i in items if i.text.strip()]
    bits = [f"{len(items)} 个附件", f"{len(ok)} 个解析出正文"]
    ocr = sum(i.ocr_used for i in items)
    if ocr:
        bits.append(f"OCR {ocr} 张图")
    failed = [i for i in items if i.error and not i.error.startswith("skip:")]
    if failed:
        bits.append(f"{len(failed)} 个失败")
    return "，".join(bits)


def human_size(n: int) -> str:
    for unit, div in (("GB", 1 << 30), ("MB", 1 << 20), ("KB", 1 << 10)):
        if n >= div:
            return f"{n / div:.1f}{unit}"
    return f"{n}B"


def dir_stats(root: Path | None = None) -> dict:
    """附件目录的占用情况（设置页与 doctor 用）。"""
    base = root or ATTACH_DIR
    files = 0
    total = 0
    if base.is_dir():
        for p in base.rglob("*"):
            if p.is_file():
                files += 1
                try:
                    total += p.stat().st_size
                except OSError:
                    pass
    return {"dir": str(base), "files": files, "bytes": total, "human": human_size(total)}
