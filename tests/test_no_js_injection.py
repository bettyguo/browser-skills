"""S1: no f-string-into-JS interpolation in primitives.

The audit flagged scroll.py for f-string-formatting recipe args directly
into JS source. Currently safe because the args are type-checked as
int, but any future recipe primitive doing the same becomes a JS
injection vector when authors come from outside the project.

This test asserts a static property over the source: no .py file under
src/browser_skills/primitives/ uses f-string syntax inside a string
passed to page.evaluate. Plus a runtime test that confirms the scroll
primitive parameterizes delta correctly.
"""

from __future__ import annotations

import re
from pathlib import Path

from browser_skills.primitives import REGISTRY
from tests.conftest import FakePage


PRIMITIVES_DIR = Path(__file__).resolve().parent.parent / "src" / "browser_skills" / "primitives"


def test_no_fstring_js_interpolation_in_primitives() -> None:
    """Static check: no primitive should construct JS source via
    f-string interpolation. Use parameterized `evaluate(js, *args)`
    instead.
    """
    offenders: list[str] = []
    # Pattern: an f-string that contains a `=>` arrow-fn opener AND a
    # `{...}` Python placeholder. Two-stage: find f-strings, then test
    # if they look like JS function bodies with interpolations.
    fstring_re = re.compile(r"""f["']([^"']*=>\s*[^"']*)["']""")
    placeholder_re = re.compile(r"\{[^{}]+\}")
    for py in PRIMITIVES_DIR.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        for m in fstring_re.finditer(text):
            body = m.group(1)
            if placeholder_re.search(body):
                # Skip placeholders that look like JS object literals
                # `{key: value}` rather than Python `{varname}`.
                # Heuristic: contains ":" → JS literal, ignore.
                for ph in placeholder_re.findall(body):
                    inner = ph.strip("{}").strip()
                    if ":" in inner:
                        continue
                    if inner.isidentifier():
                        # Python identifier interpolated into JS source.
                        offenders.append(f"{py.name}: f-string interpolates {inner!r} into JS body")
                        break
    assert not offenders, (
        "f-string JS interpolation in primitives — pass values via "
        "evaluate(js, *args) instead:\n  " + "\n  ".join(offenders)
    )


# --- Runtime check for the scroll primitive ----------------------------


class _RecordingPage(FakePage):
    """Captures every evaluate() call so the test can inspect what was
    sent — JS source and arg list separately.
    """

    def __init__(self) -> None:
        super().__init__()
        self.eval_calls: list[tuple[str, tuple]] = []

    async def evaluate(self, expression: str, *args):  # type: ignore[override]
        self.eval_calls.append((expression, args))
        if "scrollHeight" in expression:
            return 1000
        if "scrollBy" in expression:
            return 0
        if "scrollIntoView" in expression:
            return True
        return None


async def test_scroll_int_delta_is_passed_as_arg_not_interpolated() -> None:
    """When the recipe says `scroll target=window delta=250`, the
    runner used to f-string `250` directly into the JS source. The
    fix passes it as an evaluate arg so the JS source is fixed and
    delta arrives via the Playwright bridge.
    """
    page = _RecordingPage()
    await REGISTRY["scroll"](page, target="window", delta=250)
    # At least one evaluate call must have args carrying 250.
    found_parameterized = False
    for js_source, args in page.eval_calls:
        if "scrollBy" not in js_source:
            continue
        # 250 must NOT appear in the JS source string itself.
        assert "250" not in js_source, (
            f"scroll JS source still contains delta as a literal: {js_source!r}"
        )
        if 250 in args:
            found_parameterized = True
    assert found_parameterized, (
        f"scroll did not pass delta as an evaluate arg; saw: {page.eval_calls!r}"
    )


async def test_scroll_int_delta_on_selector_target_is_parameterized() -> None:
    """Same check for the selector-target branch."""
    page = _RecordingPage()
    await REGISTRY["scroll"](page, target="#feed", delta=100)
    for js_source, args in page.eval_calls:
        assert "100" not in js_source, (
            f"selector-target scroll JS still contains delta literal: {js_source!r}"
        )
