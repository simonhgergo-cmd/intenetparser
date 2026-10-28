from __future__ import annotations

import importlib

from .base import Source

REGISTRY = {
    "reddit": "reddit:RedditSource",
    "hackernews": "hackernews:HackerNewsSource",
    "bluesky": "bluesky:BlueskySource",
    "mastodon": "mastodon:MastodonSource",
    "stackexchange": "stackexchange:StackExchangeSource",
    "youtube": "youtube:YouTubeSource",
    "appstore": "appstore:AppStoreSource",
    "tiktok": "tiktok:TikTokSource",
    "import": "importer:ImportSource",
}


def load(name: str) -> type[Source]:
    module, cls = REGISTRY[name].split(":")
    return getattr(importlib.import_module(f".{module}", __name__), cls)
