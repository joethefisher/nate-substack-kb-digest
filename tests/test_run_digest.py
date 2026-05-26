import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import run_digest


def _fresh_env(**overrides) -> dict:
    return dict(overrides)


class ValidateEnvTests(unittest.TestCase):
    def test_missing_anthropic_key_raises(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            vault = Path(tmp_dir)
            (vault / ".git").mkdir()
            with patch.dict(
                os.environ,
                _fresh_env(VAULT_PATH=str(vault)),
                clear=True,
            ):
                with self.assertRaises(EnvironmentError) as cm:
                    run_digest.validate_env()
                self.assertIn("ANTHROPIC_API_KEY", str(cm.exception))

    def test_missing_vault_path_raises(self):
        with patch.dict(
            os.environ,
            _fresh_env(ANTHROPIC_API_KEY="x"),
            clear=True,
        ):
            with self.assertRaises(EnvironmentError) as cm:
                run_digest.validate_env()
            self.assertIn("VAULT_PATH", str(cm.exception))

    def test_vault_path_must_exist(self):
        with patch.dict(
            os.environ,
            _fresh_env(
                ANTHROPIC_API_KEY="x",
                VAULT_PATH="/nonexistent/path/to/vault",
            ),
            clear=True,
        ):
            with self.assertRaises(EnvironmentError):
                run_digest.validate_env()

    def test_vault_path_must_be_git_repo(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch.dict(
                os.environ,
                _fresh_env(ANTHROPIC_API_KEY="x", VAULT_PATH=tmp_dir),
                clear=True,
            ):
                with self.assertRaises(EnvironmentError) as cm:
                    run_digest.validate_env()
                self.assertIn("not a git repo", str(cm.exception))

    def test_happy_path_returns_key_and_path(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            vault = Path(tmp_dir)
            (vault / ".git").mkdir()
            with patch.dict(
                os.environ,
                _fresh_env(ANTHROPIC_API_KEY="abc", VAULT_PATH=str(vault)),
                clear=True,
            ):
                anthropic_key, vault_path = run_digest.validate_env()
        self.assertEqual(anthropic_key, "abc")
        self.assertEqual(vault_path, vault.resolve())


class RuntimePathTests(unittest.TestCase):
    def test_runtime_paths_are_repo_relative(self):
        self.assertEqual(run_digest.TMP_DIR, run_digest.PROJECT_ROOT / ".tmp")
        self.assertEqual(run_digest.LOG_FILE, run_digest.TMP_DIR / "digest.log")
        self.assertEqual(run_digest.ENV_FILE, run_digest.PROJECT_ROOT / ".env")


if __name__ == "__main__":
    unittest.main()
