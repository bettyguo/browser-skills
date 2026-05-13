# Roadmap — v0.3 (delta from v0.2.0)

> Authored at the close of audit-2 (second three-phase cycle).
> Successor to [docs/roadmap-v0.2.md](roadmap-v0.2.md); items already
> tracked there are referenced by ID and not duplicated here.

> **POST-RELEASE STATUS** (added after v0.3.0 cut):
> Items in §(e) "Must-ship in v0.3" actually shipped:
> - ✅ **C3+C7** — success-criteria DSL (parser + evaluator + runner
>   opt-in for 2 pilot skills). See CHANGELOG §0.3.0.
> - ✅ **D1** — `SkillResult` gains `vars_in`; `extracted` only
>   contains primitive-mutated keys. See CHANGELOG §0.3.0.
> - ⏸ **F1** (reference vision adapters) — deferred to v0.4.
>   Vendor-SDK work that needs more contiguous time than the v0.3 cut
>   had available; also depends on the F1-described `[anthropic]` /
>   `[openai]` / `[gemini]` optional extras decision.
> - ⏸ **S1 audit-1** (AST-based JS-injection lint) — deferred to v0.4.
>   The regex-based check is still in place and catches single-line
>   f-string cases; the AST upgrade is for multi-line patterns.
>
> v0.3.0 also rolled in the audit-2 fixes from its Phase 2 (D2 trace
> redaction broadening, Doc1-3 reload_skills documentation, T1/T5/T2
> coverage, P3 chromium-detect helper).
>
> Audit-3 was performed after v0.3.0 shipped — its Phase 2 fixes
> (C4 stale runner comments, C2+T3 single-source-of-truth for
> KNOWN_PREDICATES, T1 criteria-fire-post-vision lock-in, T2 D1
> mutation contract, S2 evaluator-error warning surfacing, S3 shared
> JS predicate constants) live on `main` for the v0.4 cut.

---

## (a) Carry-over from this audit's Phase 2

Items the audit surfaced that Phase 2 chose not to address because
they require architectural change, hit existing v0.2 carry-over, or
are explicit edge-case polish (S/M/L = ≤1d / 1-3d / >3d).

