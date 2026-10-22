"""OCR 层：把「图片里的字」变成可检索、可引用的文本。

设计取舍（与项目其它部分一致）：

  · **默认关闭**，没配 key 时所有函数都安全返回 `enabled=False`，不报错、不联网、
    不花额度。附件解析照常跑，只是图片那部分留空并如实写进 note。
  · 目前接入百度智能云 OCR（用户自己申请 AK/SK 填进 `.env`），但接口按
    「provider」抽象，后面加任意 OCR 引擎只需再写一个 provider 类。
  · 百度 OCR 的 access_token 缓存到 `data/cache/baidu_ocr_token.json`（有效期
    30 天），避免每张图都换一次 token（那是额外一次网络往返 + 一次配额）。
  · 图片先按百度要求预处理：BMP 转 PNG、超大图等比缩小、单张 ≤ 4MB。
    没有 Pillow 时也能跑（只做缩放跳过与格式判断），不会因为缺库直接失败。

环境变量（写进仓库根 `.env`，Web 设置面板也可填）：

    OCR_PROVIDER=baidu          # baidu | none
    BAIDU_OCR_API_KEY=xxx       # 百度智能云应用的 API Key
    BAIDU_OCR_SECRET_KEY=xxx    # 百度智能云应用的 Secret Key
    OCR_ACCURATE=1              # 1 用高精度版（默认），0 用标准版
    BAIDU_OCR_ENDPOINT=https://aip.baidubce.com   # 一般不用改
"""
from __future__ import annotations

import base64
import binascii
import datetime
import hashlib
import io
import json
import re
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from ..core.config import (
    DEFAULT_OCR_ENDPOINT,
    OCRSettings,
    ROOT,
    SETTINGS as CORE_SETTINGS,
)

# --------------------------------------------------------------------------- #
# 配置
# --------------------------------------------------------------------------- #
ENV_KEYS = ("OCR_PROVIDER", "BAIDU_OCR_API_KEY", "BAIDU_OCR_SECRET_KEY",
            "OCR_ACCURATE", "BAIDU_OCR_ENDPOINT")

DEFAULT_ENDPOINT = DEFAULT_OCR_ENDPOINT
TOKEN_CACHE = ROOT / "data" / "cache" / "baidu_ocr_token.json"
MAX_UPLOAD_BYTES = 4 * 1024 * 1024          # 百度单张图上限 4MB
MAX_EDGE = 4096                             # 百度要求最长边 ≤ 4096（我们留余量）

# 能被百度 OCR 直接吃的格式（bmp 需先转 png）
BAIDU_OK_EXT = ("jpg", "jpeg", "png", "bmp")

_SSL_CTX = None


def _ssl_ctx():
    global _SSL_CTX
    if _SSL_CTX is None:
        import ssl

        ctx = ssl.create_default_context()
        _SSL_CTX = ctx
    return _SSL_CTX


# 与 core.config.Settings.ocr 是同一个对象：默认进程共享，测试可替换。
SETTINGS = CORE_SETTINGS.ocr


def refresh_settings() -> OCRSettings:
    """按环境变量刷新共享配置对象（保持对象身份，避免引用漂移）。"""
    fresh = OCRSettings.from_env()
    SETTINGS.__dict__.update(fresh.__dict__)
    return SETTINGS


def mask(key: str) -> str:
    if not key:
        return ""
    if len(key) <= 8:
        return key[:2] + "*" * max(len(key) - 2, 0)
    return f"{key[:6]}…{key[-4:]}"


# --------------------------------------------------------------------------- #
# 图片预处理
# --------------------------------------------------------------------------- #
@dataclass
class ImagePayload:
    """准备上传的一张图。"""

    data: bytes = b""
    mime: str = "image/jpeg"
    filename: str = ""
    width: int = 0
    height: int = 0
    converted: bool = False
    original_bytes: int = 0
    error: str = ""

    @property
    def ok(self) -> bool:
        return bool(self.data) and not self.error


