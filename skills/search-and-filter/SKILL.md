---
name: search-and-filter
description: Types a query into a site's search input, submits, and optionally applies one or more filter facets (categories, price ranges, attributes). Common on e-commerce, doc-search, and listing sites.
version: 0.1.0
allowed-tools: [wait_for_dom_ready, fill, click, press_key, try_each, wait]
metadata:
  applies_to: any-website
  url_patterns: ["*"]
  dom_markers:
    - "input[type='search']"
    - "[role='search']"
    - "[aria-label*='search' i]"
  flake_rate_target: 0.10
  exercised_on:
    - ebay-search
    - rei-search
    - github-search
    - pypi-search
    - openalex-search
  cost_budget:
    deterministic_only: false
    max_vision_calls: 2
---

# Search and Filter

## When to invoke

User wants to search a site for `vars.query` and optionally apply
filters from `vars.filters` (a dict of facet-name → value).

The matcher fires this skill on any page with a visible search input.

## Recipe

1. wait_for_dom_ready timeout=3s
2. try_each selectors=[
     "input[type='search']",
     "input[name='q']",
     "input[name='query']",
     "[role='search'] input",
     "input[aria-label*='search' i]",
   ] action=fill value="$vars.query" on_success=stop timeout=1500ms
3. press_key key=Enter
4. wait extra=600ms

## Success criteria

- assert results_pane_visible OR url_changed_since=step1

## Filter application

The recipe above is the search part only. Applying filters is a
composition with `click` for facet checkboxes — the agent receives the
list of available filters from `extract_text` and decides which to
toggle.

## When NOT to use

- Sites with custom search-as-you-type that doesn't accept Enter
  submission. Agents fall back to clicking the search button after fill.
- Sites that ToS-prohibit automated search (LinkedIn, etc., per
  benchmarks/sites.yaml).

## Known failures

- **Sites where pressing Enter doesn't submit:** add a follow-on
  `click` against a search button — most sites surface one.
- **Search inputs inside `<form>` elements that submit on a different
  path:** the recipe's `Enter` press may navigate to a stale URL.
  Document per-site if discovered.
- **Search inputs that show typeahead before submission:** the
  typeahead overlays the results. `press_key key=Escape` first if
  it's blocking.
