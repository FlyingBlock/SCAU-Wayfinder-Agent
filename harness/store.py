"""存储层：SQLite + FTS5（中文 bigram 分词）。

为什么自己切词：FTS5 的 unicode61 把连续汉字当成一个 token，`匹配 研究生`
永远召不回 `2026年推荐免试研究生工作通知`。这里把中日韩字符切成
bigram（二字组）并以空格连接入库，查询也做同样切分，于是
「推免」→ `"推免"`、「保研政策」→ `"保研" AND "研政" AND "政策"`，
在没有 jieba 的情况下也能给出可用的中文召回。
"""
from __future__ import annotations

import datetime
import hashlib
import json
import re
import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS site (
  id           INTEGER PRIMARY KEY,
  group_id     TEXT,
  group_name   TEXT,
  name         TEXT NOT NULL,
  list_url     TEXT NOT NULL UNIQUE,
  final_url    TEXT,
  site         TEXT,
  topic        TEXT,
  status       TEXT,
  priority     INTEGER,
  max_page     INTEGER,
  article_count INTEGER DEFAULT 0,
  last_crawl   TEXT,
  last_error   TEXT
);

CREATE TABLE IF NOT EXISTS article (
  id           INTEGER PRIMARY KEY,
  dedupe_key   TEXT NOT NULL UNIQUE,
  site_id      INTEGER REFERENCES site(id),
  url          TEXT NOT NULL,
  title        TEXT,
  pub_date     TEXT,
  author       TEXT,
  body         TEXT,
  attachments  TEXT,
  topic        TEXT,
  college      TEXT,
  site_host    TEXT,
  keywords     INTEGER DEFAULT 0,
  crawled_at   TEXT NOT NULL,
  http_status  INTEGER,
  content_hash TEXT,
  char_count   INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_article_pubdate ON article(pub_date DESC);
CREATE INDEX IF NOT EXISTS idx_article_site    ON article(site_id);
CREATE INDEX IF NOT EXISTS idx_article_topic   ON article(topic);

CREATE TABLE IF NOT EXISTS field (
  article_id   INTEGER REFERENCES article(id) ON DELETE CASCADE,
  key          TEXT,
  value        TEXT,
  confidence   REAL,
  model        TEXT,
  PRIMARY KEY (article_id, key)
);

CREATE TABLE IF NOT EXISTS crawl_log (
  id         INTEGER PRIMARY KEY,
  url        TEXT,
  status     TEXT,
  http_code  INTEGER,
  bytes      INTEGER,
  ms         INTEGER,
  error      TEXT,
  ts         TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_crawllog_ts ON crawl_log(ts DESC);

CREATE VIRTUAL TABLE IF NOT EXISTS article_fts USING fts5(
  title, body, tokenize='unicode61 remove_diacritics 2'
);

-- 附件：下载到 data/attachments/ 的正文附件与图片，正文与表格抽成 text 供检索。
-- 与 article 是一对多；同一 URL 只存一行（url 唯一），
-- article_id 记「最先收录它的那篇通知」，检索时按 URL 反向关联到引用它的文章。
CREATE TABLE IF NOT EXISTS attachment (
  id           INTEGER PRIMARY KEY,
  article_id   INTEGER REFERENCES article(id) ON DELETE CASCADE,
  url          TEXT NOT NULL,
  filename     TEXT,
  kind         TEXT,
  content_type TEXT,
  stored       TEXT,
  sha1         TEXT,
  bytes        INTEGER DEFAULT 0,
  text         TEXT,
  parser       TEXT,
  note         TEXT,
  error        TEXT,
  tables       INTEGER DEFAULT 0,
  images       INTEGER DEFAULT 0,
  ocr_used     INTEGER DEFAULT 0,
  ocr_chars    INTEGER DEFAULT 0,
  ms           INTEGER DEFAULT 0,
  extra        TEXT,
  fetched_at   TEXT NOT NULL,
  parsed_at    TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_attachment_url  ON attachment(url);
CREATE INDEX IF NOT EXISTS idx_attachment_article    ON attachment(article_id);
CREATE INDEX IF NOT EXISTS idx_attachment_sha1       ON attachment(sha1);

CREATE VIRTUAL TABLE IF NOT EXISTS attachment_fts USING fts5(
  filename, text, tokenize='unicode61 remove_diacritics 2'
);
"""

# 中日韩统一表意文字 + 假名 + 谚文
CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uac00-\ud7af]")
ASCII_WORD_RE = re.compile(r"[A-Za-z0-9_]{2,}")


def tokenize_for_index(text: str) -> str:
    """中文→bigram，英文数字→保留原词。用于写入 FTS 表。"""
    if not text:
        return ""
    toks: list[str] = []
    buf: list[str] = []

    def flush_cjk() -> None:
        if not buf:
            return
        s = "".join(buf)
        buf.clear()
        if len(s) == 1:
            toks.append(s)
        else:
            toks.extend(s[i:i + 2] for i in range(len(s) - 1))

    for ch in text:
        if CJK_RE.match(ch):
            buf.append(ch)
        else:
            flush_cjk()
    flush_cjk()
    toks.extend(ASCII_WORD_RE.findall(text))
    return " ".join(toks)


def tokenize_query(query: str) -> list[str]:
    """查询切词：中文 bigram + 英文词；去掉停用式单字噪声。"""
    if not query:
        return []
    toks: list[str] = []
    buf: list[str] = []

    def flush_cjk() -> None:
        if not buf:
            return
        s = "".join(buf)
        buf.clear()
        if len(s) == 1:
            toks.append(s)
        else:
            toks.extend(s[i:i + 2] for i in range(len(s) - 1))

    for ch in query:
        if CJK_RE.match(ch):
            buf.append(ch)
        else:
            flush_cjk()
    flush_cjk()
    toks.extend(w.lower() for w in ASCII_WORD_RE.findall(query))
    # 去重保序
    seen, out = set(), []
    for t in toks:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def fts_query(tokens: Sequence[str], mode: str = "AND") -> str:
    """构造安全的 FTS5 MATCH 表达式（全部加引号，避免语法注入）。"""
    safe = [t.replace('"', "") for t in tokens if t.strip()]
    if not safe:
        return ""
    joiner = f" {mode} "
    return joiner.join(f'"{t}"' for t in safe)


def sha256(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8", "ignore")).hexdigest()


@dataclass
class Hit:
    article_id: int
    title: str
    url: str
    pub_date: str
    snippet: str
    topic: str = ""
    college: str = ""
    site_name: str = ""
    score: float = 0.0
    char_count: int = 0


class Store:
    def __init__(self, db_path: Path | str) -> None:
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.conn = sqlite3.connect(str(self.path), check_same_thread=False, timeout=60)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # ---------- 写 ----------
    def upsert_site(self, site, *, max_page: int | None = None, final_url: str = "",
                    error: str = "") -> int:
        now = datetime.datetime.now().isoformat(timespec="seconds")
        with self._lock:
            cur = self.conn.execute("SELECT id FROM site WHERE list_url=?", (site.url,))
            row = cur.fetchone()
            if row:
                sid = row["id"]
                self.conn.execute(
                    """UPDATE site SET name=?, group_id=?, group_name=?, site=?, topic=?, status=?,
                           priority=?, max_page=COALESCE(?,max_page), final_url=COALESCE(NULLIF(?,''),final_url),
                           last_crawl=?, last_error=? WHERE id=?""",
                    (site.name, site.group_id, site.group_name, site.site, site.topic, site.status,
                     site.priority, max_page, final_url, now, error, sid),
                )
            else:
                cur = self.conn.execute(
                    """INSERT INTO site (group_id,group_name,name,list_url,final_url,site,topic,status,
                           priority,max_page,last_crawl,last_error)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (site.group_id, site.group_name, site.name, site.url, final_url, site.site,
                     site.topic, site.status, site.priority, max_page, now, error),
                )
                sid = cur.lastrowid
            self.conn.commit()
            return int(sid)

    def has_article(self, key: str) -> bool:
        with self._lock:
            return self.conn.execute(
                "SELECT 1 FROM article WHERE dedupe_key=? LIMIT 1", (key,)
            ).fetchone() is not None

    def count_articles(self) -> int:
        with self._lock:
            return int(self.conn.execute("SELECT COUNT(*) c FROM article").fetchone()["c"])

    def upsert_article(
        self,
        *,
        dedupe_key: str,
        site_id: int | None,
        url: str,
        title: str,
        body: str,
        pub_date: str = "",
        author: str = "",
        attachments: Iterable[str] = (),
        topic: str = "",
        college: str = "",
        site_host: str = "",
        http_status: int = 200,
        keywords: int = 0,
    ) -> tuple[int, bool]:
        """返回 (article_id, changed)。content_hash 变化才算更新。"""
        now = datetime.datetime.now().isoformat(timespec="seconds")
        ch = sha256(title + "\n" + body)
        atts = json.dumps(list(attachments), ensure_ascii=False)
        with self._lock:
            row = self.conn.execute(
                "SELECT id, content_hash FROM article WHERE dedupe_key=?", (dedupe_key,)
            ).fetchone()
            if row:
                aid = int(row["id"])
                if row["content_hash"] == ch:
                    return aid, False
                self.conn.execute(
                    """UPDATE article SET site_id=?, url=?, title=?, pub_date=?, author=?, body=?,
                           attachments=?, topic=?, college=?, site_host=?, crawled_at=?, http_status=?,
                           content_hash=?, char_count=?, keywords=? WHERE id=?""",
                    (site_id, url, title, pub_date, author, body, atts, topic, college, site_host,
                     now, http_status, ch, len(body), keywords, aid),
                )
                self.conn.execute("DELETE FROM article_fts WHERE rowid=?", (aid,))
            else:
                cur = self.conn.execute(
                    """INSERT INTO article (dedupe_key,site_id,url,title,pub_date,author,body,
                           attachments,topic,college,site_host,keywords,crawled_at,http_status,
                           content_hash,char_count)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (dedupe_key, site_id, url, title, pub_date, author, body, atts, topic, college,
                     site_host, keywords, now, http_status, ch, len(body)),
                )
                aid = int(cur.lastrowid)
            self.conn.execute(
                "INSERT INTO article_fts (rowid, title, body) VALUES (?,?,?)",
                (aid, tokenize_for_index(title), tokenize_for_index(body)),
            )
            self.conn.commit()
            return aid, True

    def log_crawl(self, url: str, status: str, http_code: int = 0, nbytes: int = 0,
                  ms: int = 0, error: str = "") -> None:
        now = datetime.datetime.now().isoformat(timespec="seconds")
        with self._lock:
            self.conn.execute(
                "INSERT INTO crawl_log (url,status,http_code,bytes,ms,error,ts) VALUES (?,?,?,?,?,?,?)",
                (url, status, http_code, nbytes, ms, error, now),
            )
            self.conn.commit()

    def set_field(self, article_id: int, key: str, value: str,
                  confidence: float = 1.0, model: str = "") -> None:
        with self._lock:
            self.conn.execute(
                "INSERT OR REPLACE INTO field (article_id,key,value,confidence,model) VALUES (?,?,?,?,?)",
                (article_id, key, value, confidence, model),
            )
            self.conn.commit()

    # ---------- 读 ----------
    @staticmethod
    def _snippet(body: str, tokens: Sequence[str], width: int = 260) -> str:
        if not body:
            return ""
        pos = -1
        for t in tokens:
            if len(t) >= 2:
                pos = body.find(t)
                if pos >= 0:
                    break
        if pos < 0:
            return body[:width].strip()
        start = max(0, pos - width // 3)
        return ("…" if start else "") + body[start:start + width].strip() + "…"

    def search(
        self,
        query: str,
        *,
        top_k: int = 8,
        topic: str | None = None,
        college: str | None = None,
        since: str | None = None,
        host: str | None = None,
        prefer_bio: bool = False,
    ) -> list[Hit]:
        """两段式检索：FTS5 召回候选 → Python 侧按「词覆盖 + BM25」重排。

        为什么不能只靠 FTS5 排序：中文被切成 bigram 后，
        `竞赛 学分认定` → `"竞赛" OR "学分" OR "分认" OR "认定"`，
        只要命中「认定」两个字（如「家庭经济困难认定」）就会进候选，
        而真正想找的「竞赛学分认定」因为缺少某一个 bigram 反而不在 AND 结果里。
        因此这里用 OR 保证召回，再用「命中了几个查询词」+ BM25 把
        覆盖度高的文档顶上来。
        """
        tokens = tokenize_query(query)
        if not tokens:
            return []

        where, params = [], []
        if topic:
            where.append("a.topic = ?")
            params.append(topic)
        if college:
            where.append("a.college = ?")
            params.append(college)
        if host:
            where.append("a.site_host = ?")
            params.append(host)
        if since:
            where.append("(a.pub_date IS NULL OR a.pub_date = '' OR a.pub_date >= ?)")
            params.append(since)
        extra = (" AND " + " AND ".join(where)) if where else ""

        sql = f"""
            SELECT a.id, a.title, a.url, a.pub_date, a.body, a.topic, a.college, a.char_count,
                   s.name AS site_name,
                   bm25(article_fts, 3.0, 1.0) AS rank
            FROM article_fts f
            JOIN article a ON a.id = f.rowid
            LEFT JOIN site s ON s.id = a.site_id
            WHERE article_fts MATCH ?{extra}
            ORDER BY rank
            LIMIT ?
        """
        cand_limit = max(top_k * 25, 150)
        rows: list[sqlite3.Row] = []
        with self._lock:
            for expr in (fts_query(tokens, "OR"), fts_query(tokens, "AND")):
                if not expr:
                    continue
                try:
                    rows = self.conn.execute(sql, [expr, *params, cand_limit]).fetchall()
                except sqlite3.OperationalError:
                    rows = []
                if rows:
                    break

        if not rows:
            return []

        # 词覆盖度：查询里有几个 token 真的出现在标题/正文里
        long_tokens = [t for t in tokens if len(t) >= 2]
        hits: list[Hit] = []
        for r in rows:
            body = r["body"] or ""
            title = r["title"] or ""
            hay = title + "\n" + body
            covered = sum(1 for t in long_tokens if t in hay)
            coverage = covered / len(long_tokens) if long_tokens else 0.0
            title_hit = sum(1 for t in long_tokens if t in title)
            score = -float(r["rank"] or 0.0)
            score += coverage * 12.0                    # 覆盖度是主信号
            score += title_hit * 1.6                    # 标题命中额外加权
            if prefer_bio and (r["college"] or ""):
                score += 1.5
            if (r["topic"] or "") in ("competition", "academic", "graduate"):
                score += 0.6
            hits.append(
                Hit(
                    article_id=int(r["id"]),
                    title=title,
                    url=r["url"],
                    pub_date=r["pub_date"] or "",
                    snippet=self._snippet(body, tokens),
                    topic=r["topic"] or "",
                    college=r["college"] or "",
                    site_name=r["site_name"] or "",
                    score=score,
                    char_count=int(r["char_count"] or 0),
                )
            )
        hits.sort(key=lambda h: -h.score)
        return hits[:top_k]

    def get_article(self, article_id: int, max_chars: int = 6000) -> dict | None:
        with self._lock:
            r = self.conn.execute(
                """SELECT a.*, s.name AS site_name FROM article a
                   LEFT JOIN site s ON s.id=a.site_id WHERE a.id=?""",
                (article_id,),
            ).fetchone()
        if not r:
            return None
        d = dict(r)
        if max_chars and len(d.get("body") or "") > max_chars:
            d["body"] = d["body"][:max_chars] + "\n…（正文已截断）"
        return d

    def recent(self, limit: int = 40, topic: str | None = None) -> list[dict]:
        sql = """SELECT a.id, a.title, a.url, a.pub_date, a.topic, a.college, a.char_count,
                        s.name AS site_name
                 FROM article a LEFT JOIN site s ON s.id=a.site_id"""
        params: list = []
        if topic:
            sql += " WHERE a.topic=?"
            params.append(topic)
        sql += " ORDER BY COALESCE(NULLIF(a.pub_date,''),'0000-00-00') DESC, a.id DESC LIMIT ?"
        params.append(limit)
        with self._lock:
            return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def site_report(self, limit: int = 200) -> list[dict]:
        with self._lock:
            rows = self.conn.execute(
                """SELECT s.id, s.name, s.list_url, s.site, s.topic, s.priority, s.status,
                          s.max_page, s.last_error,
                          COUNT(a.id) AS n
                   FROM site s LEFT JOIN article a ON a.site_id = s.id
                   GROUP BY s.id ORDER BY n DESC, s.priority LIMIT ?""",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def stats(self) -> dict:
        with self._lock:
            total = self.conn.execute("SELECT COUNT(*) c FROM article").fetchone()["c"]
            sites = self.conn.execute("SELECT COUNT(*) c FROM site").fetchone()["c"]
            withdate = self.conn.execute(
                "SELECT COUNT(*) c FROM article WHERE pub_date IS NOT NULL AND pub_date<>''"
            ).fetchone()["c"]
            errors = self.conn.execute(
                "SELECT COUNT(*) c FROM site WHERE last_error IS NOT NULL AND last_error<>''"
            ).fetchone()["c"]
            logs = self.conn.execute("SELECT COUNT(*) c FROM crawl_log").fetchone()["c"]
            try:
                at = self.conn.execute("SELECT COUNT(*) c FROM attachment").fetchone()["c"]
                at_text = self.conn.execute(
                    "SELECT COUNT(*) c FROM attachment WHERE text IS NOT NULL AND text<>''"
                ).fetchone()["c"]
                at_bytes = self.conn.execute(
                    "SELECT COALESCE(SUM(bytes),0) s FROM attachment").fetchone()["s"]
            except sqlite3.Error:
                at = at_text = at_bytes = 0
        return {"articles": total, "sites": sites, "with_date": withdate,
                "site_errors": errors, "crawl_logs": logs,
                "attachments": at, "attachments_with_text": at_text,
                "attachment_bytes": int(at_bytes or 0)}

    # ------------------------------------------------------------------ #
    # 附件（下载到 data/attachments/ 的文件）
    # ------------------------------------------------------------------ #
    def upsert_attachment(self, *, article_id: int, url: str, filename: str = "",
                          kind: str = "", content_type: str = "", stored: str = "",
                          sha1: str = "", bytes: int = 0, text: str = "",
                          parser: str = "", note: str = "", error: str = "",
                          tables: int = 0, images: int = 0, ocr_used: int = 0,
                          ocr_chars: int = 0, ms: int = 0, extra: str = "") -> int:
        """写入/更新一份附件的解析结果，并重建它的 FTS 行。返回 attachment.id。"""
        now = datetime.datetime.now().isoformat(timespec="seconds")
        with self._lock:
            row = self.conn.execute(
                "SELECT id, article_id FROM attachment WHERE url=?", (url,)).fetchone()
            if row:
                aid = int(row["id"])
                # 同一附件被多篇通知引用时，保留最先收录它的那篇（检索会按 url 反查）
                link = int(article_id or row["article_id"] or 0)
                self.conn.execute(
                    """UPDATE attachment SET article_id=?, filename=?, kind=?, content_type=?,
                           stored=?, sha1=?, bytes=?, text=?, parser=?, note=?, error=?,
                           tables=?, images=?, ocr_used=?, ocr_chars=?, ms=?, extra=?,
                           parsed_at=? WHERE id=?""",
                    (link, filename, kind, content_type, stored, sha1, bytes,
                     text, parser, note, error, tables, images, ocr_used, ocr_chars,
                     ms, extra, now, aid),
                )
            else:
                cur = self.conn.execute(
                    """INSERT INTO attachment (article_id,url,filename,kind,content_type,stored,
                           sha1,bytes,text,parser,note,error,tables,images,ocr_used,ocr_chars,
                           ms,extra,fetched_at,parsed_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (article_id, url, filename, kind, content_type, stored, sha1, bytes,
                     text, parser, note, error, tables, images, ocr_used, ocr_chars,
                     ms, extra, now, now),
                )
                aid = int(cur.lastrowid)
            self.conn.execute("DELETE FROM attachment_fts WHERE rowid=?", (aid,))
            self.conn.execute(
                "INSERT INTO attachment_fts (rowid, filename, text) VALUES (?,?,?)",
                (aid, tokenize_for_index(filename), tokenize_for_index(text)),
            )
            self.conn.commit()
            return aid

    def get_attachment(self, attachment_id: int) -> dict | None:
        with self._lock:
            r = self.conn.execute("SELECT * FROM attachment WHERE id=?",
                                  (int(attachment_id),)).fetchone()
        return dict(r) if r else None

    def get_attachment_by_url(self, url: str) -> dict | None:
        with self._lock:
            r = self.conn.execute("SELECT * FROM attachment WHERE url=?",
                                  (url,)).fetchone()
        return dict(r) if r else None

    def get_attachments(self, article_id: int) -> list[dict]:
        with self._lock:
            rows = self.conn.execute(
                "SELECT * FROM attachment WHERE article_id=? ORDER BY id",
                (int(article_id),)).fetchall()
        return [dict(r) for r in rows]

    def attachments_for_articles(self, article_ids: Iterable[int]) -> dict[int, list[dict]]:
        """批量取多篇文章的附件（卡片层要按证据编号展示解析摘要）。"""
        ids = [int(i) for i in article_ids if i]
        if not ids:
            return {}
        out: dict[int, list[dict]] = {}
        with self._lock:
            for chunk in _chunks(ids, 400):
                marks = ",".join("?" * len(chunk))
                rows = self.conn.execute(
                    f"SELECT * FROM attachment WHERE article_id IN ({marks}) ORDER BY id",
                    chunk).fetchall()
                for r in rows:
                    d = dict(r)
                    out.setdefault(int(d["article_id"] or 0), []).append(d)
        return out

    def attachment_text_map(self, article_id: int, *, max_chars_each: int = 1200,
                            max_total: int = 6000) -> str:
        """把一篇文章所有附件的正文拼成一段（给证据/模型看）。"""
        parts: list[str] = []
        used = 0
        for a in self.get_attachments(article_id):
            text = (a.get("text") or "").strip()
            if not text:
                continue
            piece = f"【附件：{a.get('filename') or a.get('url')}】\n{text[:max_chars_each]}"
            parts.append(piece)
            used += len(piece)
            if used >= max_total:
                break
        return "\n\n".join(parts)

    def search_attachments(self, query: str, *, top_k: int = 6,
                           article_ids: Sequence[int] | None = None) -> list[dict]:
        """检索附件正文。返回带所属文章链接的结果（检索层据此把它并进证据）。"""
        tokens = tokenize_query(query)
        if not tokens:
            return []
        expr = fts_query(tokens, "OR")
        if not expr:
            return []
        sql = """
            SELECT t.rowid AS aid, a.id AS article_id, a.title, a.url AS article_url,
                   a.pub_date, a.college, a.topic, g.filename, g.stored, g.kind, g.text,
                   bm25(attachment_fts, 2.0, 1.0) AS rank
            FROM attachment_fts t
            JOIN attachment g ON g.id = t.rowid
            LEFT JOIN article a ON a.id = g.article_id
            WHERE attachment_fts MATCH ?
            ORDER BY rank LIMIT ?
        """
        params: list = [expr, max(top_k * 8, 40)]
        with self._lock:
            try:
                rows = self.conn.execute(sql, params).fetchall()
            except sqlite3.OperationalError:
                return []
        long_tokens = [t for t in tokens if len(t) >= 2]
        out: list[dict] = []
        for r in rows:
            text = r["text"] or ""
            covered = sum(1 for t in long_tokens if t in text)
            score = (-float(r["rank"] or 0.0)) + covered * 4.0
            out.append({
                "attachment_id": int(r["aid"]),
                "article_id": int(r["article_id"] or 0),
                "title": r["title"] or "",
                "article_url": r["article_url"] or "",
                "pub_date": r["pub_date"] or "",
                "college": r["college"] or "",
                "topic": r["topic"] or "",
                "filename": r["filename"] or "",
                "stored": r["stored"] or "",
                "kind": r["kind"] or "",
                "snippet": self._snippet(text, tokens),
                "score": score,
            })
        out.sort(key=lambda x: -x["score"])
        return out[:top_k]

    def articles_with_attachments(self, *, limit: int = 50) -> list[dict]:
        with self._lock:
            rows = self.conn.execute(
                """SELECT id, url, title, pub_date, attachments FROM article
                   WHERE attachments IS NOT NULL AND attachments<>'' AND attachments<>'[]'
                   ORDER BY id DESC LIMIT ?""", (int(limit),)).fetchall()
        return [dict(r) for r in rows]

    def articles_with_unparsed_attachments(self, *, limit: int = 50) -> list[dict]:
        """有附件链接、但 attachment 表里还没有对应记录的文章。"""
        with self._lock:
            rows = self.conn.execute(
                """SELECT a.id, a.url, a.title, a.pub_date, a.attachments FROM article a
                   WHERE a.attachments IS NOT NULL AND a.attachments<>'' AND a.attachments<>'[]'
                     AND NOT EXISTS (SELECT 1 FROM attachment g
                                     WHERE g.article_id = a.id
                                       AND g.text IS NOT NULL AND g.text<>'')
                   ORDER BY COALESCE(NULLIF(a.pub_date,''),'0000-00-00') DESC, a.id DESC
                   LIMIT ?""", (int(limit),)).fetchall()
        return [dict(r) for r in rows]

    def attachment_stats(self) -> dict:
        with self._lock:
            rows = self.conn.execute(
                """SELECT kind, COUNT(*) n, COALESCE(SUM(bytes),0) b,
                          SUM(CASE WHEN text IS NOT NULL AND text<>'' THEN 1 ELSE 0 END) with_text,
                          COALESCE(SUM(ocr_used),0) ocr
                   FROM attachment GROUP BY kind ORDER BY n DESC""").fetchall()
            total = self.conn.execute("SELECT COUNT(*) c FROM attachment").fetchone()["c"]
        return {"total": total, "by_kind": [dict(r) for r in rows]}

    def close(self) -> None:
        with self._lock:
            self.conn.close()


def _chunks(seq: Sequence, size: int):
    for i in range(0, len(seq), size):
        yield list(seq[i:i + size])
