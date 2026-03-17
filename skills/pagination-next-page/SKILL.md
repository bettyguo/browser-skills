---
name: pagination-next-page
description: Navigates to the next page in a paginated listing by clicking a "next" link/button or pressing the typical keyboard shortcut. Pairs with extract-table-pagination for multi-page data collection.
version: 0.1.0
allowed-tools: [wait_for_dom_ready, try_each, wait, assert]
metadata:
  applies_to: any-website
  url_patterns: ["*"]
  dom_markers:
    - "[aria-label*='next' i]"
    - "rel='next'"
    - "li.next"
    - ".pagination"
  flake_rate_target: 0.10
  exercised_on:
    - hacker-news-list
    - arxiv-listing
    - ebay-search
    - rei-search
    - stackoverflow-tag
  cost_budget:
    deterministic_only: false
    max_vision_calls: 1
---

# Pagination Next Page

## When to invoke

A listing page exposes pagination (page numbers, prev/next arrows, or
a "load more" button). The agent has just extracted page N and wants to
advance to N+1.

## Recipe

1. wait_for_dom_ready timeout=2s
2. try_each selectors=[
     "a[rel='next']",
     "[aria-label='Next page']",
     "[aria-label='Next']",
     "a.pagination-next",
     "button.pagination-next",
     "a:has-text('Next ›')",
     "a:has-text('Next')",
     "button:has-text('Load more')",
     "li.next > a",
     ".pagination a[aria-label*='next' i]",
   ] action=click on_success=stop timeout=1500ms
3. wait extra=500ms

## Success criteria

- assert url_changed_since=step1 OR new_rows_appended

## When NOT to use

- Infinite-scroll pages — use `handle-infinite-scroll`.
- Pages where the "next" link is actually a JS handler that
  re-renders the same URL with new content. The success criterion's
  `new_rows_appended` check handles this when paired with extraction.

## Known failures

- **Sites that hide the "next" link when on the last page:** recipe
  fails benignly; agent interprets as "end reached."
- **`rel='next'` link points to a different domain (rare):** recipe
  follows; agent must validate the new URL.
- **Cursor-based pagination with no visible "next" link:** agent must
  inspect API responses; skill cannot help.

## Related skills

- `extract-table-pagination` / `extract-list-pagination` — chain in a
  loop
- `verify-page-loaded` — after the next page navigates
