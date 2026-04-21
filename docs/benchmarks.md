# Benchmarks

> How we measure, what we publish, and what the numbers mean.

## What we measure

For each (skill × site) pair on the benchmark, we record:

1. **Success rate** — fraction of runs where the skill returns `status: success`
2. **Deterministic-path rate** — fraction of successes that didn't need vision
3. **Wall-time** — total skill execution time, p50 and p99
4. **Token cost** — when vision fires, the in/out token total
5. **Variance across re-runs** — std-dev of success across N consecutive runs

The killer-demo claim — "browser-skills agent in 90 s vs vision-only agent in 8 min" — is honest only if we also publish (3), (4), and (5). Lower variance and lower cost are the durable differentiation; raw success-rate-only gets eaten by vendor CUA improvements ([ADR-007](../DECISIONS.md)).

## Site selection

The 20 benchmark sites are in [benchmarks/sites.yaml](../benchmarks/sites.yaml). Selection criteria:

- Durable (existed >5 years, expected to persist)
- ToS-friendly to automation
- Each site exercises ≥2 skills
- Each skill exercised by ≥2 sites (with two documented exceptions: `detect-captcha` and `login-flow` — see [test_bundle_completeness.py](../tests/test_bundle_completeness.py))
- No anti-bot-hostile targets (Amazon retail, LinkedIn, Instagram are intentionally absent)

If a benchmark site changes its ToS or becomes anti-bot-hostile, we drop it.

## How to run

```bash
# Matcher recall, no network. ~1 second.
python benchmarks/run.py --quick

# Real Chromium. ~10 minutes for 20 sites.
python benchmarks/run.py --mode=full

# Output goes to benchmarks/results.json
```

The weekly cron in [.github/workflows/benchmark.yml](../.github/workflows/benchmark.yml) runs the full mode every Monday 06:00 UTC and publishes results to GitHub Pages. Failures open `stale-selector`-tagged issues automatically.

## How to read results

`benchmarks/results.json` schema (abbreviated):

```json
{
  "mode": "full",
  "ran_at": 1747400000.0,
  "n_sites": 20,
  "n_skills": 15,
  "aggregate": {
    "total_skill_runs": 78,
    "success_count": 71,
    "success_rate_pct": 91.0,
    "sites_with_error": 1
  },
  "sites": [
    {
      "site_id": "wikipedia-list",
      "url": "https://en.wikipedia.org/wiki/...",
      "matcher_top": ["verify-page-loaded", "extract-table-pagination"],
      "skill_results": {
        "verify-page-loaded": {
          "status": "success",
          "deterministic": true,
          "duration_ms": 412,
          "failure_reason": null
        },
        ...
      },
      "duration_ms": 1842
    },
    ...
  ]
}
```

A site can show `error: "..."` instead of `skill_results` if the page-load itself failed; this counts toward `sites_with_error` but not toward skill success/failure.

## What the numbers should look like

v1 launch targets, per skill, on its `exercised_on` sites:

| Skill | Target success rate | Target deterministic-path | Target p50 wall-time |
|---|---|---|---|
| verify-page-loaded | >98% | 100% | <500 ms |
| dismiss-cookie-banner | >95% | >90% | <800 ms |
| detect-captcha | >98% (no false neg) | 100% | <500 ms |
| extract-table-pagination | >92% | >85% | <2 s |
| handle-infinite-scroll | >85% | >75% | <8 s |
| date-picker-widget | >90% | >70% | <2 s |
| login-flow | >95% (with creds) | >85% | <3 s |
| (others) | >90% | >80% | <2 s |

If we miss these at launch, we ship with the honest numbers and document the gap. Per [README](../README.md)'s anti-pattern #4: "don't claim 100% success rates."

## Anti-pattern check

What we explicitly DON'T benchmark against:

- **Sites with strict scraping ToS** (LinkedIn, Facebook). Benchmark = quality signal; we don't stress-test ToS boundaries.
- **Sites with aggressive anti-bot** (Amazon retail, some airlines). Adds noise we can't act on.
- **Sites that ourselves run** (no synthetic-only "100% perfect" numbers).

## Cross-backend benchmark (ADR-007)

The killer-moat we're building toward — promised for v0.2: same 15 skills, same 20 sites, three backends:

- Claude 4.7 computer-use API
- GPT-5.5 native CUA
- Gemini Computer Control

Same script, three runs, publish the cross-tab. The durable claim is **"same recipe, same outcome, regardless of which model drives the browser."** That's the position no competitor currently owns.
