---
name: date-picker-widget
description: Picks a date in a calendar-style date-picker widget — clicks the input, navigates months if needed, clicks the target day. The famous "vision agent failure case" that motivates this whole library.
version: 0.1.0
allowed-tools: [wait_for_dom_ready, click, wait_for_selector, fill, press_key, wait, assert]
metadata:
  applies_to: any-website
  url_patterns: ["*"]
  dom_markers:
    - "[role='dialog'][aria-label*='calendar' i]"
    - "[role='application'][aria-label*='date' i]"
    - "[data-element='calendar']"
    - "input[type='date']"
  flake_rate_target: 0.10
  exercised_on:
    - booking-home
    - opentable-home
  cost_budget:
    deterministic_only: false
    max_vision_calls: 2
---

# Date Picker Widget

## When to invoke

The user task requires picking a date (booking demos, scheduling
demos, date-range filters). `vars.target_date` is an ISO-8601 date
string (e.g., `"2026-06-15"`).

The matcher recognizes calendar widgets via their ARIA roles. The
`<input type="date">` native picker is the easy path — `fill` it
directly. The hard path is custom calendars (booking.com,
airbnb.com, hotels.com style), and that's what this skill targets.

## Recipe

### Easy path (native `<input type="date">`)

1. fill selector="input[type='date']" value="$vars.target_date"

### Hard path (custom calendar)

1. wait_for_dom_ready timeout=3s
2. click selector="[data-element='calendar-trigger'], [aria-label*='date' i][role='button']"
3. wait_for_selector selector="[role='dialog'][aria-label*='calendar' i]" state=visible timeout=2s
4. click selector="[aria-label='$vars.target_date'], [data-date='$vars.target_date']"
5. wait extra=300ms

(Month-navigation logic — "click 'next month' until target month is visible" — is
deferred to v0.2 with the `loop` verb. v0.1 handles the case where the target
date is already visible on the initial calendar open. For booking-style sites
where check-in is in the current month, this is enough.)

## Success criteria

- assert input_has_value selector="[data-element='check-in']" value_contains="$vars.target_date"

## When NOT to use

- Date *range* pickers — use `vars.range_start` / `vars.range_end` and
  the agent composes two invocations.
- Calendars that don't expose `aria-label` or `data-date` attributes
  on day cells. Vision fallback is currently the only recourse.

## Known failures

- **Disabled past dates:** the click is ignored. The agent sees no
  state change and should re-plan.
- **Calendars opening below the fold:** the day cells render but
  aren't clickable until scrolled. Add a `scroll_into_view` step.
- **Calendars that require keyboard nav only:** v0.1 doesn't support
  keyboard nav loops; the `press_key` primitive could be composed but
  there's no standardized pattern.
- **Month navigation:** v0.1 only picks dates in the currently-visible
  month. v0.2 adds month-navigation loops.

## Related skills

- `dismiss-cookie-banner` — booking sites are EU-heavy; cookie banner first
- `verify-page-loaded` — wait for the calendar UI to render
- `searchable-dropdown` — often co-occurs (date + party-size selectors)
