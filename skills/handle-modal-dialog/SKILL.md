---
name: handle-modal-dialog
description: Detects and dismisses blocking modal dialogs (generic confirmations, "are you sure", interstitials, signed-out prompts). Sibling to dismiss-newsletter-popup and dismiss-cookie-banner.
version: 0.1.0
allowed-tools: [wait_for_dom_ready, wait, try_each, assert]
metadata:
  applies_to: any-website
  url_patterns: ["*"]
  dom_markers:
    - "role='dialog'"
    - "aria-modal='true'"
    - ".modal"
  flake_rate_target: 0.08
  flake_rate_measured: null
  exercised_on:
    - rei-search
    - opentable-home
  cost_budget:
    deterministic_only: false
    max_vision_calls: 1
  sensitive: false
---

# Handle Modal Dialog

## When to invoke

A generic catch-all for blocking dialogs that aren't specifically cookie banners or newsletter popups: e.g., a "Continue without saving?" confirmation, an "Are you 13+?" age gate prompt that's not blocking-blocking, a "Choose your region" modal, an "App available — open in app?" interstitial.

The matcher scores this skill highly when the DOM contains `role="dialog"` or `aria-modal="true"` AND no cookie-banner / newsletter-popup-specific markers are present (otherwise the more specific skills win).

This skill **defaults to "dismiss"** — it clicks the close button or the "no thanks" / "stay on web" / "not now" path. If the user task requires *accepting* the dialog, the agent should not invoke this skill.

## Recipe

1. wait_for_dom_ready timeout=2s
2. wait extra=200ms
3. try_each selectors=[
     "[role='dialog'] button[aria-label*='close' i]",
     "[role='dialog'] button[aria-label*='dismiss' i]",
     "[aria-modal='true'] button[aria-label*='close' i]",
     "button.modal-close",
     ".modal button:has-text('Close')",
     ".modal button:has-text('No thanks')",
     ".modal button:has-text('Not now')",
     ".modal button:has-text('Stay on web')",
     ".modal button:has-text('Maybe later')",
     "[role='dialog'] button:has-text('Cancel')",
     ".modal button.btn-close",
     "button[data-dismiss='modal']",
     "button[data-bs-dismiss='modal']",
   ] action=click on_success=stop timeout=1500ms
4. wait extra=300ms

## Success criteria

- assert no_visible_element selector="[role='dialog'][aria-modal='true']" OR no_change_was_needed

## When NOT to use

- The user task is *interacting with* the modal (filling a quick form, selecting a region, confirming an action). Don't dismiss what the user wants to engage.
- A login modal — use `login-flow` instead.
- A cookie banner that happens to use `role="dialog"` — `dismiss-cookie-banner` is more specific and runs first per matcher ordering.

## Known failures

- **Modals without ARIA semantics (~10% of legacy sites):** sites that use plain `<div>` overlays without `role="dialog"` won't match the markers. Vision fallback or a follow-on `exit-tracking-popup`-style skill handles.
- **Modals with intercept-everything backdrops:** dismissing the modal via Escape key would work but isn't implemented in v0.1; add `keypress` primitive in v0.2.
- **Bootstrap 4 vs Bootstrap 5 attribute drift:** `data-dismiss` (BS4) vs `data-bs-dismiss` (BS5). Both selectors above; one will match.
- **Cascading modals (one closes, another appears):** v0.1 dismisses one and returns; the agent must re-invoke if the next state has another modal.

## Example usage

```
Agent task: "Get me the cheapest flight on this page."
→ matcher sees a "We've detected you're outside the US — go to region site?" modal
→ invoke_skill("handle-modal-dialog") → success, "Stay on web" clicked
→ agent continues with the original task
```

## Related skills

- `dismiss-cookie-banner` — more specific; runs first when both apply
- `dismiss-newsletter-popup` — more specific; runs first when both apply
- `exit-tracking-popup` — for "Wait, before you go!" exit-intent dialogs
