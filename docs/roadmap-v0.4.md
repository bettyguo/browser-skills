# Roadmap — v0.4 (delta from v0.3.0)

> Authored at the close of audit-3 (third three-phase cycle).
> Successor to [docs/roadmap-v0.3.md](roadmap-v0.3.md); v0.3 items
> that didn't ship were re-ranked into this plan rather than
> duplicated.

---

## (a) Carry-over from audit-3 Phase 2

Items the audit surfaced and this phase deferred. Same S/M/L grading
as prior audits.

| ID | Severity | Item | Remediation | Effort | Risk |
|---|---|---|---|---|---|
| **C1+D1 (audit-3)** | P2 | Shallow snapshot of caller vars means a primitive that in-place-mutates a caller-passed list goes undetected by the `extracted` diff. v1 primitives reassign, but the contract is fragile. T2 (audit-3) locks in current behavior. | Deep-copy snapshot at `caller_vars = copy.deepcopy(vars or {})`. Cost: O(n) on input vars; for typical usage (≤10 keys) negligible. Behavior change for any caller relying on shared-reference behavior with the original `vars` dict. | **S** | medium (subtle behavior shift) |
| **C3 (audit-3)** | P2 | `_max_skill_mtime` uses `>` for cache invalidation. Reverting to an older revision (mtime goes backwards) leaves stale cache. | Switch to `!=` and re-test the cache-invalidation suite. | **S** | low |
| **C5 (audit-3)** | P2 | `Skill.success_criteria: list[Any]` annotation. Use `TYPE_CHECKING`-only import to type as `list[Criterion]`. | Three-line change in skill.py. | **S** | low |
| **S1 (audit-3)** | P2 | `Predicate` dataclass is mutable; cached Skills share Predicate references with running evaluator. | `@dataclass(frozen=True)`. Affects any code that mutates Predicate (none today). | **S** | low |
| **D2 (audit-3)** | P2 | `Trace.events` grows unbounded. Acceptable today; would scale poorly under per-step screenshot capture (F12). | Soft cap (e.g., 1000 events; older ones dropped with a `[trace_truncated_at:N]` event). | **S** | low |
| **P1 (audit-3)** | P2 | 16+ stat() syscalls on every cached-load call. Still pending. | 100ms TTL on mtime check. | **S** | low |
| **P2 (audit-3)** | P2 | `extracted` diff comprehension is O(n) per execute. Premature; flag. | Track primitive writes incrementally rather than diffing. | **M** | low |
| **T4 (audit-3)** | P2 | Soft-pass warning text on a sensitive skill could leak credential names through `criterion.raw_text`. | Apply S5/D2 redaction to warning strings, OR mark sensitive skills as "no soft-pass warnings." | **S** | low |
| **T5 (audit-3)** | obsolete | Drift-detection test for JS payloads — supplanted by S3's shared constants. | N/A | — | — |
| **Doc4/Doc5/Doc6/Doc7 (audit-3)** | P2 | Cosmetic doc gaps (v0.2 references in docs/mcp-design.md, docs/benchmarks.md; missing CHANGELOG compare links and pre-release date). | Mechanical sweep. | **S** | trivial |
| **Q1-Q5 (audit-3)** | P2 | Code organization nits (parse_success_criteria order, conftest fixture extraction for SKILL.md writer + MCP stub session). | Pair with the conftest-fixture refactor. | **S** | low |

**Still-open from audit-1's Phase 3** (re-prioritized here):

- **F1** (reference vision adapters) — v0.4 must-ship
- **F2** (DOM-snapshot benchmark) — v0.4 strong-ship
- **F3** (cross-backend benchmark) — v0.5 (depends on F1)
- **F4** (Stagehand TS adapter) — v0.5+
- **F5-F7** (additional skills) — demand-pull
- **F8** (`browser-skills doctor`) — shipped in v0.2

**Still-open from audit-2's Phase 3**:

- **S1 audit-1** (AST-based JS lint) — v0.4
- **S3 audit-1** (JSON5 config support) — strong-ship if budget

