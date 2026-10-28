import json
import tempfile
import unittest
from pathlib import Path

from iparse import cli
from iparse.models import Post
from iparse.pipeline import parse_interval
from iparse.store import Store

SAMPLES = [
    "I'm struggling with daycare costs. I wish there was an app that finds cheap daycare.",
    "Daycare costs are a nightmare, I'm a single mom (29F).",
    "I'm struggling with daycare costs again this year.",
    "I love my air fryer, it's been a game changer.",
    "I love my air fryer so much.",
    "Is there an app that tracks my kid's sleep? I would pay for that.",
] * 3


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.cfg = self.dir / "config.toml"
        self.cfg.write_text(f"""
[storage]
db = "{self.dir / 'db.sqlite'}"
[catalog]
groups = []
[analysis]
min_mentions = 2
min_segment_posts = 2
[output]
report = "{self.dir / 'report.html'}"
exports = "{self.dir / 'exports'}"
[sources.import]
enabled = true
[[sources.import.files]]
path = "{self.dir / 'in.jsonl'}"
source = "manual"
community = "r/Parenting"
""")
        with open(self.dir / "in.jsonl", "w") as f:
            for i, t in enumerate(SAMPLES):
                f.write(json.dumps({"id": str(i), "text": t, "score": i}) + "\n")

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *args):
        self.assertEqual(cli.main(["-c", str(self.cfg), *args]), 0)

    def test_end_to_end(self):
        self.run_cli("collect")
        self.run_cli("analyze")
        self.run_cli("report")
        self.run_cli("export", "csv")
        self.run_cli("export", "llm", "--max-chars", "3000")

        html = (self.dir / "report.html").read_text()
        self.assertIn("daycare cost", html)
        self.assertIn("audience:parents", html)
        self.assertTrue((self.dir / "exports" / "posts.csv").exists())
        packs = sorted((self.dir / "exports" / "llm").glob("pack_*.md"))
        self.assertGreater(len(packs), 1)
        self.assertIn("JSON Lines", packs[0].read_text())
        self.assertIn("Segment: all", (self.dir / "exports" / "llm" / "summary.md").read_text())

        # collecting again updates rather than duplicates
        self.run_cli("collect")
        store = Store(self.dir / "db.sqlite")
        self.assertEqual(store.counts()["posts"], len(SAMPLES))
        store.close()

    def test_store_hashes_authors(self):
        store = Store(self.dir / "s.sqlite", author_salt="salt")
        store.upsert_posts([Post(source="x", native_id="1", text="hi", author="realname")])
        row = next(store.posts())
        self.assertNotIn("realname", json.dumps(row))
        self.assertEqual(len(row["author_hash"]), 16)
        store.close()

    def test_parallel_analysis_matches_serial(self):
        from iparse.pipeline import analyze, load_config
        posts = [Post(source="x", native_id=str(i), text=SAMPLES[i % len(SAMPLES)]) for i in range(6000)]
        results = []
        for workers in (1, 2):
            store = Store(self.dir / f"w{workers}.sqlite")
            store.upsert_posts(posts)
            self.assertEqual(analyze(load_config(self.cfg), store, workers=workers), 6000)
            results.append(sorted((r["id"], json.dumps(r["problems"])) for r in store.joined()))
            self.assertEqual(store.pending_ids(1), [])
            store.close()
        self.assertEqual(results[0], results[1])

    def test_sources_run_in_parallel_and_failures_are_isolated(self):
        import time
        from unittest import mock
        from iparse import pipeline

        class Slow:
            def __init__(self, cfg, client, known):
                self.cfg = cfg

            def collect(self):
                time.sleep(0.4)
                yield Post(source=self.cfg["label"], native_id="1", text="hello")
                if self.cfg.get("boom"):
                    raise RuntimeError("source broke")

        cfg = {"catalog": {"groups": []}, "sources": {
            "reddit": {"enabled": True, "label": "a"}, "hackernews": {"enabled": True, "label": "b", "boom": True},
            "bluesky": {"enabled": True, "label": "c"}}}
        store = Store(self.dir / "par.sqlite")
        with mock.patch.object(pipeline.sources, "load", return_value=Slow):
            t = time.time()
            results = pipeline.collect(cfg, store)
            elapsed = time.time() - t
        self.assertLess(elapsed, 1.0)  # 3 x 0.4s sequentially would be 1.2s
        self.assertEqual(results, {"reddit": (1, 0), "hackernews": (1, 0), "bluesky": (1, 0)})
        store.close()

    def test_parse_interval(self):
        self.assertEqual(parse_interval("6h"), 21600)
        self.assertEqual(parse_interval("30m"), 1800)
        with self.assertRaises(ValueError):
            parse_interval("soon")


if __name__ == "__main__":
    unittest.main()