| ID | Severity | Item | Remediation | Effort | Risk |
|---|---|---|---|---|---|
| **C1 (audit-2)** | P2 | `matcher._marker_signatures` over-matches across hyphenated boundaries (`.modal` substring-matches `aria-modal`). Today masked by the +80 cookie bump but it's a real precision gap. | CSS-selector-aware matching: when a marker starts with `.` require the substring to appear inside `class="..."`; when `#` require inside `id="..."`. Tightens precision; needs care to keep the recall good. **Tracks with Q5 from audit-1** (decouple matcher rules into `metadata.match_signals`). | **M** | high (changes ranking on real sites; needs benchmark re-run) |
| **C2 (audit-2)** | P2 | `_skills_cache_dir != sd` Path comparison treats `Path("skills")` and `Path("./skills")` as different. | `sd = sd.resolve()` before assigning/comparing. | **S** | low |
| **C3 (audit-2)** | P2 | `benchmarks/run.py --site` filter that matches zero sites silently produces empty report. | After `_filter_sites`, raise `SystemExit` with a "no site matches" message if `--site` was specified but the result is empty. | **S** | low |
| **C4 (audit-2)** | P2 | Misbehaving vision adapter returning `args=None` raises TypeError caught generically; trace gets unhelpful traceback. | In `_invoke_vision`, defensively coerce: `args = proposed.get("args") or {}`. Log a structured `vision_fallback_action_malformed` event. | **S** | low |
| **C5 (audit-2)** | P2 | History sorted lexicographically — relies on `date +%Y%m%d` zero-padding. | Sort by file mtime instead of name, or rename history files to ISO-8601 with separators. | **S** | low |
| **S1 (audit-2)** | P2 | `doctor`'s redaction-by-name is hardcoded literal. | Use a regex prefix match (`BROWSER_SKILLS_*_TOKEN`, `*_PASSWORD`, etc.) or a set in [`browser_skills/config.py`](../src/browser_skills/config.py) so the rule is shared with the trace redaction set. | **S** | low |
| **S2 (audit-2)** | P2 | JS-injection lint regex doesn't catch multi-line f-strings. | Replace the regex with an `ast.NodeVisitor` that walks `JoinedStr` and `FormattedValue` nodes; flags Call sites where `evaluate(...)` receives a JoinedStr first arg. | **S** | low |
| **D1 (audit-2)** | P2 | mtime race during SKILL.md rewrite. | Add a doc note; the cache will self-correct on the next call. No code change. | **S** | n/a |
| **D3 (audit-2)** | P2 | `invocations_since_navigate += 1` skipped on exception. | Wrap the Runner call in try/finally so the counter advances regardless. | **S** | low |
| **P1 (audit-2)** | P2 | 16+ stat() syscalls per cached-load call. | 100ms TTL on mtime-check: cache the last check time, skip re-stat within window. | **S** | low |
| **P2 (audit-2)** | P2 | Screenshot returned base64 inline (~400KB) over MCP. | New `screenshot_disk` tool that writes the PNG to a tmpfile and returns the path; existing `screenshot` continues to return inline for small captures. | **S** | low |
| **T3 (audit-2)** | P2 | `_marker_signatures` has no unit tests. | One small file with 6-8 cases covering literal/quoted/stripped forms. | **S** | low |
| **T4 (audit-2)** | P2 | `_max_skill_mtime` not directly tested. | Add a test that touches a SKILL.md and asserts the helper sees the new mtime. | **S** | low |
| **T6 (audit-2)** | P2 | `doctor` missing-playwright / missing-chromium branches untested. | `monkeypatch.setattr("importlib.util.find_spec", lambda name: None if name == "playwright" else ...)`. | **S** | low |
| **Q1 (audit-2)** | P2 | `_default_skills_dir` defined twice (cli.py + server.py). | Move to a shared module — likely `browser_skills/_paths.py` or extend `_chromium.py` (rename to `_diagnostics.py`). | **S** | low |
| **Q2 (audit-2)** | P2 | `_marker_signatures` returns position-typed list. | Named tuple `MarkerSignatures(literal, quoted_values, stripped)`. | **S** | low |
| **Q3+Q4 (audit-2)** | P2 | Lazy imports inside `doctor`. | Hoist `subprocess`, `importlib.util`, `os`, `platform`, `sys`, and the `__version__` import to module top. | **S** | trivial |
| **Doc4** | P2 | `BrowserSkillsError` user-facing API not in CHANGELOG. | One-line CHANGELOG addition. | **S** | trivial |
| **Doc5** | P2 | No compare links at bottom of CHANGELOG. | Append `[0.2.0]: https://...` references. Blocked until repo is pushed to github.com. | **S** | trivial |
| **Doc6** | P2 | "[0.0.1] — Pre-release" lacks a date. | Add date. | **S** | trivial |

**Still-open from audit-1's Phase 3** (not duplicated above; see [roadmap-v0.2.md](roadmap-v0.2.md) for full text):

- **C3 + C7** (success-criteria DSL evaluator) — biggest correctness deferred
- **D1** (split `extracted` from caller-input `vars`)
- **S3** (JSON5 config support)

---

## (b) New feature proposals (incremental on audit-1's F1-F10)

Audit-2 didn't surface major new feature gaps. The launch-time
features still queued from [roadmap-v0.2.md](roadmap-v0.2.md)
(F1 reference vision adapters, F2 DOM-snapshot benchmark, F3
cross-backend benchmark, F4 Stagehand TS adapter, F5
reject-cookie-banner, F6 handle-oauth-redirect, F7 extract-card-grid,
F8 already shipped, F9 already shipped, F10 Playwright Trace Viewer
link) remain the right list. Two small additions:

### F11 — `browser-skills doctor --json` for machine consumption

