"""Import posts from local CSV / JSON / JSONL files.

Use this for anything collected by hand or exported elsewhere: comments
copied from Instagram or TikTok, a Google Takeout export, survey answers,
support tickets, etc. Each file entry looks like:

    [[sources.import.files]]
    path = "data/inbox/*.csv"
    source = "instagram"        # label shown in reports
    community = "ig:skincare"   # optional
"""
from __future__ import annotations

import csv
import glob
import hashlib
import json
from pathlib import Path
from typing import Iterator

from ..models import Post
from .base import Source, iso_to_epoch

TEXT_KEYS = ("text", "body", "content", "comment", "message", "caption", "desc", "description", "review")
FIELD_ALIASES = {
    "title": ("title", "subject"),
    "url": ("url", "link", "permalink"),
    "author": ("author", "user", "username", "handle"),
    "score": ("score", "likes", "like_count", "upvotes", "diggCount"),
    "community": ("community", "subreddit", "channel", "group", "hashtag"),
    "created": ("created_utc", "timestamp", "created_at", "date", "time"),
    "id": ("id", "native_id", "comment_id", "post_id"),
}


class ImportSource(Source):
    name = "import"

    def collect(self) -> Iterator[Post]:
        for spec in self.cfg.get("files", []):
            for path in sorted(glob.glob(spec["path"])):
                for rec in _read(Path(path)):
                    post = record_to_post(rec, spec.get("source", "import"), spec.get("community", ""))
                    if post:
                        yield post


def _read(path: Path) -> Iterator[dict]:
    suffix = path.suffix.lower()
    with path.open(encoding="utf-8-sig") as f:
        if suffix == ".csv":
            yield from csv.DictReader(f)
        elif suffix == ".jsonl":
            for line in f:
                if line.strip():
                    yield json.loads(line)
        elif suffix == ".json":
            data = json.load(f)
            yield from (data if isinstance(data, list) else data.get("items", data.get("data", [])))
        else:  # plain text: one post per non-empty line
            for line in f:
                if line.strip():
                    yield {"text": line.strip()}


def _pick(rec: dict, keys) -> str:
    lower = {k.lower(): v for k, v in rec.items()}
    for k in keys:
        v = lower.get(k.lower())
        if v not in (None, ""):
            return str(v)
    return ""


def _number(value: str) -> int:
    try:
        return int(float(value))
    except ValueError:
        return 0


def _time(value: str) -> float:
    if not value:
        return 0.0
    try:
        return float(value)
    except ValueError:
        return iso_to_epoch(value)


def record_to_post(rec: dict, source: str, community: str = "") -> Post | None:
    text = _pick(rec, TEXT_KEYS)
    title = _pick(rec, FIELD_ALIASES["title"])
    if not (text or title):
        return None
    native = _pick(rec, FIELD_ALIASES["id"]) or hashlib.sha1(f"{title}|{text}".encode()).hexdigest()[:16]
    return Post(
        source=source,
        native_id=native,
        kind=rec.get("kind", "post"),
        title=title,
        text=text,
        community=_pick(rec, FIELD_ALIASES["community"]) or community or source,
        author=_pick(rec, FIELD_ALIASES["author"]),
        url=_pick(rec, FIELD_ALIASES["url"]),
        created_utc=_time(_pick(rec, FIELD_ALIASES["created"])),
        score=_number(_pick(rec, FIELD_ALIASES["score"]) or "0"),
    )
