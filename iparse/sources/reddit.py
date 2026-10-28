"""Reddit, three ways (`mode` in [sources.reddit]):

  archive  - Arctic Shift (https://arctic-shift.photon-reddit.com), a free
             public archive of Reddit. No account or key, 100 items per
             request. Run by a third party, not Reddit. Scores are captured
             near posting time, so they can be lower than on Reddit now.
  official - Reddit itself. With `client_id`/`client_secret` from an app
             Reddit approved (Responsible Builder Policy) you get 100
             requests/min; without them, its public JSON at ~10 requests/min.
  auto     - official if credentials are set, otherwise archive (default).
"""
from __future__ import annotations

import base64
import json
import time
from typing import Iterator

from ..http import HttpError
from ..models import Post
from .base import Source

ARCHIVE = "https://arctic-shift.photon-reddit.com/api"


class RedditSource(Source):
    name = "reddit"

    def __init__(self, cfg, client, known=None):
        super().__init__(cfg, client, known)
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
        authed = bool(self.cfg.get("client_id") and self.cfg.get("client_secret"))
        mode = self.cfg.get("mode", "auto")
        if mode == "archive" or (mode == "auto" and not authed and self._archive_reachable()):
            yield from self._collect_archive()
        else:
            yield from self._collect_official(authed)

    def _archive_reachable(self) -> bool:
        subs = self.cfg.get("subreddits") or ["AskReddit"]
        try:
            self.client.get_json(f"{ARCHIVE}/posts/search", {"subreddit": subs[0], "limit": 1})
            return True
        except (HttpError, OSError, ValueError) as e:
            self.log.warning("Arctic Shift archive unavailable (%s); reading Reddit directly instead (slower)", e)
            return False

    def _collect_archive(self) -> Iterator[Post]:
        """Per subreddit: newest posts and newest comments, 100 per request."""
        per_listing = int(self.cfg.get("posts_per_listing", 100))
        stream = int(self.cfg.get("comments_per_sub", 100))
        since = int(time.time() - 86400 * float(self.cfg.get("archive_days", 7)))
        if self.cfg.get("searches"):
            self.log.info("Reddit searches are skipped in archive mode (it can't search all of Reddit)")
        for sub in self.cfg.get("subreddits", []):
            yield from self._archive("posts", sub, per_listing, since)
            if stream:
                yield from self._archive("comments", sub, stream, since)

    def _archive(self, kind: str, sub: str, limit: int, since: int) -> Iterator[Post]:
        before, fetched = None, 0
        while fetched < limit:
            page = min(100, limit - fetched)
            try:
                data = self.client.get_json(f"{ARCHIVE}/{kind}/search", {
                    "subreddit": sub, "limit": page, "sort": "desc", "after": since, "before": before})
            except (HttpError, OSError, ValueError) as e:
                self.log.warning("Skipping r/%s %s: %s", sub, kind, e)
                return
            items = data.get("data") or []
            for d in items:
                post = parse_post(d) if kind == "posts" else parse_stream_comment({"kind": "t1", "data": d})
                if post:
                    fetched += 1
                    yield post
            oldest = int(min((d.get("created_utc") or 0) for d in items)) if items else None
            if len(items) < page or not oldest or oldest == before:
                return
            before = oldest

    def _collect_official(self, authed: bool) -> Iterator[Post]:
        """Per subreddit: one request for up to 100 posts, one for the latest 100
        comments, plus the top comments of its few highest-scoring new posts."""
        sort = self.cfg.get("sort", "top")
        period = self.cfg.get("time", "week")
        per_listing = int(self.cfg.get("posts_per_listing", 100))
        stream = int(self.cfg.get("comments_per_sub", 100))
        # without credentials Reddit allows ~10 requests/min, so skip per-post requests by default
        top_posts = int(self.cfg.get("top_post_comments", 3 if authed else 0))
        per_post = int(self.cfg.get("comments_per_post", 30))

        listings = [(f"/r/{sub}/{sort}", {"t": period}, "", sub) for sub in self.cfg.get("subreddits", [])]
        listings += [("/search", {"q": q, "sort": "relevance", "t": period}, q, None)
                     for q in self.cfg.get("searches", [])]
        for path, params, query, sub in listings:
            posts = list(self._listing(path, params, per_listing, query))
            yield from posts
            if sub and stream:
                yield from self._comment_stream(sub, stream)
            fresh = [p for p in posts if p.num_comments and p.native_id not in self.known]
            for post in sorted(fresh, key=lambda p: p.score, reverse=True)[:top_posts]:
                yield from self._comments(post, per_post)

    def _listing(self, path, params, limit, query) -> Iterator[Post]:
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
                if child.get("kind") != "t3":
                    continue  # unknown subreddits redirect to a subreddit search
                post = parse_post(child.get("data", {}), query)
                if post:
                    fetched += 1
                    yield post
            after = data["data"].get("after")
            if not after:
                return

    def _comment_stream(self, sub: str, limit: int) -> Iterator[Post]:
        """Newest comments across a whole subreddit, 100 per request."""
        after, fetched = None, 0
        while fetched < limit:
            try:
                data = self._get(f"/r/{sub}/comments", {"limit": min(100, limit - fetched), "after": after})
            except HttpError as e:
                self.log.warning("Skipping comments of r/%s: %s", sub, e)
                return
            children = data.get("data", {}).get("children", [])
            for child in children:
                post = parse_stream_comment(child)
                if post:
                    fetched += 1
                    yield post
            after = data.get("data", {}).get("after")
            if not children or not after:
                return

    def _comments(self, post: Post, limit: int) -> Iterator[Post]:
        try:
            data = self._get(f"/comments/{post.native_id}", {"limit": limit, "depth": 2, "sort": "top"})
        except HttpError as e:
            self.log.warning("Skipping comments for %s: %s", post.native_id, e)
            return
        if isinstance(data, list) and len(data) > 1:
            yield from parse_comments(data[1], post, limit)

    def discover(self, query: str, limit: int = 25) -> list[dict]:
        """Subreddits matching a keyword, biggest first."""
        data = self._get("/subreddits/search", {"q": query, "limit": limit})
        subs = [c["data"] for c in data.get("data", {}).get("children", []) if c.get("kind") == "t5"]
        subs.sort(key=lambda d: d.get("subscribers") or 0, reverse=True)
        return [{"name": d["display_name"], "subscribers": d.get("subscribers") or 0,
                 "title": d.get("title", ""), "nsfw": bool(d.get("over18"))} for d in subs]


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
        url="https://www.reddit.com" + (d.get("permalink") or f"/r/{d.get('subreddit', '')}/comments/{d['id']}/"),
        created_utc=float(d.get("created_utc", 0)),
        score=int(d.get("score") or 0),
        num_comments=int(d.get("num_comments") or 0),
        query=query,
        meta={"flair": d.get("link_flair_text") or ""},
    )


def _usable_comment(d: dict) -> bool:
    body = d.get("body", "")
    return bool(body) and body not in ("[deleted]", "[removed]") and d.get("author") != "AutoModerator"


def parse_stream_comment(child: dict) -> Post | None:
    d = child.get("data", {})
    if child.get("kind") != "t1" or not _usable_comment(d):
        return None
    link = (d.get("link_id") or "").removeprefix("t3_")
    return Post(
        source="reddit",
        native_id=d["id"],
        kind="comment",
        text=d["body"],
        community=f"r/{d.get('subreddit', '')}",
        author=d.get("author", ""),
        url="https://www.reddit.com" + (d.get("permalink")
                                        or f"/r/{d.get('subreddit', '')}/comments/{link or '_'}/_/{d['id']}/"),
        created_utc=float(d.get("created_utc", 0)),
        score=int(d.get("score") or 0),
        parent_id=f"reddit:{link}" if link else "",
        meta={"post_title": d.get("link_title", "")},
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
        if _usable_comment(d):
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