- **Motivation.** Support automation: ops scripts that want to verify a fleet of installs in CI/CD pipelines. Current `doctor` output is human-formatted Rich text only.
- **User-visible behavior.** `browser-skills doctor --json` emits a single JSON object with per-check pass/warn/fail status and a top-level `exit_code` field. Easy to pipe into `jq` or a CI check.
- **Acceptance.** Output passes `python -c "import json,sys;json.load(sys.stdin)"`. Schema documented in [docs/quickstart.md](quickstart.md).
- **Effort.** **S** (2-3 hrs).
- **Dependencies.** None.

### F12 — Per-step screenshot capture toggled by `metadata.trace_screenshots`

- **Motivation.** Bug reports against complex recipes (multi-step form fills, date pickers) benefit from per-step PNGs. Current trace zip has step JSON only.
- **User-visible behavior.** When a skill's frontmatter declares `metadata.trace_screenshots: true`, the runner captures a viewport screenshot after each step and stuffs it into the trace zip at `screenshots/<step-index>.png`. Off by default to keep trace zips small.
- **Acceptance.** A new fixture-based test verifies the zip layout when the flag is set; trace zip size <2 MB for a 4-step recipe.
- **Effort.** **M** (~1 day).
- **Dependencies.** PlaywrightPage now exposes `screenshot` (C2 from audit-1).

---

## (c) Non-goals for v0.3

Reuses audit-1's list ([roadmap-v0.2.md §(c)](roadmap-v0.2.md)) verbatim:
captcha solving, anti-detection, hosted demo, external session
store, ML-based matcher, Firefox/WebKit, per-site core packs,
generic plugin system. Plus two additions from this audit:

9. **Comprehensive structured-logging refactor.** The current
   `print(..., file=sys.stderr)` for headed warnings, mixed
   `console.print` for Rich output, and `trace.record_event` for
   structured trace events is a small grab-bag. A unified logging
   facade is tempting but premature; revisit if/when we have real
   end-user log-aggregation pain.

10. **Backwards compatibility for `SkillResult.extracted` shape.**
    When v0.3 ships D1 (split into `vars_in` / `extracted`), it's a
    minor break. We will **not** ship a compatibility shim that
    populates both — the deprecation cost in maintainer attention
    outweighs the migration cost for the (small) v0.2 user base.

---

## (d) Suggested semver bump

Current: `0.2.0`. The audit-2 fixes are mostly internal coverage +
documentation + redaction-set expansion. None of them break API,
none add a new tool, none change Trace output shape (the redaction
expansion only widens what gets redacted on *existing*
`sensitive: true` skills).

Recommendation: **`0.2.0` → `0.2.1`** (patch bump) for these fixes
alone, OR roll into v0.3 if we land a meaningful feature first.

| Change | Semver impact |
|---|---|
| D2 — broaden trace redaction key set | patch (purely defensive, widens redaction for opted-in skills) |
| Doc1-3 — `reload_skills` documented across surfaces | patch (doc-only) |
| T1, T5, T2 — new tests | patch (test-only) |
| P3 — chromium-detect refactor + new `_chromium.py` private helper | patch (no public API addition; module is `_` prefixed) |

**Recommendation:** hold the version at `0.2.0` and release `0.2.1`
only when paired with at least one user-visible improvement. The
audit-2 fixes can live on `main` until then.

For v0.3 (next minor): the bump is justified when **any one** of
C3+C7 (success-criteria DSL), D1 (split extracted/vars), or F1
(reference vision adapters) lands. Those each have observable
behavior/API consequences that warrant the minor.

---

## (e) Priority ordering

Bands. New audit-2 items interleaved with audit-1's still-open list.
Each line: band + one-line rationale.

### Must-ship in v0.3

| # | Item | Rationale |
|---|---|---|
| 1 | **C3 + C7** (success-criteria DSL — from audit-1) | Highest-leverage correctness gap. Every shipped recipe is one bug away from a silent post-condition violation. Doc1 (audit-1) patched the doc; the impl is the v0.3 promise. |
| 2 | **D1** (split extracted from vars — from audit-1) | API hygiene that worsens with delay. Every additional downstream consumer parsing `SkillResult.extracted` is migration cost when we split. |
| 3 | **F1** (reference vision adapters — from audit-1) | The vision-fallback gate is half-built without an adapter shipped. The wedge story falls apart if users have to wire their own provider just to see vision in action. |
| 4 | **S1 audit-1** (JS injection hygiene full audit) | Defense in depth before community PRs scale. S1 audit-2's lint regex doesn't catch multi-line cases; the AST-based replacement is the right end state. |

