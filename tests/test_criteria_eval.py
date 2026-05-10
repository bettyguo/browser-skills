"""Tests for the success-criteria evaluator.

C3+C7 step 2: the evaluator turns each parsed Criterion into a pass /
fail / soft-pass verdict against a live page + vars map. Step 3
wires the evaluator into the runner with metadata opt-in.
"""

from __future__ import annotations

import pytest

from browser_skills.criteria import (
    Criterion,
    Predicate,
    evaluate_criterion,
    evaluate_predicate,
    parse_success_criteria,
)
from tests.conftest import FakeElement, FakePage


# --- Individual predicates ----------------------------------------------


async def test_dom_ready_passes_on_complete_page(fake_page: FakePage) -> None:
    p = Predicate(verb="dom_ready")
    assert await evaluate_predicate(fake_page, {}, p) is True


async def test_dom_ready_fails_when_not_complete(fake_page: FakePage) -> None:
    fake_page.ready_state = "loading"
    p = Predicate(verb="dom_ready")
    assert await evaluate_predicate(fake_page, {}, p) is False


async def test_no_visible_element_true_when_absent(fake_page: FakePage) -> None:
    p = Predicate(verb="no_visible_element", args={"selector": "#never"})
    assert await evaluate_predicate(fake_page, {}, p) is True


async def test_no_visible_element_false_when_visible(fake_page: FakePage) -> None:
    fake_page.add(FakeElement(tag="div", attrs={"id": "still-here"}))
    p = Predicate(verb="no_visible_element", args={"selector": "#still-here"})
    assert await evaluate_predicate(fake_page, {}, p) is False


async def test_no_visible_element_true_when_hidden(fake_page: FakePage) -> None:
    fake_page.add(FakeElement(tag="div", attrs={"id": "hidden"}, visible=False))
    p = Predicate(verb="no_visible_element", args={"selector": "#hidden"})
    assert await evaluate_predicate(fake_page, {}, p) is True


async def test_no_change_was_needed_is_always_true_sentinel(fake_page: FakePage) -> None:
    """The OR-sentinel that lets authors write
    `assert no_visible_element OR no_change_was_needed`.
    """
    p = Predicate(verb="no_change_was_needed")
    assert await evaluate_predicate(fake_page, {}, p) is True


async def test_var_is_set_recognizes_bound_variable(fake_page: FakePage) -> None:
    vars = {"rows_page_1": [{"a": 1}]}
    p = Predicate(verb="var_is_set", args={"var": "rows_page_1"})
    assert await evaluate_predicate(fake_page, vars, p) is True


async def test_var_is_set_false_when_missing(fake_page: FakePage) -> None:
    p = Predicate(verb="var_is_set", args={"var": "not_bound"})
    assert await evaluate_predicate(fake_page, {}, p) is False


async def test_var_is_set_false_when_none(fake_page: FakePage) -> None:
    """When a primitive binds the var to None (e.g., detect-captcha's
    optional extract_text), `var_is_set` reports False — useful for
    "did we detect anything?"
    """
    p = Predicate(verb="var_is_set", args={"var": "captcha_marker"})
    assert await evaluate_predicate(fake_page, {"captcha_marker": None}, p) is False


async def test_var_is_non_empty_list_true_when_populated(fake_page: FakePage) -> None:
    p = Predicate(verb="var_is_non_empty_list", args={"var": "rows"})
    assert await evaluate_predicate(fake_page, {"rows": [{}, {}]}, p) is True


async def test_var_is_non_empty_list_false_when_empty(fake_page: FakePage) -> None:
    p = Predicate(verb="var_is_non_empty_list", args={"var": "rows"})
    assert await evaluate_predicate(fake_page, {"rows": []}, p) is False


async def test_unknown_predicate_returns_none(fake_page: FakePage) -> None:
    """Unknown predicates are NOT a hard failure — the runner will
    treat None as soft-pass and emit a warning.
    """
    p = Predicate(verb="step_indicator_advanced", unknown=True)
    assert await evaluate_predicate(fake_page, {}, p) is None


async def test_evaluator_error_recorded_via_error_sink(fake_page: FakePage) -> None:
    """S2 (audit-3): when a predicate evaluator raises (e.g., a future
    refactor renames an expected arg), the exception used to be
    silently caught → None. Now the caller can pass an `error_sink`
    list and get back a one-line "verb: ErrorType: message" entry, so
    the runner surfaces the error to the SkillResult.warnings instead
    of swallowing it.
    """
    # Construct a page whose `evaluate` raises — simulates a JS error
    # in a real Playwright session.
    class _BrokenPage:
        url = "https://example.test/"

        async def evaluate(self, *args, **kwargs):
            raise RuntimeError("synthetic JS error")

    page = _BrokenPage()
    errors: list[str] = []
    p = Predicate(verb="dom_ready")  # known predicate; will hit the broken evaluate
    result = await evaluate_predicate(page, {}, p, error_sink=errors)
    assert result is None
    assert errors, "evaluator error was swallowed without recording in error_sink"
    assert errors[0].startswith("dom_ready: "), errors[0]
    assert "synthetic JS error" in errors[0]


# --- OR-semantics at the Criterion level --------------------------------


async def test_or_passes_when_any_predicate_passes(fake_page: FakePage) -> None:
    """The classic dismiss-cookie-banner pattern:
    `no_visible_element OR no_change_was_needed`. If the element IS
    still visible (recipe failed to dismiss), the criterion should
    still PASS because of the always-true sentinel on the right.
    """
    fake_page.add(FakeElement(tag="div", attrs={"id": "banner-still-here"}))
    crit = Criterion(
        predicates=[
            Predicate(verb="no_visible_element", args={"selector": "#banner-still-here"}),
            Predicate(verb="no_change_was_needed"),
        ],
        raw_text="...",
    )
    assert await evaluate_criterion(fake_page, {}, crit) is True


async def test_or_fails_only_when_every_decidable_predicate_fails(
    fake_page: FakePage,
) -> None:
    """If both OR-operands are decidable and both False, criterion fails."""
    fake_page.add(FakeElement(tag="div", attrs={"id": "a"}))
    fake_page.add(FakeElement(tag="div", attrs={"id": "b"}))
    crit = Criterion(
        predicates=[
            Predicate(verb="no_visible_element", args={"selector": "#a"}),
            Predicate(verb="no_visible_element", args={"selector": "#b"}),
        ],
        raw_text="...",
    )
    assert await evaluate_criterion(fake_page, {}, crit) is False


async def test_all_unknown_predicates_returns_none_soft_pass(
    fake_page: FakePage,
) -> None:
    """A criterion of entirely-unknown predicates is undecidable —
    soft-pass (None) so the runner doesn't fail a skill whose
    criteria are aspirational documentation.
    """
    crit = Criterion(
        predicates=[
            Predicate(verb="step_indicator_advanced", unknown=True),
            Predicate(verb="new_rows_appended", unknown=True),
        ],
        raw_text="...",
    )
    assert await evaluate_criterion(fake_page, {}, crit) is None


# --- End-to-end: parse a real skill's criteria and evaluate --------------


async def test_evaluate_dismiss_cookie_banner_criterion_against_real_text(
    fake_page: FakePage,
) -> None:
    """Parse the exact text dismiss-cookie-banner uses, evaluate it
    against a FakePage where the banner is gone — should pass.
    """
    text = (
        '- assert no_visible_element selector="#onetrust-banner-sdk" '
        "OR no_change_was_needed"
    )
    [crit] = parse_success_criteria(text)
    # Page has no banner element; both branches would pass on their own.
    assert await evaluate_criterion(fake_page, {}, crit) is True
