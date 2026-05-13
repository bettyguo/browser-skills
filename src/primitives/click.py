"""click and try_each primitives."""
from __future__ import annotations

from typing import Any

from browser_skills.primitives import REGISTRY, PageLike, StepFailed, register


@register("click")
async def click(
    page: PageLike,
    *,
    selector: str,
    timeout: int = 5000,
    **_: Any,
) -> dict[str, Any]:
    """Click first matching element. Raises StepFailed on no-match."""
    try:
        await page.click(selector, timeout=timeout)
    except Exception as e:  # noqa: BLE001
        raise StepFailed(f"click({selector}): {e}") from e
    return {"selector": selector}


@register("try_each")
async def try_each(
    page: PageLike,
    *,
    selectors: list[str],
    action: str = "click",
    on_success: str = "stop",
    timeout: int = 1500,
    **action_args: Any,
) -> dict[str, Any]:
    """Iterate selectors; for the first that matches, run `action`.

    Probe-then-act: each selector is first checked via a cheap
    `document.querySelector` call (zero-cost) and only attempted if a
    matching visible element exists right now. This avoids burning the
    full `timeout` per selector on pages where nothing matches — the
    common case for skills like dismiss-cookie-banner running on sites
    that don't have a banner.

    If `on_success == "continue"`, run `action` against every matching
    selector. Returns a record of which selectors were probed and hit.
    """
    if action not in REGISTRY:
        raise StepFailed(f"try_each.action unknown verb: {action}")
    if on_success not in ("stop", "continue"):
        raise StepFailed(f"try_each.on_success invalid: {on_success}")

    fn = REGISTRY[action]
    hits: list[str] = []
    for sel in selectors:
        if not await _selector_present(page, sel):
            continue
        try:
            await fn(page, selector=sel, timeout=timeout, **action_args)
            hits.append(sel)
            if on_success == "stop":
                break
        except StepFailed:
            continue
    return {
        "selectors_tried": selectors,
        "selectors_hit": hits,
        "matched_any": bool(hits),
    }


async def _selector_present(page: PageLike, selector: str) -> bool:
    """Cheap probe: does the selector match a visible element right now?

    Uses page.evaluate so the cost is one round-trip, not a full waitFor.
    Returns False on any error (the action attempt would have failed
    anyway).
    """
    js = (
        "(sel) => { try { const el = document.querySelector(sel); "
        "if (!el) return false; "
        "const cs = window.getComputedStyle(el); "
        "if (cs.display === 'none' || cs.visibility === 'hidden') return false; "
        "const r = el.getBoundingClientRect(); "
        "if (r.width === 0 && r.height === 0) return false; "
        "return true; } catch (e) { return false; } }"
    )
    try:
        return bool(await page.evaluate(js, selector))
    except Exception:  # noqa: BLE001
        return False
