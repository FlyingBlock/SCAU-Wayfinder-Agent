"""纯标准库 PDF 文本抽取（FlateDecode / LZW / ASCIIHex / RunLength + ToUnicode CMap）。

为什么自己写而不是装 pypdf/pdfminer：本项目的运行环境（以及 clone 后的部署环境）
只保证有 Python 标准库 + 少数几个 Office 库，`pip install` 在离线/受限环境里不可用。
学校通知的附件又几乎全是 PDF，所以这一层必须自带。

覆盖范围（按重要性）：
  · 交叉引用表与交叉引用流（PDF 1.5+）、对象流（ObjStm）
  · 流过滤器：FlateDecode（含 PNG/TIFF Predictor）、LZWDecode、ASCIIHexDecode、
    ASCII85Decode、RunLengthDecode
  · 字体：/ToUnicode CMap（bfchar / bfrange，含 `array` 形式）、简单字体的
    /Encoding（WinAnsiEncoding / MacRomanEncoding / Differences）、
    Identity-H/V 与预定义 CJK CMap（GBK-EUC-H、UniGB-UCS2-H …）
  · 内容流：BT/ET、Tf/Td/TD/Tm/T*/TJ/Tj/'/"、XObject Form 递归
  · 扫描件（整页只有一张图）判为「无文本层」，交给 OCR（见 harness/ocr.py）

已知不做的：Type3 字形、加密 PDF（仅识别并如实报错）、竖排字距细节。
"""
from __future__ import annotations

import re
import struct
import zlib
from dataclasses import dataclass, field

# --------------------------------------------------------------------------- #
# 一、对象层：词法 + 交叉引用
# --------------------------------------------------------------------------- #
WHITESPACE = b"\x00\t\n\x0c\r "
DELIMS = b"()<>[]{}/%"


class PdfError(Exception):
    """PDF 结构层面的错误（加密、损坏、非 PDF）。"""


@dataclass
class Ref:
    num: int
    gen: int = 0

    def __hash__(self) -> int:
        return hash((self.num, self.gen))


def _is_ws(c: int) -> bool:
    return c in (0, 9, 10, 12, 13, 32)


def _is_delim(c: int) -> bool:
    return c in (0x28, 0x29, 0x3C, 0x3E, 0x5B, 0x5D, 0x7B, 0x7D, 0x2F, 0x25)


class Lexer:
    """极简 PDF 对象词法器。"""

    def __init__(self, data: bytes, pos: int = 0) -> None:
        self.data = data
        self.pos = pos

    def skip_ws(self, comments: bool = True) -> None:
        d, n = self.data, len(self.data)
        while self.pos < n:
            c = d[self.pos]
            if _is_ws(c):
                self.pos += 1
            elif comments and c == 0x25:                 # %
                while self.pos < n and d[self.pos] not in (10, 13):
                    self.pos += 1
            else:
                break

    def parse(self):
        """解析下一个对象（dict / list / bytes / str / number / name / bool / None）。"""
        self.skip_ws()
        d, n = self.data, len(self.data)
        if self.pos >= n:
            return None
        c = d[self.pos]
        if c == 0x2F:                                    # /
            return self._name()
        if c == 0x28:                                    # (
            return self._literal_string()
        if c == 0x3C:                                    # < or <<
            if self.pos + 1 < n and d[self.pos + 1] == 0x3C:
                return self._dict()
            return self._hex_string()
        if c == 0x5B:                                    # [
            return self._array()
        if c in b"+-.0123456789":
            return self._number_or_ref()
        word = self._word()
        if word == b"true":
            return True
        if word == b"false":
            return False
        if word == b"null":
            return None
        return Keyword(word)                             # obj / endobj / stream / R …

    # ---- 基本类型 ----
    def _word(self) -> bytes:
        d, n, s = self.data, len(self.data), self.pos
        while self.pos < n and not _is_ws(d[self.pos]) and not _is_delim(d[self.pos]):
            self.pos += 1
        return d[s:self.pos]

    def _name(self) -> str:
        self.pos += 1
        raw = self._word()
        out = bytearray()
        i = 0
        while i < len(raw):
            if raw[i] == 0x23 and i + 2 < len(raw):      # #xx 转义
                try:
                    out.append(int(raw[i + 1:i + 3], 16))
                    i += 3
                    continue
                except ValueError:
                    pass
            out.append(raw[i])
            i += 1
        return out.decode("latin-1")

    def _literal_string(self) -> bytes:
        d, n = self.data, len(self.data)
        self.pos += 1
        out = bytearray()
        depth = 1
        while self.pos < n:
            c = d[self.pos]
            self.pos += 1
            if c == 0x5C:                                # 反斜杠
                if self.pos >= n:
                    break
                e = d[self.pos]
                self.pos += 1
                if e in b"nrtbf":
                    out.append({0x6E: 10, 0x72: 13, 0x74: 9, 0x62: 8, 0x66: 12}[e])
                elif e in b"01234567":
                    oct_digits = bytes([e])
                    while len(oct_digits) < 3 and self.pos < n and d[self.pos] in b"01234567":
                        oct_digits += bytes([d[self.pos]])
                        self.pos += 1
                    out.append(int(oct_digits, 8) & 0xFF)
                elif e in (10, 13):                      # 行延续
                    if e == 13 and self.pos < n and d[self.pos] == 10:
                        self.pos += 1
                else:
                    out.append(e)
                continue
            if c == 0x28:
                depth += 1
            elif c == 0x29:
                depth -= 1
                if depth == 0:
                    break
            out.append(c)
        return bytes(out)

    def _hex_string(self) -> bytes:
        d, n = self.data, len(self.data)
        self.pos += 1
        s = self.pos
        while self.pos < n and d[self.pos] != 0x3E:
            self.pos += 1
        h = re.sub(rb"[^0-9A-Fa-f]", b"", d[s:self.pos])
        self.pos += 1
        if len(h) % 2:
            h += b"0"
        try:
            return bytes.fromhex(h.decode("ascii"))
        except ValueError:
            return b""

    def _array(self) -> list:
        self.pos += 1
        out: list = []
        while True:
            self.skip_ws()
            if self.pos >= len(self.data):
                break
            if self.data[self.pos] == 0x5D:
                self.pos += 1
                break
            out.append(self.parse())
        return out

    def _dict(self) -> dict:
        self.pos += 2
        out: dict = {}
        while True:
            self.skip_ws()
            if self.pos >= len(self.data):
                break
            if self.data[self.pos] == 0x3E:
                self.pos += 1
                if self.pos < len(self.data) and self.data[self.pos] == 0x3E:
                    self.pos += 1
                break
            key = self.parse()
            if not isinstance(key, str):
                if isinstance(key, Keyword):
                    continue
                break
            out[key] = self.parse()
        return out

    def _number_or_ref(self):
        d, n = self.data, len(self.data)
        s = self.pos
        while self.pos < n and (d[self.pos] in b"+-.0123456789"):
            self.pos += 1
        raw = d[s:self.pos]
        if b"." in raw:
            try:
                return float(raw)
            except ValueError:
                return 0.0
        try:
            value = int(raw)
        except ValueError:
            return 0.0
        # 可能是「num gen R」形式的间接引用
        save = self.pos
        self.skip_ws(comments=False)
        s2 = self.pos
        while self.pos < n and d[self.pos] in b"0123456789":
            self.pos += 1
        if self.pos > s2:
            try:
                gen = int(d[s2:self.pos])
            except ValueError:
                gen = -1
            self.skip_ws(comments=False)
            if self.pos < n and d[self.pos] == 0x52 and (
                    self.pos + 1 >= n or _is_ws(d[self.pos + 1]) or _is_delim(d[self.pos + 1])):
                self.pos += 1
                return Ref(value, gen)
        self.pos = save
        return value


