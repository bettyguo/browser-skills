"""Primitive-level tests against FakePage."""

from __future__ import annotations

import pytest

from browser_skills.primitives import REGISTRY, StepFailed
from tests.conftest import FakeElement, FakePage


async def test_wait_sleeps_briefly(fake_page: FakePage) -> None:
    result = await REGISTRY["wait"](fake_page, extra=10)
    assert result == {"slept_ms": 10}


async def test_wait_rejects_negative(fake_page: FakePage) -> None:
    with pytest.raises(StepFailed):
        await REGISTRY["wait"](fake_page, extra=-1)


async def test_wait_for_dom_ready_ok(fake_page: FakePage) -> None:
    result = await REGISTRY["wait_for_dom_ready"](fake_page, timeout=1000)
    assert result["state"] == "domcontentloaded"


async def test_click_dismisses_visible_element(fake_page: FakePage) -> None:
    el = FakeElement(tag="button", attrs={"id": "onetrust-accept-btn-handler"})
    fake_page.add(el)
    await REGISTRY["click"](fake_page, selector="#onetrust-accept-btn-handler")
    assert "#onetrust-accept-btn-handler" in fake_page.click_log
    assert not el.visible  # post-click


async def test_click_fails_on_missing(fake_page: FakePage) -> None:
    with pytest.raises(StepFailed):
        await REGISTRY["click"](fake_page, selector="#missing", timeout=100)


async def test_try_each_short_circuits_on_first_hit(fake_page: FakePage) -> None:
    fake_page.add(
        FakeElement(tag="button", attrs={"class": "cc-allow"}, text="Allow"),
        FakeElement(
            tag="button",
            attrs={"id": "onetrust-accept-btn-handler"},
            text="Accept",
        ),
    )
    result = await REGISTRY["try_each"](
        fake_page,
        selectors=["#onetrust-accept-btn-handler", ".cc-allow"],
        action="click",
        on_success="stop",
    )
    assert result["matched_any"] is True
    # Only one click happened — first selector wins.
    assert len(result["selectors_hit"]) == 1
    assert result["selectors_hit"][0] == "#onetrust-accept-btn-handler"
    assert len(fake_page.click_log) == 1


async def test_try_each_returns_no_match_when_all_miss(fake_page: FakePage) -> None:
    result = await REGISTRY["try_each"](
        fake_page,
        selectors=["#a", "#b"],
        action="click",
        on_success="stop",
        timeout=100,
    )
    assert result["matched_any"] is False
    assert result["selectors_hit"] == []


async def test_assert_no_visible_element_passes_when_absent(fake_page: FakePage) -> None:
    result = await REGISTRY["assert"](
        fake_page, no_visible_element="#nope"
    )
    assert result["ok"] is True


async def test_assert_no_visible_element_fails_when_visible(fake_page: FakePage) -> None:
    fake_page.add(FakeElement(tag="div", attrs={"id": "still-here"}))
    with pytest.raises(StepFailed):
        await REGISTRY["assert"](fake_page, no_visible_element="#still-here")


async def test_assert_no_visible_element_passes_when_hidden(fake_page: FakePage) -> None:
    el = FakeElement(tag="div", attrs={"id": "hidden"}, visible=False)
    fake_page.add(el)
    result = await REGISTRY["assert"](fake_page, no_visible_element="#hidden")
    assert result["ok"] is True


async def test_assert_dom_ready(fake_page: FakePage) -> None:
    result = await REGISTRY["assert"](fake_page, condition="dom_ready")
    assert result["ok"] is True


async def test_assert_main_content_present(fake_page: FakePage) -> None:
    fake_page.add(FakeElement(tag="main"))
    result = await REGISTRY["assert"](fake_page, condition="main_content_present")
    assert result["ok"] is True


async def test_assert_unknown_condition_raises_not_soft_passes(
    fake_page: FakePage,
) -> None:
    """C6: previously, an unrecognized `assert condition=X` returned
    `{ok: True, warning: 'unrecognized; treated as soft-pass'}`, which
    silently passes assertions the runner doesn't understand — masking
    real failures. The primitive must raise StepFailed for unknown
    conditions so the runner records the step as failed.
    """
    with pytest.raises(StepFailed, match="unknown condition"):
        await REGISTRY["assert"](fake_page, condition="is_logged_in")


async def test_extract_text_binds_variable(fake_page: FakePage) -> None:
    fake_page.add(FakeElement(tag="h1", attrs={"id": "title"}, text="Hello"))
    vars: dict[str, object] = {}
    result = await REGISTRY["extract_text"](
        fake_page, selector="#title", into="$headline", vars=vars
    )
    assert result["value"] == "Hello"
    assert vars["headline"] == "Hello"


async def test_extract_text_strict_raises_on_no_match(fake_page: FakePage) -> None:
    """Default behavior: a no-match is a step failure."""
    from browser_skills.primitives import StepFailed

    with pytest.raises(StepFailed):
        await REGISTRY["extract_text"](fake_page, selector="#never")


async def test_extract_text_optional_returns_none_on_no_match(fake_page: FakePage) -> None:
    """`optional=true` is the detect-* pattern: absence is the desired
    success case, the variable is set to None so the agent can branch.
    """
    vars: dict[str, object] = {"sentinel": "untouched"}
    result = await REGISTRY["extract_text"](
        fake_page, selector="#never", into="$probe", optional=True, vars=vars
    )
    assert result["matched"] is False
    assert result["value"] is None
    assert vars["probe"] is None
    assert vars["sentinel"] == "untouched"


async def test_try_each_skips_absent_selectors_quickly(fake_page: FakePage) -> None:
    """Regression test for the perf bug found on Hacker News: try_each
    must probe before attempting to click, so 15 try_each selectors
    against a page with no banner complete in milliseconds, not 20+
    seconds. We assert the probe path via the `selectors_hit` shape and
    by passing a deliberately long action timeout that would dominate
    if the probe weren't happening.
    """
    fake_page.add(FakeElement(tag="div", attrs={"id": "irrelevant"}))
    result = await REGISTRY["try_each"](
        fake_page,
        selectors=[f"#missing-{i}" for i in range(10)],
        action="click",
        on_success="stop",
        timeout=30000,
    )
    assert result["matched_any"] is False
    assert result["selectors_hit"] == []
    # No clicks attempted — all selectors were probed-absent.
    assert fake_page.click_log == []
