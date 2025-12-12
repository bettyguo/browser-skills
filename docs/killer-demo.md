# Killer demo — locked spec

> One scenario. Every skill must serve it. Every README, video, and launch
> post leads with it. If a feature doesn't help this demo land, defer it.

## Scenario: "Monitor 5 ML conference sites for newly accepted papers"

A real, recurring task that researchers actually do. It's boring (cookie
banners on every page, pagination, table extraction), so the wedge —
"agent does boring stuff in milliseconds, saves reasoning for the actual
task" — is immediately legible.

### User instruction (typed into Claude Code or any computer-use agent)

> Use browser-skills. Visit the 5 conference URLs in `conferences.txt`
> and extract any newly added papers since yesterday. Save the new ones
> to `new_papers.json`.

### Agent execution (target)

For each URL in `conferences.txt`:

1. `matcher.list_applicable_skills(url, dom_summary)`
   → `[dismiss-cookie-banner, verify-page-loaded, extract-table-pagination, detect-captcha]`
2. Open the page.
3. `invoke_skill(dismiss-cookie-banner)` — **deterministic, ~200 ms**
4. `invoke_skill(verify-page-loaded)` — **deterministic, ~100 ms**
5. `invoke_skill(detect-captcha)` — **deterministic, ~50 ms** (returns no-captcha)
6. `invoke_skill(extract-table-pagination)` — deterministic recipe; vision fallback only if pagination structure is unrecognized

After 5 sites: diff against local cache → return 14 new papers.

### Numbers we promise (validated at M2)

| Metric | With browser-skills | Vision-only baseline |
|---|---|---|
| Wall time (5 sites) | **≤ 90 s** | ≥ 8 min |
| Model calls for boring steps | **0** (deterministic) | ~30 (cookie banners + page-loaded reasoning ×5 + pagination ×N) |
| Cost / run | **~$0.05** (vision used only for novel decisions) | **~$0.80** (vision on every interaction) |
| Repeatability across runs | **>95%** | ~60% (vision reasoning drifts) |

The contrast is the demo. Don't soften it; if we can't hit these numbers
honestly on real sites, that's the bug.

## Why this scenario specifically

- **Real:** researchers actually monitor conferences. We're not inventing a use case.
- **Boring-step-dense:** 4-5 boring skills hit per site × 5 sites = compounding wins.
- **No login wall:** conference paper pages are public, ToS-friendly.
- **Verifiable output:** "14 new papers" — easy for the audience to grok.
- **Re-runnable:** the cache diff means re-runs are different every day; not a canned demo.

## Concrete URLs for the demo run

(Chosen for: public, stable, table-friendly, no aggressive anti-bot)

- https://arxiv.org/list/cs.AI/recent
- https://openreview.net/group?id=ICLR.cc/2026/Conference  *(verify URL at video-record time)*
- https://nips.cc/Conferences/2025/AcceptedPapersInitial
- https://icml.cc/Conferences/2025/AcceptedPapersInitial
- https://aclweb.org/  *(verify ACL 2026 acceptance list URL at record time)*

Per the inner loop: re-verify these URLs every session — conference sites
shift their paper pages around.

## What this demo deliberately is NOT

- **Not "agent books a flight."** Booking is dramatic but ToS-loaded
  (airlines hate automation), success rates wobble, and one bad demo run
  tanks credibility. Save flight-booking for a stretch demo *after*
  launch when the skill set is mature.
- **Not "agent applies to 100 jobs."** Ethically bad-faith; would
  attract a community we don't want.
- **Not a hosted live demo on our infra.** Per anti-pattern #7. We ship a
  recorded video + reproducible local instructions.

## What we need to record the demo

- The 5 URLs above, verified live
- Two video tracks side-by-side:
  - Left: browser-skills agent — fast, deterministic, ~90 s
  - Right: vision-only baseline (same agent without our skills) — slow, ~8 min
- A trace zip from the browser-skills run, visible on disk at the end
- The `new_papers.json` artifact

## Stretch demos (post-launch, not v1)

- Hotel/flight booking (date-picker showcase) — once date-picker skill flake rate <5%
- "Fill 10 contact forms with the same info" (multi-step-form + upload-file) — natural sales-ops demo
- "Diff my SaaS settings page across two accounts" — niche but very pretty

## DoD for the demo

- [ ] Recorded once at Phase 3 / M5 (then re-recorded at launch if anything looks stale)
- [ ] Reproducible: someone clones the repo, runs one command, gets the same result (±the new-paper diff)
- [ ] Trace zip embedded as artifact in the launch post
