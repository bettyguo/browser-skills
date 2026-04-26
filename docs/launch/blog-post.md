# Why browser agents are bad at the boring stuff (and how to fix it)

> Draft. ~2000 words. Companion to the v1 launch. Final pass and pub date set by the launch-day runbook.

---

I asked my agent to book a flight for me last week. It failed four times. Not because the model couldn't reason about prices or layovers — that part was fine. It failed because the agent kept getting stuck on cookie banners.

Specifically: the *same* cookie banner. The booking site uses a standard OneTrust consent banner that any human dismisses in half a second by clicking "Accept All Cookies." The first time my agent saw it, it took 4 reasoning steps to figure out what the banner was, what the buttons did, and which one to click. Fine — that's the cost of generality.

But on the next site, the next test run, the next session — **it did the entire reasoning trip again.** Every single time. Same model, same banner, same conclusion. Forty-five seconds of wall time, three vision calls, $0.12 of token cost, per page, per session. For something the human user solved in *half a second* by **already knowing what a cookie banner is.**

That's not a model problem. That's a content problem.

## The hot category, the cold reality

Computer-use and browser agents are the freshest hot category in AI in 2026. Anthropic's computer-use API has matured significantly since 2025. GPT-5.5 (April 2026) shipped native computer-use. Claude 4.6 + Agent Teams (Feb 2026) made multi-step browser workflows tractable. Gemini Computer Control isn't far behind.

The capabilities are *spectacular*. The models can read a webpage, understand what the user wants, plan a multi-step interaction, recover from errors, and execute. WebVoyager benchmarks have climbed from ~60% to ~89% in eighteen months. By any reasonable measure, browser agents work.

And yet. Anyone who's actually deployed one knows the dirty secret: **they're glacial for the boring stuff.**

A vision-only agent on a typical e-commerce site:

