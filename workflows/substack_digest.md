# Workflow: Nate's Newsletter Substack → Notion Digest

## Objective
Automatically scrape new articles from natesnewsletter.substack.com daily, summarize each using Claude, and create structured Notion pages for easy reading.

## Required Inputs
- `ANTHROPIC_API_KEY` — Claude API key (in `.env`)
- `NOTION_API_KEY` — Notion integration secret (required for non-dry runs)
- `NOTION_DATABASE_ID` — Target Notion database ID (required for non-dry runs)
- Firecrawl CLI authenticated (already done — run `firecrawl credit-usage` to verify)

## Execution

### Manual run
```bash
cd "/Users/joe/code/Nate Substack Digest"
./.venv/bin/python run_digest.py --verbose
```

### Dry run (no Notion writes)
```bash
./.venv/bin/python run_digest.py --dry-run
```

Note: the script resolves `.env` and `.tmp` relative to the repository root, so it can be launched from any working directory.

### Automated (Cowork scheduled task in Claude Desktop)
1. Open Claude Desktop → Cowork → click "Scheduled" in the sidebar
2. Create a new scheduled task with:
   - **Name:** Nate's Newsletter Digest
   - **Description:** Scrapes natesnewsletter.substack.com for new articles, summarizes each with Claude, and saves them to the Nate's Newsletter Digest database in Notion.
   - **Cadence:** Daily
   - **Working folder:** `/Users/joe/code/Nate Substack Digest`
   - **Prompt:**
     ```
     Run the Nate's Newsletter Substack digest.

     Working directory: /Users/joe/code/Nate Substack Digest

     Run this command:
     ./.venv/bin/python run_digest.py --verbose

     If it exits with code 0: report how many articles were processed and their titles.
     If it exits with code 1: report which articles were skipped and why — these may be paywalled.
     If it exits with code 2: something critical failed (scrape or missing credentials). Show the full error output so I can investigate.
     ```

Note: Task only runs while your computer is awake and Claude Desktop is open. If skipped, Cowork will run it automatically when the app is reopened.

## Tool Execution Sequence

1. **`tools/scrape_substack.py`** — Calls `firecrawl scrape` on the Substack index. Extracts all article URLs matching the `/p/` path pattern.
2. **`tools/check_new_articles.py`** — Loads `.tmp/processed_articles.json`. Filters out already-processed URLs.
3. **`tools/summarize_article.py`** — For each new article: calls `firecrawl scrape` for full content, then sends to Claude API. Returns TL;DR + Key Takeaways + Why It Matters.
4. **`tools/create_notion_page.py`** — Creates a Notion page with the summary. Returns the page URL.
5. State is saved after each successfully created page.

## Expected Outputs

- New Notion pages in "Nate's Newsletter Digest" database
- Updated `.tmp/processed_articles.json` with processed URLs
- Log output at `.tmp/digest.log`

## Notion Database Schema

| Property | Type | Notes |
|---|---|---|
| Name | Title | Article title |
| URL | URL | Full Substack article URL |
| TL;DR | Rich Text | 1-2 sentence summary (visible in database view) |
| Status | Select | Unread / Reading / Done |
| Added | Date | Date the automation ran |
| Tags | Multi-select | Manually populated by user |

Each page body contains: TL;DR section, Key Takeaways (bullets), Why It Matters paragraph, divider, and source link.

## Edge Cases and Known Behaviors

- **Paywalled articles**: If scraped content is < 200 characters, the article is skipped with a warning. It is NOT marked as processed and will be retried next run (in case the issue was transient).
- **Scrape failures**: If the Firecrawl scrape of an individual article fails, it is logged and skipped. The index scrape failing causes an immediate exit (nothing is safe to process).
