"""Bluesky (the closest free, open substitute for X/Twitter).

Search may require a login. A free Bluesky account with an app password
(Settings -> App passwords) is enough: set `handle` and `app_password`.
"""
from __future__ import annotations

from typing import Iterator

from ..http import HttpError
from ..models import Post
from .base import Source, iso_to_epoch

PUBLIC = "https://public.api.bsky.app/xrpc"
PDS = "https://bsky.social/xrpc"


class BlueskySource(Source):
    name = "bluesky"

    def __init__(self, cfg, client, known=None):
        super().__init__(cfg, client, known)
        self._jwt: str | None = None

    def _login(self) -> None:
        handle, pw = self.cfg.get("handle"), self.cfg.get("app_password")
        if handle and pw and not self._jwt:
            data = self.client.post_json(f"{PDS}/com.atproto.server.createSession",
                                         {"identifier": handle, "password": pw})
            self._jwt = data["accessJwt"]

    def collect(self) -> Iterator[Post]:
        self._login()
        base = PDS if self._jwt else PUBLIC
        headers = {"Authorization": f"Bearer {self._jwt}"} if self._jwt else {}
        per_query = int(self.cfg.get("max_per_query", 200))
        lang = self.cfg.get("lang")
        for q in self.cfg.get("queries", []):
            cursor, fetched = None, 0
            while fetched < per_query:
                params = {"q": q, "limit": min(100, per_query - fetched), "cursor": cursor,
                          "sort": self.cfg.get("sort", "top"), "lang": lang}
                try:
                    data = self.client.get_json(f"{base}/app.bsky.feed.searchPosts", params, headers)
                except HttpError as e:
                    hint = " (set handle/app_password in config)" if e.status in (401, 403) else ""
                    self.log.warning("Skipping Bluesky %r: %s%s", q, e, hint)
                    break
                posts = data.get("posts", [])
                for p in posts:
                    post = parse_post(p, q)
                    if post:
                        fetched += 1
                        yield post
                cursor = data.get("cursor")
                if not posts or not cursor:
                    break


def parse_post(p: dict, query: str = "") -> Post | None:
    record = p.get("record", {})
    text = record.get("text", "")
    if not text:
        return None
    handle = p.get("author", {}).get("handle", "")
    rkey = p.get("uri", "").rsplit("/", 1)[-1]
    return Post(
        source="bluesky",
        native_id=p.get("cid") or p.get("uri", ""),
        kind="comment" if record.get("reply") else "post",
        text=text,
        community=f"bsky:{query}" if query else "bluesky",
        author=handle,
        url=f"https://bsky.app/profile/{handle}/post/{rkey}",
        created_utc=iso_to_epoch(record.get("createdAt")),
        score=int(p.get("likeCount", 0)) + int(p.get("repostCount", 0)),
        num_comments=int(p.get("replyCount", 0)),
        query=query,
        lang=",".join(record.get("langs", []) or []),
    )
