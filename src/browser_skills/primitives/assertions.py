"""assert primitive — evaluates a small DSL of conditions."""

from __future__ import annotations

from typing import Any

from browser_skills._js_predicates import (
    JS_DOM_READY,
    JS_MAIN_CONTENT_PRESENT,
    JS_NO_ELEMENT,
    JS_NO_VISIBLE_ELEMENT,
)
from browser_skills.primitives import PageLike, StepFailed, register


@register("assert")
async def assert_(
    page: PageLike,
    *,
    condition: str | None = None,
    no_visible_element: str | None = None,
    no_element: str | None = None,
    timeout: int = 3000,
    **kwargs: Any,
) -> dict[str, Any]:
    """A tolerant assertion primitive.

    Supports two call styles:
      - `assert condition=dom_ready`  → predicate-based
      - `assert no_visible_element selector="..."`  → DSL-shorthand

    The recipe parser may emit either style; both route here.
    """
    # Shorthand: no_visible_element / no_element come in as args from the parser
    if no_visible_element:
        return await _assert_no_visible_element(page, no_visible_element)
    if no_element:
        return await _assert_no_element(page, no_element)

    if condition == "dom_ready":
        ready = await page.evaluate(JS_DOM_READY)
        if not ready:
            raise StepFailed("assert dom_ready: document not complete")
        return {"condition": "dom_ready", "ok": True}

    if condition == "main_content_present":
        ok = await page.evaluate(JS_MAIN_CONTENT_PRESENT)
        if not ok:
            raise StepFailed("assert main_content_present: no main/article and short body")
        return {"condition": "main_content_present", "ok": True}

    # Unknown condition: refuse to claim success. Silent soft-pass would
    # mask broken recipes — if the author meant a condition we don't
    # implement, surface it loudly so they can either fix the typo or
    # request the predicate.
    raise StepFailed(
        f"assert: unknown condition {condition!r}. "
        f"Known: dom_ready, main_content_present. "
        f"Use `assert no_visible_element selector=...` or "
        f"`assert no_element selector=...` for selector-shaped asserts."
    )


async def _assert_no_visible_element(page: PageLike, selector: str) -> dict[str, Any]:
    ok = await page.evaluate(JS_NO_VISIBLE_ELEMENT, selector)
    if not ok:
        raise StepFailed(f"assert no_visible_element: '{selector}' is still visible")
    return {"selector": selector, "ok": True}


async def _assert_no_element(page: PageLike, selector: str) -> dict[str, Any]:
    ok = await page.evaluate(JS_NO_ELEMENT, selector)
    if not ok:
        raise StepFailed(f"assert no_element: '{selector}' still in DOM")
    return {"selector": selector, "ok": True}
