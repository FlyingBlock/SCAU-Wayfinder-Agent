"""办公文件解析层：把附件（Office / PDF / 压缩包 / 图片）变成可检索的文本。

为什么需要这一层：校内通知最值钱的信息（报名截止、赛程、名额、加分表、课程
名单）几乎都在附件里，正文往往只有一句「详见附件」。卡片层只能看到附件名，
模型也就无从引用。

设计取舍：

  · **不装新依赖**。解析器按「有则更好、没有也能跑」分层：
    python-docx / openpyxl / python-pptx / Pillow 装了就用，没装就退回自带的
    zip+XML / 纯 Python 二进制解析。PDF、.doc、.xls 三个最要命的格式都自己实现了
    （见 pdftext.py 与本文的 OLE2 / BIFF 实现），因为学校附件里它们最多。
  · 每份附件返回一个 `ParsedFile`：正文 + 表格（转成逐行文本）+ 图片清单 +
    用了哪种解析器 + 未解析掉部分的原因。调用方（attachments.py）负责落库与引用。
  · .doc/.xls 有两条路：优先用项目自带的 LibreOffice（DSH 的 libreoffice-kit，
    若可用），失败或不可用就走内置解析器。内置解析器对「Word 97–2003 + 片段表」
    的文件是精确的，对少数畸形文件会退回「扫描可见文本」并如实写进 note。

对外只有一个入口：`parse_bytes(data, name) -> ParsedFile` / `parse_path(path)`。
"""
from __future__ import annotations

import io
import json
import re
import struct
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from . import ocr as ocrmod

# --------------------------------------------------------------------------- #
# 结果结构
# --------------------------------------------------------------------------- #
@dataclass
class ParsedFile:
    """一份附件或图片的解析结果。"""

    name: str = ""
    kind: str = ""                       # 扩展名（小写，不含点）
    text: str = ""
    tables: list[list[list[str]]] = field(default_factory=list)
    images: list[dict] = field(default_factory=list)
    parser: str = ""                     # docx-openpyxl / pdf-stdlib / ole2-word / …
    note: str = ""                       # 没解析到的部分、可疑之处
    error: str = ""
    pages: int = 0
    truncated: bool = False
    ocr_used: int = 0
    ocr_chars: int = 0
    bytes: int = 0
    extra: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.error and bool(self.text.strip())

    @property
    def has_content(self) -> bool:
        return bool(self.text.strip()) or bool(self.tables) or bool(self.images)

    def add_text(self, chunk: str) -> None:
        if chunk and chunk.strip():
            self.text = (self.text + "\n\n" + chunk.strip()).strip()

    def summary(self) -> str:
        if self.error:
            return f"解析失败：{self.error}"
        bits = []
        if self.text.strip():
            bits.append(f"{len(self.text)} 字符")
        if self.images:
            bits.append(f"{len(self.images)} 张图")
        if self.ocr_used:
            bits.append(f"OCR {self.ocr_used} 张")
        if self.tables:
            bits.append(f"{len(self.tables)} 张表")
        if self.pages:
            bits.append(f"{self.pages} 页")
        if not bits:
            bits.append("没抽到文字")
        line = "，".join(bits)
        if self.note:
            line += f"（{self.note}）"
        return line


# --------------------------------------------------------------------------- #
# 扩展名分类
# --------------------------------------------------------------------------- #
OFFICE_WORD = {"doc", "docx", "docm", "rtf", "wps"}
OFFICE_SHEET = {"xls", "xlsx", "xlsm", "xlsb", "csv", "et"}
OFFICE_SLIDE = {"ppt", "pptx", "pps", "ppsx", "dps"}
PDF_EXT = {"pdf"}
IMAGE_EXT = {"jpg", "jpeg", "png", "gif", "bmp", "tif", "tiff", "webp", "ico", "emf", "wmf"}
ARCHIVE_EXT = {"zip", "rar", "7z", "tar", "gz", "tgz"}
TEXT_EXT = {"txt", "text", "md", "htm", "html", "xml", "json", "log"}

#: 值得下载并尝试解析的附件（采集侧用它过滤）
PARSEABLE_EXT = (OFFICE_WORD | OFFICE_SHEET | OFFICE_SLIDE | PDF_EXT | IMAGE_EXT
                 | ARCHIVE_EXT | TEXT_EXT)

MAX_TEXT_CHARS = 400_000


def ext_of(name: str) -> str:
    base = (name or "").split("?")[0].split("#")[0]
    tail = base.rsplit("/", 1)[-1]
    return tail.rsplit(".", 1)[-1].lower() if "." in tail else ""


def is_image(name: str, data: bytes = b"") -> bool:
    return ext_of(name) in IMAGE_EXT or ocrmod.looks_like_image(data or b"", name)


def is_parseable(name: str) -> bool:
    return ext_of(name) in PARSEABLE_EXT


# --------------------------------------------------------------------------- #
# 一、OOXML（docx / xlsx / pptx）——一律先走 zip+XML，装了库再走库
# --------------------------------------------------------------------------- #
def _zip_open(data: bytes) -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BytesIO(data))


