# Ecosystem Recon: Browser-Skills Competitive Landscape

**Date:** 2026-05-13
**Author:** market/ecosystem recon for `browser-skills` (Skills bundle + MCP server)
**Status:** Honest assessment — there is meaningful prior art; the wedge is narrower than it first appears but is still open if scoped correctly.

---

## TL;DR

Three things have changed the field since this project was scoped:

1. **Anthropic shipped Agent Skills as an open standard (Dec 18, 2025; agentskills.io).** By March 2026, 32 tools (Claude Code, Codex CLI, ChatGPT, Cursor, VS Code/Copilot, Gemini CLI, Junie, Kiro, Goose, etc.) read the same `SKILL.md` format. The SKILL.md format is no longer "mattpocock-style" prior art; it is a ratified industry spec under Apache 2.0 + CC-BY-4.0. **Good news for us — we don't need to invent a format.**
2. **At least three "browser skills" repos already exist** — `browserbase/skills` (~3.2k), `vercel-labs/agent-browser` (~32.9k, has a `skills/` directory), and `browser-act/skills` (~1.2k MIT). Plus `browser-use` itself now ships a `browser_use/skills` Python module. **None of them, however, ship the specific reusable patterns library we proposed** (cookie banners, infinite scroll, multi-step forms, table extraction, login flows) as agent-agnostic SKILL.md artifacts. They ship CLI-vendor-coupled skills.
3. **Vendor computer-use (Claude Opus 4.7, GPT-5.5 native CUA, Operator/ChatGPT-agent-mode) has gotten substantially better in 2026,** which compresses the "we'll teach the agent how to scroll" value prop. But it has gotten *no better* at site-specific patterns and *no better* at reproducibility. That's still the wedge.

The skills-folder wedge is **partially open** (confidence: medium-high) — but only if we position as **agent-agnostic, site-pattern-focused, vendor-neutral** skills, not as another framework-coupled skill collection.

---

## Competitive table

| Tool | Lang | License | Stars (May 2026) | Ships skill artifacts? | Our differentiation |
|---|---|---|---|---|---|
| **browser-use** | Python | MIT | ~91k | Yes (`browser_use/skills/`), but framework-coupled SkillService API, not portable SKILL.md | We target SKILL.md, work across any agent runtime |
| **Stagehand** (Browserbase) | TS (+ Go/Ruby/PHP via canonical layer) | MIT | ~10k | No — primitives (`act`/`extract`/`observe`/`agent`), not packaged recipes | Recipes vs primitives; vendor-neutral |
| **Skyvern** | Python | AGPL-3.0 | ~14k | No — workflow builder + SDK, not a skills bundle | Permissive license; agent-agnostic |
| **OpenAI Operator / ChatGPT agent mode** | closed | proprietary | n/a | No — sunset standalone Jul 2025, now `ChatGPT agent mode` w/ CUA | We're OSS, work with non-OpenAI agents, give reproducible patterns |
| **Anthropic computer-use API** | n/a | proprietary | n/a | Indirectly — Anthropic publishes Agent Skills spec, but no official browser-skills bundle | We provide the missing skill content for the spec they invented |
| **Playwright + LLM glue** (Playwright MCP, Playwright Agents, AgentQL) | TS/Python | Apache-2.0 / MIT | microsoft/playwright-mcp huge | Playwright Agents ships `planner`/`generator`/`healer` — testing-focused, not web-task patterns | Different domain (we target end-user workflows, not tests) |
| **`browserbase/skills`** | JS | MIT | ~3.2k | YES — but Browserbase-platform-coupled | Vendor-neutral; portable to local Playwright, browser-use, computer-use |
| **`vercel-labs/agent-browser`** | Rust CLI | MIT | ~32.9k | YES — `skills/` dir with workflow skills bundled w/ CLI | Decoupled from any single CLI |
| **`browser-act/skills`** | Python | MIT | ~1.2k | YES — but "scenarios" (Amazon ASIN, YT transcripts, Google News), not generic web patterns | Generic patterns (banners/scroll/forms/tables) vs vertical scrapers |
| **mattpocock/skills** | n/a | MIT | n/a (popular reference) | YES — but coding skills (diagnose, triage), no browser | Same SKILL.md form factor, different domain |
| **VoltAgent/awesome-agent-skills** | curated list | n/a | n/a | Aggregator — gap noted: no dedicated cookie-banner/infinite-scroll skills | Fills a documented gap in the curated list |
| **`browser-skills` (us)** | Python (MCP) + SKILL.md | TBD (MIT recommended) | 0 | YES (designed-in) | Agent-agnostic, pattern-library-first, MCP-deliverable |

---

## Per-competitor briefings