@dataclass
class Keyword:
    text: bytes

    def __repr__(self) -> str:                            # pragma: no cover - 调试用
        return "Keyword(%r)" % self.text


@dataclass
class Stream:
    dict: dict
    raw: bytes

    def data(self) -> bytes:
        return decode_stream(self.raw, self.dict)


# --------------------------------------------------------------------------- #
# 二、流过滤器
# --------------------------------------------------------------------------- #
def _apply_predictor(data: bytes, parms: dict) -> bytes:
    pred = int(parms.get("Predictor") or 1)
    if pred <= 1:
        return data
    colors = int(parms.get("Colors") or 1)
    bpc = int(parms.get("BitsPerComponent") or 8)
    columns = int(parms.get("Columns") or 1)
    bpp = max(1, (colors * bpc + 7) // 8)
    row_len = (columns * colors * bpc + 7) // 8
    if pred == 2:
        if bpc != 8:
            return data
        out = bytearray(data)
        for r in range(0, len(out) - row_len + 1, row_len):
            for i in range(bpp, row_len):
                out[r + i] = (out[r + i] + out[r + i - bpp]) & 0xFF
        return bytes(out)
    # PNG 预测器：每行前面多一个 filter type 字节
    out = bytearray()
    prev = bytearray(row_len)
    pos = 0
    while pos + 1 + row_len <= len(data) + row_len:
        if pos >= len(data):
            break
        ft = data[pos]
        row = bytearray(data[pos + 1:pos + 1 + row_len])
        if len(row) < row_len:
            row.extend(b"\x00" * (row_len - len(row)))
        pos += 1 + row_len
        if ft == 1:
            for i in range(bpp, row_len):
                row[i] = (row[i] + row[i - bpp]) & 0xFF
        elif ft == 2:
            for i in range(row_len):
                row[i] = (row[i] + prev[i]) & 0xFF
        elif ft == 3:
            for i in range(row_len):
                left = row[i - bpp] if i >= bpp else 0
                row[i] = (row[i] + ((left + prev[i]) >> 1)) & 0xFF
        elif ft == 4:
            for i in range(row_len):
                a = row[i - bpp] if i >= bpp else 0
                b = prev[i]
                c = prev[i - bpp] if i >= bpp else 0
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                row[i] = (row[i] + pr) & 0xFF
        out.extend(row)
        prev = row
    return bytes(out)


def _lzw_decode(data: bytes, early: int = 1) -> bytes:
    out = bytearray()
    table: list[bytes] = [bytes([i]) for i in range(256)] + [b"", b""]
    bitpos = 0
    codelen = 9
    prev: bytes | None = None

    def read_code(width: int) -> int | None:
        nonlocal bitpos
        if bitpos + width > len(data) * 8:
            return None
        code = 0
        for _ in range(width):
            byte = data[bitpos >> 3]
            bit = (byte >> (7 - (bitpos & 7))) & 1
            code = (code << 1) | bit
            bitpos += 1
        return code

    while True:
        code = read_code(codelen)
        if code is None:
            break
        if code == 256:
            table = [bytes([i]) for i in range(256)] + [b"", b""]
            codelen = 9
            prev = None
            continue
        if code == 257:
            break
        if prev is None:
            entry = table[code] if code < len(table) else b""
        elif code < len(table):
            entry = table[code]
            table.append(prev + entry[:1])
        else:
            entry = prev + prev[:1]
            table.append(entry)
        out += entry
        prev = entry
        if len(table) + early >= (1 << codelen) and codelen < 12:
            codelen += 1
    return bytes(out)


def _ascii85(data: bytes) -> bytes:
    data = re.sub(rb"\s", b"", data)
    if data.startswith(b"<~"):
        data = data[2:]
    if data.endswith(b"~>"):
        data = data[:-2]
    out = bytearray()
    group: list[int] = []
    for ch in data:
        if ch == 0x7A and not group:                     # z
            out += b"\x00\x00\x00\x00"
            continue
        if not (0x21 <= ch <= 0x75):
            continue
        group.append(ch - 33)
        if len(group) == 5:
            value = 0
            for g in group:
                value = value * 85 + g
            out += struct.pack(">I", value & 0xFFFFFFFF)
            group = []
    if group:
        pad = 5 - len(group)
        value = 0
        for g in group + [84] * pad:
            value = value * 85 + g
        out += struct.pack(">I", value & 0xFFFFFFFF)[:4 - pad]
    return bytes(out)


def _ascii_hex(data: bytes) -> bytes:
    h = re.sub(rb"[^0-9A-Fa-f]", b"", data.split(b">")[0])
    if len(h) % 2:
        h += b"0"
    try:
        return bytes.fromhex(h.decode("ascii"))
    except ValueError:
        return b""


def _run_length(data: bytes) -> bytes:
    out = bytearray()
    i = 0
    while i < len(data):
        length = data[i]
        i += 1
        if length == 128:
            break
        if length < 128:
            out += data[i:i + length + 1]
            i += length + 1
        else:
            if i < len(data):
                out += bytes([data[i]]) * (257 - length)
                i += 1
    return bytes(out)


def decode_stream(raw: bytes, obj: dict) -> bytes:
    """按 /Filter + /DecodeParms 解码流内容（失败时返回原样，不抛异常）。"""
    filters = obj.get("Filter")
    if filters is None:
        return raw
    if isinstance(filters, str):
        filters = [filters]
    parms = obj.get("DecodeParms") or obj.get("DP")
    if isinstance(parms, dict) or parms is None:
        parms = [parms] * len(filters)
    data = raw
    for i, name in enumerate(filters):
        p = parms[i] if i < len(parms) and isinstance(parms[i], dict) else {}
        try:
            if name in ("FlateDecode", "Fl"):
                data = zlib.decompress(data)
                data = _apply_predictor(data, p)
            elif name in ("LZWDecode", "LZW"):
                data = _lzw_decode(data, int(p.get("EarlyChange") or 1))
                data = _apply_predictor(data, p)
            elif name in ("ASCII85Decode", "A85"):
                data = _ascii85(data)
            elif name in ("ASCIIHexDecode", "AHx"):
                data = _ascii_hex(data)
            elif name in ("RunLengthDecode", "RL"):
                data = _run_length(data)
            elif name in ("DCTDecode", "JPXDecode", "CCITTFaxDecode", "JBIG2Decode"):
                return b""                               # 图像流：不是文本
        except Exception:
            try:
                d = zlib.decompressobj()
                data = d.decompress(data)
                data = _apply_predictor(data, p)
            except Exception:
                return data
    return data


# --------------------------------------------------------------------------- #
# 三、文档：对象收集（xref 优先，失败则全文扫描）
# --------------------------------------------------------------------------- #
OBJ_RE = re.compile(rb"(\d{1,10})\s+(\d{1,5})\s+obj\b")


class Pdf:
    """一个 PDF 文件的对象仓库。惰性解析 + 缓存。"""

    def __init__(self, data: bytes) -> None:
        if not data[:1024].lstrip().startswith(b"%PDF"):
            head = data[:1024]
            if b"%PDF" not in head:
                raise PdfError("不是 PDF 文件（找不到 %PDF 头）")
        self.data = data
        self._offsets: dict[int, int] = {}
        self._cache: dict[int, object] = {}
        self._objstm: dict[int, dict] = {}
        self.encrypted = False
        self._collect()

    # ---- 对象定位 ----
    def _collect(self) -> None:
        d = self.data
        # ① startxref → 交叉引用表或交叉引用流（后者能覆盖 PDF 1.5+ 的对象流）
        for m in re.finditer(rb"startxref\s+(\d+)", d):
            offset = int(m.group(1))
            if not (0 <= offset < len(d)):
                continue
            try:
                self._read_xref_at(offset)
            except Exception:
                pass
        # ② 全文扫描 "N G obj"，损坏/线性化文件也能救回来
        for m in OBJ_RE.finditer(d):
            self._offsets.setdefault(int(m.group(1)), m.start())
        # ③ 对象流：先扫出 /Type /ObjStm 的对象号，再整体解包（顺序很重要，
        #    否则 get_object 会因为「它是个普通对象」而提前返回 None）
        stm_nums: list[int] = []
        for num, off in list(self._offsets.items()):
            head = d[off:off + 400]
            if b"/ObjStm" in head or b"/Type/ObjStm" in head:
                stm_nums.append(num)
        for num in stm_nums:
            self._load_objstm(num)
        if self.trailer.get("Encrypt") is not None:
            self.encrypted = True

    trailer: dict = {}

    def _read_xref_at(self, offset: int) -> None:
        d = self.data
        lex = Lexer(d, offset)
        lex.skip_ws()
        m = re.match(rb"(\d+)\s+(\d+)\s+obj\b", d[lex.pos:lex.pos + 64])
        if m:
            # 交叉引用流：对象号就是紧随 startxref 的那个对象
            self._read_xref_stream(int(m.group(1)))
            return
        if d[lex.pos:lex.pos + 4] != b"xref":
            return
        self._read_xref_table(lex.pos)

    def _read_xref_table(self, offset: int) -> None:
        d = self.data
        if not (0 <= offset < len(d)):
            return
        lex = Lexer(d, offset)
        if lex._word() != b"xref":
            return
        while True:
            lex.skip_ws()
            if d[lex.pos:lex.pos + 7] == b"trailer":
                lex.pos += 7
                tr = lex.parse()
                if isinstance(tr, dict):
                    self.trailer = {**self.trailer, **tr}
                return
            m = re.match(rb"(\d+)\s+(\d+)", d[lex.pos:lex.pos + 64])
            if not m:
                return
            start, count = int(m.group(1)), int(m.group(2))
            lex.pos += m.end()
            for i in range(count):
                em = re.match(rb"\s*(\d{10})\s+(\d{5})\s+([nf])", d[lex.pos:lex.pos + 32])
                if not em:
                    return
                lex.pos += em.end()
                if em.group(3) == b"n":
                    self._offsets.setdefault(start + i, int(em.group(1)))

    def _read_xref_stream(self, num: int) -> None:
        obj = self.get_object(num)
        if not isinstance(obj, Stream):
            return
        # 交叉引用流的字典本身就是 trailer（含 /Root、/Info、/Size）
        self.trailer = {**obj.dict, **self.trailer}
        data = obj.data()
        widths = obj.dict.get("W") or []
        if not isinstance(widths, list) or len(widths) < 3:
            return
        w = [int(x or 0) for x in widths]
        size = int(obj.dict.get("Size") or 0)
        index = obj.dict.get("Index") or [0, size]
        index = [int(x) for x in index]
        pos = 0
        row = sum(w)
        for k in range(0, len(index) - 1, 2):
            first, count = index[k], index[k + 1]
            for i in range(count):
                if pos + row > len(data):
                    return
                fields = []
                for width in w:
                    v = 0
                    for b in data[pos:pos + width]:
                        v = (v << 8) | b
                    fields.append(v)
                    pos += width
                if len(fields) >= 3 and fields[0] == 1:
                    self._offsets.setdefault(first + i, fields[1])

    # ---- 对象读取 ----
    def get_object(self, num: int):
        num = int(num)
        if num in self._cache:
            return self._cache[num]
        self._cache[num] = None                          # 防递归
        off = self._offsets.get(num)
        obj = None
        if off is not None:
            obj = self._parse_at(off)
        if obj is None:
            for stm in self._objstm.values():            # 压缩对象
                if num in stm:
                    obj = stm[num]
                    break
        self._cache[num] = obj
        return obj

    def _parse_at(self, offset: int):
        lex = Lexer(self.data, offset)
        # xref 指向的是 "N G obj" 的 N（前面可能有换行/空白）
        m = re.match(rb"\s*(\d+)\s+(\d+)\s+obj\b", self.data[offset:offset + 64])
        if m:
            lex.pos = offset + m.end()
            lex.skip_ws()                                # 跳过 "obj" 与对象之间的空白
        else:
            lex.skip_ws()
        try:
            obj = lex.parse()
        except Exception:
            return None
        if isinstance(obj, dict):
            save = lex.pos
            lex.skip_ws()
            if self.data[lex.pos:lex.pos + 6] == b"stream":
                lex.pos += 6
                if self.data[lex.pos:lex.pos + 2] == b"\r\n":
                    lex.pos += 2
                elif self.data[lex.pos:lex.pos + 1] in (b"\n", b"\r"):
                    lex.pos += 1
                length = obj.get("Length")
                if isinstance(length, Ref):
                    length = self.get_object(length.num)
                start = lex.pos
                if isinstance(length, int) and 0 <= length <= len(self.data) - start:
                    raw = self.data[start:start + length]
                    end = self.data.find(b"endstream", start + length)
                    if end < 0 or end - (start + length) > 4:
                        e = self.data.find(b"endstream", start)
                        raw = self.data[start:e if e > 0 else len(self.data)]
                        raw = raw.rstrip(b"\r\n")
                else:
                    e = self.data.find(b"endstream", start)
                    raw = self.data[start:e if e > 0 else len(self.data)]
                    raw = raw.rstrip(b"\r\n")
                return Stream(obj, raw)
            lex.pos = save
        return obj

    def _load_objstm(self, num: int) -> None:
        """解包一个 /Type /ObjStm 对象流：流头部是 N 组 (对象号, 偏移)。"""
        if num in self._objstm:
            return
        off = self._offsets.get(num)
        if off is None:
            return
        try:
            obj = self._parse_at(off)
            if not isinstance(obj, Stream):
                return
            if str(obj.dict.get("Type") or "") not in ("ObjStm", ""):
                return
            data = obj.data()
            n = int(obj.dict.get("N") or 0)
            first = int(obj.dict.get("First") or 0)
            if n <= 0 or first <= 0 or first > len(data):
                return
            nums = [int(x) for x in re.findall(rb"\d+", data[:first])]
            pairs = list(zip(nums[0::2], nums[1::2]))[:n]
            table: dict[int, object] = {}
            for onum, ooff in pairs:
                table[onum] = Lexer(data, first + ooff).parse()
            if table:
                self._objstm[num] = table
        except Exception:
            return

    # ---- 便捷访问 ----
    def resolve(self, obj, depth: int = 0):
        while isinstance(obj, Ref) and depth < 32:
            obj = self.get_object(obj.num)
            depth += 1
        return obj

    def stream_of(self, obj) -> Stream | None:
        obj = self.resolve(obj)
        return obj if isinstance(obj, Stream) else None


# --------------------------------------------------------------------------- #
# 四、字符编码：ToUnicode CMap + 预定义编码
# --------------------------------------------------------------------------- #
STD_ENCODINGS = {
    "WinAnsiEncoding": "cp1252",
    "MacRomanEncoding": "mac_roman",
    "StandardEncoding": "latin-1",
    "PDFDocEncoding": "latin-1",
    "MacExpertEncoding": "mac_roman",
}

# 预定义 CJK CMap → 字节解码方式（无 /ToUnicode 时退化为「按原编码解出 Unicode」）。
# 学校的旧 PDF（Word/WPS 导出）大量使用 UniGB-UCS2-H，这时字节本身就是 Unicode，
# 解码比任何字符表都准确。
PREDEFINED_CMAPS = {
    "UniGB-UCS2-H": ("utf-16-be", 2),
    "UniGB-UCS2-V": ("utf-16-be", 2),
    "UniGB-UTF16-H": ("utf-16-be", 2),
    "UniGB-UTF16-V": ("utf-16-be", 2),
    "UniCNS-UCS2-H": ("utf-16-be", 2),
    "UniJIS-UCS2-H": ("utf-16-be", 2),
    "UniKS-UCS2-H": ("utf-16-be", 2),
    "GBK-EUC-H": ("gb18030", 2),
    "GBK-EUC-V": ("gb18030", 2),
    "GB-EUC-H": ("gb18030", 2),
    "GBpc-EUC-H": ("gb18030", 2),
    "GBKp-EUC-H": ("gb18030", 2),
    "B5pc-H": ("big5", 2),
    "ETen-B5-H": ("big5", 2),
    "EUC-H": ("euc_jp", 2),
    "90ms-RKSJ-H": ("cp932", 2),
    "KSC-EUC-H": ("euc_kr", 2),
}


def _utf16_be(b: bytes) -> str:
    if len(b) % 2:
        b += b"\x00"
    return b.decode("utf-16-be", "ignore")


def parse_tounicode(data: bytes) -> dict[int, str]:
    """解析 ToUnicode CMap：返回 {字符码: Unicode 文本}。

    同时支持 bfchar / bfrange 的两种写法（目标为单个 code 或 array）。
    """
    out: dict[int, str] = {}
    text = data
    for block in re.finditer(rb"beginbfchar(.*?)endbfchar", text, re.S):
        for src, dst in re.findall(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]*)>", block.group(1)):
            try:
                out[int(src, 16)] = _utf16_be(bytes.fromhex(dst.decode()))
            except ValueError:
                continue
    for block in re.finditer(rb"beginbfrange(.*?)endbfrange", text, re.S):
        body = block.group(1)
        pat = rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*(?:<([0-9A-Fa-f]*)>|\[(.*?)\])"
        for m in re.finditer(pat, body, re.S):
            try:
                lo = int(m.group(1), 16)
                hi = int(m.group(2), 16)
            except ValueError:
                continue
            if hi < lo or hi - lo > 65535:
                continue
            if m.group(3) is not None:
                base = _utf16_be(bytes.fromhex(m.group(3).decode()))
                if not base:
                    continue
                for i, code in enumerate(range(lo, hi + 1)):
                    out[code] = base[:-1] + chr(ord(base[-1]) + i)
            else:
                items = re.findall(rb"<([0-9A-Fa-f]*)>", m.group(4) or b"")
                for i, item in enumerate(items):
                    out[lo + i] = _utf16_be(bytes.fromhex(item.decode()))
    return out


