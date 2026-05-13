# Contributing

Thanks for thinking about a PR. Practical notes below; the
non-negotiables come first.

## Won't-do list

These are off the table; PRs that touch them get closed.

- Captcha solving. Detection only.
- Anti-detection or fingerprint spoofing.
- Credential harvesting. Login skills use a Playwright persistent
  context or env-var values; nothing else gets stored.
- Site-bespoke skills in the core bundle. General patterns only.
  Per-site logic can live in a fork or a community-packs repo.

See [docs/ethics.md](docs/ethics.md) for the longer rationale.

## What's most useful

Roughly in priority order:

1. Bug reports with attached trace zips for stale selectors. The
   weekly benchmark cron files these as `stale-selector` issues; if
   you have one from a failed run, attach the trace.
2. New selectors for existing skills. Open a PR adding to the
   `try_each` list in the relevant SKILL.md and bump the patch
   version.
3. New skills that fit the general-pattern bar. Open an issue first
   so we can talk about overlap with existing skills.
4. Adapter improvements for browser-use, Stagehand, or a new
   browser-automation library.
5. Benchmark site additions: ToS-friendly, non-overlapping with
   existing fixtures.

## License

All contributions are MIT. Contributors keep copyright; contributions
are licensed in.

DCO sign-off, not a CLA. Add a `Signed-off-by` line to your commits:

```
git commit -s -m "Add a selector to dismiss-newsletter-popup"
```

That line is the [developer certificate of origin](https://developercertificate.org/);
it certifies you have the right to contribute under the project
license.

## Dev setup

```sh
git clone https://github.com/bettyguo/browser-skills
cd browser-skills
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m playwright install chromium
pytest tests/
```

Quick sanity checks:

```sh
pytest tests/test_bundle_completeness.py      # SKILL.md invariants
python benchmarks/run.py --quick              # matcher recall, no network
python benchmarks/run.py --mode=full          # real Chromium, ~10 min
```

## Authoring a new skill

1. `browser-skills new <name>` to scaffold.
2. Edit `skills/<name>/SKILL.md` per [docs/skill-recipe-format.md](docs/skill-recipe-format.md).
3. Authoring bar: required frontmatter fields, recipe is
   deterministic-first (no `vision` in the happy path), at least one
   verifiable `assert`, at least one documented known failure, an
   honest `flake_rate_target`.
4. Add a fixture test or extend `tests/test_bundle_completeness.py`.

## Code style

- Python 3.11+. `ruff` for lint, `mypy` for types; both run in CI.
- Async throughout the primitives and runner.
- Comments explain *why*, not *what*. The function name and its body
  should already say what.
- Tests must run without network. Real-site checks belong in the
  weekly benchmark workflow.

## Reviews

- One reviewer for selector or fixture changes (patch-level).
- Two reviewers for recipe-structure changes, new skills, or
  cross-skill matcher rules.

## Communication

- Bugs and feature requests: GitHub Issues.
- Security reports (e.g. a trace leaking creds): mail the maintainer
  privately, don't open a public issue.