---

## (b) New feature proposals

### F13 — Predicate-author registry for skill packs

- **Motivation.** v0.3 introduced 8 known predicates. Adding more
  (e.g., `url_changed_since`, `cookie_set_named`, `combobox_has_value`)
  requires editing `criteria.py`. Skill-pack authors might want to
  contribute predicates without forking the runtime.
- **User-visible behavior.** A new public API:
  `browser_skills.criteria.register_predicate(name, evaluator)`.
  Skill packs register at import time. Conflicts with built-ins
  raise on registration.
- **Acceptance.** A third-party pack registers `url_changed_since` and
  one of the v1 skills (search-and-filter, pagination-next-page) opts
  in with its real criterion.
- **Effort.** **M** (~1 day).
- **Dependencies.** S3 (audit-3) — shared constants already extracted.

### F14 — `browser-skills bench --compare HEAD~1` for PR review

- **Motivation.** Reviewers of skill PRs want to see "did this PR
  regress matcher accuracy or skill success rate against the
  benchmark suite?" Today they'd have to run the benchmark twice
  manually.
- **User-visible behavior.** `browser-skills bench --compare HEAD~1`
  runs the benchmark on HEAD and HEAD~1 and prints a colored diff
  table showing per-skill/per-site changes.
- **Acceptance.** A PR adding a new skill to the bundle shows up
  in the diff output as `+1 skill, no regressions`.
- **Effort.** **M** (~2 days).
- **Dependencies.** F2 (DOM-snapshot benchmark) — without snapshots
  the comparisons are network-noisy.

### F15 — Recipe-level `templated_arg` substitution

- **Motivation.** `fill-multi-step-form` and `date-picker-widget`
  recipes use `value="$vars.name"` syntax. The recipe parser passes
  this through as the literal string today (callers report the
  primitive receives `"$vars.name"` not the substituted value).
- **User-visible behavior.** Recipe-DSL adds `$vars.X` template
  substitution. The parser leaves the placeholder structure; the
  runner substitutes against `vars_in` (D1) before passing args to
  primitives.
- **Acceptance.** A skill that does `fill selector="#name" value="$vars.name"`
  with `vars={"name": "Alice"}` actually fills "Alice" into the
  input.
- **Effort.** **M** (~1-2 days).
- **Dependencies.** D1 (`vars_in` available as the substitution source).

---

## (c) Non-goals for v0.4

Reuses audit-1+audit-2's lists (captcha solving, anti-detection,
hosted demo, external session store, ML-based matcher, Firefox/WebKit,
per-site core packs, generic plugin system, structured-logging
refactor, D1 backcompat shim) and adds two:

11. **Deep-copy of caller vars by default** (audit-3 C1+D1).
    Reconsider if a real bug surfaces; otherwise document the
    contract and move on.
12. **Async predicate registration for F13**. Predicate registration
    is import-time only; runtime dynamic registration adds threading
    complexity for marginal value.

---

## (d) Suggested semver bump

Current: `0.3.0`. Audit-3 Phase 2 fixes are:

| Change | Semver impact |
|---|---|
| C4 stale comments | none (docs) |
| C2+T3 KNOWN_PREDICATES derivation | patch (internal refactor) |
| T1 post-vision criteria test | none (test-only) |
| T2 D1 mutation contract test | none (test-only) |
| S2 `error_sink` parameter on evaluator | patch (additive parameter; v0.3 callers unaffected) |
| S2 new "criterion eval error" warning shape | **minor** (callers reading SkillResult.warnings see a new string format) |
| S3 `_js_predicates.py` private module | none (underscore-prefixed; not stable surface) |
| Doc1-3 STATUS + roadmap refresh | none (docs) |

**Recommendation:** `0.3.0` → `0.3.1` for these fixes alone. The S2
warning-shape change is borderline minor but the format is additive
(new entries; existing entries unchanged) so patch is defensible.

