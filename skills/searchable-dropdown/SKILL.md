---
name: searchable-dropdown
description: Selects an option in a searchable / typeahead dropdown (combobox). Types to filter, then clicks the matching option. Common on city pickers, country selectors, package-search dropdowns.
version: 0.1.0
allowed-tools: [click, fill, wait_for_selector, press_key, wait, assert]
metadata:
  applies_to: any-website
  url_patterns: ["*"]
  dom_markers:
    - "[role='combobox']"
    - "[role='listbox']"
    - "[aria-autocomplete='list']"
    - ".react-select"
    - ".select2"
  flake_rate_target: 0.12
  exercised_on:
    - opentable-home
    - booking-home
  cost_budget:
    deterministic_only: false
    max_vision_calls: 1
---

# Searchable Dropdown

## When to invoke

The page has a `role="combobox"` widget — typically used when the
option list is long (countries, cities, products). The agent provides
the desired option in `vars.option_text`.

## Recipe

1. click selector="[role='combobox'], [aria-haspopup='listbox']"
2. wait_for_selector selector="[role='listbox']" state=visible timeout=2s
3. fill selector="[role='combobox'], [role='listbox'] input[type='text']" value="$vars.option_text"
4. wait_for_selector selector="[role='option']:not([aria-disabled='true'])" state=visible timeout=2s
5. click selector="[role='option']:not([aria-disabled='true'])"
6. wait extra=200ms

## Success criteria

- assert combobox_has_value value="$vars.option_text"

## When NOT to use

- Plain `<select>` elements — use `select_option` primitive directly.
- Multi-select comboboxes — v0.1 picks the first match only.
- Async-loaded options where the listbox doesn't render until the
  filter API responds. Lengthen the `wait_for_selector` timeout via
  `vars.option_load_timeout`.

## Known failures

- **Comboboxes without standard ARIA:** Material-UI v4, antd v3, etc.
  use custom roles. The matcher's marker set covers the common
  libraries, but old/custom widgets need a fixture.
- **Comboboxes where the input is separate from the listbox:** v0.1
  fills the visible input; some libraries hide it behind another
  click. Add an upfront `click` to expand.
- **Comboboxes that auto-select on first matching keystroke:** the
  recipe's explicit-click step is unnecessary but harmless.

## Related skills

- `date-picker-widget` — often co-occurs in booking flows
- `fill-multi-step-form` — drops down inside form steps
