"""Runner + criteria evaluator end-to-end.

this work: skills that opt in via `metadata.evaluate_success_criteria:
true` get their parsed criteria evaluated after the recipe completes.
Decidable False criteria turn the run into status=failed even if every
recipe step succeeded.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from browser_skills.runner import Runner
from browser_skills.skill import parse_skill
from tests.conftest import FakeElement, FakePage


def _write_skill(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "SKILL.md"
    p.write_text(textwrap.dedent(body).lstrip(), encoding="utf-8")
    return p


# --- Opt-in skill with a failing criterion ------------------------------


async def test_opt_in_skill_fails_when_criterion_decidably_false(tmp_path: Path) -> None:
    """The recipe completes (one no-op wait) but the criterion asks
    that a present-and-visible element NOT be visible. Without the
    opt-in flag the runner would report success; with it, the runner
    must report failed.
    """
    skill_md = _write_skill(
        tmp_path,
        """
        ---
        name: ex-criteria-fail
        description: d
        version: 0.1.0
        metadata:
          evaluate_success_criteria: true
        ---

        ## Recipe
        1. wait extra=1ms

        ## Success criteria
        - assert no_visible_element selector="#stays-here"
        """,
    )
    skill = parse_skill(skill_md)
    page = FakePage()
    page.add(FakeElement(tag="div", attrs={"id": "stays-here"}))
    runner = Runner()
    result = await runner.execute(skill, page)
    assert result.status == "failed"
    assert result.failure_reason is not None
    assert "no_visible_element" in result.failure_reason or "stays-here" in result.failure_reason


async def test_opt_in_skill_passes_when_criterion_satisfied(tmp_path: Path) -> None:
    """Same recipe; same criterion text; this time the element isn't
    on the page so `no_visible_element` is True → criterion passes →
    runner reports success.
    """
    skill_md = _write_skill(
        tmp_path,
        """
        ---
        name: ex-criteria-pass
        description: d
        version: 0.1.0
        metadata:
          evaluate_success_criteria: true
        ---

        ## Recipe
        1. wait extra=1ms

        ## Success criteria
        - assert no_visible_element selector="#never-present"
        """,
    )
    skill = parse_skill(skill_md)
    page = FakePage()
    runner = Runner()
    result = await runner.execute(skill, page)
    assert result.status == "success"


async def test_opt_in_skill_with_or_clause_uses_or_semantics(tmp_path: Path) -> None:
    """The classic dismiss-cookie-banner pattern: `no_visible_element
    selector="#x" OR no_change_was_needed`. The page still has the
    element, but the OR-sentinel keeps the criterion passing.
    """
    skill_md = _write_skill(
        tmp_path,
        """
        ---
        name: ex-or-clause
        description: d
        version: 0.1.0
        metadata:
          evaluate_success_criteria: true
        ---

        ## Recipe
        1. wait extra=1ms

        ## Success criteria
        - assert no_visible_element selector="#still-here" OR no_change_was_needed
        """,
    )
    skill = parse_skill(skill_md)
    page = FakePage()
    page.add(FakeElement(tag="div", attrs={"id": "still-here"}))
    runner = Runner()
    result = await runner.execute(skill, page)
    assert result.status == "success"


async def test_skill_without_opt_in_ignores_criteria(tmp_path: Path) -> None:
    """Skill without `evaluate_success_criteria: true`: success is "every
    recipe step succeeded." The shipped bundle is opt-out so this path
    matters.
    """
    skill_md = _write_skill(
        tmp_path,
        """
        ---
        name: ex-no-opt-in
        description: d
        version: 0.1.0
        ---

        ## Recipe
        1. wait extra=1ms

        ## Success criteria
        - assert no_visible_element selector="#stays-here"
        """,
    )
    skill = parse_skill(skill_md)
    page = FakePage()
    page.add(FakeElement(tag="div", attrs={"id": "stays-here"}))
    runner = Runner()
    result = await runner.execute(skill, page)
    # Without opt-in, the criterion is ignored despite being decidably False.
    assert result.status == "success"


# --- Soft-pass via warning for unknown predicates -----------------------


async def test_opt_in_skill_with_only_unknown_predicates_soft_passes(
    tmp_path: Path,
) -> None:
    """A skill opts in but its single criterion uses an aspirational
    predicate the evaluator doesn't know. The runner must NOT fail —
    soft-pass + warning so we don't break opt-in skills whose criteria
    drift into aspirational verbs.
    """
    skill_md = _write_skill(
        tmp_path,
        """
        ---
        name: ex-soft-pass
        description: d
        version: 0.1.0
        metadata:
          evaluate_success_criteria: true
        ---

        ## Recipe
        1. wait extra=1ms

        ## Success criteria
        - assert step_indicator_advanced
        """,
    )
    skill = parse_skill(skill_md)
    page = FakePage()
    runner = Runner()
    result = await runner.execute(skill, page)
    assert result.status == "success"
    # The warning must surface so authors notice their criterion isn't
    # actually being evaluated.
    assert any("step_indicator_advanced" in w for w in result.warnings)


# --- Pilot skills (verify-page-loaded, extract-table-pagination) --------


async def test_criteria_fire_after_vision_rescues_recipe(tmp_path: Path) -> None:
    """the  concern was that vision fallback
    could silently mask criteria failures — vision succeeds, runner
    reports success, criteria never get checked.

    After this work + this verification: when an opt-in skill's
    recipe fails, vision fallback runs, and EVEN IF the adapter
    "rescues" by executing some action, the post-vision criteria still
    decide the final status. If the criteria are decidably-false, the
    skill returns failed despite vision's claim of success.
    """
    from browser_skills import config
    from browser_skills.primitives.vision_fallback import VisionAction

    # Stub vision adapter that returns a no-op `wait` action (page
    # state remains unchanged after vision "rescue").
    class _Adapter:
        async def describe(self, *, image_b64, intent, allowed_actions, context):
            return VisionAction(verb="wait", args={"extra": 1}, rationale="t1", tokens_in=2, tokens_out=1)

    config.set_vision_adapter(_Adapter())

    skill_md = _write_skill(
        tmp_path,
        """
        ---
        name: ex-t1-vision-and-criteria
        description: d
        version: 0.1.0
        metadata:
          evaluate_success_criteria: true
          cost_budget:
            max_vision_calls: 1
        ---

        ## Recipe
        1. click selector="#never" timeout=50ms

        ## Success criteria
        - assert no_visible_element selector="#stays-visible"
        """,
    )
    skill = parse_skill(skill_md)
    page = FakePage()
    # The criterion's target element is present + visible. Vision
    # "rescues" the recipe (it runs a no-op wait), but the page state
    # still violates the criterion.
    page.add(FakeElement(tag="div", attrs={"id": "stays-visible"}))

    runner = Runner()
    result = await runner.execute(skill, page)

    # Vision did fire (model_calls=1, deterministic_path=False).
    assert result.model_calls == 1, (
        "vision adapter wasn't invoked even though the recipe step failed "
        "and a budget was available"
    )
    assert result.deterministic_path is False
    # …but the post-vision criterion check still ran and failed.
    assert result.status == "failed", (
        "vision rescue masked a real criteria failure — C7 regression"
    )
    assert result.failure_reason is not None
    assert "stays-visible" in result.failure_reason or "no_visible_element" in result.failure_reason


async def test_evaluator_error_surfaces_as_runner_warning(tmp_path: Path) -> None:
    """if a predicate evaluator raises (page.evaluate
    crashes, JS payload is malformed, etc.), the error must surface in
    SkillResult.warnings instead of being silently swallowed.
    """
    skill_md = _write_skill(
        tmp_path,
        """
        ---
        name: ex-s2
        description: d
        version: 0.1.0
        metadata:
          evaluate_success_criteria: true
        ---

        ## Recipe
        1. wait extra=1ms

        ## Success criteria
        - assert dom_ready
        """,
    )
    skill = parse_skill(skill_md)

    # Fake page whose evaluate raises for the dom_ready check.
    class _Page(FakePage):
        async def evaluate(self, expression, *args):
            if "document.readyState" in expression:
                raise RuntimeError("simulated JS crash")
            return await super().evaluate(expression, *args)

    page = _Page()
    runner = Runner()
    result = await runner.execute(skill, page)

    # The criterion was undecidable; runner soft-passes the run as
    # success, but a warning must point at the failed evaluator.
    assert any("criterion eval error" in w for w in result.warnings), (
        f"expected an eval-error warning in result.warnings; got: {result.warnings}"
    )
    assert any("dom_ready" in w for w in result.warnings)


async def test_pilot_skill_verify_page_loaded_has_opt_in_flag() -> None:
    """Lock in that verify-page-loaded is the pilot. Step 3 flipped
    its `evaluate_success_criteria` to true; this test catches
    accidental flag removal.
    """
    repo_skills = Path(__file__).resolve().parent.parent / "skills"
    skill = parse_skill(repo_skills / "verify-page-loaded" / "SKILL.md")
    assert skill.evaluate_success_criteria is True


async def test_pilot_skill_extract_table_pagination_has_opt_in_flag() -> None:
    repo_skills = Path(__file__).resolve().parent.parent / "skills"
    skill = parse_skill(repo_skills / "extract-table-pagination" / "SKILL.md")
    assert skill.evaluate_success_criteria is True
