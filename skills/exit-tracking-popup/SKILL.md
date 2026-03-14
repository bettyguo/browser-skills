---
name: exit-tracking-popup
description: Dismisses exit-intent popups ("Wait! Before you go!", "Don't leave without your discount", abandonment recovery overlays) that fire on mouse-leave or scroll-up patterns.
version: 0.1.0
allowed-tools: [wait, try_each, press_key]
metadata:
  applies_to: any-website
  url_patterns: ["*"]
  dom_markers:
    - "[class*='exit-intent' i]"
    - "[class*='abandonment' i]"
    - "[data-exit-intent]"
    - "[class*='discount-popup' i]"
  flake_rate_target: 0.12
  exercised_on:
    - bbc-home
    - rei-search
  cost_budget:
    deterministic_only: false
    max_vision_calls: 1
---

# Exit Tracking Popup

## When to invoke

After the agent has been on the page for a few seconds and is about
to navigate away (or after a scroll-pattern that triggers
exit-intent JS), a "Wait!" overlay appears trying to keep them. The
dismiss controls are typically a small "x", a "no thanks" link, or
Escape.

The matcher fires this skill when exit-intent markers are present
*and* the page is not in initial-load.

## Recipe

1. wait extra=200ms
2. try_each selectors=[
     "[class*='exit-intent' i] button[aria-label*='close' i]",
     "[data-exit-intent] button[aria-label*='close' i]",
     "[class*='abandonment' i] button[aria-label*='close' i]",
     "[class*='discount-popup' i] button[aria-label*='close' i]",
     "[class*='exit-intent' i] button:has-text('No thanks')",
     "[class*='exit-intent' i] button:has-text('I'm not interested')",
     "[class*='abandonment' i] button.btn-close",
     "[data-exit-intent] button.dismiss",
   ] action=click on_success=stop timeout=1000ms
3. press_key key=Escape

## Success criteria

- assert no_visible_element selector="[class*='exit-intent' i]" OR no_change_was_needed

## When NOT to use

- The user is *interested* in the offer. Don't auto-dismiss.

## Known failures

- **Exit-intent popups that block scroll until clicked:** dismissal
  must be clicking the visible close, not Escape.
- **Exit-intent popups that DOM-remove themselves on second hover:**
  the recipe runs while it's still attached; later state is fine.
- **Exit-intent popups stacked behind other popups:** dismiss
  newsletter/modal first, then exit-intent.

## Related skills

- `dismiss-newsletter-popup` — sibling skill; matcher orders by signal
  strength
- `handle-modal-dialog` — generic dialog parent
