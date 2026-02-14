---
name: handle-infinite-scroll
description: Scrolls a page to load additional content via infinite-scroll, with stop conditions (no-more-content, max iterations, or target selector visible). Used for feeds, lists, and search results that lazy-load.
version: 0.1.0
allowed-tools: [wait_for_dom_ready, scroll_until, wait, assert]
metadata:
  applies_to: any-website
  url_patterns: ["*"]
  dom_markers: []
  flake_rate_target: 0.15
  flake_rate_measured: null
  exercised_on:
    - wikipedia-infinite
    - guardian-home
  cost_budget:
    deterministic_only: false
    max_vision_calls: 1
  sensitive: false
---

# Handle Infinite Scroll

## When to invoke

When the page extends its content as the user scrolls down (Twitter/X feeds, Reddit posts, Instagram search, news homepages, search-result feeds). The matcher cannot easily detect infinite-scroll *a priori* — it's a runtime behavior, not a DOM marker. So this skill is typically invoked when:

- The user task explicitly mentions "scroll to load more" / "all posts" / "everything available"
- A previous `extract_*` skill returned fewer rows than the user expected
- The page has `<button>Load more</button>` (visual cue) — though "load more" buttons are a different skill, `pagination-next-page`

## Recipe

1. wait_for_dom_ready timeout=3s
2. scroll_until condition="no_more_content" max_iters=20 delay=400ms
3. wait extra=500ms

## Success criteria

- assert scrolled_at_least_once

There's no strict "succeeded" semantic here — if `max_iters` was hit, the skill returns `success` and the caller decides if it has enough rows. The trace records the actual iteration count and final page height.

## Configurable knobs

The recipe above is the default. Authors can override via the agent invoking with `vars`:

- `vars.max_scroll_iters` → overrides `max_iters` (cap: 100)
- `vars.target_selector` → switches condition to `selector_present:<css>` (stops when the named selector becomes visible)

## When NOT to use

- The page paginates instead of scrolling — use `pagination-next-page`.
- The "infinite" scroll is actually a "load more" button — use `pagination-next-page` (the button-click variant).
- Virtualized lists where scrolling DESTROYS earlier rows from the DOM (some React virtualization). The extractor must be invoked *during* the scroll loop, not after — a future composite skill `infinite-scroll-and-extract` will handle this.

## Known failures

- **Virtualized lists (~15% of modern feeds):** offscreen rows are unmounted; by the time `scroll_until` stops, only the last viewport's rows are in the DOM. Workaround: invoke `extract_*` skill at each iteration (manual composition).
- **JS-heavy sites that pause loading on tab-blur:** if the test runs in a headless context that the site sniffs as "not visible," loading never triggers. Use `--headed` mode for these.
- **Sites with anti-scroll-bot detection:** some sites detect "too fast" scrolling and stop serving content. `delay=400ms` is calibrated for "human-like"; lower values trigger blocks.
- **Sites that load content based on screen size:** running with a tiny viewport produces fewer rows per scroll. Default viewport in `start_browser` is 1280×800 — keep that for benchmark consistency.

## Example usage

```
Agent task: "Show me all posts on this Reddit page."
→ invoke_skill("verify-page-loaded") → success
→ invoke_skill("handle-infinite-scroll") → success, scrolled 12 times
→ invoke_skill("extract-list-pagination") → all rows captured
```

## Related skills

- `pagination-next-page` — for paginated alternatives to infinite scroll
- `verify-page-loaded` — run first; need a stable initial state
- `extract-table-pagination` / `extract-list-pagination` — typically chained after scrolling