### Strong-ship (if v0.3 budget allows)

| # | Item | Rationale |
|---|---|---|
| 5 | **F2** (DOM-snapshot benchmark — from audit-1) | Real recall numbers are the moat (ADR-007). v0.2 patched D4 with a notes field; real numbers are the next step. |
| 6 | **C2 + C4 + D3 + Q3+Q4 audit-2** (one-shot polish commit) | Bundle: Path normalization, defensive vision-adapter input check, navigate-counter try/finally, import hoisting. Each independent commit but related shape. |
| 7 | **T3 + T4 + T6 audit-2** (helper-level test coverage) | Locks in the matcher helper, mtime helper, and doctor branches before the v0.3 refactors touch them. |
| 8 | **C5 + P1 audit-2** (history sort + stat-TTL) | Each ~30-min fix; pair them. |

### Nice-to-have

| # | Item | Rationale |
|---|---|---|
| 9 | **C1 audit-2 / Q5 audit-1** (matcher CSS-selector awareness) | Architectural; worth doing once the v0.3 must-ship list has stabilized. Easier to scope after C3+C7's recipe-level work clarifies what matcher precision is actually needed. |
| 10 | **F11** (`doctor --json`) | One-afternoon win for ops users. |
| 11 | **F12** (per-step screenshots in trace) | Real bug-report value once we hit our first complex-recipe issue. Don't pre-build it. |
| 12 | **F5 audit-1** (`reject-cookie-banner`) | Real but narrow audience. Ship when someone asks. |
| 13 | **S3 audit-1** (JSON5 config) | One user issue away from urgent. Cheap when triggered. |
| 14 | **P2 audit-2** (`screenshot_disk` MCP tool) | Premature without data. Revisit when an agent that screenshots every step shows up. |

### Park for v0.4+

| # | Item | Rationale |
|---|---|---|
| 15 | **F4** (Stagehand TS adapter) | Its own minor release. Don't dilute v0.3. |
| 16 | **F3** (cross-backend benchmark) | Depends on F1; pair with the v0.4 "first cross-backend numbers" launch post. |
| 17 | **F6** (`handle-oauth-redirect`) | Wait until login-flow accumulates real failure data. |
| 18 | **F7** (`extract-card-grid`) | Demand-pull. Wait for an issue. |

---

## Compared to v0.2 roadmap — what changed

- **No new P0s discovered.** v0.2's audit was thorough; this round caught only P1s and P2s.
- **One emerged-via-fix issue** — when expanding the trace redaction set, the lack of a `BROWSER_SKILLS_*_PASSWORD`-shape env-var prefix rule in `doctor` became more visible. Bundled here as S1 (audit-2).
- **One ratcheted-up issue** — the matcher's CSS-selector imprecision (C1 audit-2) was visible in audit-1 as Q5; audit-2's matcher correctness tests (T7 audit-1) made it concrete enough to bite. Promoted from "decoupling refactor" to "precision gap to fix as part of v0.3 work."
- **Two new features queued** (F11 doctor --json, F12 per-step screenshots) but neither must-ship.

## Compared to actual v0.2 → v0.2.1 contemplated cut

Audit-2's fixes (D2, Doc1-3, T1, T5, T2, P3) are individually patch-shaped. Recommend rolling them into the v0.3 release rather than cutting v0.2.1 — version inflation isn't free, and the audit-2 fixes have no urgency for downstream consumers (no broken downstream API, no critical security regression).

If a v0.2.1 is cut anyway (e.g., the trace-redaction expansion in D2 is graded as security-significant enough), the CHANGELOG must clearly mark it as a redaction-set expansion and not a "trace format change." Existing trace consumers continue to work; they just see redactions on a wider set of arg names.
