"""Glue between config, sources, storage, analysis and outputs."""
from __future__ import annotations

import copy
import logging
import os
import queue
import re
import threading
import time
import tomllib
from concurrent.futures import ProcessPoolExecutor
from functools import partial
from pathlib import Path

from . import catalog, sources
from .analysis import ANALYSIS_VERSION, aggregate, analyze_post
from .http import Client
from .store import Store

log = logging.getLogger("iparse")

# catalog field -> (source name, config key)
CATALOG_FIELDS = {"reddit": ("reddit", "subreddits"), "se": ("stackexchange", "sites"),
                  "mastodon": ("mastodon", "hashtags"), "apps": ("appstore", "search_terms")}


def load_config(path: str | Path) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


def open_store(cfg: dict) -> Store:
    st = cfg.get("storage", {})
    return Store(st.get("db", "data/iparse.db"), st.get("author_salt", "intenetparser"))


def make_client(cfg: dict) -> Client:
    http = cfg.get("http", {})
    return Client(min_interval=float(http.get("min_interval", 1.0)),
                  host_intervals={k: float(v) for k, v in http.get("hosts", {}).items()})


def source_configs(cfg: dict) -> dict[str, dict]:
    """Source sections with the selected catalog groups' communities merged in."""
    out = copy.deepcopy(cfg.get("sources", {}))
    cat = cfg.get("catalog", {})
    groups = catalog.select(cat.get("groups", ["*"]), bool(cat.get("include_sensitive", False)))
    for group in groups.values():
        for field, (src, key) in CATALOG_FIELDS.items():
            if group[field] and src in out:
                current = out[src].setdefault(key, [])
                current += [x for x in group[field] if x not in current]
    return out


def collect(cfg: dict, store: Store, only: list[str] | None = None) -> dict[str, tuple[int, int]]:
    """Run every enabled source in its own thread; this thread writes to the database."""
    client = make_client(cfg)
    jobs = []
    for name, scfg in source_configs(cfg).items():
        if (only and name not in only) or (not only and not scfg.get("enabled", False)):
            continue
        if name not in sources.REGISTRY:
            log.warning("Unknown source %r in config", name)
            continue
        jobs.append((name, scfg))

    q: queue.Queue = queue.Queue(maxsize=100)

    def worker(name: str, scfg: dict, known: set[str]) -> None:
        batch = []
        try:
            for post in sources.load(name)(scfg, client, known).collect():
                batch.append(post)
                if len(batch) >= 500:
                    q.put((name, batch))
                    batch = []
        except Exception as e:  # one broken source must not stop the others
            log.error("%s failed: %s", name, e)
        finally:
            q.put((name, batch))
            q.put((name, None))

    results = {name: (0, 0) for name, _ in jobs}
    for name, scfg in jobs:
        log.info("Starting %s", name)
        threading.Thread(target=worker, args=(name, scfg, store.known_ids(name)), daemon=True).start()

    running, started, last_log = len(jobs), time.time(), time.time()
    while running:
        name, batch = q.get()
        if batch is None:
            running -= 1
            log.info("%s done: %d new, %d updated", name, *results[name])
            continue
        n, u = store.upsert_posts(batch)
        results[name] = (results[name][0] + n, results[name][1] + u)
        if time.time() - last_log > 30:
            total = sum(r[0] for r in results.values())
            log.info("%d new posts so far (%.0f min) %s", total, (time.time() - started) / 60,
                     {k: v[0] for k, v in results.items()})
            last_log = time.time()
    return results


def _analyze_chunk(posts: list[dict], community_map: dict) -> list[dict]:
    return [analyze_post(p, community_map) for p in posts]


def analyze(cfg: dict, store: Store, everything: bool = False, workers: int | None = None) -> int:
    """Analyse new posts, in parallel across CPU cores when there are many."""
    community_map = cfg.get("segments", {}).get("communities", {})
    ids = store.pending_ids(None if everything else ANALYSIS_VERSION)
    chunk = 2000
    batches = (store.posts_by_ids(ids[i:i + chunk]) for i in range(0, len(ids), chunk))
    workers = workers or int(cfg.get("analysis", {}).get("workers", 0)) or os.cpu_count() or 1
    total = 0
    if len(ids) < 5000 or workers == 1:
        for posts in batches:
            total += store.save_analysis(_analyze_chunk(posts, community_map))
        return total
    with ProcessPoolExecutor(workers) as pool:
        for rows in pool.map(partial(_analyze_chunk, community_map=community_map), batches):
            total += store.save_analysis(rows)
            log.info("Analysed %d / %d", total, len(ids))
    return total


def prune(cfg: dict, store: Store) -> int:
    """Drop posts older than [storage] keep_days (0 = keep everything)."""
    days = float(cfg.get("storage", {}).get("keep_days", 0))
    return store.prune(time.time() - days * 86400) if days > 0 else 0


