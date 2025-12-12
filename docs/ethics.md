# Ethics + ToS posture

> Browser automation sits at a legal and ethical intersection. This document
> sets the project's defaults, hard lines, and what users are on the hook
> for. It is not legal advice. It is a credible OSS-community posture.

## Hard lines (will not change)

The following are **non-negotiable** for the core project. PRs that violate
these will be closed, regardless of demand.

1. **No captcha solving.** We `detect-and-warn`. We never ship a solver, we
   never link out to a solving service as a "compatible companion," and we
   never accept PRs to integrate one.
   - Why: every captcha service raises the threat surface (legal,
     reputational, the kind of users that arrive in the community).
   - What detection skills do: identify the captcha type, surface it
     to the agent, stop. The agent (or human) decides next.
2. **No anti-detection / fingerprint spoofing.** We don't bundle stealth
   plugins, residential proxies, canvas-fingerprint patchers, or
   anti-bot-evasion tooling. Users compose those themselves at their own
   risk. Our default Playwright launch is the boring, identifiable default.
3. **No credential harvesting.** Login skills use:
   - **Playwright persistent context** (the user's already-signed-in browser
     session), OR
   - **Environment variables** the user provides
   We never read keychains, scrape password managers, or store credentials
   anywhere in the trace.
4. **No solving of access control.** Paywalls, age gates, and login walls
   are **detected**, not bypassed. If a skill can't proceed without
   credentials/payment, it stops and reports.

## Defaults (configurable; opt-out documented)

These are **on by default** to make the boring-case behavior responsible.
Users can override; the override is visible in the trace.

- **Respect `robots.txt`** for the URL pattern in question. Toggle:
  `--ignore-robots` (and the override is recorded in the trace).
- **Rate limit to human-like cadence.** ~1 page-load / 2 seconds by default
  across a domain. Toggle: `--rate-limit <rps>`.
- **User-Agent identifies as automated.** Default UA includes
  `browser-skills/<version>` so sysadmins can identify and contact us.
  Toggle: `--user-agent <string>`. (Setting a misleading UA is **your**
  choice and **your** liability.)
- **No scraping past `noindex`/`nofollow`** for paginated link traversal
  unless explicitly opted in.

## What users are on the hook for

The library is general-purpose. We don't and can't audit your use case.
You are responsible for:

- **Reading each target site's Terms of Service.** Some sites permit
  automation; some don't; some require API use; some have rate limits
  encoded in their ToS. Read them.
- **Respecting copyright / database rights.** Extracted data may be
  re-distributable, may be aggregable for personal use only, or may be
  legally restricted entirely. That's your call.
- **Respecting jurisdictional law.** GDPR (EU), CCPA (CA), PIPEDA (CA),
  PIPL (CN), and others have rules about automated data collection and
  PII handling. Many user goals are fine; some aren't. Read up.
- **Authentication consent.** Only automate logins to your own accounts
  or accounts you have explicit permission to drive.
- **The output.** What you do with extracted data is on you.

## Benchmark site policy

We run benchmarks against [a curated list](../benchmarks/sites.yaml). The
selection criteria explicitly exclude:

- Sites with scraping-restrictive ToS (LinkedIn, Facebook, Instagram).
- Sites with aggressive anti-bot postures (Amazon retail, some airlines).
- Sites where benchmark-running would violate published rate limits.

If a benchmark site changes its ToS or becomes anti-bot-hostile, we drop
it. The benchmark is a quality signal, not a stress test.

## What the trace records (and doesn't)

Every skill execution emits a trace zip (HAR + screenshots + step log).
The trace **never** contains:

- Cleartext credentials (even if the agent typed them — they're redacted)
- Cookies marked HttpOnly / Secure unless the user passes `--include-cookies`
- Any data the skill itself was told to mark sensitive (via the
  `sensitive: true` recipe convention)

The trace **does** contain:

- URLs visited, redirects taken
- DOM snapshots and computed selectors at each step
- Screenshots (full or element-scoped, configurable)
- Decisions the skill made and why ("matched `#onetrust-accept-btn-handler`")
- Wall time per step

This makes traces shareable for bug reports without leaking secrets.

## Reporting concerns

If you find:

- A skill that bypasses an access control we don't intend it to
- A site reaching out about our benchmark traffic
- A misuse pattern in a downstream user we should know about

Open an issue with the `ethics` label, or email the maintainers privately
if it involves a specific incident. We move on these quickly.

## Why this posture (and why now)

Browser automation is having a regulatory moment. The 2025-2026 wave of
computer-use agents has surfaced real harms — credential phishing via
adversarial websites, copyright extraction at scale, automated harassment
loops. The OSS browser-agent community as a whole is one bad headline away
from a tooling backlash. Posture matters. Even if you don't care about the
ethics for their own sake, care about not handing detractors the easy story.

— The maintainers
