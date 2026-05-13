"""MCP server tool tests via fastmcp in-process Client.

These tests cover the server surface without spinning up a real browser —
the start_browser / navigate / invoke_skill paths need Playwright and
network, so they're only exercised in the weekly benchmark cron.
"""
from __future__ import annotations

import pytest


pytest.importorskip("fastmcp")


async def test_mcp_lists_expected_tools() -> None:
    from browser_skills.server import build_mcp

    mcp = build_mcp()
    tools = await mcp.get_tools()
    names = set(tools)
    assert names == {
        "start_browser",
        "navigate",
        "close_browser",
        "list_skills",
        "reload_skills",
        "list_applicable_skills",
        "invoke_skill",
        "screenshot",
        "page_state",
    }


async def test_mcp_tool_set_documented_in_readme_and_design_doc() -> None:
    """the README and docs/mcp-design.md tool
    lists drifted from the actual server (missing `reload_skills`
    after D3). Lock the two surfaces together so future tool
    additions touch the docs in the same PR.
    """
    from pathlib import Path

    from browser_skills.server import build_mcp

    mcp = build_mcp()
    tool_names = set(await mcp.get_tools())

    repo_root = Path(__file__).resolve().parent.parent
    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    design = (repo_root / "docs" / "mcp-design.md").read_text(encoding="utf-8")

    missing_in_readme = [t for t in tool_names if t not in readme]
    missing_in_design = [t for t in tool_names if t not in design]
    assert not missing_in_readme, (
        f"README.md is missing MCP tool(s) from the listing: {missing_in_readme}"
    )
    assert not missing_in_design, (
        f"docs/mcp-design.md is missing MCP tool(s): {missing_in_design}"
    )


async def test_mcp_list_skills_returns_bundle() -> None:
    from fastmcp import Client

    from browser_skills.server import build_mcp

    mcp = build_mcp()
    async with Client(mcp) as client:
        result = await client.call_tool("list_skills", {})
        payload = result.data
        assert payload["ok"] is True
        names = {s["name"] for s in payload["skills"]}
        # M4 ships the full v1 bundle of 15 skills.
        # Source of truth: tests/test_bundle_completeness.py::EXPECTED_V1_SKILLS
        from tests.test_bundle_completeness import EXPECTED_V1_SKILLS

        assert EXPECTED_V1_SKILLS.issubset(names), (
            f"MCP server list_skills should expose all v1 skills; missing: "
            f"{EXPECTED_V1_SKILLS - names}"
        )


async def test_mcp_session_not_found_error_shape() -> None:
    from fastmcp import Client

    from browser_skills.server import build_mcp

    mcp = build_mcp()
    async with Client(mcp) as client:
        result = await client.call_tool(
            "list_applicable_skills", {"session_id": "sess_doesnotexist"}
        )
        payload = result.data
    assert payload["ok"] is False
    assert payload["error"]["code"] == "session_not_found"
    assert payload["error"]["retryable"] is False


