"""Tests for the form primitives (fill, press_key, select_option,
screenshot_verb).

none of these had unit tests,
so the v1 skills built on them (fill-multi-step-form, login-flow,
date-picker-widget, searchable-dropdown, dismiss-newsletter-popup,
exit-tracking-popup) were end-to-end-untested at the primitive layer.
"""
from __future__ import annotations

import pytest

from browser_skills.primitives import REGISTRY, StepFailed
from tests.conftest import FakeElement, FakePage


async def test_fill_writes_value_to_input(fake_page: FakePage) -> None:
    fake_page.add(FakeElement(tag="input", attrs={"id": "username"}))
    result = await REGISTRY["fill"](
        fake_page, selector="#username", value="alice"
    )
    assert result["selector"] == "#username"
    assert result["value_length"] == len("alice")
    assert fake_page.fill_log == [("#username", "alice")]


async def test_fill_records_value_length_not_value(fake_page: FakePage) -> None:
    """The primitive's return dict deliberately omits the raw value —
    that's what the trace will record. Trace redaction (S5) handles the
    args, but the primitive's `detail` should also not echo back the
    sensitive value.
    """
    fake_page.add(FakeElement(tag="input", attrs={"type": "password"}))
    result = await REGISTRY["fill"](
        fake_page,
        selector="input[type='password']",
        value="hunter2",
    )
    assert "value" not in result, "fill primitive's detail must not echo value"
    assert result["value_length"] == 7


async def test_fill_raises_on_no_match(fake_page: FakePage) -> None:
    with pytest.raises(StepFailed):
        await REGISTRY["fill"](
            fake_page, selector="#missing", value="x", timeout=100
        )


async def test_press_key_dispatches_keydown(fake_page: FakePage) -> None:
    result = await REGISTRY["press_key"](fake_page, key="Escape")
    assert result["key"] == "Escape"
    assert fake_page.key_log == [(None, "Escape")]


async def test_press_key_on_specific_selector(fake_page: FakePage) -> None:
    fake_page.add(FakeElement(tag="input", attrs={"id": "search"}))
    await REGISTRY["press_key"](fake_page, key="Enter", selector="#search")
    assert fake_page.key_log == [("#search", "Enter")]


async def test_select_option_requires_value_or_label(fake_page: FakePage) -> None:
    fake_page.add(FakeElement(tag="select", attrs={"id": "country"}))
    with pytest.raises(StepFailed, match="value= or label="):
        await REGISTRY["select_option"](fake_page, selector="#country")


async def test_select_option_picks_by_value(fake_page: FakePage) -> None:
    fake_page.add(FakeElement(tag="select", attrs={"id": "country"}))
    result = await REGISTRY["select_option"](
        fake_page, selector="#country", value="US"
    )
    assert result["selected_value"] == "US"
    assert fake_page.select_log == [("#country", "US")]


async def test_select_option_raises_on_not_a_select(fake_page: FakePage) -> None:
    fake_page.add(FakeElement(tag="div", attrs={"id": "fake-dropdown"}))
    with pytest.raises(StepFailed, match="not_a_select"):
        await REGISTRY["select_option"](
            fake_page, selector="#fake-dropdown", value="x"
        )


async def test_screenshot_verb_returns_zero_bytes_when_page_has_no_screenshot(
    fake_page: FakePage,
) -> None:
    """FakePage does not implement screenshot. The screenshot verb must
    degrade gracefully (this is also why C2 mattered — the real wrapper
    DOES implement screenshot, and the verb is meant to find it).
    """
    result = await REGISTRY["screenshot"](fake_page)
    assert result["bytes"] == 0
