"""browser-skills CLI.

Commands:
  list                       — show all skills in the bundle
  info <name>                — parsed details for one skill
  version                    — print __version__
  new <name>                 — scaffold skills/<name>/SKILL.md (+ fixture)
  test <name>                — run a skill against tests/fixtures/<name>/page.html
  mcp serve                  — run the MCP server (stdio or streamable-http)
  mcp install <target>       — write an MCP stanza into a client config file
"""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from browser_skills.skill import load_bundle, parse_skill, SkillParseError


_VALID_SKILL_NAME_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")

app = typer.Typer(
    name="browser-skills",
    help="Reusable site-pattern recipes for browser-using agents.",
    no_args_is_help=True,
    add_completion=False,
)
mcp_app = typer.Typer(name="mcp", help="MCP server commands.", no_args_is_help=True)
app.add_typer(mcp_app, name="mcp")
console = Console()


def _default_skills_dir() -> Path:
    """Locate the bundled skills/ directory.

    Resolution order:
      1. $BROWSER_SKILLS_DIR if set
      2. ./skills relative to cwd (development checkout)
      3. <package>/_skills (installed wheel)
    """
    import os

    env = os.environ.get("BROWSER_SKILLS_DIR")
    if env:
        return Path(env)
    cwd_skills = Path.cwd() / "skills"
    if cwd_skills.is_dir():
        return cwd_skills
    return Path(__file__).parent / "_skills"


@app.command(name="list")
def list_skills(
    skills_dir: Path = typer.Option(  # noqa: B008
        None, "--skills-dir", help="Override skills/ directory location."
    ),
) -> None:
    """List all skills in the bundle."""
    sd = skills_dir or _default_skills_dir()
    if not sd.is_dir():
        console.print(f"[red]No skills directory at {sd}[/red]")
        raise typer.Exit(code=1)
    skills = load_bundle(sd)
    if not skills:
        console.print(f"[yellow]No skills found under {sd}[/yellow]")
        return
    table = Table(title=f"Skills in {sd}", show_header=True)
    table.add_column("name", style="cyan")
    table.add_column("version", style="green")
    table.add_column("description")
    table.add_column("steps", justify="right")
    for s in skills:
        table.add_row(s.name, s.version, s.description, str(len(s.recipe.steps)))
    console.print(table)


@app.command()
def info(
    name: str = typer.Argument(..., help="Skill name (matches the directory name)."),
    skills_dir: Path = typer.Option(  # noqa: B008
        None, "--skills-dir", help="Override skills/ directory location."
    ),
    json_out: bool = typer.Option(False, "--json", help="Emit JSON instead of pretty output."),
) -> None:
    """Show parsed details for a single skill."""
    sd = skills_dir or _default_skills_dir()
    path = sd / name / "SKILL.md"
    if not path.exists():
        console.print(f"[red]No SKILL.md at {path}[/red]")
        raise typer.Exit(code=1)
    try:
        skill = parse_skill(path)
    except SkillParseError as e:
        console.print(f"[red]Parse error: {e}[/red]")
        raise typer.Exit(code=2) from None

    if json_out:
        payload = {
            "name": skill.name,
            "version": skill.version,
            "description": skill.description,
            "allowed_tools": skill.allowed_tools,
            "metadata": skill.metadata,
            "recipe_steps": [
                {"verb": s.verb, "args": s.args, "line": s.line_in_source}
                for s in skill.recipe.steps
            ],
        }
        typer.echo(json.dumps(payload, indent=2, default=str))
        return

    console.rule(f"[cyan]{skill.name}[/cyan] v{skill.version}")
    console.print(skill.description, style="italic")
    console.print()
    console.print(f"[bold]allowed-tools:[/bold] {', '.join(skill.allowed_tools)}")
    exercised = skill.metadata.get("exercised_on", [])
    if exercised:
        console.print(f"[bold]exercised on:[/bold] {', '.join(exercised)}")
    console.print(f"[bold]recipe steps ({len(skill.recipe.steps)}):[/bold]")
    for i, step in enumerate(skill.recipe.steps, start=1):
        args = ", ".join(f"{k}={v!r}" for k, v in step.args.items()) or "(no args)"
        # Disable rich markup interpretation; selectors contain `[` chars that
        # Rich would otherwise treat as style tags.
        console.print(f"  {i:2d}. [green]{step.verb}[/green]  ", end="")
        console.print(args, markup=False, highlight=False)


@app.command()
def version() -> None:
    """Print version."""
    from browser_skills import __version__

    typer.echo(__version__)


