import tempfile
import unittest
from pathlib import Path

from tools.check_new_articles import filter_new_articles
from tools.create_kb_entry import NATE_SUBDIR


def make_fake_vault(tmp_dir: str) -> Path:
    """Create a minimally-initialized git repo at tmp_dir so create_kb_entry's
    vault validation passes."""
    vault = Path(tmp_dir)
    (vault / ".git").mkdir()
    return vault


class FilterNewArticlesTests(unittest.TestCase):
    def test_returns_all_articles_when_vault_is_empty(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            vault = make_fake_vault(tmp_dir)
            articles = [
                {"url": "https://example.com/p/post-one", "title": "Post One"},
                {"url": "https://example.com/p/post-two", "title": "Post Two"},
            ]
            new = filter_new_articles(articles, vault)
        self.assertEqual(new, articles)

    def test_skips_articles_already_in_vault(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            vault = make_fake_vault(tmp_dir)
            nate_dir = vault / NATE_SUBDIR
            nate_dir.mkdir(parents=True)
            (nate_dir / "post-one.md").write_text("existing", encoding="utf-8")

            articles = [
                {"url": "https://example.com/p/post-one", "title": "Post One"},
                {"url": "https://example.com/p/post-two", "title": "Post Two"},
            ]
            new = filter_new_articles(articles, vault)

        self.assertEqual(len(new), 1)
        self.assertEqual(new[0]["url"], "https://example.com/p/post-two")

    def test_empty_input_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            vault = make_fake_vault(tmp_dir)
            self.assertEqual(filter_new_articles([], vault), [])


if __name__ == "__main__":
    unittest.main()
