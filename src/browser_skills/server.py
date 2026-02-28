"""MCP server. Exposes the browser-skills toolset to any MCP-aware client
(Claude Code, Codex, Cursor, etc.) over stdio or HTTP.

Built on fastmcp. See docs/mcp-design.md for the full tool surface and
error model. Session storage is in-memory; restart clears all
sessions. Concurrent sessions capped at MAX_CONCURRENT_SESSIONS.

HTTP-transport auth: the design doc describes a bearer-token flow; the
implementation here does NOT validate tokens (tracked as Phase 3
roadmap item; until then, only stdio is considered hardened).
"""

from __future__ import annotations

import asyncio
import base64
import os
import secrets
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from browser_skills import __version__, config
from browser_skills.matcher import PageState, match
from browser_skills.runner import Runner
from browser_skills.skill import Skill, load_bundle

MAX_CONCURRENT_SESSIONS = 10


@dataclass
class _Session:
    """A live browser session. Holds the Playwright handles."""

    id: str
    headed: bool
    pw: Any
    browser: Any
    context: Any
    page: Any
    trace_ids: list[str] = field(default_factory=list)
    # Reset to 0 on every successful navigate; incremented on every
    # invoke_skill. is_initial_load is `== 0`, so the matcher correctly
    # de-prioritizes "first-load" skills (verify-page-loaded,
    # dismiss-cookie-banner) on the same page after the first invocation.
    invocations_since_navigate: int = 0


_sessions: dict[str, _Session] = {}
_skills_cache: list[Skill] | None = None
_skills_cache_max_mtime: float = 0.0
_skills_cache_dir: Path | None = None
_runner = Runner()


def _new_session_id() -> str:
    return f"sess_{secrets.token_hex(6)}"


def _reset_skills_cache() -> None:
    """Force the next _load_skills_cached call to re-read from disk.
    Exposed for the `reload_skills` MCP tool and for tests.
    """
    global _skills_cache, _skills_cache_max_mtime, _skills_cache_dir
    _skills_cache = None
    _skills_cache_max_mtime = 0.0
    _skills_cache_dir = None


def _max_skill_mtime(skills_dir: Path) -> float:
    """Largest mtime across SKILL.md files (and the directory itself,
    which captures additions/removals).
    """
    try:
        top = skills_dir.stat().st_mtime
    except OSError:
        return 0.0
    best = top
    for sub in skills_dir.iterdir() if skills_dir.is_dir() else ():
        skill_md = sub / "SKILL.md"
        if skill_md.is_file():
            try:
                m = skill_md.stat().st_mtime
                if m > best:
                    best = m
            except OSError:
                continue
    return best


def _load_skills_cached(skills_dir: Path | None = None) -> list[Skill]:
    """Cache-aware loader. Reads SKILL.md files only when the bundle's
    on-disk state changes (max mtime across the directory and its
    SKILL.md files). Reload otherwise returns the same list object,
    so callers can rely on identity.
    """
    global _skills_cache, _skills_cache_max_mtime, _skills_cache_dir
    sd = skills_dir or _default_skills_dir()
    current_mtime = _max_skill_mtime(sd)
    if (
        _skills_cache is None
        or _skills_cache_dir != sd
        or current_mtime > _skills_cache_max_mtime
    ):
        _skills_cache = load_bundle(sd)
        _skills_cache_max_mtime = current_mtime
        _skills_cache_dir = sd
    return _skills_cache


def _default_skills_dir() -> Path:
    env = os.environ.get("BROWSER_SKILLS_DIR")
    if env:
        return Path(env)
    cwd_skills = Path.cwd() / "skills"
    if cwd_skills.is_dir():
        return cwd_skills
    return Path(__file__).parent / "_skills"


# --- Tool implementations -------------------------------------------------


_TRUTHY_ENV = frozenset({"1", "true", "yes", "on"})


def _env_is_truthy(name: str) -> bool:
    """Return True for the common shell-truthy spellings, case-insensitive.

    We accept {"1", "true", "yes", "on"} to match the convention used by
    most major tools (Docker, Kubernetes, Ansible). A misspelling like
    `BROWSER_SKILLS_FORBID_HEADED=tru` would NOT block headed mode — the
    safer failure here is to err visibly (admin notices headed launches
    succeeding) rather than silently lock out a legitimate user.
    """
    raw = os.environ.get(name, "").strip().lower()
    return raw in _TRUTHY_ENV


