"""Skill / Recipe / Step / SkillResult data model and SKILL.md parser.

Format conformance: agentskills.io spec + the browser-skills recipe convention
documented in docs/skill-recipe-format.md.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

import yaml


@dataclass
class Step:
    verb: str
    args: dict[str, Any]
    line_in_source: int


@dataclass
class Recipe:
    steps: list[Step] = field(default_factory=list)


@dataclass
class Skill:
    name: str
    version: str
    description: str
    allowed_tools: list[str]
    metadata: dict[str, Any]
    recipe: Recipe
    success_criteria_raw: str
    when_not_to_use: str
    known_failures: str
    source_path: Path | None = None
    # Parsed form of success_criteria_raw — populated by parse_skill.
    # Empty list when the section is missing or contains no `- assert`
    # lines. See browser_skills/criteria.py for the structure.
    success_criteria: list[Any] = field(default_factory=list)

    @property
    def max_vision_calls(self) -> int:
        return int(self.metadata.get("cost_budget", {}).get("max_vision_calls", 0))

    @property
    def dom_markers(self) -> list[str]:
        return list(self.metadata.get("dom_markers", []))

    @property
    def url_patterns(self) -> list[str]:
        return list(self.metadata.get("url_patterns", []))

    @property
    def evaluate_success_criteria(self) -> bool:
        """Opt-in: when True, the runner evaluates parsed
        success_criteria after the recipe completes (and again after
        vision fallback if used). A failing decidable criterion turns
        the SkillResult to status=failed. Default False keeps the
        v0.1/0.2 behavior — recipe completion alone signals success.
        """
        return bool(self.metadata.get("evaluate_success_criteria", False))


@dataclass
class SkillResult:
    skill: str
    version: str
    status: Literal["success", "failed", "skipped"]
    deterministic_path: bool
    duration_ms: int
    model_calls: int
    tokens_used: int
    trace_id: str | None
    # `extracted` contains ONLY the keys that were added or changed by
    # primitive calls during this run (D1, v0.3+). To see what the
    # caller passed in, read `vars_in`. In v0.2 these were conflated
    # in `extracted` — see CHANGELOG.
    extracted: dict[str, Any] = field(default_factory=dict)
    # Echo of the caller's `vars` input. Read-only from the runner's
    # perspective. Added in v0.3 (D1).
    vars_in: dict[str, Any] = field(default_factory=dict)
    steps_executed: int = 0
    failure_reason: str | None = None
    warnings: list[str] = field(default_factory=list)


# --- Parser ---------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)
_SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
_RECIPE_STEP_RE = re.compile(r"^\s*(\d+)\.\s+(\w+)\b\s*(.*)$")


class BrowserSkillsError(Exception):
    """Base for all browser-skills exceptions. Library users can
    `except BrowserSkillsError` to catch anything this package raises.
    """


class SkillParseError(BrowserSkillsError, ValueError):
    """Raised when a SKILL.md cannot be parsed.

    Inherits from both BrowserSkillsError (project-wide catch) and
    ValueError (legacy compatibility — early test code caught ValueError).
    """


def parse_skill(path: str | Path) -> Skill:
    """Parse a SKILL.md file into a Skill object.

    Tolerant: prose in sections is preserved; only `## Recipe` is parsed
    into structured steps. If a recipe step doesn't match the verb DSL,
    it's recorded as a `prose` step (the runner falls back to vision
    interpretation for those).
    """
    path = Path(path)
    raw = path.read_text(encoding="utf-8")

    m = _FRONTMATTER_RE.match(raw)
    if not m:
        raise SkillParseError(f"{path}: missing YAML frontmatter")

    try:
        meta = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        raise SkillParseError(f"{path}: malformed YAML frontmatter: {e}") from e

    if not isinstance(meta, dict):
        raise SkillParseError(f"{path}: frontmatter must be a mapping")

    for required in ("name", "description", "version"):
        if required not in meta:
            raise SkillParseError(f"{path}: missing required frontmatter field '{required}'")

    body = m.group(2)
    sections = _split_sections(body)

    recipe = _parse_recipe(sections.get("Recipe", ""))

    # Parse the success-criteria section into structured Criteria.
    # Done lazily to keep the import cycle small (criteria.py only
    # imports stdlib + re).
    from browser_skills.criteria import parse_success_criteria

    success_criteria_raw = sections.get("Success criteria", "")
    parsed_criteria = parse_success_criteria(success_criteria_raw)

    return Skill(
        name=str(meta["name"]),
        version=str(meta["version"]),
        description=str(meta["description"]),
        allowed_tools=list(meta.get("allowed-tools", [])),
        metadata=dict(meta.get("metadata", {})),
        recipe=recipe,
        success_criteria_raw=success_criteria_raw,
        success_criteria=parsed_criteria,
        when_not_to_use=sections.get("When NOT to use", ""),
        known_failures=sections.get("Known failures", ""),
        source_path=path,
    )


def _split_sections(body: str) -> dict[str, str]:
    """Split a markdown body by `## ` headings into a name->content map.

    Content runs up to the next `##` heading or end of body. Top-level `#`
    (skill title) is discarded — sections are keyed by the H2 heading text.
    """
    parts: dict[str, str] = {}
    last_heading: str | None = None
    last_start = 0
    for m in _SECTION_RE.finditer(body):
        if last_heading is not None:
            parts[last_heading] = body[last_start:m.start()].strip()
        last_heading = m.group(1).strip()
        last_start = m.end()
    if last_heading is not None:
        parts[last_heading] = body[last_start:].strip()
    return parts


_KV_KEY_RE = re.compile(r"(\w+)=")


def _parse_recipe(text: str) -> Recipe:
    """Parse the `## Recipe` section into a list of Step objects.

    Lines starting with a number followed by `. ` are steps. Other lines
    (prose between steps, sub-bullets) are ignored — recipe authors should
    keep prose in `## When to invoke` or `## Known failures` instead.
    """
    recipe = Recipe()
    if not text.strip():
        return recipe

    buf: list[str] = []
    current_step_num: int | None = None
    current_line_offset = 0

    def flush(line_no: int) -> None:
        nonlocal buf, current_step_num
        if current_step_num is None:
            buf = []
            return
        joined = " ".join(s.strip() for s in buf).strip()
        verb, args = _parse_step_body(joined)
        recipe.steps.append(Step(verb=verb, args=args, line_in_source=line_no))
        buf = []
        current_step_num = None

    for line_no, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        m = _RECIPE_STEP_RE.match(line)
        if m:
            flush(current_line_offset)
            current_step_num = int(m.group(1))
            current_line_offset = line_no
            buf.append(f"{m.group(2)} {m.group(3)}")
        elif current_step_num is not None and stripped and not stripped.startswith("#"):
            # continuation of the previous step (multi-line try_each lists, etc.)
            buf.append(stripped)
    flush(current_line_offset)
    return recipe


def _parse_step_body(body: str) -> tuple[str, dict[str, Any]]:
    """Split `verb key=value key=value ...` into (verb, args).

    Bracket- and quote-aware: a value may be `[a, b, c]`, `"quoted"`,
    `'quoted'`, or a bare token. Key tokens that appear inside brackets or
    quoted strings (e.g., `label=` inside `[aria-label='c']`) are not
    treated as top-level keys.
    """
    parts = body.strip().split(None, 1)
    if not parts:
        return ("noop", {})
    verb = parts[0]
    rest = parts[1] if len(parts) > 1 else ""
    args: dict[str, Any] = {}

    # Find only top-level key starts (outside brackets/quotes).
    key_starts = _find_toplevel_keys(rest)
    for i, (key, value_start) in enumerate(key_starts):
        next_start = key_starts[i + 1][1] - len(key_starts[i + 1][0]) - 1 \
            if i + 1 < len(key_starts) else len(rest)
        raw = _slice_value(rest, value_start, next_start)
        args[key] = _coerce_value(raw)
    return verb, args


def _find_toplevel_keys(text: str) -> list[tuple[str, int]]:
    """Return [(key, value_start_index), ...] for every `key=` token that
    appears at bracket depth 0 and outside quoted strings."""
    out: list[tuple[str, int]] = []
    bracket = 0
    quote: str | None = None
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if quote:
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in ("'", '"'):
            quote = ch
            i += 1
            continue
        if ch == "[":
            bracket += 1
            i += 1
            continue
        if ch == "]":
            bracket -= 1
            i += 1
            continue
        if bracket == 0 and (ch.isalpha() or ch == "_"):
            m = _KV_KEY_RE.match(text, i)
            if m:
                out.append((m.group(1), m.end()))
                i = m.end()
                continue
        i += 1
    return out


def _slice_value(text: str, start: int, hard_end: int) -> str:
    """Extract the value literal at `text[start:]`, respecting brackets
    and quote pairs. Stops at the first whitespace that is NOT inside
    a bracket or quote, or at hard_end, whichever comes first.
    """
    i = start
    while i < hard_end and text[i] == " ":
        i += 1
    if i >= hard_end:
        return ""
    bracket = 0
    quote: str | None = None
    j = i
    while j < hard_end:
        ch = text[j]
        if quote:
            if ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
        elif ch == "[":
            bracket += 1
        elif ch == "]":
            bracket -= 1
            if bracket == 0:
                j += 1
                break
        elif bracket == 0 and ch.isspace():
            break
        j += 1
    return text[i:j].strip()


_DURATION_RE = re.compile(r"^(\d+(?:\.\d+)?)(ms|s)$")


def _coerce_value(raw: str) -> Any:
    """Coerce a parsed arg literal into a Python value.

    Supports: durations (`500ms`, `2s`), ints, floats, booleans, quoted
    strings, bracketed lists of strings, and bare strings.
    """
    s = raw.strip()
    if s.startswith("[") and s.endswith("]"):
        # naive list parse; entries may be quoted or bare. Splits on commas
        # outside quotes.
        inner = s[1:-1]
        items: list[str] = []
        current = ""
        quote: str | None = None
        for ch in inner:
            if quote:
                if ch == quote:
                    quote = None
                    continue
                current += ch
            elif ch in ("'", '"'):
                quote = ch
            elif ch == ",":
                if current.strip():
                    items.append(current.strip().strip("'\""))
                current = ""
            else:
                current += ch
        if current.strip():
            items.append(current.strip().strip("'\""))
        return items
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    if s.lower() in ("true", "false"):
        return s.lower() == "true"
    m = _DURATION_RE.match(s)
    if m:
        value = float(m.group(1))
        unit = m.group(2)
        return int(value) if unit == "ms" else int(value * 1000)
    try:
        if "." in s:
            return float(s)
        return int(s)
    except ValueError:
        return s


def load_bundle(skills_dir: str | Path) -> list[Skill]:
    """Load all SKILL.md files under skills_dir/*/SKILL.md."""
    skills_dir = Path(skills_dir)
    out: list[Skill] = []
    for sub in sorted(skills_dir.iterdir()):
        if not sub.is_dir():
            continue
        skill_md = sub / "SKILL.md"
        if skill_md.exists():
            out.append(parse_skill(skill_md))
    return out
