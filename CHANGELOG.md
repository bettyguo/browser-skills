# Changelog

## [0.3.0]

Released 2026-05-13.

### Added

- Success-criteria DSL. `## Success criteria` blocks in SKILL.md are
  now parsed at load time, and (when a skill opts in via
  `metadata.evaluate_success_criteria: true`) evaluated at the end of
  every run. Eight known predicates: `dom_ready`,
  `main_content_present`, `no_visible_element`, `no_element`,
  `no_change_was_needed` (always-True sentinel for OR clauses),
  `var_is_set`, `var_is_unset`, `var_is_non_empty_list`. Pilot
  opt-ins: `verify-page-loaded` and `extract-table-pagination`.
- `SkillResult.vars_in` echoes the caller's `vars` input, separate
  from `extracted`. New field on the dataclass; new field in the MCP
  `invoke_skill` response envelope.
- `browser_skills._chromium.chromium_install_path()` helper, used by
  both `doctor` and the integration-test skip decorator.

### Changed (downstream-visible)

- `SkillResult.extracted` now contains only keys that primitive calls
  added or mutated during the run. v0.2 returned the union of caller
  input and primitive output, which made it impossible to tell which
  was which. If you were reading `result.extracted["my_input"]` to
  recover an input you passed, use `result.vars_in["my_input"]`.
- Trace redaction set covers `passwd`, `pwd`, `api_key`, `apikey`,
  `api-key`, and `bearer` in addition to the v0.2 set
  (`value`, `password`, `token`, `secret`, `auth`). Skills marked
  `sensitive: true` redact the broader vocabulary in the exported
  trace zip.
- `verify-page-loaded` and `extract-table-pagination` bumped to
  v0.2.0 to mark their opt-in to runtime-evaluated criteria.

### Fixed

- `_free_port` in the integration tests retries until it gets a port
  Chromium will accept, avoiding `ERR_UNSAFE_PORT` on SIP / X11 / IRC
  ports.
- The `scroll` primitive passes `delta` as an `evaluate(...)` arg
  instead of f-string-interpolating into the JS source.

### Known limitations

- The vision-fallback gate still requires the caller to supply a
  `VisionAdapter`. Reference adapters for the major model vendors
  are on the next release.
- A handful of success-criteria predicates remain unimplemented
  (`step_indicator_advanced`, `url_changed_since`, `combobox_has_value`,
  etc.). Opt-in skills using them get a soft-pass with a warning.

---

## [0.2.0]

Released 2026-05-13. First user-facing version. Bundles the original
build (15 skills, MCP server, CLI, benchmark scaffolding) with the
fixes from a post-launch correctness audit.

### Added

- 15 skills under [skills/](skills/), all conformant to
  agentskills.io.
- MCP server (fastmcp) with 9 tools: `start_browser`, `navigate`,
  `close_browser`, `list_skills`, `reload_skills`,
  `list_applicable_skills`, `invoke_skill`, `screenshot`,
  `page_state`.
- CLI: `list`, `info`, `version`, `new`, `test`, `doctor`,
  `mcp serve`, `mcp install {claude-desktop, cursor, codex,
  continue, print}`.
- Runner with deterministic-first execution and a vision-fallback
  gate behind a `VisionAdapter` protocol.
- Heuristic matcher with per-page-shape correctness tests.
- Trace recorder with manifest + per-step JSON + README, zipped on
  export. Redacts credential-shaped args on skills marked
  `sensitive: true`.
- `benchmarks/run.py` (`--quick` + `--mode=full`),
  `benchmarks/publish.py`, `benchmarks/file_issues.py`. Weekly cron
  runs the full suite and publishes results to GitHub Pages.

### Changed

- `Trace.record_step` redacts credential-shaped args when the skill
  is marked `sensitive: true`. Manifest gains a `sensitive` field.
- `assert` primitive raises `StepFailed` on unknown conditions
  instead of returning a soft-pass dict.
- `PageState.is_initial_load` tracks invocations since the last
  `navigate`, not the lifetime of the session.
- `dom-marker` matcher pulls values out of quoted attribute
  selectors so `[class*='newsletter' i]` markers match real DOM.
- `detect-captcha`'s keyword set covers Cloudflare Turnstile,
  reCAPTCHA, and hCaptcha, not just the literal word "captcha."
- `BROWSER_SKILLS_FORBID_HEADED` env var accepts `1`, `true`, `yes`,
  `on` (case-insensitive). The earlier check matched only `"1"`.
- `browser-skills mcp install` no longer offers an HTTP transport
  option. `mcp serve --transport=streamable-http` still exists for
  advanced users who put it behind their own auth.

### Fixed

- `try_each` probes each selector with a cheap `querySelector` call
  before attempting the action. Cookie-banner-style skills on pages
  with no banner went from 23 s to under 1 s.
- `extract_text` gained an `optional=true` flag so detect-* skills
  no longer fail on the no-match case.
- `PlaywrightPage` adapter exposes `screenshot` and `query_selector`
  so vision fallback and the screenshot recipe verb work via the
  MCP server.
- Weekly benchmark workflow runs `--mode=full`, archives results to
  `benchmarks/_runs/`, and actually deploys to GitHub Pages.

## [0.0.1]

Released 2025-11-15. Project scaffolding: license, gitignore,
pyproject, CI workflow stub, src package layout. Not published.
