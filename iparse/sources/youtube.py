"""YouTube video comments via the YouTube Data API v3.

Needs a free API key (Google Cloud console -> enable "YouTube Data API v3"
-> create API key). The free quota is 10,000 units/day: a search costs 100,
a page of comments costs 1. No billing account is needed.
"""
from __future__ import annotations

from typing import Iterator

from ..http import HttpError
from ..models import Post
from .base import Source, iso_to_epoch

API = "https://www.googleapis.com/youtube/v3"


class YouTubeSource(Source):
    name = "youtube"

    def collect(self) -> Iterator[Post]:
        key = self.cfg.get("api_key")
        if not key:
            self.log.warning("YouTube skipped: set api_key (free) in config")
            return
        videos = list(self.cfg.get("video_ids", []))
        for q in self.cfg.get("queries", []):
            videos += self._search(key, q)
        per_video = int(self.cfg.get("comments_per_video", 100))
        for vid, query in dict.fromkeys(v if isinstance(v, tuple) else (v, "") for v in videos):
            yield from self._comments(key, vid, query, per_video)

    def _search(self, key: str, query: str) -> list[tuple[str, str]]:
        try:
            data = self.client.get_json(f"{API}/search", {
                "key": key, "q": query, "part": "id", "type": "video", "order": "relevance",
                "maxResults": int(self.cfg.get("videos_per_query", 10)),
                "relevanceLanguage": self.cfg.get("lang")})
        except HttpError as e:
            self.log.warning("YouTube search %r failed: %s", query, e)
            return []
        return [(i["id"]["videoId"], query) for i in data.get("items", []) if i.get("id", {}).get("videoId")]

    def _comments(self, key: str, video_id: str, query: str, limit: int) -> Iterator[Post]:
        token, fetched = None, 0
        while fetched < limit:
            try:
                data = self.client.get_json(f"{API}/commentThreads", {
                    "key": key, "videoId": video_id, "part": "snippet", "order": "relevance",
                    "maxResults": min(100, limit - fetched), "textFormat": "plainText",
                    "pageToken": token})
            except HttpError as e:
                self.log.warning("Comments for %s unavailable: %s", video_id, e)
                return
            for item in data.get("items", []):
                fetched += 1
                yield parse_comment(item, video_id, query)
            token = data.get("nextPageToken")
            if not token:
                return


def parse_comment(item: dict, video_id: str, query: str = "") -> Post:
    s = item["snippet"]["topLevelComment"]["snippet"]
    return Post(
        source="youtube",
        native_id=item["id"],
        kind="comment",
        text=s.get("textOriginal") or s.get("textDisplay", ""),
        community=f"yt:{query}" if query else "youtube",
        author=s.get("authorChannelId", {}).get("value", "") or s.get("authorDisplayName", ""),
        url=f"https://www.youtube.com/watch?v={video_id}&lc={item['id']}",
        created_utc=iso_to_epoch(s.get("publishedAt")),
        score=int(s.get("likeCount", 0)),
        num_comments=int(item["snippet"].get("totalReplyCount", 0)),
        parent_id=f"youtube:{video_id}",
        query=query,
    )
