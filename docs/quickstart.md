# Quickstart

5-minute end-to-end. Assumes a working Python 3.11+ and pip.

## Install

```bash
pip install browser-skills
python -m playwright install chromium
```

## Install the MCP server into your client

Pick the one you use; the command writes the right JSON to the right
config file, prompting only when overwrite is needed.

```bash
browser-skills mcp install claude-desktop    # macOS / Windows / Linux
browser-skills mcp install cursor
browser-skills mcp install codex
browser-skills mcp install continue
browser-skills mcp install print             # print JSON to stdout, copy-paste manually
```

Restart the client.

## Sanity check

In your client, ask the agent:

> List your available browser-skills. Then start a browser, visit `https://en.wikipedia.org/wiki/List_of_countries_by_population_(United_Nations)`, and tell me the top 3 most-populous countries from the table.

You should see the agent call `list_skills`, `start_browser`,
`navigate`, `list_applicable_skills`, then `invoke_skill("verify-page-loaded")`
and `invoke_skill("extract-table-pagination")`. The answer comes back
in a few seconds with no vision calls; the table is structured HTML.

## Author your first skill

```bash
mkdir skills/dismiss-acme-banner && $EDITOR skills/dismiss-acme-banner/SKILL.md
```

Minimum-viable skill:

```markdown
---
name: dismiss-acme-banner
description: Dismisses the ACME consent banner that appears on acme.example
version: 0.1.0
allowed-tools: [click, wait]
metadata:
  url_patterns: ["*acme.example*"]
  dom_markers: ["#acme-banner"]
  exercised_on: [acme-home, acme-help]
---

# Dismiss ACME Banner

## When to invoke
First page load on `acme.example`.

## Recipe
1. wait extra=300ms
2. click selector="#acme-banner-accept"
3. wait extra=200ms

## Success criteria
- assert no_visible_element selector="#acme-banner"
```

Test it against a local HTML file:

```bash
mkdir -p tests/fixtures/dismiss-acme-banner
$EDITOR tests/fixtures/dismiss-acme-banner/page.html   # paste in a banner mock
browser-skills test dismiss-acme-banner --headed
```

## Reuse in your scripts

```python
import asyncio
from playwright.async_api import async_playwright
from browser_skills.adapters.playwright_raw import PlaywrightPage
from browser_skills.matcher import PageState, match
from browser_skills.runner import Runner
from browser_skills.skill import load_bundle

skills = load_bundle("skills/")
runner = Runner()

async def visit(url: str) -> None:
    async with async_playwright() as pw:
        browser = await pw.chromium.launch()
        page = await browser.new_page()
        await page.goto(url, wait_until="domcontentloaded")
        dom = (await page.content())[:4000]
        state = PageState(url=page.url, dom_summary=dom,
                          cookies_present=True, is_initial_load=True)
        for candidate in match(skills, state).skills[:3]:
            skill = next(s for s in skills if s.name == candidate.name)
            result = await runner.execute(skill, PlaywrightPage(page))
            print(f"  {candidate.name}: {result.status} ({result.duration_ms}ms)")
        await browser.close()

asyncio.run(visit("https://www.bbc.com/"))
```

## Where to next

- [docs/skill-recipe-format.md](skill-recipe-format.md): the SKILL.md DSL in full.
- [docs/matcher-design.md](matcher-design.md): how skills get picked.
- [docs/runner-design.md](runner-design.md): execution semantics and vision fallback.
- [docs/mcp-design.md](mcp-design.md): the MCP tool surface.
- [docs/ethics.md](ethics.md): what we will and won't do.
- [CONTRIBUTING.md](../CONTRIBUTING.md) for PRs.
