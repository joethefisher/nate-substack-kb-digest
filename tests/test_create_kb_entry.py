import logging
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.create_kb_entry import (
    NATE_SUBDIR,
    already_in_vault,
    build_kb_markdown,
    get_vault_path,
    kb_entry_path,
    run_vault_git_ops,
    slug_from_url,
    write_kb_entry,
)


def make_fake_vault(tmp_dir: str) -> Path:
    vault = Path(tmp_dir)
    (vault / ".git").mkdir()
    return vault


def make_real_git_vault(tmp_dir: str) -> Path:
    """Init a real git repo for tests that exercise git ops."""
    vault = Path(tmp_dir)
    subprocess.run(["git", "init", "-b", "main", str(vault)], check=True, capture_output=True)
    # commit something so HEAD exists
    (vault / "seed.md").write_text("seed\n", encoding="utf-8")
    subprocess.run(["git", "add", "seed.md"], cwd=vault, check=True, capture_output=True)
    subprocess.run(
        [
            "git",
            "-c", "user.name=test",
            "-c", "user.email=test@test.local",
            "commit", "-m", "seed",
        ],
        cwd=vault, check=True, capture_output=True,
    )
    return vault


SAMPLE_SUMMARY = {
    "url": "https://natesnewsletter.substack.com/p/example-post-slug",
    "title": "Example post title",
    "tldr": "First sentence. Second sentence.",
    "key_takeaways": ["Takeaway one.", "Takeaway two."],
    "why_it_matters": "Because reasons.",
    "tags": ["ai", "strategy"],
    "published_date": "2026-05-20",
    "youtube_url": "",
}


class SlugTests(unittest.TestCase):
    def test_slug_from_substack_url(self):
        url = "https://natesnewsletter.substack.com/p/hello-world"
        self.assertEqual(slug_from_url(url), "hello-world")

    def test_slug_strips_trailing_slash(self):
        url = "https://natesnewsletter.substack.com/p/hello-world/"
        self.assertEqual(slug_from_url(url), "hello-world")

    def test_invalid_url_raises(self):
        with self.assertRaises(ValueError):
            slug_from_url("https://natesnewsletter.substack.com/about")


