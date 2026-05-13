"""Version invariants — keep pyproject, package, and CHANGELOG in sync."""
from __future__ import annotations

import re
from pathlib import Path

import tomllib

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_package_version_matches_pyproject() -> None:
    """`browser_skills.__version__` must match `[project] version =`
    in pyproject.toml. The two drift apart silently if not checked.
    """
    with (REPO_ROOT / "pyproject.toml").open("rb") as f:
        pyproject = tomllib.load(f)
    pyproject_version = pyproject["project"]["version"]

    from browser_skills import __version__

    assert __version__ == pyproject_version, (
        f"browser_skills.__version__ = {__version__!r} but "
        f"pyproject.toml has version = {pyproject_version!r}"
    )


def test_changelog_has_entry_for_current_version() -> None:
    """A version bump without a changelog entry is the kind of thing
    that always slips through review.
    """
    from browser_skills import __version__

    changelog = (REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    # Match `## [0.2.0]` or `## [0.2.0] —` etc.
    header_re = re.compile(rf"^##\s*\[{re.escape(__version__)}\]", re.MULTILINE)
    assert header_re.search(changelog), (
        f"CHANGELOG.md is missing an entry for v{__version__}"
    )
