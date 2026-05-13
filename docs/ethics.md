# Ethics and ToS

Browser automation sits at a legal and ethical intersection. This
document lays out the project's defaults, the things we won't change,
and what users are on the hook for themselves. None of it is legal
advice.

## Won't-change list

These are non-negotiable for the core repo. PRs that touch them get
closed.

1. No captcha solving. We detect and warn. No solver, no link to a
   solving service, no PRs to integrate one. Every captcha service
   raises threat surface, legal and reputational both; the detection
   skills surface the captcha to the agent and stop, and the agent
   (or human) decides what to do next.

2. No anti-detection or fingerprint spoofing. No stealth plugins, no
   residential proxies, no canvas-fingerprint patchers. Users
   compose those themselves at their own risk. Our default
   Playwright launch is the boring identifiable default.

3. No credential harvesting. Login skills use either a Playwright
   persistent context (the user's already-signed-in browser session)
   or environment variables the user supplies. Keychains, password
   managers, and trace logs are off-limits.

4. No bypassing access controls. Paywalls, age gates, and login
   walls are detected, not bypassed. If a skill can't proceed
   without credentials or payment, it stops and reports.

## Defaults

On by default, intended to make the routine path responsible. Users
can override; the override is recorded in the trace.

- Respect `robots.txt` for the URL pattern in question. Override
  with `--ignore-robots`.
- Rate-limit to roughly one page-load per two seconds per domain.
  Override with `--rate-limit <rps>`.
- User-agent identifies as automated. Default UA includes
  `browser-skills/<version>` so sysadmins can identify and contact
  us. Override with `--user-agent <string>`; setting a misleading UA
  is the user's choice and the user's liability.
- No traversal past `noindex` / `nofollow` for paginated link
  walking, unless explicitly opted in.

## What users are on the hook for

The library is general-purpose; we can't audit your use case.

- Read the target site's Terms of Service. Some permit automation,
  some don't, some require API use, some have rate limits encoded
  in the ToS.
- Respect copyright and database rights. Extracted data may be
  re-distributable, aggregable for personal use only, or legally
  restricted entirely. Your call.
- Respect jurisdictional law. GDPR (EU), CCPA (CA), PIPEDA (CA),
  PIPL (CN), and friends have rules about automated data
  collection and PII handling. Many user goals are fine; some
  aren't.
- Authentication consent. Only automate logins to your own accounts,
  or accounts you have explicit permission to drive.
- The output. What you do with extracted data is on you.

## Benchmark site policy

Benchmarks run against the [curated list](../benchmarks/sites.yaml).
Excluded by selection:

- Sites with scraping-restrictive ToS (LinkedIn, Facebook,
  Instagram).
- Sites with aggressive anti-bot (Amazon retail, some airlines).
- Sites where benchmark-running would violate published rate limits.

If a site's ToS changes or it becomes anti-bot-hostile, we drop it.
The benchmark is a quality signal, not a stress test.

## What the trace records

Each skill execution emits a trace zip (HAR, screenshots, step log).
The trace never contains:

- Cleartext credentials. Even if the agent typed them, they're
  redacted.
- Cookies marked `HttpOnly` or `Secure` unless `--include-cookies`
  is passed.
- Anything the skill marked sensitive via the `sensitive: true`
  metadata flag.

The trace does contain:

- URLs visited and redirects taken.
- DOM snapshots and computed selectors per step.
- Screenshots (full or element-scoped; configurable).
- Decisions the skill made and why.
- Wall time per step.

So traces are shareable for bug reports without leaking secrets.

## Reporting

If you find a skill bypassing access controls, a site reaching out
about benchmark traffic, or a misuse pattern in a downstream user,
open an issue with the `ethics` label. Specific incidents should be
mailed privately to the maintainer.

## Why bother

The 2025–2026 wave of computer-use agents has surfaced real harms:
credential phishing via adversarial sites, scaled copyright
extraction, automated harassment loops. The open-source browser-agent
community is one bad headline away from a tooling backlash. Even if
you don't care about ethics for their own sake, care about not
handing detractors the easy story.
