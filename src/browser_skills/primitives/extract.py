"""extract_text and extract_table primitives. Bind values into the
runner's variable scope.
"""

from __future__ import annotations

from typing import Any

from browser_skills.primitives import PageLike, StepFailed, register


@register("extract_text")
async def extract_text(
    page: PageLike,
    *,
    selector: str,
    into: str | None = None,
    timeout: int = 5000,
    optional: bool = False,
    vars: dict[str, Any] | None = None,
    **_: Any,
) -> dict[str, Any]:
    """Extract the textContent of the first matching element.

    `optional=true` makes a no-match return a clean `value: None` (bound
    to the named variable if `into` is set), rather than raising StepFailed.
    Used by detect-* skills where "absence" is the desired success case.
    """
    vars = vars if vars is not None else {}
    js = (
        "(sel) => { const el = document.querySelector(sel); "
        "return el ? el.textContent.trim() : null; }"
    )
    text = await page.evaluate(js, selector)
    if text is None:
        if not optional:
            raise StepFailed(f"extract_text: selector '{selector}' matched nothing")
        if into:
            vars[into.lstrip("$")] = None
        return {"selector": selector, "value": None, "bound_to": into, "matched": False}
    if into:
        vars[into.lstrip("$")] = text
    return {"selector": selector, "value": text, "bound_to": into, "matched": True}


@register("extract_table")
async def extract_table(
    page: PageLike,
    *,
    selector: str = "table",
    into: str | None = None,
    timeout: int = 5000,
    vars: dict[str, Any] | None = None,
    **_: Any,
) -> dict[str, Any]:
    """Extract an HTML <table> as a list of dicts keyed by header cells.

    Naive but adequate for v1: first row becomes headers; subsequent rows
    become entries. Handles `<thead>` if present, else uses the first row.
    """
    vars = vars if vars is not None else {}
    js = """
    (sel) => {
      const tbl = document.querySelector(sel);
      if (!tbl) return null;
      const headRow = tbl.querySelector('thead tr') || tbl.querySelector('tr');
      if (!headRow) return [];
      const headers = Array.from(headRow.querySelectorAll('th,td'))
                            .map(c => (c.textContent || '').trim());
      const bodyRows = Array.from(tbl.querySelectorAll('tbody tr'));
      const rows = bodyRows.length ? bodyRows :
                   Array.from(tbl.querySelectorAll('tr')).slice(1);
      return rows.map(r => {
        const cells = Array.from(r.querySelectorAll('th,td'))
                            .map(c => (c.textContent || '').trim());
        const obj = {};
        headers.forEach((h, i) => { obj[h || `col${i}`] = cells[i] || ''; });
        return obj;
      });
    }
    """
    rows = await page.evaluate(js, selector)
    if rows is None:
        raise StepFailed(f"extract_table: selector '{selector}' matched no table")
    if into:
        vars[into.lstrip("$")] = rows
    return {"selector": selector, "row_count": len(rows), "bound_to": into}
