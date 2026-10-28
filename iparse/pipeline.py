"""Glue between config, sources, storage, analysis and outputs."""
from __future__ import annotations

import logging
import re
import tomllib
from pathlib import Path

from . import sources
from .analysis import ANALYSIS_VERSION, aggregate, analyze_post
from .http import Client
from .store import Store

log = logging.getLogger("iparse")


def load_config(path: str | Path) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)


def open_store(cfg: dict) -> Store:
    st = cfg.get("storage", {})
    return Store(st.get("db", "data/iparse.db"), st.get("author_salt", "intenetparser"))


def collect(cfg: dict, store: Store, only: list[str] | None = None) -> dict[str, tuple[int, int]]:
    client = Client(min_interval=float(cfg.get("http", {}).get("min_interval", 2.0)))
    results = {}
    for name, scfg in cfg.get("sources", {}).items():
        if only and name not in only:
            continue
        if not only and not scfg.get("enabled", False):
            continue
        if name not in sources.REGISTRY:
            log.warning("Unknown source %r in config", name)
            continue
        log.info("Collecting from %s ...", name)
        src = sources.load(name)(scfg, client)
        new = updated = 0
        batch = []
        try:
            for post in src.collect():
                batch.append(post)
                if len(batch) >= 200:
                    n, u = store.upsert_posts(batch)
                    new, updated, batch = new + n, updated + u, []
                    log.info("  %s: %d new so far", name, new)
        except Exception as e:  # one broken source must not stop the others
            log.error("  %s failed: %s", name, e)
        n, u = store.upsert_posts(batch)
        results[name] = (new + n, updated + u)
        log.info("  %s: %d new, %d updated", name, *results[name])
    return results


def analyze(cfg: dict, store: Store, everything: bool = False) -> int:
    community_map = cfg.get("segments", {}).get("communities", {})
    version = None if everything else ANALYSIS_VERSION
    rows, total = [], 0
    for post in store.posts(unanalyzed_for_version=version):
        rows.append(analyze_post(post, community_map))
        if len(rows) >= 1000:
            total += store.save_analysis(rows)
            rows = []
    return total + store.save_analysis(rows)


def build_aggregate(cfg: dict, store: Store) -> dict:
    a = cfg.get("analysis", {})
    return aggregate(store.joined(), min_mentions=int(a.get("min_mentions", 2)),
                     top=int(a.get("top", 25)), min_segment_posts=int(a.get("min_segment_posts", 10)))


def parse_interval(value: str) -> int:
    m = re.fullmatch(r"\s*(\d+)\s*([smhd]?)\s*", str(value))
    if not m:
        raise ValueError(f"Bad interval {value!r}, use e.g. 30m, 6h, 1d")
    return int(m.group(1)) * {"": 1, "s": 1, "m": 60, "h": 3600, "d": 86400}[m.group(2)]


def output_paths(cfg: dict) -> tuple[Path, Path]:
    out = cfg.get("output", {})
    return Path(out.get("report", "reports/report.html")), Path(out.get("exports", "exports"))
