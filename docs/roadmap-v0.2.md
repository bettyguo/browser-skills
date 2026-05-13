# Roadmap — v0.2

> Authored at the close of the Phase 2 audit + fix pass.
> Living doc; revise as items land. Successor to [STATUS.md](../STATUS.md).

---

## (a) Carry-over from Phase 2 — deferred fixes

Items the audit surfaced and Phase 2 deferred because they required
architectural change, an API break, or exceeded the per-commit
~50 LOC ceiling. Each has a proposed remediation and an effort
estimate (S = ≤1 day, M = 1-3 days, L = >3 days).

| ID | Severity | Item | Remediation | Effort | Risk |
|---|---|---|---|---|---|
| **C3 + C7** | P1 | `## Success criteria` is documentation-only; vision fallback returns success on any executed action. Doc1 patched the doc; impl is still gap. | Small predicate language: `no_visible_element selector=...`, `no_element selector=...`, `dom_changed since=stepN`, `url_changed since=stepN`, `cookie_set named=...`, plus OR/AND. Parser + AST + per-predicate evaluator. Runner re-evaluates after recipe AND after each vision-fallback action. Soft-mode flag for migration. | **M** | recipe-format change; needs migration plan for the 15 shipped skills |
| **S1** | P1 | Several primitives f-string-interpolate args into JS source (`scroll.py:30,36`, `extract.py:62-81`). Safe today; community-contributed primitives could exploit. | Ban f-string JS; pass via `evaluate(js, *args)`. Audit all primitives. Add a lint check that grep-flags `f"...evaluate"` patterns in `src/browser_skills/primitives/`. | **S** | low; mechanical |
| **S3** | P1 | `mcp install` refuses configs with JSON5-style comments (Cursor's `mcp.json` historically had them). | Optional `[json5]` extra; fall back to `json` parse, retry with `json5` on JSONDecodeError. Document that comments aren't preserved on round-trip. | **S** | low; new optional dep |
| **D1** | P1 | `SkillResult.extracted` conflates caller-passed vars with skill-extracted vars. | Split into two maps: `vars_in` (read-only inputs) and `extracted` (only `extract_*`-bound). Touch every extract primitive's signature; bump trace manifest schema. | **M** | API break (minor bump) |
| **D3** | P2 | `server._skills_cache` never invalidates; editing a SKILL.md needs server restart. | New MCP tool `reload_skills` (force-reload). Optionally: mtime check at the top of `_load_skills_cached` (1-line). | **S** | low |
| **T2** | P1 | `scroll`, `scroll_until` primitives have zero tests; `handle-infinite-scroll` skill is end-to-end-untested. | FakePage dispatcher already handles scrollHeight/scrollBy in stubs; extend with `selector_present` branch. Add 6-8 tests. | **S** | low |
| **T3** | P2 | Matcher tests assert presence, not ordering — the hand-tuned scoring is exactly what drifts. | For each pair of skills where ordering is critical (cookie-banner vs newsletter-popup, captcha vs anything), add a synthetic PageState and assert top-1 / top-2 identity. | **S** | low |
| **T5** | P1 | CLI is entirely untested. `mcp install` writes the user's filesystem with no tested invariants. | typer `CliRunner` harness. Assert JSON output of `info --json`, JSON shape written by `mcp install --print`, idempotency of `new <name>`. | **M** | medium; typer test setup |
| **T6** | P2 | `benchmarks/file_issues.py` and `benchmarks/publish.py` have no tests. | Unit test `_diff_regressions` (pure function), `_format_per_skill` (pure function over a fake report dict). | **S** | low |
| **T7** | P2 | No test asserts the matcher picks the *correct* skill for each benchmark site type. | For each benchmark site's `skills:` hints in [`benchmarks/sites.yaml`](../benchmarks/sites.yaml), assert the matcher's top-N for that synthetic state. | **M** | medium |
| **Doc5** | P1 | `docs/mcp-design.md` documents Bearer-token HTTP auth that the server doesn't implement. | Either implement (fastmcp middleware that validates `Authorization: Bearer ${BROWSER_SKILLS_MCP_TOKEN}` and rejects with `permission_denied` otherwise), or remove the HTTP transport from `mcp install` until it's safe. **Recommend: implement.** | **M** | medium |
| **Q1-Q4, Q6-Q8** | P2 | Code-quality nits (redundant imports, hand-rolled file-uri, scroll branch indentation, custom exception base class, etc.). | Bundled cleanup commit; no behavior change. | **S** | trivial |
| **Q5** | P2 | Matcher hard-codes skill names (`if skill.name == "detect-captcha"`). Renaming silently breaks scoring. | Skills declare `metadata.match_signals: [{condition: "captcha_in_dom", bonus: 80}, ...]`; matcher reads from metadata. | **M** | architectural; touches every skill's frontmatter |

---

## (b) New feature proposals

Each features ranked separately under §(e). Format: motivation →
user-visible behavior → acceptance criteria → effort → dependencies.

### F1 — Reference vision adapters (Anthropic, OpenAI, Gemini)

- **Motivation.** The vision-fallback gate exists (ADR-011 BYO-model) but the bundle ships no adapters. Users wanting to see vision behavior end-to-end must implement the `VisionAdapter` Protocol themselves before they can evaluate. The wedge story relies on this being one `pip install` away.
- **User-visible behavior.** `pip install browser-skills[anthropic]` → `from browser_skills.adapters.vision import ClaudeAdapter`. Setting it via `config.set_vision_adapter(ClaudeAdapter())` causes vision fallbacks to invoke Claude. Same for `[openai]` (GPT-5.5 CUA) and `[gemini]` (Gemini Computer Control).
- **Acceptance.** Three adapters exist. For each, running a skill whose deterministic recipe fails against a broken fixture with `max_vision_calls=1` produces `SkillResult(deterministic_path=False, model_calls=1, tokens_used>0)`. Per-adapter cost-of-one-call documented in their docstrings.
- **Effort.** **M** (~2-3 days for all three).
- **Dependencies.** Vendor SDKs (already optional via extras). Vendor API access for the test fixtures (use mocks in CI; mark adapter integration as `slow`).

### F2 — DOM-snapshot benchmark (real `--quick` mode)

- **Motivation.** Phase 2 D4 patched a misleading metric with a `notes` field; the underlying issue is still that `--mode=quick` feeds the matcher synthesized DOM rather than real page HTML. The benchmark moat (ADR-007) requires real recall numbers, not "structural" checks.
- **User-visible behavior.** New command: `python benchmarks/snapshot.py` opens each site in `--mode=full` once and writes `benchmarks/snapshots/<site_id>.html.gz` (gzipped to keep repo size sane). `--mode=quick` then reads those snapshots instead of synthesizing markers. Refresh cadence: monthly via a separate workflow.
- **Acceptance.** Quick mode reports top-1, top-2, top-3 matcher hit rates against the snapshotted DOMs. Numbers are stable across runs (no network) and update only when snapshots are refreshed.
- **Effort.** **M** (~1 day).
- **Dependencies.** Disk-space discipline (target: ≤2 MB total snapshot store).

### F3 — Cross-backend benchmark (ADR-007 fulfillment)

- **Motivation.** The durable strategic position is "same recipe, same outcome, regardless of which model drives the browser." We promised this in ADR-007 and the launch blog draft but haven't shipped it.
- **User-visible behavior.** `python benchmarks/run.py --mode=full --backends=claude-4-7,gpt-5-5,gemini-cc` writes a single results.json with per-backend skill timings. The published HTML adds a per-backend column.
- **Acceptance.** 15 skills × 20 sites × 3 backends measured; results in the GitHub Pages benchmark page; numbers cited in the launch post.
- **Effort.** **L** (~1 week).
- **Dependencies.** F1 (reference vision adapters); CI budget for API calls (~$50/run × weekly).

### F4 — Stagehand / TypeScript runner (ADR-001's v1.5 promise)

- **Motivation.** TS audience is large; recipes are language-agnostic per ADR-006. Cross-runtime portability is the position no other browser-skill repo holds.
- **User-visible behavior.** `npx browser-skills-ts mcp install cursor` writes the same MCP stanza as the Python version, pointing at a Node-based server that reads the same SKILL.md files and drives Stagehand.
- **Acceptance.** Same 15 skills × the synthetic localhost integration test pass through the TS adapter. Same matcher behavior. Same trace manifest shape.
- **Effort.** **L** (1-2 weeks).
- **Dependencies.** Recipe DSL must be carefully spec'd in a language-agnostic doc (currently lives partly in the Python parser). Either embed Stagehand or call out to it.

### F5 — `reject-cookie-banner` skill

- **Motivation.** Some tasks (privacy testing, audits) require *rejecting* cookies, not accepting. The shipped `dismiss-cookie-banner` always accepts.
- **User-visible behavior.** New skill in the bundle; agent invokes when consent state matters.
- **Acceptance.** 5+ test sites verify reject paths; documented in [docs/skills-design.md](skills-design.md).
- **Effort.** **S** (2-3 hrs).
- **Dependencies.** None.

### F6 — `handle-oauth-redirect` skill

- **Motivation.** Real login flows often route through SSO providers (Google, Microsoft, Okta). Current `login-flow` can't navigate the redirect chain; it returns success after submitting the form on the IdP.
- **User-visible behavior.** New skill; chained after `login-flow` for SSO targets.
- **Acceptance.** Two real sandbox flows (auth0 sandbox + a self-hosted Keycloak) pass deterministically.
- **Effort.** **M** (~1 day).
- **Dependencies.** Sandbox SSO setup for tests.

### F7 — `extract-card-grid` skill

- **Motivation.** Many search-result pages render in `<div>` grids, not `<table>`. The shipped `extract-table-pagination` doesn't help.
- **User-visible behavior.** New skill; matcher fires on pages with repeated-structure `<article>` / `<div role="article">` / `[data-testid$="card"]` patterns.
- **Acceptance.** Verified on ≥3 benchmark sites with card-style results.
- **Effort.** **S** (3-4 hrs).
- **Dependencies.** None.

### F8 — `browser-skills doctor` command

- **Motivation.** Anticipated launch-week support load: users hitting "fastmcp not installed," "no chromium," "wrong Python." A doctor command short-circuits the support thread.
- **User-visible behavior.** `browser-skills doctor` prints a pass/fail line per check: Python version, Playwright install (+ chromium binary path), fastmcp install, current `BROWSER_SKILLS_*` env vars, MCP config files found.
- **Acceptance.** All checks runnable on macOS/Linux/Windows.
- **Effort.** **S** (2-3 hrs).
- **Dependencies.** None.

### F9 — CONTRIBUTING.md DCO enforcement

- **Motivation.** [CONTRIBUTING.md](../CONTRIBUTING.md) requires `git commit -s` (DCO sign-off) but the repo doesn't enforce it. Easy to drift on early PRs.
- **User-visible behavior.** PRs without `Signed-off-by:` in every commit are blocked by CI.
- **Acceptance.** A test PR without DCO is rejected by the CI check.
- **Effort.** **S** (1 hr — drop-in DCO GitHub Action).
- **Dependencies.** None.

### F10 — `browser-skills new` includes a Playwright Trace Viewer link in `--headed` mode

- **Motivation.** Skill authoring debug loop is slow; printing the Playwright `traceViewer://` URL after a `browser-skills test --headed` run drops authors directly into a visual debugger.
- **User-visible behavior.** Headed test runs print a "Open this trace in Playwright Trace Viewer:" line.
- **Acceptance.** Authoring guide updated; one new fixture trace exported.
- **Effort.** **S** (3-4 hrs).
- **Dependencies.** Real Playwright tracing wired in (currently we record our own simpler trace; this proposes also leveraging Playwright's built-in).

---

## (c) Non-goals for v0.2

Explicit. Saying "no" is as load-bearing as saying "yes."

1. **Captcha solving.** Ever. Per ADR-004. Even "just an integration with 2captcha." No.
2. **Anti-detection / fingerprint spoofing.** Per ADR-004. We will not bundle a stealth plugin, residential proxy integration, or canvas fingerprint patcher. Users compose those themselves; we don't link to them as "compatible companions."
3. **Hosted demo.** Per ADR-012. The launch is a recorded video + local repro instructions. Re-evaluate post-1.0 only if growth plateaus and we can fund the abuse surface.
4. **PostgreSQL session store** (or any external session backend). Premature. In-memory is correct for stdio MCP; HTTP MCP at scale is itself a future-only concern.
5. **ML-based matcher / embedding-similarity scoring.** Hand-tuned rules first. Revisit once we have telemetry on miss cases from real users.
6. **Firefox / WebKit browser support.** Track Playwright's support, but don't promise it. Chromium is the only supported target for v0.2.
7. **Per-site skill packs in the core repo.** Per anti-pattern #3 in the master plan. Site-specific skills live in user forks or a future `browser-skills-community` repo, not here.
8. **Generic plugin system.** No `entry_points`-loaded primitives in v0.2. Authors write skills (markdown), not Python plugins. Defer architectural complexity until we have evidence we need it.

---

## (d) Suggested semver bump

Current: `0.0.1`. Recommend **`0.0.1` → `0.2.0`** (skip `0.1.0`).

| Change set | Semver impact | Justification |
|---|---|---|
| 15 skills shipped (M2+M4) | minor | additive |
| MCP server + 8 tools (M3) | minor | additive |
| CLI: `new`, `test`, `mcp serve`, `mcp install` | minor | additive |
| `extract_text optional=true` parameter | patch | additive |
| Trace `sensitive: bool` field + redaction (S5) | **minor** | new field in serialized manifest; opt-in by skill flag — consumers reading the manifest will see a new top-level key |
| C2 — PlaywrightPage adds screenshot/query_selector | patch | additive |
| C6 — `assert` raises on unknown condition (was soft-pass) | **minor** | behavior change for downstream depending on soft-pass — but the soft-pass was a documented mis-feature |
| D2 — `is_initial_load` semantics change | **minor** | callers see different values for the same call shape |
| D4 — quick-mode aggregate adds `notes` field | patch | additive |
| Workflow YAML changes (C1, C4, C5) | n/a | not in package shipping surface |
| `BROWSER_SKILLS_FORBID_HEADED` truthy expansion (S2) | patch | broadens existing guard, no break |
| P3 — module-level `CHROMIUM_AVAILABLE` removed | patch | test infra; no public-API impact |

**Two minor-bump-worthy items** (trace serialization, assertion behavior). Pre-1.0, the convention is that `0.x.y → 0.(x+1).0` signals "this release breaks at least one downstream assumption." Both qualify.

**Skip to 0.2.0, not 0.1.0** — the M2+M4+M5 cuts that landed in the same session essentially constitute "the first usable release." Calling that 0.1.0 and then bumping to 0.2.0 for Phase 2 fixes inflates the version number for no signal. One 0.2.0 release with a clear changelog is cleaner.

Action: bump `[project] version = "0.2.0"` in [pyproject.toml](../pyproject.toml) at the start of the release branch; commit with a CHANGELOG entry summarizing the above.

---

## (e) Priority ordering — rationale per item

Bands, not a flat list. Each item: which band + one-line rationale.

### Must-ship in v0.2

| # | Item | Rationale |
|---|---|---|
| 1 | **C3 + C7** (success-criteria DSL) | The doc-vs-impl gap from Doc1 is patched with a callout; every shipped recipe is still one bug away from a silent post-condition violation. Highest-leverage correctness fix outstanding. |
| 2 | **D1** (split extracted from vars) | API hygiene that gets worse the longer we wait — downstream consumers parsing `SkillResult.extracted` are accumulating on the wrong contract. |
| 3 | **S1** (JS injection hygiene) | Security-shaped; should land before community contributions accelerate and we lose the per-author audit. |
| 4 | **Doc5** (HTTP auth — implement OR drop) | Currently we document a token flow we don't enforce. The fix is either "implement" or "remove HTTP from `mcp install`"; either is acceptable, but the status quo is the foot-gun. |
| 5 | **T7** (per-site matcher correctness) | Without it, we can't tell when a skill rename or scoring rule breaks matching. Smallest test-coverage gap with the largest leverage. |
| 6 | **F1** (reference vision adapters) | The vision-fallback gate is half-built without an adapter shipping. The "deterministic-first, vision-as-fallback" pitch falls apart if users have to wire their own provider to see vision at all. |

### Strong-ship (in v0.2 if budget allows)

| # | Item | Rationale |
|---|---|---|
| 7 | **F2** (DOM-snapshot benchmark) | Patching D4 with a notes field was unsatisfying. Real recall numbers are the moat per ADR-007 — get them. |
| 8 | **T5** (CLI tests) | `mcp install` writes the user's filesystem; tested invariants are overdue. |
| 9 | **D3** (skill cache invalidation) | Quality-of-life for skill authors; one MCP tool + one mtime check. Tiny effort, real win. |
| 10 | **S3** (JSON5 / commented config support) | One bug report away from urgent (Cursor's config historically allows comments); cheap to ship. |
| 11 | **F8** (`browser-skills doctor`) | Reduces launch-week support load. Pay it forward before traffic hits. |
| 12 | **F9** (DCO enforcement) | A 1-hour drop-in that protects licensing posture forever. No reason to defer. |

### Nice-to-have

| # | Item | Rationale |
|---|---|---|
| 13 | **T2** (scroll tests) | Coverage gap for `handle-infinite-scroll`; cheap. |
| 14 | **T3** (matcher ordering tests) | Catches scoring drift; cheap. |
| 15 | **T6** (benchmark scripts tests) | `_diff_regressions` is non-trivial logic; tests pay for themselves the first time it changes. |
| 16 | **Q1-Q8 bundle** (incl. Q5 matcher decoupling) | Quality batch; pair with Q5's metadata-driven signal refactor for a single cleanup commit. |
| 17 | **F5** (`reject-cookie-banner`) | Real user demand likely (privacy-testing audience); small effort; orthogonal to other work. |
| 18 | **F10** (Playwright Trace Viewer link in `--headed`) | Authoring-loop win; small effort. |

### Park for v0.3+

| # | Item | Rationale |
|---|---|---|
| 19 | **F4** (Stagehand TS runner) | Big enough to warrant its own release. Don't dilute v0.2 with it. |
| 20 | **F3** (cross-backend benchmark) | Depends on F1 (vision adapters) landing first; the headline value is best paired with the v0.3 "we have real cross-backend numbers" launch. |
| 21 | **F6** (`handle-oauth-redirect`) | Wait until `login-flow` has more real-site failure data — design against actual failure modes, not anticipated ones. |
| 22 | **F7** (`extract-card-grid`) | Demand-pull, not push. Wait for a real user issue. |

---

## Suggested release sequence

**v0.2.0** — code freeze when items 1-6 land + 7-12 if budget. Release candidate, then GA. Estimated calendar time: 3-4 weeks of part-time work.

**v0.2.x patch releases** — for items 13-18 individually, as each lands.

**v0.3.0** — F4 (Stagehand TS) as a major-feature release. Probably 6-8 weeks after v0.2.0.

**v0.4.0** — F3 (cross-backend benchmark) headline. Pairs with the "first real cross-backend numbers" blog post promised in the launch draft.

---

## What this roadmap does not commit to

- A calendar date. The 7-week original master plan is exhausted; v0.2 work is paced by the maintainer.
- A guaranteed v0.2 scope. Items 1-6 are "must-ship"; 7-12 ship if there's time. If real-world bug reports surface, those preempt this list.
- An ironclad non-goals list. If a partner integration (e.g., Browserbase asks for a particular interop hook) materializes, we'll evaluate.
