"""Matcher tests — score the v1 shipped skills against synthetic PageStates."""

from __future__ import annotations

from pathlib import Path

from browser_skills.matcher import PageState, match
from browser_skills.skill import load_bundle


REPO_SKILLS = Path(__file__).resolve().parent.parent / "skills"


def test_dismiss_cookie_banner_ranks_first_on_banner_page() -> None:
    skills = load_bundle(REPO_SKILLS)
    state = PageState(
        url="https://www.bbc.com/",
        dom_summary="<div id='onetrust-banner-sdk'><button id='onetrust-accept-btn-handler'>Accept</button></div>",
        visible_text_sample="We use cookies to make our service work",
        cookies_present=True,
        is_initial_load=True,
    )
    result = match(skills, state)
    assert result.skills, "expected at least one match"
    names = [s.name for s in result.skills]
    assert "dismiss-cookie-banner" in names
    assert names[0] == "dismiss-cookie-banner"


def test_verify_page_loaded_is_present_on_initial_load() -> None:
    skills = load_bundle(REPO_SKILLS)
    state = PageState(
        url="https://en.wikipedia.org/wiki/Foo",
        dom_summary="<main><h1>Foo</h1></main>",
        is_initial_load=True,
        cookies_present=False,
    )
    result = match(skills, state)
    names = [s.name for s in result.skills]
    assert "verify-page-loaded" in names


def test_matcher_returns_empty_below_threshold() -> None:
    skills = load_bundle(REPO_SKILLS)
    state = PageState(
        url="https://example.test/post-load",
        dom_summary="",
        is_initial_load=False,
        cookies_present=False,
    )
    result = match(skills, state)
    # All wildcards yield very low scores below THRESHOLD
    assert all(s.score < 100 for s in result.skills)


def test_matcher_records_signals() -> None:
    skills = load_bundle(REPO_SKILLS)
    state = PageState(
        url="https://www.theguardian.com/",
        dom_summary="<div data-cookieconsent='banner'><button>Accept all</button></div>",
        cookies_present=True,
        is_initial_load=True,
    )
    result = match(skills, state)
    top = result.skills[0]
    assert top.signals, "expected scoring signals on the top match"