### 1. browser-use (`browser-use/browser-use`)
Python-first, vision-driven, ~91k stars in May 2026 — the de-facto market leader for OSS browser agents and the project most often cited alongside Stagehand and Skyvern. April 2026 changes: BYO LLM keys with V3 sessions, agent emits a re-runnable Python script (a "recipe" of sorts), secrets-in-traces hardening, and removal of `litellm` from core deps after the March 24 supply-chain incident. They have a `browser_use/skills/` module now, but it is a `SkillService`/`skill-id` API tied to their runtime — not portable SKILL.md artifacts. **Threat level: high if they pivot to publishing SKILL.md; today they don't.**

### 2. Stagehand (Browserbase)
TypeScript SDK with `act`/`extract`/`observe`/`agent` primitives; v3 went CDP-native (dropped the Playwright dependency, +44% on complex DOM); ~10k stars; MIT; canonical core with Go/Ruby/PHP/Node clients as of Jan 13, 2026; server-side caching of `act`/`extract`/`observe` results on `BROWSERBASE` env. They sell primitives, not recipes — there is a clear "you bring the patterns" gap. Their separate `browserbase/skills` repo (see below) is the recipe layer, and that's the one to watch most closely.

### 3. Skyvern
Vision+LLM, vertical-focused, AGPL-3.0, ~14k stars; SDK v1 in January 2026 with Python + TS clients and both embedded and cloud modes; hit 85.85% on WebVoyager (best on form-fill `WRITE` tasks). AGPL is a meaningful adoption friction — many companies cannot bundle AGPL into commercial agents — which structurally limits Skyvern as a skills *substrate* and creates oxygen for an MIT/Apache skills library.

### 4. OpenAI Operator → ChatGPT agent mode + GPT-5.5 CUA
Standalone Operator sunset in July 2025; the capability merged into ChatGPT "agent mode" with the Computer-Using Agent (CUA) model. GPT-5.5 (released April 23, 2026; API April 24) advances *native* computer use materially — OpenAI explicitly markets agentic-coding, computer-use, and tool-orchestration as headline 5.5 gains. April 2026 also brought "Codex Background Computer Use" (autonomous macOS app driving). Closed, proprietary, no skills artifacts. **Strategic implication: native CUA gets better at perception, but neither GPT-5.5 nor Claude 4.7 ships site-specific patterns out of the box.** That gap is where reusable skills live.

### 5. Anthropic computer-use API & Claude lineage
Claude Opus 4.7 released April 16, 2026 (vision up to 3.75 MP, new tokenizer, +13% on coding benchmarks, "3x more production tasks resolved"). Claude Sonnet 4.6 + Agent Teams shipped Feb 5, 2026 in Claude Code v2.1.32 — multiple agents on a shared codebase, 1M-token isolated contexts, mailbox messaging. Agent Skills launched as a *Claude* feature in October 2025 and was **open-standardized at agentskills.io on December 18, 2025** under Apache 2.0 / CC-BY-4.0. Anthropic does **not** publish an official browser skills bundle for the spec they created — they are betting on community to fill that surface. That is precisely the lane this project is aimed at.

### 6. Playwright + LLM glue
Microsoft's `playwright-mcp` (large MCP-server adoption), Playwright Test Agents (`planner`/`generator`/`healer`, Oct 2025), and AgentQL (`page.get_by_ai` natural-language selectors) form a *testing-and-automation-engineer* stack, not an end-user-task stack. Important context, low direct competition: their skill artifacts (Playwright Test Agents) are tightly coupled to the test runner, not portable web-task recipes.

### 7. Existing "browser skills" repos — the critical finding
- **`browserbase/skills`** (~3.2k, JS, MIT, official Browserbase repo): 11 skills, but they are *capability layers* (`browser`, `browserbase-cli`, `functions`, `site-debugger`, `browser-trace`, `safe-browser`, `bb-usage`, `cookie-sync`, `fetch`, `search`, `ui-test`) — **not** site-pattern recipes. Heavy Browserbase-platform coupling (`bb` CLI, residential proxies, Browserbase Functions). Doesn't cover cookie banners, infinite scroll, multi-step forms, or table extraction as named skills.
- **`vercel-labs/agent-browser`** (~32.9k, Rust CLI, MIT): bundled `skills/` served via `agent-browser skills get <name>` and installable into Claude Code / Cursor via `npx skills add`. Skills are *workflow instructions* coupled to the `agent-browser` CLI. Large reach (32.9k stars), serious threat as a distribution channel — but the skills don't decouple from their CLI.
- **`browser-act/skills`** (~1.2k, Python, MIT): scenario skills — Amazon ASIN lookup, Best-Selling Products, YouTube transcripts, Google Maps/News, social monitoring, lead gen. Vertical scrapers, not generic web-interaction patterns.
- **`browser-use/browser_use/skills`**: in-tree Python `SkillService`/`skill-id` API; not SKILL.md; not portable.
- **`SawyerHood/dev-browser`**: a single Claude Skill that lets the agent run sandboxed JS in a browser — a primitive, not a pattern library.
- **`VoltAgent/awesome-agent-skills`** (curated list, "1000+ skills"): explicit gap — no dedicated cookie-banner or infinite-scroll skills are highlighted; browser coverage is "Playwright" / "Firecrawl flows" / "form handling" inside larger bundles.

