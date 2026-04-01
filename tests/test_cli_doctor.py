"""`browser-skills doctor` smoke tests.

F8: the doctor command exists and produces useful output for the
common diagnostic scenarios (working install, missing chromium,
missing fastmcp).
"""

from __future__ import annotations

from typer.testing import CliRunner

from browser_skills.cli import app


runner = CliRunner()


def test_doctor_runs_and_lists_key_checks() -> None:
    """The command runs to completion and reports on each of the
    documented categories. Exit code can be 0 or 1 depending on the
    local env; we just check structure.
    """
    result = runner.invoke(app, ["doctor"])
    # The output must mention every documented diagnostic category, so
    # users can grep for what they're trying to debug.
    out = result.stdout.lower()
    for marker in ("python", "playwright", "fastmcp", "skills directory"):
        assert marker in out, f"doctor output missing {marker!r}: {result.stdout!r}"


def test_doctor_redacts_mcp_token(monkeypatch) -> None:
    """The BROWSER_SKILLS_MCP_TOKEN env var contains a credential.
    `doctor` must echo its presence without revealing the value.
    """
    monkeypatch.setenv("BROWSER_SKILLS_MCP_TOKEN", "secret-token-do-not-leak")
    result = runner.invoke(app, ["doctor"])
    assert "secret-token-do-not-leak" not in result.stdout, (
        "doctor leaked $BROWSER_SKILLS_MCP_TOKEN into stdout"
    )
    assert "[REDACTED]" in result.stdout or "REDACTED" in result.stdout
