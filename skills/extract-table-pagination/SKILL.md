---
name: extract-table-pagination
description: Extract structured data from an HTML table, optionally walking through paginated views. Returns a list of row dicts keyed by header cells. The demo skill (used to monitor conference paper lists).
version: 0.2.0
allowed-tools: [wait_for_dom_ready, wait_for_selector, extract_table, click, wait, assert]
metadata:
  applies_to: any-website
  url_patterns: ["*"]
  dom_markers:
    - "<table"
    - "role='table'"
  flake_rate_target: 0.08
  flake_rate_measured: null
  exercised_on:
    - wikipedia-list
    - arxiv-listing
    - hacker-news-list
    - openalex-search
    - weather-gov-forecast
  cost_budget:
    deterministic_only: false
    max_vision_calls: 1
  sensitive: false
  # Pilot opt-in for runner-evaluated success criteria (this work).
  # The single criterion `$rows_page_1 is_non_empty_list` is a
  # KNOWN_PREDICATE — definitively decidable from the runner's vars
  # map after the extract_table step binds it.
  evaluate_success_criteria: true
---

# Extract Table Pagination

## When to invoke

When the user task involves reading structured data from an HTML table — the page either shows a `<table>` element, or a `role="table"` ARIA structure. If the table is paginated, the skill walks pages via a "next" link/button until either the next link is absent, the row count stops growing, or a configurable `max_pages` is reached.

The matcher gives this a high score when the DOM summary contains `<table` and the visible-text sample has table-like indicators (numeric columns, repeated short text).

## Recipe

1. wait_for_dom_ready timeout=5s
2. wait_for_selector selector="table, [role='table']" state=visible timeout=5s
3. extract_table selector="table" into="$rows_page_1"
4. wait extra=200ms

## Success criteria

- assert $rows_page_1 is_non_empty_list

## Pagination companion

For paginated tables, chain with the `pagination-next-page` skill in a loop. The runner's `vars` map preserves bindings across skill invocations so the agent can accumulate rows.

Pseudo-recipe the agent assembles:
```
while page <= max_pages:
    invoke_skill("extract-table-pagination") → $rows_page_N
    accumulated += $rows_page_N
    if no "next" link visible: break
    invoke_skill("pagination-next-page")
```

We deliberately keep extraction and pagination as separate skills so the agent can interleave with other steps (rate-limit pauses, filter applications, deduplication).

## When NOT to use

- The data lives in a `<div>`-grid layout (card grid, masonry, etc.) — use the future `extract-card-grid` skill, or vision fallback.
- The table is virtualized (only renders visible rows on scroll, e.g., AG Grid, MUI DataGrid). Use `handle-infinite-scroll` with row-extraction inside the scroll loop instead.
- The "table" is actually a layout `<table>` from 2003-era HTML (no `<th>`, no semantic structure). The extractor will produce noisy results; better to extract by text-selector and structure manually.

## Known failures

- **Virtualized tables (~5% of modern web apps):** only the visible rows are in the DOM at any time. The extractor returns just those. Workaround: combine with `handle-infinite-scroll` or scroll-and-extract.
- **Tables with rowspan/colspan (~3%):** the naive header-zip extractor mis-aligns columns. Vision fallback handles for now; v0.2.0 will support `extract_table mode="rowspan-aware"`.
- **No `<thead>`, no `<th>` (~5% of legacy sites):** the extractor uses the first row as headers; if that row is data, the first record is lost. Workaround: pass `headers=[...]` arg (planned v0.2.0).
- **Server-side-rendered "infinite scroll" disguised as pagination:** the next-page link returns the SAME rows on click. Detection logic in `pagination-next-page` aborts when row hashes match.

## Example usage

```
Agent task: "Get the latest cs.AI papers from arxiv."
→ invoke_skill("verify-page-loaded") → success
→ invoke_skill("extract-table-pagination") → success, $rows_page_1 = [{title, authors, abstract}, ...]
→ agent inspects $rows_page_1 and reports
```

## Related skills

- `verify-page-loaded` — run first; tables on slow-rendering pages need readiness check
- `pagination-next-page` — chain to walk multiple pages
- `handle-infinite-scroll` — alternative when content lazy-loads instead of paginating
- `dismiss-cookie-banner` — usually run before any extraction
