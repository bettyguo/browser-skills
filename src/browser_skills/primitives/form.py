"""Form-input primitives: fill, select_option, press_key.

Each routes through the PageLike protocol; FakePage in tests records the
operation in a log so tests can assert on intent.
"""

from __future__ import annotations

import base64
from typing import Any

from browser_skills.primitives import PageLike, StepFailed, register


@register("fill")
async def fill(
    page: PageLike,
    *,
    selector: str,
    value: str,
    timeout: int = 5000,
    clear: bool = True,
    **_: Any,
) -> dict[str, Any]:
    """Type `value` into the first matching input/textarea."""
    try:
        await page.fill(selector, value, timeout=timeout)
    except Exception as e:  # noqa: BLE001
        raise StepFailed(f"fill({selector}): {e}") from e
    return {"selector": selector, "value_length": len(value), "cleared": clear}


@register("select_option")
async def select_option(
    page: PageLike,
    *,
    selector: str,
    value: str | None = None,
    label: str | None = None,
    timeout: int = 5000,
    **_: Any,
) -> dict[str, Any]:
    """Select an option in a `<select>` element by value OR label.

    Routes through a small JS shim so this works whether the underlying
    Page exposes a native select_option or not (FakePage uses evaluate).
    """
    if value is None and label is None:
        raise StepFailed("select_option requires value= or label=")
    js = """
    (args) => {
      const [sel, value, label] = args;
      const el = document.querySelector(sel);
      if (!el || el.tagName !== 'SELECT') return {ok:false, reason:'not_a_select'};
      const opts = Array.from(el.options);
      let target = null;
      if (value !== null) target = opts.find(o => o.value === value);
      if (!target && label !== null) target = opts.find(o => (o.label || o.textContent).trim() === label);
      if (!target) return {ok:false, reason:'option_not_found'};
      el.value = target.value;
      el.dispatchEvent(new Event('change', {bubbles: true}));
      return {ok:true, value: target.value};
    }
    """
    result = await page.evaluate(js, [selector, value, label])
    if not isinstance(result, dict) or not result.get("ok"):
        raise StepFailed(
            f"select_option({selector}): "
            f"{result.get('reason', 'unknown') if isinstance(result, dict) else 'no_response'}"
        )
    return {"selector": selector, "selected_value": result["value"]}


@register("press_key")
async def press_key(
    page: PageLike,
    *,
    key: str,
    selector: str | None = None,
    **_: Any,
) -> dict[str, Any]:
    """Press a key. Optionally focused on a specific selector first.

    Used by:
      - date-picker-widget (Escape to close)
      - handle-modal-dialog fallback (Escape)
      - searchable-dropdown (Enter to confirm selection)
    """
    # Real Playwright supports page.keyboard.press(key) and
    # page.press(selector, key). Use evaluate as a portable fallback.
    js = """
    (args) => {
      const [sel, key] = args;
      const target = sel ? document.querySelector(sel) : document.activeElement || document.body;
      if (!target) return {ok:false, reason:'no_target'};
      const ev = new KeyboardEvent('keydown', {key, bubbles:true, cancelable:true});
      target.dispatchEvent(ev);
      return {ok:true};
    }
    """
    result = await page.evaluate(js, [selector, key])
    if not isinstance(result, dict) or not result.get("ok"):
        raise StepFailed(
            f"press_key({key}): "
            f"{result.get('reason', 'unknown') if isinstance(result, dict) else 'no_response'}"
        )
    return {"key": key, "selector": selector}


@register("screenshot")
async def screenshot_verb(
    page: PageLike,
    *,
    selector: str | None = None,
    into: str | None = None,
    vars: dict[str, Any] | None = None,
    **_: Any,
) -> dict[str, Any]:
    """Capture a screenshot. Real Playwright handles this natively; the
    FakePage records the call.
    """
    vars = vars if vars is not None else {}
    screenshot_fn = getattr(page, "screenshot", None)
    img_bytes: bytes = b""
    if screenshot_fn is not None:
        try:
            if selector:
                el = await page.query_selector(selector)  # type: ignore[attr-defined]
                if el is not None:
                    img_bytes = await el.screenshot()
            else:
                img_bytes = await screenshot_fn(full_page=False)
        except Exception:  # noqa: BLE001
            img_bytes = b""
    if into:
        vars[into.lstrip("$")] = base64.b64encode(img_bytes).decode("ascii") if img_bytes else ""
    return {"selector": selector, "bytes": len(img_bytes), "bound_to": into}