@dataclass
class Font:
    """一个字体资源对象整理出的解码信息。"""

    resource: str = ""
    subtype: str = ""
    base_font: str = ""
    to_unicode: dict[int, str] = field(default_factory=dict)
    reverse: dict[str, int] = field(default_factory=dict)
    code_bytes: int = 1
    simple_codec: str | None = None                  # 简单字体：单字节 → Unicode
    simple_map: dict[int, str] = field(default_factory=dict)
    cid_codec: str | None = None                     # CID 字体：按原编码解
    cid_bytes: int = 2
    descendant: str = ""
    identity: bool = False
    matrix_scale: float = 1.0                        # 字体矩阵缩放（Type3 / 缩放假 Tf）

    def decode(self, raw: bytes) -> str:
        """把内容流里的字符串按本字体解码成 Unicode。"""
        if not raw:
            return ""
        if self.simple_codec or self.simple_map:
            out = []
            for b in raw:
                if b in self.simple_map:
                    out.append(self.simple_map[b])
                elif self.simple_codec:
                    out.append(bytes([b]).decode(self.simple_codec, "replace"))
                else:
                    out.append("")
            return "".join(out)
        if self.to_unicode:
            return self._decode_cid(raw, self.to_unicode)
        if self.cid_codec:
            try:
                return raw.decode(self.cid_codec, "ignore")
            except LookupError:
                pass
        if self.identity:
            return _utf16_be(raw)
        # 没有任何线索：按 2 字节 Latin 兜底（好过丢失整段）
        return self._decode_cid(raw, {})

    def _decode_cid(self, raw: bytes, table: dict[int, str]) -> str:
        n = max(1, self.code_bytes)
        out = []
        for i in range(0, len(raw) - n + 1, n):
            code = int.from_bytes(raw[i:i + n], "big")
            ch = table.get(code)
            if ch is None:
                ch = table.get(code & 0xFF) if n == 2 else None
            out.append(ch or "")
        return "".join(out)


