"""Apple App Store customer reviews via Apple's free public RSS feed.

Low-star reviews of popular apps are a direct list of unmet needs.
Apps can be given by id, or found by search term (top results).
"""
from __future__ import annotations

from typing import Iterator

from ..http import HttpError
from ..models import Post
from .base import Source, iso_to_epoch


class AppStoreSource(Source):
    name = "appstore"

    def collect(self) -> Iterator[Post]:
        country = self.cfg.get("country", "us")
        apps: dict[str, str] = {str(a): "" for a in self.cfg.get("app_ids", [])}
        for term in self.cfg.get("search_terms", []):
            apps.update(self._search(term, country))
        pages = min(int(self.cfg.get("pages_per_app", 3)), 10)
        for app_id, term in apps.items():
            for page in range(1, pages + 1):
                url = (f"https://itunes.apple.com/{country}/rss/customerreviews/"
                       f"page={page}/id={app_id}/sortby=mostrecent/json")
                try:
                    data = self.client.get_json(url)
                except HttpError as e:
                    self.log.warning("Reviews for app %s unavailable: %s", app_id, e)
                    break
                entries = parse_feed(data, app_id, term)
                if not entries:
                    break
                yield from entries

    def _search(self, term: str, country: str) -> dict[str, str]:
        try:
            data = self.client.get_json("https://itunes.apple.com/search", {
                "term": term, "entity": "software", "country": country,
                "limit": int(self.cfg.get("apps_per_term", 5))})
        except HttpError as e:
            self.log.warning("App search %r failed: %s", term, e)
            return {}
        return {str(r["trackId"]): term for r in data.get("results", []) if r.get("trackId")}


def parse_feed(data: dict, app_id: str, term: str = "") -> list[Post]:
    feed = data.get("feed", {})
    entries = feed.get("entry", [])
    if isinstance(entries, dict):
        entries = [entries]
    app_name = ""
    out = []
    for e in entries:
        if "im:rating" not in e:  # first entry can be the app itself
            app_name = e.get("im:name", {}).get("label", app_name)
            continue
        rating = int(e["im:rating"]["label"])
        out.append(Post(
            source="appstore",
            native_id=e.get("id", {}).get("label", ""),
            kind="review",
            title=e.get("title", {}).get("label", ""),
            text=e.get("content", {}).get("label", ""),
            community=f"app:{app_name or app_id}",
            author=e.get("author", {}).get("name", {}).get("label", ""),
            url=f"https://apps.apple.com/app/id{app_id}",
            created_utc=iso_to_epoch(e.get("updated", {}).get("label")),
            score=int(e.get("im:voteSum", {}).get("label", 0) or 0),
            query=term,
            meta={"rating": rating, "app_id": app_id,
                  "version": e.get("im:version", {}).get("label", "")},
        ))
    return out