async def _start_browser_impl(
    headed: bool = False,
    context_name: str | None = None,
    ignore_https_errors: bool = False,
    viewport: dict[str, int] | None = None,
) -> dict[str, Any]:
    if headed and (config.forbid_headed or _env_is_truthy("BROWSER_SKILLS_FORBID_HEADED")):
        return _err("permission_denied", "headed mode is disabled on this server")
    if len(_sessions) >= MAX_CONCURRENT_SESSIONS:
        return _err("too_many_sessions", f"max {MAX_CONCURRENT_SESSIONS} sessions in flight")

    from playwright.async_api import async_playwright

    warnings: list[str] = []
    if headed:
        warnings.append("HEADED_MODE_ENABLED")
        print("[browser-skills] WARNING: headed browser opening", file=sys.stderr)

    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=not headed)
    vp = viewport or {"width": 1280, "height": 800}
    ctx_kwargs: dict[str, Any] = {
        "viewport": vp,
        "ignore_https_errors": ignore_https_errors,
        "user_agent": (
            f"Mozilla/5.0 (compatible; browser-skills/{__version__}; "
            f"+https://github.com/browser-skills/browser-skills)"
        ),
    }
    context = await browser.new_context(**ctx_kwargs)
    page = await context.new_page()

    sid = _new_session_id()
    _sessions[sid] = _Session(
        id=sid, headed=headed, pw=pw, browser=browser, context=context, page=page
    )
    return {"ok": True, "session_id": sid, "warnings": warnings}


async def _navigate_impl(
    session_id: str,
    url: str,
    wait_until: str = "domcontentloaded",
) -> dict[str, Any]:
    sess = _sessions.get(session_id)
    if not sess:
        return _err("session_not_found", session_id)
    try:
        resp = await sess.page.goto(url, wait_until=wait_until, timeout=20000)
    except Exception as e:  # noqa: BLE001
        return _err("internal", f"goto failed: {e}")
    status = resp.status if resp else 0
    # Fresh page → first-load skills are eligible again.
    sess.invocations_since_navigate = 0
    state = await _build_page_state(sess)
    return {"ok": True, "page_state": _state_to_dict(state), "status": status}


async def _close_browser_impl(session_id: str) -> dict[str, Any]:
    sess = _sessions.pop(session_id, None)
    if not sess:
        return _err("session_not_found", session_id)
    try:
        await sess.context.close()
        await sess.browser.close()
        await sess.pw.stop()
    except Exception:  # noqa: BLE001
        pass
    return {"ok": True, "session_id": session_id}


async def _reload_skills_impl() -> dict[str, Any]:
    """Force-invalidate the skill cache and re-read the bundle.
    Useful when editing SKILL.md files against a long-running server.
    """
    _reset_skills_cache()
    skills = _load_skills_cached()
    return {"ok": True, "skill_count": len(skills)}


async def _list_skills_impl() -> dict[str, Any]:
    skills = _load_skills_cached()
    return {
        "ok": True,
        "skills": [
            {
                "name": s.name,
                "version": s.version,
                "description": s.description,
                "allowed_tools": s.allowed_tools,
                "metadata": s.metadata,
            }
            for s in skills
        ],
    }


async def _list_applicable_skills_impl(session_id: str) -> dict[str, Any]:
    sess = _sessions.get(session_id)
    if not sess:
        return _err("session_not_found", session_id)
    skills = _load_skills_cached()
    state = await _build_page_state(sess)
    result = match(skills, state)
    return {
        "ok": True,
        "candidates": [
            {
                "name": m.name,
                "score": m.score,
                "confidence": m.confidence,
                "signals": m.signals,
            }
            for m in result.skills
        ],
        "rationale": result.rationale,
        "matched_in_ms": result.matched_in_ms,
    }


async def _invoke_skill_impl(
    session_id: str,
    skill_name: str,
    vars: dict[str, Any] | None = None,
    vision_budget: int | None = None,
) -> dict[str, Any]:
    sess = _sessions.get(session_id)
    if not sess:
        return _err("session_not_found", session_id)
    skills = _load_skills_cached()
    skill = next((s for s in skills if s.name == skill_name), None)
    if skill is None:
        return _err("skill_not_found", skill_name)

    from browser_skills.adapters.playwright_raw import PlaywrightPage

    wrapped = PlaywrightPage(sess.page)
    result = await _runner.execute(skill, wrapped, vars=vars, vision_budget=vision_budget)
    if result.trace_id:
        sess.trace_ids.append(result.trace_id)
    # The page has now had at least one skill run against it; subsequent
    # matcher calls should not treat it as initial-load.
    sess.invocations_since_navigate += 1
    return {
        "ok": True,
        "skill": result.skill,
        "version": result.version,
        "status": result.status,
        "deterministic_path": result.deterministic_path,
        "duration_ms": result.duration_ms,
        "model_calls": result.model_calls,
        "tokens_used": result.tokens_used,
        "trace_id": result.trace_id,
        "extracted": result.extracted,
        "vars_in": result.vars_in,
        "steps_executed": result.steps_executed,
        "failure_reason": result.failure_reason,
        "warnings": result.warnings,
    }


