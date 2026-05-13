# Matcher design

> Given a page state (URL + DOM summary), which of the bundle's skills are applicable, and in what order should the agent consider them?

## Why a matcher exists

Browser agents in 2026 (Claude 4.7, GPT-5.5 native CUA, Gemini Computer Control) can already pick skills out of a bundle if the descriptions are good. So why not just dump 15 SKILL.md descriptions and let the model pick?

Two reasons:

1. **Cost.** Asking the model "which of these 15 skills applies?" on every page is a model call. At scale (the demo monitors 5 sites; a real automation might hit 500) those calls add up.
2. **Stability.** Model-driven selection drifts between runs. The same page produces different skill picks under different model versions / temperatures. The matcher gives us a deterministic baseline.

The matcher is **a hint**, not a gate. The final decision stays with the agent. If the agent picks a skill the matcher didn't suggest, we run it anyway — and we log the disagreement so we can improve the matcher.

## Inputs

```python
class PageState:
    url: str
    title: Optional[str]
    dom_summary: str            # max 4kb; truncated outerHTML + landmark roles
    visible_text_sample: str    # max 2kb; visible text in viewport
    cookies_present: bool
    is_initial_load: bool       # True if this is the first interaction after navigate()
```

The runner is responsible for building `PageState`. Skills can request their own state extension via a recipe `# Pre-match probe` block (rare; v1 doesn't need it).

## Algorithm

Pure-Python heuristic scoring, no model call.

```
for skill in bundle:
    score = 0
    # 1. URL-pattern match
    if any(fnmatch(state.url, pattern) for pattern in skill.metadata.url_patterns):
        score += 100
    # 2. DOM-marker match
    for marker in skill.metadata.dom_markers:
        if marker in state.dom_summary:        # naive substring; CSS-parsed in v2
            score += 50
    # 3. Page-state signals
    if skill.name == "verify-page-loaded" and state.is_initial_load:
        score += 30
    if skill.name == "dismiss-cookie-banner" and state.cookies_present and state.is_initial_load:
        score += 30
    if skill.name == "detect-captcha" and "captcha" in state.dom_summary.lower():
        score += 80
    # 4. Description keyword match (fallback when frontmatter is light)
    if any(kw in skill.description.lower() for kw in extract_keywords(state)):
        score += 10
    # 5. Penalize over-applicability
    if skill.metadata.applies_to == "any-website":
        score *= 0.9  # mild penalty to prefer specific skills
    results.append((skill, score))

results.sort(key=lambda t: t[1], reverse=True)
return [r for r in results if r[1] > THRESHOLD]
```

`THRESHOLD = 20`. Below that, the skill isn't applicable enough to recommend.

## Output

```python
class MatchResult:
    skills: list[SkillMatch]      # sorted by score desc, top 10
    rationale: str                # 1-paragraph "why these"
    matched_in_ms: int
```

```python
class SkillMatch:
    name: str
    score: float
    confidence: Literal["high", "medium", "low"]  # bucketed from score
    signals: list[str]            # which scoring rules fired
```

## Versions

**v1 (the early scoping M3)** — the heuristic above. Hand-tuned scoring rules per skill type. ~50 lines of Python.

**v2 (post-launch)** — embedding similarity over `(page features, skill description)`. Probably better recall on novel sites; needs an embedding model on hand. Defer until v1 is in production and we have telemetry on miss cases.

**v3 (speculative)** — learned scorer trained on user-confirmed picks. Only worth it if v2 plateaus.

## What the matcher does NOT do

- **Doesn't pick exactly one skill.** Returns ranked candidates; agent decides.
- **Doesn't run the skill.** Pure prediction.
- **Doesn't call any model.** Pure Python, sub-millisecond.
- **Doesn't memoize across page navigations.** Each page is a fresh evaluation. Page-state caching is a runner concern, not a matcher concern.

## Testing strategy

- **Unit:** for each v1 skill, a fixture PageState that *should* match and one that *shouldn't*. Run the matcher; assert the score boundary.
- **Integration:** open each benchmark site, build PageState, run matcher, snapshot the result. Snapshot updates require human review (catches selector-marker rot).
- **Adversarial:** PageStates where two skills both look applicable (cookie banner + newsletter popup co-occurring). Assert ordering is sensible.

## Failure-mode catalog

| Failure | Cause | Mitigation |
|---|---|---|
| Matcher returns empty list on a page with a clear cookie banner | DOM markers don't cover the banner's selector style | Add the missing selector to skill's `dom_markers`; bump skill patch version |
| Wrong skill ranked first | Score tie or marker overlap | Tighten markers; add penalty rules; if persistent, document and let agent override |
| Matcher takes >50ms | DOM summary too large or too many skills | Truncate DOM summary harder; pre-compile selectors at bundle load |

## Telemetry

Each matcher call emits to the trace:

```json
{
  "event": "match",
  "url": "https://bbc.com",
  "candidates": [
    {"skill": "dismiss-cookie-banner", "score": 180, "signals": ["dom_marker", "is_initial_load", "cookies_present"]},
    {"skill": "verify-page-loaded", "score": 30, "signals": ["is_initial_load"]}
  ],
  "matched_in_ms": 4
}
```

The weekly benchmark cron compares matcher outputs across runs and opens issues if recall drops by >5pp on any site.
