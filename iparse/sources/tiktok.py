"""TikTok, experimental: logged-out, read-only browsing of public pages.

Opens public hashtag pages and video pages in a headless browser and reads
the JSON that the page itself loads (video captions, and comments when
TikTok shows them to logged-out visitors). It never logs in, never likes,
follows or comments, and does not try to disguise itself. Expect TikTok to
show captchas or empty pages at times; when that happens this source just
yields less data.

Requires: pip install playwright && playwright install chromium
Automated access is against TikTok's terms of service; use at your own risk
and keep the volume low.
"""
from __future__ import annotations

import json
import time
from typing import Iterator

from ..models import Post
from .base import Source

ITEM_PATHS = ("/api/challenge/item_list", "/api/search/item", "/api/post/item_list")
COMMENT_PATH = "/api/comment/list"


class TikTokSource(Source):
    name = "tiktok"

    def collect(self) -> Iterator[Post]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            self.log.warning("TikTok skipped: pip install playwright && playwright install chromium")
            return

        delay = float(self.cfg.get("delay_seconds", 4))
        scrolls = int(self.cfg.get("scrolls_per_page", 4))
        videos_per_tag = int(self.cfg.get("videos_per_tag", 8))
        comments_per_video = int(self.cfg.get("comments_per_video", 50))

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=bool(self.cfg.get("headless", True)))
            page = browser.new_context(locale=self.cfg.get("locale", "en-US")).new_page()
            captured: list[tuple[str, dict]] = []

            def on_response(resp):
                url = resp.url
                if any(x in url for x in ITEM_PATHS) or COMMENT_PATH in url:
                    try:
                        captured.append((url, resp.json()))
                    except Exception:  # non-JSON or aborted responses
                        pass

            page.on("response", on_response)
            try:
                for tag in self.cfg.get("hashtags", []):
                    tag = tag.lstrip("#")
                    captured.clear()
                    page.goto(f"https://www.tiktok.com/tag/{tag}", wait_until="domcontentloaded")
                    time.sleep(delay)
                    for _ in range(scrolls):
                        page.mouse.wheel(0, 2500)
                        time.sleep(delay)
                    videos = [v for _, data in captured for v in parse_item_list(data, tag)]
                    videos += parse_rehydration(_rehydration_json(page), tag)
                    videos = list({v.native_id: v for v in videos}.values())
                    videos.sort(key=lambda v: v.score, reverse=True)
                    yield from videos

                    for video in videos[:videos_per_tag]:
                        captured.clear()
                        page.goto(video.url, wait_until="domcontentloaded")
                        time.sleep(delay)
                        for _ in range(scrolls):
                            page.mouse.wheel(0, 1500)
                            time.sleep(delay)
                        comments = [c for url, data in captured if COMMENT_PATH in url
                                    for c in parse_comments(data, video)]
                        yield from comments[:comments_per_video]
            finally:
                browser.close()


def _rehydration_json(page) -> dict:
    try:
        raw = page.locator("script#__UNIVERSAL_DATA_FOR_REHYDRATION__").first.text_content(timeout=3000)
        return json.loads(raw or "{}")
    except Exception:
        return {}


def _video_post(item: dict, tag: str) -> Post | None:
    vid, desc = item.get("id"), item.get("desc", "")
    if not vid or not desc:
        return None
    author = item.get("author", {})
    handle = author.get("uniqueId", "") if isinstance(author, dict) else str(author)
    stats = item.get("stats", {}) or {}
    return Post(
        source="tiktok",
        native_id=str(vid),
        kind="video",
        text=desc,
        community=f"#{tag}",
        author=handle,
        url=f"https://www.tiktok.com/@{handle}/video/{vid}",
        created_utc=float(item.get("createTime", 0) or 0),
        score=int(stats.get("diggCount", 0) or 0),
        num_comments=int(stats.get("commentCount", 0) or 0),
        query=tag,
    )


def parse_item_list(data: dict, tag: str) -> list[Post]:
    items = data.get("itemList") or [d.get("item", d) for d in data.get("data", []) if isinstance(d, dict)]
    return [p for p in (_video_post(i, tag) for i in items or []) if p]


def parse_rehydration(data: dict, tag: str) -> list[Post]:
    scope = data.get("__DEFAULT_SCOPE__", {})
    item = scope.get("webapp.video-detail", {}).get("itemInfo", {}).get("itemStruct")
    return [p for p in [_video_post(item, tag)] if p] if item else []


def parse_comments(data: dict, video: Post) -> list[Post]:
    out = []
    for c in data.get("comments") or []:
        text = c.get("text", "")
        if not text:
            continue
        user = c.get("user", {}) or {}
        out.append(Post(
            source="tiktok",
            native_id=str(c.get("cid")),
            kind="comment",
            text=text,
            community=video.community,
            author=user.get("unique_id", "") or user.get("uid", ""),
            url=video.url,
            created_utc=float(c.get("create_time", 0) or 0),
            score=int(c.get("digg_count", 0) or 0),
            num_comments=int(c.get("reply_comment_total", 0) or 0),
            parent_id=video.id,
            query=video.query,
        ))
    return out