def _sniff_image(data: bytes) -> tuple[str, str]:
    """返回 (格式, mime)。识别 PNG/JPEG/GIF/BMP/TIFF/WEBP。"""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png", "image/png"
    if data[:2] == b"\xff\xd8":
        return "jpeg", "image/jpeg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif", "image/gif"
    if data[:2] == b"BM":
        return "bmp", "image/bmp"
    if data[:4] in (b"II*\x00", b"MM\x00*"):
        return "tiff", "image/tiff"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp", "image/webp"
    if data[:4] == b"\x01\x00\x00\x00" or data[:4] == b"\x00\x00\x01\x00":
        return "ico", "image/x-icon"
    return "", "application/octet-stream"


def looks_like_image(data: bytes, name: str = "") -> bool:
    fmt, _ = _sniff_image(data or b"")
    if fmt:
        return True
    return bool(re.search(r"\.(jpe?g|png|gif|bmp|tiff?|webp|ico)$", (name or "").lower()))


def prepare_image(data: bytes, *, name: str = "", max_edge: int = MAX_EDGE,
                  max_bytes: int = MAX_UPLOAD_BYTES) -> ImagePayload:
    """把任意图片整成「百度能收」的形态：BMP/超大/超重都就地转成 PNG/JPEG。

    没有 Pillow 时只做「原样透传 + 大小判断」，不让解析整条链因为缺库崩掉。
    """
    payload = ImagePayload(filename=name, original_bytes=len(data or b""))
    if not data:
        payload.error = "空文件"
        return payload
    fmt, mime = _sniff_image(data)
    payload.mime = mime
    payload.data = data
    need_convert = fmt in ("bmp", "tiff", "gif", "webp", "ico", "") or len(data) > max_bytes
    if not need_convert:
        return payload
    try:
        from PIL import Image                                    # type: ignore
    except Exception:
        if len(data) > max_bytes:
            payload.error = f"图片 {len(data) // 1024}KB 超过上限，且未安装 Pillow 无法压缩"
        return payload
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
        payload.width, payload.height = img.size
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        w, h = img.size
        scale = min(1.0, max_edge / max(w, h) if max(w, h) else 1.0)
        if scale < 1.0:
            img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=88)
        out = buf.getvalue()
        if len(out) > max_bytes:                                 # 再压一轮
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=70)
            out = buf.getvalue()
        if len(out) > max_bytes:
            payload.error = f"图片压缩后仍为 {len(out) // 1024}KB，超过上限"
            return payload
        payload.data = out
        payload.mime = "image/jpeg"
        payload.converted = True
        payload.width, payload.height = img.size
    except Exception as e:                                       # noqa: BLE001
        if len(data) > max_bytes:
            payload.error = f"图片转换失败：{type(e).__name__}"
    return payload


# --------------------------------------------------------------------------- #
# Provider 抽象
# --------------------------------------------------------------------------- #
@dataclass
class OCRResult:
    text: str = ""
    provider: str = ""
    engine: str = ""
    error: str = ""
    ms: int = 0
    chars: int = 0
    raw_error_code: int = 0
    skipped_reason: str = ""

    @property
    def ok(self) -> bool:
        return bool(self.text) and not self.error


class OCRProvider:
    name = "none"
    label = "未配置"

    @property
    def available(self) -> bool:
        return False

    def recognize(self, data: bytes, *, name: str = "") -> OCRResult:
        return OCRResult(error="OCR 未配置", provider=self.name,
                         skipped_reason="not_configured")


class NullOCR(OCRProvider):
    name = "none"
    label = "未配置（图片里的文字不会被提取）"


