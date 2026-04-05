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