def _xml_text(xml: str) -> str:
    """从 OOXML 片段里取可读文本：<w:t> / <a:t> / <t> 都覆盖，保留段落与制表。"""
    if not xml:
        return ""
    out = xml
    out = re.sub(r"<(?:w:br|w:cr|a:br)\s*/>", "\n", out)
    out = re.sub(r"</(?:w:p|a:p)>", "\n", out)
    out = re.sub(r"</(?:w:tr|a:tr)>", "\n", out)
    out = re.sub(r"</(?:w:tc|a:tc)>", "\t", out)
    # 保留文本节点的内容，删掉其余标签
    out = re.sub(r"<(?!/?(?:[a-z]+:)?t(?:\s[^>]*)?>)[^>]*>", "", out)
    out = re.sub(r"</?(?:[a-z]+:)?t(?:\s[^>]*)?>", "", out)
    for ent, ch in (("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'),
                    ("&apos;", "'"), ("&amp;", "&")):
        out = out.replace(ent, ch)
    out = re.sub(r"[ \t]*\n[ \t]*", "\n", out)
    out = re.sub(r"\t{2,}", "\t", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


def _zip_images(zf: zipfile.ZipFile, prefixes: tuple[str, ...]) -> list[dict]:
    out: list[dict] = []
    for info in zf.infolist():
        low = info.filename.lower()
        if not any(low.startswith(p) for p in prefixes):
            continue
        if not re.search(r"\.(png|jpe?g|gif|bmp|tiff?|emf|wmf|webp)$", low):
            continue
        try:
            data = zf.read(info.filename)
        except Exception:
            continue
        out.append({"name": PurePosixPath(info.filename).name, "data": data,
                    "path": info.filename, "size": len(data)})
    return out


def _svg_or_vml_text(zf: zipfile.ZipFile) -> str:
    """Word 用文本框/艺术字时正文在 VML/SVG 里，顺手也取出来。"""
    chunks: list[str] = []
    for info in zf.infolist():
        name = info.filename.lower()
        if name.endswith(".vml") or "/drawings/" in name or name.endswith(".svg"):
            try:
                raw = zf.read(info.filename).decode("utf-8", "ignore")
            except Exception:
                continue
            txt = re.sub(r"<[^>]+>", " ", raw)
            txt = re.sub(r"\s+", " ", txt).strip()
            if len(txt) > 4:
                chunks.append(txt)
    return "\n".join(chunks)


# ---- docx ----
_W_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def parse_docx(data: bytes, name: str = "") -> ParsedFile:
    out = ParsedFile(name=name, kind="docx")
    try:
        zf = _zip_open(data)
    except zipfile.BadZipFile:
        out.error = "不是有效的 docx（zip 结构损坏）"
        return out
    with zf:
        try:
            doc_xml = zf.read("word/document.xml").decode("utf-8", "ignore")
        except KeyError:
            out.error = "docx 里没有 word/document.xml"
            return out
        out.parser = "docx-stdlib"
        text = _xml_text(doc_xml)
        # 表格单独整理一份（表格文本已经包含在 text 里，这里给出结构化副本）
        for tbl in re.findall(r"<w:tbl\b.*?</w:tbl>", doc_xml, re.S):
            rows: list[list[str]] = []
            for tr in re.findall(r"<w:tr\b.*?</w:tr>", tbl, re.S):
                cells = []
                for tc in re.findall(r"<w:tc\b.*?</w:tc>", tr, re.S):
                    cells.append(_xml_text(tc).replace("\n", " ").replace("\t", " ").strip())
                if any(cells):
                    rows.append(cells)
            if rows:
                out.tables.append(rows)
        extra = _svg_or_vml_text(zf)
        if extra:
            text = (text + "\n\n" + extra).strip()
        out.text = text[:MAX_TEXT_CHARS]
        out.truncated = len(text) > MAX_TEXT_CHARS
        out.images = _zip_images(zf, ("word/media/",))
        if not out.images:
            out.images = _zip_images(zf, ("word/embeddings/",))
        if not out.text.strip() and out.images:
            out.note = "正文为空，内容可能全在图片里（已交给 OCR）"
    return out


# ---- xlsx ----
def _cell_text(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        if v == int(v) and abs(v) < 1e15:
            return str(int(v))
        return f"{v:g}"
    return re.sub(r"\s+", " ", str(v)).strip()


def parse_xlsx(data: bytes, name: str = "") -> ParsedFile:
    out = ParsedFile(name=name, kind=ext_of(name) or "xlsx")
    try:
        zf = _zip_open(data)
    except zipfile.BadZipFile:
        out.error = "不是有效的 xlsx（zip 结构损坏）"
        return out
    with zf:
        out.images = _zip_images(zf, ("xl/media/",))
        shared: list[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            raw = zf.read("xl/sharedStrings.xml").decode("utf-8", "ignore")
            shared = [_xml_text(m).replace("\n", " ") for m in
                      re.findall(r"<si\b.*?</si>", raw, re.S)]
        try:
            from openpyxl import load_workbook                      # type: ignore

            wb = load_workbook(io.BytesIO(data), data_only=True, read_only=True)
            out.parser = "xlsx-openpyxl"
            chunks: list[str] = []
            for ws in wb.worksheets:
                rows: list[list[str]] = []
                for row in ws.iter_rows(values_only=True):
                    vals = [_cell_text(v) for v in row]
                    while vals and not vals[-1]:
                        vals.pop()
                    if any(vals):
                        rows.append(vals)
                if not rows:
                    continue
                out.tables.append(rows)
                chunks.append(f"===== 工作表：{ws.title} =====")
                chunks.extend(" | ".join(r) for r in rows[:4000])
            wb.close()
            out.text = "\n".join(chunks)[:MAX_TEXT_CHARS]
        except Exception:
            # 退化：直接读 sheet XML（不解析公式结果，但文本与数字都在）
            out.parser = "xlsx-stdlib"
            chunks = []
            sheets: list[tuple[str, str]] = []
            wb_xml = zf.read("xl/workbook.xml").decode("utf-8", "ignore") \
                if "xl/workbook.xml" in zf.namelist() else ""
            for m in re.finditer(r'<sheet\b[^>]*name="([^"]*)"[^>]*r:id="([^"]*)"', wb_xml):
                sheets.append((m.group(1), m.group(2)))
            rels = {}
            if "xl/_rels/workbook.xml.rels" in zf.namelist():
                rel_xml = zf.read("xl/_rels/workbook.xml.rels").decode("utf-8", "ignore")
                for m in re.finditer(r'Id="([^"]+)"[^>]*Target="([^"]+)"', rel_xml):
                    rels[m.group(1)] = m.group(2).lstrip("/")
            names = [n for n in zf.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml$", n)]
            targets = [rels.get(rid, "") for _, rid in sheets] or names
            for idx, target in enumerate(targets):
                path = target if target in zf.namelist() else (
                    names[idx] if idx < len(names) else "")
                if not path:
                    continue
                raw = zf.read(path).decode("utf-8", "ignore")
                label = sheets[idx][0] if idx < len(sheets) else path
                chunks.append(f"===== 工作表：{label} =====")
                rows = []
                for rm in re.finditer(r"<row\b[^>]*>(.*?)</row>", raw, re.S):
                    cells = []
                    for cm in re.finditer(r'<c\b([^>]*)>(.*?)</c>', rm.group(1), re.S):
                        attrs, body = cm.group(1), cm.group(2)
                        t = re.search(r't="([^"]+)"', attrs)
                        typ = t.group(1) if t else "n"
                        vm = re.search(r"<v>(.*?)</v>", body, re.S)
                        ism = re.search(r"<is>.*?<t[^>]*>(.*?)</t>", body, re.S)
                        if typ == "s" and vm:
                            try:
                                cells.append(shared[int(vm.group(1))])
                                continue
                            except (ValueError, IndexError):
                                pass
                        if ism:
                            cells.append(re.sub(r"<[^>]+>", "", ism.group(1)))
                        elif vm:
                            cells.append(re.sub(r"<[^>]+>", "", vm.group(1)))
                        else:
                            cells.append("")
                    while cells and not cells[-1]:
                        cells.pop()
                    if any(cells):
                        rows.append(cells)
                out.tables.append(rows)
                chunks.extend(" | ".join(r) for r in rows[:4000])
            out.text = "\n".join(chunks)[:MAX_TEXT_CHARS]
    if not out.text.strip() and out.images:
        out.note = "表格里没有文字，内容可能是扫描件或图片"
    return out


# ---- pptx ----
def parse_pptx(data: bytes, name: str = "") -> ParsedFile:
    out = ParsedFile(name=name, kind=ext_of(name) or "pptx")
    try:
        zf = _zip_open(data)
    except zipfile.BadZipFile:
        out.error = "不是有效的 pptx（zip 结构损坏）"
        return out
    with zf:
        out.parser = "pptx-stdlib"
        slides = sorted(
            (n for n in zf.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)),
            key=lambda n: int(re.findall(r"\d+", n)[-1]))
        chunks = []
        for i, path in enumerate(slides, 1):
            raw = zf.read(path).decode("utf-8", "ignore")
            txt = _xml_text(raw)
            notes = ""
            note_path = path.replace("slides/slide", "notesSlides/notesSlide")
            if note_path in zf.namelist():
                notes = _xml_text(zf.read(note_path).decode("utf-8", "ignore"))
            piece = f"===== 第 {i} 页 ====="
            if txt:
                piece += "\n" + txt
            if notes:
                piece += "\n[备注] " + notes
            chunks.append(piece)
        out.pages = len(slides)
        out.text = "\n\n".join(chunks)[:MAX_TEXT_CHARS]
        out.images = _zip_images(zf, ("ppt/media/",))
    return out


# --------------------------------------------------------------------------- #
# 二、PDF —— 文本层 + 内嵌图片（扫描件交给 OCR）
# --------------------------------------------------------------------------- #
def pdf_images(data: bytes, *, max_images: int = 20, min_bytes: int = 4000) -> list[dict]:
    """抽出 PDF 里的内嵌图片（DCTDecode/JPXDecode/FlateDecode 位图）。

    只为 OCR 用：过滤掉小于 min_bytes 的图（图标、线条、水印小图）。
    """
    from .pdftext import Pdf, decode_stream

    out: list[dict] = []
    try:
        pdf = Pdf(data)
    except Exception:
        return out
    seen: set[str] = set()
    for num in list(pdf._offsets)[:4000]:
        if len(out) >= max_images:
            break
        obj = pdf.get_object(num)
        if not isinstance(obj, __import__("harness.pdftext", fromlist=["Stream"]).Stream):
            continue
        d = obj.dict
        if str(d.get("Subtype") or "") != "Image":
            continue
        filt = d.get("Filter")
        filters = [filt] if isinstance(filt, str) else list(filt or [])
        raw = obj.raw
        if not raw or len(raw) < min_bytes:
            continue
        name = f"pdf-img-{num}"
        try:
            if "DCTDecode" in filters or "DCT" in filters:
                payload, ext = raw, "jpg"
            elif "JPXDecode" in filters:
                payload, ext = raw, "jp2"
            elif "FlateDecode" in filters or "Fl" in filters:
                payload, ext = _flate_image_to_png(obj.dict, decode_stream(raw, d)), "png"
            elif "CCITTFaxDecode" in filters:
                continue                                   # 传真编码：跳过（会有噪点）
            else:
                continue
        except Exception:
            continue
        if not payload:
            continue
        import hashlib

        h = hashlib.sha1(payload).hexdigest()
        if h in seen:
            continue
        seen.add(h)
        out.append({"name": f"{name}.{ext}", "data": payload, "size": len(payload),
                    "page_hint": num})
    return out


def _flate_image_to_png(obj: dict, samples: bytes) -> bytes:
    """把 Flate 解码后的原始位图样本包成 PNG（无 Pillow 也能做，纯 zlib+struct）。"""
    import zlib

    w = int(obj.get("Width") or 0)
    h = int(obj.get("Height") or 0)
    bpc = int(obj.get("BitsPerComponent") or 8)
    cs = obj.get("ColorSpace")
    cs_name = cs if isinstance(cs, str) else ""
    ncomp = {"DeviceRGB": 3, "DeviceGray": 1, "DeviceCMYK": 4}.get(cs_name, 0)
    if ncomp == 0 or w <= 0 or h <= 0 or bpc != 8:
        return b""
    row = w * ncomp
    if len(samples) < row * h:
        return b""
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        raw += samples[y * row:(y + 1) * row]
    color_type = {1: 0, 3: 2, 4: 6}[ncomp]
    def chunk(tag: bytes, payload: bytes) -> bytes:
        return (struct.pack(">I", len(payload)) + tag + payload
                + struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF))
    ihdr = struct.pack(">IIBBBBB", w, h, 8, color_type, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(bytes(raw), 6)) + chunk(b"IEND", b""))


def parse_pdf(data: bytes, name: str = "") -> ParsedFile:
    from .pdftext import extract_pdf

    out = ParsedFile(name=name, kind="pdf")
    res = extract_pdf(data, max_chars=MAX_TEXT_CHARS)
    out.parser = "pdf-stdlib"
    out.pages = res.pages
    if res.error:
        out.error = res.error
        return out
    out.text = res.text
    out.truncated = len(res.text) >= MAX_TEXT_CHARS
    out.extra["scanned_pages"] = res.image_only_pages
    out.extra["pages_with_text"] = res.pages_with_text
    out.extra["producer"] = res.producer
    if res.scanned:
        out.note = "PDF 没有文本层（疑似扫描件），已提取内嵌图片交给 OCR"
        out.images = pdf_images(data)
    elif res.image_only_pages:
        out.note = f"其中 {res.image_only_pages} 页疑似扫描件"
        if not out.text.strip():
            out.images = pdf_images(data)
    return out


# --------------------------------------------------------------------------- #
# 三、OLE2 复合文档（.doc / .xls 的老格式）
# --------------------------------------------------------------------------- #
FREESECT = 0xFFFFFFFF
ENDOFCHAIN = 0xFFFFFFFE
FATSECT = 0xFFFFFFFD
DIFSECT = 0xFFFFFFFC


class OleFile:
    """最小可用的 OLE2 / 复合文档读取器（只读、只解压需要的流）。"""

    def __init__(self, data: bytes) -> None:
        if data[:8] != b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
            raise ValueError("不是 OLE2 复合文档（签名不符）")
        self.data = data
        self.sect_size = 1 << struct.unpack_from("<H", data, 0x1E)[0]
        self.mini_size = 1 << struct.unpack_from("<H", data, 0x20)[0]
        self.dir_start = struct.unpack_from("<I", data, 0x30)[0]
        self.mini_cutoff = struct.unpack_from("<I", data, 0x38)[0]
        mini_fat_start = struct.unpack_from("<I", data, 0x3C)[0]
        difat_start = struct.unpack_from("<I", data, 0x44)[0]
        num_difat = struct.unpack_from("<I", data, 0x48)[0]
        self._fat = self._read_fat(difat_start, num_difat)
        self._minifat = self._read_minifat(mini_fat_start)
        self.entries = self._read_dir()
        root = next((e for e in self.entries if e["type"] == 5), None)
        self._ministream = self._read_chain(root["start"]) if root and \
            root["start"] < 0xFFFFFFFA else b""

    # ---- 结构 ----
    def _sector(self, sid: int) -> int:
        return (sid + 1) * self.sect_size

    def _read_fat(self, difat_start: int, num_difat: int) -> list[int]:
        sids: list[int] = []
        for i in range(109):
            v = struct.unpack_from("<I", self.data, 0x4C + i * 4)[0]
            if v >= 0xFFFFFFFA:
                break
            sids.append(v)
        sid = difat_start
        for _ in range(min(num_difat, 4096)):
            if sid >= 0xFFFFFFFA:
                break
            base = self._sector(sid)
            cnt = self.sect_size // 4 - 1
            for i in range(cnt):
                v = struct.unpack_from("<I", self.data, base + i * 4)[0]
                if v < 0xFFFFFFFA:
                    sids.append(v)
            sid = struct.unpack_from("<I", self.data, base + cnt * 4)[0]
        fat: list[int] = []
        for fs in sids:
            base = self._sector(fs)
            for i in range(self.sect_size // 4):
                if base + i * 4 + 4 <= len(self.data):
                    fat.append(struct.unpack_from("<I", self.data, base + i * 4)[0])
        return fat

    def _read_minifat(self, start: int) -> list[int]:
        if start >= 0xFFFFFFFA:
            return []
        raw = self._read_chain(start)
        return list(struct.unpack_from("<%dI" % (len(raw) // 4), raw, 0)) if raw else []

    def _read_dir(self) -> list[dict]:
        raw = self._read_chain(self.dir_start)
        out = []
        for i in range(0, len(raw) - 127, 128):
            e = raw[i:i + 128]
            etype = e[0x42]
            if etype not in (1, 2, 5):
                continue
            nlen = struct.unpack_from("<H", e, 0x40)[0]
            out.append({
                "name": e[:max(0, nlen - 2)].decode("utf-16-le", "ignore"),
                "type": etype,
                "start": struct.unpack_from("<I", e, 0x74)[0],
                "size": struct.unpack_from("<I", e, 0x78)[0],
            })
        return out

    def _chain(self, start: int, fat: list[int]) -> list[int]:
        out, sid, seen = [], start, set()
        while sid < 0xFFFFFFFA and sid not in seen:
            seen.add(sid)
            out.append(sid)
            sid = fat[sid] if sid < len(fat) else ENDOFCHAIN
        return out

    def _read_chain(self, start: int) -> bytes:
        if start >= 0xFFFFFFFA:
            return b""
        return b"".join(self.data[self._sector(s):self._sector(s) + self.sect_size]
                        for s in self._chain(start, self._fat))

    def _read_mini(self, start: int, size: int) -> bytes:
        if start >= 0xFFFFFFFA:
            return b""
        out = b"".join(self._ministream[s * self.mini_size:(s + 1) * self.mini_size]
                       for s in self._chain(start, self._minifat))
        return out[:size]

    def names(self) -> list[str]:
        return [e["name"] for e in self.entries if e["type"] == 2]

    def stream(self, name: str) -> bytes:
        for e in self.entries:
            if e["type"] != 2:
                continue
            if e["name"] == name or e["name"].lstrip("\x01\x05") == name:
                if e["size"] < self.mini_cutoff and self._ministream:
                    out = self._read_mini(e["start"], e["size"])
                    if out:
                        return out
                return self._read_chain(e["start"])[:e["size"]]
        raise KeyError(name)


# ---- .doc：FIB → 片段表 → 正文 ----
def _doc_piece_table(ole: OleFile) -> tuple[str, str]:
    """返回 (正文, 解析方式)。方式为 'piecetable' 或 'scan'。"""
    wd = ole.stream("WordDocument")
    flags = struct.unpack_from("<H", wd, 0x0A)[0]
    tbl_name = "1Table" if (flags >> 9) & 1 else "0Table"
    try:
        tbl = ole.stream(tbl_name)
    except KeyError:
        tbl = b""
    if len(wd) < 64:
        return "", "empty"
    csw = struct.unpack_from("<H", wd, 32)[0]
    p = 34 + csw * 2
    if p + 2 > len(wd):
        return _doc_scan_text(wd), "scan"
    cslw = struct.unpack_from("<H", wd, p)[0]
    p += 2
    fibRgLw = wd[p:p + cslw * 4]
    p += cslw * 4
    if p + 2 > len(wd):
        return _doc_scan_text(wd), "scan"
    cbRgFcLcb = struct.unpack_from("<H", wd, p)[0]
    p += 2
    rg = wd[p:]

    # cfcrgFcLcb 里每一项是 (fc, lcb)。不写死下标（不同 nFib 的下标会整体偏移），
    # 而是按 CLX 的结构特征去找：可选 Prc 链 + 0x02 Pcdt + 长度自洽 + cp 递增。
    best: tuple[float, str] | None = None
    for i in range(min(len(rg) // 8, cbRgFcLcb, 600)):
        fc, lcb = struct.unpack_from("<II", rg, i * 8)
        if lcb < 16 or fc + lcb > len(tbl) or lcb > len(tbl):
            continue
        clx = tbl[fc:fc + lcb]
        q = 0
        while q + 3 <= len(clx) and clx[q] == 0x01:
            q += 3 + struct.unpack_from("<H", clx, q + 1)[0]
        if q + 5 > len(clx) or clx[q] != 0x02:
            continue
        cch = struct.unpack_from("<H", clx, q + 1)[0]
        if cch < 16 or (cch - 4) % 12 or q + 3 + cch > lcb:
            continue
        npc = (cch - 4) // 12
        base = q + 3
        try:
            cps = list(struct.unpack_from("<%dI" % (npc + 1), clx, base))
        except struct.error:
            continue
        if cps[0] != 0 or any(cps[j] >= cps[j + 1] for j in range(npc)):
            continue
        total = cps[-1]
        if total <= 0 or total > max(len(wd), 1) * 4:
            continue
        pieces: list[str] = []
        bad = 0
        for k in range(npc):
            pcd = base + (npc + 1) * 4 + k * 8
            if pcd + 8 > len(clx):
                bad += 1
                break
            fcval = struct.unpack_from("<I", clx, pcd + 2)[0]
            comp = bool(fcval & 0x40000000)
            fcv = fcval & 0x3FFFFFFF
            realfc = (fcv // 2) if comp else fcv
            ncp = cps[k + 1] - cps[k]
            if realfc + (ncp if comp else ncp * 2) > len(wd):
                bad += 1
                break
            if comp:
                pieces.append(wd[realfc:realfc + ncp].decode("gb18030", "ignore"))
            else:
                pieces.append(wd[realfc:realfc + ncp * 2].decode("utf-16-le", "ignore"))
        if bad:
            continue
        text = "".join(pieces)
        score = _text_score(text)
        if best is None or score > best[0]:
            best = (score, _clean_doc_text(text))
    if best is not None and best[0] >= 0.55 and len(best[1]) > 40:
        return best[1], "piecetable"
    return _doc_scan_text(wd), "scan"


_TEXT_CHARS = re.compile(r"[\u4e00-\u9fff\u3000-\u303f\uff00-\uffefA-Za-z0-9，。；：、（）《》〔〕%．\-—\s]")


def _text_score(text: str) -> float:
    if not text:
        return 0.0
    return len(_TEXT_CHARS.findall(text)) / len(text)


def _clean_doc_text(text: str) -> str:
    """去掉 Word 的控制字符：\\x07 单元格/行结束、\\x0c 分页、\\x0b 换行。"""
    text = text.replace("\r", "\n").replace("\x0b", "\n").replace("\x0c", "\n")
    text = re.sub(r"[\x00-\x08\x0e-\x1f]", "", text)
    text = re.sub(r"[ \t]*\n[ \t]*", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


_DOC_TEXT_RE = re.compile(
    r"[\u3400-\u4dbf\u4e00-\u9fff\u3000-\u303f\uff00-\uffef"
    r"\r\n\t\x0b\x0c -~]")


def _runs_to_lines(text: str, *, keep_ascii: bool = False) -> list[str]:
    """把「文本/非文本混排」的长字符串切成有意义的行。

    比「逐字符过滤」强的地方：不会把整段话拆成一行一个字，也不会把二进制垃圾
    里的偶然字母（`bjbj`、`NSWS`）当成正文——短行与低字符密度直接丢掉。
    """
    lines: list[str] = []
    buf: list[str] = []
    for ch in text:
        if _DOC_TEXT_RE.match(ch):
            buf.append(ch)
            continue
        if len(buf) >= 6:
            lines.append("".join(buf))
        buf = []
    if len(buf) >= 6:
        lines.append("".join(buf))

    out: list[str] = []
    for line in lines:
        for piece in re.split(r"[\r\n\x0b\x0c]+", line):
            piece = re.sub(r"[ \t]{2,}", " ", piece).strip()
            if len(piece) < 5:
                continue
            cjk = len(re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff]", piece))
            ascii_alnum = len(re.findall(r"[A-Za-z0-9]", piece))
            if cjk >= 3:
                out.append(piece)
            elif keep_ascii and ascii_alnum >= 8 and cjk == 0:
                out.append(piece)
    return out


def _doc_scan_text(wd: bytes) -> str:
    """兜底：在 WordDocument 流里扫出可读的 UTF-16LE / GBK 文本段。

    只在片段表拿不到时使用（文件被畸形工具写过）。真实 Word 的正文是一整段
    UTF-16LE，所以直接解出来再切行，比逐字节猜要准得多。
    """
    try:
        u16 = _runs_to_lines(wd.decode("utf-16-le", "ignore"))
    except Exception:
        u16 = []
    text16 = "\n".join(u16)

    # 压缩片段（8-bit GBK）的情况：只在 UTF-16 读不出东西时才用它
    text_gbk = ""
    if len(text16) < 200:
        try:
            gbk = _runs_to_lines(wd.decode("gb18030", "ignore"))
        except Exception:
            gbk = []
        text_gbk = "\n".join(gbk)

    best = text16 if len(text16) >= len(text_gbk) else text_gbk
    return _clean_doc_text(best)


def parse_doc(data: bytes, name: str = "") -> ParsedFile:
    out = ParsedFile(name=name, kind="doc")
    try:
        ole = OleFile(data)
    except ValueError as e:
        # 有些「.doc」其实是 RTF / HTML / 纯文本
        head = data[:1024].lstrip()
        if head.startswith(b"{\\rtf"):
            out.parser = "rtf-stdlib"
            out.text = _clean_doc_text(rtf_to_text(data.decode("latin-1", "ignore")))
            out.note = "扩展名是 .doc，实际是 RTF"
            return out
        if b"<html" in head.lower() or head.startswith(b"<?xml"):
            out.parser = "html-stdlib"
            out.text = html_to_text(data.decode("utf-8", "ignore"))
            out.note = "扩展名是 .doc，实际是 HTML"
            return out
        out.error = str(e)
        return out
    if "WordDocument" not in ole.names():
        out.error = "OLE2 里没有 WordDocument 流（可能是 .xls 或 .ppt 改名）"
        return out
    out.parser = "ole2-word"
    text, how = _doc_piece_table(ole)
    out.text = text
    out.extra["method"] = how
    if how == "scan":
        out.note = "片段表不可用，已按可见文本扫描（可能漏字）"
    # 内嵌图片（WordDocument 里的 Data 流或 1Table 的图片偏移不好定位，
    # 这里只在有 .doc 内嵌 PNG/JPEG 时顺手取出）
    imgs = _ole_embedded_images(ole)
    if imgs:
        out.images = imgs
    if not out.text.strip() and out.images:
        out.note = "正文为空，内容可能在图片里"
    return out


def _ole_embedded_images(ole: OleFile, *, max_images: int = 10) -> list[dict]:
    """OLE2 里找内嵌图片：PNG/JPEG 魔数扫描（够用，且不依赖图形库）。"""
    out: list[dict] = []
    seen: set[str] = set()
    streams = [n for n in ole.names() if n not in ("WordDocument", "1Table", "0Table")]
    for name in ["\x01Ole10Native", "Data"] + streams:
        if len(out) >= max_images:
            break
        try:
            raw = ole.stream(name)
        except Exception:
            continue
        if not raw:
            continue
        for m in re.finditer(rb"\xff\xd8\xff", raw):
            start = m.start()
            end = raw.find(b"\xff\xd9", start)
            if end > start + 2048:
                blob = raw[start:end + 2]
                import hashlib

                h = hashlib.sha1(blob).hexdigest()
                if h not in seen:
                    seen.add(h)
                    out.append({"name": f"{name}-{start}.jpg", "data": blob,
                                "size": len(blob), "path": name})
            if len(out) >= max_images:
                break
        for m in re.finditer(rb"\x89PNG\r\n\x1a\n", raw):
            start = m.start()
            end = raw.find(b"IEND", start)
            if end > start + 512:
                blob = raw[start:end + 8]
                import hashlib

                h = hashlib.sha1(blob).hexdigest()
                if h not in seen:
                    seen.add(h)
                    out.append({"name": f"{name}-{start}.png", "data": blob,
                                "size": len(blob), "path": name})
            if len(out) >= max_images:
                break
    return out


# ---- .xls：BIFF8 ----
def _biff_records(data: bytes) -> list[tuple[int, bytes]]:
    out: list[tuple[int, bytes]] = []
    pos = 0
    n = len(data)
    while pos + 4 <= n:
        rid, size = struct.unpack_from("<HH", data, pos)
        body = data[pos + 4:pos + 4 + size]
        if len(body) < size:
            break
        out.append((rid, body))
        pos += 4 + size
    return out


def _xls_sst(records: list[tuple[int, bytes]], start: int) -> list[str]:
    """拼出 SST（共享字符串表），CONTINUE(0x3C) 的记录要续上。

    布局：[总条数 u32][唯一条数 u32] 之后是「XLUnicodeRichExtendedString」串：
    [cch u8][flags u8][可选 cRun u16][可选 cbExtRst u32][字符数据]。
    cch 只占 1 字节（BIFF8 里 SST 串长度上限 255），这一点很容易写错成 u16。
    """
    if start < 0 or start >= len(records) or records[start][0] != 0x00FC:
        return []
    buf = bytearray(records[start][1])
    i = start + 1
    while i < len(records) and records[i][0] == 0x003C:
        buf += records[i][1]
        i += 1
    raw = bytes(buf)
    if len(raw) < 9:
        return []
    total = struct.unpack_from("<I", raw, 4)[0]
    strings: list[str] = []
    pos = 8
    for _ in range(min(total, 200_000)):
        if pos + 3 > len(raw):
            break
        cch = raw[pos]
        flags = raw[pos + 1]
        pos += 2
        rich = flags & 0x08
        far_east = flags & 0x04
        nrun = 0
        if rich:
            if pos + 2 > len(raw):
                break
            nrun = struct.unpack_from("<H", raw, pos)[0]
            pos += 2
        ext = 0
        if far_east:
            if pos + 4 > len(raw):
                break
            ext = struct.unpack_from("<I", raw, pos)[0]
            pos += 4
        if flags & 0x01:                                   # 宽字符（UTF-16LE）
            nbytes = cch * 2
            strings.append(raw[pos:pos + nbytes].decode("utf-16-le", "ignore"))
        else:
            strings.append(raw[pos:pos + cch].decode("latin-1", "ignore"))
        pos += cch * 2 if flags & 0x01 else cch
        pos += nrun * 4
        pos += ext
    return strings


def _xls_cell_value(rid: int, body: bytes, sst: list[str]) -> str:
    try:
        if rid == 0x00FD:                                  # LABELSST
            idx = struct.unpack_from("<I", body, 6)[0]
            return sst[idx] if 0 <= idx < len(sst) else ""
        if rid == 0x0204:                                  # LABEL（BIFF8 里少见）
            cch = struct.unpack_from("<H", body, 6)[0]
            flags = body[8]
            raw = body[9:]
            return (raw[:cch * 2].decode("utf-16-le", "ignore") if flags & 0x01
                    else raw[:cch].decode("latin-1", "ignore"))
        if rid == 0x0203:                                  # NUMBER
            return _num_text(struct.unpack_from("<d", body, 6)[0])
        if rid == 0x027E:                                  # RK
            return _num_text(_rk_value(struct.unpack_from("<I", body, 6)[0]))
        if rid in (0x0006, 0x0406):                        # FORMULA
            return _num_text(struct.unpack_from("<d", body, 6)[0])
        if rid == 0x00BD:                                  # MULRK
            cells = []
            n = (len(body) - 6) // 6
            for i in range(n):
                rk = struct.unpack_from("<I", body, 6 + i * 6 + 2)[0]
                cells.append(_num_text(_rk_value(rk)))
            return " ".join(c for c in cells if c)
        if rid == 0x0201:                                  # BLANK
            return ""
        if rid == 0x00BE:                                  # MULBLANK
            return ""
        if rid == 0x0007:                                  # STRING（公式结果）
            cch = struct.unpack_from("<H", body, 0)[0]
            flags = body[2] if len(body) > 2 else 0
            raw = body[3:]
            return (raw[:cch * 2].decode("utf-16-le", "ignore") if flags & 0x01
                    else raw[:cch].decode("latin-1", "ignore"))
        if rid == 0x0207:                                  # DBCELL：不是数据
            return ""
    except Exception:
        return ""
    return ""


def _rk_value(rk: int) -> float:
    if rk & 0x02:
        v = float(rk >> 2)
    else:
        v = struct.unpack("<d", struct.pack("<Q", (rk & 0xFFFFFFFC) << 32))[0]
    return v / 100.0 if rk & 0x01 else v


def _num_text(v: float) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v == int(v) and abs(v) < 1e15:
        return str(int(v))
    return f"{v:g}"


def _xls_sheet_names(records: list[tuple[int, bytes]]) -> list[str]:
    """读 BOUNDSHEET(0x0085)：[lbPlyPos u32][grbit u8][cch u8][grbitName u8][名字]。"""
    names: list[str] = []
    at = next((i for i, (rid, _) in enumerate(records) if rid == 0x0085), -1)
    if at < 0:
        return names
    for rid, body in records[at:]:
        if rid != 0x0085:
            break
        if len(body) < 8:
            continue
        cch = body[5]
        unicode_name = bool(body[6] & 0x01)
        raw = body[7:]
        if unicode_name:
            names.append(raw[:cch * 2].decode("utf-16-le", "ignore"))
        else:
            names.append(raw[:cch].decode("latin-1", "ignore"))
    return names


def _xls_sheets(records: list[tuple[int, bytes]], sst: list[str]
                ) -> list[tuple[str, list[list[str]]]]:
    """把单元格按工作表分组：BOF(0x0809) 的 DT 字段区分「全局/工作表/图表」。"""
    names = _xls_sheet_names(records)
    sheets: list[tuple[str, list[list[str]]]] = []
    current: list[list[str]] | None = None
    cur_row: dict[int, str] = {}

    def flush_row() -> None:
        nonlocal cur_row
        if current is not None and cur_row:
            width = max(cur_row) + 1
            current.append([cur_row.get(i, "") for i in range(min(width, 256))])
        cur_row = {}

    def close_sheet() -> None:
        nonlocal current
        flush_row()
        if current is not None:
            sheets.append((names[len(sheets)] if len(sheets) < len(names)
                           else f"Sheet{len(sheets) + 1}", current))
        current = None

    for rid, body in records:
        if rid == 0x0809:                                   # BOF
            dt = struct.unpack_from("<H", body, 2)[0] if len(body) >= 4 else 0x0010
            # 0x0005 = workbook globals，0x0010 = worksheet，0x0020 = chart，0x0040 = macro
            if dt in (0x0010, 0x0020, 0x0040):
                close_sheet()
                current = []
            continue
        if rid == 0x000A:                                   # EOF
            if current is not None:
                close_sheet()
            continue
        if current is None:
            continue                                    # 还在 globals 区
        if rid == 0x0208:                               # ROW
            flush_row()
            continue
        if rid == 0x00BD:                               # MULRK：一行多列
            try:
                base = struct.unpack_from("<H", body, 0)[0]
                n = (len(body) - 6) // 6
                for i in range(n):
                    rk = struct.unpack_from("<I", body, 6 + i * 6 + 2)[0]
                    cur_row[base + i] = _num_text(_rk_value(rk))
            except Exception:
                pass
            continue
        val = _xls_cell_value(rid, body, sst)
        if val:
            col = struct.unpack_from("<H", body, 2)[0] if len(body) >= 4 else 0
            cur_row[col] = val
    close_sheet()
    return sheets


def parse_xls(data: bytes, name: str = "") -> ParsedFile:
    out = ParsedFile(name=name, kind="xls")
    try:
        ole = OleFile(data)
    except ValueError as e:
        out.error = str(e)
        return out
    stream_name = "Workbook" if "Workbook" in ole.names() else (
        "Book" if "Book" in ole.names() else "")
    if not stream_name:
        out.error = "OLE2 里没有 Workbook/Book 流"
        return out
    out.parser = "ole2-biff"
    book = ole.stream(stream_name)
    records = _biff_records(book)
    sst_at = next((i for i, (rid, _) in enumerate(records) if rid == 0x00FC), -1)
    sst = _xls_sst(records, sst_at) if sst_at >= 0 else []
    out.extra["sst"] = len(sst)
    sheets = _xls_sheets(records, sst)
    chunks: list[str] = []
    for title, rows in sheets:
        if not rows:
            continue
        out.tables.append(rows)
        chunks.append(f"===== 工作表：{title} =====")
        chunks.extend(" | ".join(r) for r in rows[:4000])
    out.text = "\n".join(chunks)[:MAX_TEXT_CHARS]
    if not out.text.strip():
        out.note = "BIFF 里没读到单元格（可能是加密或不含数据的空表）"
    # 内嵌图片
    for n in ole.names():
        if n in ("Workbook", "Book", "\x05SummaryInformation"):
            continue
    return out


def parse_rtf(text: str) -> str:
    return _clean_doc_text(rtf_to_text(text))


def rtf_to_text(raw: str) -> str:
    """极简 RTF → 文本。

    两个坑：
      · 中文在 RTF 里是**多个连续的 \\'xx 字节**（GBK 双字节），必须把它们攒起来
        一起解码；一个一个解会得到 `»ªÄÏÅ©Òµ` 这种乱码。
      · `\\uNNNN` 是 Unicode 转义，后面的 `?` 是给不理解该控制字的阅读器的占位符，要去掉。
    """
    def hex_seq(m) -> str:
        blob = bytes(int(b, 16) for b in re.findall(r"\\'([0-9a-fA-F]{2})", m.group(0)))
        for enc in ("gb18030", "big5", "cp1252"):
            try:
                return blob.decode(enc)
            except UnicodeDecodeError:
                continue
        return blob.decode("latin-1", "ignore")

    raw = re.sub(r"(?:\\'[0-9a-fA-F]{2})+", hex_seq, raw)
    raw = re.sub(r"\\u(-?\d+)\s?\??", lambda m: chr(int(m.group(1)) & 0xFFFF), raw)
    raw = re.sub(r"\\par[d]?\b", "\n", raw)
    raw = re.sub(r"\\cell\b", "\t", raw)
    raw = re.sub(r"\\row\b", "\n", raw)
    raw = re.sub(r"\\tab\b", "\t", raw)
    raw = re.sub(r"\\[a-zA-Z]+-?\d*\s?", "", raw)
    raw = raw.replace("\\{", "{").replace("\\}", "}").replace("\\\\", "\\")
    raw = raw.replace("{", "").replace("}", "")
    raw = re.sub(r"[ \t]*\n[ \t]*", "\n", raw)
    return re.sub(r"\n{3,}", "\n\n", raw).strip()


def _rtf_hex(hex_pair: str) -> str:
    """单个 \\'xx 的解码（保留给外部引用；多字节请走 rtf_to_text 的批量路径）。"""
    b = bytes([int(hex_pair, 16)])
    for enc in ("gb18030", "cp1252"):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            continue
    return ""


def html_to_text(html: str) -> str:
    html = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", html)
    html = re.sub(r"(?i)<br\s*/?>", "\n", html)
    html = re.sub(r"(?i)</(p|div|tr|li|h[1-6])>", "\n", html)
    html = re.sub(r"(?i)</t[dh]>", "\t", html)
    html = re.sub(r"<[^>]+>", "", html)
    import html as htmlmod

    out = htmlmod.unescape(html)
    out = re.sub(r"[ \t]*\n[ \t]*", "\n", out)
    return re.sub(r"\n{3,}", "\n\n", out).strip()


# --------------------------------------------------------------------------- #
# 四、压缩包
# --------------------------------------------------------------------------- #
def parse_archive(data: bytes, name: str = "", *, depth: int = 0,
                  max_entries: int = 20, max_bytes: int = 40_000_000) -> ParsedFile:
    out = ParsedFile(name=name, kind=ext_of(name) or "zip")
    try:
        zf = _zip_open(data)
    except zipfile.BadZipFile:
        out.error = "压缩包无法打开（不是 zip，或是分卷/加密 rar/7z）"
        out.note = "如需解析 rar/7z 请先手动解压后作为附件上传"
        return out
    with zf:
        out.parser = "zip-stdlib"
        infos = [i for i in zf.infolist() if not i.is_dir()]
        # 防 zip 炸弹：条目数与解压总量都要设上限
        if len(infos) > 2000:
            infos = infos[:2000]
            out.note = "压缩包条目过多，只解析前 2000 个"
        total = 0
        subs: list[tuple[str, ParsedFile]] = []
        for info in infos[:max_entries]:
            inner = PurePosixPath(info.filename)
            if inner.is_absolute() or ".." in inner.parts:
                continue                                    # 防路径穿越
            if info.file_size > 20_000_000:
                continue
            total += info.file_size
            if total > max_bytes:
                out.note = (out.note + "；" if out.note else "") + "压缩包过大，只解析了前几个文件"
                break
            if not is_parseable(info.filename):
                continue
            try:
                blob = zf.read(info.filename)
            except Exception:
                continue
            sub = parse_bytes(blob, info.filename, depth=depth + 1)
            if sub.has_content:
                subs.append((info.filename, sub))
            if len(sub.images) and len(out.images) < 20:
                out.images.extend(sub.images[:20 - len(out.images)])
        chunks = []
        for path, sub in subs:
            chunks.append(f"----- 压缩包内文件：{path} -----")
            if sub.text.strip():
                chunks.append(sub.text)
            if sub.ocr_chars:
                out.ocr_chars += sub.ocr_chars
                out.ocr_used += sub.ocr_used
        out.text = "\n\n".join(chunks)[:MAX_TEXT_CHARS]
        for _, sub in subs:
            out.tables.extend(sub.tables[:4])
        names = [i.filename for i in infos[:max_entries]]
        out.extra["entries"] = names
        if not chunks:
            out.note = (out.note + "；" if out.note else "") + (
                "包里没有可解析的文档（" + "、".join(names[:6]) + "）")
    return out


# --------------------------------------------------------------------------- #
# 五、图片 / 纯文本
# --------------------------------------------------------------------------- #
def parse_image(data: bytes, name: str = "", *, use_ocr: bool = True) -> ParsedFile:
    out = ParsedFile(name=name, kind=ext_of(name) or "png")
    out.parser = "image"
    payload = ocrmod.prepare_image(data, name=name)
    out.images = [{"name": name or "image", "data": data, "size": len(data)}]
    out.extra["image_size"] = (payload.width, payload.height)
    if payload.error:
        out.note = payload.error
    if not use_ocr:
        return out
    if not ocrmod.enabled():
        out.note = (out.note + "；" if out.note else "") + \
            "未配置 OCR，图片里的文字没有提取（设置 → OCR 里填百度 OCR Key）"
        return out
    res = ocrmod.recognize_image(payload.data or data, name=name)
    if res.error:
        out.note = (out.note + "；" if out.note else "") + res.error
    elif res.text.strip():
        out.text = res.text
        out.ocr_used = 1
        out.ocr_chars = len(res.text)
    else:
        out.note = (out.note + "；" if out.note else "") + "OCR 未识别到文字"
    return out


def parse_text(data: bytes, name: str = "") -> ParsedFile:
    out = ParsedFile(name=name, kind=ext_of(name) or "txt")
    out.parser = "text"
    text, enc = _decode_text(data)
    if ext_of(name) in ("htm", "html"):
        out.parser = "html-stdlib"
        text = html_to_text(text)
    out.text = text[:MAX_TEXT_CHARS]
    out.extra["encoding"] = enc
    return out


def _decode_text(data: bytes) -> tuple[str, str]:
    for enc in ("utf-8-sig", "utf-8", "gb18030", "big5", "cp1252"):
        try:
            return data.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", "ignore"), "utf-8(replace)"


# --------------------------------------------------------------------------- #
# 六、可选的 LibreOffice 加速（.doc/.xls/.ppt 转文本）
# --------------------------------------------------------------------------- #
_LO_KIT: tuple[str, str] | None | bool = None


def _libreoffice_kit() -> tuple[str, str] | None:
    """探测 DSH 自带的 libreoffice-kit（node + cli）。找不到返回 None。"""
    global _LO_KIT
    if _LO_KIT is not None:
        return _LO_KIT or None
    import os
    import shutil
    import sys

    node = shutil.which("node") or ""
    candidates = [
        Path(r"D:\Program Files\DeepSeek Harness\resources\runtime\primary-runtime"
             r"\dependencies\node\bin\node.exe"),
    ]
    if not node:
        for c in candidates:
            if c.is_file():
                node = str(c)
                break
    cli = ""
    for base in _kit_bases():
        p = base / "lib" / "cli.js"
        if p.is_file():
            cli = str(p)
            break
    if node and cli and os.name == "nt":
        _LO_KIT = (node, cli)
        return _LO_KIT
    _LO_KIT = False
    return None


def _kit_bases():
    import os

    env = os.environ.get("DSH_LIBREOFFICE_KIT", "")
    if env:
        yield Path(env)
    for root in (os.environ.get("DSH_RESOURCES_DIR", ""),
                 r"D:\Program Files\DeepSeek Harness\resources"):
        if not root:
            continue
        yield Path(root) / "app.asar.unpacked" / "dsh" / "node_modules" / "@deepseek-ai" / "libreoffice-kit"
        yield Path(root) / "runtime" / "app.asar.unpacked" / "dsh" / "node_modules" / "@deepseek-ai" / "libreoffice-kit"


def libreoffice_available() -> bool:
    return _libreoffice_kit() is not None


def convert_with_libreoffice(data: bytes, name: str, target: str = "txt") -> str:
    """用自带的 LibreOffice 转换（.doc/.xls/.ppt → txt/csv）。失败返回 ""。

    这条路径只在解析器自己搞不定时作为补充：它需要 node 子进程与临时目录，
    在受限环境里不一定可用，所以任何异常都静默退化为内置解析器。
    """
    kit = _libreoffice_kit()
    if not kit:
        return ""
    import os
    import shutil
    import subprocess
    import tempfile

    node, cli = kit
    ext = ext_of(name) or "bin"
    tmp = Path(tempfile.mkdtemp(prefix="scau-lo-"))
    try:
        src = tmp / f"in.{ext}"
        src.write_bytes(data)
        outdir = tmp / "out"
        outdir.mkdir()
        cmd = [node, cli, "convert", "--input", str(src),
               "--output", str(outdir / f"in.{target}")]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        cand = outdir / f"in.{target}"
        if proc.returncode == 0 and cand.is_file():
            raw = cand.read_bytes()
            text, _ = _decode_text(raw)
            return text
        return ""
    except Exception:
        return ""
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# --------------------------------------------------------------------------- #
# 七、入口
# --------------------------------------------------------------------------- #
def parse_bytes(data: bytes, name: str = "", *, depth: int = 0,
                use_ocr: bool = True) -> ParsedFile:
    """按扩展名 + 魔数分派解析。永不抛异常，失败写进 error/note。"""
    name = name or ""
    ext = ext_of(name)
    res: ParsedFile
    try:
        if not data:
            return ParsedFile(name=name, kind=ext, error="空文件")
        head = data[:8]
        # 魔数优先：扩展名骗人的附件太多了（.doc 实际是 zip/rtf/html 很常见）
        if head[:4] == b"%PDF":
            res = parse_pdf(data, name)
        elif head[:4] == b"PK\x03\x04":
            if ext in OFFICE_WORD or ext == "":
                inner = _ooxml_kind(data)
                res = (parse_docx(data, name) if inner == "word"
                       else parse_xlsx(data, name) if inner == "sheet"
                       else parse_pptx(data, name) if inner == "slide"
                       else parse_archive(data, name, depth=depth))
            elif ext in OFFICE_SHEET:
                res = parse_xlsx(data, name)
            elif ext in OFFICE_SLIDE:
                res = parse_pptx(data, name)
            else:
                res = parse_archive(data, name, depth=depth)
        elif head[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
            if ext in OFFICE_SHEET:
                res = parse_xls(data, name)
            elif ext in OFFICE_SLIDE:
                res = _parse_ole_ppt(data, name)
            elif ext in OFFICE_WORD or ext in ("", "ppt", "xls"):
                res = parse_doc(data, name)
            else:
                res = parse_doc(data, name)
        elif ext in ("doc", "xls", "ppt") and ext != "":
            # 不是 OLE2 也不是 zip：多半是 RTF/HTML/TXT 改了名
            res = parse_doc(data, name)
        elif ext == "rtf" or data[:5] == b"{\\rtf":
            res = ParsedFile(name=name, kind="rtf", parser="rtf-stdlib",
                             text=rtf_to_text(data.decode("latin-1", "ignore"))[:MAX_TEXT_CHARS])
        elif ext in ("htm", "html") or b"<html" in data[:2048].lower():
            res = parse_text(data, name or "page.html")
        elif is_image(name, data):
            res = parse_image(data, name, use_ocr=use_ocr)
        elif ext in ("csv",):
            res = parse_csv(data, name)
        elif ext in TEXT_EXT or ext == "":
            res = parse_text(data, name)
        else:
            res = ParsedFile(name=name, kind=ext,
                             note=f"暂不支持解析 .{ext} 格式（文件已保存，可在原文里查看）")
    except Exception as e:                                   # noqa: BLE001
        res = ParsedFile(name=name, kind=ext, error=f"{type(e).__name__}: {e}")
    res.name = res.name or name
    res.kind = res.kind or ext
    res.bytes = len(data)
    # 图片 OCR：正文解析完之后统一补一次（docx/xlsx/pptx/zip 里的内嵌图）
    if use_ocr and res.images and not res.error and not _is_pure_image(res):
        _ocr_embedded(res)
    return res


def _is_pure_image(res: ParsedFile) -> bool:
    return res.parser == "image"


def _ooxml_kind(data: bytes) -> str:
    try:
        with _zip_open(data) as zf:
            names = set(zf.namelist())
    except Exception:
        return ""
    if "word/document.xml" in names:
        return "word"
    if "xl/workbook.xml" in names:
        return "sheet"
    if any(n.startswith("ppt/slides/slide") for n in names):
        return "slide"
    return ""


def _parse_ole_ppt(data: bytes, name: str) -> ParsedFile:
    """老 .ppt：先试 LibreOffice，再退化为「扫可见文本」。"""
    out = ParsedFile(name=name, kind="ppt")
    text = convert_with_libreoffice(data, name, "txt")
    if text.strip():
        out.parser = "libreoffice"
        out.text = text[:MAX_TEXT_CHARS]
        return out
    try:
        ole = OleFile(data)
    except ValueError as e:
        out.error = str(e)
        return out
    out.parser = "ole2-ppt-scan"
    chunks: list[str] = []
    for n in ole.names():
        if n in ("PowerPoint Document", "Pictures"):
            continue
        try:
            raw = ole.stream(n)
        except Exception:
            continue
        if len(raw) < 64:
            continue
        t = _doc_scan_text(raw)
        if len(t) > 40:
            chunks.append(t)
    out.text = "\n".join(chunks)[:MAX_TEXT_CHARS]
    out.note = "老版 .ppt 只能扫出可见文本；分页与表格结构丢失（装了 LibreOffice 会更准）"
    out.images = _ole_embedded_images(ole)
    return out


def parse_csv(data: bytes, name: str = "") -> ParsedFile:
    import csv as csvmod

    out = ParsedFile(name=name, kind="csv", parser="csv-stdlib")
    text, enc = _decode_text(data)
    out.extra["encoding"] = enc
    rows: list[list[str]] = []
    try:
        for row in csvmod.reader(io.StringIO(text)):
            vals = [c.strip() for c in row]
            while vals and not vals[-1]:
                vals.pop()
            if any(vals):
                rows.append(vals)
    except Exception:
        rows = [[ln] for ln in text.splitlines() if ln.strip()]
    out.tables = [rows] if rows else []
    chunks = [" | ".join(r) for r in rows[:4000]]
    out.text = "\n".join(chunks)[:MAX_TEXT_CHARS]
    return out


_OCR_EMBED_MAX = 8


def _ocr_embedded(res: ParsedFile) -> None:
    """对解析出来的内嵌图片跑 OCR，把文字追加到正文。"""
    if not res.images or not ocrmod.enabled():
        if res.images and not ocrmod.enabled():
            res.note = (res.note + "；" if res.note else "") + \
                f"有 {len(res.images)} 张内嵌图片，未配置 OCR 所以没提取图里的文字"
        return
    picked = [im for im in res.images if int(im.get("size") or len(im.get("data") or b"")) >= 3000]
    if not picked:
        picked = res.images[:2]
    chunks: list[str] = []
    for im in picked[:_OCR_EMBED_MAX]:
        data = im.get("data") or b""
        if not data:
            continue
        r = ocrmod.recognize_image(data, name=str(im.get("name") or ""))
        if r.ok:
            res.ocr_used += 1
            res.ocr_chars += len(r.text)
            chunks.append(f"[图片 OCR：{im.get('name', '')}]\n{r.text}")
        elif r.error and not res.note:
            res.note = r.error
    if chunks:
        res.add_text("\n\n".join(chunks))
    elif res.images and not res.note:
        res.note = f"有 {len(res.images)} 张内嵌图片，OCR 没识别到文字"


def parse_path(path: str | Path, *, use_ocr: bool = True) -> ParsedFile:
    p = Path(path)
    return parse_bytes(p.read_bytes(), p.name, use_ocr=use_ocr)


def supported_extensions() -> list[str]:
    return sorted(PARSEABLE_EXT)
