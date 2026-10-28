import unittest

from iparse.analysis.aggregate import aggregate
from iparse.analysis.analyzer import analyze_post, keyphrases, sentiment
from iparse.analysis.segments import age_band, infer_segments


def post(text, community="r/test", source="reddit", score=0, pid="p", **meta):
    return {"id": pid, "source": source, "community": community, "text": text, "title": "",
            "score": score, "url": f"https://x/{pid}", "meta": meta}


class AnalyzerTests(unittest.TestCase):
    def test_problem_wish_joy_objects(self):
        r = analyze_post(post("I'm struggling with meal planning. I wish there was an app that plans "
                              "groceries for me. I would pay for that. I love my air fryer."))
        self.assertEqual([s["object"] for s in r["problems"]], ["meal planning"])
        self.assertEqual([s["object"] for s in r["wishes"]], ["plan grocery", "plan grocery"])
        self.assertEqual([s["object"] for s in r["joys"]], ["air fryer"])

    def test_object_before_trigger(self):
        r = analyze_post(post("Honestly, the new update is a complete mess."))
        self.assertEqual(r["problems"][0]["object"], "update")

    def test_sentiment_direction_and_negation(self):
        self.assertGreater(sentiment("I love this, it is amazing"), 0.5)
        self.assertLess(sentiment("This is terrible and I hate it"), -0.5)
        self.assertLess(sentiment("not good at all"), 0)
        self.assertEqual(sentiment("the table is brown"), 0)

    def test_low_rating_review_counts_as_problem(self):
        r = analyze_post(post("Meh.", community="app:Budgeter", source="appstore", rating=1))
        self.assertEqual(r["problems"][0]["object"], "budgeter")
        self.assertLess(r["sentiment"], 0)

    def test_keyphrases_skip_stopwords(self):
        phrases = keyphrases("Daycare costs are insane. Daycare waitlists too.")
        self.assertIn("daycare", phrases)
        self.assertNotIn("are", phrases)


class SegmentTests(unittest.TestCase):
    def test_community_and_self_report(self):
        tags = infer_segments({"source": "reddit", "community": "r/Parenting"},
                              "As a nurse (34F) my toddler never sleeps. My landlord is awful.")
        for t in ["platform:reddit", "audience:parents", "role:healthcare worker", "age:25-34",
                  "gender:woman", "role:parent", "housing:renter"]:
            self.assertIn(t, tags)

    def test_no_false_ages(self):
        tags = infer_segments({"source": "reddit"}, "I'm 30 minutes away and drove 20m. Raised $20M.")
        self.assertFalse([t for t in tags if t.startswith(("age:", "gender:"))])

    def test_custom_community_map(self):
        tags = infer_segments({"source": "reddit", "community": "r/BabyBumps"}, "",
                              {"r/BabyBumps": ["expecting parents"]})
        self.assertIn("audience:expecting parents", tags)

    def test_age_band(self):
        self.assertEqual(age_band(19), "18-24")
        self.assertEqual(age_band(70), "65+")
        self.assertIsNone(age_band(8))


class AggregateTests(unittest.TestCase):
    def _rows(self):
        texts = [
            ("I'm struggling with daycare costs.", "r/Parenting", 100),
            ("Daycare costs are a nightmare.", "r/Parenting", 5),
            ("I'm struggling with daycare costs for twins.", "r/Parenting", 1),
            ("I hate my commute.", "r/jobs", 3),
            ("I love my kindle.", "r/college", 2),
        ]
        rows = []
        for i, (t, c, s) in enumerate(texts):
            p = post(t, community=c, score=s, pid=f"p{i}")
            rows.append({**p, **analyze_post(p)})
        return rows

    def test_themes_ranked_and_merged(self):
        agg = aggregate(self._rows(), min_mentions=1, min_segment_posts=1)
        top = agg["segments"]["all"]["problems"][0]
        self.assertEqual(top["theme"], "daycare cost")
        self.assertEqual(top["mentions"], 3)  # "daycare cost for twin" folded in
        self.assertEqual(top["examples"][0]["score"], 100)
        self.assertIn("audience:parents", agg["segments"])
        self.assertEqual(agg["totals"]["posts"], 5)

    def test_small_segments_hidden(self):
        agg = aggregate(self._rows(), min_mentions=1, min_segment_posts=3)
        self.assertIn("audience:parents", agg["segments"])
        self.assertNotIn("audience:students", agg["segments"])


if __name__ == "__main__":
    unittest.main()
