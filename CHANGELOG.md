# Changelog

All notable changes to browser-skills. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versioning follows [SemVer](https://semver.org/spec/v2.0.0.html)
(pre-1.0: minor bumps signal at least one downstream-visible behavior
change).

---

## [0.3.0] — 2026-05-13

Second user-facing release. Two roadmap-v0.3 must-ship items shipped
(C3+C7 success-criteria DSL, D1 extracted/vars split), plus the
audit-2 fixes that were held for this cut and a quality batch.

### Added

- **Success-criteria DSL** (C3+C7). `## Success criteria` sections in
  SKILL.md are now parsed at load time and (when the skill opts in
  via `metadata.evaluate_success_criteria: true`) evaluated at the
  end of every run. Eight known predicates: `dom_ready`,
  `main_content_present`, `no_visible_element`, `no_element`,
  `no_change_was_needed` (always-True sentinel for OR-clauses),
  `var_is_set`, `var_is_unset`, `var_is_non_empty_list`.
  OR-semantics at the criterion level. Unknown predicates
  soft-pass with a warning so authors can ship aspirational
  criteria without breaking the run. Pilot opt-ins:
  [verify-page-loaded](skills/verify-page-loaded/SKILL.md) and
  [extract-table-pagination](skills/extract-table-pagination/SKILL.md).
- **`SkillResult.vars_in`** — echo of the caller's `vars` input,
  separate from `extracted`. New field on the dataclass; new field
  in the MCP `invoke_skill` response envelope.
- **`reload_skills` documentation** across [README.md](README.md),
  [docs/mcp-design.md](docs/mcp-design.md), and [CLAUDE.md](CLAUDE.md).
  (The tool itself shipped in v0.2.0; v0.3 closes the doc gap.)
- **`browser_skills._chromium.chromium_install_path()`** — shared
  helper for `doctor` and integration-test skip detection. Private
  (underscore-prefixed) module; not part of the stable surface.

### Changed (downstream-visible)

- **`SkillResult.extracted` semantics** (D1): now contains ONLY keys
  added or mutated by primitive calls during this run. v0.2 returned
  `dict(vars)` — the union of caller-input and primitive-bound keys,
  which made it impossible to tell "you gave me this" from "I
  extracted this." If you were reading `result.extracted["my_input"]`
  to recover an input you passed, switch to
  `result.vars_in["my_input"]`. See [tests/test_result_vars_split.py](tests/test_result_vars_split.py)
  for the discriminating cases.
- **Trace redaction set** (D2): broadened to cover `passwd`, `pwd`,
  `api_key`, `apikey`, `api-key`, `bearer` in addition to v0.2's
  `{value, password, token, secret, auth}`. Skills with
  `metadata.sensitive: true` now redact a wider vocabulary in the
  exported trace zip.
- **Skill files** [verify-page-loaded](skills/verify-page-loaded/SKILL.md)
  and [extract-table-pagination](skills/extract-table-pagination/SKILL.md)
  bumped from v0.1.0 to v0.2.0 to signal their opt-in to
  runtime-evaluated success criteria.

### Fixed

- **`_free_port` flake** in integration tests: retries until it gets
  a port Chromium will accept (avoids 5060/SIP, 6000/X11, 6665-6669
  IRC, etc.). Surfaced as a real CI flake during the C3+C7 work.
- **`scroll` primitive** parameterizes `delta` via `evaluate(js, *args)`
  instead of f-string-interpolating the value into JS source.
  Defense-in-depth against future community-authored primitives.
  (S1 was in the v0.2 roadmap; mechanically applied in v0.3.)

### Test infrastructure

- 154 tests passing in ~13 s, up from v0.2's 104. New coverage:
  - C3+C7 — 34 tests across parser, evaluator, and runner wiring
  - D1 — 6 tests covering the round-trip semantics
  - `reload_skills` via fastmcp Client (T1)
  - `vision_budget` MCP override propagation (T5)
  - `mcp install` file-write paths: target write, preserve
    unrelated keys, idempotent, refuse-bad-JSON (T2)
  - `_chromium` helper presence + lint that no caller re-inlines
    the dry-run subprocess pattern (P3)
  - Workflow / README / docs/mcp-design tool listings stay in sync
    with `build_mcp().get_tools()` (Doc1-3)

### Migration notes

- **`result.extracted` semantics changed.** If any of your code paths
  read this dict to recover input values you passed in `vars=`, you
  need `result.vars_in` now. The Python and MCP envelopes both
  expose the new field.
- Skills built on v0.2 keep working without modification. Only
  pilots (verify-page-loaded, extract-table-pagination) get
  runtime-evaluated criteria; the other 13 v1 skills retain "recipe
  completion = success" behavior until their criteria are audited
  and the metadata flag flipped.

### Known limitations (deferred to v0.4)

- **F1** reference vision adapters (Anthropic / OpenAI / Gemini) —
  the BYO-model gate from v0.1 still requires users to write their
  own adapter. v0.4 must-ship.
- **F4** Stagehand TS adapter — recipes are still Python-only at
  the runner level.
- **S1 audit-1** full AST-based JS-injection lint — the regex check
  shipped in v0.2 covers single-line f-strings; multi-line cases are
  still on the v0.4 list.
- Several success-criteria predicates remain unimplemented
  (aspirational verbs like `step_indicator_advanced`,
  `url_changed_since`, `combobox_has_value`); these soft-pass with a
  warning when an opt-in skill uses them.

---

## [0.2.0] — 2026-05-13

First user-facing release. Combines the original v1 bundle work
(15 skills, MCP server, CLI, benchmark scaffolding) with a complete
three-phase audit cycle that turned up and fixed two P0 security
issues, two P0 correctness bugs, and a handful of P1s. Version
jumps from 0.0.1 directly to 0.2.0; see [docs/roadmap-v0.2.md](docs/roadmap-v0.2.md)
for the semver rationale.

### Added

- **Skill bundle.** 15 v1 skills conformant to [agentskills.io](https://agentskills.io):
  dismiss-cookie-banner, dismiss-newsletter-popup, handle-modal-dialog,
  verify-page-loaded, fill-multi-step-form, upload-download-file,
  extract-table-pagination, handle-infinite-scroll, search-and-filter,
  pagination-next-page, date-picker-widget, searchable-dropdown,
  login-flow, detect-captcha, exit-tracking-popup.
- **MCP server** on `fastmcp` with 9 tools: `start_browser`,
  `navigate`, `close_browser`, `list_skills`, `reload_skills` (new
  in 0.2), `list_applicable_skills`, `invoke_skill`, `screenshot`,
  `page_state`.
- **CLI**: `browser-skills list`, `info`, `version`, `new`, `test`,
  `doctor` (new in 0.2), `mcp serve`, `mcp install {claude-desktop|
  cursor|codex|continue|print}`.
- **Runner** with deterministic-first + vision-fallback gate
  (BYO-model via `VisionAdapter` Protocol; reference adapters are
  v0.3 work).
- **Matcher** — sub-millisecond heuristic scoring with per-site
  correctness tests covering cookie/captcha/modal/newsletter/
  table-extract page shapes.
- **Trace** — append-only step + event log, zip export with
  manifest + per-step JSON + README. Honors `sensitive: true`
  skill metadata to redact credential-shaped args.
- **Benchmark harness**: `benchmarks/run.py --mode={quick|full}`
  with `--site` and `--limit` flags, `benchmarks/publish.py` for
  HTML report, `benchmarks/file_issues.py` to auto-file
  stale-selector issues.
- **CI**: PR test workflow + DCO-sign-off enforcement + weekly
  real-site benchmark cron that publishes to GitHub Pages.
- **`browser-skills doctor`** — diagnostic command covering Python,
  Playwright, Chromium binary, fastmcp, env vars, skills directory,
  and MCP client config presence.
- **`browser-skills new <name>`** — scaffold a starter SKILL.md
  plus optional fixture HTML.

### Changed (behavior — may surprise downstream)

- **`Trace.record_step` redacts credential-shaped args** for skills
  with `metadata.sensitive: true`. The exported manifest gains a
  `sensitive: bool` field. Previously a login-flow trace shipped the
  password in plaintext. [Audit ref: S5.]
- **`assert` primitive raises `StepFailed` on unknown conditions**
  instead of returning a soft-pass dict. A recipe author writing
  `assert is_logged_in` (a predicate the implementation doesn't
  recognize) now sees a real failure with a list of known predicates.
  [Audit ref: C6.]
- **`PageState.is_initial_load`** now tracks invocations *since the
  last navigate*, not lifetime across the session. Matcher's
  "first-load" bumps for dismiss-cookie-banner and verify-page-loaded
  now correctly fire on every fresh navigate. [Audit ref: D2.]
- **Matcher scoring**: dom-marker matching now extracts content from
  quoted strings in CSS attribute selectors (`[class*='newsletter'
  i]` → recognizes `newsletter`), and `detect-captcha`'s keyword
  set covers Cloudflare Turnstile, reCAPTCHA, and hCaptcha — not
  just the literal word "captcha." The `is_initial_load + cookies_
  present` bump for `dismiss-cookie-banner` rises from +30 to +80
  so it outranks the generic `handle-modal-dialog` skill on banners
  that also use aria-modal markup. [Audit ref: T7.]
- **`browser-skills mcp install`** drops the `--transport=http`
  option until Bearer-token auth is implemented. The `mcp serve
  --transport=streamable-http` server still exists for advanced
  users who put it behind their own auth. [Audit ref: Doc5.]
- **`BROWSER_SKILLS_FORBID_HEADED`** env-var check now accepts
  `1/true/yes/on` (case-insensitive), not just the literal string
  `"1"`. [Audit ref: S2.]

### Fixed

- **`try_each` probe-then-act** (the 30× perf fix found via real
  Hacker News benchmark) — `dismiss-cookie-banner` against a
  banner-less page went from 23.4 s to 0.76 s.
- **`extract_text optional=true`** parameter — `detect-captcha`'s
  "no captcha present" happy path no longer returns `failed`.
- **`PlaywrightPage` adapter** exposes `screenshot` and
  `query_selector` — vision fallback and the screenshot recipe verb
  no longer silently capture zero bytes via the MCP server.
  [Audit ref: C2.]
- **Weekly benchmark cron** actually runs `--mode=full` (was
  silently `--quick`/no-network), archives `results.json` into
  `benchmarks/_runs/` so `file_issues.py` has history to diff
  against, and deploys `benchmarks/_site/` to GitHub Pages.
  [Audit refs: C1, C4, C5.]
- **JS-source hygiene** — `scroll` primitive parameterizes `delta`
  via `evaluate(js, *args)` instead of f-string-interpolating into
  the JS source. [Audit ref: S1.]
- **Skill cache** auto-invalidates when SKILL.md mtimes change; new
  `reload_skills` MCP tool forces re-read. [Audit ref: D3.]
- **Chromium availability** check no longer calls `asyncio.run()` at
  test-module import time (used to launch and close Chromium during
  pytest collection). [Audit ref: P3.]

### Documentation

- [README.md](README.md) rewritten around "missing content layer
  for agentskills.io" positioning, with a 15-skill catalog table.
- New: [docs/quickstart.md](docs/quickstart.md),
  [docs/authoring.md](docs/authoring.md),
  [docs/benchmarks.md](docs/benchmarks.md),
  [docs/ethics.md](docs/ethics.md),
  [docs/ecosystem-recon.md](docs/ecosystem-recon.md),
  [docs/skill-recipe-format.md](docs/skill-recipe-format.md),
  [docs/matcher-design.md](docs/matcher-design.md),
  [docs/runner-design.md](docs/runner-design.md),
  [docs/mcp-design.md](docs/mcp-design.md),
  [docs/roadmap-v0.2.md](docs/roadmap-v0.2.md).
- [CONTRIBUTING.md](CONTRIBUTING.md) with hard lines + DCO
  sign-off requirement, now CI-enforced.
- [CLAUDE.md](CLAUDE.md) — orientation for Claude Code sessions on
  this repo.
- [DECISIONS.md](DECISIONS.md) — 12 ADRs covering scope, format
  conformance, runtime portability, ethics posture, and headed-mode
  defaults.

### Known limitations (deferred to v0.3)

- `## Success criteria` sections in SKILL.md are documentation-only;
  the parsed-DSL evaluator is on the roadmap. To verify a
  post-condition today, end your recipe with an explicit `assert`
  step.
- HTTP transport for the MCP server lacks Bearer-token auth in v0.2.
- `SkillResult.extracted` conflates caller-input `vars` with
  skill-extracted values. Splitting is planned (and minor-bump-worthy)
  for v0.3.

### Test suite

102 tests passing in ~12 s, including real-Chromium integration
tests against a localhost ThreadingHTTPServer.

---

## [0.0.1] — Pre-release

Bootstrap. Repo structure, ADRs, ecosystem recon, skill-set design,
benchmark site list, ethics posture, CI scaffolding. Not user-facing.
