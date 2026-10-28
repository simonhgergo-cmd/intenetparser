"""Mastodon public hashtag timelines (no account needed on most instances)."""
from __future__ import annotations

from typing import Iterator

from ..http import HttpError
from ..models import Post
from .base import Source, iso_to_epoch, strip_html


class MastodonSource(Source):
    name = "mastodon"

    def collect(self) -> Iterator[Post]:
        per_tag = int(self.cfg.get("max_per_tag", 200))
        for instance in self.cfg.get("instances", ["mastodon.social"]):
            for tag in self.cfg.get("hashtags", []):
                yield from self._tag(instance, tag.lstrip("#"), per_tag)

    def _tag(self, instance: str, tag: str, limit: int) -> Iterator[Post]:
        max_id, fetched = None, 0
        while fetched < limit:
            try:
                statuses = self.client.get_json(f"https://{instance}/api/v1/timelines/tag/{tag}",
                                                {"limit": 40, "max_id": max_id})
            except HttpError as e:
                self.log.warning("Skipping %s #%s: %s", instance, tag, e)
                return
            if not statuses:
                return
            for s in statuses:
                post = parse_status(s, tag)
                if post:
                    fetched += 1
                    yield post
            max_id = statuses[-1]["id"]


def parse_status(s: dict, tag: str = "") -> Post | None:
    text = strip_html(s.get("content"))
    if not text or s.get("reblog"):
        return None
    return Post(
        source="mastodon",
        native_id=s.get("uri") or s["id"],
        kind="comment" if s.get("in_reply_to_id") else "post",
        text=text,
        community=f"#{tag}" if tag else "mastodon",
        author=s.get("account", {}).get("acct", ""),
        url=s.get("url") or s.get("uri", ""),
        created_utc=iso_to_epoch(s.get("created_at")),
        score=int(s.get("favourites_count", 0)) + int(s.get("reblogs_count", 0)),
        num_comments=int(s.get("replies_count", 0)),
        query=tag,
        lang=s.get("language") or "",
    )
