"""Stack Exchange sites (parenting, money, cooking, workplace, ...).

Free: 300 requests/day without a key, 10,000/day with a free key from
https://stackapps.com/apps/oauth/register.
"""
from __future__ import annotations

import time
from typing import Iterator

from ..http import HttpError
from ..models import Post
from .base import Source, strip_html

API = "https://api.stackexchange.com/2.3"


class StackExchangeSource(Source):
    name = "stackexchange"

    def collect(self) -> Iterator[Post]:
        per_site = int(self.cfg.get("max_per_site", 200))
        queries = self.cfg.get("queries") or [None]
        for site in self.cfg.get("sites", []):
            for q in queries:
                yield from self._search(site, q, per_site)

    def _search(self, site: str, query: str | None, limit: int) -> Iterator[Post]:
        page, fetched = 1, 0
        while fetched < limit:
            params = {"site": site, "sort": self.cfg.get("sort", "votes"), "order": "desc",
                      "pagesize": min(100, limit - fetched), "page": page, "filter": "withbody",
                      "q": query, "key": self.cfg.get("key"),
                      "fromdate": int(time.time() - 86400 * int(self.cfg.get("days", 365)))}
            try:
                data = self.client.get_json(f"{API}/search/advanced", params)
            except HttpError as e:
                self.log.warning("Skipping %s: %s", site, e)
                return
            items = data.get("items", [])
            for item in items:
                fetched += 1
                yield parse_question(item, site, query or "")
            if data.get("backoff"):
                time.sleep(int(data["backoff"]))
            if not items or not data.get("has_more"):
                return
            page += 1


def parse_question(item: dict, site: str, query: str = "") -> Post:
    return Post(
        source="stackexchange",
        native_id=f"{site}:{item['question_id']}",
        kind="post",
        title=strip_html(item.get("title")),
        text=strip_html(item.get("body")),
        community=f"se/{site}",
        author=str(item.get("owner", {}).get("user_id", "")),
        url=item.get("link", ""),
        created_utc=float(item.get("creation_date", 0)),
        score=int(item.get("score", 0)),
        num_comments=int(item.get("answer_count", 0)),
        query=query,
        meta={"tags": item.get("tags", [])},
    )