@app.command()
def doctor() -> None:
    """Diagnose a browser-skills install: Python, Playwright, fastmcp,
    env vars, MCP config files. Prints a pass/fail line per check.
    Exits non-zero if any required check fails.
    """
    import importlib.util
    import os
    import platform as _platform
    import sys

    from browser_skills import __version__

    issues = 0

    def _row(label: str, status: str, detail: str = "") -> None:
        nonlocal issues
        if status == "fail":
            issues += 1
        icon = {"ok": "[green]ok[/green]", "warn": "[yellow]warn[/yellow]",
                "fail": "[red]fail[/red]", "info": "[dim]info[/dim]"}[status]
        suffix = f" — {detail}" if detail else ""
        console.print(f"  {icon}  {label}{suffix}", highlight=False)

    console.rule(f"browser-skills doctor — v{__version__}")
    # 1. Python version
    py = sys.version_info
    py_ok = (py.major, py.minor) >= (3, 11)
    _row(
        f"Python {py.major}.{py.minor}.{py.micro}",
        "ok" if py_ok else "fail",
        "(>=3.11 required)" if not py_ok else "",
    )

    # 2. Platform
    _row(f"{_platform.system()} / {_platform.machine()}", "info")

    # 3. Playwright import
    pw_spec = importlib.util.find_spec("playwright")
    _row(
        "playwright module",
        "ok" if pw_spec else "fail",
        "" if pw_spec else "pip install browser-skills (or playwright)",
    )

    # 4. Chromium binary (shared helper, also used by the integration-
    # test skip decorator — see browser_skills._chromium).
    if pw_spec:
        from browser_skills._chromium import chromium_install_path

        chrome_path = chromium_install_path()
        _row(
            "Chromium browser",
            "ok" if chrome_path else "warn",
            str(chrome_path) if chrome_path else "python -m playwright install chromium",
        )

    # 5. fastmcp
    mcp_spec = importlib.util.find_spec("fastmcp")
    _row(
        "fastmcp module",
        "ok" if mcp_spec else "warn",
        "" if mcp_spec else "(needed for the MCP server; pip install fastmcp)",
    )

    # 6. Env vars
    env_vars = ["BROWSER_SKILLS_DIR", "BROWSER_SKILLS_FORBID_HEADED", "BROWSER_SKILLS_MCP_TOKEN"]
    for v in env_vars:
        val = os.environ.get(v)
        if val is None:
            _row(f"${v}", "info", "unset")
        else:
            shown = val if v != "BROWSER_SKILLS_MCP_TOKEN" else "[REDACTED]"
            _row(f"${v}", "info", f"= {shown}")

    # 7. Skills directory found
    sd = _default_skills_dir()
    skill_count = (
        len(list(sd.glob("*/SKILL.md"))) if sd.is_dir() else 0
    )
    _row(
        f"Skills directory ({sd})",
        "ok" if skill_count > 0 else "warn",
        f"{skill_count} skills" if skill_count > 0 else "no SKILL.md files found",
    )

    # 8. MCP client configs
    home = Path(os.path.expanduser("~"))
    candidates = {
        "Claude Desktop (macOS)": home / "Library/Application Support/Claude/claude_desktop_config.json",
        "Claude Desktop (Windows)": home / "AppData/Roaming/Claude/claude_desktop_config.json",
        "Claude Desktop (Linux)": home / ".config/Claude/claude_desktop_config.json",
        "Cursor": home / ".cursor/mcp.json",
        "Codex CLI": home / ".codex/mcp_servers.json",
        "Continue": home / ".continue/config.json",
    }
    any_found = False
    for label, path in candidates.items():
        if path.exists():
            any_found = True
            _row(f"{label} config", "info", str(path))
    if not any_found:
        _row("MCP client configs", "info", "none of the standard paths found")

    console.rule()
    if issues:
        console.print(f"[red]{issues} failure(s)[/red] — fix the items marked 'fail' above.")
        raise typer.Exit(code=1)
    console.print("[green]All required checks passed.[/green]")


