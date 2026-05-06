"""Parser for the `## Success criteria` SKILL.md section.

C3+C7 step 1: the parser is shipped without behavior change. The
evaluator (step 2) and runner wiring (step 3) ship next.

Coverage:
  - Single-predicate criteria
  - OR-joined predicates
  - Variable-shaped predicates (`$rows is_non_empty_list`)
  - Unknown predicates flagged but accepted
  - Quoted args (selectors with `[role='dialog']` syntax)
  - All v1 bundle skills parse without raising
"""

from __future__ import annotations

from pathlib import Path

from browser_skills.criteria import (
    KNOWN_PREDICATES,
    Criterion,
    Predicate,
    parse_success_criteria,
)
from browser_skills.skill import load_bundle


REPO_SKILLS = Path(__file__).resolve().parent.parent / "skills"


def test_empty_input_returns_empty_list() -> None:
    assert parse_success_criteria("") == []
    assert parse_success_criteria("   \n   ") == []


def test_prose_only_section_returns_empty_list() -> None:
    """Sections that are pure prose (no `- assert` lines) parse to []."""
    text = "This skill always succeeds. See related skills below."
    assert parse_success_criteria(text) == []


def test_single_known_predicate() -> None:
    crit = parse_success_criteria("- assert dom_ready")
    assert len(crit) == 1
    assert len(crit[0].predicates) == 1
    p = crit[0].predicates[0]
    assert p.verb == "dom_ready"
    assert p.unknown is False
    assert p.args == {}


def test_predicate_with_quoted_selector_arg() -> None:
    text = '- assert no_visible_element selector="[role=\'dialog\']"'
    crit = parse_success_criteria(text)
    assert len(crit) == 1
    p = crit[0].predicates[0]
    assert p.verb == "no_visible_element"
    assert p.unknown is False
    # The bracketed selector survives intact (the parser's bracket/quote
    # awareness mirrors the recipe DSL parser).
    assert p.args == {"selector": "[role='dialog']"}


def test_or_joined_predicates() -> None:
    text = '- assert no_visible_element selector="#x" OR no_change_was_needed'
    crit = parse_success_criteria(text)
    assert len(crit) == 1
    assert len(crit[0].predicates) == 2
    assert crit[0].predicates[0].verb == "no_visible_element"
    assert crit[0].predicates[1].verb == "no_change_was_needed"


def test_variable_shaped_predicate() -> None:
    crit = parse_success_criteria("- assert $rows_page_1 is_non_empty_list")
    assert len(crit) == 1
    p = crit[0].predicates[0]
    assert p.verb == "var_is_non_empty_list"
    assert p.args == {"var": "rows_page_1"}
    assert p.unknown is False


def test_unknown_predicate_flagged() -> None:
    """Predicates we don't yet evaluate (aspirational ones like
    `step_indicator_advanced`, `url_changed_since`, etc.) parse to
    Predicate(unknown=True) so the future evaluator can soft-pass them.
    """
    crit = parse_success_criteria("- assert step_indicator_advanced")
    p = crit[0].predicates[0]
    assert p.verb == "step_indicator_advanced"
    assert p.unknown is True


def test_known_predicate_set_is_documented() -> None:
    """The KNOWN_PREDICATES set should at least cover the verbs the
    existing `assert` primitive handles (dom_ready, main_content_
    present, no_visible_element, no_element) plus the OR-sentinel and
    the variable-shaped predicates.
    """
    expected_subset = {
        "dom_ready",
        "main_content_present",
        "no_visible_element",
        "no_element",
        "no_change_was_needed",
        "var_is_set",
        "var_is_unset",
        "var_is_non_empty_list",
    }
    missing = expected_subset - set(KNOWN_PREDICATES)
    assert not missing, f"KNOWN_PREDICATES missing: {missing}"


def test_known_predicates_matches_dispatch_exactly() -> None:
    """C2 (audit-3): KNOWN_PREDICATES is derived from _DISPATCH so the
    parser can never claim a verb is known that the evaluator can't
    handle, and vice versa. Locks the relationship.
    """
    from browser_skills.criteria import _DISPATCH

    assert KNOWN_PREDICATES == frozenset(_DISPATCH.keys()), (
        "KNOWN_PREDICATES and _DISPATCH have drifted; the parser would "
        "either route an evaluable predicate to unknown→soft-pass, or "
        "the evaluator would KeyError on a predicate the parser accepted "
        "as known (caught broadly as None → silent failure)"
    )


def test_multiple_criteria_one_per_line() -> None:
    text = "\n".join([
        "- assert dom_ready",
        "- assert no_visible_element selector=\"#spinner\"",
        "- assert main_content_present",
    ])
    crit = parse_success_criteria(text)
    assert len(crit) == 3
    assert [c.predicates[0].verb for c in crit] == [
        "dom_ready", "no_visible_element", "main_content_present",
    ]


# --- Bundle-wide invariants ----------------------------------------------


def test_every_shipped_skill_success_criteria_parses() -> None:
    """Every SKILL.md in the v1 bundle parses without raising. Some
    predicates are unknown (aspirational); that's recorded with
    `unknown=True`, not an exception.
    """
    bundle = load_bundle(REPO_SKILLS)
    for s in bundle:
        # success_criteria is populated by parse_skill; it should always
        # be a list (possibly empty for skills with no assert lines).
        assert isinstance(s.success_criteria, list), (
            f"{s.name}: success_criteria is not a list"
        )
        for c in s.success_criteria:
            assert isinstance(c, Criterion)
            for p in c.predicates:
                assert isinstance(p, Predicate)


def test_at_least_one_pilot_skill_has_only_known_predicates() -> None:
    """The pilot-skill set (skills we plan to flip
    metadata.evaluate_success_criteria=true on in step 3) must have
    success_criteria entirely composed of KNOWN_PREDICATES. Locks in
    the migration target.
    """
    bundle = load_bundle(REPO_SKILLS)
    by_name = {s.name: s for s in bundle}
    # verify-page-loaded is our cleanest pilot — every assert line uses
    # primitives the v0.1 `assert` verb already implements.
    skill = by_name["verify-page-loaded"]
    assert skill.success_criteria, "verify-page-loaded should have parsed criteria"
    for c in skill.success_criteria:
        for p in c.predicates:
            assert not p.unknown, (
                f"verify-page-loaded uses an unknown predicate "
                f"{p.verb!r}; cannot flip evaluate_success_criteria=true "
                f"until evaluator covers it"
            )
