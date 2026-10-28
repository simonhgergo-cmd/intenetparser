import tomllib
import unittest
from pathlib import Path

from iparse.interactive import set_in_section

EXAMPLE = (Path(__file__).resolve().parent.parent / "config.example.toml").read_text()


class SetInSectionTests(unittest.TestCase):
    def test_edits_example_config(self):
        text = EXAMPLE
        text = set_in_section(text, "catalog", "groups", ["parents", "Canada"])
        text = set_in_section(text, "catalog", "include_sensitive", True)
        text = set_in_section(text, "sources.reddit", "client_id", "abc")
        text = set_in_section(text, "sources.reddit", "client_secret", "s3c")
        text = set_in_section(text, "sources.youtube", "enabled", True)
        text = set_in_section(text, "storage", "author_salt", "xyz")
        cfg = tomllib.loads(text)
        self.assertEqual(cfg["catalog"], {"groups": ["parents", "Canada"], "include_sensitive": True})
        self.assertEqual(cfg["sources"]["reddit"]["client_id"], "abc")
        self.assertEqual(cfg["sources"]["reddit"]["client_secret"], "s3c")
        self.assertTrue(cfg["sources"]["youtube"]["enabled"])
        self.assertFalse(cfg["sources"]["tiktok"]["enabled"])  # other sections untouched
        self.assertEqual(cfg["storage"]["author_salt"], "xyz")

    def test_running_twice_replaces_instead_of_duplicating(self):
        text = set_in_section(EXAMPLE, "sources.reddit", "client_id", "one")
        text = set_in_section(text, "sources.reddit", "client_id", "two")
        self.assertEqual(text.count('client_id = "two"'), 1)
        self.assertNotIn('"one"', text)
        self.assertEqual(tomllib.loads(text)["sources"]["reddit"]["client_id"], "two")

    def test_missing_section_is_added(self):
        cfg = tomllib.loads(set_in_section("[a]\nx = 1\n", "b.c", "y", "z"))
        self.assertEqual(cfg, {"a": {"x": 1}, "b": {"c": {"y": "z"}}})


if __name__ == "__main__":
    unittest.main()
