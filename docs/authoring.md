# Authoring a skill

> Hands-on walkthrough. We build a hypothetical `dismiss-survey-popup`
> skill from scratch and ship it to the bundle. ~20 minutes.

## Step 0 — Does the skill belong?

A v1 skill ships if it scores ≥3 of these (from ):

1. **Frequency** — the boring step happens on >50% of agent sessions
2. **Friction cost** — without a skill, vision-only agents burn ≥1 model call + visible latency
3. **Generality** — the pattern is recognizable across ≥10 sites without per-site logic
4. **Determinism** — ≥80% can be handled by selectors + DOM heuristics
5. **Demo legibility** — observable in the trace

If it doesn't score 3+, it's a *user-authored* skill that lives in
their fork or a community-packs repo, not core.

## Step 1 — Create the directory

```bash
mkdir skills/dismiss-survey-popup
cd skills/dismiss-survey-popup
```

## Step 2 — Write the SKILL.md

Start with the canonical frontmatter:

```yaml
---
name: dismiss-survey-popup
description: Dismisses "How was your experience?" survey popups (Qualtrics, Hotjar Polls, ForeSee). Defaults to "No thanks" / close.
version: 0.1.0
allowed-tools: [wait, try_each, press_key]
metadata:
  applies_to: any-website
  url_patterns: ["*"]
  dom_markers:
    - "[class*='survey' i]"
    - "[id*='qualtrics' i]"
    - "[class*='hotjar' i]"
  flake_rate_target: 0.10
  exercised_on: [bbc-home, nytimes-home]
  cost_budget:
    deterministic_only: false
    max_vision_calls: 1
---
```

Then the markdown body. Every section has a purpose:

```markdown
# Dismiss Survey Popup

## When to invoke
After 5-10 seconds on a page, a survey banner appears asking the user to
rate the page. Dismiss-controls: small "x", "No thanks" link, or Escape.

## Recipe
1. wait extra=300ms
2. try_each selectors=[
     "[class*='qualtrics' i] button[aria-label*='close' i]",
     "[class*='survey' i] button:has-text('No thanks')",
     "[id*='hotjar' i] button.close",
   ] action=click on_success=stop timeout=1000ms
3. press_key key=Escape

## Success criteria
- assert no_visible_element selector="[class*='survey' i]" OR no_change_was_needed

## When NOT to use
- The user *wants* to take the survey.

## Known failures
- Surveys served from cross-origin iframes can't be clicked through.
- Some surveys re-attach after dismissal; v0.1 dismisses once.
```

## Step 3 — Add fixtures

Local HTML, big enough to exercise your `try_each` selectors:

```bash
mkdir -p tests/fixtures/dismiss-survey-popup
$EDITOR tests/fixtures/dismiss-survey-popup/page.html
```

Sample:

```html
<!DOCTYPE html>
<html><body>
  <div class='qualtrics-survey-popup' role='dialog'>
    <p>How was your experience?</p>
    <button aria-label='close'>×</button>
  </div>
</body></html>
```

## Step 4 — Test

```bash
browser-skills test dismiss-survey-popup
```

Expected output:

```
SUCCESS dismiss-survey-popup
deterministic_path: True
duration_ms:        420
steps_executed:     3
model_calls:        0
```

If you get `FAILED`:
- Increase the timeout on `try_each`
- Add a more specific selector to the list
- Check that the markup in your fixture matches what real sites use

## Step 5 — Update the bundle invariants

Add the new skill name to `tests/test_bundle_completeness.py::EXPECTED_V1_SKILLS`
(only if you're upgrading it to a v1-shipped skill).

Run the test suite:

```bash
pytest tests/
```

All green? You're done.

## Step 6 — Open a PR

- Include a paragraph in the PR description explaining what real sites
  this targets and why the deterministic-vs-vision differentiation matters here.
- The PR template asks for the 5-criterion score; be honest. A 3/5 skill
  ships; a 1/5 skill is "interesting, lives in your fork."
- DCO sign-off: `git commit -s`.

## Common authoring mistakes

| Anti-pattern | Why bad | Better |
|---|---|---|
| Selectors like `.css-xz9q4` | Auto-generated, breaks on next build | Use ARIA roles, data-* attrs, semantic classes |
| `flake_rate_target: 0.01` everywhere | Dishonest; CI will flag the lie | Use a realistic target; publish measured rates |
| Vision in the happy path | Wedge collapse | Vision is the fallback. The recipe is the path. |
| Long prose in `## Recipe` | The runner won't parse it | Numbered verb steps; prose belongs in `## When to invoke` |
| `exercised_on: []` | Won't pass `test_bundle_completeness` | List ≥2 real benchmark sites (or document the exception) |
| `:has-text('Confirm and proceed')` for the dismiss button | Wrong intent | This skill's posture is DISMISS; pick "No thanks" / close, not accept |

## Skill anatomy reference

See [docs/skill-recipe-format.md](skill-recipe-format.md) for the full
DSL — action verbs, selector syntax, variable scope, success criteria
language, vision-fallback semantics, versioning rules.