### 8. mattpocock/skills and SKILL.md prior art
The format we were going to "extend" became a ratified open standard five months ago. Matt Pocock's repo is the recognizable *exemplar* for engineering-domain skills (diagnose, grill-with-docs, triage, improve-codebase-architecture), with the canonical bucket layout (`engineering/`, `productivity/`, `misc/`, `personal/`, `in-progress/`, `deprecated/`). The wider standard is now agentskills.io: YAML frontmatter (`name`, `description`, optional `disable-model-invocation`, `allowed-tools`) + Markdown body + optional `scripts/`, `references/`, `assets/`. **Implication: do not invent a format. Conform to agentskills.io and inherit the 32-tool runtime distribution for free.**

### 9. 2025→2026 strategic shifts
- **Agent Skills became a cross-vendor standard in 48 hours (Dec 2025).** SKILL.md is the new MCP-tier interop primitive.
- **CUA quality jumped** (Claude 4.7 vision @ 3.75 MP, GPT-5.5 native CUA, Codex Background Computer Use) → less need to *teach the agent how to click*, more need to *teach the agent what the site expects*.
- **Agent Teams (Claude 4.6, Feb 2026)** make multi-agent web workflows viable; site-pattern recipes become more valuable per agent because each teammate can specialize.
- **Browserbase consolidated** — Stagehand canonical (Jan 13), server-side cache, multi-language clients; they own the commercial primitives layer and now have an official skills repo. The "Browserbase ecosystem" is the heaviest gravity well in this space.

---

## Is the skills-folder wedge open?

**Verdict: PARTIALLY OPEN — confidence MEDIUM-HIGH.**

What's already taken:
- The format (agentskills.io spec, ratified, 32-tool adoption). Do not fight it; conform.
- Vendor-coupled skill collections (`browserbase/skills`, `vercel-labs/agent-browser`, `browser-act/skills`).
- Capability-layer skills (driving a browser, debugging traces, cookie sync to a managed platform).

What's *not* taken — the actual wedge:
- **Agent-agnostic, runtime-neutral, site-pattern recipes** in SKILL.md form: cookie-banner dismissal (GDPR/CCPA/Chinese-PIPL variants), infinite-scroll harvesting with dedup and termination heuristics, multi-step form pacing (step indicator detection, validation-error recovery), table extraction (virtualized tables, pagination/server-side sorting), login flows (SSO/MFA/captcha branching).
- **MCP-server-delivered** skills (not a CLI you must install). Most existing libs are CLI-coupled (`bb`, `agent-browser`).
- **Cross-runtime portability**: same SKILL.md drives Claude computer-use, GPT-5.5 CUA, Gemini Computer Control, Playwright-MCP, browser-use, Stagehand.

The wedge is "the missing content layer for an existing standard," not "a new format." That is a real, defendable position — but it is a **months, not years** window before either Browserbase expands `browserbase/skills` into generic patterns, or Anthropic ships official browser skills alongside agentskills.io.

---

## Top 3 risks

1. **Browserbase extends `browserbase/skills` from capabilities to patterns.** They already have 3.2k stars, official-vendor status, and the Stagehand primitives below. If they add `cookie-banner`, `infinite-scroll`, `multi-step-form`, `table-extract` skills, our content advantage evaporates. *Mitigation:* ship fast (next 60-90 days), make skills explicitly Browserbase-compatible *and* runtime-neutral so we ride their distribution.
2. **Vendor CUA closes the gap on common patterns.** Claude 4.7 vision @ 3.75 MP and GPT-5.5 native CUA may already handle cookie banners and infinite scroll well enough that explicit skills feel redundant. *Mitigation:* benchmark side-by-side (with/without skill) and publish numbers — reproducibility, token cost, and reliability variance are our differentiation even when raw success rates are similar.
3. **`vercel-labs/agent-browser` (32.9k stars) becomes the de-facto skills distribution channel.** It already installs into Claude Code/Cursor via `npx skills add`. If they publish a generic-patterns expansion, their distribution dwarfs ours. *Mitigation:* publish to `agent-browser`'s skill registry as an upstream contribution rather than competing — make `browser-skills` the *content provider* across registries.

---

## Top 3 opportunities

