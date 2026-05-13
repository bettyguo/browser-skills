"""SKILL.md parser tests."""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from browser_skills.skill import SkillParseError, load_bundle, parse_skill


def _write(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "SKILL.md"
    p.write_text(textwrap.dedent(body).lstrip(), encoding="utf-8")
    return p


def test_parses_minimal_skill(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        """
        ---
        name: example
        description: An example skill
        version: 0.1.0
        ---

        # Example

        ## Recipe
        1. wait extra=300ms
        2. click selector="#go"

        ## Success criteria
        - assert dom_ready
        """,
    )
    skill = parse_skill(p)
    assert skill.name == "example"
    assert skill.version == "0.1.0"
    assert len(skill.recipe.steps) == 2
    assert skill.recipe.steps[0].verb == "wait"
    assert skill.recipe.steps[0].args == {"extra": 300}
    assert skill.recipe.steps[1].verb == "click"
    assert skill.recipe.steps[1].args == {"selector": "#go"}


def test_parses_multiline_try_each(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        """
        ---
        name: ex
        description: d
        version: 0.0.1
        ---

        ## Recipe
        1. try_each selectors=[
             "#a",
             "button.b",
             "[aria-label='c']",
           ] action=click on_success=stop timeout=1500ms
        """,
    )
    skill = parse_skill(p)
    assert len(skill.recipe.steps) == 1
    step = skill.recipe.steps[0]
    assert step.verb == "try_each"
    assert step.args["selectors"] == ["#a", "button.b", "[aria-label='c']"]
    assert step.args["action"] == "click"
    assert step.args["on_success"] == "stop"
    assert step.args["timeout"] == 1500


def test_rejects_missing_frontmatter(tmp_path: Path) -> None:
    p = tmp_path / "bad.md"
    p.write_text("# no frontmatter\n", encoding="utf-8")
    with pytest.raises(SkillParseError):
        parse_skill(p)


def test_rejects_missing_required_field(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        """
        ---
        name: ex
        version: 0.0.1
        ---
        body
        """,
    )
    with pytest.raises(SkillParseError, match="description"):
        parse_skill(p)


def test_coerces_durations_ints_lists_bools(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        """
        ---
        name: ex
        description: d
        version: 0.0.1
        ---

        ## Recipe
        1. fancy a=10 b=10ms c=2s d=true e=false f=[1, 2, 3] g="hi there"
        """,
    )
    skill = parse_skill(p)
    args = skill.recipe.steps[0].args
    assert args["a"] == 10
    assert args["b"] == 10
    assert args["c"] == 2000
    assert args["d"] is True
    assert args["e"] is False
    assert args["f"] == ["1", "2", "3"]
    assert args["g"] == "hi there"


def test_loads_bundle_from_repo_skills_dir() -> None:
    """The two reference skills shipped in skills/ must parse cleanly."""
    repo_skills = Path(__file__).resolve().parent.parent / "skills"
    bundle = load_bundle(repo_skills)
    names = {s.name for s in bundle}
    assert "dismiss-cookie-banner" in names
    assert "verify-page-loaded" in names
    for s in bundle:
        assert s.version
        assert s.description
        assert s.recipe.steps, f"{s.name} parsed with zero recipe steps"
