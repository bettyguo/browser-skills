---
name: login-flow
description: Signs into a site using credentials provided via `vars` (typically sourced from environment variables) or via a pre-saved Playwright persistent context. Never harvests or stores credentials. See docs/ethics.md.
version: 0.1.0
allowed-tools: [wait_for_dom_ready, wait_for_selector, fill, click, wait, assert]
metadata:
  applies_to: any-website
  url_patterns: ["*"]
  dom_markers:
    - "input[type='password']"
    - "[aria-label*='password' i]"
    - "form[action*='login' i]"
  flake_rate_target: 0.10
  exercised_on:
    - the-internet-herokuapp
  cost_budget:
    deterministic_only: false
    max_vision_calls: 1
  sensitive: true
---

# Login Flow

## When to invoke

The user task requires authentication. The agent provides credentials in:

- `vars.username` (or `vars.email`)
- `vars.password`

Per  and [docs/ethics.md](../../docs/ethics.md): we use the
agent-provided creds *only* — typically sourced by the agent from env
vars (`$SITE_X_USER`, `$SITE_X_PASS`) the user has set, or from a
password manager the user controls. **We never harvest, prompt for, or
store credentials.** The `sensitive: true` metadata flag tells the
trace recorder to redact form-fill events in the exported zip.

## Recipe

1. wait_for_dom_ready timeout=5s
2. wait_for_selector selector="input[type='password']" state=visible timeout=5s
3. fill selector="input[type='email'], input[name='username'], input[name='email'], input[id='username'], input[id='email']" value="$vars.username"
4. fill selector="input[type='password']" value="$vars.password"
5. click selector="button[type='submit'], button:has-text('Sign in'), button:has-text('Log in'), input[type='submit']"
6. wait extra=1000ms

## Success criteria

- assert no_visible_element selector="input[type='password']"
- assert url_changed_since=step1 OR cookie_set_named="session"

## When NOT to use

- **OAuth / SSO flows** that redirect through identity providers
  (Google, Microsoft, Okta). Use `handle-oauth-redirect` (v0.2.0).
- **Magic-link / passwordless flows.** Out of v1 scope; agent must
  poll its inbox separately.
- **MFA-protected logins.** If MFA is enabled and there's no pre-saved
  session, the recipe will hit the MFA challenge and stop. The agent
  surfaces the MFA prompt and asks the user how to proceed.

## Known failures

- **Sites that hide the password field until the email is submitted
  first** (Google-style): the recipe fills email, submits, then needs
  to re-find the password field. v0.1 fails on these; the agent can
  retry with a "submit, wait, re-invoke" loop.
- **Captcha after a few failed attempts:** `detect-captcha` should be
  chained after this skill.
- **"Are you sure?" dialogs post-login:** `handle-modal-dialog` chains.

## Trace handling

Per `sensitive: true`:
- form-fill events for password fields are recorded as `{value:
  "[REDACTED]"}` in the trace
- screenshots taken during this skill's steps are blackened over the
  password field's bounding box (v0.1 omits screenshots from this
  skill entirely)

## Related skills

- `dismiss-cookie-banner` — sites with consent walls hit this first
- `detect-captcha` — failed-login rate-limiting often triggers captcha
