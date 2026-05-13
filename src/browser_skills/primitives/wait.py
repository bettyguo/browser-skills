"""wait, wait_for_dom_ready, wait_for_selector primitives."""
from __future__ import annotations

import asyncio
from typing import Any

from browser_skills.primitives import PageLike, StepFailed, register


@register("wait")
async def wait(_page: PageLike, *, extra: int = 0, **_: Any) -> dict[str, Any]:
    """Sleep for `extra` milliseconds. Used for layout-settle gaps."""
    if extra < 0 or extra > 30000:
        raise StepFailed(f"wait.extra out of range: {extra}ms")
    await asyncio.sleep(extra / 1000)
    return {"slept_ms": extra}


@register("wait_for_dom_ready")
async def wait_for_dom_ready(
    page: PageLike, *, timeout: int = 10000, **_: Any
) -> dict[str, Any]:
    """Wait until document.readyState progresses through to interactive/complete."""
    await page.wait_for_load_state("domcontentloaded", timeout=timeout)
    return {"state": "domcontentloaded"}


@register("wait_for_selector")
async def wait_for_selector(
    page: PageLike,
    *,
    selector: str,
    timeout: int = 5000,
    state: str = "visible",
    **_: Any,
) -> dict[str, Any]:
    if state not in ("visible", "attached", "hidden", "detached"):
        raise StepFailed(f"wait_for_selector.state invalid: {state}")
    await page.wait_for_selector(selector, state=state, timeout=timeout)
    return {"selector": selector, "state": state}
