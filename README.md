# browser-skills

> **The missing content layer for [agentskills.io](https://agentskills.io).**
> Agent-agnostic, runtime-neutral recipes for the boring web patterns every browser agent re-learns from scratch — cookie banners, infinite scroll, multi-step forms, table extraction, login flows.

[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![SKILL.md spec](https://img.shields.io/badge/spec-agentskills.io-blue.svg)](https://agentskills.io/specification)

**Status:** v0.1.0, pre-launch (May 2026). 15 skills shipped; 41 tests green; real-Chromium integration verified.

---

## The problem

Browser agents in 2026 (Claude 4.7, GPT-5.5 native CUA, Gemini Computer Control) are **bad at the boring stuff**. They re-reason cookie banners on every page. They get stuck in infinite scroll. They burn vision calls on calendar widgets. A task that should take 90 seconds takes 8 minutes because the agent is re-discovering how to be a browser user, every page, every session.

That's not a model problem. It's a **content** problem. The agent doesn't need a smarter brain — it needs a **library of patterns** for the parts that don't deserve reasoning.

## The fix

Drop this skills folder into your `.claude/skills/` directory (or any tool that reads the [agentskills.io](https://agentskills.io) standard — Claude Code, Codex, Cursor, VS Code Copilot, Gemini CLI, Junie, Kiro, Goose, …). Or run the MCP server. Either way, your agent now handles:

- Cookie banners in 200 ms instead of 4 reasoning steps
- Infinite scroll with a documented stop condition
- Multi-step forms with field-label inference
- Table extraction (paginated, virtualized, server-side-sorted)
- Login flows (your creds, your session — we never harvest)
- 10 more boring patterns

…all **deterministically** when selectors hold, with **vision as the fallback** when they don't. Reproducible across runs. Lower token cost. Cross-agent.

## Quickstart

```bash
pip install browser-skills
python -m playwright install chromium
browser-skills mcp install claude-desktop     # or: cursor, codex, continue, print
# restart your client; the 15 skills + 8 MCP tools are now available
```

Or use it directly from Python:

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
        print(f"{result.status} in {result.duration_ms}ms — vision used: {not result.deterministic_path}")
        await browser.close()

asyncio.run(main())
```

## Skill catalog

15 skills in v1. Each conforms to the [agentskills.io specification](https://agentskills.io/specification) and ships with documented success criteria, known failures, and per-site flake-rate targets.

| Category | Skill | What it does |
|---|---|---|
| **Consent / popups** | [dismiss-cookie-banner](skills/dismiss-cookie-banner/SKILL.md) | OneTrust, Cookiebot, CC-window, custom — 15 selectors. <5% target flake. |
| | [dismiss-newsletter-popup](skills/dismiss-newsletter-popup/SKILL.md) | "Subscribe!" overlays on content sites. |
| | [handle-modal-dialog](skills/handle-modal-dialog/SKILL.md) | Generic `role="dialog"` catch-all, defaults to dismiss. |
| | [exit-tracking-popup](skills/exit-tracking-popup/SKILL.md) | "Wait! Don't leave!" exit-intent overlays. |
| **State checks** | [verify-page-loaded](skills/verify-page-loaded/SKILL.md) | DOM ready + spinner-absent + main-content present. Vision-forbidden. |
| | [detect-captcha](skills/detect-captcha/SKILL.md) | reCAPTCHA / hCaptcha / Turnstile detection. **Detect-only.** See [ethics](docs/ethics.md). |
| **Forms** | [fill-multi-step-form](skills/fill-multi-step-form/SKILL.md) | Stepper wizards (Typeform, Calendly-style). |
| | [upload-download-file](skills/upload-download-file/SKILL.md) | HTML5 file inputs. |
| | [login-flow](skills/login-flow/SKILL.md) | env-var creds or persistent context. `sensitive: true`; trace redacts passwords. |
| **Data extraction** | [extract-table-pagination](skills/extract-table-pagination/SKILL.md) | `<table>` → list of row dicts. The demo skill. |
| | [handle-infinite-scroll](skills/handle-infinite-scroll/SKILL.md) | Scroll-until-no-more-content with documented stop conditions. |
| **Navigation** | [search-and-filter](skills/search-and-filter/SKILL.md) | Type query, submit, capture results. |
| | [pagination-next-page](skills/pagination-next-page/SKILL.md) | `rel="next"`, aria-label="Next", `li.next`, etc. |
| **Widgets** | [date-picker-widget](skills/date-picker-widget/SKILL.md) | Native `<input type="date">` + custom calendar widgets. |
| | [searchable-dropdown](skills/searchable-dropdown/SKILL.md) | `role="combobox"` typeahead. |

See  for the brainstorm-to-cut rationale.

## What makes this different

| | Existing browser-skill repos | browser-skills |
|---|---|---|
| Format | Custom or vendor-coupled | [agentskills.io](https://agentskills.io) conformant — drops into 32 tools |
| Skill content | CLI capabilities or vertical scrapers | **Site patterns** (banners, scroll, forms, tables) |
| Runtime | Coupled to one CLI / framework | Cross-runtime via MCP — Claude, GPT-5.5, Gemini, browser-use, Stagehand, Playwright |
| Execution | Mostly vision-driven | **Deterministic first**, vision as fallback |
| Captcha | "Solving libraries available" | **Detect only.** Never solve. Ever. |
| Reproducibility | Drifts between runs | Same recipe, same outcome — variance is a *bug* |

Adjacent repos we don't compete with on content:
[browserbase/skills](https://github.com/browserbase/skills) (Browserbase capability layers),
[vercel-labs/agent-browser](https://github.com/vercel-labs/agent-browser) (32k-star Rust CLI workflows),
[browser-act/skills](https://github.com/browser-act/skills) (vertical scrapers).
We integrate with their delivery; we don't replicate their function.

## MCP server

After `browser-skills mcp install <client>`:

```
start_browser(headed=False)                 → session_id
navigate(session_id, url)                   → page_state
list_skills()                               → catalog
reload_skills()                             → force-reread SKILL.md files
list_applicable_skills(session_id)          → matcher results
invoke_skill(session_id, skill_name, vars)  → SkillResult (deterministic, traced)
screenshot(session_id, selector?)           → b64 PNG
page_state(session_id)                      → debug shape
close_browser(session_id)                   → trace_id (if any)
```

See [docs/mcp-design.md](docs/mcp-design.md) for the full surface, auth model, and error envelopes.

## Ethics + ToS

Browser automation is having a regulatory moment. We take a credible posture:

- **No captcha solving.** Detect-and-warn only. Hard line.
- **No anti-detection / fingerprint spoofing.** Default Playwright launch, identifiable UA.
- **No credential harvesting.** Login skills use persistent context or env vars only.
- **Respect `robots.txt`** by default; rate-limit to human-like cadence; identify as `browser-skills/<version>` in the UA string.

Full posture in [docs/ethics.md](docs/ethics.md).

## Authoring your own skill

```bash
mkdir skills/my-skill && $EDITOR skills/my-skill/SKILL.md
```

The format is `agentskills.io` YAML frontmatter + Markdown body with a structured `## Recipe` section. Full spec: [docs/skill-recipe-format.md](docs/skill-recipe-format.md). Walkthrough: [CONTRIBUTING.md](CONTRIBUTING.md).

Test against a local fixture:
```bash
browser-skills test my-skill --fixture tests/fixtures/my-skill/page.html --headed
```

## Benchmarks

Twenty curated, ToS-friendly sites in [benchmarks/sites.yaml](benchmarks/sites.yaml). Each v1 skill is exercised on ≥2 of them. The benchmark cron re-runs weekly post-launch (see [.github/workflows/benchmark.yml](.github/workflows/benchmark.yml)); stale-selector failures open issues automatically.

```bash
python benchmarks/run.py --quick       # matcher recall, no network (CI)
python benchmarks/run.py --mode=full   # real Chromium, ~10 min
```

## Project state

- the project tracker — current phase, hours, blockers, next steps
- the project's ethics doc — 12 ADRs (no captcha solving, vision-as-fallback, BYO vision adapter, etc.)
- [docs/](docs/) — design docs (recipe format, matcher, runner, MCP, ethics, ecosystem)
-  — competitive landscape (May 2026)

## License

[MIT](LICENSE). All skills MIT under the ethics doc. DCO sign-off on commits ([CONTRIBUTING.md](CONTRIBUTING.md)).
