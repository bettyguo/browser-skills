# Runner design

> Given a parsed skill + a live Playwright page, execute the recipe deterministically (with vision fallback), record a trace, return a structured result.

## Lifecycle

```
parse_skill(SKILL.md path) -> Skill
    │
    ▼
runner.execute(skill, page, vars={}) -> SkillResult
    │
    ├── snapshot.start()                  # URL, DOM hash, screenshot
    ├── for step in recipe.steps:
    │       try:
    │           result = primitives[step.verb](page, **step.args, vars=vars)
    │           trace.record(step, result, "ok")
    │       except StepRetryable as e:
    │           trace.record(step, e, "retry"); maybe re-execute
    │       except StepFailed as e:
    │           trace.record(step, e, "fail")
    │           if skill.has_vision_fallback and vision_budget > 0:
    │               result = vision_fallback(page, skill, intent=skill.description)
    │               break  # vision is one-shot per skill execution
    │           else:
    │               return SkillResult(status="failed", ...)
    ├── verify success_criteria
    ├── snapshot.end()
    └── return SkillResult(status="success", deterministic_path=True, ...)
```

## Data structures

```python
class Skill:
    name: str
    version: str
    description: str
    allowed_tools: list[str]
    metadata: dict
    recipe: Recipe
    success_criteria: list[Assertion]
    when_not_to_use: str
    known_failures: str

class Recipe:
    steps: list[Step]

class Step:
    verb: str                   # "click", "wait", "extract_table", etc.
    args: dict[str, Any]        # parsed key=value from the markdown line
    line_in_source: int         # for error messages
```

```python
class SkillResult:
    skill: str
    version: str
    status: Literal["success", "failed", "skipped"]
    deterministic_path: bool
    duration_ms: int
    model_calls: int
    tokens_used: int
    trace_id: str
    extracted: dict             # values bound by extract_* verbs
    steps_executed: int
    failure_reason: Optional[str]
    warnings: list[str]
```

## Primitives layer

Each action verb maps to a function under [`src/browser_skills/primitives/`](../src/browser_skills/primitives/). The runner is a dispatcher; primitives do the work.

### `primitives/click.py`

```python
async def click(page: Page, selector: str, timeout_ms: int = 5000,
                index: int = 0, vars: dict = None) -> StepResult:
    """
    Click first matching element. Raises StepRetryable on timeout
    (caller may retry), StepFailed on detached-element or unstable layout.
    """
```

Similar shape for `wait`, `wait_for_dom_ready`, `wait_for_selector`, `fill`, `select_option`, `scroll`, `scroll_until`, `extract_text`, `extract_table`, `screenshot`, `assert_*`, `try_each`.

### Special verb: `try_each`

```python
async def try_each(page, selectors: list[str], action: str,
                   on_success: str = "stop", **action_args) -> StepResult:
    """
    Iterate selectors; for the first that matches, run `action`.
    on_success="stop": short-circuit after first hit.
    on_success="continue": run action against every match.
    """
```

This is the workhorse for "the page has one of N variants of the same widget" — heavily used by cookie-banner / newsletter-popup / modal-dialog skills.

### Special verb: `vision`

```python
async def vision(page, intent: str, scope: str = "viewport",
                 allowed_actions: list[str] = None) -> StepResult:
    """
    Screenshot, send to vision adapter, receive proposed action, execute it.
    Counts against the skill's max_vision_calls budget.
    """
```

Returns a wrapped action (e.g., a `click` with model-proposed selector). Recipes should not use `vision` in the happy path; it's the fallback when `try_each` exhausts.

## Vision fallback gate

Three conditions must all hold before vision runs:

1. The deterministic recipe failed a step or its success criterion.
2. `skill.metadata.cost_budget.max_vision_calls > 0`.
3. A vision adapter is configured (`browser_skills.config.vision_adapter is not None`).

If any fail, the runner returns `SkillResult(status="failed", failure_reason="no_vision_fallback_path")`. The agent decides what to do next — often this is a healthy outcome (don't burn vision budget on a skill that's just out of scope for this site).

## Trace recording

Every step gets a trace entry. Trace structure is intentionally cheap to write and easy to load:

```
trace_<id>/
├── manifest.json           # SkillResult + step index
├── steps/
│   ├── 001-wait_for_dom_ready.json
│   ├── 002-wait.json
│   ├── 003-try_each.json
│   └── ...
├── screenshots/
│   ├── 001.png
│   ├── 003.png
│   └── ...
├── har.json                # full HAR if recording was enabled
└── README.txt              # human-readable summary
```

Export: `browser-skills trace export <trace_id> --to bug.zip`.

## Concurrency model

- Each MCP `invoke_skill` call gets its own Playwright `BrowserContext`. No shared state between concurrent calls.
- A single skill execution is **synchronous within itself** — steps run sequentially. We don't try to parallelize steps inside a recipe.
- Multiple skills running concurrently against the *same* page are forbidden in v1 (returns error). the early scoping may add a queue.

## Sandbox / safety hooks

- **Step timeout cap:** any single step >30s aborts. Recipes can override per-step but not above 60s.
- **Total skill timeout:** 5 min per skill execution; aborts and returns `failed`.
- **Navigation guard:** if a step causes an unexpected cross-origin navigation, the runner pauses and emits `unexpected_navigation` to the trace. The agent must explicitly confirm-and-continue. Rationale: protects against phishing-style redirects that vision-only agents would happily follow.
- **DOM-bomb guard:** if a step makes the DOM exceed 5 MB or the page CPU exceed 90% for >5 s, abort.

## Variable scope

Variables bound by `extract_*` are visible:
- to subsequent steps in the same recipe
- in the final `SkillResult.extracted` dict
- NOT across skill boundaries (the agent must thread them explicitly)

This keeps skill executions composable and avoids hidden global state.

## What the runner does NOT do

- **Doesn't navigate.** The caller is responsible for opening the page. Skills act on the page they're given.
- **Doesn't choose which skill to run.** The matcher / agent decides.
- **Doesn't retry failed skills.** One execution attempt per invocation. Retries are an agent-level decision.
- **Doesn't manage browser sessions.** Sessions are MCP-tool-level (`start_browser` / `close_browser`).

## Testing strategy

- **Unit:** each primitive tested against synthetic HTML pages (`pytest-httpserver`).
- **Recipe parser:** golden tests — parse fixture SKILL.md files and assert the resulting Recipe shape.
- **End-to-end deterministic:** run each v1 skill against its fixture HTML; assert `status=success`, `deterministic_path=True`, `model_calls=0`.
- **End-to-end with vision fallback:** broken-fixture pages where the deterministic path must fail; assert the vision adapter is called exactly once.
- **Concurrency:** spawn 10 concurrent skill executions, each against its own context; assert no cross-talk.

## Performance targets

| Operation | Target (p50) | Target (p99) |
|---|---|---|
| `parse_skill(SKILL.md)` | <2 ms | <10 ms |
| `runner.execute(simple skill)` | <500 ms | <2 s |
| `runner.execute(extract_table on 50-row page)` | <2 s | <8 s |
| Trace zip size for typical skill | <500 KB | <5 MB |

Misses against these go into the issue tracker as `perf-regression`.
