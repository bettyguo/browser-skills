# STATUS

> Project tracker. Update at the end of every session.

## Current state (2026-05-13, post-v0.3.0 cut)

- **Phase:** Released as v0.3.0. Roadmap to v0.4 in [docs/roadmap-v0.3.md](docs/roadmap-v0.3.md) (re-prioritized post-cut; see "actual ship status" notes).
- **Hours spent:** ~58 of 105 budget
- **Blocker:** None
- **Tests:** **162 passing** (pytest, ~12-18s incl. real-Chromium integration; audit-3 added 8 tests)
- **Bundle:** 15 / 15 v1 skills + 2 pilots opted into runtime-evaluated success criteria
- **Release artifacts:** [CHANGELOG.md](CHANGELOG.md) §0.2.0 + §0.3.0 + [docs/roadmap-v0.2.md](docs/roadmap-v0.2.md) + [docs/roadmap-v0.3.md](docs/roadmap-v0.3.md)
- **v0.3 must-ship retrospective** (per [docs/roadmap-v0.3.md](docs/roadmap-v0.3.md) §(e); actual ship status in CHANGELOG):
  - ✅ #1 **C3+C7** — success-criteria DSL parser, evaluator, runner wiring + 2 pilot skills
  - ✅ #2 **D1** — SkillResult.vars_in / extracted split
  - ⏸ #3 **F1** — reference vision adapters (deferred to v0.4)
  - ⏸ #4 **S1 audit-1** — AST-based JS-injection lint (deferred to v0.4)
- **Post-cut audit-3 fixes** (held for the v0.4 cut; see commits 2fb6796..48592fd):
  - C4 stale runner comments; C2+T3 KNOWN_PREDICATES single source of truth;
    T1 criteria-fire-post-vision lock-in; T2 D1 in-place-mutation contract;
    S2 evaluator-error warning surfacing; S3 shared JS predicate constants.
- **Next session:** F1 (reference vision adapters — Anthropic / OpenAI / Gemini), the largest remaining v0.4 must-ship.

## Phase progress (original master plan)

| Phase | Budget | Spent | Status |
|---|---|---|---|
| 0 Think | 7 hr | ~3 hr | done |
| 1 Design | 12 hr | ~3 hr | done |
| 2 Code | 55 hr | ~13 hr | ✅ M1-M5 done |
| 3 Polish | 20 hr | ~3 hr | docs done; hero video + bench-publish page pending |
| 4 Launch | 11 hr | ~3 hr | content drafted in [docs/launch/](docs/launch/) |
| **post-launch audit + v0.2 cut** | — | ~13 hr | ✅ done (this session) |

## Top risks (track weekly)

1. **Browserbase expands `browserbase/skills` (~3.2k) into generic patterns.** Mitigation: ship in 60-90 days; ensure Browserbase-compatible primitives so we ride their distribution.
2. **vercel-labs/agent-browser (~32.9k) becomes de-facto skill distribution channel.** Mitigation: publish to their registry as upstream contribution; don't compete on distribution, compete on content.
3. **Vendor CUA (Claude 4.7, GPT-5.5 native, Gemini Computer Control) closes the common-pattern gap.** Mitigation: benchmark reproducibility + variance + cost per task as defining metrics, not just success rate (ADR-007).

## Milestone progress (Phase 2)

- [x] M1 — Primitives + runner skeleton (10 hr) ✅
- [x] M2 — First 5 skills + benchmark scaffolding (14 hr) ✅ (6 skills shipped)
- [x] M3 — Matcher + MCP integration (10 hr) ✅ (8 MCP tools; `mcp install` for 4 clients)
- [x] M4 — Remaining 10 skills (13 hr) ✅ (9 shipped; total = 15 v1 skills)
- [x] M5 — Trace + headed mode + UX polish (8 hr) ✅ (`browser-skills test <skill>` with `--headed`; trace zip already shipped in M1)

## Definition of Done checklist

