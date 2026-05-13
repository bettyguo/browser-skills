# Skill Recipe Format

> The convention for browser-skill recipes inside an agentskills.io-conformant SKILL.md.
> **Not a spec extension.** Everything below fits inside the [agentskills.io specification](https://agentskills.io/specification) as it stands.

## What this document is

A reference for skill authors. Spells out:
- The YAML frontmatter shape (spec-compliant fields + our `metadata:` map)
- The required Markdown sections inside the body
- The action-verb DSL used in `## Recipe` steps
- Selector syntax
- Success criteria, fallback, and trace conventions

If a skill follows this format, the runner can execute it deterministically. If a skill ignores this format and uses freeform prose, it still loads (it's valid SKILL.md), but the runner falls back to vision interpretation step-by-step.

---

## Minimum-viable skill

```markdown
---
name: dismiss-cookie-banner
description: Detects and dismisses cookie consent banners on any site
version: 0.1.0
allowed-tools: [click, wait]
metadata:
  applies_to: any-website
  flake_rate_target: 0.05
  exercised_on: [bbc.com, theguardian.com, nytimes.com]
---

# Dismiss Cookie Banner

## When to invoke
On any new page navigation, before interacting with content.

## Recipe
1. wait_for_dom_ready timeout=2s
2. wait extra=500ms
3. try_each selectors=[
     "[aria-label*='cookie' i] button:has-text('Accept')",
     "[aria-label*='cookie' i] button:has-text('Agree')",
     "#onetrust-accept-btn-handler",
     "button.cc-allow",
     "button.cc-accept-all",
     "button:has-text('Accept all cookies')",
   ] action=click on_success=stop
4. wait extra=300ms

## Success criteria
- Cookie banner element no longer in DOM, OR
- No matching selector was ever found (no-op success)

## When NOT to use
- The user task is *about* the cookie banner itself (privacy testing, screenshot of pre-consent state).

## Known failures
- Custom Drupal-style banners outside the common-selector set (~2% of sites). Vision fallback handles.
- Cross-origin iframe banners (~1%). Cannot be dismissed; documented and reported.
```

---

## YAML frontmatter

Spec-permitted fields only. We do **not** invent new top-level keys.

| Field | Required | Type | Notes |
|---|---|---|---|
| `name` | yes | kebab-case string | Globally unique among the bundle. Matches the directory name. |
| `description` | yes | one-line string | Used by agents to decide whether to invoke. Keep <120 chars. |
| `version` | yes | semver string | Patch bumps for selector tweaks; minor for new failure modes handled; major for recipe-shape changes. |
| `disable-model-invocation` | no | bool | Spec field. Set `true` for skills only callable programmatically. We never use it in v1. |
| `allowed-tools` | no | list[string] | Spec field. The action verbs the recipe uses (`click`, `wait`, `extract`, `scroll`, `fill`, `screenshot`, `vision`). Lets agentskills.io tools constrain the surface. |
| `metadata` | no | map | **Free-form map permitted by the spec.** Holds our convention fields below. |

### Conventional fields inside `metadata:`

```yaml
metadata:
  applies_to: any-website            # or a URL glob: "*.booking.com"
  url_patterns: ["*"]                # optional list of URL patterns for matcher
  dom_markers:                       # optional CSS selectors hinting applicability
    - "[aria-label*='cookie' i]"
    - "#onetrust-banner-sdk"
  flake_rate_target: 0.05            # max acceptable flake rate at launch
  flake_rate_measured: null          # populated by benchmark CI
  exercised_on:                      # at least 2 site IDs from benchmarks/sites.yaml
    - bbc.com
    - theguardian.com
  cost_budget:                       # for the demo's cost story
    deterministic_only: true         # if true, never invoke vision
    max_vision_calls: 0              # 0 means vision is forbidden for this skill
  sensitive: false                   # if true, trace omits screenshots for this step
```

Tools that don't understand `metadata:` ignore it (per the agentskills.io spec).

---

## Required Markdown sections

Order matters; the runner parses by section heading.

### `## When to invoke`
Plain prose. Tells the matcher (and any LLM doing skill selection) when this skill should run. 1-3 sentences.

### `## Recipe`
A numbered list of action-verb steps. **This is the executable part.**

Recipes are written in a small DSL — verb followed by `key=value` arguments. Spaces inside selectors are fine; arguments are parsed by name not position.

#### Action verbs (v1)

| Verb | Args | Effect |
|---|---|---|
| `wait_for_dom_ready` | `timeout` | Wait until `document.readyState === "complete"` |
| `wait_for_selector` | `selector`, `timeout`, `state=(visible\|attached\|hidden)` | Wait for selector match |
| `wait` | `extra` (ms) | Sleep |
| `click` | `selector`, `timeout`, `index=0` | Click first matching element |
| `try_each` | `selectors` (list), `action`, `on_success=(stop\|continue)` | Iterate selectors, run action, optionally short-circuit |
| `fill` | `selector`, `value`, `clear=true` | Type into input |
| `select_option` | `selector`, `value` or `label` | `<select>` dropdown |
| `scroll` | `target=(window\|selector)`, `delta=(N px\|page\|element-into-view)` | Scroll |
| `scroll_until` | `condition`, `max_iters=50`, `delay=300ms` | Scroll loop with stop predicate |
| `extract_text` | `selector`, `into=$varname` | Bind matched text to a variable |
| `extract_table` | `selector`, `into=$varname` | Bind table rows to a list-of-dicts |
| `screenshot` | `selector` (optional), `into=$varname` | Capture image |
| `assert` | `condition` | Skill-aborts if false. Used in `## Success criteria` block too. |
| `vision` | `intent`, `scope=(viewport\|element)` | Fallback. Calls vision adapter. Recipes should not use this in the happy path. |

#### Selectors

CSS-selector strings as understood by Playwright, including text-engine syntax:

- `button:has-text('Accept')`
- `[aria-label*='cookie' i] button`
- `text=/^Sign in$/i`
- `>>` chaining is allowed

Avoid Python-specific Playwright locator chains (e.g., `.first()`, `.nth(0)`) — the runner adds those when executing the verb. This keeps recipes portable across language adapters (the ethics doc).

#### Variables

`$varname` syntax. Bound by `extract_*` and `screenshot` verbs. Available to subsequent steps and to the recipe's structured return value (see below).

### `## Success criteria`
What "this skill worked" looks like. Written as one or more `assert` lines:

```
- assert no_element selector="[aria-label*='cookie' i]" OR no_change_was_needed
- assert dom_changed since=step1
```

**v0.1 status (must read):** the `## Success criteria` section is
currently **documentation-only**. The runner treats "all recipe steps
completed without raising" as success; it does not parse this section.
To actually verify a post-condition in v0.1, add an explicit `assert`
step as the **last numbered step in `## Recipe`** — the assertions
primitive runs there and raises StepFailed on a violation, which the
runner records as `failed`.

The parsed-DSL evaluation of `## Success criteria` (plus the post-vision
re-check described below) is on the v0.2 roadmap.

When that lands: a success criterion that fails after the deterministic
recipe and the vision fallback will cause the skill to return
`{status: failed, ...}` regardless of which steps technically completed.

### `## When NOT to use`
Prose. Documents foot-guns; the matcher can skip skills whose "NOT" conditions match.

### `## Known failures`
Prose list. Documented limitations. Each item should pair with either: (a) a known workaround the user composes, (b) a vision-fallback path, or (c) "explicitly out of scope."

---

## Optional sections (no parser semantics)

These are pure documentation; the runner ignores them.

- `## Example usage` — sample agent prompt where the skill kicks in
- `## Telemetry notes` — what the trace contains for this skill
- `## Related skills` — sibling skill names; matcher may use as composition hints

---

## Vision fallback semantics

When the deterministic recipe fails (a step raises StepFailed):

1. The runner emits `vision_fallback_attempt` to the trace.
2. If a vision adapter is configured AND `metadata.cost_budget.max_vision_calls > 0`, the runner invokes:
   ```
   adapter.describe(screenshot, intent=skill.description, allowed_actions=skill.allowed_tools)
   ```
3. The adapter returns an `Action` (one of the action verbs). The runner executes it.
4. **v0.1 status:** if the action executes without raising, the skill returns success. Looping until a success-criterion predicate is satisfied is on the v0.2 roadmap (paired with the `## Success criteria` DSL evaluator above).
5. If vision is not configured, the skill returns `{status: failed, warnings: ["no_vision_adapter_configured"]}`. The agent decides whether to retry differently.

The vision fallback is deliberately **scoped to a single skill's intent** — not a general "drive the browser" call. This keeps the cost story honest (vision used in <10% of skill executions when recipes are healthy).

---

## What the runner returns

```json
{
  "skill": "dismiss-cookie-banner",
  "version": "0.1.0",
  "status": "success | failed | skipped",
  "deterministic_path": true,           // false if vision was used
  "duration_ms": 207,
  "model_calls": 0,
  "tokens_used": 0,
  "trace_id": "tr_abc123",
  "extracted": {},                       // populated by extract_* verbs
  "steps_executed": 4,
  "failure_reason": null,
  "warnings": []
}
```

The agent uses this to decide next steps; the trace zip captures full detail.

---

## Authoring checklist

A skill is ready to ship when:

- [ ] `name`, `description`, `version`, and `metadata.exercised_on` (≥2 sites) populated
- [ ] Recipe is deterministic-first (no `vision` in happy path)
- [ ] Success criteria has at least one verifiable `assert`
- [ ] Known failures documents at least one (intellectual honesty)
- [ ] Tested against fixture HTML in `tests/fixtures/<skill-name>/`
- [ ] Tested against the ≥2 sites in `metadata.exercised_on`
- [ ] No selectors that look like temporary autogenerated classes (`.css-xz9q4`, etc.)
- [ ] `flake_rate_target` is honest (not aspirationally low)

The scaffold tool (`browser-skills new <name>`, the early scoping) prints this checklist.

---

## Migration / breakage policy

- **Patch bump** (`0.1.0 → 0.1.1`): added a new selector to `try_each`, fixed a wait timing, expanded `known failures`. Backwards compatible.
- **Minor bump** (`0.1.0 → 0.2.0`): added a new optional action verb, added a new sub-skill compose, changed the `extracted` shape additively.
- **Major bump** (`0.1.0 → 1.0.0`): removed a verb, restructured the `extracted` schema, renamed `metadata` keys.

Skills declare a minimum runtime in `metadata.requires_runtime: ">=0.3.0"` if they depend on a new verb. Older runtimes refuse to load them with a clear error.
