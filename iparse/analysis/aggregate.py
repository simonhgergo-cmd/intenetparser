"""Roll per-post analysis up into ranked themes for every segment."""
from __future__ import annotations

import math
import time
from collections import Counter, defaultdict

ALL = "all"


def _engagement(score: int) -> float:
    return 1.0 + math.log1p(max(score or 0, 0))


class _Themes:
    def __init__(self):
        self.mentions: Counter[str] = Counter()
        self.weight: defaultdict[str, float] = defaultdict(float)
        self.posts: defaultdict[str, set] = defaultdict(set)
        self.sources: defaultdict[str, Counter] = defaultdict(Counter)
        self.examples: defaultdict[str, list] = defaultdict(list)
        self.sentiment: defaultdict[str, float] = defaultdict(float)

    def add(self, key: str, post: dict, signal: dict, weight: float) -> None:
        if post["id"] in self.posts[key]:
            return  # count each post once per theme
        self.posts[key].add(post["id"])
        self.mentions[key] += 1
        self.weight[key] += weight
        self.sources[key][post["source"]] += 1
        self.sentiment[key] += post.get("sentiment") or 0.0
        self.examples[key].append((post.get("score") or 0, signal["quote"], post.get("url") or "",
                                   post["source"]))

    def merge_related(self) -> None:
        """Fold a longer theme into a shorter one it starts or ends with, when the
        shorter one is at least as common: "meal planning for my family" ->
        "meal planning", "afford textbook" -> "textbook"."""
        keys = sorted(self.mentions, key=lambda k: (len(k.split()), -self.mentions[k]))
        for long in [k for k in keys if len(k.split()) > 1]:
            for short in keys:
                if short != long and short in self.mentions and long in self.mentions \
                        and len(short.split()) < len(long.split()) \
                        and (long.startswith(short + " ") or long.endswith(" " + short)) \
                        and self.mentions[short] >= self.mentions[long]:
                    self._fold(long, short)
                    break

    def _fold(self, src: str, dst: str) -> None:
        for pid in self.posts.pop(src):
            self.posts[dst].add(pid)
        self.mentions[dst] = len(self.posts[dst])
        del self.mentions[src]
        self.weight[dst] += self.weight.pop(src)
        self.sources[dst].update(self.sources.pop(src))
        self.examples[dst] += self.examples.pop(src)
        self.sentiment[dst] += self.sentiment.pop(src)

    def ranked(self, min_mentions: int, top: int, examples: int = 3) -> list[dict]:
        self.merge_related()
        out = []
        for key, n in self.mentions.items():
            if n < min_mentions:
                continue
            ex = sorted(self.examples[key], key=lambda e: e[0], reverse=True)
            seen, picked = set(), []
            for score, quote, url, source in ex:
                if quote not in seen:
                    seen.add(quote)
                    picked.append({"quote": quote, "url": url, "source": source, "score": score})
                if len(picked) >= examples:
                    break
            out.append({
                "theme": key,
                "mentions": n,
                "score": round(self.weight[key], 2),
                "avg_sentiment": round(self.sentiment[key] / n, 3),
                "sources": dict(self.sources[key].most_common()),
                "examples": picked,
            })
        out.sort(key=lambda t: (t["score"], t["mentions"]), reverse=True)
        return out[:top]


def aggregate(rows, min_mentions: int = 2, top: int = 25, min_segment_posts: int = 10) -> dict:
    """rows: dicts from Store.joined()."""
    rows = list(rows)
    segs: defaultdict[str, dict] = defaultdict(lambda: {
        "posts": 0, "sentiment_sum": 0.0, "problems": _Themes(), "wishes": _Themes(),
        "joys": _Themes(), "topics": Counter(), "topic_posts": Counter(),
    })
    corpus_topics: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()

    for post in rows:
        source_counts[post["source"]] += 1
        eng = _engagement(post.get("score"))
        sent = post.get("sentiment") or 0.0
        topics = set(post.get("keyphrases") or [])
        corpus_topics.update(topics)
        for seg in [ALL, *post.get("segments", [])]:
            s = segs[seg]
            s["posts"] += 1
            s["sentiment_sum"] += sent
            s["topics"].update(topics)
            for kind, boost in (("problems", 1 + max(0.0, -sent)), ("wishes", 1.0), ("joys", 1 + max(0.0, sent))):
                for sig in post.get(kind) or []:
                    key = sig.get("object")
                    if key:
                        s[kind].add(key, post, sig, eng * sig["weight"] * boost)

    total = max(len(rows), 1)
    out_segments = {}
    for name, s in segs.items():
        if name != ALL and s["posts"] < min_segment_posts:
            continue
        out_segments[name] = {
            "posts": s["posts"],
            "avg_sentiment": round(s["sentiment_sum"] / max(s["posts"], 1), 3),
            "topics": _distinctive_topics(s["topics"], s["posts"], corpus_topics, total, top,
                                          use_lift=name != ALL),
            "problems": s["problems"].ranked(min_mentions, top),
            "wishes": s["wishes"].ranked(min_mentions, top),
            "joys": s["joys"].ranked(min_mentions, top),
        }
    return {
        "generated_at": time.time(),
        "totals": {"posts": len(rows), "by_source": dict(source_counts.most_common()),
                   "segments": {k: v["posts"] for k, v in sorted(out_segments.items(), key=lambda kv: -kv[1]["posts"])}},
        "segments": out_segments,
    }


def _distinctive_topics(seg_counts: Counter, seg_n: int, corpus: Counter, corpus_n: int,
                        top: int, use_lift: bool) -> list[dict]:
    """Most-discussed phrases; for sub-segments ranked by how over-represented they are."""
    min_count = max(2, int(seg_n * 0.005))
    out = []
    for phrase, c in seg_counts.items():
        if c < min_count:
            continue
        share = c / seg_n
        lift = share / ((corpus[phrase] + 1) / (corpus_n + 1))
        rank = share * math.log1p(lift) if use_lift else share
        out.append({"topic": phrase, "posts": c, "share": round(share, 4), "lift": round(lift, 2), "_r": rank})
    out.sort(key=lambda t: t["_r"], reverse=True)
    # Drop "daycare" and "cost" when "daycare cost" covers most of their posts.
    by_phrase = {t["topic"]: t for t in out}
    kept = []
    for t in out:
        words = t["topic"].split()
        covered = any(len(o.split()) > len(words) and all(w in o.split() for w in words)
                      and by_phrase[o]["posts"] >= 0.8 * t["posts"] for o in by_phrase)
        if not covered:
            del t["_r"]
            kept.append(t)
        if len(kept) >= top:
            break
    return kept