- [x] All 15 skills working — bundle complete; success rates pending the first full benchmark cron run
- [x] MCP server installable from one command — `browser-skills mcp install {claude-desktop|cursor|codex|continue|print}`
- [x] Trace export reliable for every skill — `trace.export_zip()` ships in [src/browser_skills/trace.py](src/browser_skills/trace.py)
- [x] Ethics doc prominent + honest — [docs/ethics.md](docs/ethics.md); hard lines in [README.md](README.md) and [CONTRIBUTING.md](CONTRIBUTING.md)
- [ ] Hero video + benchmark page live — both deferred to launch-day session
- [x] CI green; weekly benchmark cron — [.github/workflows/ci.yml](.github/workflows/ci.yml) + [.github/workflows/benchmark.yml](.github/workflows/benchmark.yml)
- [ ] Pre-launch outreach done — drafts staged in [docs/launch/posts.md](docs/launch/posts.md), DMs not sent

## Session log

### Session 1 — 2026-05-13 (Phase 0 bootstrap)

- Created repo skeleton: [src/browser_skills/](src/browser_skills/), [skills/](skills/), [benchmarks/](benchmarks/), [docs/](docs/), [tests/](tests/)
- Wrote [STATUS.md](STATUS.md), [DECISIONS.md](DECISIONS.md), [LICENSE](LICENSE), [pyproject.toml](pyproject.toml), [README.md](README.md) placeholder
- Wrote Phase 0 design artifacts:
  - [docs/skills-design.md](docs/skills-design.md) — 30 candidates cut to 15 launch skills
  - [benchmarks/sites.yaml](benchmarks/sites.yaml) — 20 benchmark sites
  - [docs/killer-demo.md](docs/killer-demo.md) — locked demo spec
  - [docs/ecosystem-recon.md](docs/ecosystem-recon.md) — competitive landscape (via subagent)