class BaiduOCR(OCRProvider):
    """百度智能云通用文字识别（标准版 / 高精度版）。"""

    name = "baidu"

    def __init__(self, settings: OCRSettings) -> None:
        self.s = settings

    @property
    def label(self) -> str:                                      # type: ignore[override]
        return "百度 OCR（%s）" % ("高精度含位置版" if self.s.accurate else "标准版")

    @property
    def available(self) -> bool:
        return self.s.configured

    # ---- token ----
    def _cache_read(self) -> str:
        try:
            raw = json.loads(TOKEN_CACHE.read_text(encoding="utf-8"))
        except Exception:
            return ""
        token = str(raw.get("access_token") or "")
        expires = float(raw.get("expires_at") or 0)
        if token and expires - time.time() > 3600:
            return token
        return ""

    def _cache_write(self, token: str, expires_in: int) -> None:
        try:
            TOKEN_CACHE.parent.mkdir(parents=True, exist_ok=True)
            TOKEN_CACHE.write_text(json.dumps({
                "access_token": token,
                "expires_at": time.time() + max(60, expires_in - 600),
                "saved_at": datetime.datetime.now().isoformat(timespec="seconds"),
                "api_key_tail": self.s.api_key[-6:],
            }, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass

    def token(self, *, force: bool = False) -> tuple[str, str]:
        """取 access_token。返回 (token, error)。"""
        if not self.available:
            return "", "未配置百度 OCR 的 API Key / Secret Key"
        if not force:
            cached = self._cache_read()
            if cached:
                return cached, ""
        url = (f"{self.s.endpoint}/oauth/2.0/token?grant_type=client_credentials"
               f"&client_id={urllib.parse.quote(self.s.api_key)}"
               f"&client_secret={urllib.parse.quote(self.s.secret_key)}")
        try:
            with urllib.request.urlopen(url, timeout=self.s.timeout,
                                        context=_ssl_ctx()) as resp:
                body = json.loads(resp.read().decode("utf-8", "ignore"))
        except urllib.error.HTTPError as e:
            return "", f"取 token 失败：HTTP {e.code}"
        except Exception as e:                                   # noqa: BLE001
            return "", f"取 token 失败：{type(e).__name__}"
        token = str(body.get("access_token") or "")
        if not token:
            err = body.get("error_description") or body.get("error") or "未知错误"
            return "", f"取 token 被拒绝：{err}（检查 API Key / Secret Key）"
        self._cache_write(token, int(body.get("expires_in") or 2592000))
        return token, ""

    # ---- 识别 ----
    def recognize(self, data: bytes, *, name: str = "") -> OCRResult:
        return self._recognize_mode(data, "accurate" if self.s.accurate else "general",
                                    name=name)

    def recognize_captcha(self, data: bytes, *, name: str = "captcha.png") -> OCRResult:
        """验证码：两个引擎各试一次，取「更像验证码」的那个结果。

        高精度版对清晰小图更准，标准版对带噪声/笔画的图更耐受，验证码两种都常见，
        所以不按配置赌一个，而是都跑一遍（多花一次配额，但验证码本来就只几张）。
        """
        order = ["accurate", "general"] if self.s.accurate else ["general", "accurate"]
        best: OCRResult | None = None
        for mode in order:
            res = self._recognize_mode(data, mode, name=name)
            if res.error and not res.text:
                if best is None or (not best.text and not best.error):
                    best = res
                continue
            res.text = clean_captcha_text(res.text)
            res.chars = len(res.text)
            if res.text:
                return res
            if best is None:
                best = res
        return best or OCRResult(provider=self.name, error="验证码识别没有返回结果")

    def _recognize_mode(self, data: bytes, mode: str, *, name: str = "") -> OCRResult:
        if not self.available:
            return OCRResult(error="", provider=self.name,
                             skipped_reason="not_configured",
                             text="")
        t0 = time.time()
        payload = prepare_image(data, name=name)
        if not payload.ok:
            return OCRResult(provider=self.name, error=payload.error)
        token, err = self.token()
        if not token:
            return OCRResult(provider=self.name, error=err)
        path = ("/rest/2.0/ocr/v1/accurate_basic" if mode == "accurate"
                else "/rest/2.0/ocr/v1/general_basic")
        body = urllib.parse.urlencode({
            "image": base64.b64encode(payload.data).decode("ascii"),
            "detect_direction": "true",
            "paragraph": "false",
            "probability": "false",
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{self.s.endpoint}{path}?access_token={urllib.parse.quote(token)}",
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded",
                     "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.s.timeout,
                                        context=_ssl_ctx()) as resp:
                out = json.loads(resp.read().decode("utf-8", "ignore"))
        except urllib.error.HTTPError as e:
            return OCRResult(provider=self.name, error=f"OCR 请求失败：HTTP {e.code}",
                             ms=int((time.time() - t0) * 1000))
        except Exception as e:                                   # noqa: BLE001
            return OCRResult(provider=self.name,
                             error=f"OCR 请求失败：{type(e).__name__}",
                             ms=int((time.time() - t0) * 1000))
        code = int(out.get("error_code") or 0)
        if code:
            msg = str(out.get("error_msg") or "")
            hint = {
                110: "token 失效或不是本应用，已自动重试一次仍失败，请检查 Key",
                111: "token 过期，请重新保存配置",
                17: "今日调用量已达上限",
                18: "QPS 超限，请稍后再试",
                216101: "图片格式不支持",
                216201: "图片尺寸不合法（最长边需 ≤ 4096，最短边 ≥ 15）",
                216202: "图片体积超过 4MB",
                216630: "识别失败（可能是图片过于模糊）",
            }.get(code, "")
            return OCRResult(provider=self.name, error=f"百度 OCR 返回 {code}：{msg}"
                             + (f"（{hint}）" if hint else ""),
                             raw_error_code=code, ms=int((time.time() - t0) * 1000))
        words = [str(w.get("words") or "") for w in (out.get("words_result") or [])]
        text = _join_words(words)
        return OCRResult(text=text, provider=self.name, engine=path.rsplit("/", 1)[-1],
                         chars=len(text), ms=int((time.time() - t0) * 1000))


def _join_words(words: list[str]) -> str:
    """把百度返回的逐行结果拼成正文。

    中文行之间直接换行（学校文档的表格/名单一行就是一条记录）；纯英文行之间
    补一个空格，避免英文单词被粘成一片。
    """
    out: list[str] = []
    for w in words:
        w = (w or "").strip()
        if not w:
            continue
        if out and re.search(r"[A-Za-z0-9]$", out[-1]) and re.match(r"^[A-Za-z0-9]", w):
            out[-1] = out[-1] + " " + w
        else:
            out.append(w)
    return "\n".join(out)


_CACHE: dict[str, OCRResult] = {}
_LOCK = threading.Lock()


def get_provider(settings: OCRSettings | None = None) -> OCRProvider:
    s = settings or SETTINGS
    if s.provider == "baidu" and s.configured:
        return BaiduOCR(s)
    return NullOCR()


# --------------------------------------------------------------------------- #
# 登录验证码专用识别
#
# 通用 OCR 是给「整页文档」设计的，直接拿来认验证码命中率很低：图小、噪声多、
# 笔画细、还常常是四位随机字符。所以这里单独一条路：
#   ① 先用 Pillow 做针对验证码的预处理（灰度 → 放大 → Otsu 二值化）；
#   ② 标准版与高精度版**各试一次**，取更像验证码的那个结果（两者的强项不同）；
#   ③ 把输出收敛成「验证码该有的样子」（去噪、算术题直接算出来）。
# 没装 Pillow 也照跑：跳过 ①，直接送原图。
# --------------------------------------------------------------------------- #
CAPTCHA_NOISE = re.compile(r"[^0-9A-Za-z\u4e00-\u9fff]")
CAPTCHA_MATH = re.compile(r"(\d{1,3})\s*([+\-xX×*])\s*(\d{1,3})")
CAPTCHA_MAX_CHARS = 10                  # 超过这个长度基本是认错了整行文字


def _otsu_threshold(hist: list[int], total: int) -> int:
    """Otsu 类间方差最大化求二值化阈值（纯 Python，验证码图很小，够快）。"""
    sum_all = sum(i * h for i, h in enumerate(hist))
    sum_b = 0.0
    w_b = 0
    best, best_var = 128, -1.0
    for t in range(256):
        w_b += hist[t]
        if w_b == 0:
            continue
        w_f = total - w_b
        if w_f == 0:
            break
        sum_b += t * hist[t]
        m_b = sum_b / w_b
        m_f = (sum_all - sum_b) / w_f
        var = w_b * w_f * (m_b - m_f) ** 2
        if var > best_var:
            best_var, best = var, t
    return best


def preprocess_captcha(data: bytes, *, scale: float = 2.0) -> tuple[bytes, str]:
    """把验证码整成「OCR 更容易认」的形态。返回 (图片字节, 说明)。

    步骤：灰度 → 放大（原图往往只有 100×40，字符不到 20px 高）→ Otsu 二值化
    （去掉背景纹理与干扰线，只留深色笔画）。

    没有 Pillow 时原样返回，附一句说明——照旧能试，只是准头差些。
    """
    try:
        from PIL import Image, ImageOps                   # type: ignore
    except Exception:
        return data, "未装 Pillow，跳过验证码预处理"
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
        img = ImageOps.grayscale(img)
        w, h = img.size
        if not w or not h:
            return data, "验证码图片尺寸异常"
        if scale and scale != 1.0:
            img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))),
                             Image.LANCZOS)
        hist = img.histogram()[:256]
        thr = _otsu_threshold(hist, sum(hist) or 1)
        # 深色笔画 → 黑，浅色背景 → 白（通用 OCR 对黑字白底最友好）
        img = img.point(lambda p: 0 if p <= thr else 255, mode="L")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue(), f"灰度 + {scale:g}× 放大 + Otsu 二值化（阈值 {thr}）"
    except Exception as e:                                # noqa: BLE001
        return data, f"预处理失败（{type(e).__name__}），已用原图"