async def test_mcp_invoke_skill_vision_budget_overrides_skill_default() -> None:
    """the MCP `invoke_skill` tool accepts a per-call
    `vision_budget` argument. The runner is supposed to honor it as an
    override of the skill's `metadata.cost_budget.max_vision_calls`,
    but nothing in the test suite verified that the value propagates
    end-to-end.

    Setup: inject a stub session, a stub skill (zero vision budget by
    default but its deterministic recipe always fails), and a stub
    vision adapter. Then invoke_skill with vision_budget=1 — vision
    must fire and the response must report model_calls=1.
    """
    from fastmcp import Client

    from browser_skills import config
    from browser_skills.primitives.vision_fallback import VisionAction
    from browser_skills.server import (
        _Session,
        _sessions,
        _skills_cache,  # noqa: F401  (kept for clarity; reassigned below)
        build_mcp,
    )
    from browser_skills.skill import Recipe, Skill, Step
    import browser_skills.server as server_mod

    # 1. Inject a stub vision adapter that returns a no-op `wait`.
    class _Adapter:
        async def describe(self, *, image_b64, intent, allowed_actions, context):
            return VisionAction(
                verb="wait", args={"extra": 1}, rationale="t5", tokens_in=3, tokens_out=2
            )

    config.set_vision_adapter(_Adapter())

    # 2. Inject a stub skill whose recipe always fails. Its declared
    #    max_vision_calls is 0 — so without the per-call override,
    #    vision MUST NOT fire.
    stub_skill = Skill(
        name="t5-failing-skill",
        version="0.0.0",
        description="for T5 test only",
        allowed_tools=["click"],
        metadata={"cost_budget": {"max_vision_calls": 0}},
        recipe=Recipe(steps=[
            Step(verb="click", args={"selector": "#never", "timeout": 50}, line_in_source=1),
        ]),
        success_criteria_raw="",
        when_not_to_use="",
        known_failures="",
    )
    server_mod._skills_cache = [stub_skill]
    server_mod._skills_cache_max_mtime = float("inf")  # don't refresh
    # Pin the cache to whatever _default_skills_dir resolves to so the
    # mtime guard doesn't reset our injected stub via the
    # `_skills_cache_dir != sd` branch.
    from browser_skills.server import _default_skills_dir
    server_mod._skills_cache_dir = _default_skills_dir()

    # 3. Inject a session with a fake page that fails clicks.
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    page = SimpleNamespace(
        url="https://example.test/",
        click=AsyncMock(side_effect=TimeoutError("no element")),
        evaluate=AsyncMock(return_value=False),  # probe returns "not present"
        screenshot=AsyncMock(return_value=b""),
        title=AsyncMock(return_value=""),
        content=AsyncMock(return_value=""),
        wait_for_load_state=AsyncMock(return_value=None),
        wait_for_selector=AsyncMock(return_value=object()),
        fill=AsyncMock(return_value=None),
        query_selector=AsyncMock(return_value=None),
    )
    sess = _Session(
        id="sess_t5", headed=False, pw=None, browser=None,
        context=SimpleNamespace(cookies=AsyncMock(return_value=[])),
        page=page,
    )
    _sessions["sess_t5"] = sess

    try:
        mcp = build_mcp()
        # 3a. WITHOUT the override — vision budget defaults to skill's 0,
        # so vision MUST NOT fire and the skill must return failed.
        async with Client(mcp) as client:
            result = await client.call_tool(
                "invoke_skill",
                {"session_id": "sess_t5", "skill_name": "t5-failing-skill"},
            )
            no_override = result.data
        assert no_override["ok"] is True
        assert no_override["status"] == "failed"
        assert no_override["model_calls"] == 0, (
            "vision fired even though the skill's max_vision_calls is 0 "
            "and no override was passed"
        )

        # 3b. WITH vision_budget=1 — the override must propagate to
        # Runner.execute, vision must fire, model_calls must be 1.
        async with Client(mcp) as client:
            result = await client.call_tool(
                "invoke_skill",
                {
                    "session_id": "sess_t5",
                    "skill_name": "t5-failing-skill",
                    "vision_budget": 1,
                },
            )
            with_override = result.data
        assert with_override["ok"] is True
        assert with_override["status"] == "success", (
            "vision_budget=1 did not propagate; vision did not fire to "
            "rescue the failing recipe"
        )
        assert with_override["model_calls"] == 1
        assert with_override["tokens_used"] == 5  # 3 + 2 from the stub adapter
    finally:
        _sessions.pop("sess_t5", None)
        config.set_vision_adapter(None)
        # Drop the injected stub-skill cache so other tests get the real bundle.
        server_mod._skills_cache = None
        server_mod._skills_cache_max_mtime = 0.0
        server_mod._skills_cache_dir = None


async def test_mcp_reload_skills_via_client_returns_skill_count() -> None:
    """`reload_skills` had function-level coverage via
    test_skill_cache.py but no test exercised the full MCP-wiring path
    (`Client.call_tool("reload_skills", {})`). This catches breakage in
    the tool registration or the response envelope without needing a
    real browser.
    """
    from fastmcp import Client

    from browser_skills.server import build_mcp

    mcp = build_mcp()
    async with Client(mcp) as client:
        result = await client.call_tool("reload_skills", {})
        payload = result.data
    assert payload["ok"] is True
    # The bundled skills/ directory has 15 v1 skills; reload returns
    # the count, which we use as the freshness signal.
    assert isinstance(payload["skill_count"], int)
    assert payload["skill_count"] >= 15


async def test_mcp_invoke_skill_rejects_unknown_skill() -> None:
    from fastmcp import Client

    from browser_skills.server import build_mcp, _sessions, _Session

    # Inject a stub session so we reach the skill lookup branch.
    sess = _Session(
        id="sess_test",
        headed=False,
        pw=None,
        browser=None,
        context=None,
        page=None,
    )
    _sessions["sess_test"] = sess
    try:
        mcp = build_mcp()
        async with Client(mcp) as client:
            result = await client.call_tool(
                "invoke_skill",
                {"session_id": "sess_test", "skill_name": "does-not-exist"},
            )
            payload = result.data
        assert payload["ok"] is False
        assert payload["error"]["code"] == "skill_not_found"
    finally:
        _sessions.pop("sess_test", None)
