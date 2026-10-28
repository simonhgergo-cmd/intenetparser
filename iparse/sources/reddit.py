"""Reddit via its public JSON listings.

Works without an account. Optionally set `client_id`/`client_secret` from a
free "script" app (https://www.reddit.com/prefs/apps) to use the OAuth API,
which is more reliable from servers that Reddit rate-limits or blocks.
Reddit's free API terms cover non-commercial use.
"""
from __future__ import annotations

import base64
import json
import time
from typing import Iterator

from ..http import HttpError
from ..models import Post
from .base import Source


class RedditSource(Source):
    name = "reddit"

    def __init__(self, cfg, client):
        super().__init__(cfg, client)
        self._token: str | None = None
        self._token_expires = 0.0

    # --- transport -------------------------------------------------------
    def _auth_headers(self) -> dict:
        cid, secret = self.cfg.get("client_id"), self.cfg.get("client_secret")
        if not (cid and secret):
            return {}
        if not self._token or time.time() > self._token_expires - 60:
            basic = base64.b64encode(f"{cid}:{secret}".encode()).decode()
            raw = self.client.request(
                "https://www.reddit.com/api/v1/access_token",
                headers={"Authorization": f"Basic {basic}",
                         "Content-Type": "application/x-www-form-urlencoded"},
                data=b"grant_type=client_credentials", method="POST")
            tok = json.loads(raw)
            self._token = tok["access_token"]
            self._token_expires = time.time() + tok.get("expires_in", 3600)
        return {"Authorization": f"Bearer {self._token}"}

    def _get(self, path: str, params: dict):
        headers = self._auth_headers()
        base = "https://oauth.reddit.com" if headers else "https://www.reddit.com"
        if not headers and not path.endswith(".json"):
            path += ".json"
        params = {"raw_json": 1, **params}
        return self.client.get_json(base + path, params=params, headers=headers)

    # --- collection ------------------------------------------------------
    def collect(self) -> Iterator[Post]:
        sort = self.cfg.get("sort", "top")
        period = self.cfg.get("time", "week")
        per_listing = int(self.cfg.get("posts_per_listing", 50))
        comments = int(self.cfg.get("comments_per_post", 30))

        for sub in self.cfg.get("subreddits", []):
            yield from self._listing(f"/r/{sub}/{sort}", {"t": period}, per_listing, comments, query="")
        for q in self.cfg.get("searches", []):
            yield from self._listing("/search", {"q": q, "sort": "relevance", "t": period},
                                     per_listing, comments, query=q)

    def _listing(self, path, params, limit, comments, query) -> Iterator[Post]:
        after = None
        fetched = 0
        while fetched < limit:
            try:
                data = self._get(path, {**params, "limit": min(100, limit - fetched), "after": after})
            except HttpError as e:
                self.log.warning("Skipping %s: %s", path, e)
                return
            children = data.get("data", {}).get("children", [])
            if not children:
                return
            for child in children:
                post = parse_post(child.get("data", {}), query)
                if post is None:
                    continue
                fetched += 1
                yield post
                if comments and post.num_comments:
                    yield from self._comments(post, comments)
            after = data["data"].get("after")
            if not after:
                return

    def _comments(self, post: Post, limit: int) -> Iterator[Post]:
        try:
            data = self._get(f"/comments/{post.native_id}", {"limit": limit, "depth": 2, "sort": "top"})
        except HttpError as e:
            self.log.warning("Skipping comments for %s: %s", post.native_id, e)
            return
        if isinstance(data, list) and len(data) > 1:
            yield from parse_comments(data[1], post, limit)


def parse_post(d: dict, query: str = "") -> Post | None:
    if not d.get("id") or d.get("stickied"):
        return None
    return Post(
        source="reddit",
        native_id=d["id"],
        kind="post",
        title=d.get("title", ""),
        text=d.get("selftext", "") or "",
        community=f"r/{d.get('subreddit', '')}",
        author=d.get("author", ""),
        url="https://www.reddit.com" + d.get("permalink", ""),
        created_utc=float(d.get("created_utc", 0)),
        score=int(d.get("score", 0)),
        num_comments=int(d.get("num_comments", 0)),
        query=query,
        meta={"flair": d.get("link_flair_text") or ""},
    )


def parse_comments(listing: dict, parent: Post, limit: int) -> Iterator[Post]:
    count = 0
    stack = list(reversed(listing.get("data", {}).get("children", [])))
    while stack and count < limit:
        node = stack.pop()
        if node.get("kind") != "t1":
            continue
        d = node.get("data", {})
        body = d.get("body", "")
        if body and body not in ("[deleted]", "[removed]") and d.get("author") != "AutoModerator":
            count += 1
            yield Post(
                source="reddit",
                native_id=d["id"],
                kind="comment",
                text=body,
                community=parent.community,
                author=d.get("author", ""),
                url="https://www.reddit.com" + d.get("permalink", ""),
                created_utc=float(d.get("created_utc", 0)),
                score=int(d.get("score", 0)),
                parent_id=parent.id,
                query=parent.query,
            )
        replies = d.get("replies")
        if isinstance(replies, dict):
            stack.extend(reversed(replies.get("data", {}).get("children", [])))
