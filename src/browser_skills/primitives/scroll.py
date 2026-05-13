"""scroll and scroll_until primitives."""
from __future__ import annotations

import asyncio
from typing import Any

from browser_skills.primitives import PageLike, StepFailed, register


@register("scroll")
async def scroll(
    page: PageLike,
    *,
    target: str = "window",
    delta: Any = "page",
    **_: Any,
) -> dict[str, Any]:
    """Scroll the window or a specific selector.

    delta:
      - "page": scroll one viewport height
      - "element-into-view": scroll until target selector is in view
      - int (px): scroll by px
    """
    if target == "window" and delta == "page":
        js = "() => { window.scrollBy(0, window.innerHeight); return window.scrollY; }"
        y = await page.evaluate(js)
        return {"target": "window", "scrolled_to_y": y}
    if isinstance(delta, int):
        # pass delta as an evaluate arg, not via f-string. JS source
        # is now constant; user-influenced values cross the bridge as
        # data, never as code. (Same hygiene as parameterized SQL.)
        if target == "window":
            js = "(d) => { window.scrollBy(0, d); return window.scrollY; }"
            y = await page.evaluate(js, delta)
            return {"target": "window", "scrolled_to_y": y}
        js = (
            "(args) => { const [sel, d] = args; "
            "const el = document.querySelector(sel); "
            "if (!el) return null; el.scrollBy(0, d); return el.scrollTop; }"
        )
        y = await page.evaluate(js, [target, delta])
        return {"target": target, "scrolled_to_y": y}
    if delta == "element-into-view":
        js = (
            "(sel) => { const el = document.querySelector(sel); "
            "if (!el) return false; el.scrollIntoView({behavior:'instant', block:'center'}); "
            "return true; }"
        )
        ok = await page.evaluate(js, target)
        if not ok:
            raise StepFailed(f"scroll: selector '{target}' not found")
        return {"target": target, "scrolled_into_view": True}
    raise StepFailed(f"scroll: unsupported delta={delta}")


@register("scroll_until")
async def scroll_until(
    page: PageLike,
    *,
    condition: str,
    max_iters: int = 50,
    delay: int = 300,
    **_: Any,
) -> dict[str, Any]:
    """Repeatedly scroll the window down until `condition` is true.

    `condition` is one of:
      - "no_more_content": page height stops growing for 2 consecutive iters
      - "selector_present:<css>": a selector becomes visible
    """
    if condition == "no_more_content":
        last_h = -1
        stable = 0
        for i in range(max_iters):
            h = await page.evaluate("() => document.documentElement.scrollHeight")
            if h == last_h:
                stable += 1
                if stable >= 2:
                    return {"iters": i, "final_height": h, "reason": "no_more_content"}
            else:
                stable = 0
                last_h = h
            await page.evaluate("() => window.scrollBy(0, window.innerHeight)")
            await asyncio.sleep(delay / 1000)
        return {"iters": max_iters, "reason": "max_iters"}
    if condition.startswith("selector_present:"):
        sel = condition.split(":", 1)[1]
        for i in range(max_iters):
            visible = await page.evaluate(
                "(s) => { const el = document.querySelector(s); "
                "if (!el) return false; const r = el.getBoundingClientRect(); "
                "return r.top < window.innerHeight && r.bottom > 0; }",
                sel,
            )
            if visible:
                return {"iters": i, "reason": "selector_present", "selector": sel}
            await page.evaluate("() => window.scrollBy(0, window.innerHeight)")
            await asyncio.sleep(delay / 1000)
        return {"iters": max_iters, "reason": "max_iters"}
    raise StepFailed(f"scroll_until: unknown condition '{condition}'")