# WinAnsi / MacRoman 之外的常见字形名（Differences 数组里出现的名字）。
# 只列学校文档里真正会遇到的：符号、项目符号、省略号、破折号、方框、钩。
GLYPH_NAMES = {
    "space": " ", "bullet": "•", "periodcentered": "·", "endash": "–", "emdash": "—",
    "quotedblleft": "“", "quotedblright": "”", "quoteleft": "‘", "quoteright": "’",
    "ellipsis": "…", "percent": "%", "degree": "°", "section": "§", "paragraph": "¶",
    "asteriskmath": "∗", "minus": "−", "plusminus": "±", "multiply": "×", "divide": "÷",
    "lessequal": "≤", "greaterequal": "≥", "notequal": "≠", "approxequal": "≈",
    "infinity": "∞", "summation": "∑", "radical": "√", "integral": "∫",
    "openbullet": "◦", "square": "□", "blacksquare": "■", "circle": "○", "blackcircle": "●",
    "checkmark": "✓", "cross": "✗", "trademark": "™", "copyright": "©", "registered": "®",
    "dagger": "†", "daggerdbl": "‡", "florin": "ƒ", "Euro": "€", "sterling": "£", "yen": "¥",
    "onehalf": "½", "onequarter": "¼", "threequarters": "¾",
    "arrowleft": "←", "arrowup": "↑", "arrowright": "→", "arrowdown": "↓",
    "arrowboth": "↔", "arrowdblright": "⇒", "element": "∈", "union": "∪", "intersection": "∩",
    "alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "epsilon": "ε", "theta": "θ",
    "lambda": "λ", "mu": "μ", "pi": "π", "rho": "ρ", "sigma": "σ", "tau": "τ", "phi": "φ",
    "omega": "ω", "Delta": "Δ", "Sigma": "Σ", "Omega": "Ω", "Phi": "Φ",
}

