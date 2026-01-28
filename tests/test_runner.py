"""End-to-end runner tests: parse a SKILL.md, execute against FakePage,
assert a SkillResult with the expected status and deterministic_path.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from browser_skills import config
from browser_skills.primitives.vision_fallback import VisionAction
from browser_skills.runner import Runner
from browser_skills.skill import parse_skill
from tests.conftest import FakeElement, FakePage


def _write(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "SKILL.md"
    p.write_text(textwrap.dedent(body).lstrip(), encoding="utf-8")
    return p


async def test_runner_executes_minimal_recipe(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        """
        ---
        name: ex
        description: d
        version: 0.1.0
        ---

        ## Recipe
        1. wait extra=5ms
        2. wait_for_dom_ready timeout=1s
        """,
    )
    skill = parse_skill(p)
    runner = Runner()
    page = FakePage()
    result = await runner.execute(skill, page)
    assert result.status == "success"
    assert result.deterministic_path is True
    assert result.model_calls == 0
    assert result.steps_executed == 2


async def test_runner_executes_dismiss_cookie_banner_against_fake_dom(tmp_path: Path) -> None:
    """Execute the real dismiss-cookie-banner SKILL.md against a fake page
    that has a OneTrust-style banner. Asserts deterministic success.
    """
    repo_skills = Path(__file__).resolve().parent.parent / "skills"
    skill = parse_skill(repo_skills / "dismiss-cookie-banner" / "SKILL.md")

    page = FakePage()
    page.add(
        FakeElement(
            tag="div",
            attrs={"id": "onetrust-banner-sdk"},
            text="We use cookies",
        ),
        FakeElement(
            tag="button",
            attrs={"id": "onetrust-accept-btn-handler"},
            text="Accept All Cookies",
        ),
    )

    runner = Runner()
    result = await runner.execute(skill, page)
    assert result.status == "success", result.failure_reason
    assert result.deterministic_path is True
    assert "#onetrust-accept-btn-handler" in page.click_log


async def test_runner_fails_cleanly_when_no_recipe_match(tmp_path: Path) -> None:
    p = _write(
        tmp_path,
        """
        ---
        name: ex
        description: d
        version: 0.1.0
        metadata:
          cost_budget:
            max_vision_calls: 0
        ---

        ## Recipe
        1. click selector="#never" timeout=50ms
        """,
    )
    skill = parse_skill(p)
    page = FakePage()
    runner = Runner()
    result = await runner.execute(skill, page)
    assert result.status == "failed"
    assert "warnings" in result.__dict__
    assert result.deterministic_path is True  # no vision was attempted


class _FakeVisionAdapter:
    async def describe(self, *, image_b64, intent, allowed_actions, context):
        return VisionAction(
            verb="wait",
            args={"extra": 1},
            rationale="fallback dummy action",
            tokens_in=10,
            tokens_out=5,
        )


async def test_runner_invokes_vision_fallback_when_configured(tmp_path: Path) -> None:
    config.set_vision_adapter(_FakeVisionAdapter())
    p = _write(
        tmp_path,
        """
        ---
        name: ex
        description: a thing
        version: 0.1.0
        metadata:
          cost_budget:
            max_vision_calls: 1
        ---

        ## Recipe
        1. click selector="#never" timeout=50ms
        """,
    )
    skill = parse_skill(p)
    page = FakePage()
    runner = Runner()
    result = await runner.execute(skill, page)
    assert result.status == "success"
    assert result.deterministic_path is False
    assert result.model_calls == 1
    assert result.tokens_used == 15


async def test_runner_does_not_invoke_vision_when_budget_is_zero(tmp_path: Path) -> None:
    config.set_vision_adapter(_FakeVisionAdapter())
    p = _write(
        tmp_path,
        """
        ---
        name: ex
        description: d
        version: 0.1.0
        metadata:
          cost_budget:
            max_vision_calls: 0
        ---

        ## Recipe
        1. click selector="#never" timeout=50ms
        """,
    )
    skill = parse_skill(p)
    page = FakePage()
    runner = Runner()
    result = await runner.execute(skill, page)
    assert result.status == "failed"
    assert result.model_calls == 0
