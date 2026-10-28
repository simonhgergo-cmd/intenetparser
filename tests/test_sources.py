import json
import tempfile
import unittest
from pathlib import Path

from iparse.sources import appstore, bluesky, hackernews, importer, mastodon, reddit, stackexchange, tiktok, youtube
from iparse.sources import load, REGISTRY


class FakeClient:
    """Returns canned JSON for the first URL fragment that matches."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def get_json(self, url, params=None, headers=None):
        self.calls.append((url, params))
        for frag, resp in self.routes.items():
            if frag in url:
                return resp(params) if callable(resp) else resp
        raise AssertionError(f"unexpected url {url}")


REDDIT_LISTING = {"data": {"after": None, "children": [
    {"kind": "t3", "data": {"id": "abc", "title": "Daycare costs", "selftext": "I can't afford daycare.",
                            "subreddit": "Parenting", "author": "u1", "permalink": "/r/Parenting/comments/abc/x/",
                            "created_utc": 1700000000, "score": 42, "num_comments": 2}},
    {"kind": "t3", "data": {"id": "pin", "title": "Rules", "stickied": True}},
]}}
REDDIT_COMMENTS = [{}, {"data": {"children": [
    {"kind": "t1", "data": {"id": "c1", "body": "Same here", "author": "u2", "permalink": "/c1", "score": 5,
                            "created_utc": 1700000100, "replies": {"data": {"children": [
                                {"kind": "t1", "data": {"id": "c2", "body": "[deleted]", "author": "x"}},
                                {"kind": "t1", "data": {"id": "c3", "body": "Nested reply", "author": "u3",
                                                        "permalink": "/c3", "score": 1, "replies": ""}}]}}}},
    {"kind": "more", "data": {}},
]}}]


class SourceTests(unittest.TestCase):
    def test_registry_loads_every_source(self):
        for name in REGISTRY:
            self.assertTrue(load(name).name)

    def test_reddit_listing_stream_and_top_comments(self):
        stream = {"data": {"after": None, "children": [
            {"kind": "t1", "data": {"id": "s1", "body": "I hate daycare waitlists", "subreddit": "Parenting",
                                    "link_id": "t3_zzz", "permalink": "/s1", "score": 3, "author": "u9"}},
            {"kind": "t1", "data": {"id": "s2", "body": "x", "author": "AutoModerator"}}]}}
        client = FakeClient({"/comments/abc": REDDIT_COMMENTS, "/r/Parenting/comments": stream,
                             "/r/Parenting/top": REDDIT_LISTING})
        src = reddit.RedditSource({"subreddits": ["Parenting"], "comments_per_post": 10, "mode": "official",
                                   "top_post_comments": 3}, client)
        posts = list(src.collect())
        self.assertEqual([p.native_id for p in posts], ["abc", "s1", "c1", "c3"])
        self.assertEqual(posts[0].community, "r/Parenting")
        self.assertEqual(posts[1].parent_id, "reddit:zzz")
        self.assertEqual(posts[2].parent_id, "reddit:abc")
        self.assertTrue(client.calls[0][0].endswith(".json"))

    def test_reddit_skips_comments_of_known_posts(self):
        client = FakeClient({"/r/Parenting/comments": {"data": {"children": []}},
                             "/r/Parenting/top": REDDIT_LISTING})
        src = reddit.RedditSource({"subreddits": ["Parenting"], "mode": "official", "top_post_comments": 3},
                                  client, known={"abc"})
        self.assertEqual([p.native_id for p in src.collect()], ["abc"])
        self.assertFalse(any("/comments/abc" in url for url, _ in client.calls))

    def test_reddit_ignores_redirected_subreddit_search(self):
        client = FakeClient({"/r/nope/comments": {"data": {"children": []}},
                             "/r/nope/top": {"data": {"children": [{"kind": "t5", "data": {"id": "x"}}]}}})
        src = reddit.RedditSource({"subreddits": ["nope"], "mode": "official"}, client)
        self.assertEqual(list(src.collect()), [])

    def test_reddit_archive_mode(self):
        now = 1_800_000_000

        def posts(params):
            if params["limit"] == 1:  # reachability probe
                return {"data": []}
            if params.get("before"):  # second page
                return {"data": [{"id": "old", "title": "Old", "selftext": "", "subreddit": "Parenting",
                                  "created_utc": now - 100_000}]}
            return {"data": [{"id": f"p{i}", "title": "Rent is a nightmare", "selftext": "", "subreddit": "Parenting",
                              "created_utc": now - i * 100, "score": None} for i in range(1, 101)]}

        comments = {"data": [{"id": "k1", "body": "I wish there was an app for this", "subreddit": "Parenting",
                              "link_id": "t3_p1", "created_utc": now}]}
        client = FakeClient({"/posts/search": posts, "/comments/search": comments})
        src = reddit.RedditSource({"subreddits": ["Parenting"], "posts_per_listing": 105, "comments_per_sub": 5}, client)
        got = list(src.collect())
        self.assertEqual([p.native_id for p in got], [f"p{i}" for i in range(1, 101)] + ["old", "k1"])
        self.assertEqual(got[0].url, "https://www.reddit.com/r/Parenting/comments/p1/")
        self.assertEqual(got[-1].url, "https://www.reddit.com/r/Parenting/comments/p1/_/k1/")
        self.assertEqual(got[-1].parent_id, "reddit:p1")
        second_page = [p for url, p in client.calls if "/posts/search" in url and p.get("before")]
        self.assertEqual(second_page[0]["before"], now - 100 * 100)
        self.assertTrue(all("arctic-shift" in url for url, _ in client.calls))

    def test_reddit_auto_falls_back_to_official_when_archive_down(self):
        class Down(FakeClient):
            def get_json(self, url, params=None, headers=None):
                if "arctic-shift" in url:
                    raise OSError("connection refused")
                return super().get_json(url, params, headers)

        client = Down({"/r/Parenting/comments": {"data": {"children": []}}, "/r/Parenting/top": REDDIT_LISTING})
        posts = list(reddit.RedditSource({"subreddits": ["Parenting"]}, client).collect())
        self.assertEqual([p.native_id for p in posts], ["abc"])  # no per-post requests without an app
        self.assertTrue(any("www.reddit.com" in url for url, _ in client.calls))

    def test_hackernews_hit(self):
        hit = {"objectID": "9", "comment_text": "<p>I wish there was a <i>better</i> tool</p>", "author": "pg",
               "created_at_i": 1700000000, "story_id": 1}
        p = hackernews.parse_hit(hit, "q")
        self.assertEqual(p.kind, "comment")
        self.assertEqual(p.text, "I wish there was a better tool")
        self.assertEqual(p.parent_id, "hackernews:1")

    def test_bluesky_post(self):
        p = bluesky.parse_post({"uri": "at://did:plc:x/app.bsky.feed.post/3k", "cid": "bafy",
                                "author": {"handle": "a.bsky.social"},
                                "record": {"text": "so frustrating", "createdAt": "2024-01-01T00:00:00Z"},
                                "likeCount": 3, "repostCount": 1}, "q")
        self.assertEqual(p.url, "https://bsky.app/profile/a.bsky.social/post/3k")
        self.assertEqual(p.score, 4)
        self.assertGreater(p.created_utc, 0)

    def test_mastodon_skips_boosts(self):
        self.assertIsNone(mastodon.parse_status({"id": "1", "content": "<p>x</p>", "reblog": {"id": "2"}}))
        p = mastodon.parse_status({"id": "1", "uri": "u", "content": "<p>Hello<br>world</p>",
                                   "account": {"acct": "a@b"}, "created_at": "2024-01-01T00:00:00Z"}, "AskFedi")
        self.assertEqual(p.text, "Hello\nworld")
        self.assertEqual(p.community, "#AskFedi")

    def test_stackexchange_question(self):
        p = stackexchange.parse_question({"question_id": 5, "title": "How do I &amp; stop", "body": "<p>Help</p>",
                                          "score": 3, "owner": {"user_id": 7}, "link": "L"}, "parenting")
        self.assertEqual(p.native_id, "parenting:5")
        self.assertEqual(p.title, "How do I & stop")
        self.assertEqual(p.community, "se/parenting")

    def test_youtube_without_key_yields_nothing(self):
        self.assertEqual(list(youtube.YouTubeSource({}, FakeClient({})).collect()), [])

    def test_youtube_comment(self):
        item = {"id": "c1", "snippet": {"totalReplyCount": 2, "topLevelComment": {"snippet": {
            "textOriginal": "Great video", "likeCount": 9, "publishedAt": "2024-01-01T00:00:00Z",
            "authorChannelId": {"value": "UC1"}}}}}
        p = youtube.parse_comment(item, "vid", "q")
        self.assertEqual(p.url, "https://www.youtube.com/watch?v=vid&lc=c1")
        self.assertEqual(p.score, 9)

    def test_appstore_feed(self):
        feed = {"feed": {"entry": [
            {"im:name": {"label": "Budgeter"}},
            {"id": {"label": "r1"}, "im:rating": {"label": "1"}, "title": {"label": "Crashes"},
             "content": {"label": "Keeps crashing"}, "author": {"name": {"label": "x"}},
             "updated": {"label": "2024-01-01T00:00:00-07:00"}},
        ]}}
        posts = appstore.parse_feed(feed, "123", "budget")
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0].community, "app:Budgeter")
        self.assertEqual(posts[0].meta["rating"], 1)

    def test_tiktok_parsers(self):
        items = tiktok.parse_item_list({"itemList": [
            {"id": "1", "desc": "budget tips", "author": {"uniqueId": "me"}, "stats": {"diggCount": 10}},
            {"id": "2", "desc": ""}]}, "budgeting")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].url, "https://www.tiktok.com/@me/video/1")
        comments = tiktok.parse_comments({"comments": [{"cid": "c", "text": "I need this", "digg_count": 2,
                                                        "user": {"unique_id": "u"}}]}, items[0])
        self.assertEqual(comments[0].parent_id, "tiktok:1")
        rehyd = {"__DEFAULT_SCOPE__": {"webapp.video-detail": {"itemInfo": {"itemStruct": {
            "id": "3", "desc": "x", "author": {"uniqueId": "a"}}}}}}
        self.assertEqual(tiktok.parse_rehydration(rehyd, "t")[0].native_id, "3")

    def test_import_csv_and_txt(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "a.csv").write_text("username,comment,likes\nbob,I hate my commute,12\nann,,1\n")
            Path(d, "b.txt").write_text("first line\n\nsecond line\n")
            Path(d, "c.json").write_text(json.dumps([{"caption": "love it", "id": "x1"}]))
            src = importer.ImportSource({"files": [{"path": f"{d}/*", "source": "instagram"}]}, None)
            posts = list(src.collect())
        self.assertEqual([p.text for p in posts], ["I hate my commute", "first line", "second line", "love it"])
        self.assertEqual(posts[0].score, 12)
        self.assertEqual(posts[3].native_id, "x1")
        self.assertTrue(all(p.source == "instagram" for p in posts))


if __name__ == "__main__":
    unittest.main()