# 常见中文字体的内置编码是 GBK 单/双字节混排（WPS 导出的旧文档很多）
GBK_FONT_HINTS = ("simsun", "simhei", "simkai", "simfang", "msyh", "fangsong", "kaiti",
                  "songti", "heiti", "yahei", "stsong", "sthei", "stkaiti", "stfangsong",
                  "microsoftyahei", "dengxian", "sungti", "mingliu", "pmingliu")


def _glyph_to_unicode(name: str) -> str | None:
    """字形名 → Unicode。覆盖 uniXXXX / uXXXX 与常见名字。"""
    if not name:
        return None
    if name in GLYPH_NAMES:
        return GLYPH_NAMES[name]
    m = re.fullmatch(r"uni([0-9A-Fa-f]{4,6})", name)
    if m:
        try:
            return chr(int(m.group(1), 16))
        except ValueError:
            return None
    m = re.fullmatch(r"u([0-9A-Fa-f]{4,6})", name)
    if m:
        try:
            return chr(int(m.group(1), 16))
        except ValueError:
            return None
    m = re.fullmatch(r"g(\d+)", name)                    # 子集字体：g12 → 无信息
    if m:
        return None
    # Arial-BoldMT 这类复合名有时只差一个短横：Name → Name
    if len(name) == 1:
        return name
    return None


def build_simple_map(encoding, base_font: str) -> tuple[dict[int, str], str | None]:
    """简单字体：/Encoding（名字或 Differences 数组）+ BaseFont → (码表, 单字节编码)。

    返回的编码用于「码表里没有的码位」兜底；中文旧 PDF 的 BaseFont 常是
    `ABCDEE+宋体` 且 Encoding 为 WinAnsi，此时 WinAnsi 只会吐出乱码拉丁字母，
    所以额外按 BaseFont 名字给一次 GBK 尝试（对 SimSun 系列是明显更优的选择）。
    """
    codec = "latin-1"
    diff: dict[int, str] = {}
    if isinstance(encoding, str):
        codec = STD_ENCODINGS.get(encoding, "latin-1")
    elif isinstance(encoding, dict):
        base = encoding.get("BaseEncoding")
        if isinstance(base, str):
            codec = STD_ENCODINGS.get(base, "latin-1")
        diffs = encoding.get("Differences")
        if isinstance(diffs, list):
            cur = 0
            for item in diffs:
                if isinstance(item, (int, float)):
                    cur = int(item)
                elif isinstance(item, str):
                    ch = _glyph_to_unicode(item)
                    if ch:
                        diff[cur] = ch
                    cur += 1
    low = (base_font or "").lower()
    subset_stripped = re.sub(r"^[A-Z]{6}\+", "", base_font or "")
    if any(h in low for h in GBK_FONT_HINTS):
        codec = "gb18030"
    return diff, codec


