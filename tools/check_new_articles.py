"""
Determine which scraped articles are "new" — i.e. don't yet have a KB entry
in the vault. The vault is the source of truth: file existence == processed.

This replaces the prior JSON-state mechanism. The vault is the memory.
"""

from pathlib import Path

from tools.create_kb_entry import already_in_vault


def filter_new_articles(articles: list, vault_path: Path | None = None) -> list:
    """
    Return only articles that do NOT yet exist as KB entries in the vault.
    """
    return [a for a in articles if not already_in_vault(a["url"], vault_path)]
