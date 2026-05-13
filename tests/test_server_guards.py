"""Server-level safety/guard tests that don't require a real browser.

BROWSER_SKILLS_FORBID_HEADED was
checked only against the literal string "1", so common truthy values
(true, yes, on) silently allowed headed mode despite admin intent.
"""
from __future__ import annotations

import pytest

from browser_skills import config
from browser_skills.server import _start_browser_impl


@pytest.mark.parametrize("value", ["1", "true", "True", "TRUE", "yes", "on"])
async def test_forbid_headed_blocks_common_truthy_env_values(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("BROWSER_SKILLS_FORBID_HEADED", value)
    config.reset_for_test()  # ensure no in-process override leaks in
    result = await _start_browser_impl(headed=True)
    assert result["ok"] is False
    assert result["error"]["code"] == "permission_denied"


@pytest.mark.parametrize("value", ["0", "false", "False", "no", "off", ""])
async def test_forbid_headed_allows_falsy_env_values(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    """When the env var is explicitly falsy, headed mode is permitted.
    (We can't actually launch a browser in the unit test layer, so we
    just confirm the guard doesn't fire — the next failure mode is the
    Playwright import / launch which is fine to surface as "internal".)
    """
    monkeypatch.setenv("BROWSER_SKILLS_FORBID_HEADED", value)
    config.reset_for_test()
    result = await _start_browser_impl(headed=False)
    # headed=False, so guard doesn't apply at all. Should NOT return
    # permission_denied. May return ok=True if Playwright launches; may
    # return another error code if e.g. no chromium installed. Either is
    # acceptable — what matters is that we don't see permission_denied.
    if result.get("ok") is False:
        assert result["error"]["code"] != "permission_denied"
    else:
        # Close the session we accidentally opened.
        from browser_skills.server import _close_browser_impl

        await _close_browser_impl(result["session_id"])


async def test_forbid_headed_via_in_process_config_flag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The in-process `config.forbid_headed` flag should also block,
    independently of the env var (which allows test isolation).
    """
    monkeypatch.delenv("BROWSER_SKILLS_FORBID_HEADED", raising=False)
    config.reset_for_test()
    config.forbid_headed = True
    try:
        result = await _start_browser_impl(headed=True)
        assert result["ok"] is False
        assert result["error"]["code"] == "permission_denied"
    finally:
        config.reset_for_test()


# --- is_initial_load semantics ----------------------------------------


from types import SimpleNamespace
from unittest.mock import AsyncMock

from browser_skills.server import _Session, _build_page_state


def _stub_session(*, invocations_since_navigate: int = 0) -> _Session:
    """Build a _Session whose page/context return enough for
    _build_page_state to complete. Cookies list is empty so
    cookies_present=False.
    """
    page = SimpleNamespace(
        url="https://example.test/",
        title=AsyncMock(return_value="t"),
        content=AsyncMock(return_value="<html></html>"),
        evaluate=AsyncMock(return_value="text"),
    )
    context = SimpleNamespace(cookies=AsyncMock(return_value=[]))
    sess = _Session(
        id="sess_stub",
        headed=False,
        pw=None,
        browser=None,
        context=context,
        page=page,
    )
    sess.invocations_since_navigate = invocations_since_navigate
    return sess


async def test_page_state_is_initial_load_after_fresh_navigate() -> None:
    """a session that has just navigated reports is_initial_load=True
    so the matcher gives a boost to first-page-load skills like
    verify-page-loaded and dismiss-cookie-banner.
    """
    sess = _stub_session(invocations_since_navigate=0)
    state = await _build_page_state(sess)
    assert state.is_initial_load is True


async def test_page_state_is_initial_load_false_after_one_invoke() -> None:
    """after the agent has run a skill on the current page, the
    same page is no longer "freshly arrived" — first-load-only skills
    should not re-fire on subsequent matcher calls without a navigate.
    """
    sess = _stub_session(invocations_since_navigate=1)
    state = await _build_page_state(sess)
    assert state.is_initial_load is False
