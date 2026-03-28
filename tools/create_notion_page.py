"""
Create a Notion page in the digest database from a structured summary dict.
Uses the notion-client Python library.
"""

from datetime import datetime, timezone
import time

from notion_client import Client
from notion_client import errors

NOTION_ATTEMPTS = 3
INITIAL_RETRY_DELAY_SECONDS = 1.0


def build_rich_text(text: str, chunk_size: int = 2000) -> list[dict]:
    chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)] or [""]
    return [{"type": "text", "text": {"content": chunk}} for chunk in chunks]

