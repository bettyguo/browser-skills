---
name: dismiss-cookie-banner
description: Detects and dismisses cookie consent banners on any site. Use on the first interaction after navigation to any page that may show a banner.
version: 0.1.0
allowed-tools: [wait_for_dom_ready, wait, try_each, assert]
metadata:
  applies_to: any-website
  url_patterns: ["*"]
  dom_markers:
    - "[aria-label*='cookie' i]"
    - "#onetrust-banner-sdk"
    - ".cc-window"
    - "[id*='cookie' i][role='dialog']"
  flake_rate_target: 0.05
  flake_rate_measured: null
  exercised_on:
    - bbc-home
    - guardian-home
    - nytimes-home
  cost_budget:
    deterministic_only: false
    max_vision_calls: 1
  sensitive: false
---

# Dismiss Cookie Banner

## When to invoke

On the first interaction after navigating to a new page, before the agent attempts to interact with content. Especially relevant for sites in EU, UK, California, or Chinese jurisdictions, where banners are near-universal.

The matcher will assign this skill a high score when:
- `is_initial_load = true`
- `cookies_present = true` and DOM contains a cookie-related marker

## Recipe

1. wait_for_dom_ready timeout=2s
2. wait extra=400ms
3. try_each selectors=[
     "#onetrust-accept-btn-handler",
     "button#onetrust-pc-btn-handler",
     ".cc-allow",
     ".cc-accept-all",
     "button.cookie-accept",
     "button:has-text('Accept all cookies')",
     "button:has-text('Accept All Cookies')",
     "button:has-text('Accept all')",
     "button:has-text('Accept cookies')",
     "button:has-text('I Agree')",
     "button:has-text('Agree and continue')",
     "button:has-text('Got it')",
     "[aria-label*='Accept' i][aria-label*='cookie' i]",
     "[data-testid*='cookie-banner-accept']",
     "[data-cookieconsent='accept']",
   ] action=click on_success=stop timeout=1500ms
4. wait extra=300ms

## Success criteria

- assert no_visible_element selector="[aria-label*='cookie' i][role='dialog']" OR no_visible_element selector="#onetrust-banner-sdk" OR no_change_was_needed

## When NOT to use

- The user task is *about* the cookie banner itself — e.g., privacy testing, a screenshot of the pre-consent state, or auditing consent UI.
- The site has already had its banner dismissed in the persistent context (this skill is idempotent but logs an unnecessary execution).

## Known failures

- **Custom CMS banners (~2% of sites):** sites running bespoke consent UIs may not match any of the standard selectors. The vision fallback handles these when an adapter is configured; otherwise the skill returns `failed` and the agent decides.
- **Cross-origin iframe banners (~1%):** banners served from a different origin (e.g., embedded consent providers using `<iframe>`) cannot be clicked through Playwright's default context. We report `failed` with `reason="iframe_cross_origin"`.
- **"Reject all" intent:** this skill always accepts. If your task requires rejecting cookies, use the future `reject-cookie-banner` skill (post-launch) or override the recipe via the agent.

## Example usage

```
Agent: "Go to bbc.com and tell me the top story."
→ matcher selects [dismiss-cookie-banner, verify-page-loaded, extract-text]
→ invoke_skill("dismiss-cookie-banner") → success in 207ms, deterministic_path=true
→ invoke_skill("verify-page-loaded") → success in 84ms
→ agent reads the top story headline directly
```

## Related skills

- `verify-page-loaded` — typically chained immediately after this one
- `dismiss-newsletter-popup` — sometimes co-occurs on news sites
- `exit-tracking-popup` — for the rare "we use cookies for analytics" upsells that aren't the main consent UI
