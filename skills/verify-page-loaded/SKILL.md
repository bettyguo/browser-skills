---
name: verify-page-loaded
description: Confirms that the current page has finished loading and is ready for interaction. Detects loading spinners, skeleton screens, and content placeholders. Run before extraction skills.
version: 0.2.0
allowed-tools: [wait_for_dom_ready, wait_for_selector, wait, assert]
metadata:
  applies_to: any-website
  url_patterns: ["*"]
  dom_markers: []
  flake_rate_target: 0.02
  flake_rate_measured: null
  exercised_on:
    - wikipedia-list
    - arxiv-listing
    - bbc-home
  cost_budget:
    deterministic_only: true
    max_vision_calls: 0
  sensitive: false
  # Pilot opt-in for runner-evaluated success criteria (this work).
  # Every predicate in this skill's ## Success criteria section is a
  # KNOWN_PREDICATE; the evaluator can decide them definitively.
  evaluate_success_criteria: true
---

# Verify Page Loaded

## When to invoke

After any navigation, and after any interaction that may have triggered new content (clicking pagination, expanding a section, submitting a form). Especially important before extraction skills — extracting from a half-rendered DOM produces incomplete results.

This skill is **vision-forbidden** (`max_vision_calls: 0`). If the deterministic checks fail, the skill returns `failed` and the agent knows the page is genuinely not ready — vision wouldn't help.

## Recipe

1. wait_for_dom_ready timeout=10s
2. wait_for_selector selector="body" state=visible timeout=2s
3. wait extra=200ms
4. assert no_visible_element selector="[aria-busy='true']" timeout=3s
5. assert no_visible_element selector=".loading, .spinner, [class*='skeleton']" timeout=3s

## Success criteria

- assert dom_ready
- assert no_visible_element selector="[aria-busy='true']"
- assert main_content_present

The `main_content_present` assertion checks for one of: `<main>`, `[role=main]`, `<article>`, or a body height > 200px (heuristic for "something rendered").

## When NOT to use

- On pages that legitimately stay in a loading state (live dashboards, video-call interfaces, etc.). Use a custom skill or rely on agent reasoning.
- Inside an extraction loop where the page is the same as before; this skill assumes a fresh state.

## Known failures

- **Single-page apps with no DOMContentLoaded signal change:** rare but happens with React/Vue apps that use shadow DOM heavily. Falls back to the spinner-absence check.
- **Pages with always-present skeleton-style classes:** some design systems use `.skeleton` for normal layout elements, not loading. Authors can override the recipe to remove step 5.
- **Sites that block until consent is given:** if a cookie banner is also blocking, run [`dismiss-cookie-banner`](../dismiss-cookie-banner/SKILL.md) first.

## Example usage

```
Agent task: "Get the latest cs.AI papers from arxiv."
→ matcher selects [verify-page-loaded, extract-table-pagination]
→ invoke_skill("verify-page-loaded") → success in 89ms, deterministic_path=true
→ invoke_skill("extract-table-pagination") proceeds against a fully-rendered page
```

## Related skills

- `dismiss-cookie-banner` — usually precedes this skill
- `extract-table-pagination` — usually follows this skill
- `handle-infinite-scroll` — uses similar primitives but with a different success criterion