def build_aggregate(cfg: dict, store: Store) -> dict:
    a = cfg.get("analysis", {})
    return aggregate(store.joined(), min_mentions=int(a.get("min_mentions", 2)),
                     top=int(a.get("top", 25)), min_segment_posts=int(a.get("min_segment_posts", 10)))


def _pages(n, per_page) -> int:
    return max(1, -(-int(n) // per_page))


def plan(cfg: dict) -> list[dict]:
    """Rough requests / items / minutes per enabled source for one cycle."""
    client = make_client(cfg)
    iv = lambda host: client.host_intervals.get(host, client.min_interval)  # noqa: E731
    rows = []
    for name, c in source_configs(cfg).items():
        if not c.get("enabled"):
            continue
        g = lambda k, d=0: c.get(k, d)  # noqa: E731
        if name == "reddit":
            subs, searches = len(g("subreddits", [])), len(g("searches", []))
            top, per_listing = int(g("top_post_comments", 3)), int(g("posts_per_listing", 100))
            req = subs * (_pages(per_listing, 100) + _pages(g("comments_per_sub", 100), 100) + top) \
                + searches * (_pages(per_listing, 100) + top)
            items = (subs + searches) * (per_listing + top * int(g("comments_per_post", 30))) \
                + subs * int(g("comments_per_sub", 100))
            authed = g("client_id") and g("client_secret")
            secs = req * iv("oauth.reddit.com" if authed else "www.reddit.com")
            note = f"{subs} subreddits" + ("" if authed else " - add client_id/secret for ~10x speed")
        elif name == "hackernews":
            req = len(g("queries", [])) * len(g("tags", ["story", "comment"])) * _pages(g("max_per_query", 200), 100)
            items, secs, note = req * 100, req * iv("hn.algolia.com"), ""
        elif name == "bluesky":
            req = len(g("queries", [])) * _pages(g("max_per_query", 200), 100)
            items, secs, note = req * 100, req * iv("public.api.bsky.app"), ""
        elif name == "mastodon":
            per_inst = len(g("hashtags", [])) * _pages(g("max_per_tag", 200), 40)
            req = per_inst * len(g("instances", ["mastodon.social"]))
            items, secs, note = req * 40, per_inst * client.min_interval, f"{len(g('hashtags', []))} hashtags"
        elif name == "stackexchange":
            req = len(g("sites", [])) * len(g("queries") or [None]) * _pages(g("max_per_site", 200), 100)
            items, secs = req * 100, req * iv("api.stackexchange.com")
            note = f"{len(g('sites', []))} sites" + ("" if g("key") or req <= 300 else " - over 300/day: add a free key")
        elif name == "appstore":
            apps = len(g("search_terms", [])) * int(g("apps_per_term", 3)) + len(g("app_ids", []))
            req = len(g("search_terms", [])) + apps * int(g("pages_per_app", 2))
            items, secs = apps * int(g("pages_per_app", 2)) * 50, req * iv("itunes.apple.com")
            note = f"{len(g('search_terms', []))} search terms"
        elif name == "youtube":
            vids = len(g("queries", [])) * int(g("videos_per_query", 10)) + len(g("video_ids", []))
            req = len(g("queries", [])) + vids * _pages(g("comments_per_video", 100), 100)
            items, secs = vids * int(g("comments_per_video", 100)), req * iv("www.googleapis.com")
            note = "" if g("api_key") else "needs api_key"
        elif name == "tiktok":
            tags, vids = len(g("hashtags", [])), int(g("videos_per_tag", 8))
            req = tags * (1 + vids)
            items = tags * vids * (1 + int(g("comments_per_video", 50)))
            secs = req * float(g("delay_seconds", 4)) * (1 + int(g("scrolls_per_page", 4)))
            note = "best case; TikTok often blocks logged-out browsing"
        else:
            req, items, secs, note = 0, 0, 0, "local files"
        rows.append({"source": name, "requests": req, "items": items, "minutes": secs / 60, "note": note})
    return rows


def discover(cfg: dict, query: str) -> list[dict]:
    reddit = sources.load("reddit")(cfg.get("sources", {}).get("reddit", {}), make_client(cfg))
    return reddit.discover(query)


def parse_interval(value: str) -> int:
    m = re.fullmatch(r"\s*(\d+)\s*([smhd]?)\s*", str(value))
    if not m:
        raise ValueError(f"Bad interval {value!r}, use e.g. 30m, 6h, 1d")
    return int(m.group(1)) * {"": 1, "s": 1, "m": 60, "h": 3600, "d": 86400}[m.group(2)]


def output_paths(cfg: dict) -> tuple[Path, Path]:
    out = cfg.get("output", {})
    return Path(out.get("report", "reports/report.html")), Path(out.get("exports", "exports"))
