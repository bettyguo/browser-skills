---
name: fill-multi-step-form
description: Fills a multi-step form (stepper wizard) by routing labeled fields to values from `vars`, clicking "Next" between steps, and submitting at the end. Pairs with the `searchable-dropdown` and `date-picker-widget` skills for compound widgets.
version: 0.1.0
allowed-tools: [wait_for_dom_ready, wait_for_selector, fill, select_option, click, wait, assert]
metadata:
  applies_to: any-website
  url_patterns: ["*"]
  dom_markers:
    - "<form"
    - "role='form'"
    - "[role='progressbar']"
    - ".stepper"
    - "step-indicator"
  flake_rate_target: 0.15
  exercised_on:
    - httpbin-forms
    - the-internet-herokuapp
  cost_budget:
    deterministic_only: false
    max_vision_calls: 3
---

# Fill Multi-Step Form

## When to invoke

The page has a form spread across multiple steps (Typeform, Calendly, hotel
checkout, multi-page job applications, etc.). The agent has the values to fill
in `vars` keyed by either field-`name`, field-`id`, or label text.

The matcher runs this skill when the DOM has a `<form>` plus any
step-indicator marker. Without step-indicators, the simpler
single-step form pattern (`fill` primitive calls authored by the agent
directly) usually suffices.

## Recipe

1. wait_for_dom_ready timeout=5s
2. wait_for_selector selector="form, [role='form']" state=visible timeout=5s
3. fill selector="input[name='name'], input[id*='name' i][type='text']" value="$vars.name"
4. fill selector="input[type='email'], input[name*='email' i]" value="$vars.email"
5. click selector="button:has-text('Next'), button:has-text('Continue'), button[type='submit']" timeout=2s
6. wait extra=400ms

## Success criteria

- assert no_visible_element selector="[role='alert'][aria-invalid='true']"
- assert step_indicator_advanced

## Notes

The recipe above is the minimum-viable scaffolding. Real forms vary
widely; agents are expected to compose `fill` primitives directly when
the field set is fully known up front. This skill is most useful when:

- The field set is partially unknown until later steps render
- Validation errors must be detected and recovered (handled by the
  agent on `failed` return)

## When NOT to use

- Login forms — use `login-flow`.
- Forms inside a captcha-protected flow — `detect-captcha` first.

## Known failures

- **Hidden fields with same name as visible fields:** the selector
  picks the wrong one. Workaround: use an `id` selector instead.
- **Steps that conditionally show fields based on earlier answers:**
  v0.1 doesn't handle dynamic form structure. Agent must invoke the
  skill once per step.
- **Drag-and-drop fields, signature widgets:** out of scope.
