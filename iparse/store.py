"""SQLite storage for collected posts and their analysis."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Iterable, Iterator

from .models import Post

SCHEMA = """
CREATE TABLE IF NOT EXISTS posts (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    native_id TEXT NOT NULL,
    kind TEXT,
    community TEXT,
    author_hash TEXT,
    title TEXT,
    text TEXT,
    url TEXT,
    created_utc REAL,
    score INTEGER,
    num_comments INTEGER,
    parent_id TEXT,
    query TEXT,
    lang TEXT,
    meta TEXT,
    collected_at REAL
);
CREATE INDEX IF NOT EXISTS posts_source ON posts(source);
CREATE TABLE IF NOT EXISTS analysis (
    post_id TEXT PRIMARY KEY REFERENCES posts(id) ON DELETE CASCADE,
    version INTEGER,
    sentiment REAL,
    problems TEXT,
    joys TEXT,
    wishes TEXT,
    segments TEXT,
    keyphrases TEXT,
    analyzed_at REAL
);
"""

POST_COLUMNS = ["id", "source", "native_id", "kind", "community", "author_hash", "title", "text",
                "url", "created_utc", "score", "num_comments", "parent_id", "query", "lang", "meta",
                "collected_at"]
ANALYSIS_JSON = ["problems", "joys", "wishes", "segments", "keyphrases"]


class Store:
    def __init__(self, path: str | Path, author_salt: str = "intenetparser"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=NORMAL")
        self.db.executescript(SCHEMA)
        self.author_salt = author_salt

    def close(self) -> None:
        self.db.close()

    def _hash_author(self, source: str, author: str) -> str:
        if not author:
            return ""
        return hashlib.sha256(f"{self.author_salt}|{source}|{author}".encode()).hexdigest()[:16]

    def upsert_posts(self, posts: Iterable[Post]) -> tuple[int, int]:
        """Insert new posts and refresh engagement numbers on existing ones.

        Returns (new, updated).
        """
        now = time.time()
        rows = {}
        for p in posts:
            if p.full_text:
                rows[p.id] = (p.id, p.source, p.native_id, p.kind, p.community,
                              self._hash_author(p.source, p.author), p.title, p.text, p.url, p.created_utc,
                              int(p.score or 0), int(p.num_comments or 0), p.parent_id, p.query, p.lang,
                              json.dumps(p.meta, ensure_ascii=False), now)
        if not rows:
            return 0, 0
        existing = set()
        ids = list(rows)
        for i in range(0, len(ids), 900):  # SQLite caps bound parameters
            chunk = ids[i:i + 900]
            existing.update(r[0] for r in self.db.execute(
                f"SELECT id FROM posts WHERE id IN ({','.join('?' * len(chunk))})", chunk))
        self.db.executemany(
            f"INSERT INTO posts ({', '.join(POST_COLUMNS)}) VALUES ({', '.join('?' * len(POST_COLUMNS))}) "
            "ON CONFLICT(id) DO UPDATE SET score = excluded.score, "
            "num_comments = excluded.num_comments, text = excluded.text, title = excluded.title",
            rows.values(),
        )
        self.db.commit()
        return len(rows) - len(existing), len(existing)

    def known_ids(self, source: str) -> set[str]:
        return {r[0] for r in self.db.execute("SELECT native_id FROM posts WHERE source = ?", (source,))}

    def pending_ids(self, version: int | None) -> list[str]:
        """Ids of posts needing analysis (all posts when version is None)."""
        if version is None:
            return [r[0] for r in self.db.execute("SELECT id FROM posts")]
        return [r[0] for r in self.db.execute(
            "SELECT p.id FROM posts p LEFT JOIN analysis a ON a.post_id = p.id "
            "WHERE a.post_id IS NULL OR a.version < ?", (version,))]

    def posts_by_ids(self, ids: list[str]) -> list[dict]:
        out = []
        for i in range(0, len(ids), 900):
            chunk = ids[i:i + 900]
            for row in self.db.execute(f"SELECT * FROM posts WHERE id IN ({','.join('?' * len(chunk))})", chunk):
                d = dict(row)
                d["meta"] = json.loads(d["meta"] or "{}")
                out.append(d)
        return out

    def posts(self) -> Iterator[dict]:
        for row in self.db.execute("SELECT * FROM posts"):
            d = dict(row)
            d["meta"] = json.loads(d["meta"] or "{}")
            yield d

    def save_analysis(self, rows: Iterable[dict]) -> int:
        now = time.time()
        params = [(r["post_id"], r["version"], r["sentiment"],
                   *(json.dumps(r[k], ensure_ascii=False) for k in ANALYSIS_JSON), now) for r in rows]
        self.db.executemany(
            "INSERT OR REPLACE INTO analysis (post_id, version, sentiment, problems, joys, wishes, "
            "segments, keyphrases, analyzed_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", params)
        self.db.commit()
        return len(params)

    def joined(self) -> Iterator[dict]:
        """Posts with their analysis attached (only analysed posts)."""
        sql = ("SELECT p.*, a.sentiment, a.problems, a.joys, a.wishes, a.segments, a.keyphrases "
               "FROM posts p JOIN analysis a ON a.post_id = p.id")
        for row in self.db.execute(sql):
            d = dict(row)
            d["meta"] = json.loads(d["meta"] or "{}")
            for k in ANALYSIS_JSON:
                d[k] = json.loads(d[k] or "[]")
            yield d

    def counts(self) -> dict:
        total = self.db.execute("SELECT COUNT(*) FROM posts").fetchone()[0]
        analysed = self.db.execute("SELECT COUNT(*) FROM analysis").fetchone()[0]
        by_source = dict(self.db.execute("SELECT source, COUNT(*) FROM posts GROUP BY source").fetchall())
        return {"posts": total, "analyzed": analysed, "by_source": by_source}
