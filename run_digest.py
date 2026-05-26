#!/usr/bin/env python3
"""
Nate's Newsletter → KB Digest

Scrapes new articles from natesnewsletter.substack.com, summarizes each with
Claude, writes a KB entry (summary + full article body) into the shared vault
at <VAULT>/kb/raw/nate-substack/<slug>.md, and pushes the vault remote so the
new files are visible to Kai and any other vault clone.

Usage:
    python3 run_digest.py                  # process all not-yet-in-vault articles
    python3 run_digest.py --limit 3        # cap at N new articles (smoke testing)
    python3 run_digest.py --dry-run        # scrape + summarize, but skip writes
    python3 run_digest.py --no-push        # write to vault, skip git push
    python3 run_digest.py --verbose        # debug logging
"""

import argparse
import fcntl
import logging
import os
import sys
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent
TMP_DIR = PROJECT_ROOT / ".tmp"
ENV_FILE = PROJECT_ROOT / ".env"
LOG_FILE = TMP_DIR / "digest.log"
LOCK_FILE = TMP_DIR / "digest.lock"

load_dotenv(ENV_FILE)

SUBSTACK_URL = "https://natesnewsletter.substack.com/"


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(LOG_FILE),
        ],
    )


def ensure_runtime_dirs() -> None:
    TMP_DIR.mkdir(exist_ok=True)


@contextmanager
def acquire_run_lock():
    with open(LOCK_FILE, "w", encoding="utf-8") as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("Another digest run is already in progress.") from exc
        lock_file.write(str(os.getpid()))
        lock_file.flush()
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def validate_env() -> tuple[str, Path]:
    """
    Check required env vars. Returns (anthropic_key, vault_path).
    Raises EnvironmentError listing missing/invalid vars.
    """
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    vault_raw = os.getenv("VAULT_PATH")

    missing = []
    if not anthropic_key:
        missing.append("ANTHROPIC_API_KEY")
    if not vault_raw:
        missing.append("VAULT_PATH")
    if missing:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            "Please add them to your .env file."
        )

    vault_path = Path(vault_raw).expanduser().resolve()
    if not vault_path.is_dir():
        raise EnvironmentError(f"VAULT_PATH does not exist: {vault_path}")
    if not (vault_path / ".git").is_dir():
        raise EnvironmentError(f"VAULT_PATH is not a git repo: {vault_path}")

    return anthropic_key, vault_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Nate's Newsletter → KB digest automation"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scrape + summarize but skip KB writes and git ops",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Cap the number of new articles to process this run (smoke testing)",
    )
    parser.add_argument(
        "--no-push",
        action="store_true",
        help="Write KB entries but skip the vault git ops (commit + push)",
    )
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    args = parser.parse_args()

    ensure_runtime_dirs()
    setup_logging(args.verbose)
    log = logging.getLogger(__name__)

    if args.dry_run:
        log.info("--- DRY RUN MODE: no KB writes, no git ops ---")

    try:
        anthropic_key, vault_path = validate_env()
    except EnvironmentError as e:
        log.error(str(e))
        return 2

    log.info(f"Vault: {vault_path}")

    # Defer tool imports until env is loaded
    from tools.scrape_substack import get_article_list
    from tools.check_new_articles import filter_new_articles
    from tools.summarize_article import summarize_article
    from tools.create_kb_entry import (
        write_kb_entry,
        run_vault_git_ops,
        kb_entry_path,
    )

    try:
        with acquire_run_lock():
            log.info(f"Scraping article list from {SUBSTACK_URL}")
            try:
                all_articles = get_article_list(SUBSTACK_URL)
                log.info(f"Found {len(all_articles)} total articles")
            except (RuntimeError, ValueError) as e:
                log.error(f"Failed to scrape Substack index: {e}")
                return 2

            new_articles = filter_new_articles(all_articles, vault_path)
            log.info(f"{len(new_articles)} new article(s) to process")

            if args.limit is not None and len(new_articles) > args.limit:
                log.info(f"Limiting to first {args.limit} article(s) per --limit")
                new_articles = new_articles[: args.limit]

            if not new_articles:
                log.info("No new articles. Nothing to do.")
                return 0

            failures = []
            processed_count = 0
            written_paths = []

            for article in new_articles:
                url = article["url"]
                title = article["title"]
                log.info(f"Processing: {title}")
                log.debug(f"  URL: {url}")

                try:
                    summary = summarize_article(url, title, anthropic_key)
                    full_text = summary.pop("full_content")
                    log.info("  Summarized OK")
                    log.debug(f"  TL;DR: {summary['tldr'][:120]}...")
                except ValueError as e:
                    log.warning(f"  Skipping (likely paywalled): {e}")
                    failures.append({"url": url, "reason": str(e)})
                    continue
                except Exception as e:
                    log.error(f"  Summarization failed: {e}")
                    failures.append({"url": url, "reason": str(e)})
                    continue

                if args.dry_run:
                    target = kb_entry_path(url, vault_path)
                    log.info(f"  [DRY RUN] Would write: {target}")
                else:
                    try:
                        written = write_kb_entry(summary, full_text, vault_path)
                        log.info(f"  Wrote KB entry: {written}")
                        written_paths.append(written)
                    except Exception as e:
                        log.error(f"  KB write failed: {e}")
                        failures.append({"url": url, "reason": str(e)})
                        continue

                processed_count += 1

            if not args.dry_run and not args.no_push and written_paths:
                commit_msg = (
                    f"feat(kb): nate-substack digest "
                    f"({datetime.now().strftime('%Y-%m-%d %H:%M')}) — "
                    f"{len(written_paths)} new article(s)"
                )
                try:
                    run_vault_git_ops(vault_path, commit_msg, log)
                except Exception as e:
                    log.error(f"Vault git ops failed: {e}")
                    return 1

            log.info(
                f"Done. Processed: {processed_count}, Failed/Skipped: {len(failures)}"
            )
            if failures:
                for f in failures:
                    log.warning(f"  SKIPPED: {f['url']} — {f['reason']}")

            return 0 if not failures else 1
    except RuntimeError as e:
        log.error(str(e))
        return 2


if __name__ == "__main__":
    sys.exit(main())