def build_font(pdf: "Pdf", name: str, font_obj) -> Font:
    """把一个字体资源对象整理成 `Font`（含 ToUnicode / 编码 / 码宽）。"""
    font = Font(resource=name)
    d = pdf.resolve(font_obj)
    if not isinstance(d, dict):
        return font
    font.subtype = str(d.get("Subtype") or "")
    font.base_font = str(d.get("BaseFont") or "")
    # 字体矩阵：Docear/LaTeX 类工具会把 Tf 的字号放大 10~20 倍再用 FontMatrix 缩回，
    # 不归一化的话「行高」判断会把每行都当成不同行。
    matrix = pdf.resolve(d.get("FontMatrix"))
    if isinstance(matrix, list) and len(matrix) >= 1:
        try:
            scale = abs(float(matrix[0]))
            if 0.01 <= scale <= 100:
                font.matrix_scale = scale
        except (TypeError, ValueError):
            pass
    tu = pdf.stream_of(d.get("ToUnicode"))
    if tu is not None:
        try:
            font.to_unicode = parse_tounicode(tu.data())
        except Exception:
            font.to_unicode = {}
    # 码宽：CID 字体默认 2 字节；简单字体 1 字节
    enc = d.get("Encoding")
    enc_name = enc if isinstance(enc, str) else (enc or {}).get("BaseEncoding") if isinstance(enc, dict) else None
    if isinstance(enc_name, str) and enc_name in PREDEFINED_CMAPS:
        font.cid_codec, font.code_bytes = PREDEFINED_CMAPS[enc_name]
    if font.subtype in ("Type0",):
        font.identity = True
        if isinstance(enc_name, str) and enc_name.startswith("Identity"):
            font.code_bytes = 2
        desc_fonts = pdf.resolve(d.get("DescendantFonts"))
        if isinstance(desc_fonts, list) and desc_fonts:
            desc = pdf.resolve(desc_fonts[0])
            if isinstance(desc, dict):
                font.descendant = str(desc.get("BaseFont") or "")
                cidinfo = desc.get("CIDSystemInfo")
                if isinstance(cidinfo, dict):
                    reg = str(cidinfo.get("Registry") or "")
                    if reg in ("Adobe",) and not font.cid_codec:
                        font.cid_codec = "utf-16-be"
        if font.cid_codec is None and font.to_unicode:
            # 以 ToUnicode 的码位宽度为准（Identity-H 常见 2 字节）
            font.code_bytes = 2
    else:
        font.simple_map, font.simple_codec = build_simple_map(enc, font.base_font)
    if font.to_unicode:
        width = max(font.to_unicode)
        if font.simple_codec is None:
            font.code_bytes = 2 if width > 0xFF else 1
    font.reverse = {}
    for code, ch in list(font.to_unicode.items())[:4000]:
        if len(ch) == 1 and ch not in font.reverse:
            font.reverse[ch] = code
    return font


def load_fonts(pdf: "Pdf", resources) -> dict[str, Font]:
    res = pdf.resolve(resources)
    if not isinstance(res, dict):
        return {}
    fonts = pdf.resolve(res.get("Font"))
    out: dict[str, Font] = {}
    if isinstance(fonts, dict):
        for name, obj in fonts.items():
            try:
                out[name] = build_font(pdf, name, obj)
            except Exception:
                out[name] = Font(resource=name)
    return out


# --------------------------------------------------------------------------- #
# 五、内容流 → 文本片段
#
# 坐标不能只用「累加平移」糊过去：学校里的 PDF 大量由 Word/WPS/LaTeX 导出，
# 常见 `1 0 0 -1 0 841.9 cm` 先把页面翻过来，再用 `0.05 0 0 -0.05 x y Tm`
# 把字号放大 20 倍放置文本。整条变换链（CTM × Tm）不跟踪的话，
# 「哪一段在上面」会整体反过来，行序全错。
# --------------------------------------------------------------------------- #
Matrix = tuple  # (a, b, c, d, e, f)


def mat_mul(m1: Matrix, m2: Matrix) -> Matrix:
    a1, b1, c1, d1, e1, f1 = m1
    a2, b2, c2, d2, e2, f2 = m2
    return (a1 * a2 + b1 * c2, a1 * b2 + b1 * d2,
            c1 * a2 + d1 * c2, c1 * b2 + d1 * d2,
            e1 * a2 + f1 * c2 + e2, e1 * b2 + f1 * d2 + f2)


def mat_apply(m: Matrix, x: float, y: float) -> tuple[float, float]:
    a, b, c, d, e, f = m
    return (a * x + c * y + e, b * x + d * y + f)


def mat_scale(m: Matrix) -> float:
    """矩阵的近似缩放（用于把字号换算成页面单位）。"""
    a, b, c, d = m[0], m[1], m[2], m[3]
    return max(0.01, (abs(a * d - b * c)) ** 0.5)


@dataclass
class Frag:
    """一段文本及其在页面上的位置（用于按阅读顺序重排）。

    x/y 是**页面显示坐标**（y 向上，与 CTM 一起跟踪过翻转）。
    """

    text: str
    x: float
    y: float
    size: float
    order: int

    def __post_init__(self) -> None:
        self.x = float(self.x)
        self.y = float(self.y)
        self.size = float(self.size)