- ADRs logged: 001 (Python-first, Stagehand TS in v1.5), 002 (**superseded same-day**), 003 (vision is fallback), 004 (no captcha solving), **005 (conform to agentskills.io, don't extend)**, **006 (cross-runtime portability is defining)**, **007 (benchmark moat: WebVoyager numbers across 3 backends)**

**Material strategic shifts (from ecosystem recon — read [docs/ecosystem-recon.md](docs/ecosystem-recon.md) before next session):**

1. **SKILL.md is now ratified** (agentskills.io, Anthropic, Dec 18 2025). 32 tools adopt it. We **conform**, don't extend. ADR-002 superseded by ADR-005.
2. **Three browser-skills repos already exist** — but none ships agent-agnostic site-pattern recipes:
   - [browserbase/skills](https://github.com/browserbase/skills) (~3.2k) — capability layers, Browserbase-coupled
   - [vercel-labs/agent-browser](https://github.com/vercel-labs/agent-browser) (~32.9k) — workflow skills coupled to Rust CLI
   - [browser-act/skills](https://github.com/browser-act/skills) (~1.2k) — vertical scrapers (Amazon ASIN, YT transcripts)
3. **60-90 day window** before Browserbase or vercel-labs may expand into generic patterns.
4. **Repositioning:** "Extension to SKILL.md" → "**Reference browser-pattern bundle for agentskills.io.**" Update README at Phase 3.

**Open questions for next session:** none blocking. Begin Phase 1 with revised positioning baked in.

### Session 1 continuation — 2026-05-13 (Phase 1 design + Phase 2 M1 start)

- All section-10 open questions resolved via ADRs 008-012:
  - 008: headed mode in MCP — supported, opt-in, trace-flagged
  - 009: skill versioning via agentskills.io `version` field; updates via `pip install -U`
  - 010: all skills MIT
  - 011: vision fallback is BYO-model via `VisionAdapter` interface
  - 012: no hosted demo
- Phase 1 design docs landed:
  - [docs/skill-recipe-format.md](docs/skill-recipe-format.md) — agentskills.io-conformant convention; action-verb DSL
  - [docs/matcher-design.md](docs/matcher-design.md) — heuristic scorer, no model call
  - [docs/runner-design.md](docs/runner-design.md) — deterministic + vision-fallback gate, trace recording
  - [docs/mcp-design.md](docs/mcp-design.md) — full MCP surface: session, navigate, list/invoke skill, screenshot, trace export
- Two reference skills authored to validate the format:
  - [skills/dismiss-cookie-banner/SKILL.md](skills/dismiss-cookie-banner/SKILL.md)
  - [skills/verify-page-loaded/SKILL.md](skills/verify-page-loaded/SKILL.md)
- Phase 2 M1 skeleton coded:
  - [src/browser_skills/skill.py](src/browser_skills/skill.py) — frontmatter + recipe parser (bracket- and quote-aware DSL)
  - [src/browser_skills/primitives/](src/browser_skills/primitives/) — wait, click/try_each, extract, scroll, assertions, vision_fallback
  - [src/browser_skills/runner.py](src/browser_skills/runner.py) — recipe execution with vision-fallback gate
  - [src/browser_skills/matcher.py](src/browser_skills/matcher.py) — heuristic scoring
  - [src/browser_skills/trace.py](src/browser_skills/trace.py) — trace recording + zip export
  - [src/browser_skills/cli.py](src/browser_skills/cli.py) — `browser-skills list / info / version`
  - [src/browser_skills/adapters/playwright_raw.py](src/browser_skills/adapters/playwright_raw.py) — Playwright adapter stub (M2 fills in)
  - [src/browser_skills/server.py](src/browser_skills/server.py) — MCP server stub (M3 implements)
- Tests: **29 passing** across parser, primitives, runner, matcher, trace. `tests/conftest.py` provides a `FakePage` so primitives are unit-testable without Chromium.

**M1 remaining:** Playwright integration test (run runner against a real Chromium against a synthetic local HTML page). Lands first in M2 ("First 5 skills + benchmark scaffolding") alongside the next 3 skills.

**Next session — Phase 2 M2:** 3 more reference skills (handle-modal-dialog, extract-table-pagination, detect-captcha), a Playwright-backed integration test harness, `benchmarks/run.py` skeleton.

### Session 1 continuation — 2026-05-13 (M2 + M3 land)

- 4 new SKILL.md files (bringing the v1 bundle to 6):
  - [skills/extract-table-pagination/](skills/extract-table-pagination/) — killer-demo skill
  - [skills/handle-modal-dialog/](skills/handle-modal-dialog/) — generic blocking-dialog catch-all
  - [skills/detect-captcha/](skills/detect-captcha/) — detect-only, `max_vision_calls: 0` (ADR-004)
  - [skills/handle-infinite-scroll/](skills/handle-infinite-scroll/) — composes with extract for feeds
- [benchmarks/run.py](benchmarks/run.py) — quick mode (matcher recall) + full mode (real Chromium). Quick mode shows 100% matcher recall on the 20 benchmark sites.
- [src/browser_skills/server.py](src/browser_skills/server.py) — full MCP server on `fastmcp`: 8 tools (`start_browser`, `navigate`, `close_browser`, `list_skills`, `list_applicable_skills`, `invoke_skill`, `screenshot`, `page_state`). Session storage in-memory, max 10 concurrent.
- [src/browser_skills/cli.py](src/browser_skills/cli.py) — `browser-skills mcp serve` and `browser-skills mcp install {claude-desktop|cursor|codex|continue|print}` with auto-detected per-OS config paths.
- [tests/test_mcp_server.py](tests/test_mcp_server.py) — fastmcp in-process Client tests: tool registration, list_skills, error shapes for missing session and missing skill.
- [tests/test_bundle_completeness.py](tests/test_bundle_completeness.py) — bundle invariants: v1 skills present, semver versions, non-empty recipes, exercised_on ≥2, no vision in recipe happy path, detect-captcha has `max_vision_calls=0`.
- [CONTRIBUTING.md](CONTRIBUTING.md) — hard lines, MIT + DCO sign-off, dev setup, skill authoring checklist.

**M3 remaining:** Real-Playwright integration test (drive a synthetic localhost HTML page through dismiss-cookie-banner end-to-end). Will land alongside the first real-site benchmark snapshot.

**M4 plan:** 9 more skills to reach 15 — `dismiss-newsletter-popup`, `fill-multi-step-form`, `upload-download-file`, `search-and-filter`, `pagination-next-page`, `date-picker-widget`, `searchable-dropdown`, `login-flow`, `exit-tracking-popup`. ~1 hr per skill = ~9 hr (under the 13 hr M4 budget).

### Session 1 continuation — 2026-05-13 (M4 + M5 + Phase 3 launch prep)

- M4: shipped the remaining 9 SKILL.md files. v1 bundle complete at 15. Bundle invariants enforced via `tests/test_bundle_completeness.py`.
- Added `src/browser_skills/primitives/form.py` — fill, select_option, press_key, screenshot.
- M5: `browser-skills test <skill>` command — runs against `tests/fixtures/<skill>/page.html` via real Chromium, with `--headed` flag for visual debugging.
- M5: 3 reference fixture HTML pages for dismiss-cookie-banner, extract-table-pagination, verify-page-loaded.
- Real-Playwright integration tests (2) pass against a localhost synthetic page — full pipeline: navigate → matcher → invoke_skill → assert DOM changed.
- Phase 3 docs:
  - [README.md](README.md) — rewritten around the "missing content layer for agentskills.io" positioning. Skill catalog (table of all 15). MCP tool surface. Comparison to existing repos.
  - [docs/quickstart.md](docs/quickstart.md) — 5-minute install + sanity check + script reuse.
  - [docs/authoring.md](docs/authoring.md) — 20-minute walkthrough of authoring `dismiss-survey-popup` from scratch.
  - [docs/benchmarks.md](docs/benchmarks.md) — measurement methodology, target numbers per skill, anti-pattern check.
- Total tests: **41 passing** (~7s incl. real-Chromium integration).

**Next session — Phase 4 launch prep:**

1. **Hero video** (Phase 3 §6.2) — record killer-demo against the 5 conference URLs.
2. **Benchmark publishing** (§6.4) — GitHub Pages site rendering `benchmarks/results.json` weekly.
3. **Community outreach** (§6.5) — DMs to browser-use / Browserbase / Stagehand teams; coordinate with Anthropic DevRel for agentskills.io cross-promotion.
4. **Show HN / r/MachineLearning / Twitter** posts drafted but not posted (§7.1, §7.2).

### Session 1 continuation — 2026-05-13 (real-site validation + bug fixes + tooling)

- **`browser-skills new <name>`** scaffold command — writes a starter SKILL.md and tests/fixtures/<name>/page.html, with kebab-case validation.
- **[benchmarks/publish.py](benchmarks/publish.py)** — renders `results.json` to a single-page HTML report (aggregate banner, per-site table with skill-status pills, per-skill aggregate with p50/p99). For GitHub Pages.
- **[benchmarks/file_issues.py](benchmarks/file_issues.py)** — diffs the latest run against `benchmarks/_runs/results-*.json` history, opens `stale-selector` issues for newly-failing pairs via the GitHub REST API. `--dry-run` for local testing.
- **[benchmarks/run.py](benchmarks/run.py)** gained `--limit N` and `--site <id>` flags to spot-check `--mode=full` cheaply.

**Real benchmark caught two bugs** (the inner loop the master prompt called for):

1. `dismiss-cookie-banner` against `hacker-news-list` took **23.4 s** — `try_each` was attempting each of its 15 selectors with the full 1500 ms timeout on a page with no banner. Fixed by adding a `_selector_present` probe before each action attempt in [src/browser_skills/primitives/click.py](src/browser_skills/primitives/click.py). New timing: **0.76 s** (30× faster).
2. `detect-captcha` against `wikipedia-list` returned `failed` because `extract_text` raised on no-match — but the documented happy path is "no captcha present." Added `optional=true` to `extract_text` in [src/browser_skills/primitives/extract.py](src/browser_skills/primitives/extract.py); updated [skills/detect-captcha/SKILL.md](skills/detect-captcha/SKILL.md). Now: `success` with `$captcha_marker = None`. 14 ms.

Three new regression tests lock in both fixes. **44 tests passing in 6.74s.**

**[CLAUDE.md](CLAUDE.md)** written — orientation for future Claude Code sessions on this repo. One read = ready to be useful within a turn.

### Session 1 v0.3 — 2026-05-13 (C3+C7 success-criteria DSL)

After audit-2's Phase 2 fixes (D2, Doc1-3, T1, T5, T2, P3) and the
v0.3 roadmap, this batch shipped the largest must-ship item:

**C3+C7 — Success-criteria DSL** (3 commits, opt-in migration):

  - Commit `d70a23c` (step 1, parser): new [criteria.py](src/browser_skills/criteria.py)
    with `parse_success_criteria()`, `Predicate`, `Criterion`, and the
    `KNOWN_PREDICATES` set (8 verbs). Skill class gains
    `success_criteria: list[Criterion]` populated at parse time. No
    behavior change yet. 11 parser tests + bundle-wide invariants.

  - Commit `5f409e7` (step 2, evaluator): `evaluate_criterion()` with
    tri-valued semantics (True / False / None=soft-pass). OR-semantics
    at the criterion level. Never raises — exceptions become None.
    Still no runner wiring. 16 evaluator tests.

  - Commit `c504ac4` (step 3, runner): runner consults parsed criteria
    after the recipe (and after vision fallback). Skill opts in via
    `metadata.evaluate_success_criteria: true`; default off retains
    v0.1/0.2 behavior. Decidable False → status=failed; unknown
    predicate → soft-pass + warning. Pilot opt-ins:
    [verify-page-loaded](skills/verify-page-loaded/SKILL.md) (v0.1.0
    → v0.2.0) and [extract-table-pagination](skills/extract-table-pagination/SKILL.md)
    (v0.1.0 → v0.2.0). 7 runner-wiring tests.

**Plus a pop-up fix**:

  - Commit `549af01`: `_free_port` in integration tests retries until
    it gets a port Chromium will accept (avoids 5060/SIP, 6000/X11,
    IRC ports, etc.). Surfaced as a real flake during the C3+C7 test
    run.

148 tests passing in ~12s. Three more v0.3 must-ship items
outstanding: D1 (extracted/vars split), F1 (vision adapters), S1
audit-1 (AST-based JS lint).

### Session 1 wrap-up — 2026-05-13 (audit cycle + v0.2.0 release cut)

Three-phase audit ([Phase 1 findings inline in conversation]; Phase 2
delivered as 13 commits; Phase 3 is [docs/roadmap-v0.2.md](docs/roadmap-v0.2.md)),
then v0.2 must-ship + strong-ship items, then release.

Audit fixes committed (one per logical fix, each with regression test):
- **P0s:** C1 (workflow `--mode=full`), C2 (PlaywrightPage adds
  screenshot/query_selector), C4 (workflow archives results.json), S5
  (trace redacts credential args on `sensitive: true` skills)
- **P1s:** C5 (workflow deploys to GH Pages), C6 (assert raises on
  unknown predicate), S2 (broaden FORBID_HEADED truthy), D2
  (is_initial_load tracks navigates), D4 (quick-mode honesty note),
  P3 (lazy chromium check), T1 partial (form-primitive tests),
  Doc1 (success-criteria doc), Doc2/3/4 (stale phase comments)

v0.2 roadmap items shipped same session:
- **S1** — `scroll` parameterizes `delta` via evaluate args (no f-string JS)
- **D3** — skill cache auto-invalidates on mtime change; `reload_skills` MCP tool
- **F9** — DCO sign-off enforcement GitHub Action
- **Doc5** — `mcp install --transport=http` removed; HTTP auth deferred to v0.3
- **F8** — `browser-skills doctor` diagnostic command
- **T7** — per-site matcher correctness tests + 3 matcher fixes they surfaced
- **Q1-Q4, Q6-Q8** — code-quality cleanup batch (no behavior change)
- Version bump to 0.2.0; CHANGELOG.md authored

Release artifact: **v0.2.0** — first user-facing version. 104 tests
passing in ~13s. CHANGELOG flags every downstream-visible behavior
change. Test invariants now enforce version/CHANGELOG parity.

Phase 3 roadmap items deferred to v0.3 (per priority ordering): C3+C7
(success-criteria DSL), D1 (split extracted/vars), F1 (reference
vision adapters), F4 (Stagehand TS adapter), F3 (cross-backend
benchmark).
