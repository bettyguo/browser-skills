"""Tests for the PlaywrightPage adapter — the wrapper that sits between
real Playwright Pages and the project's PageLike protocol.

Regression test for Phase 1 finding C2: the wrapper was missing
`screenshot` and `query_selector` methods, causing vision fallback and
the screenshot recipe verb to silently fail when running through the
MCP server (which always wraps the real page).
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from browser_skills.adapters.playwright_raw import PlaywrightPage


def _fake_real_page(**overrides: Any) -> Any:
    """Build a SimpleNamespace that mimics enough of a real Playwright Page
    for the wrapper-delegation tests. Methods are AsyncMock so we can
    assert calls.
    """
    defaults = dict(
        url="https://example.test/",
        click=AsyncMock(return_value=None),
        fill=AsyncMock(return_value=None),
        wait_for_load_state=AsyncMock(return_value=None),
        wait_for_selector=AsyncMock(return_value=object()),
        evaluate=AsyncMock(return_value=42),
        screenshot=AsyncMock(return_value=b"PNG-BYTES"),
        query_selector=AsyncMock(return_value=object()),
    )
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


async def test_screenshot_delegates_to_real_page() -> None:
    """C2: the wrapper must expose `screenshot` so vision fallback's
    _capture(page, scope) can locate it via getattr.
    """
    real = _fake_real_page()
    wrapper = PlaywrightPage(real)
    assert hasattr(wrapper, "screenshot"), (
        "PlaywrightPage missing `screenshot`; vision fallback will receive "
        "empty image bytes when running via the MCP server."
    )
    out = await wrapper.screenshot(full_page=False)
    assert out == b"PNG-BYTES"
    real.screenshot.assert_awaited_once_with(full_page=False)


async def test_query_selector_delegates_to_real_page() -> None:
    """C2: the wrapper must expose `query_selector` so the `screenshot`
    recipe verb (form.py) can scope captures to a specific selector.
    """
    real = _fake_real_page()
    wrapper = PlaywrightPage(real)
    assert hasattr(wrapper, "query_selector"), (
        "PlaywrightPage missing `query_selector`; element-scoped screenshots "
        "fall back to viewport capture silently."
    )
    out = await wrapper.query_selector(".target")
    assert out is not None
    real.query_selector.assert_awaited_once_with(".target")


async def test_existing_delegations_still_work() -> None:
    """Sanity: the methods that previously worked still do."""
    real = _fake_real_page()
    wrapper = PlaywrightPage(real)
    await wrapper.click("#go", timeout=1000)
    real.click.assert_awaited_once_with("#go", timeout=1000)
    await wrapper.fill("input", "hello", timeout=2000)
    real.fill.assert_awaited_once_with("input", "hello", timeout=2000)
    result = await wrapper.evaluate("() => 42")
    assert result == 42
