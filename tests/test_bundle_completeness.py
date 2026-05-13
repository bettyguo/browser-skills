"""Bundle-level invariants. These tests run after every PR — if a new
skill is added or an existing one is modified, the bundle must still
satisfy the M2-shipping contract documented in docs/skill-recipe-format.md.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from browser_skills.skill import Skill, load_bundle

REPO_SKILLS = Path(__file__).resolve().parent.parent / "skills"


# v1 ships these skills; the suite enforces that they remain present.
EXPECTED_V1_SKILLS = {
    "dismiss-cookie-banner",
    "dismiss-newsletter-popup",
    "handle-modal-dialog",
    "verify-page-loaded",
    "fill-multi-step-form",
    "upload-download-file",
    "extract-table-pagination",
    "handle-infinite-scroll",
    "search-and-filter",
    "pagination-next-page",
    "date-picker-widget",
    "searchable-dropdown",
    "login-flow",
    "detect-captcha",
    "exit-tracking-popup",
}


@pytest.fixture(scope="module")
def bundle() -> list[Skill]:
    return load_bundle(REPO_SKILLS)


def test_v1_shipped_skills_all_present(bundle: list[Skill]) -> None:
    names = {s.name for s in bundle}
    missing = EXPECTED_V1_SKILLS - names
    assert not missing, f"missing v1 skills: {sorted(missing)}"


def test_every_skill_declares_semver_version(bundle: list[Skill]) -> None:
    semver_re = re.compile(r"^\d+\.\d+\.\d+(-[\w.]+)?$")
    bad = [s.name for s in bundle if not semver_re.match(s.version)]
    assert not bad, f"non-semver versions: {bad}"


def test_every_skill_has_at_least_one_recipe_step(bundle: list[Skill]) -> None:
    bad = [s.name for s in bundle if not s.recipe.steps]
    assert not bad, f"skills with empty recipes: {bad}"


def test_every_skill_metadata_exercised_on_has_two_or_more_sites(
    bundle: list[Skill],
) -> None:
    # Skills where shipping with 1 fixture is the correct posture (documented).
    SINGLE_FIXTURE_OK = {
        "detect-captcha",   # only one ToS-friendly captcha benchmark site
        "login-flow",       # only the-internet sandbox in v1 (auth-loaded sites are intentionally limited)
    }
    bad: list[str] = []
    for s in bundle:
        exercised = s.metadata.get("exercised_on", [])
        if not isinstance(exercised, list) or len(exercised) < 2:
            if s.name in SINGLE_FIXTURE_OK and len(exercised) >= 1:
                continue
            bad.append(s.name)
    assert not bad, (
        "skills with <2 exercised_on entries (see docs/skill-recipe-format.md "
        f"authoring checklist): {bad}"
    )


def test_no_skill_uses_vision_in_recipe_happy_path(bundle: list[Skill]) -> None:
    """Per : deterministic-first. Vision is only allowed as fallback,
    never as a recipe step. If a recipe uses the `vision` verb directly,
    the value collapses (the agent might as well call vision itself).
    """
    bad: list[str] = []
    for s in bundle:
        for step in s.recipe.steps:
            if step.verb == "vision":
                bad.append(f"{s.name}:line{step.line_in_source}")
    assert not bad, f"skills using vision in recipe steps: {bad}"


def test_detect_captcha_has_max_vision_calls_zero(bundle: list[Skill]) -> None:
    """Per the ethics posture: detect-captcha must never invoke
    the vision adapter — that would be a step toward solving.
    """
    skill = next((s for s in bundle if s.name == "detect-captcha"), None)
    assert skill is not None
    assert skill.max_vision_calls == 0, (
        "detect-captcha must not call vision (cost_budget.max_vision_calls=0)"
    )