- 5 seconds dismissing the cookie banner (it has to read it, decide what to do, click, verify)
- 3 seconds dismissing the newsletter popup (same pattern, again)
- 8 seconds figuring out the search box (oh, it's a `<button>` that opens a search overlay, not an inline input)
- 12 seconds applying a filter (the dropdown is a custom React component the model has to *visually parse*)
- 30 seconds extracting search results (visiting each result, scrolling, OCR'ing prices)
- Finally returning your answer

A human does this in 20 seconds. The agent takes 5 minutes. **80% of that time is on patterns the agent has seen a thousand times before and re-reasons from scratch each session.**

The wedge isn't a smarter model. It's a library of patterns for the parts that don't deserve reasoning.

## What we tried before

Lots of folks have tried to fix this. They mostly fall into three camps:

**The wrapper camp.** Tools like browser-use (~91k stars on GitHub) and Stagehand (Browserbase) wrap Playwright and add LLM glue. They give you nice primitives — `act("click the accept button")`, `extract("the product price")` — but the LLM still does the reasoning every time. Better than raw Playwright, but the model is still inside the hot path of every interaction.

**The framework camp.** Tools like Skyvern build vertical agents around specific use cases (forms, RPA, vertical workflows). Great for the use cases they cover; you're on your own outside them. And they're framework-coupled — you can't take a Skyvern "skill" and run it under a Claude agent.

**The bundle camp.** A handful of repos ship reusable skill bundles. Browserbase has [browserbase/skills](https://github.com/browserbase/skills) — but those are capability layers tied to their cloud platform (`bb` CLI, `browser-trace`, residential proxies). Vercel Labs has [vercel-labs/agent-browser](https://github.com/vercel-labs/agent-browser) — 32.9k stars! — but the skills are coupled to their Rust CLI. There's [browser-act/skills](https://github.com/browser-act/skills) — but those are vertical scrapers (Amazon ASIN lookup, YouTube transcripts), not generic patterns.

None of them ship the thing I actually wanted: **agent-agnostic, runtime-neutral recipes for the boring stuff that any browser-using agent re-learns from scratch.**

## A funny thing happened in December

While we were sketching this project, Anthropic dropped a bomb: on December 18, 2025, they ratified Agent Skills as an open standard at [agentskills.io](https://agentskills.io). Apache 2.0 / CC-BY-4.0. By March 2026, 32 tools read the same `SKILL.md` format — Claude Code, Codex CLI, ChatGPT, Cursor, VS Code Copilot, Gemini CLI, Junie, Kiro, Goose, and a long tail.

This was huge. It meant we didn't need to invent a format. We didn't need to lobby vendors. We didn't need to fight for distribution. **There was already a ratified industry standard with 32-tool adoption.** It just needed *content*.

That's what `browser-skills` is. The missing content layer for `agentskills.io`. We don't compete with `browser-use` or `Stagehand` or `agent-browser` — we *compose* with them. We ship 15 reusable, deterministic site-pattern recipes in the format every modern agent already knows how to read.

## The wedge: deterministic first, vision second

Every recipe in `browser-skills` has two tiers:

1. **A deterministic selector-based sequence.** For 80%+ of pages, this hits. Cookie banner? `try_each` across 15 known selectors. First one that matches, click. Done in 200 ms, zero model calls.

2. **A vision fallback.** When the deterministic path fails (custom banner, unusual DOM), the runner invokes a vision adapter (BYO model — Claude, GPT-5.5, Gemini, your call) to figure out the next step. Vision budget is per-skill and capped; if you blow through it, the skill returns `failed` and the agent decides what to do.

The point isn't to *avoid vision*. The point is to **use the model where it matters**. Not on the cookie banner that's the same every time. Not on the infinite-scroll loop. Not on the date-picker widget. The model should be reasoning about the *task* — should I book the Hilton or the Marriott — not about the *interface*.

## Numbers, with caveats

We benchmark our 15 v1 skills against 20 curated sites. Each skill is exercised on ≥2 sites. The benchmark cron re-runs weekly and opens issues for stale selectors. The numbers below are launch targets, not yet measured; we'll publish the measured numbers (with honest variance bars) on day one.

| Skill | Target success | Target deterministic | p50 wall-time |
|---|---|---|---|
| verify-page-loaded | >98% | 100% | <500 ms |
| dismiss-cookie-banner | >95% | >90% | <800 ms |
| extract-table-pagination | >92% | >85% | <2 s |
| handle-infinite-scroll | >85% | >75% | <8 s |
| login-flow | >95% (with creds) | >85% | <3 s |
| (others) | >90% | >80% | <2 s |

The killer-demo claim: a vision-only agent monitors 5 ML conference paper sites in about 8 minutes (cookie banners + page-loaded reasoning + pagination on every site). The same agent, plus `browser-skills`, does it in 90 seconds. That's not because we made the model faster. It's because we **stopped letting the model do the boring stuff.**

## Things we will not do

OSS browser-agent projects are one bad headline away from a regulatory backlash. So we drew some hard lines, prominently:

- **No captcha solving.** Ever. We detect captchas and stop. The presence of a captcha is a signal — to the agent, and to the user — that something deserves attention. We will not be a tool you reach for to defeat anti-bot controls.

- **No anti-detection / fingerprint spoofing.** We don't ship stealth tooling. We don't link to it as "compatible companions." Our default Playwright launch is the boring, identifiable default, with a UA that says `browser-skills/<version>`.

- **No credential harvesting.** Login skills use the user's existing Playwright persistent context (already-signed-in browser session) or env-var creds the user provides. We don't read keychains, we don't store passwords, and traces of login flows redact the password field.

- **Respect robots.txt** by default; rate-limit to human-like cadence; identify ourselves. Users can override; the overrides are visible in the trace.

None of this is lawyer-grade protection. It's a credible posture for the OSS community. The point is to make `browser-skills` a tool whose existence is good for the ecosystem, not a wedge for regulators to swing against the whole category.

## What's in v1

Fifteen skills, six categories:

- **Consent / popups** (4 skills): cookie banners, newsletter popups, generic modals, exit-intent
- **State checks** (2): page-loaded, captcha detection
- **Forms** (3): multi-step forms, file upload/download, login flows
- **Data extraction** (2): table-with-pagination, infinite scroll
- **Navigation** (2): search-and-filter, pagination-next-page
- **Widgets** (2): date pickers, searchable dropdowns

Plus:

- The MCP server, installable into Claude Desktop, Cursor, Codex CLI, or Continue with one command
- A trace format for reproducible debugging (`browser-skills test <skill>` runs a skill against a local fixture; the resulting trace zip is shareable in bug reports)
- 20 curated benchmark sites, weekly cron-driven re-validation
- The full agentskills.io-conformant format — these skills drop into any of the 32 tools that already read SKILL.md

## What's next

After we ship v1:

- **Stagehand / TypeScript backend** (v1.5) — recipes are language-agnostic; we just need an adapter
- **Cross-backend benchmark** — same 15 skills, same 20 sites, three browser-driving backends (Claude 4.7, GPT-5.5, Gemini Computer Control). Same recipe, same outcome — that's the durable position no competitor currently owns
- **Community skill packs** — site-specific patterns that don't ship in the core but live in their own bundle
- **Headed-mode debugging UI** — see what the agent is doing in real time

If you build with browser agents, try the bundle:

```bash
pip install browser-skills
python -m playwright install chromium
browser-skills mcp install claude-desktop   # or cursor / codex / continue
```

Then ask your agent to do something boring. Watch how fast.

---

*[Author bio + project links here]*

*Discussion: [HN post]() · [Twitter thread]()*