def extract_frags(pdf: "Pdf", content: bytes, resources, *, depth: int = 0,
                  order_start: int = 0, base_ctm: Matrix = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
                  ) -> list[Frag]:
    """解析内容流，返回文本片段列表（带页面坐标）。递归展开 XObject Form。"""
    if depth > 4 or not content:
        return []
    fonts = load_fonts(pdf, resources)
    res = pdf.resolve(resources) if resources is not None else None
    xobjects = pdf.resolve(res.get("XObject")) if isinstance(res, dict) else None

    frags: list[Frag] = []
    lex = Lexer(content)
    stack: list = []
    font: Font | None = None
    size = 12.0
    ctm: Matrix = base_ctm
    gs: list[Matrix] = []                                # q/Q 栈
    tlm: Matrix = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)         # 文本行矩阵
    tm: Matrix = tlm                                      # 文本矩阵
    leading = 0.0
    font_name: str | None = None
    font_size = size
    order = order_start
    pending: list[str] = []
    pending_pos: tuple[float, float] | None = None
    pending_size = size

    def num(v, default: float = 0.0) -> float:
        return float(v) if isinstance(v, (int, float)) else default

    def ensure_pos() -> tuple[float, float]:
        """当前文本原点（页面坐标）。"""
        m = mat_mul(tm, ctm)
        return mat_apply(m, 0.0, 0.0)

    def flush() -> None:
        nonlocal order, pending_pos, pending_size
        if pending:
            text = "".join(pending)
            pending.clear()
            if text.strip():
                x, y = pending_pos if pending_pos else ensure_pos()
                frags.append(Frag(text, x, y, pending_size, order))
                order += 1
            pending_pos = None

    def show(raw: bytes) -> None:
        nonlocal pending_pos, pending_size
        if pending_pos is None:
            pending_pos = ensure_pos()
            pending_size = size * mat_scale(mat_mul(tm, ctm)) * (font.matrix_scale if font else 1.0)
        pending.append(font.decode(raw) if font is not None else raw.decode("latin-1", "ignore"))

    def restore_font() -> None:
        """回到 BT 时按「当前字号所属的字体资源名」重新取字体。

        字体是**图形状态**的一部分：Word/WPS 导出的 PDF 里同一个字体经常只 Tf 一次，
        后面的 BT…ET 块直接接着用。早先实现在 ET 里把 font 置空、BT 时又不恢复，
        于是那些块全部退化成 latin-1，吐出 `Aú`、`\\x05N` 这类乱码。
        """
        nonlocal font, size
        if font_name:
            font = fonts.get(font_name)
            if font is not None:
                size = font_size

    def move_text(dx: float, dy: float) -> None:
        nonlocal tlm, tm
        tlm = mat_mul((1, 0, 0, 1, dx, dy), tlm)
        tm = tlm

    while True:
        try:
            obj = lex.parse()
        except Exception:
            break
        if obj is None and lex.pos >= len(content):
            break
        if isinstance(obj, Keyword):
            op = obj.text.decode("latin-1", "ignore")
            if op == "q":
                gs.append(ctm)
            elif op == "Q":
                flush()
                if gs:
                    ctm = gs.pop()
            elif op == "cm":
                flush()
                if len(stack) >= 6:
                    ctm = mat_mul((num(stack[-6]), num(stack[-5]), num(stack[-4]),
                                   num(stack[-3]), num(stack[-2]), num(stack[-1])), ctm)
            elif op == "BT":
                flush()
                tlm = tm = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
                restore_font()
            elif op == "Tf":
                flush()
                fname = stack[-2] if len(stack) >= 2 and isinstance(stack[-2], str) else None
                if len(stack) >= 2:
                    size = num(stack[-1], size)
                if fname:
                    font_name = fname
                font_size = size
                font = fonts.get(font_name) if font_name else None
            elif op in ("Td", "TD"):
                flush()
                if len(stack) >= 2:
                    move_text(num(stack[-2]), num(stack[-1]))
                if op == "TD" and stack:
                    leading = -num(stack[-1])
            elif op == "Tm":
                flush()
                if len(stack) >= 6:
                    tlm = tm = (num(stack[-6]), num(stack[-5]), num(stack[-4]),
                                num(stack[-3]), num(stack[-2]), num(stack[-1]))
            elif op == "T*":
                flush()
                move_text(0.0, -leading)
            elif op == "TL":
                if stack:
                    leading = num(stack[-1])
            elif op == "Tj":
                if stack and isinstance(stack[-1], bytes):
                    show(stack[-1])
            elif op == "TJ":
                if stack and isinstance(stack[-1], list):
                    for item in stack[-1]:
                        if isinstance(item, bytes):
                            show(item)
                        elif isinstance(item, (int, float)) and item < -180:
                            pending.append(" ")      # 大负间距 ≈ 空格
            elif op in ("'", '"'):
                flush()
                if op == '"' and len(stack) >= 3:
                    leading = num(stack[-2], leading)
                move_text(0.0, -leading)
                if stack and isinstance(stack[-1], bytes):
                    show(stack[-1])
            elif op == "Do":
                flush()
                if (depth < 4 and isinstance(xobjects, dict) and stack
                        and isinstance(stack[-1], str)):
                    xo = pdf.stream_of(xobjects.get(stack[-1]))
                    if xo is not None and str(xo.dict.get("Subtype") or "") == "Form":
                        sub_ctm = ctm
                        fm = pdf.resolve(xo.dict.get("Matrix"))
                        if isinstance(fm, list) and len(fm) >= 6:
                            try:
                                sub_ctm = mat_mul(tuple(float(v) for v in fm[:6]), ctm)
                            except (TypeError, ValueError):
                                sub_ctm = ctm
                        sub = extract_frags(pdf, xo.data(),
                                            xo.dict.get("Resources") or resources,
                                            depth=depth + 1, order_start=order,
                                            base_ctm=sub_ctm)
                        frags.extend(sub)
                        order += len(sub)
            elif op == "ET":
                flush()
            stack.clear()
            continue
        stack.append(obj)
        if len(stack) > 64:
            del stack[:-16]
    flush()
    return frags


def estimated_width(f: "Frag") -> float:
    """粗略估一段文本的横向宽度（决定要不要插入空格用）。"""
    size = max(1.0, f.size)
    cjk = 0
    other = 0
    for ch in f.text:
        if "\u2e80" <= ch <= "\u9fff" or "\uff00" <= ch <= "\uffef":
            cjk += 1
        else:
            other += 1
    return size * (cjk * 0.95 + other * 0.5)


def _join_line(line: list[Frag]) -> str:
    """把同一行的片段拼成字符串：片段间有明显空隙才补空格。

    中文 PDF 常把整行拆成每个字一段（且每段自带 x），逐字按「字宽」判空隙会把
    「华南农业大学」变成「华 南 农 业」——检索侧是按 bigram 匹配的，一旦插空格
    就整条召回失效。所以这里只在**片段之间**判空隙，且阈值取 0.4 个字宽。
    """
    line = sorted(line, key=lambda f: (f.x, f.order))
    buf: list[str] = []
    prev: Frag | None = None
    prev_end = 0.0
    for f in line:
        if prev is not None:
            gap = f.x - prev_end
            size = max(1.0, min(f.size or 0, prev.size or 0) if prev.size and f.size else (f.size or prev.size or 12.0))
            if gap > max(1.0, size * 0.4) and buf and not buf[-1].endswith(" "):
                buf.append(" ")
        buf.append(f.text)
        prev_end = f.x + estimated_width(f)
        prev = f
    return re.sub(r"[ \t\u3000]+", " ", "".join(buf)).strip()


