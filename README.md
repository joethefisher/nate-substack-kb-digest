# Nate's Newsletter → KB Digest

I’ve always valued Nate’s work, but I rarely had time to keep up with both his YouTube content and his Substack articles. I’d get the emails, save them with good intentions, and then never actually make time to read the full posts. This automation closes that loop into my shared knowledge vault.

Daily Substack → KB workflow:

- Scrapes new posts from `natesnewsletter.substack.com`
- Summarizes each with Claude (TL;DR, key takeaways, why it matters, tags)
- Writes a markdown KB entry — **summary + full article body** — into the shared vault at `<VAULT>/kb/raw/nate-substack/<slug>.md`
- Pushes the vault remote so the new entries reach Kai and any other vault clone immediately

State is the vault itself: if `<VAULT>/kb/raw/nate-substack/<slug>.md` exists, the article is "processed." No separate JSON state file to lose or sync.

## Why This Exists

This project turns a newsletter feed into a personal research queue. It is designed to be reliable enough for unattended scheduled runs while still being simple to inspect and extend.

## Stack

- Python 3.10+ (developed against 3.12)
- Firecrawl CLI (article scraping)
- Anthropic Messages API (summarization)
- Plain markdown files in a git-backed vault (output)

## Requirements

- Python 3.12 (Homebrew: `brew install python@3.12`)
- Firecrawl CLI installed and authenticated
- Anthropic API key
- A git-backed vault at `VAULT_PATH` (this script will pull/commit/push)

## Setup

```bash
cd ~/code/nate-substack-kb-digest
/opt/homebrew/opt/python@3.12/bin/python3.12 -m venv .venv
./.venv/bin/pip install -r requirements.txt
cp .env.example .env
# Edit .env and set ANTHROPIC_API_KEY + VAULT_PATH
```

Required `.env` keys:

```env
ANTHROPIC_API_KEY=...
VAULT_PATH=/Users/jobot/vault
```

Optional:

```env
ANTHROPIC_MODEL=claude-sonnet-4-6
```

## Running

```bash
# Default — process all not-yet-in-vault articles, write + push
./.venv/bin/python run_digest.py

# Dry-run — scrape + summarize but skip writes/push
./.venv/bin/python run_digest.py --dry-run

# Smoke test — cap at 3 new articles
./.venv/bin/python run_digest.py --limit 3

# Write to vault but skip the git push (debug)
./.venv/bin/python run_digest.py --no-push

# Verbose
./.venv/bin/python run_digest.py --verbose
```

Exit codes: 0 = success, 1 = partial (some failures), 2 = setup/env error.

## Scheduling

Daily run via macOS launchd at 06:00 PT. The plist lives at `~/Library/LaunchAgents/com.joefisher.substack-kb-digest.plist`.

Load:

```bash
launchctl load ~/Library/LaunchAgents/com.joefisher.substack-kb-digest.plist
```

Trigger manually:

```bash
launchctl start com.joefisher.substack-kb-digest
```

Logs at `.tmp/launchd.out.log` and `.tmp/launchd.err.log`.

## Tests

```bash
./.venv/bin/python -m pytest tests/ -v
```

## Project Structure

```text
run_digest.py                 Orchestrates the full workflow
tools/scrape_substack.py      Scrapes the Substack index, returns article URLs
tools/check_new_articles.py   Filters out articles already in vault (file-existence state)
tools/summarize_article.py    Scrapes article body + Claude summary
tools/create_kb_entry.py      Writes KB markdown + handles vault git ops
workflows/substack_digest.md  Human-readable SOP
tests/                        Unit tests
```

## Operational Behavior

- State = vault file existence (one source of truth, no JSON drift).
- Run lock (`fcntl.flock` on `.tmp/digest.lock`) prevents overlapping runs.
- Exponential backoff on Firecrawl, Anthropic, and git operations.
- Paywalled or too-short articles are skipped and retried on the next run.
- Vault git ops: `git pull --rebase` → stage `kb/raw/nate-substack/` → commit + push. Silent no-op when nothing changed.

## Migrated from Notion

Earlier this project wrote summaries to a Notion database. The destination migrated to a shared KB vault on 2026-05-25 — see commit history for the cutover. The Notion writer and its tests are removed; the rest of the pipeline is unchanged.