def clean_captcha_text(raw: str) -> str:
    """把 OCR 输出收敛成「验证码」：取第一行、算术题算出来、只留字母数字。

    验证码要么是 4-6 位字母数字、要么是中文提示词、要么是一道小学算术题
    （`3+5=?`）。OCR 常带回换行、空格、问号之类的噪声，这里统一收拾干净。
    """
    for line in (raw or "").splitlines():
        line = line.strip()
        if not line:
            continue
        math = _eval_math(line)
        if math:
            return math
        text = CAPTCHA_NOISE.sub("", line)
        if text and len(text) <= CAPTCHA_MAX_CHARS:
            return text
    return ""


def _eval_math(text: str) -> str:
    """`3 + 5 = ?` → `8`。不是算术题就返回空串。"""
    m = CAPTCHA_MATH.search(text or "")
    if not m:
        return ""
    try:
        a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
    except ValueError:
        return ""
    if op == "+":
        val = a + b
    elif op == "-":
        val = a - b
    else:
        if a > 1000 or b > 1000:
            return ""
        val = a * b
    return str(val) if 0 <= val <= 9999 else ""


def looks_like_captcha(text: str) -> bool:
    """判断一段 OCR 输出像不像验证码（用于两个引擎之间挑一个更好的）。"""
    t = (text or "").strip()
    if not t or len(t) > CAPTCHA_MAX_CHARS:
        return False
    if CAPTCHA_NOISE.search(t):                # 还残留标点/空格 → 多半认的是整行
        return False
    return True