def frags_to_text(frags: list[Frag]) -> str:
    """按阅读顺序（行自上而下、行内自左而右）拼出页面文本。"""
    if not frags:
        return ""
    usable = [f for f in frags if f.text and f.text.strip()]
    if not usable:
        return ""
    heights = sorted(f.size for f in usable if f.size > 0.5)
    median = heights[len(heights) // 2] if heights else 12.0
    # 同一行内的基线差异通常远小于字高；下标/上标会略大，但不该到半个字
    tol = max(1.5, min(median * 0.45, 8.0))

    # ① 贪心聚行：按 y 降序，找 y 最接近且已存在的行
    lines: list[list[Frag]] = []
    for f in sorted(usable, key=lambda f: (-f.y, f.x, f.order)):
        best: list[Frag] | None = None
        best_dy = tol
        for line in lines:
            dy = abs(line[0].y - f.y)
            if dy <= best_dy:
                best, best_dy = line, dy
        if best is None:
            lines.append([f])
        else:
            best.append(f)
    for line in lines:
        line.sort(key=lambda f: (f.x, f.order))
    lines.sort(key=lambda ln: (-max(f.y for f in ln), min(f.x for f in ln)))

    # ② 视觉上并排的两行（标题 + 右下角小字）按 y 排不会错，但同一基线组内
    #    可能出现 x 重叠的两行（分栏、页眉），这里按 x 区间重叠合并成一行。
    merged: list[list[Frag]] = []
    for line in lines:
        x0, x1 = min(f.x for f in line), max(f.x + estimated_width(f) for f in line)
        y = max(f.y for f in line)
        target = None
        for other in merged:
            oy = max(f.y for f in other)
            ox0 = min(f.x for f in other)
            ox1 = max(f.x + estimated_width(f) for f in other)
            if abs(oy - y) <= tol and min(x1, ox1) - max(x0, ox0) > 0.3 * min(x1 - x0, ox1 - ox0):
                target = other
                break
        if target is None:
            merged.append(list(line))
        else:
            target.extend(line)

    out_lines = [_join_line(line) for line in merged]
    text = "\n".join(ln for ln in out_lines if ln)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# --------------------------------------------------------------------------- #
# 六、页面树 → 逐页文本
# --------------------------------------------------------------------------- #
def iter_pages(pdf: "Pdf") -> list[dict]:
    """返回按阅读顺序排列的页面对象（沿 /Root → /Pages 树展平）。"""
    pages: list[dict] = []
    seen: set[int] = set()

    roots: list[object] = []
    tr = pdf.trailer or {}
    root = pdf.resolve(tr.get("Root"))
    if isinstance(root, dict):
        roots.append(root.get("Pages"))
    # 有些线性化文件 trailer 里没有 Root：退化为全文找 /Type /Catalog
    if not roots:
        for m in re.finditer(rb"/Type\s*/Catalog", pdf.data):
            head = pdf.data.rfind(b"obj", 0, m.start())
            if head < 0:
                continue
            num_m = None
            for num_m in re.finditer(rb"(\d+)\s+(\d+)\s+obj", pdf.data[max(0, head - 60):head + 4]):
                pass
            if num_m:
                cat = pdf.get_object(int(num_m.group(1)))
                if isinstance(cat, dict):
                    roots.append(cat.get("Pages"))
                    break

    def walk(node, depth: int = 0) -> None:
        if depth > 32:
            return
        node = pdf.resolve(node)
        if not isinstance(node, dict):
            return
        oid = id(node)
        if oid in seen:
            return
        seen.add(oid)
        kids = pdf.resolve(node.get("Kids"))
        typ = str(node.get("Type") or "")
        if typ == "Page" or (not isinstance(kids, list)):
            if typ == "Page" or node.get("Contents") is not None:
                pages.append(node)
            return
        for kid in kids:
            walk(kid, depth + 1)

    for r in roots:
        walk(r)
    return pages


def page_text(pdf: "Pdf", page: dict) -> str:
    contents = page.get("Contents")
    chunks: list[bytes] = []
    if isinstance(contents, list):
        objs = [pdf.stream_of(c) for c in contents]
    else:
        objs = [pdf.stream_of(contents)]
    for st in objs:
        if st is None:
            continue
        try:
            chunks.append(st.data())
        except Exception:
            continue
    if not chunks:
        return ""
    resources = page.get("Resources")
    # 资源可能在父节点上，取不到就不带资源（至少还能输出 WinAnsi 文本）
    frags: list[Frag] = []
    order = 0
    for chunk in chunks:
        sub = extract_frags(pdf, chunk, resources, order_start=order)
        order += len(sub)
        frags.extend(sub)
    return frags_to_text(frags)


@dataclass
class PdfText:
    """PDF 抽取结果。"""

    text: str = ""
    pages: int = 0
    pages_with_text: int = 0
    image_only_pages: int = 0
    error: str = ""
    encrypted: bool = False
    producer: str = ""

    @property
    def ok(self) -> bool:
        return not self.error

    @property
    def has_text(self) -> bool:
        return bool(re.search(r"[\w\u4e00-\u9fff]", self.text or ""))

    @property
    def scanned(self) -> bool:
        """整本几乎没有文本层 → 需要 OCR（扫描件）。"""
        return self.ok and self.pages > 0 and not self.has_text

    def summary(self) -> str:
        if self.error:
            return f"PDF 解析失败：{self.error}"
        bits = [f"{self.pages} 页", f"{len(self.text)} 字符"]
        if self.image_only_pages:
            bits.append(f"{self.image_only_pages} 页疑似扫描件")
        if self.scanned:
            bits.append("无文本层，需 OCR")
        return "，".join(bits)


def _page_has_images(pdf: "Pdf", page: dict) -> bool:
    res = pdf.resolve(page.get("Resources"))
    if not isinstance(res, dict):
        return False
    xo = pdf.resolve(res.get("XObject"))
    if not isinstance(xo, dict):
        return False
    for v in xo.values():
        d = pdf.resolve(v)
        if isinstance(d, Stream) and str(d.dict.get("Subtype") or "") == "Image":
            return True
        if isinstance(d, dict) and str(d.get("Subtype") or "") == "Image":
            return True
    return False


def extract_pdf(data: bytes, *, max_pages: int = 200, max_chars: int = 400_000) -> PdfText:
    """抽取 PDF 文本（纯内存，不落盘）。"""
    try:
        pdf = Pdf(data)
    except PdfError as e:
        return PdfText(error=str(e))
    except Exception as e:                                # noqa: BLE001
        return PdfText(error=f"{type(e).__name__}: {e}")
    if pdf.encrypted:
        return PdfText(error="PDF 已加密，无法直接抽取文本", encrypted=True)
    info = pdf.resolve((pdf.trailer or {}).get("Info"))
    producer = ""
    if isinstance(info, dict):
        producer = str(info.get("Producer") or info.get("Creator") or "")
    try:
        pages = iter_pages(pdf)
    except Exception as e:                                # noqa: BLE001
        return PdfText(error=f"页面树解析失败：{type(e).__name__}: {e}", producer=producer)
    out: list[str] = []
    with_text = 0
    image_only = 0
    used = 0
    for i, page in enumerate(pages[:max_pages], 1):
        try:
            txt = page_text(pdf, page)
        except Exception:
            txt = ""
        if txt.strip():
            with_text += 1
            out.append(txt)
            used += len(txt)
            if used >= max_chars:
                out.append("（正文过长，已截断）")
                break
        elif _page_has_images(pdf, page):
            image_only += 1
    return PdfText(text="\n\n".join(out).strip(), pages=len(pages),
                   pages_with_text=with_text, image_only_pages=image_only,
                   producer=producer)


def extract_pdf_file(path) -> PdfText:
    with open(path, "rb") as fh:
        return extract_pdf(fh.read())
