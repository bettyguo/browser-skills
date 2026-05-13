"""Shared JS-payload constants for predicates evaluated against a live
page. Used by both `criteria.py` (post-recipe success-criteria
evaluation) and `primitives/assertions.py` (in-recipe `assert` verb).

These two modules were duplicating identical JS strings; a regex tweak
in one wouldn't reflect in the other and the silent-divergence risk
made the matcher / criteria stories harder to maintain in sync.
Single source of truth lives here.
"""
from __future__ import annotations


# Returns True iff `document.readyState === 'complete'`. Used by
# `dom_ready` predicate.
JS_DOM_READY: str = "() => document.readyState === 'complete'"


# Returns truthy iff the page has a `<main>`, `[role=main]`, `<article>`
# OR a body taller than 200px (fallback for SPAs that don't use
# semantic landmarks). Used by `main_content_present` predicate.
JS_MAIN_CONTENT_PRESENT: str = (
    "() => !!document.querySelector('main, [role=main], article') "
    "|| document.body.scrollHeight > 200"
)


# Argument: selector. Returns True iff no visible element matches
# (no match in the DOM at all, OR matched element has display:none,
# visibility:hidden, or zero size). Used by `no_visible_element`
# predicate.
JS_NO_VISIBLE_ELEMENT: str = (
    "(s) => { const el = document.querySelector(s); "
    "if (!el) return true; "
    "const r = el.getBoundingClientRect(); "
    "const cs = window.getComputedStyle(el); "
    "return cs.display === 'none' || cs.visibility === 'hidden' || "
    "(r.width === 0 && r.height === 0); }"
)


# Argument: selector. Returns True iff querySelector returns null
# (the element is not in the DOM at all — stronger than `no_visible_
# element`, which also accepts hidden elements). Used by `no_element`
# predicate.
JS_NO_ELEMENT: str = "(s) => !document.querySelector(s)"
