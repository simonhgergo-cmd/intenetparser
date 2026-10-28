import unittest

from iparse import catalog
from iparse.analysis.segments import infer_segments
from iparse.pipeline import plan, source_configs


class CatalogTests(unittest.TestCase):
    def test_select_all_skips_sensitive(self):
        chosen = catalog.select(["*"])
        self.assertIn("parents", chosen)
        self.assertNotIn("mental health (community)", chosen)
        self.assertIn("mental health (community)", catalog.select(["*"], include_sensitive=True))

    def test_select_dimension_and_exclusion(self):
        chosen = catalog.select(["region", "-India"])
        self.assertTrue(chosen)
        self.assertTrue(all(g["dim"] == "region" for g in chosen.values()))
        self.assertNotIn("India", chosen)

    def test_unknown_group(self):
        with self.assertRaises(ValueError):
            catalog.select(["martians"])

    def test_no_duplicate_subreddits_within_group(self):
        for name, g in catalog.CATALOG.items():
            self.assertEqual(len(g["reddit"]), len(set(g["reddit"])), name)

    def test_catalog_drives_segments(self):
        tags = infer_segments({"source": "reddit", "community": "r/AusFinance"}, "")
        self.assertIn("region:Australia", tags)
        tags = infer_segments({"source": "appstore", "community": "app:Foo", "query": "baby tracker"}, "")
        self.assertIn("audience:parents", tags)
        self.assertIn("audience:tech workers", infer_segments({"source": "hackernews", "community": "hackernews"}, ""))

    def test_source_configs_merges_catalog(self):
        cfg = {"catalog": {"groups": ["teachers"]},
               "sources": {"reddit": {"enabled": True, "subreddits": ["MyExtra", "Teachers"]},
                           "mastodon": {"enabled": True}}}
        out = source_configs(cfg)
        self.assertEqual(out["reddit"]["subreddits"], ["MyExtra", "Teachers", "teaching", "education"])
        self.assertIn("teachers", out["mastodon"]["hashtags"])
        self.assertEqual(cfg["sources"]["reddit"]["subreddits"], ["MyExtra", "Teachers"])  # not mutated

    def test_plan_reflects_reddit_mode(self):
        def minutes(**reddit):
            cfg = {"catalog": {"groups": []},
                   "sources": {"reddit": {"enabled": True, "subreddits": ["a"] * 100, **reddit}}}
            return plan(cfg)[0]["minutes"]
        archive, direct = minutes(), minutes(mode="official")
        app = minutes(client_id="x", client_secret="y")
        self.assertLess(archive * 3, direct)
        self.assertLess(app * 3, direct)

if __name__ == "__main__":
    unittest.main()
