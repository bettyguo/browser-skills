# Launch posts (drafts)

> Pre-staged copy for Show HN, Reddit, Twitter, and direct outreach.
> Pick a launch day (per the launch-day runbook), then paste these.

---

## Show HN

**Title:** `Show HN: browser-skills – Stop your agent from re-discovering cookie banners`

**Body:**

Hi HN. I built browser-skills, a Skills bundle + MCP server for browser-using AI agents (Claude computer-use, GPT-5.5 native CUA, Gemini Computer Control, anything that drives a browser).

The pitch: modern browser agents are spectacular at reasoning about tasks but **really slow at the boring stuff** — they re-reason cookie banners on every page, get stuck in infinite scroll, and burn vision calls on calendar widgets. A task that should take 90 seconds takes 8 minutes because the agent is re-discovering "how to be a browser user" every session.

That's not a model problem — it's a *content* problem. browser-skills ships 15 reusable site-pattern recipes in the [agentskills.io](https://agentskills.io) format (the open standard Anthropic ratified in Dec 2025, now read by 32 tools). Each recipe is **deterministic first** (selectors + DOM heuristics, ~200 ms per call, zero model invocations) with **vision as fallback** (BYO model adapter — Claude, GPT-5.5, Gemini).

Skills shipping in v1:
- Consent/popups: cookie banners, newsletter, modals, exit-intent
- State: page-loaded, captcha-DETECT (we don't solve — see below)
- Forms: multi-step, file upload, login flows
- Data: table extraction with pagination, infinite scroll
- Widgets: date pickers, searchable dropdowns
- Navigation: search-and-filter, pagination-next-page

**Hard lines:** no captcha solving (detect-only), no anti-detection tooling, no credential harvesting. The full ethics posture is in [docs/ethics.md](docs/ethics.md).

We deliberately *don't* compete with browser-use, Stagehand, browser-act, browserbase/skills, or vercel-labs/agent-browser. We compose with them — recipes are runtime-neutral so the same SKILL.md drives a Claude agent or a browser-use script or a Stagehand workflow.

Repo: https://github.com/browser-skills/browser-skills

Real-Chromium integration tests pass; 41 tests green; benchmark cron re-runs weekly against 20 curated sites. Happy to answer questions.

---

## r/MachineLearning (with [P] flag)

**Title:** `[P] browser-skills: reusable site-pattern recipes for browser-using agents (agentskills.io conformant)`

**Body:**

Posting a small project we shipped after watching browser agents (Claude 4.7, GPT-5.5 CUA, Gemini Computer Control) get spectacularly fast at task reasoning but stay stuck on boring web patterns — cookie banners, infinite scroll, calendar widgets — on every page, every session.

We did some ecosystem recon first. Three browser-skill repos already exist:
- [browserbase/skills](https://github.com/browserbase/skills) (3.2k) — Browserbase capability layers, not site patterns
- [vercel-labs/agent-browser](https://github.com/vercel-labs/agent-browser) (32.9k) — Rust CLI with bundled workflow skills
- [browser-act/skills](https://github.com/browser-act/skills) (1.2k) — vertical scrapers

None of them ships agent-agnostic, runtime-neutral site-pattern recipes (banners, scroll, forms, tables, login). That's our lane.

What we built:
- 15 SKILL.md recipes, fully conformant to agentskills.io spec
- A deterministic-first runner with vision fallback (BYO adapter — Anthropic, OpenAI, Gemini)
- MCP server, installable into Claude Desktop/Cursor/Codex/Continue with one command
- Heuristic matcher (no model call — sub-ms scoring)
- Benchmark harness against 20 curated sites; weekly cron re-validates

The longer-term wedge is **reproducibility + lower variance + lower token cost**, not raw success rate — vendor CUA quality is climbing fast and we don't expect to beat them on perception. We do expect to remain useful by keeping the boring patterns deterministic.

Code: https://github.com/browser-skills/browser-skills
Recipe format spec: https://github.com/browser-skills/browser-skills/blob/main/docs/skill-recipe-format.md
Ecosystem recon: https://github.com/browser-skills/browser-skills/blob/main/docs/ecosystem-recon.md

---

## r/ClaudeAI / r/MCP

**Title:** `browser-skills: 15 reusable web-task recipes + MCP server, installs into Claude Desktop with one command`

**Body:**

If you've ever asked Claude to do something on the web and watched it spend two minutes figuring out a cookie banner, this is for you.

`browser-skills` is a Skills bundle + MCP server with 15 reusable recipes for the boring web stuff Claude (and other browser agents) re-learns on every session: cookie banners, newsletter popups, modal dialogs, multi-step forms, table extraction, infinite scroll, date pickers, login flows.

Install:
```bash
pip install browser-skills
python -m playwright install chromium
browser-skills mcp install claude-desktop
```

Then ask Claude:

> Visit en.wikipedia.org/wiki/List_of_countries_by_population_(United_Nations) and tell me the top 3 most populous countries.

You should see Claude call `list_skills`, `start_browser`, `navigate`, then `invoke_skill("verify-page-loaded")` and `invoke_skill("extract-table-pagination")`. Three seconds, zero vision calls. The table extracts deterministically because the recipe knows how to read `<thead>` + `<tbody>`.

It conforms to the [agentskills.io](https://agentskills.io) spec Anthropic published in December — so the same recipes also work in Codex CLI, Cursor, Gemini CLI, and the other 28 tools that adopted the standard.

Repo: https://github.com/browser-skills/browser-skills

---

## Twitter thread

**Tweet 1:**
> I asked my AI agent to book a flight last week. It failed four times — not because of pricing or layovers, but because it kept getting stuck on cookie banners. 🍪
>
> So we built browser-skills: 15 reusable recipes for the boring web stuff every browser agent re-learns from scratch.
>
> 🧵

**Tweet 2:**
> The dirty secret of 2026 browser agents: they're spectacular at reasoning about *tasks* but glacial at *interfaces*.
>
> Vision agent on an e-commerce site: 5s for cookie banner + 3s for popup + 8s for the search box + 12s for a filter dropdown … per session, every time.
>
> Humans do this in 20s.

**Tweet 3:**
> The wedge isn't a smarter model. It's a library of patterns for the parts that don't deserve reasoning.
>
> @agentskills_io became a ratified standard in Dec 2025 (32 tools read SKILL.md now). All we did was write the missing content layer.

**Tweet 4:**
> 15 skills in v1:
>
> 🍪 cookie banners, newsletter, modals, exit-intent
> ⏳ page-loaded, captcha-DETECT (we never solve)
> 📝 multi-step forms, file upload, login
> 📊 table extraction, infinite scroll
> 🗓️ date pickers, searchable dropdowns
> 🔍 search & filter, pagination

**Tweet 5:**
> Each recipe is deterministic-first (selectors + DOM heuristics, ~200ms, zero model calls).
>
> Vision is the *fallback*, not the primary — BYO adapter (Claude, GPT-5.5, Gemini).
>
> Runs against agentskills.io tools, browser-use, Stagehand, or anything that drives a browser.

**Tweet 6:**
> Hard lines we won't cross:
> ❌ No captcha solving (detect-only)
> ❌ No anti-detection / fingerprint spoofing
> ❌ No credential harvesting
>
> The OSS browser-agent community is one bad headline from a regulatory backlash. Posture matters.

**Tweet 7:**
> Install (1 line):
>
> `pip install browser-skills && browser-skills mcp install claude-desktop`
>
> Or run it from Python. Or drop the skills/ folder into your .claude/skills/ directory.
>
> 41 tests green incl. real-Chromium integration. Repo: github.com/browser-skills/browser-skills

---

## Direct-outreach DMs (templates)

### browser-use maintainers (@magnusrodseth, @gregpr07)

> Hey — built `browser-skills`, an agentskills.io-conformant skills bundle (cookie banners, scroll, tables, forms, etc.) that compose with `browser-use` rather than competing. Each recipe is runtime-neutral; the adapter for `browser-use` is on the roadmap. Would love your sanity check on the format before launch — happy to credit + cross-promote. Repo: [link]

### Stagehand / Browserbase team

> Hey — shipping `browser-skills`, a bundle of agent-agnostic recipes for the boring web patterns (banners, scroll, forms, tables). Conforms to agentskills.io. Built deliberately to *compose* with Stagehand — we ship recipes, you ship primitives. The TS adapter is planned for v1.5. Would love your feedback on the recipe format; could be a fit for `browserbase/skills` alongside your capability-layer skills. Repo: [link]

### Anthropic DevRel (agentskills.io contact)

> Hey — we built the first community-shipped browser-skills bundle for agentskills.io: 15 reusable site-pattern recipes (cookie banners, scroll, tables, forms, login). Fully spec-conformant. Would love to see it listed in the reference-bundle section of agentskills.io if there's interest. Real-Chromium integration tests pass; recipes work cross-runtime. Repo: [link]

### OpenAI DevRel

> Hey — built `browser-skills`, an agent-agnostic skills bundle that works with GPT-5.5 native CUA out of the box. The Codex CLI MCP integration is one command. Could be useful as a reference example for the CUA developer docs — happy to cooperate. Repo: [link]

---

## Launch-day runbook (timeline)

Per the master prompt §7.3:

- **T-14 days:** post Tweet 1 (the cookie-banner frustration). Gauge engagement.
- **T-7 days:** post a 10-second GIF of `dismiss-cookie-banner` running vs not running.
- **T-2 days:** post the full demo video (the 5-conference-paper-monitor scenario).
- **Day 0:**
  - 8:00 PT: Show HN post
  - 9:00 PT: r/MachineLearning, r/MCP, r/ClaudeAI, r/webdev, r/automation
  - 9:30 PT: Twitter thread
  - 10:00 PT: DMs to browser-use, Stagehand, Anthropic, OpenAI contacts
- **Day 0 + 4hrs:** respond to HN comments aggressively (you get one chance at the front page)
- **Day +1:** if traction, draft a follow-up "first 1000 cookie banners dismissed: what failed" post for week 2
- **Day +7:** "First week of browser-skills: numbers, surprises, what's broken" follow-up
