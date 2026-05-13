"""both `criteria.py` (success-criteria evaluator) and
`primitives/assertions.py` (in-recipe `assert` verb) need the same JS
payloads to check page state. They used to duplicate the JS strings
inline; this test pins the single-source-of-truth contract.

If a future refactor reintroduces the inline JS in either module,
this test fails — pushing the author back to the shared constants
in `browser_skills._js_predicates`.
"""
from __future__ import annotations

from pathlib import Path

from browser_skills._js_predicates import (
    JS_DOM_READY,
    JS_MAIN_CONTENT_PRESENT,
    JS_NO_ELEMENT,
    JS_NO_VISIBLE_ELEMENT,
)


SRC_ROOT = Path(__file__).resolve().parent.parent / "src" / "browser_skills"


def _text(path: str) -> str:
    return (SRC_ROOT / path).read_text(encoding="utf-8")


def test_criteria_module_uses_shared_constants() -> None:
    """criteria.py must reference the named constants, not re-inline
    the JS bodies.
    """
    text = _text("criteria.py")
    for name in ("JS_DOM_READY", "JS_MAIN_CONTENT_PRESENT", "JS_NO_VISIBLE_ELEMENT", "JS_NO_ELEMENT"):
        assert name in text, f"criteria.py no longer references {name}"
    # Negative check: the literal JS source for dom_ready must NOT
    # appear in criteria.py (lives only in _js_predicates.py now).
    assert "() => document.readyState === 'complete'" not in text, (
        "criteria.py reintroduced the dom_ready JS literal — use "
        "browser_skills._js_predicates.JS_DOM_READY instead"
    )


def test_assertions_primitive_uses_shared_constants() -> None:
    """primitives/assertions.py must reference the same named constants."""
    text = _text("primitives/assertions.py")
    for name in ("JS_DOM_READY", "JS_MAIN_CONTENT_PRESENT", "JS_NO_VISIBLE_ELEMENT", "JS_NO_ELEMENT"):
        assert name in text, f"primitives/assertions.py no longer references {name}"
    assert "() => document.readyState === 'complete'" not in text, (
        "primitives/assertions.py reintroduced the dom_ready JS literal — "
        "use browser_skills._js_predicates.JS_DOM_READY instead"
    )


def test_shared_constants_are_well_formed_strings() -> None:
    """Sanity: each constant is a non-empty string that looks like a JS
    arrow function. Catches accidental empty / None assignments.
    """
    for name, value in (
        ("JS_DOM_READY", JS_DOM_READY),
        ("JS_MAIN_CONTENT_PRESENT", JS_MAIN_CONTENT_PRESENT),
        ("JS_NO_VISIBLE_ELEMENT", JS_NO_VISIBLE_ELEMENT),
        ("JS_NO_ELEMENT", JS_NO_ELEMENT),
    ):
        assert isinstance(value, str) and value, f"{name} is not a non-empty string"
        assert "=>" in value, f"{name} doesn't look like a JS arrow function: {value!r}"