def recognize_captcha(data: bytes, *, settings: OCRSettings | None = None,
                      preprocess: bool = True) -> OCRResult:
    """识别一张登录验证码。**不走内容哈希缓存**（每张验证码只用一次）。

    provider 若实现了 `recognize_captcha` 就走它（会两个引擎各试一次），
    否则退回普通 `recognize`。结果统一过一遍 `clean_captcha_text`。
    """
    if not data:
        return OCRResult(error="空图片")
    s = settings or SETTINGS
    provider = get_provider(s)
    if not provider.available:
        return OCRResult(provider=provider.name, skipped_reason="not_configured",
                         error="未配置 OCR，无法自动识别验证码")
    img, note = preprocess_captcha(data) if preprocess else (data, "")
    fn = getattr(provider, "recognize_captcha", None)
    res = fn(img, name="captcha.png") if callable(fn) else provider.recognize(
        img, name="captcha.png")
    res.text = clean_captcha_text(res.text)
    res.chars = len(res.text)
    if res.text and note:
        res.engine = f"{res.engine}+prep"
    return res


def captcha_health(settings: OCRSettings | None = None) -> tuple[bool, str]:
    """设置面板「验证码识别自检」用：拿一张自己生成的验证码图跑一遍全链路。"""
    s = settings or SETTINGS
    if not get_provider(s).available:
        return False, "未配置 OCR（需要 OCR_PROVIDER=baidu 且填好 API Key / Secret Key）"
    img = make_captcha_image("A7K2")
    res = recognize_captcha(img, settings=s)
    if res.error and not res.text:
        return False, res.error
    if res.text:
        return True, f"识别链路可用（样例图「A7K2」认成「{res.text}」，耗时 {res.ms}ms）"
    return True, f"链路连通，但这张样例图没认出字符（耗时 {res.ms}ms）"


