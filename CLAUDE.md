# CLAUDE.md — orientation for Claude Code sessions on this repo

> Read at session start. Roughly 1500 tokens; you can read it cold and
> have enough context to be useful within one turn.

## What this project is

`browser-skills` is a Skills bundle + MCP server for browser-using AI
agents. It ships 15 reusable site-pattern recipes (cookie banners,
infinite scroll, multi-step forms, table extraction, login flows,
etc.) in the [agentskills.io](https://agentskills.io) format ratified
by Anthropic in December 2025.

**One-line position:** the missing content layer for agentskills.io.
We're not a framework, not a browser-driver, not a captcha solver. We
ship reusable, runtime-neutral recipes that any browser-using agent
can plug in.

**Master execution plan:** `c:\opensource\11-browser-skills.md` — the
seven-week project brief that drove every milestone. Re-read it when
in doubt about priorities.

## Session-start checklist

1. **Read [STATUS.md](STATUS.md)** — current phase, milestones,
   blockers, hours-spent.
2. **Read [DECISIONS.md](DECISIONS.md)** — 12 ADRs, several
   superseded; pay attention to **status: accepted vs superseded**.
3. **Run** `python -m pytest tests/` — should be green in ~7s.
4. **Run** `python benchmarks/run.py --quick` — should report 100%
   matcher recall across 20 sites.
5. **Check** browser-use, Stagehand, browserbase/skills,
   vercel-labs/agent-browser for recent commits — the competitive
   recon in [docs/ecosystem-recon.md](docs/ecosystem-recon.md) is
   dated 2026-05-13; re-validate before any strategic decision.

## What you must not do

Per [DECISIONS.md](DECISIONS.md) and [docs/ethics.md](docs/ethics.md):

- **Never add captcha-solving** code (ADR-004). Detection only.
- **Never add anti-detection / fingerprint-spoofing** code. Default
  Playwright launch is the boring, identifiable default.
- **Never harvest credentials.** Login skills use env vars or
  Playwright persistent context.
- **Never invent a new skill format.** Conform to agentskills.io
  (ADR-005). Recipe conventions are a *convention within the spec*,
  not a spec extension.
- **Never use the `vision` verb in a recipe's happy path** (ADR-003).
  Vision is the fallback. The bundle's invariants test enforces this.

## What you should do automatically

- Use TodoWrite for any task with >2 steps.
- Mark tasks completed as soon as they're done.
- Keep tests green at every commit. The bar is 44+ tests passing in
  <10s.
- Update [STATUS.md](STATUS.md) at the end of every session with a
  dated entry under "Session N — YYYY-MM-DD".
- If you change a SKILL.md frontmatter field, also update
  [tests/test_bundle_completeness.py](tests/test_bundle_completeness.py).
- If you add a new primitive verb, also update
  [docs/skill-recipe-format.md](docs/skill-recipe-format.md).
- If you change the MCP tool surface, also update
  [docs/mcp-design.md](docs/mcp-design.md) and the test in
  [tests/test_mcp_server.py::test_mcp_lists_expected_tools](tests/test_mcp_server.py).

## Architecture in 60 seconds

- **Skill** ([src/browser_skills/skill.py](src/browser_skills/skill.py)) —
  a parsed SKILL.md (frontmatter + recipe). The parser is bracket- and
  quote-aware so selectors like `[aria-label='foo']` survive inside a
  `try_each` selector list.
- **PageLike** ([src/browser_skills/primitives/__init__.py](src/browser_skills/primitives/__init__.py)) —
  a Protocol satisfied by both real Playwright pages and the test
  FakePage. Every primitive accepts a PageLike.
- **Primitives** ([src/browser_skills/primitives/](src/browser_skills/primitives/)) —
  one file per verb category. New verbs register via `@register("name")`.
- **Runner** ([src/browser_skills/runner.py](src/browser_skills/runner.py)) —
  steps through a recipe; on failure, gates vision fallback by
  `max_vision_calls + adapter_configured`.
- **Matcher** ([src/browser_skills/matcher.py](src/browser_skills/matcher.py)) —
  sub-ms heuristic scorer. No model call. Hand-tuned rules per skill type.
- **Trace** ([src/browser_skills/trace.py](src/browser_skills/trace.py)) —
  append-only event log; zip export.
- **MCP server** ([src/browser_skills/server.py](src/browser_skills/server.py)) —
  fastmcp + 9 tools (incl. `reload_skills` for hot-reloading edited
  SKILL.md files). Sessions in-memory. Headed mode is opt-in,
  trace-flagged.
- **CLI** ([src/browser_skills/cli.py](src/browser_skills/cli.py)) —
  `list`, `info`, `version`, `new`, `test`, `mcp serve`, `mcp install`.

## Test FakePage

[tests/conftest.py](tests/conftest.py) provides a FakePage with an
in-memory DOM model and a routed `evaluate()` that recognizes the JS
payloads each primitive emits.

**If you add a primitive that uses `page.evaluate(...)`**: also add a
case in FakePage's `evaluate()`. Otherwise the test will raise an
AssertionError telling you to do exactly that. Branch ordering
matters — see the comment near the `try { const el = document...`
probe branch.

## Working with real Chromium

Integration tests in
[tests/test_integration_playwright.py](tests/test_integration_playwright.py)
spin up a localhost ThreadingHTTPServer and drive Playwright against
it. They skip if Chromium isn't installed (`python -m playwright
install chromium`). Mark new integration tests with
`@pytest.mark.slow` so `pytest tests/ -m 'not slow'` still runs fast.

## Running a real-site benchmark

```bash
python benchmarks/run.py --mode=full --site hacker-news-list   # single site
python benchmarks/run.py --mode=full --limit 3                 # first 3 sites
python benchmarks/publish.py                                   # render HTML
```

Real-site bugs found this way are how the deterministic-first wedge
gets sharpened. Two real bugs caught from a single Hacker News +
Wikipedia run:

1. `try_each` was blindly attempting each selector with a 1500 ms
   timeout — 23 s on a page with no banner. Fixed by probe-then-act in
   [src/browser_skills/primitives/click.py](src/browser_skills/primitives/click.py).
2. `extract_text` raised on no-match, but `detect-captcha`'s
   happy-path is "no captcha present." Fixed by adding `optional=true`
   in [src/browser_skills/primitives/extract.py](src/browser_skills/primitives/extract.py).

If you run a real benchmark and find perf > 5 s for a deterministic
skill, that's almost certainly a missing probe somewhere.

## What's done, what's left

Done (Phases 0–4 mostly):
- 15 skills shipped
- MCP server + 4-client install command
- 44 tests green (incl. real Chromium integration)
- All design docs, ethics doc, README, quickstart, authoring guide
- Launch content drafted in [docs/launch/](docs/launch/)
- Benchmark publish + GitHub issue filing scripts

Remaining for launch:
- Hero video (manual)
- GitHub Pages benchmark publish (workflow already wired; needs first deploy)
- Outreach DMs to browser-use, Stagehand/Browserbase, Anthropic, OpenAI

## Strategic risks to track

From [docs/ecosystem-recon.md](docs/ecosystem-recon.md):

1. **Browserbase** extending [browserbase/skills](https://github.com/browserbase/skills) (~3.2k) into generic site patterns. Mitigation: ship fast; remain Browserbase-compatible.
2. **vercel-labs/agent-browser** (~32.9k) expanding into our lane. Mitigation: contribute upstream, become the *content provider* across registries rather than competing on distribution.
3. **Vendor CUA improvements** (Claude 4.7, GPT-5.5 native, Gemini Computer Control) closing the common-pattern gap. Mitigation: benchmark **reproducibility + variance + cost**, not just success rate (ADR-007).

## File-pointer cheat sheet

| What | Where |
|---|---|
| Skill DSL spec | [docs/skill-recipe-format.md](docs/skill-recipe-format.md) |
| Matcher rules | [docs/matcher-design.md](docs/matcher-design.md), [src/browser_skills/matcher.py](src/browser_skills/matcher.py) |
| Runner gates (vision fallback) | [docs/runner-design.md](docs/runner-design.md), [src/browser_skills/runner.py](src/browser_skills/runner.py) |
| MCP tool surface | [docs/mcp-design.md](docs/mcp-design.md), [src/browser_skills/server.py](src/browser_skills/server.py) |
| Ethics + non-goals | [docs/ethics.md](docs/ethics.md) |
| All 15 skills | [skills/](skills/) |
| Benchmark sites | [benchmarks/sites.yaml](benchmarks/sites.yaml) |
| Benchmark runner | [benchmarks/run.py](benchmarks/run.py), [benchmarks/publish.py](benchmarks/publish.py), [benchmarks/file_issues.py](benchmarks/file_issues.py) |
| Tests | [tests/](tests/) — 44 tests, ~7s |
| Launch content | [docs/launch/](docs/launch/) |