@app.command(name="new")
def new_skill(
    name: str = typer.Argument(..., help="Kebab-case skill name (matches the directory)."),
    skills_dir: Path = typer.Option(  # noqa: B008
        None, "--skills-dir", help="Override skills/ directory location."
    ),
    fixture: bool = typer.Option(
        True, "--fixture/--no-fixture", help="Also scaffold a tests/fixtures/<name>/page.html."
    ),
) -> None:
    """Scaffold a new skill directory with a starter SKILL.md.

    Writes:
      skills/<name>/SKILL.md     — agentskills.io-conformant template
      tests/fixtures/<name>/page.html  (unless --no-fixture)
    """
    if not _is_valid_skill_name(name):
        console.print(
            f"[red]Invalid skill name: {name!r}. "
            f"Use kebab-case (lowercase, hyphens, no leading/trailing dashes).[/red]"
        )
        raise typer.Exit(code=1)

    sd = skills_dir or _default_skills_dir()
    skill_dir = sd / name
    if skill_dir.exists():
        console.print(f"[red]{skill_dir} already exists; refusing to overwrite[/red]")
        raise typer.Exit(code=1)
    skill_dir.mkdir(parents=True)
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(_SKILL_TEMPLATE.format(name=name), encoding="utf-8")
    console.print(f"[green]Wrote {skill_md}[/green]")

    if fixture:
        fix_dir = Path("tests/fixtures") / name
        fix_dir.mkdir(parents=True, exist_ok=True)
        fix_html = fix_dir / "page.html"
        if not fix_html.exists():
            fix_html.write_text(_FIXTURE_TEMPLATE.format(name=name), encoding="utf-8")
            console.print(f"[green]Wrote {fix_html}[/green]")

    console.print(
        "\n[bold]Next steps:[/bold]\n"
        f"  1. Edit {skill_md} — replace the placeholder selectors with real ones\n"
        f"  2. Edit the fixture HTML to match what real sites use\n"
        f"  3. Run: browser-skills test {name}\n"
        f"  4. When the recipe is solid, see CONTRIBUTING.md to open a PR\n"
    )


def _is_valid_skill_name(name: str) -> bool:
    return bool(_VALID_SKILL_NAME_RE.match(name))


_SKILL_TEMPLATE = """\
---
name: {name}
description: TODO — one-line description of what this skill does and when to invoke it
version: 0.1.0
allowed-tools: [wait, click, try_each, assert]
metadata:
  applies_to: any-website
  url_patterns: ["*"]
  dom_markers:
    - "TODO-css-selector-or-substring"
  flake_rate_target: 0.10
  exercised_on:
    - TODO-site-id-1
    - TODO-site-id-2
  cost_budget:
    deterministic_only: false
    max_vision_calls: 1
---

# {name}

## When to invoke

TODO — 1-3 sentences. When should the matcher pick this skill? Be specific
enough that an agent reading just this section can decide "yes" or "no".

## Recipe

1. wait extra=200ms
2. try_each selectors=[
     "TODO-primary-selector",
     "TODO-alternate-selector",
   ] action=click on_success=stop timeout=1500ms
3. wait extra=200ms

## Success criteria

- assert no_visible_element selector="TODO" OR no_change_was_needed

## When NOT to use

- TODO — at least one scenario where this skill should be skipped

## Known failures

- TODO — at least one documented failure mode. Intellectual honesty.
"""


_FIXTURE_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{name} fixture</title>
</head>
<body>
  <main>
    <h1>{name} fixture</h1>
    <!-- TODO: replace this with markup that exercises your recipe's selectors. -->
  </main>
