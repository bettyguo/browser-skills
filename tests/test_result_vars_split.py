"""D1 — separation of caller-input vars from primitive-extracted values.

Before this change, `SkillResult.extracted` returned `dict(vars)` — the
union of caller-input and primitive-bound keys. A caller reading
`result.extracted["my_input"]` couldn't distinguish "you passed this in"
from "the skill extracted this."

After: `vars_in` echoes the caller's input verbatim; `extracted`
contains only keys added or mutated during the run.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

from browser_skills.runner import Runner
from browser_skills.skill import parse_skill
from tests.conftest import FakeElement, FakePage


def _write_skill(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "SKILL.md"
    p.write_text(textwrap.dedent(body).lstrip(), encoding="utf-8")
    return p


async def test_caller_vars_round_trip_into_vars_in_not_extracted(tmp_path: Path) -> None:
    """Caller passes `target_date`. The recipe doesn't extract anything.
    `vars_in` carries the caller's input; `extracted` is empty.
    """
    skill = parse_skill(
        _write_skill(
            tmp_path,
            """
            ---
            name: ex-d1
            description: d
            version: 0.1.0
            ---

            ## Recipe
            1. wait extra=1ms
            """,
        )
    )
    page = FakePage()
    runner = Runner()
    result = await runner.execute(skill, page, vars={"target_date": "2026-06-15"})

    assert result.vars_in == {"target_date": "2026-06-15"}
    assert "target_date" not in result.extracted, (
        "caller's input leaked into `extracted`; v0.2 behavior was the "
        "bug D1 fixes"
    )
    assert result.extracted == {}


async def test_extracted_contains_only_primitive_bound_keys(tmp_path: Path) -> None:
    """Caller passes some context. The recipe binds a new variable via
    `extract_text into=$headline`. The new variable shows up in
    `extracted`; the caller's input shows up only in `vars_in`.
    """
    skill = parse_skill(
        _write_skill(
            tmp_path,
            """
            ---
            name: ex-extract
            description: d
            version: 0.1.0
            ---

            ## Recipe
            1. extract_text selector="h1" into="$headline"
            """,
        )
    )
    page = FakePage()
    page.add(FakeElement(tag="h1", text="Hello World"))
    runner = Runner()
    result = await runner.execute(skill, page, vars={"context": "homepage-test"})

    assert result.vars_in == {"context": "homepage-test"}
    assert result.extracted == {"headline": "Hello World"}


async def test_extracted_captures_overwrite_of_caller_var(tmp_path: Path) -> None:
    """Edge case: caller passes `$rows = []` (e.g., as a placeholder)
    and the recipe rebinds it via extract_table. `extracted[rows]`
    should reflect the new value; `vars_in[rows]` still shows what the
    caller passed.

    This is the discriminating case for "extracted = only mutations"
    vs "extracted = primitive-touched keys."
    """
    skill = parse_skill(
        _write_skill(
            tmp_path,
            """
            ---
            name: ex-overwrite
            description: d
            version: 0.1.0
            ---

            ## Recipe
            1. extract_text selector="h1" into="$rows"
            """,
        )
    )
    page = FakePage()
    page.add(FakeElement(tag="h1", text="New value"))
    runner = Runner()
    result = await runner.execute(skill, page, vars={"rows": []})

    assert result.vars_in == {"rows": []}, "vars_in must preserve caller input"
    assert result.extracted == {"rows": "New value"}, (
        "extracted must reflect the new primitive-written value"
    )


async def test_unchanged_caller_var_does_not_appear_in_extracted(
    tmp_path: Path,
) -> None:
    """If the caller passes a var that NO primitive touches, it must NOT
    appear in `extracted` — even though it's still in the runner's
    working vars map (so recipe templating can reference it).
    """
    skill = parse_skill(
        _write_skill(
            tmp_path,
            """
            ---
            name: ex-unchanged
            description: d
            version: 0.1.0
            ---

            ## Recipe
            1. wait extra=1ms
            2. wait extra=1ms
            """,
        )
    )
    page = FakePage()
    runner = Runner()
    result = await runner.execute(
        skill, page, vars={"untouched_a": 1, "untouched_b": "two"}
    )

    assert result.vars_in == {"untouched_a": 1, "untouched_b": "two"}
    assert result.extracted == {}


async def test_no_caller_vars_still_produces_valid_result(tmp_path: Path) -> None:
    """The common case (caller passes no vars at all): vars_in is an
    empty dict, extracted holds whatever the recipe bound.
    """
    skill = parse_skill(
        _write_skill(
            tmp_path,
            """
            ---
            name: ex-no-input
            description: d
            version: 0.1.0
            ---

            ## Recipe
            1. extract_text selector="h1" into="$title"
            """,
        )
    )
    page = FakePage()
    page.add(FakeElement(tag="h1", text="Title text"))
    runner = Runner()
    result = await runner.execute(skill, page)

    assert result.vars_in == {}
    assert result.extracted == {"title": "Title text"}


async def test_d1_in_place_mutation_of_caller_value_does_not_show_in_extracted(
    tmp_path: Path,
) -> None:
    """T2 (audit-3): locks in the documented contract for the corner
    case where a primitive mutates a caller-passed mutable in place.

    `caller_vars = dict(vars or {})` is shallow. If a primitive does
    `vars["rows"].append(x)`, both caller_vars["rows"] and vars["rows"]
    reference the same list and both see the appended value. The
    runner's `extracted` diff (`caller_vars[k] != vars[k]`) compares
    the same list to itself → False → the mutation is INVISIBLE to
    `extracted`.

    The current contract: extract_* primitives REASSIGN (replace the
    value in the vars dict) — they don't mutate the underlying mutable.
    No shipped v1 primitive violates this. This test pins that
    contract: future authors who try in-place mutation will see the
    silent-loss behavior and (hopefully) reach for reassignment.

    If this test changes behavior in a future commit (e.g., the
    runner snapshots via deepcopy), update the assertion and the
    contract docstring on runner.py:execute.
    """
    from browser_skills.primitives import REGISTRY, register
    from browser_skills.skill import Recipe, Skill, Step

    @register("__t2_in_place_append")
    async def _append(page, *, key, value, vars=None, **_):
        vars = vars if vars is not None else {}
        vars[key].append(value)
        return {"key": key}

    try:
        skill = Skill(
            name="t2-mutate",
            version="0.0.0",
            description="for T2 test",
            allowed_tools=["__t2_in_place_append"],
            metadata={},
            recipe=Recipe(steps=[
                Step(
                    verb="__t2_in_place_append",
                    args={"key": "rows", "value": "x"},
                    line_in_source=1,
                ),
            ]),
            success_criteria_raw="",
            when_not_to_use="",
            known_failures="",
        )
        page = FakePage()
        runner = Runner()
        original_list: list = []
        result = await runner.execute(skill, page, vars={"rows": original_list})

        # The mutation IS observable via the caller's reference
        # (both the runner and caller share the list).
        assert original_list == ["x"]
        # vars_in echo also shares the reference, so its `rows` is
        # also ["x"] — vars_in is NOT a deep copy.
        assert result.vars_in["rows"] == ["x"]
        # …but extracted MISSES the mutation because the snapshot
        # and current value point at the same list object → `!=`
        # returns False.
        assert "rows" not in result.extracted, (
            "extracted unexpectedly captured the in-place mutation; if "
            "you changed the runner to deepcopy or track writes "
            "explicitly, update this test and the contract on "
            "runner.execute"
        )
    finally:
        # Clean up the test-only primitive registration so subsequent
        # tests don't see it.
        REGISTRY.pop("__t2_in_place_append", None)


async def test_mcp_invoke_skill_response_exposes_vars_in() -> None:
    """The MCP server's invoke_skill tool surfaces SkillResult through
    a JSON envelope. After D1, that envelope must include `vars_in`
    so MCP clients can see the same split the Python API exposes.
    """
    from fastmcp import Client
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from browser_skills.server import (
        _Session,
        _sessions,
        _default_skills_dir,
        build_mcp,
    )
    from browser_skills.skill import Recipe, Skill, Step
    import browser_skills.server as server_mod

    stub_skill = Skill(
        name="d1-stub",
        version="0.0.0",
        description="for D1 test only",
        allowed_tools=["wait"],
        metadata={},
        recipe=Recipe(steps=[
            Step(verb="wait", args={"extra": 1}, line_in_source=1),
        ]),
        success_criteria_raw="",
        when_not_to_use="",
        known_failures="",
    )
    server_mod._skills_cache = [stub_skill]
    server_mod._skills_cache_max_mtime = float("inf")
    server_mod._skills_cache_dir = _default_skills_dir()

    page = SimpleNamespace(
        url="https://example.test/",
        click=AsyncMock(return_value=None),
        evaluate=AsyncMock(return_value=None),
        screenshot=AsyncMock(return_value=b""),
        title=AsyncMock(return_value=""),
        content=AsyncMock(return_value=""),
        wait_for_load_state=AsyncMock(return_value=None),
        wait_for_selector=AsyncMock(return_value=object()),
        fill=AsyncMock(return_value=None),
        query_selector=AsyncMock(return_value=None),
    )
    sess = _Session(
        id="sess_d1", headed=False, pw=None, browser=None,
        context=SimpleNamespace(cookies=AsyncMock(return_value=[])),
        page=page,
    )
    _sessions["sess_d1"] = sess

    try:
        mcp = build_mcp()
        async with Client(mcp) as client:
            result = await client.call_tool(
                "invoke_skill",
                {
                    "session_id": "sess_d1",
                    "skill_name": "d1-stub",
                    "vars": {"caller_key": "caller_value"},
                },
            )
        payload = result.data
        assert payload["ok"] is True
        assert "vars_in" in payload, (
            "MCP invoke_skill response missing `vars_in` field (D1)"
        )
        assert payload["vars_in"] == {"caller_key": "caller_value"}
        assert payload["extracted"] == {}
    finally:
        _sessions.pop("sess_d1", None)
        server_mod._skills_cache = None
        server_mod._skills_cache_max_mtime = 0.0
        server_mod._skills_cache_dir = None
