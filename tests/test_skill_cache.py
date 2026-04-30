"""Skill-cache invalidation.

D3: editing a SKILL.md while the MCP server was running had no effect
because `_load_skills_cached` cached forever. This test verifies that
the cache auto-invalidates when a SKILL.md is modified.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from browser_skills.server import _load_skills_cached, _reset_skills_cache


@pytest.fixture
def temp_skills_dir(tmp_path: Path) -> Path:
    """Two trivial skills in a throwaway directory."""
    for name, version in (("alpha", "0.1.0"), ("beta", "0.1.0")):
        sub = tmp_path / name
        sub.mkdir()
        (sub / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: d\nversion: {version}\n---\n\n"
            "## Recipe\n1. wait extra=1ms\n",
            encoding="utf-8",
        )
    _reset_skills_cache()
    yield tmp_path
    _reset_skills_cache()


def test_cache_reloads_when_skill_md_modified(temp_skills_dir: Path) -> None:
    """Modifying any SKILL.md under the bundle must cause the next
    `_load_skills_cached` call to pick up the change.
    """
    first = _load_skills_cached(temp_skills_dir)
    versions_before = {s.name: s.version for s in first}
    assert versions_before == {"alpha": "0.1.0", "beta": "0.1.0"}

    # Modify alpha's version and bump its mtime to "now" so it's strictly
    # newer than the cache. On fast filesystems the previous write may
    # already share our timestamp, so bump explicitly.
    alpha = temp_skills_dir / "alpha" / "SKILL.md"
    new_now = time.time() + 5
    alpha.write_text(
        "---\nname: alpha\ndescription: d\nversion: 0.1.1\n---\n\n"
        "## Recipe\n1. wait extra=1ms\n",
        encoding="utf-8",
    )
    os.utime(alpha, (new_now, new_now))

    second = _load_skills_cached(temp_skills_dir)
    versions_after = {s.name: s.version for s in second}
    assert versions_after["alpha"] == "0.1.1", (
        "skill cache did not reload after SKILL.md modification"
    )


def test_cache_reloads_when_skill_added(temp_skills_dir: Path) -> None:
    """Adding a new skill directory should also invalidate the cache."""
    _load_skills_cached(temp_skills_dir)
    new_dir = temp_skills_dir / "gamma"
    new_dir.mkdir()
    new_md = new_dir / "SKILL.md"
    new_md.write_text(
        "---\nname: gamma\ndescription: d\nversion: 0.1.0\n---\n\n"
        "## Recipe\n1. wait extra=1ms\n",
        encoding="utf-8",
    )
    # Bump the new file's mtime to be strictly newer than the cache.
    future = time.time() + 5
    os.utime(new_md, (future, future))

    second = _load_skills_cached(temp_skills_dir)
    names = {s.name for s in second}
    assert "gamma" in names


def test_cache_does_not_reload_when_unchanged(temp_skills_dir: Path) -> None:
    """A second call without any FS change must return the SAME list
    object (cheap; no reparse). Reparsing every call would defeat the
    purpose of a cache.
    """
    a = _load_skills_cached(temp_skills_dir)
    b = _load_skills_cached(temp_skills_dir)
    assert a is b, "cache returned a fresh list when nothing changed"
