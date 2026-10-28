"""Hacker News via the free Algolia search API (no key needed)."""
from __future__ import annotations

from typing import Iterator

from ..http import HttpError
from ..models import Post
from .base import Source, strip_html

API = "https://hn.algolia.com/api/v1/search"


class HackerNewsSource(Source):
    name = "hackernews"

    def collect(self) -> Iterator[Post]:
        per_query = int(self.cfg.get("max_per_query", 200))
        tags = self.cfg.get("tags", ["story", "comment"])
        for q in self.cfg.get("queries", []):
            for tag in tags:
                yield from self._search(q, tag, per_query)

    def _search(self, query: str, tag: str, limit: int) -> Iterator[Post]:
        page = fetched = 0
        while fetched < limit:
            try:
                data = self.client.get_json(API, {"query": query, "tags": tag,
                                                  "hitsPerPage": min(100, limit - fetched), "page": page})
            except HttpError as e:
                self.log.warning("Skipping HN %r/%s: %s", query, tag, e)
                return
            hits = data.get("hits", [])
            for hit in hits:
                post = parse_hit(hit, query)
                if post:
                    fetched += 1
                    yield post
            page += 1
            if not hits or page >= data.get("nbPages", 0):
                return


def parse_hit(hit: dict, query: str = "") -> Post | None:
    text = strip_html(hit.get("comment_text") or hit.get("story_text"))
    title = hit.get("title") or ""
    if not (text or title):
        return None
    oid = hit["objectID"]
    is_comment = bool(hit.get("comment_text"))
    return Post(
        source="hackernews",
        native_id=oid,
        kind="comment" if is_comment else "post",
        title="" if is_comment else title,
        text=text,
        community="hackernews",
        author=hit.get("author") or "",
        url=f"https://news.ycombinator.com/item?id={oid}",
        created_utc=float(hit.get("created_at_i") or 0),
        score=int(hit.get("points") or 0),
        num_comments=int(hit.get("num_comments") or 0),
        parent_id=f"hackernews:{hit['story_id']}" if is_comment and hit.get("story_id") else "",
        query=query,
    )
