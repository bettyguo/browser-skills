# browser-skills

A bundle of reusable site-pattern recipes for browser-using AI agents,
in the [agentskills.io](https://agentskills.io) SKILL.md format. Drops
into Claude Code, Cursor, Codex CLI, etc., or runs as an MCP server.

[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## What it does

Modern browser agents are good at task reasoning and slow at routine
web interactions. They re-derive how to dismiss a cookie banner every
session, get stuck on infinite-scroll feeds, and burn vision calls on
calendar widgets.

This repo ships 15 recipes for the common boring patterns. Each is
selector-driven by default with vision as a fallback, so most calls
finish in a few hundred milliseconds and zero model tokens.

## Install

```bash
pip install browser-skills
python -m playwright install chromium
browser-skills mcp install claude-desktop   # or: cursor, codex, continue, print
```

Restart your client; the skills are available immediately.

Or use the runner directly:

```python
import asyncio
from playwright.async_api import async_playwright
from browser_skills.adapters.playwright_raw import PlaywrightPage
from browser_skills.runner import Runner
from browser_skills.skill import parse_skill


async def main():
    skill = parse_skill("skills/dismiss-cookie-banner/SKILL.md")
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page()
        await page.goto("https://bbc.com")
        result = await Runner().execute(skill, PlaywrightPage(page))
        print(result.status, result.duration_ms)
        await browser.close()


asyncio.run(main())
```

## Skills

| Skill | Notes |
|---|---|
| [dismiss-cookie-banner](skills/dismiss-cookie-banner/SKILL.md) | OneTrust, Cookiebot, generic accept-all. ~15 selectors. |
| [dismiss-newsletter-popup](skills/dismiss-newsletter-popup/SKILL.md) | Email-signup overlays on content sites. |
| [handle-modal-dialog](skills/handle-modal-dialog/SKILL.md) | Generic `role="dialog"` catch-all, defaults to dismiss. |
| [exit-tracking-popup](skills/exit-tracking-popup/SKILL.md) | Exit-intent overlays. |
| [verify-page-loaded](skills/verify-page-loaded/SKILL.md) | DOM ready, spinner-absent, main content present. |
| [detect-captcha](skills/detect-captcha/SKILL.md) | reCAPTCHA, hCaptcha, Turnstile detection. Detect-only. |
| [fill-multi-step-form](skills/fill-multi-step-form/SKILL.md) | Stepper wizards. |
| [upload-download-file](skills/upload-download-file/SKILL.md) | HTML5 file inputs. |
| [login-flow](skills/login-flow/SKILL.md) | env-var credentials or persistent context. Trace redacts passwords. |
| [extract-table-pagination](skills/extract-table-pagination/SKILL.md) | `<table>` to list of row dicts. |
| [handle-infinite-scroll](skills/handle-infinite-scroll/SKILL.md) | scroll-until-no-more-content with stop conditions. |
| [search-and-filter](skills/search-and-filter/SKILL.md) | Type a query, submit, capture results. |
| [pagination-next-page](skills/pagination-next-page/SKILL.md) | `rel="next"`, `aria-label="Next"`, and friends. |
| [date-picker-widget](skills/date-picker-widget/SKILL.md) | Native `<input type="date">` plus custom calendars. |
| [searchable-dropdown](skills/searchable-dropdown/SKILL.md) | `role="combobox"` typeahead. |

## MCP server

`browser-skills mcp install <client>` writes the stdio stanza into the
right config file. The server exposes:

```
start_browser(headed=False)                 -> session_id
navigate(session_id, url)                   -> page_state
list_skills()                               -> catalog
reload_skills()                             -> reload SKILL.md files
list_applicable_skills(session_id)          -> matcher results
invoke_skill(session_id, skill_name, vars)  -> SkillResult
screenshot(session_id, selector?)           -> b64 PNG
page_state(session_id)                      -> debug shape
close_browser(session_id)                   -> trace_id (if any)
```

HTTP transport works via `browser-skills mcp serve --transport=streamable-http`
but is not offered by the install command until bearer-token validation
is wired up.

See [docs/mcp-design.md](docs/mcp-design.md) for the full surface and
error envelope.

## What this won't do

- Solve captchas. Detect-and-warn only.
- Anti-bot evasion or fingerprint spoofing.
- Harvest or persist credentials. Login skills use a Playwright
  persistent context or env-var values.

`robots.txt` is respected by default, the rate limit is human-cadence,
the user-agent identifies as `browser-skills/<version>`. See
[docs/ethics.md](docs/ethics.md).

## Authoring a skill

```bash
browser-skills new my-skill
$EDITOR skills/my-skill/SKILL.md
browser-skills test my-skill --headed
```

The format is YAML frontmatter plus a Markdown body with a structured
`## Recipe` section. Walkthrough in [docs/authoring.md](docs/authoring.md);
DSL spec in [docs/skill-recipe-format.md](docs/skill-recipe-format.md).

## Benchmarks

Twenty sites in [benchmarks/sites.yaml](benchmarks/sites.yaml), each
exercising at least two skills. A weekly cron runs the full suite and
publishes results to GitHub Pages; stale selectors open issues
automatically.

```bash
python benchmarks/run.py --quick      # matcher only, no network
python benchmarks/run.py --mode=full  # real Chromium against the 20 sites
```

## License

[MIT](LICENSE). Contributors sign commits off with `git commit -s`
(DCO); see [CONTRIBUTING.md](CONTRIBUTING.md).