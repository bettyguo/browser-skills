---
name: detect-captcha
description: Detects whether the current page contains a captcha challenge (reCAPTCHA, hCaptcha, Cloudflare Turnstile, GeeTest, etc.). Reports detection and stops. Never attempts to solve. See docs/ethics.md.
version: 0.1.0
allowed-tools: [wait_for_dom_ready, extract_text, assert]
metadata:
  applies_to: any-website
  url_patterns: ["*"]
  dom_markers:
    - ".g-recaptcha"
    - ".h-captcha"
    - ".cf-turnstile"
    - "iframe[src*='recaptcha']"
    - "iframe[src*='hcaptcha']"
    - "iframe[src*='challenges.cloudflare.com']"
  flake_rate_target: 0.02
  flake_rate_measured: null
  exercised_on:
    - cloudflare-protected-test
  cost_budget:
    deterministic_only: true
    max_vision_calls: 0
  sensitive: false
---

# Detect Captcha

## When to invoke

Run any time the deterministic recipe of another skill fails on what *looks like* it should have worked, OR proactively before any step that involves form submission, login, or rate-sensitive interaction. The matcher runs this when known captcha markers appear in the DOM.

**This skill is detect-only.** It identifies captcha provider, surfaces metadata, and stops. If you need to bypass a captcha, you are out of scope of this project — see [docs/ethics.md](../../docs/ethics.md). PRs adding solving logic will be closed.

## Recipe

1. wait_for_dom_ready timeout=3s
2. extract_text selector=".g-recaptcha, .h-captcha, .cf-turnstile, iframe[src*='recaptcha'], iframe[src*='hcaptcha'], iframe[src*='challenges.cloudflare.com']" into="$captcha_marker" optional=true

## Success criteria

The skill always returns `success` if the recipe completes. The interesting state is in the returned `extracted` map:

- `$captcha_marker` populated → captcha detected (the value identifies the provider via its container class or iframe URL)
- `$captcha_marker` not populated → no captcha present

The caller decides what to do next: stop, prompt the user, switch to a non-captcha-protected URL, etc.

## When NOT to use

- Never. This skill is cheap, deterministic, and side-effect-free. Always safe to invoke.

## Known failures

- **Invisible captchas (~15% of reCAPTCHA v3 deployments):** the badge is hidden by default. The challenge only appears on risk-flagged sessions. Detection via the `.grecaptcha-badge` selector covers this case; it's in v0.2.0.
- **Custom captcha implementations (~5%):** sites running bespoke "click the kittens" challenges won't match standard markers. Vision detection would help but vision fallback is forbidden for this skill (see `cost_budget.max_vision_calls: 0`).
- **Captcha loaded post-interaction:** the captcha only renders after a form-submit click. Re-invoke this skill after any submit step.

## Example usage

```
Agent task: "Search for foo on site X and grab the first 3 results."
→ invoke_skill("verify-page-loaded") → success
→ invoke_skill("dismiss-cookie-banner") → success
→ invoke_skill("detect-captcha") → success, $captcha_marker = None
→ invoke_skill("search-and-filter") → success
...vs...
→ invoke_skill("detect-captcha") → success, $captcha_marker = "<reCAPTCHA iframe>"
→ agent: "Site X is showing a reCAPTCHA. I cannot continue automatically. Switch to a different source?"
```

## Ethical posture

This skill exists *to make captcha presence visible to the agent* so the agent (and the user) can make an informed decision. The decision is **not** "now solve it." See ADR-004 in [DECISIONS.md](../../DECISIONS.md).

## Related skills

- `verify-page-loaded` — captchas often render after page load; run loaded-check first
- `detect-rate-limit` (v0.2.0) — captchas often appear after rate-limit triggers
