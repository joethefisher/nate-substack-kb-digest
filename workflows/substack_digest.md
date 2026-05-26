# Workflow: Nate's Newsletter Substack → KB Digest

## Objective

Daily, scrape new articles from `natesnewsletter.substack.com`, summarize each with Claude, and write a markdown KB entry (summary + full article body) into the shared vault at `<VAULT>/kb/raw/nate-substack/<slug>.md`. Push the vault so new entries are visible to Kai immediately.

## Inputs

- `natesnewsletter.substack.com/` — index page, scraped via Firecrawl CLI.
- `ANTHROPIC_API_KEY` — for summarization.
- `VAULT_PATH` — local clone of the shared knowledge vault.

## Outputs

- One markdown file per new article at `<VAULT>/kb/raw/nate-substack/<slug>.md` containing:
  - YAML frontmatter (source, publication, author, dates, tags)
  - Title + source link
  - TL;DR
  - Key Takeaways (bulleted)
  - Why It Matters
  - Tags
  - Full article body (verbatim from Firecrawl)
- One git commit + push per run with N new entries.

## State

The vault is the state. An article is "processed" iff its KB entry file exists in `<VAULT>/kb/raw/nate-substack/`. No separate JSON file.

## Tools used

- `tools/scrape_substack.py` — Substack index → list of article URLs
- `tools/check_new_articles.py` — filter to URLs not yet in vault
- `tools/summarize_article.py` — scrape body + Claude summary
- `tools/create_kb_entry.py` — write markdown + run vault git ops

## Process

1. Acquire `.tmp/digest.lock` (skip if another run in progress).
2. Scrape Substack index → list of `{url, title, slug}`.
3. Filter to URLs not yet in vault.
4. For each new article:
   a. Scrape full content + summarize via Claude.
   b. Skip if content too short (< 200 chars — likely paywalled).
   c. Write `<VAULT>/kb/raw/nate-substack/<slug>.md` atomically (temp file + rename).
5. After all writes, run vault git ops: pull --rebase → add → commit (if changes) → push.
6. Log summary, return exit code (0 success / 1 partial / 2 env error).

## Edge cases

- **Paywalled article:** content shorter than `MIN_CONTENT_LENGTH = 200` → skip, log warning, will retry next run (file isn't created so won't be marked as processed).
- **Firecrawl transient failure:** 3 retries with exponential backoff.
- **Anthropic transient failure:** 3 retries with exponential backoff on connection/timeout/rate-limit/5xx.
- **Git pull conflict:** logged as warning, continue (commit may then fail on push — surface in exit code).
- **Overlapping runs:** prevented by `fcntl.flock`.

## Scheduling

macOS launchd, daily 06:00 PT — `~/Library/LaunchAgents/com.joefisher.substack-kb-digest.plist`.

## Related

- Vault project record: `[[substack-digest]]` in `<VAULT>/kai/projects/`.
- Migration plan: `[[substack-kb-digest-migration]]`.
- Wiki topic destination (for synthesis): `kb/wiki/agentic/news/`.