</body>
</html>
"""


@app.command(name="test")
def test_skill(
    name: str = typer.Argument(..., help="Skill name to test against its fixture page."),
    headed: bool = typer.Option(False, "--headed", help="Show the browser window."),
    skills_dir: Path = typer.Option(  # noqa: B008
        None, "--skills-dir"
    ),
    fixture: Path = typer.Option(  # noqa: B008
        None,
        "--fixture",
        help="Path to a local HTML file to test against. "
        "Defaults to tests/fixtures/<name>/page.html.",
    ),
) -> None:
    """Run a skill against a local HTML fixture and pretty-print the result.

    Quick sanity check while authoring or debugging — no network, no
    third-party site, but a real Chromium so selectors are exercised.
    """
    sd = skills_dir or _default_skills_dir()
    skill_path = sd / name / "SKILL.md"
    if not skill_path.exists():
        console.print(f"[red]No SKILL.md at {skill_path}[/red]")
        raise typer.Exit(code=1)

    fixture_path = fixture or (Path("tests/fixtures") / name / "page.html")
    if not fixture_path.exists():
        console.print(
            f"[yellow]No fixture at {fixture_path}; "
            f"create one or pass --fixture[/yellow]"
        )
        raise typer.Exit(code=2)

    asyncio.run(_run_test_against_fixture(skill_path, fixture_path, headed))


async def _run_test_against_fixture(
    skill_path: Path, fixture_path: Path, headed: bool
) -> None:
    from playwright.async_api import async_playwright

    from browser_skills.adapters.playwright_raw import PlaywrightPage
    from browser_skills.runner import Runner
    from browser_skills.skill import parse_skill

    skill = parse_skill(skill_path)
    file_url = fixture_path.resolve().as_uri()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=not headed)
        try:
            context = await browser.new_context(viewport={"width": 1280, "height": 800})
            page = await context.new_page()
            await page.goto(file_url, wait_until="domcontentloaded", timeout=10000)

            runner = Runner()
            result = await runner.execute(skill, PlaywrightPage(page))

            color = "green" if result.status == "success" else "red"
            console.rule(f"[{color}]{result.status.upper()}[/{color}] {skill.name}")
            console.print(f"deterministic_path: {result.deterministic_path}")
            console.print(f"duration_ms:        {result.duration_ms}")
            console.print(f"steps_executed:     {result.steps_executed}")
            console.print(f"model_calls:        {result.model_calls}")
            console.print(f"tokens_used:        {result.tokens_used}")
            if result.failure_reason:
                console.print(f"[red]failure_reason:[/red] {result.failure_reason}")
            if result.warnings:
                console.print(f"warnings:           {result.warnings}")
            if result.extracted:
                console.print(f"extracted:          {result.extracted}")
            if headed:
                console.print("\n[dim]Browser window stays open for 3s …[/dim]")
                await asyncio.sleep(3)
        finally:
            await browser.close()


# --- MCP subcommands ------------------------------------------------------


@mcp_app.command("serve")
def mcp_serve(
    transport: str = typer.Option("stdio", help="stdio | streamable-http"),
    host: str = typer.Option("127.0.0.1"),
    port: int = typer.Option(8081),
) -> None:
    """Run the MCP server."""
    from browser_skills.server import serve

    serve(transport=transport, host=host, port=port)


@mcp_app.command("install")
def mcp_install(
    target: str = typer.Argument(
        ..., help="claude-desktop | cursor | codex | continue | print"
    ),
) -> None:
    """Write an MCP server stanza (stdio transport) to the appropriate
    config file (or print it).

    HTTP transport is intentionally not supported by this command in
    v0.2 — see [docs/mcp-design.md](docs/mcp-design.md). Until Bearer-
    token auth is implemented and tested, writing an HTTP MCP stanza
    into a user's client config would be a quiet foot-gun. Run
    `browser-skills mcp serve --transport=streamable-http` manually if
    you intend to put it behind your own auth (Tailscale, Cloudflare
    Access, etc.); we don't pre-write that config for you.
    """
    import json
    import os
    import platform

    stanza = {
        "command": "browser-skills",
        "args": ["mcp", "serve", "--transport", "stdio"],
    }

    if target == "print":
        body = {"mcpServers": {"browser-skills": stanza}}
        typer.echo(json.dumps(body, indent=2))
        return

    home = Path(os.path.expanduser("~"))
    config_paths = {
        "claude-desktop": {
            "Windows": home / "AppData/Roaming/Claude/claude_desktop_config.json",
            "Darwin": home / "Library/Application Support/Claude/claude_desktop_config.json",
            "Linux": home / ".config/Claude/claude_desktop_config.json",
        },
        "cursor": {
            "*": home / ".cursor/mcp.json",
        },
        "codex": {
            "*": home / ".codex/mcp_servers.json",
        },
        "continue": {
            "*": home / ".continue/config.json",
        },
    }
    if target not in config_paths:
        console.print(f"[red]Unknown target: {target}[/red]")
        raise typer.Exit(code=1)
    plat = platform.system() or "Linux"
    path_map = config_paths[target]
    cfg_path = path_map.get(plat) or path_map.get("*")
    if cfg_path is None:
        console.print(f"[red]No path for {target} on {plat}[/red]")
        raise typer.Exit(code=1)

    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    existing: dict = {}
    if cfg_path.exists():
        try:
            existing = json.loads(cfg_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            console.print(f"[red]{cfg_path} is not valid JSON; refusing to overwrite[/red]")
            raise typer.Exit(code=2) from None

    existing.setdefault("mcpServers", {})["browser-skills"] = stanza
    cfg_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    console.print(f"[green]Wrote MCP config to {cfg_path}[/green]")
    console.print(json.dumps({"browser-skills": stanza}, indent=2))


if __name__ == "__main__":
    app()
