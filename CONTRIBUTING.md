# Contributing to browser-skills

Thanks for thinking about contributing. This document covers the
practical mechanics and the few non-negotiables.

## Hard lines (will not change)

Before you spend time on something, make sure it isn't one of these.
See [docs/ethics.md](docs/ethics.md) and the project's ethics doc:

- **No captcha solving.** Detect-only. Solving PRs are closed.
- **No anti-detection / fingerprint spoofing.** We don't ship stealth
  tooling.
- **No credential harvesting.** Login skills use Playwright persistent
  context or env vars only.
- **No site-bespoke skills in the core bundle.** General patterns only.
  Site-specific skills can live in your own fork or, eventually, a
  community-packs repo.

## What we're looking for

In rough priority order:

1. **Bug reports + traces** for stale selectors. The benchmark cron
   surfaces these as `stale-selector` issues. If you have a `trace.zip`
   from a failed skill execution, attach it.
2. **New selectors** for existing skills. Banner / popup / modal
   variants we don't yet cover. PR target: add to the `try_each`
   list in the existing skill's SKILL.md, bump the patch version.
3. **New skills** that fit the general-pattern bar (see
   ). Open an issue first
   so we can align on naming and overlap with existing skills.
4. **Backend adapter improvements** for browser-use, Stagehand, or
   any new browser-automation library. 
5. **Benchmark site additions** that are ToS-friendly and
   non-overlapping with existing fixtures.

## Licensing

All contributions are MIT (see [LICENSE](LICENSE) and ).
Contributors retain copyright; contributions are licensed in.

We use **DCO sign-off**, not a CLA. Add a `Signed-off-by` line to your
commits:

```
git commit -s -m "Add new selector to dismiss-newsletter-popup"
```

That line is the developer certificate of origin
([developercertificate.org](https://developercertificate.org/)) — your
commit certifies that you have the right to contribute the code under
the project license.

## Development setup

```sh
git clone https://github.com/browser-skills/browser-skills
cd browser-skills
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
python -m playwright install chromium
pytest tests/
```

Running the bundle parser-only sanity check (~1 second):

```sh
pytest tests/test_bundle_completeness.py
```

Running the matcher recall over the benchmark site list (no network):

```sh
python benchmarks/run.py --quick
```

Running the full benchmark with real Chromium (slow, ~10 minutes):

```sh
python benchmarks/run.py --mode=full
```

## Authoring a new skill

1. `mkdir skills/your-skill-name && cd skills/your-skill-name`
2. Create `SKILL.md` per the format in
   [docs/skill-recipe-format.md](docs/skill-recipe-format.md).
3. Hit the authoring checklist at the bottom of that doc:
   - `name`, `description`, `version`, `metadata.exercised_on` (≥2 sites)
   - Recipe is deterministic-first (no `vision` in happy path)
   - Success criteria has at least one verifiable `assert`
   - Known failures documents at least one (intellectual honesty)
   - `flake_rate_target` is honest, not aspirational
4. Add a parser fixture test or extend `tests/test_bundle_completeness.py`.
5. Update  if you're
   adding to the launch set (rare).

## Code style

- Python 3.11+. `ruff` for lint, `mypy` for types — both run in CI.
- Async by default in primitives; the runner is async end-to-end.
- No comments that just describe what code does. Use a comment for
  *why* something is non-obvious (a workaround, a hidden invariant).
- Tests must run without network. Real-site checks belong in the
  weekly benchmark workflow, not in `pytest tests/`.

## PR review

- One reviewer for selector / fixture changes (patch-level)
- Two reviewers for recipe structure changes, new skills, or
  cross-skill matcher rules (minor/major)
- ADR required for: licensing decisions, vendor-lock-in choices,
  scope-boundary changes (anti-pattern violations)

## Communication

- Bugs and feature requests: GitHub Issues
- Security issues (e.g., trace leaking creds): private maintainer email
- Strategy discussion: GitHub Discussions
