"""语料 API：状态、检索、正文、附件与本地文件。

全部是只读接口：采集与入库属于 CLI 的职责，Web 端不触发写库。
"""
from __future__ import annotations

import mimetypes
import urllib.parse
from pathlib import Path

from ..documents.attachments import ATTACH_DIR
from ..server.http import Request, Response, error_response, json_response
from ..services import Services
from ..settings.service import ocr_configured


def status(req: Request, svc: Services) -> Response:
    st = svc.store()
    try:
        stats = st.stats()
        last = st.last_crawl_ts()
    finally:
        st.close()
    return json_response({
        "articles": stats["articles"], "sites": stats["sites"],
        "with_date": stats["with_date"],
        "llm_configured": svc.settings.llm.configured,
        "llm_model": svc.settings.llm.model,
        "llm_base_url": svc.settings.llm.base_url,
        "web_search": svc.searcher().settings.provider,
        "last_crawl": last,
        "db": str(svc.settings.crawl.db_path),
        "attachments": stats.get("attachments", 0),
        "attachments_with_text": stats.get("attachments_with_text", 0),
        "ocr_configured": ocr_configured(),
    })


def search(req: Request, svc: Services) -> Response:
    query = (req.query.get("q") or "").strip()
    try:
        k = min(int(req.query.get("k") or 12), 50)
    except ValueError:
        k = 12
    st = svc.store()
    try:
        total = st.count_articles()
        hits = st.search(query, top_k=k, topic=req.query.get("topic") or None,
                         since=req.query.get("since") or None) if query else []
    finally:
        st.close()
    return json_response({
        "total": total,
        "hits": [
            {"id": h.article_id, "title": h.title, "url": h.url,
             "pub_date": h.pub_date, "snippet": h.snippet, "college": h.college,
             "site_name": h.site_name, "topic": h.topic, "score": round(h.score, 3)}
            for h in hits
        ],
    })


def article(req: Request, svc: Services) -> Response:
    try:
        aid = int(req.query.get("id") or 0)
    except ValueError:
        aid = 0
    st = svc.store()
    try:
        art = st.get_article(aid, max_chars=20000)
    finally:
        st.close()
    return json_response(art or {"error": "not found"})


def attachment(req: Request, svc: Services) -> Response:
    """读一份附件的解析结果（卡片上「看解析出的正文」用）。"""
    st = svc.store()
    try:
        row = None
        if req.query.get("id"):
            row = st.get_attachment(int(req.query["id"]))
        elif req.query.get("article"):
            rows = st.get_attachments(int(req.query["article"]))
            row = rows[0] if rows else None
    except (TypeError, ValueError):
        row = None
    finally:
        st.close()
    if not row:
        return json_response({"error": "not found"}, 404)
    text = row.get("text") or ""
    return json_response({
        "id": row.get("id"), "article_id": row.get("article_id"),
        "url": row.get("url"), "filename": row.get("filename"),
        "kind": row.get("kind"), "bytes": row.get("bytes"),
        "stored": row.get("stored"), "parser": row.get("parser"),
        "note": row.get("note"), "error": row.get("error"),
        "tables": row.get("tables"), "images": row.get("images"),
        "ocr_used": row.get("ocr_used"), "ocr_chars": row.get("ocr_chars"),
        "chars": len(text),
        "text": text[:20000],
        "truncated": len(text) > 20000,
    })


def attachment_file(req: Request, svc: Services) -> Response:
    """把下载到 data/attachments/ 的文件本体发出去。

    只允许发附件目录里的文件：先 resolve 再判断前缀，防止 `../` 穿越。
    """
    rel = urllib.parse.unquote(req.query.get("stored") or req.query.get("path") or "")
    if not rel:
        return error_response("缺少 stored 参数", 400)
    base = ATTACH_DIR.resolve()
    rel_norm = rel.replace("\\", "/").lstrip("/")
    prefix = "data/attachments/"
    if rel_norm.startswith(prefix):
        rel_norm = rel_norm[len(prefix):]
    target = ((base / rel_norm).resolve() if not Path(rel_norm).is_absolute()
              else Path(rel_norm).resolve())
    if target != base and base not in target.parents:
        return error_response("越权路径", 403)
    if not target.is_file():
        return error_response("文件不存在（可能已被清理）", 404)
    data = target.read_bytes()
    ctype = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
    ascii_name = target.name.encode("ascii", "ignore").decode() or "attachment"
    disposition = (f"inline; filename=\"{ascii_name}\"; "
                   f"filename*=UTF-8''{urllib.parse.quote(target.name)}")
    return Response(status=200, body=data, content_type=ctype,
                    headers={"Content-Disposition": disposition})
