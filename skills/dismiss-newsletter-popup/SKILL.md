---
name: dismiss-newsletter-popup
description: Dismisses newsletter / "subscribe" / "sign up for emails" popups that appear after a short delay or scroll trigger on content sites.
version: 0.1.0
allowed-tools: [wait_for_dom_ready, wait, try_each, press_key]
metadata:
  applies_to: any-website
  url_patterns: ["*"]
  dom_markers:
    - "[class*='newsletter' i]"
    - "[id*='newsletter' i]"
    - "[class*='subscribe' i]"
    - "[aria-label*='newsletter' i]"
  flake_rate_target: 0.10
  exercised_on:
    - guardian-home
    - nytimes-home
    - rei-search
  cost_budget:
    deterministic_only: false
    max_vision_calls: 1
---

# Dismiss Newsletter Popup

## When to invoke

After a few seconds on a content site (news, blogs, retail), a popup
appears offering a newsletter signup. The dismiss controls are typically:
a small "x" in the corner, a "no thanks" link, or pressing Escape.

The matcher fires this skill when the DOM contains a newsletter marker
*and* the page is not in initial-load (these popups typically appear
after a delay).

## Recipe

1. wait_for_dom_ready timeout=2s
2. wait extra=200ms
3. try_each selectors=[
     "[class*='newsletter' i] button[aria-label*='close' i]",
     "[id*='newsletter' i] button[aria-label*='close' i]",
     "[class*='subscribe' i] button[aria-label*='close' i]",
     "[class*='newsletter' i] button:has-text('No thanks')",
     "[class*='subscribe' i] button:has-text('No thanks')",
     "[class*='newsletter' i] button:has-text('Maybe later')",
     "button.newsletter-dismiss",
     "button.email-signup-close",
     "[data-testid*='newsletter-close']",
     "[data-testid*='email-signup-close']",
   ] action=click on_success=stop timeout=1000ms
4. press_key key=Escape

## Success criteria

- assert no_visible_element selector="[class*='newsletter' i][role='dialog']" OR no_change_was_needed

## When NOT to use

- The user explicitly wants to subscribe — don't auto-dismiss.

## Known failures

- **Popups that block scroll until interacted with:** Escape doesn't always close them; the close button is small and unlabeled. Vision fallback for these.
- **Popups inside cross-origin iframes:** can't be clicked through Playwright's default context.
- **Multiple newsletter popups stacked:** v0.1 dismisses one; agent re-invokes for the next.
