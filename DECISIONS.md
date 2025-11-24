# DECISIONS

> Architecture Decision Records (ADRs). Append-only. Newest first.
>
> Format per entry: ID, date, status, context, decision, consequences. Keep each one short.

---

## ADR-012 — No hosted demo

- **Date:** 2026-05-13
- **Status:** accepted
- **Context:** A hosted "try it now" demo would help star conversion but: (a) opens an attack surface (anyone can browse anywhere through our infra); (b) is expensive to run reliably under load; (c) any abuse becomes our reputation problem; (d) the demo's value vs. a local-install is small for the target audience (developers comfortable with pip install).
- **Decision:** No hosted demo. The README leads with a recorded video; users reproduce locally via `pip install browser-skills && browser-skills demo`. The recorded video is the marketing; the local reproduction is the proof.
- **Consequences:** Lower star-conversion ceiling than projects with hosted demos. Acceptable — target audience is developers, not casual evaluators.

## ADR-011 — Vision fallback: BYO-model via adapter interface

- **Date:** 2026-05-13
- **Status:** accepted
- **Context:** Vision fallback (when deterministic recipe fails) needs a multimodal model. Hard-coding Anthropic, OpenAI, or Gemini SDKs would create vendor lock-in and conflict with our agent-agnostic positioning ([ADR-006](#adr-006--cross-runtime-portability-is-a-defining-constraint)).
- **Decision:** Define a thin `VisionAdapter` interface (`describe(image, intent) -> action`). Ship reference adapters as optional extras: `pip install browser-skills[anthropic]`, `[openai]`, `[gemini]`. Users can implement their own. Default behavior with no adapter installed: deterministic-only (vision fallback is logged as "no adapter configured; skipping fallback").
- **Consequences:** Slightly more setup friction for the vision path. Users who want vision must pick a provider. Worth it — agent-agnostic position requires not picking favorites.

## ADR-010 — Per-skill license: MIT across the bundle

- **Date:** 2026-05-13
- **Status:** accepted
- **Context:** Skills are content (markdown) and may be community-contributed. Varied licenses across skills (some MIT, some Apache, some CC-BY) creates a packaging headache and complicates redistribution.
- **Decision:** All v1 skills are MIT. CONTRIBUTING.md requires PRs to acknowledge MIT licensing of contributed skill content. Contributors retain copyright; contributions are licensed in. No CLA required, but DCO sign-off on commits.
- **Consequences:** Some prospective contributors with strict CC-BY/AGPL preferences won't submit upstream. They can fork. Worth the simpler downstream story.

## ADR-009 — Skill versioning: agentskills.io `version` field, defer update tooling

- **Date:** 2026-05-13
- **Status:** accepted
- **Context:** Skills age — sites change, selectors break. Users need a way to know which version they have and whether updates exist.
- **Decision:** Each `SKILL.md` declares a `version:` field (semver) in YAML frontmatter — already permitted by the agentskills.io spec. Recipe-breaking changes bump major; selector tweaks bump patch. We don't ship an in-product updater in v1; users `pip install -U browser-skills` (refreshes bundled skills) or `git pull` if they cloned. Auto-update tooling deferred to a potential future companion (`skill-forge` from the broader project plan).
- **Consequences:** Users have to opt into updates. Acceptable — most Claude Code / Cursor users update their tools weekly. Sets up clean integration point if/when `skill-forge` materializes.

## ADR-008 — Headed mode in MCP: supported, opt-in, trace-flagged

- **Date:** 2026-05-13
- **Status:** accepted
- **Context:** Headed mode is genuinely useful for debugging — you see the agent operating. But it's a security concern on shared machines (a browser window appears, potentially showing private data to whoever's nearby). The master-prompt open question was whether to support it via MCP.
- **Decision:** Support headed mode via the MCP `start_browser` tool with explicit `headed: true` parameter. Default remains headless. When `headed: true`:
  - Log a `HEADED_MODE_ENABLED` line to the trace
  - Print a warning to stderr (visible to whoever launched the MCP server)
  - On servers with `BROWSER_SKILLS_FORBID_HEADED=1` env var set, the tool errors out (admin opt-out)
- **Consequences:** Devs get the debugging value; admins/orgs can lock it down. The trace flag means audits can spot misuse.

## ADR-007 — Benchmark moat: WebVoyager / WebArena reproducibility numbers

- **Date:** 2026-05-13
- **Status:** accepted
- **Context:** browser-use (89.1%), Skyvern (85.85%), Operator-CUA (87%) all publish WebVoyager numbers. Vendor CUA quality is also climbing (Claude 4.7 vision @ 3.75 MP, GPT-5.5 native CUA). The "skills make agents click" pitch alone won't survive — the wedge that lasts is **reproducibility + lower variance + lower token cost**, not raw success rate.
- **Decision:** Phase 2 / M5 includes a benchmark harness that runs the v1 skills bundle against WebVoyager-style tasks with three backends (Claude 4.7, GPT-5.5, Gemini Computer Control), publishing: (a) success rate vs. vendor-only baseline, (b) run-to-run variance, (c) tokens / latency / cost per task. Even a 2-3 point lift with lower variance is publishable.
- **Consequences:** Adds ~6 hours to Phase 2 M5 (was 8 hr, now ~14 hr — pull from Phase 3 polish if needed). Forces an honest posture (we'll publish numbers we don't yet have). Worth it; reproducibility-as-moat is the only durable differentiator if vendor CUA keeps improving.

## ADR-006 — Cross-runtime portability is a defining constraint

- **Date:** 2026-05-13
- **Status:** accepted
- **Context:** Adjacent prior art (browserbase/skills, vercel-labs/agent-browser, browser-act/skills, browser_use/skills) is all CLI- or framework-coupled. agentskills.io has 32-tool adoption *for the format*, but no project ships site-pattern content that works across runtimes.
- **Decision:** Every v1 skill must run via **at least two** delivery paths:
  1. **MCP server** (`browser-skills mcp`) — primary, runtime-neutral
  2. **Drop-in `.claude/skills/` directory** — markdown only, no installation
  And the recipe must be executable against **at least three** browser backends:
  1. Direct Playwright (Python) — reference impl
  2. browser-use adapter
  3. Stagehand (TS) adapter — v1.5, but recipes are written backend-agnostically from day 1
- **Consequences:** Recipes must avoid Python-specific selectors (e.g., no `page.locator("text=...").first()` syntax). Use the agentskills.io-conformant recipe DSL (selectors as strings, actions as named primitives). Adds adapter design work to Phase 1; pays off by claiming the "works with your stack" position no competitor currently owns.

## ADR-005 — Conform to agentskills.io spec; don't invent a format

- **Date:** 2026-05-13
- **Status:** accepted — **supersedes the "extend SKILL.md" framing in ADR-002**
- **Context:** When the master prompt was written, SKILL.md was an emerging mattpocock-style convention we planned to **extend** with browser recipes. The ecosystem-recon revealed: on **2025-12-18**, Anthropic ratified Agent Skills as an open standard at **agentskills.io** (Apache 2.0 + CC-BY-4.0); by March 2026, 32 tools read the same format (Claude Code, Codex, ChatGPT, Cursor, VS Code Copilot, Gemini CLI, Junie, Kiro, Goose, etc.). Inventing our own extension means losing all that distribution.
- **Decision:** v1 skills **conform strictly** to the agentskills.io spec — YAML frontmatter (`name`, `description`, optional `disable-model-invocation`, optional `allowed-tools`) + Markdown body + optional `scripts/`, `references/`, `assets/`. Our "recipe" is just a structured `## Recipe` section in the markdown body — fully spec-compliant, no custom frontmatter fields invented. The browser-specific structure (action verbs: `click`, `wait`, `extract`, etc.) is documented in [docs/skill-recipe-format.md](docs/skill-recipe-format.md) (Phase 1) as a *convention*, not a spec change.
- **Consequences:** Every existing agentskills.io-aware tool can read our skills as-is — free distribution. ADR-002's `flake_rate` and `recipe_version` frontmatter fields are reclassified as **convention only** (carried under a single spec-permitted `metadata:` map if at all), not as format extensions. Submit the bundle as a reference implementation to `agentskills/agentskills` and `VoltAgent/awesome-agent-skills` (which has a documented gap exactly here).

## ADR-004 — No captcha solving. Ever.

- **Date:** 2026-05-13
- **Status:** accepted
- **Context:** Captcha-solving libraries exist (2captcha, anti-captcha, ML solvers). Bundling one would make some demos look magical.
- **Decision:** Captcha-related skills are **detect-and-warn** only. We document presence of a captcha and stop. The user composes their own captcha service if they want one — we don't ship it, link to it, or accept PRs for it.
- **Consequences:** Some demo paths will dead-end on captchas (esp. cloudflare-protected sites). Acceptable tradeoff — the alternative is unbounded legal/ethical exposure and a class of users we don't want in the community.

## ADR-003 — Vision is fallback, not primary

- **Date:** 2026-05-13
- **Status:** accepted
- **Context:** Browser agents today (browser-use, Skyvern, Operator) are vision-first: every interaction routes through a multimodal model. This is slow (>1 s/step), expensive ($), and brittle (renders change). The wedge for browser-skills is precisely *avoiding* vision for repeatable patterns.
- **Decision:** Each recipe has two tiers: (1) deterministic selector-based primitive sequence — runs first, no model call; (2) vision fallback — invoked only when the deterministic path fails. Recipes that never need vision are the goal.
- **Consequences:** Skill authors must invest in robust selectors. Stale selectors will be a real maintenance burden (CI must catch). But the demo story — "8 minutes vision agent → 90 s skills agent" — depends on this discipline.

## ADR-002 — Skill format: SKILL.md frontmatter + structured Recipe section

- **Date:** 2026-05-13
- **Status:** **superseded by ADR-005** (same day)
- **Context:** Standard SKILL.md (mattpocock-style) is freeform markdown. Good for human guidance to an LLM, but not directly executable. Browser skills need executable steps.
- **Decision (original):** Extend SKILL.md with custom frontmatter fields (`applies_to`, `flake_rate`, `recipe_version`, `url_patterns`, `dom_markers`) and structured markdown sections.
- **Why superseded:** Same-session ecosystem recon revealed SKILL.md is now an Anthropic-ratified open standard at agentskills.io (Dec 18, 2025). Inventing custom frontmatter forfeits 32-tool runtime distribution. See ADR-005.

## ADR-001 — Python-first, Stagehand (TypeScript) adapter in v1.5

- **Date:** 2026-05-13
- **Status:** accepted
- **Context:** Two viable ecosystems: Python (Playwright + browser-use) and TypeScript (Playwright + Stagehand). Both have real audiences. Shipping both at launch ~doubles surface area.
- **Decision:** v1 ships Python only. Stagehand/TS adapter targeted for v1.5 (~month 2 post-launch). Skill recipes (the markdown) are language-agnostic — only the runner is Python.
- **Consequences:** TS audience misses launch. Mitigated by: (a) recipes work via MCP from any language; (b) v1.5 promise; (c) primary audience for skill bundles is Claude Code / Cursor users who interact via MCP regardless of underlying language.

---

## Open questions

All master-prompt section-10 questions are now resolved:

- ✅ Stagehand parity timing — ADR-001 (v1.5)
- ✅ Headed mode in MCP — ADR-008
- ✅ Skill versioning — ADR-009
- ✅ Per-skill license — ADR-010
- ✅ Vision-fallback vendor lock-in — ADR-011
- ✅ Hosted demo — ADR-012

New open items as they surface get appended here; resolve to ADRs.
