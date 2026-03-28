"""
Scrape a full Substack article and summarize it using the Claude API.
Returns a structured summary dict ready for Notion page creation.
"""

import json
import os
import re
import subprocess
import tempfile
import time

import anthropic

SUMMARY_PROMPT = """\
You are a research assistant. Read the following article and produce a concise, \
accurate summary.

Article Title: {title}

Article Content:
{content}

Respond in exactly this format, with no extra text before or after:

## Title
[5-8 word title that captures the core topic, no clickbait]

## TL;DR
[1-2 sentences capturing the core message]

## Key Takeaways
- [Takeaway 1]
- [Takeaway 2]
- [Takeaway 3]
- [Optional Takeaway 4]
- [Optional Takeaway 5]

## Why It Matters
[1 paragraph on broader significance or implications]

## Tags
[3-5 short topic tags, comma-separated, e.g. AI Strategy, Career, Productivity]
"""

MIN_CONTENT_LENGTH = 200
FIRECRAWL_ATTEMPTS = 3
ANTHROPIC_ATTEMPTS = 3
INITIAL_RETRY_DELAY_SECONDS = 1.0
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")

MONTH_MAP = {
    "jan": "01", "feb": "02", "mar": "03", "apr": "04",
    "may": "05", "jun": "06", "jul": "07", "aug": "08",
    "sep": "09", "oct": "10", "nov": "11", "dec": "12",
}