1. **Become the reference browser-skills bundle for agentskills.io.** Anthropic open-sourced the spec but did not ship official browser skills. Submit our bundle as a reference implementation; pursue inclusion in the `agentskills/agentskills` repo and `VoltAgent/awesome-agent-skills` (which has a documented gap exactly here).
2. **Integration partnerships across runtimes.** Wire compatibility shims for: Playwright-MCP (microsoft/playwright-mcp, dominant MCP), browser-use (~91k stars), Stagehand (`act`/`extract`/`observe`), and Claude Agent Teams (Feb 2026 — each teammate consumes a different skill). Pitch each as "drop in this skills folder and your existing stack gets +X on WebVoyager-style tasks."
3. **Benchmark + reproducibility moat.** Run our skills bundle against WebVoyager / WebArena / OSWorld with Claude 4.7, GPT-5.5, and Gemini Computer Control, then publish results. browser-use is at 89.1%, Skyvern 85.85%, Operator-CUA 87% on WebVoyager — a 2-3 point lift purely from skills, *with lower token cost and lower variance*, is a publishable, citeable wedge. Pair with a public reproducibility harness in `benchmarks/`.

---

## Recommended positioning (one sentence)

> *"`browser-skills` is the missing content layer for agentskills.io: agent-agnostic, MCP-deliverable, SKILL.md-conformant recipes for the boring web patterns every browser agent re-learns from scratch — cookie banners, infinite scroll, multi-step forms, table extraction, login flows — benchmarked across Claude 4.7, GPT-5.5, and Gemini Computer Control."*

---

## Sources

- [browser-use GitHub](https://github.com/browser-use/browser-use) and [changelog](https://browser-use.com/changelog)
- [browser-use skills module](https://github.com/browser-use/browser-use/tree/main/browser_use/skills)
- [Stagehand GitHub](https://github.com/browserbase/stagehand); [Stagehand docs](https://docs.browserbase.com/introduction/stagehand); [Stagehand v3 / canonical announcement](https://www.browserbase.com/blog/browser-automation-all-languages-with-stagehand)
- [Skyvern GitHub](https://github.com/Skyvern-AI/skyvern); [Browser Tools framework wars (DEV)](https://dev.to/stevengonsalvez/browser-tools-for-ai-agents-part-2-the-framework-wars-browser-use-stagehand-skyvern-4gn)
- [browserbase/skills](https://github.com/browserbase/skills)
- [vercel-labs/agent-browser](https://github.com/vercel-labs/agent-browser); [agent-browser skills page](https://agent-browser.dev/skills)
- [browser-act/skills](https://github.com/browser-act/skills)
- [VoltAgent/awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills)
- [SawyerHood/dev-browser](https://github.com/SawyerHood/dev-browser)
- [mattpocock/skills](https://github.com/mattpocock/skills)
- [Anthropic Agent Skills announcement](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills); [Agent Skills open standard (SiliconANGLE)](https://siliconangle.com/2025/12/18/anthropic-makes-agent-skills-open-standard/); [agentskills.io specification](https://agentskills.io/specification); [agentskills GitHub](https://github.com/agentskills/agentskills)
- [Claude Opus 4.7 announcement](https://www.anthropic.com/news/claude-opus-4-7)
- [Claude Agent Teams docs](https://code.claude.com/docs/en/agent-teams); [Claude Opus 4.6 + Agent Teams (NxCode)](https://www.nxcode.io/resources/news/claude-agent-teams-parallel-ai-development-guide-2026)
- [OpenAI GPT-5.5 announcement](https://openai.com/index/introducing-gpt-5-5/); [CNBC GPT-5.5](https://www.cnbc.com/2026/04/23/openai-announces-latest-artificial-intelligence-model.html); [TechCrunch GPT-5.5](https://techcrunch.com/2026/04/23/openai-chatgpt-gpt-5-5-ai-model-superapp/)
- [OpenAI Operator / CUA](https://openai.com/index/computer-using-agent/); [ChatGPT agent](https://openai.com/index/introducing-chatgpt-agent/); [Codex Background Computer Use (Remio)](https://www.remio.ai/post/openai-codex-can-now-control-your-desktop-what-it-means-for-the-ai-coding-agent-race)
- [microsoft/playwright-mcp](https://github.com/microsoft/playwright-mcp); [Playwright Test Agents](https://playwright.dev/docs/test-agents)
- [Best 30+ Open Source Web Agents 2026 (AIMultiple)](https://aimultiple.com/open-source-web-agents); [11 Best AI Browser Agents 2026 (Firecrawl)](https://www.firecrawl.dev/blog/best-browser-agents)
- [Agent Skills Open Standard Interoperability Guide (Paperclipped)](https://www.paperclipped.de/en/blog/agent-skills-open-standard-interoperability/)