async def _screenshot_impl(
    session_id: str, selector: str | None = None
) -> dict[str, Any]:
    sess = _sessions.get(session_id)
    if not sess:
        return _err("session_not_found", session_id)
    try:
        if selector:
            el = await sess.page.query_selector(selector)
            if not el:
                return _err("internal", f"selector not found: {selector}")
            data = await el.screenshot()
        else:
            data = await sess.page.screenshot(full_page=False)
    except Exception as e:  # noqa: BLE001
        return _err("internal", f"screenshot failed: {e}")
    return {"ok": True, "image_b64": base64.b64encode(data).decode("ascii")}


async def _page_state_impl(session_id: str) -> dict[str, Any]:
    sess = _sessions.get(session_id)
    if not sess:
        return _err("session_not_found", session_id)
    state = await _build_page_state(sess)
    return {"ok": True, "page_state": _state_to_dict(state)}


# --- Helpers --------------------------------------------------------------


async def _build_page_state(sess: _Session) -> PageState:
    page = sess.page
    try:
        title = await page.title()
        dom = await page.content()
        try:
            cookies = await sess.context.cookies()
        except Exception:  # noqa: BLE001
            cookies = []
        visible_text = await page.evaluate(
            "() => document.body ? document.body.innerText.slice(0, 2000) : ''"
        )
    except Exception:  # noqa: BLE001
        title, dom, cookies, visible_text = None, "", [], ""
    return PageState(
        url=page.url,
        title=title,
        dom_summary=dom[:4000],
        visible_text_sample=visible_text or "",
        cookies_present=bool(cookies),
        is_initial_load=sess.invocations_since_navigate == 0,
    )


def _state_to_dict(state: PageState) -> dict[str, Any]:
    return {
        "url": state.url,
        "title": state.title,
        "dom_summary_len": len(state.dom_summary),
        "visible_text_sample_len": len(state.visible_text_sample),
        "cookies_present": state.cookies_present,
        "is_initial_load": state.is_initial_load,
    }


def _err(code: str, message: str, retryable: bool = False) -> dict[str, Any]:
    return {
        "ok": False,
        "error": {"code": code, "message": message, "retryable": retryable},
    }


# --- fastmcp wiring -------------------------------------------------------


def build_mcp() -> Any:
    """Construct the FastMCP instance. Deferred import so the package
    remains usable without the `mcp` extras installed.
    """
    from fastmcp import FastMCP

    mcp = FastMCP(name="browser-skills", version=__version__)

    @mcp.tool(name="start_browser")
    async def start_browser(
        headed: bool = False,
        context_name: str | None = None,
        ignore_https_errors: bool = False,
        viewport: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        return await _start_browser_impl(headed, context_name, ignore_https_errors, viewport)

    @mcp.tool(name="navigate")
    async def navigate(
        session_id: str, url: str, wait_until: str = "domcontentloaded"
    ) -> dict[str, Any]:
        return await _navigate_impl(session_id, url, wait_until)

    @mcp.tool(name="close_browser")
    async def close_browser(session_id: str) -> dict[str, Any]:
        return await _close_browser_impl(session_id)

    @mcp.tool(name="list_skills")
    async def list_skills() -> dict[str, Any]:
        return await _list_skills_impl()

    @mcp.tool(name="reload_skills")
    async def reload_skills() -> dict[str, Any]:
        return await _reload_skills_impl()

    @mcp.tool(name="list_applicable_skills")
    async def list_applicable_skills(session_id: str) -> dict[str, Any]:
        return await _list_applicable_skills_impl(session_id)

    @mcp.tool(name="invoke_skill")
    async def invoke_skill(
        session_id: str,
        skill_name: str,
        vars: dict[str, Any] | None = None,
        vision_budget: int | None = None,
    ) -> dict[str, Any]:
        return await _invoke_skill_impl(session_id, skill_name, vars, vision_budget)

    @mcp.tool(name="screenshot")
    async def screenshot(
        session_id: str, selector: str | None = None
    ) -> dict[str, Any]:
        return await _screenshot_impl(session_id, selector)

    @mcp.tool(name="page_state")
    async def page_state(session_id: str) -> dict[str, Any]:
        return await _page_state_impl(session_id)

    return mcp


def serve(transport: str = "stdio", host: str = "127.0.0.1", port: int = 8081) -> None:
    """Launch the MCP server."""
    mcp = build_mcp()
    if transport == "stdio":
        mcp.run(transport="stdio")
    elif transport in ("streamable-http", "http"):
        mcp.run(transport="streamable-http", host=host, port=port)
    else:
        raise ValueError(f"unsupported transport: {transport}")


__all__ = ["build_mcp", "serve"]
