import json
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from iparse.interactive import set_in_section
from iparse.webapp import App, make_handler

OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


class WebAppTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        texts = ["I'm struggling with daycare costs.", "I'm struggling with daycare costs too."] * 3
        (d / "in.jsonl").write_text("\n".join(json.dumps({"id": str(i), "text": t}) for i, t in enumerate(texts)))
        self.cfg = d / "config.toml"
        self.app = App(self.cfg)  # creates config.toml from the example
        text = self.cfg.read_text()
        for src in ("reddit", "hackernews", "bluesky", "mastodon", "stackexchange", "appstore"):
            text = set_in_section(text, f"sources.{src}", "enabled", False)
        text = set_in_section(text, "sources.import", "enabled", True)
        text = set_in_section(text, "storage", "db", str(d / "db.sqlite"))
        text = set_in_section(text, "output", "report", str(d / "report.html"))
        text = set_in_section(text, "output", "exports", str(d / "exports"))
        text += f'\n[[sources.import.files]]\npath = "{d / "in.jsonl"}"\nsource = "manual"\n'
        self.cfg.write_text(text)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.app))
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def call(self, path, body=None, headers=None):
        hdrs = {"X-IParse": "1", "Content-Type": "application/json"} if body is not None else {}
        hdrs.update(headers or {})
        data = None if body is None else json.dumps(body).encode()
        try:
            with OPENER.open(urllib.request.Request(self.base + path, data=data, headers=hdrs), timeout=10) as r:
                return r.status, r.read().decode()
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode()

    def test_page_status_and_protection(self):
        self.assertIn("Internet Parser", self.call("/")[1])
        self.assertTrue(json.loads(self.call("/api/status")[1])["first_run"])
        self.assertEqual(self.call("/api/status", headers={"Host": "evil.example"})[0], 403)
        self.assertEqual(self.call("/api/run", {}, headers={"X-IParse": ""})[0], 403)
        self.assertEqual(self.call("/exports/..%2Fconfig.toml")[0], 404)

    def test_settings_roundtrip(self):
        s = json.loads(self.call("/api/settings")[1])
        self.assertTrue(all(g["selected"] for g in s["groups"]["region"]))
        code, body = self.call("/api/settings", {"groups": ["parents", "Canada"], "every": "1d", "keep_days": 30,
                                                 "reddit_mode": "archive", "sources": {"youtube": False}})
        self.assertEqual(json.loads(body), {"ok": True, "message": "Mentve."})
        s = json.loads(self.call("/api/settings")[1])
        chosen = [g["name"] for gs in s["groups"].values() for g in gs if g["selected"]]
        self.assertEqual(chosen, ["parents", "Canada"])
        self.assertEqual((s["every"], s["keep_days"], s["reddit_mode"]), ("1d", 30, "archive"))
        self.assertFalse(json.loads(self.call("/api/settings", {"groups": []})[1])["ok"])
        self.assertFalse(json.loads(self.call("/api/settings", {"groups": ["parents"], "every": "soon"})[1])["ok"])

    def test_run_produces_report_and_exports(self):
        self.assertTrue(json.loads(self.call("/api/run", {"loop": False})[1])["ok"])
        for _ in range(100):
            status = json.loads(self.call("/api/status")[1])
            if not status["running"]:
                break
            time.sleep(0.1)
        self.assertIsNone(status["last_error"])
        self.assertEqual(status["posts"], 6)
        self.assertIn("daycare cost", self.call("/report")[1])
        files = json.loads(self.call("/api/exports")[1])
        self.assertEqual(files[0]["name"], "summary.md")
        self.assertEqual(self.call("/exports/summary.md")[0], 200)


if __name__ == "__main__":
    unittest.main()
