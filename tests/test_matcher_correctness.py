"""Per-site matcher correctness assertions.

previously, matcher tests asserted presence of skills above
threshold, not whether the *right* skill was picked. The hand-tuned
scoring rules in matcher.py are exactly the thing most likely to
drift; this file catches drift.

Each test synthesizes the PageState a real visit would produce
(documented by the benchmark site's `skills:` hint in
benchmarks/sites.yaml), then asserts the matcher's top pick. Together
the tests document the contract: "on a banner-bearing page, the
banner skill outranks the modal skill"; "on a captcha page, captcha
detect outranks every other applicable skill"; etc.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from browser_skills.matcher import PageState, match
from browser_skills.skill import Skill, load_bundle

REPO_SKILLS = Path(__file__).resolve().parent.parent / "skills"


@pytest.fixture(scope="module")
def bundle() -> list[Skill]:
    return load_bundle(REPO_SKILLS)


# Each case: (test name, dom_summary, expected_top_1, also_in_top_3)
# Crafted from the markers shipped in each skill's metadata.dom_markers.
CASES = [
    pytest.param(
        "<div id='onetrust-banner-sdk'><button id='onetrust-accept-btn-handler'>Accept</button></div>",
        "dismiss-cookie-banner",
        {"dismiss-cookie-banner", "verify-page-loaded"},
        True,  # cookies_present
        True,  # is_initial_load
        id="onetrust_cookie_banner",
    ),
    pytest.param(
        "<div class='newsletter-modal'><button class='newsletter-dismiss'>×</button></div>",
        "dismiss-newsletter-popup",
        {"dismiss-newsletter-popup"},
        False,
        False,
        id="newsletter_popup",
    ),
    pytest.param(
        "<div class='g-recaptcha' data-sitekey='abc'></div>",
        "detect-captcha",
        {"detect-captcha"},
        False,
        True,
        id="recaptcha_present",
    ),
    pytest.param(
        "<iframe src='https://challenges.cloudflare.com/cdn-cgi/challenge'></iframe>",
        "detect-captcha",
        {"detect-captcha"},
        False,
        True,
        id="cloudflare_turnstile",
    ),
    pytest.param(
        "<div role='dialog' aria-modal='true'><button>Close</button></div>",
        "handle-modal-dialog",
        {"handle-modal-dialog"},
        False,
        True,
        id="generic_modal",
    ),
    pytest.param(
        "<main><table><thead><tr><th>id</th></tr></thead></table></main>",
        # Note: extract-table-pagination's dom_markers list contains the
        # literal string '<table' (no closing angle, matches `<table>`
        # and `<table class='x'>` both). On an initial-load page with
        # cookies_present, verify-page-loaded co-occurs above threshold;
        # the test just asserts extract-table-pagination is in the top 3.
        None,
        {"extract-table-pagination"},
        False,
        True,
        id="table_extract_target",
    ),
]


@pytest.mark.parametrize("dom_summary,expected_top,must_include,cookies,initial", CASES)
def test_matcher_picks_correct_top_skill(
    bundle: list[Skill],
    dom_summary: str,
    expected_top: str | None,
    must_include: set[str],
    cookies: bool,
    initial: bool,
) -> None:
    """For each curated page-shape, the matcher's choice must satisfy
    the documented expectation:

      - When `expected_top` is set, the matcher's #1 result must
        match it exactly.
      - `must_include` is a set of skills required to appear in the
        top-3, regardless of position.
    """
    state = PageState(
        url="https://example.test/synthetic",
        dom_summary=dom_summary,
        visible_text_sample="",
        cookies_present=cookies,
        is_initial_load=initial,
    )
    result = match(bundle, state)
    names = [m.name for m in result.skills]
    if expected_top is not None:
        assert names, f"matcher returned no skills for {dom_summary!r}"
        assert names[0] == expected_top, (
            f"expected top match {expected_top!r}, got {names[0]!r}; "
            f"full ranking: {names[:5]}"
        )
    missing = must_include - set(names[:3])
    assert not missing, (
        f"top-3 missing required skill(s) {missing}; got {names[:3]}"
    )


def test_cookie_banner_outranks_modal_when_both_apply(bundle: list[Skill]) -> None:
    """When a page has both a cookie-banner marker and a generic modal
    marker, dismiss-cookie-banner must win — it's the more specific
    skill, and the matcher's hand-tuned bump for is_initial_load +
    cookies_present should put it on top. If the modal skill ever
    leapfrogs (e.g., someone tightens cookie-banner's markers), that's
    a real bug.
    """
    state = PageState(
        url="https://example.test/",
        dom_summary=(
            "<div role='dialog' aria-modal='true' "
            "id='onetrust-banner-sdk'><button id='onetrust-accept-btn-handler'>"
            "Accept</button></div>"
        ),
        cookies_present=True,
        is_initial_load=True,
    )
    result = match(bundle, state)
    names = [m.name for m in result.skills]
    cookie_pos = names.index("dismiss-cookie-banner") if "dismiss-cookie-banner" in names else 999
    modal_pos = names.index("handle-modal-dialog") if "handle-modal-dialog" in names else 999
    assert cookie_pos < modal_pos, (
        f"cookie-banner should outrank generic modal; "
        f"got cookie@{cookie_pos}, modal@{modal_pos}, ranking: {names[:5]}"
    )


def test_captcha_outranks_cookie_when_both_apply(bundle: list[Skill]) -> None:
    """When captcha is detected, it MUST appear above any other skill
    in the ranking. A captcha-blocked page where the agent first tries
    to dismiss a cookie banner is wasted budget; we want captcha
    detection surfaced first so the agent can stop.
    """
    state = PageState(
        url="https://example.test/",
        dom_summary=(
            "<div id='onetrust-banner-sdk'></div>"
            "<div class='g-recaptcha'></div>"
        ),
        cookies_present=True,
        is_initial_load=True,
    )
    result = match(bundle, state)
    names = [m.name for m in result.skills]
    assert names[0] == "detect-captcha", (
        f"detect-captcha must outrank everything else; "
        f"ranking: {names[:5]}"
    )