For v0.4 (next minor): the bump is justified when **any one** of F1
(reference vision adapters), F13 (predicate registry), or F15 (template
substitution) lands. Each has observable behavior/API consequences.

---

## (e) Priority ordering

### Must-ship in v0.4

| # | Item | Rationale |
|---|---|---|
| 1 | **F1** (reference vision adapters — Anthropic / OpenAI / Gemini) | The vision-fallback gate is half-built without an adapter ships. Highest-leverage feature carry-over from audit-1. |
| 2 | **S1 audit-1** (AST-based JS-injection lint) | Defense-in-depth before community contributions accelerate. Multi-line f-string cases aren't caught by the v0.2 regex check. |
| 3 | **F15** (recipe-level `$vars.X` substitution) | Already documented in multiple shipped SKILL.md recipes; today the parser passes literal `"$vars.name"` through. Closes a doc-impl mismatch. |
| 4 | **Audit-3 C1+D1 escape hatch** (deep-copy snapshot OR explicit documentation) | The shallow-copy contract bites someone the first time a community primitive does in-place mutation. Pick: implement deep-copy OR add a runtime warning when a primitive mutates a caller-passed mutable. |

### Strong-ship (in v0.4 if budget allows)

| # | Item | Rationale |
|---|---|---|
| 5 | **F2** (DOM-snapshot benchmark) | Real recall numbers are the moat (ADR-007). Audit-2 patched D4 with a notes field; this is the next step. |
| 6 | **F13** (predicate-author registry) | Unblocks community skill packs adding predicates. M-effort; clean architectural shape. |
| 7 | **S3 audit-1** (JSON5 config support) | One issue away from urgent. Cheap when triggered. |
| 8 | **Audit-3 P1+P2 perf** (mtime TTL + extracted incremental tracking) | Bundle: one perf commit. Telemetry would help prioritize; ship now if v0.4 is "polish + features" cut. |

### Nice-to-have

| # | Item | Rationale |
|---|---|---|
| 9 | **F14** (`bench --compare HEAD~1`) | PR reviewer ergonomics. Depends on F2 landing first. |
| 10 | **Audit-3 C3** (mtime `!=` semantic) | git-checkout-then-server-reload edge case; rare in practice. |
| 11 | **Audit-3 C5** (Skill.success_criteria type annotation) | Cosmetic typing; no runtime effect. |
| 12 | **Audit-3 S1** (frozen Predicate) | Defense-in-depth; no current bug. |
| 13 | **Audit-3 Q1-Q5** + **Doc4-Doc7** | Cleanup batch. Pair with one of the larger commits. |

### Park for v0.5+

| # | Item | Rationale |
|---|---|---|
| 14 | **F4** (Stagehand TS adapter) | Major work; deserves its own release. |
| 15 | **F3** (cross-backend benchmark) | Depends on F1 landing AND on F2 snapshots being stable. |
| 16 | **F6** (`handle-oauth-redirect`) | Wait for real-world login-flow failure data. |
| 17 | **F7** (`extract-card-grid`) | Demand-pull. |

---

## Compared to v0.3 roadmap — what changed

- **No new P0s discovered.** Three consecutive thorough audits and
  still no P0. Codebase is healthy.
- **One emerged-via-fix item** — when I extracted `_js_predicates.py`
  (S3), I noticed the recipe-level `$vars.X` substitution is
  documented but not implemented. Promoted to F15 must-ship.
- **D1 work in v0.3 left a fragility** — shallow snapshot. T2 locks
  in the current contract; v0.4 must decide whether to upgrade to
  deep-copy or accept the documented behavior.
- **One promotion** — F1 (vision adapters) was v0.3 must-ship that
  didn't ship; it's still must-ship in v0.4. Same with S1 audit-1.

## Compared to actual v0.3 → v0.3.1 contemplated cut

If a v0.3.1 patch is desired (security-sensitive flagging of S2's
warning-surface change), it's defensible. Otherwise roll into v0.4.
The audit-3 fixes are individually small; bundling into the next
feature release minimizes version-string noise for downstream.
