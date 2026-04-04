"""Tests for browser_skills._chromium.chromium_install_path.

Regression check for P3: the chromium-detect logic used to be
duplicated between cli.doctor and tests/test_integration_playwright.
Now in one place — these tests assert (a) the helper exists and
returns a sensible type, and (b) neither caller still inlines the
subprocess + regex pattern.
"""

from __future__ import annotations

from pathlib import Path


def test_helper_exists_and_returns_path_or_none() -> None:
    from browser_skills._chromium import chromium_install_path

    result = chromium_install_path()
    # Either Chromium is installed (Path that exists) or not (None).
    assert result is None or (isinstance(result, Path) and result.exists())


def test_no_duplicate_chromium_dry_run_in_callers() -> None:
    """The whole point of P3 is one source of truth. Lint-style assertion
    that neither cli.py nor the integration-test module still inlines
    the `playwright install --dry-run chromium` subprocess pattern.
    """
    repo_root = Path(__file__).resolve().parent.parent
    cli_text = (repo_root / "src" / "browser_skills" / "cli.py").read_text(
        encoding="utf-8"
    )
    test_text = (
        repo_root / "tests" / "test_integration_playwright.py"
    ).read_text(encoding="utf-8")
    # The string "install --dry-run" should appear only via the helper
    # (which doesn't live in either of these files).
    assert "install --dry-run" not in cli_text, (
        "cli.py still inlines `playwright install --dry-run chromium` — "
        "should call browser_skills._chromium.chromium_install_path"
    )
    assert "install --dry-run" not in test_text, (
        "test_integration_playwright still inlines the dry-run subprocess "
        "— should call browser_skills._chromium.chromium_install_path"
    )
