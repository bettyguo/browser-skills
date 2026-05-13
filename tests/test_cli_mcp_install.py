"""Tests for `browser-skills mcp install`.

T5 partial (CLI tests for mcp install) + Doc5 enforcement: the install
command should not emit HTTP-transport MCP stanzas until Bearer-token
auth is implemented. Until then, users can only install the stdio
stanza, which is trusted by virtue of being a child process of their
client.
"""
from __future__ import annotations

import json

from typer.testing import CliRunner

from browser_skills.cli import app


runner = CliRunner()


def test_mcp_install_print_emits_stdio_stanza() -> None:
    """The default `--print` output must be the stdio stanza —
    runnable by Claude Desktop, Cursor, Codex, Continue, etc., with
    no exposed network surface.
    """
    result = runner.invoke(app, ["mcp", "install", "print"])
    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    server = payload["mcpServers"]["browser-skills"]
    assert "command" in server, (
        "mcp install --print should emit a stdio stanza (command + args), "
        f"got: {server!r}"
    )
    assert server["command"] == "browser-skills"
    assert "mcp" in server["args"] and "serve" in server["args"]


def test_mcp_install_print_does_not_emit_unauthenticated_http() -> None:
    """until HTTP-transport Bearer-token auth is implemented, the
    install command must not emit an HTTP stanza — that would write
    a client config pointing at an MCP server with NO authentication.
    The `mcp serve --transport=streamable-http` flag still exists for
    advanced users who run behind their own auth (Tailscale, Cloudflare
    Access, etc.), but it is not advertised through `install`.
    """
    result = runner.invoke(app, ["mcp", "install", "print"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    server = payload["mcpServers"]["browser-skills"]
    assert "url" not in server, (
        "mcp install must not emit an `url` field (HTTP stanza) until "
        "Bearer-token auth is implemented (the early scoping roadmap Doc5)."
    )


def test_mcp_install_rejects_unknown_target() -> None:
    result = runner.invoke(app, ["mcp", "install", "made-up-client"])
    assert result.exit_code != 0
    assert "Unknown target" in result.stdout


# --- File-write target tests ---


def _patch_home(monkeypatch, home: object) -> None:
    """Redirect os.path.expanduser('~') to a tmp_path for the duration
    of the test, regardless of platform. The Path('~').expanduser()
    code path uses os.path.expanduser internally.
    """
    home_str = str(home)
    monkeypatch.setattr("os.path.expanduser", lambda p: home_str if p == "~" else p)


def test_mcp_install_cursor_writes_stdio_stanza_to_correct_path(
    tmp_path, monkeypatch
) -> None:
    """Cursor uses a platform-agnostic config at ~/.cursor/mcp.json.
    `mcp install cursor` should create that file with our stdio stanza.
    """
    _patch_home(monkeypatch, tmp_path)
    result = runner.invoke(app, ["mcp", "install", "cursor"])
    assert result.exit_code == 0, result.stdout

    cfg_path = tmp_path / ".cursor" / "mcp.json"
    assert cfg_path.exists(), f"mcp install cursor did not create {cfg_path}"
    payload = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert "mcpServers" in payload
    assert "browser-skills" in payload["mcpServers"]
    stanza = payload["mcpServers"]["browser-skills"]
    assert stanza["command"] == "browser-skills"
    assert stanza["args"] == ["mcp", "serve", "--transport", "stdio"]


def test_mcp_install_preserves_unrelated_mcp_servers(tmp_path, monkeypatch) -> None:
    """The user may already have other MCP servers configured (e.g.,
    playwright-mcp, filesystem-mcp). `mcp install` must add our stanza
    alongside, not blow theirs away.
    """
    _patch_home(monkeypatch, tmp_path)
    cfg_dir = tmp_path / ".cursor"
    cfg_dir.mkdir()
    cfg_path = cfg_dir / "mcp.json"
    cfg_path.write_text(
        json.dumps(
            {
                "mcpServers": {
                    "other-server": {"command": "other", "args": ["run"]},
                    "yet-another": {"url": "http://localhost:9000"},
                }
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["mcp", "install", "cursor"])
    assert result.exit_code == 0, result.stdout

    after = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert set(after["mcpServers"]) == {"other-server", "yet-another", "browser-skills"}
    # Verify the pre-existing entries weren't mutated.
    assert after["mcpServers"]["other-server"] == {"command": "other", "args": ["run"]}
    assert after["mcpServers"]["yet-another"] == {"url": "http://localhost:9000"}


def test_mcp_install_is_idempotent(tmp_path, monkeypatch) -> None:
    """Running `mcp install cursor` twice in a row must succeed and
    produce the same file content the second time (no duplicated
    keys, no error).
    """
    _patch_home(monkeypatch, tmp_path)

    first = runner.invoke(app, ["mcp", "install", "cursor"])
    assert first.exit_code == 0

    second = runner.invoke(app, ["mcp", "install", "cursor"])
    assert second.exit_code == 0

    cfg_path = tmp_path / ".cursor" / "mcp.json"
    parsed = json.loads(cfg_path.read_text(encoding="utf-8"))
    # Exactly one browser-skills entry, regardless of how many times we ran.
    assert list(parsed["mcpServers"]).count("browser-skills") == 1


def test_mcp_install_refuses_to_overwrite_invalid_json(
    tmp_path, monkeypatch
) -> None:
    """If the existing config isn't valid JSON, we MUST NOT silently
    rewrite it — we'd lose whatever was there (comments, hand edits,
    JSON5 quirks). The current behavior is to error with exit_code 2.
    """
    _patch_home(monkeypatch, tmp_path)
    cfg_dir = tmp_path / ".cursor"
    cfg_dir.mkdir()
    cfg_path = cfg_dir / "mcp.json"
    cfg_path.write_text("this is not json", encoding="utf-8")

    result = runner.invoke(app, ["mcp", "install", "cursor"])
    assert result.exit_code != 0
    # File contents unchanged.
    assert cfg_path.read_text(encoding="utf-8") == "this is not json"


def test_mcp_install_does_not_accept_transport_http_in_v0_2() -> None:
    """`--transport=http` would emit an unauthenticated HTTP MCP
    stanza into the user's client config. Until Bearer-token auth is
    implemented (the early scoping roadmap), the `--transport` option must not
    accept `http` — typer should reject the value at parse time, OR
    the command should error out, OR there should be no --transport
    option at all (the v0.2 choice). Any of these is acceptable; what
    is NOT acceptable is silently writing an http stanza.
    """
    result = runner.invoke(app, ["mcp", "install", "print", "--transport", "http"])
    if result.exit_code == 0:
        # If somehow the command succeeded, the stanza must not be
        # an http one.
        payload = json.loads(result.stdout)
        server = payload["mcpServers"]["browser-skills"]
        assert "url" not in server, (
            "mcp install --transport=http should not emit an `url` "
            "stanza (unauthenticated HTTP) in v0.2"
        )
