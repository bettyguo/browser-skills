"""browser-skills CLI — M1 surface: list / info / version.

The mcp serve / mcp install commands ship in M3, and test / new /
doctor in M5.
"""

from __future__ import annotations

import json
import os
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
console = Console()


def _default_skills_dir() -> Path:
    env = os.environ.get("BROWSER_SKILLS_DIR")
    if env:
        return Path(env)
    cwd_skills = Path.cwd() / "skills"
    if cwd_skills.is_dir():
        return cwd_skills
    return Path(__file__).parent / "_skills"


@app.command(name="list")
def list_skills(skills_dir: Path = typer.Option(None, "--skills-dir")) -> None:
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
    name: str = typer.Argument(...),
    skills_dir: Path = typer.Option(None, "--skills-dir"),
    json_out: bool = typer.Option(False, "--json"),
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
        typer.echo(json.dumps({
            "name": skill.name, "version": skill.version,
            "description": skill.description,
            "recipe_steps": [
                {"verb": s.verb, "args": s.args} for s in skill.recipe.steps
            ],
        }, indent=2, default=str))
        return
    console.rule(f"[cyan]{skill.name}[/cyan] v{skill.version}")
    console.print(skill.description, style="italic")


@app.command()
def version() -> None:
    """Print version."""
    from browser_skills import __version__
    typer.echo(__version__)


if __name__ == "__main__":
    app()
