# Skill-set design — Phase 0 brainstorm and cut

> 30 candidate skills → 15 for v1 launch. Each skill is **general** (applies to many sites). Site-specific automations are user-authored, not shipped.
>
> All skills conform to the [agentskills.io](https://agentskills.io/specification) spec (YAML frontmatter + Markdown body + optional `scripts/`/`references/`/`assets/`). Browser-specific recipe conventions are documented in `docs/skill-recipe-format.md` (Phase 1) — they are a **convention** within the spec, not a spec extension. See [ADR-005](../DECISIONS.md).
>
> Test of a good skill: can I name 3+ real sites where exactly this pattern matters, and is the deterministic-vs-vision wedge clearly worth it?

## Selection criteria

A skill ships at launch if it scores ≥3 of these:

1. **Frequency:** the boring step happens on >50% of agent sessions (cookie banners, "verify loaded", etc.)
2. **Friction cost:** without a skill, vision-only agents burn ≥1 model call + visible latency on it
3. **Generality:** the pattern is recognizable across ≥10 sites without per-site logic
4. **Determinism:** ≥80% of cases can be handled by selectors + DOM heuristics, with vision as fallback
5. **Demo legibility:** observable in the trace ("dismissed cookie banner in 200ms")

Anything scoring <3 goes to a "stretch" list — community-author-able post-launch.

---

## Brainstorm (30 candidates)

### Tier A — Boring stuff with high frequency (8)

| # | Skill | Frequency | Friction | Generality | Determinism | Demo |
|---|---|---|---|---|---|---|
| 1 | dismiss-cookie-banner | ★★★ | ★★★ | ★★★ | ★★ | ★★★ |
| 2 | dismiss-newsletter-popup | ★★ | ★★ | ★★★ | ★★ | ★★ |
| 3 | dismiss-modal-dialog (generic) | ★★ | ★★ | ★★★ | ★★ | ★★ |
| 4 | exit-tracking-popup | ★★ | ★ | ★★ | ★★ | ★ |
| 5 | dismiss-paywall-overlay | ★ | ★★ | ★★ | ★ | ★★ |
| 6 | accept-age-gate | ★ | ★ | ★★ | ★★★ | ★ |
| 7 | dismiss-app-promotion-banner | ★★ | ★ | ★★ | ★★ | ★ |
| 8 | verify-page-loaded | ★★★ | ★★★ | ★★★ | ★★★ | ★★ |

### Tier B — Forms (5)

| # | Skill | Notes |
|---|---|---|
| 9 | fill-single-page-form | Generic name/email/etc. with label inference |
| 10 | fill-multi-step-form | Stepper wizards (Typeform, Calendly-style) |
| 11 | upload-file | File input or drag-drop; HTML5 standard |
| 12 | submit-and-await-confirmation | Click submit, wait for success indicator |
| 13 | recover-validation-errors | Read error messages, surface back to agent |

### Tier C — Data extraction & navigation (7)

| # | Skill | Notes |
|---|---|---|
| 14 | extract-structured-table | HTML `<table>` → JSON rows |
| 15 | extract-list-pagination | Repeat across `?page=N` or "next" link |
| 16 | handle-infinite-scroll | Scroll-and-extract loop with stop condition |
| 17 | extract-card-grid | Cards in repeated structure (search results, product grids) |
| 18 | search-and-filter | Type query, apply filters, capture results |
| 19 | pagination-next-page | Generic "next" navigation |
| 20 | follow-link-by-text | Click a link by visible text (with fuzzy match) |

### Tier D — Widgets (4)

| # | Skill | Notes |
|---|---|---|
| 21 | date-picker-widget | Click open, navigate months, select date |
| 22 | searchable-dropdown | Type to filter, click option |
| 23 | radio-or-checkbox-group | Read labels, select by intent |
| 24 | open-sidebar-or-tray | Click "menu", "filters", "options" |

### Tier E — Auth (3)

| # | Skill | Notes |
|---|---|---|
| 25 | login-flow | Username/password from env, submit |
| 26 | handle-oauth-redirect | Wait for redirect-back to origin |
| 27 | wait-for-magic-link | Polls inbox or skips if no inbox configured |

### Tier F — Hostile environments (3)

| # | Skill | Notes |
|---|---|---|
| 28 | detect-captcha | Detect-and-warn only. Never solve. |
| 29 | detect-paywall | Detect-and-warn; capture metadata |
| 30 | detect-rate-limit | 429s, "you've been rate-limited" messages |

---

## v1 launch cut — 15 skills

Selected for the strongest combination of frequency, friction relief, and demo legibility. Each one has a clear "boring step → instant skill" story.

| Order | Skill | Tier | Why in v1 |
|---|---|---|---|
| 1 | `dismiss-cookie-banner` | A | THE archetype — every agent demo hits this |
| 2 | `dismiss-newsletter-popup` | A | Second-most-common nuisance overlay |
| 3 | `handle-modal-dialog` | A | Generic catch-all for blocking modals |
| 4 | `verify-page-loaded` | A | Foundational — most skills need it first |
| 5 | `fill-multi-step-form` | B | Highest-leverage form pattern; demo-friendly |
| 6 | `upload-download-file` | B | Frequent in real automations; HTML5 deterministic |
| 7 | `extract-table-pagination` | C | Killer-demo skill (paper-monitoring scenario) |
| 8 | `handle-infinite-scroll` | C | Famous failure mode for vision agents |
| 9 | `search-and-filter` | C | E-commerce / search demos |
| 10 | `pagination-next-page` | C | Pairs with table extraction |
| 11 | `date-picker-widget` | D | Booking demos (hotel/flight); famous vision failure |
| 12 | `searchable-dropdown` | D | Multi-step forms need this |
| 13 | `login-flow` | E | Required for any logged-in demo |
| 14 | `detect-captcha` | F | Ethics posture; never solve |
| 15 | `exit-tracking-popup` | A | Visible win, easy demo |

**Cut from v1 (post-launch / community contributions):** age-gate, paywall-overlay, app-promotion banner, single-page-form (subsumed by multi-step), validation-error recovery (composable from multi-step), card-grid (subsumed by table-pagination), follow-link-by-text (low marginal value over agent's native click), radio/checkbox group (subsumed by multi-step), open-sidebar (low frequency), oauth-redirect (security-loaded; defer), magic-link (depends on email stack), detect-paywall (overlaps with paywall-overlay), detect-rate-limit (better as primitive).

---

## Example URLs per skill (preview — full list in benchmarks/sites.yaml)

- `dismiss-cookie-banner` — bbc.com, theguardian.com, european retailers, anything in EU jurisdiction
- `handle-infinite-scroll` — twitter.com (now x), reddit.com, instagram.com search, news feeds
- `extract-table-pagination` — wikipedia.org tables, openalex.org search, papers-with-code.com leaderboards
- `date-picker-widget` — booking.com, airbnb.com, hotels.com, opentable.com
- `pagination-next-page` — google.com search (with cohort caveats), forum sites, archive.org search

Full example URLs (≥2 per skill) ship with each skill's SKILL.md so authors can re-validate them quickly.

---

## Notes on flake rates (target by launch)

| Skill | Target flake rate |
|---|---|
| dismiss-cookie-banner | <5% |
| verify-page-loaded | <2% |
| extract-table-pagination | <8% |
| handle-infinite-scroll | <15% (the hardest one) |
| date-picker-widget | <10% |
| login-flow | <5% (per-site, with env creds present) |
| detect-captcha | <2% miss rate (false negative is the dangerous case) |

Flake rates are measured against the benchmark set ([benchmarks/sites.yaml](../benchmarks/sites.yaml)) and republished weekly post-launch.