class GetVaultPathTests(unittest.TestCase):
    def test_missing_env_raises(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(EnvironmentError):
                get_vault_path()

    def test_nonexistent_path_raises(self):
        with patch.dict(os.environ, {"VAULT_PATH": "/nonexistent/vault"}, clear=True):
            with self.assertRaises(FileNotFoundError):
                get_vault_path()

    def test_non_git_dir_raises(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch.dict(os.environ, {"VAULT_PATH": tmp_dir}, clear=True):
                with self.assertRaises(FileNotFoundError):
                    get_vault_path()


class AlreadyInVaultTests(unittest.TestCase):
    def test_false_when_file_absent(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            vault = make_fake_vault(tmp_dir)
            self.assertFalse(
                already_in_vault(
                    "https://natesnewsletter.substack.com/p/missing-slug",
                    vault,
                )
            )

    def test_true_when_file_present(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            vault = make_fake_vault(tmp_dir)
            nate_dir = vault / NATE_SUBDIR
            nate_dir.mkdir(parents=True)
            (nate_dir / "present-slug.md").write_text("x", encoding="utf-8")
            self.assertTrue(
                already_in_vault(
                    "https://natesnewsletter.substack.com/p/present-slug",
                    vault,
                )
            )


class BuildMarkdownTests(unittest.TestCase):
    def test_frontmatter_and_sections_present(self):
        md = build_kb_markdown(SAMPLE_SUMMARY, "Full body text here.")
        self.assertTrue(md.startswith("---\n"))
        self.assertIn("name: example-post-slug", md)
        self.assertIn("type: kb-raw", md)
        self.assertIn("source: https://natesnewsletter.substack.com/p/example-post-slug", md)
        self.assertIn("publication: Nate's Newsletter (Substack)", md)
        self.assertIn("published: 2026-05-20", md)
        self.assertIn("tags: [ai, strategy]", md)
        self.assertIn("# Example post title", md)
        self.assertIn("## TL;DR", md)
        self.assertIn("First sentence. Second sentence.", md)
        self.assertIn("## Key Takeaways", md)
        self.assertIn("- Takeaway one.", md)
        self.assertIn("## Why It Matters", md)
        self.assertIn("## Full article", md)
        self.assertIn("Full body text here.", md)

    def test_omits_youtube_when_empty(self):
        md = build_kb_markdown(SAMPLE_SUMMARY, "body")
        self.assertNotIn("youtube_url:", md)

    def test_includes_youtube_when_present(self):
        summary = {**SAMPLE_SUMMARY, "youtube_url": "https://youtu.be/abc"}
        md = build_kb_markdown(summary, "body")
        self.assertIn("youtube_url: https://youtu.be/abc", md)


class WriteKbEntryTests(unittest.TestCase):
    def test_writes_file_at_expected_path(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            vault = make_fake_vault(tmp_dir)
            target = write_kb_entry(SAMPLE_SUMMARY, "FULL TEXT", vault)
            self.assertEqual(
                target,
                vault / NATE_SUBDIR / "example-post-slug.md",
            )
            self.assertTrue(target.exists())
            content = target.read_text(encoding="utf-8")
            self.assertIn("FULL TEXT", content)
            self.assertIn("# Example post title", content)


class RunVaultGitOpsTests(unittest.TestCase):
    def test_no_changes_is_noop(self):
        real_run = subprocess.run
        with tempfile.TemporaryDirectory() as tmp_dir:
            vault = make_real_git_vault(tmp_dir)
            # Pre-commit a file in NATE_SUBDIR so the directory + index entry exist;
            # then the function will find nothing new to commit.
            nate_dir = vault / NATE_SUBDIR
            nate_dir.mkdir(parents=True)
            (nate_dir / "seed.md").write_text("seed", encoding="utf-8")
            real_run(["git", "add", NATE_SUBDIR], cwd=vault, check=True, capture_output=True)
            real_run(
                [
                    "git",
                    "-c", "user.name=test",
                    "-c", "user.email=t@t.local",
                    "commit", "-m", "seed-nate-dir",
                ],
                cwd=vault, check=True, capture_output=True,
            )

            log = logging.getLogger("test.git")

            def fake_run(cmd, *args, **kwargs):
                if cmd[:2] in (["git", "pull"], ["git", "push"]):
                    class _R:
                        returncode = 0
                        stdout = ""
                        stderr = ""
                    return _R()
                return real_run(cmd, *args, **kwargs)

            with patch(
                "tools.create_kb_entry.subprocess.run",
                side_effect=fake_run,
            ):
                # Nothing new staged — function should return without raising.
                run_vault_git_ops(vault, "test", log)

    def test_commits_when_new_file_present(self):
        real_run = subprocess.run
        with tempfile.TemporaryDirectory() as tmp_dir:
            vault = make_real_git_vault(tmp_dir)
            nate_dir = vault / NATE_SUBDIR
            nate_dir.mkdir(parents=True)
            (nate_dir / "new-article.md").write_text("body", encoding="utf-8")

            log = logging.getLogger("test.git")

            def fake_run(cmd, *args, **kwargs):
                if cmd[:2] in (["git", "pull"], ["git", "push"]):
                    class _R:
                        returncode = 0
                        stdout = ""
                        stderr = ""
                    return _R()
                return real_run(cmd, *args, **kwargs)

            with patch(
                "tools.create_kb_entry.subprocess.run",
                side_effect=fake_run,
            ):
                run_vault_git_ops(vault, "test: add new-article", log)

            # Verify the commit landed on HEAD with our message
            log_out = real_run(
                ["git", "log", "-1", "--pretty=%s"],
                cwd=vault, check=True, capture_output=True, text=True,
            ).stdout.strip()
            self.assertEqual(log_out, "test: add new-article")


if __name__ == "__main__":
    unittest.main()