def make_captcha_image(text: str = "A7K2") -> bytes:
    """生成一张「像验证码」的测试图（白底黑字 + 两条干扰线）。

    没有 Pillow 时退回一张最小合法 PNG（百度会返回「未识别到文字」，
    仍然能验证 token 与配额是不是通的）。
    """
    try:
        from PIL import Image, ImageDraw                        # type: ignore

        w, h = 120, 44
        img = Image.new("RGB", (w, h), "white")
        draw = ImageDraw.Draw(img)
        draw.line([(0, 12), (w, 30)], fill=(150, 150, 150), width=1)
        draw.line([(0, 34), (w, 14)], fill=(180, 180, 180), width=1)
        for i, ch in enumerate(text):
            draw.text((12 + i * 24, 12), ch, fill="black")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return make_test_image("CAPTCHA")


def enabled(settings: OCRSettings | None = None) -> bool:
    return get_provider(settings).available


def recognize_image(data: bytes, *, name: str = "", settings: OCRSettings | None = None,
                    use_cache: bool = True) -> OCRResult:
    """识别一张图片。同一张图（按内容哈希）只调一次 OCR。"""
    if not data:
        return OCRResult(error="空图片")
    s = settings or SETTINGS
    provider = get_provider(s)
    if not provider.available:
        return OCRResult(provider=provider.name, skipped_reason="not_configured")
    key = hashlib.sha256(data).hexdigest()
    if use_cache:
        with _LOCK:
            hit = _CACHE.get(key)
        if hit is not None:
            return hit
    res = provider.recognize(data, name=name)
    if res.ok and use_cache:
        with _LOCK:
            if len(_CACHE) > 200:
                _CACHE.clear()
            _CACHE[key] = res
    return res


def health(settings: OCRSettings | None = None) -> tuple[bool, str]:
    """设置面板的「测试」按钮用：真发一张小图，看能不能认出来。"""
    s = settings or SETTINGS
    provider = get_provider(s)
    if not provider.available:
        return False, "未配置 OCR（需要 OCR_PROVIDER=baidu 且填好 API Key / Secret Key）"
    img = make_test_image()
    res = provider.recognize(img, name="ocr-test.png")
    if res.error:
        return False, res.error
    if res.text.strip():
        return True, f"识别成功（{res.text.strip()[:40]}，耗时 {res.ms}ms）"
    return True, f"接口连通（这张测试图没识别出文字，耗时 {res.ms}ms）"


def make_test_image(text: str = "华南农业大学 2026") -> bytes:
    """生成一张带文字的测试图（用于连通性验证）。

    有 Pillow 就真正画字，没有就退化成一个最小的合法 PNG（百度会返回
    「未识别到文字」而不是报错，仍然能验证 token 与配额）。
    """
    try:
        from PIL import Image, ImageDraw                        # type: ignore

        img = Image.new("RGB", (520, 90), "white")
        draw = ImageDraw.Draw(img)
        try:
            draw.text((14, 30), text, fill="black")
        except Exception:
            draw.rectangle([14, 30, 280, 60], outline="black")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except Exception:
        return binascii.unhexlify(
            "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
            "890000000d4944415478da63f8cfc000000301010018dd8db00000000049454e44ae426082")


def summary_line(settings: OCRSettings | None = None) -> str:
    s = settings or SETTINGS
    if s.configured:
        return f"OCR：{s.describe()}（已配置）"
    return "OCR：未配置（图片里的文字不会被提取；可在设置面板或 .env 里填百度 OCR Key）"
