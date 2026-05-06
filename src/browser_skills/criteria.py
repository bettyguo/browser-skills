"""Parsing for `## Success criteria` sections in SKILL.md.

This is the first half of the v0.3 success-criteria DSL (audit-1 C3+C7):
turn the prose-y `## Success criteria` section into a structured list
of Criteria. Each Criterion is one or more Predicates OR'd together.

Evaluation lives in a follow-up commit; this module is parse-only so
the behavior-change is gated separately from the format work.

Syntax it accepts:

    - assert <predicate>
    - assert <predicate> OR <predicate>
    - assert <predicate> OR <predicate> OR <predicate>

Lines that don't start with `- assert ` are skipped (prose).
Predicates the parser doesn't recognize are kept with `unknown=True`
so the evaluator can soft-pass them later (skill criteria across the
v1 bundle use a wide vocabulary, much of it aspirational).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from browser_skills._js_predicates import (
    JS_DOM_READY,
    JS_MAIN_CONTENT_PRESENT,
    JS_NO_ELEMENT,
    JS_NO_VISIBLE_ELEMENT,
)

# `KNOWN_PREDICATES` is derived from `_DISPATCH` at import time, so the
# parser can never claim a verb is known that the evaluator doesn't
# handle (or vice versa). Single source of truth lives at _DISPATCH
# below. The `KNOWN_PREDICATES` symbol is kept as the public-facing
# read-only set for tests and docs.


@dataclass
class Predicate:
    """A single success-criterion predicate.

    `args` is parsed key=value pairs; for `$varname <verb>` shapes,
    the variable name (without the `$`) is in `args["var"]`.
    """

    verb: str
    args: dict[str, Any] = field(default_factory=dict)
    unknown: bool = False


@dataclass
class Criterion:
    """One success-criterion line. A list of Predicates OR'd together
    (single-predicate criteria are length-1 lists).
    """

    predicates: list[Predicate]
    raw_text: str
    parseable: bool = True


# Result type for evaluator. True = pass, False = explicit failure
# (the page does not satisfy the criterion), None = couldn't decide
# (unknown predicate, evaluator error, etc.). Callers treat None as
# soft-pass and surface a warning in the trace.
EvalResult = bool | None


async def evaluate_criterion(
    page: Any,
    vars: dict[str, Any],
    criterion: Criterion,
    error_sink: list[str] | None = None,
) -> EvalResult:
    """Evaluate one Criterion against a live page + the runner's vars
    map. OR-semantics: if ANY predicate evaluates True, criterion
    passes. If ALL predicates evaluate False (and at least one was a
    known/decidable predicate), criterion fails. If every predicate
    is unknown or undecidable, returns None (soft-pass).

    `error_sink` forwards to `evaluate_predicate` — see that docstring.
    """
    saw_decidable_false = False
    for p in criterion.predicates:
        result = await evaluate_predicate(page, vars, p, error_sink=error_sink)
        if result is True:
            return True
        if result is False:
            saw_decidable_false = True
    if saw_decidable_false:
        return False
    return None


async def evaluate_predicate(
    page: Any,
    vars: dict[str, Any],
    p: Predicate,
    error_sink: list[str] | None = None,
) -> EvalResult:
    """Evaluate one predicate. Returns True/False for known predicates,
    None for unknown/undecidable. Never raises — callers expect None
    on internal failure too (the runner treats None as soft-pass).

    `error_sink`: optional list to which the evaluator appends a
    one-line "verb: error" message when an exception is swallowed.
    The runner threads its `warnings` list in so internal eval errors
    end up in the trace and the SkillResult instead of disappearing
    silently. None by default for backwards compatibility with direct
    callers (tests).
    """
    if p.unknown:
        return None
    try:
        return await _DISPATCH[p.verb](page, vars, p.args)
    except Exception as e:  # noqa: BLE001
        if error_sink is not None:
            error_sink.append(f"{p.verb}: {type(e).__name__}: {e}")
        return None


# --- Per-predicate evaluators --------------------------------------------


async def _eval_dom_ready(page: Any, _vars: dict[str, Any], _args: dict[str, Any]) -> EvalResult:
    return bool(await page.evaluate(JS_DOM_READY))


async def _eval_main_content_present(
    page: Any, _vars: dict[str, Any], _args: dict[str, Any]
) -> EvalResult:
    return bool(await page.evaluate(JS_MAIN_CONTENT_PRESENT))


async def _eval_no_visible_element(
    page: Any, _vars: dict[str, Any], args: dict[str, Any]
) -> EvalResult:
    selector = args.get("selector")
    if not selector:
        return None
    return bool(await page.evaluate(JS_NO_VISIBLE_ELEMENT, selector))


async def _eval_no_element(
    page: Any, _vars: dict[str, Any], args: dict[str, Any]
) -> EvalResult:
    selector = args.get("selector")
    if not selector:
        return None
    return bool(await page.evaluate(JS_NO_ELEMENT, selector))


async def _eval_no_change_was_needed(
    _page: Any, _vars: dict[str, Any], _args: dict[str, Any]
) -> EvalResult:
    """Sentinel: this predicate is always true. Authors use it as the
    second operand of an OR clause to express "either we successfully
    cleared the thing, or there was nothing to clear in the first
    place." If the runner gets here, the recipe ran; the OR clause
    accepts that as a valid success state.
    """
    return True


async def _eval_var_is_set(
    _page: Any, vars: dict[str, Any], args: dict[str, Any]
) -> EvalResult:
    var = args.get("var")
    if not var:
        return None
    return var in vars and vars[var] is not None


async def _eval_var_is_unset(
    _page: Any, vars: dict[str, Any], args: dict[str, Any]
) -> EvalResult:
    var = args.get("var")
    if not var:
        return None
    return var not in vars or vars[var] is None


async def _eval_var_is_non_empty_list(
    _page: Any, vars: dict[str, Any], args: dict[str, Any]
) -> EvalResult:
    var = args.get("var")
    if not var:
        return None
    value = vars.get(var)
    return isinstance(value, list) and len(value) > 0


_DISPATCH = {
    "dom_ready": _eval_dom_ready,
    "main_content_present": _eval_main_content_present,
    "no_visible_element": _eval_no_visible_element,
    "no_element": _eval_no_element,
    "no_change_was_needed": _eval_no_change_was_needed,
    "var_is_set": _eval_var_is_set,
    "var_is_unset": _eval_var_is_unset,
    "var_is_non_empty_list": _eval_var_is_non_empty_list,
}


# Public read-only view, derived. Adding a verb to _DISPATCH
# automatically adds it here — single source of truth.
KNOWN_PREDICATES: frozenset[str] = frozenset(_DISPATCH.keys())


_ASSERT_LINE_RE = re.compile(r"^\s*-\s*assert\s+(.+)$", re.IGNORECASE)
_OR_SPLIT_RE = re.compile(r"\s+OR\s+", re.IGNORECASE)
_VARNAME_RE = re.compile(r"^\$([A-Za-z_][A-Za-z0-9_]*)$")
# Top-level key= scanner — reused shape from skill.py recipe parser, but
# kept local so the modules don't accidentally couple.
_KV_KEY_RE = re.compile(r"(\w+)=")


def parse_success_criteria(raw: str) -> list[Criterion]:
    """Parse `## Success criteria` text into a list of Criteria.

    Empty or whitespace-only input → empty list. Lines that aren't
    `- assert ...` shape → ignored. Each remaining line becomes one
    Criterion with one or more Predicates (OR-joined).
    """
    if not raw or not raw.strip():
        return []
    out: list[Criterion] = []
    for line in raw.splitlines():
        m = _ASSERT_LINE_RE.match(line)
        if not m:
            continue
        body = m.group(1).strip()
        parts = _OR_SPLIT_RE.split(body)
        predicates = [_parse_predicate(p.strip()) for p in parts]
        out.append(Criterion(predicates=predicates, raw_text=line.strip()))
    return out


def _parse_predicate(text: str) -> Predicate:
    """Parse one predicate (no OR — caller handles OR-splitting).

    Recognized shapes:
      - `<verb>`                              (no args)
      - `<verb> key="val" key=val2`           (key=value args)
      - `$varname <verb>`                     (variable-shaped predicate)
    """
    if not text:
        return Predicate(verb="", args={}, unknown=True)

    tokens = text.split(None, 1)
    head = tokens[0]
    rest = tokens[1] if len(tokens) > 1 else ""

    # Variable-shaped predicate: `$varname is_set`, `$x is_non_empty_list`, etc.
    var_m = _VARNAME_RE.match(head)
    if var_m:
        var_name = var_m.group(1)
        # Verb is the next token; remaining tokens are args.
        sub = rest.split(None, 1)
        if not sub:
            return Predicate(verb="", args={"var": var_name}, unknown=True)
        verb_for_var = "var_" + sub[0] if not sub[0].startswith("var_") else sub[0]
        args = _parse_kv_args(sub[1] if len(sub) > 1 else "")
        args["var"] = var_name
        return Predicate(
            verb=verb_for_var,
            args=args,
            unknown=verb_for_var not in KNOWN_PREDICATES,
        )

    # Otherwise: verb [key=val ...]
    verb = head
    args = _parse_kv_args(rest)
    return Predicate(verb=verb, args=args, unknown=verb not in KNOWN_PREDICATES)


def _parse_kv_args(text: str) -> dict[str, Any]:
    """Parse `key="val" key2=val2 key3=val3` into a dict.

    Bracket- and quote-aware so selectors like `[aria-label='x']`
    survive intact inside a value. Lightweight version of the recipe
    parser's _parse_step_body machinery.
    """
    if not text.strip():
        return {}
    args: dict[str, Any] = {}
    bracket = 0
    quote: str | None = None
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if quote:
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in ("'", '"'):
            quote = ch
            i += 1
            continue
        if ch == "[":
            bracket += 1
            i += 1
            continue
        if ch == "]":
            bracket -= 1
            i += 1
            continue
        if bracket == 0 and (ch.isalpha() or ch == "_"):
            m = _KV_KEY_RE.match(text, i)
            if m:
                key = m.group(1)
                val_start = m.end()
                # Find value end: next whitespace at bracket==0 + quote==None.
                j = val_start
                bracket_v = 0
                quote_v: str | None = None
                while j < n:
                    cv = text[j]
                    if quote_v:
                        if cv == quote_v:
                            quote_v = None
                    elif cv in ("'", '"'):
                        quote_v = cv
                    elif cv == "[":
                        bracket_v += 1
                    elif cv == "]":
                        bracket_v -= 1
                    elif bracket_v == 0 and cv.isspace():
                        break
                    j += 1
                raw_val = text[val_start:j].strip()
                # Strip outer quotes if any.
                if len(raw_val) >= 2 and raw_val[0] == raw_val[-1] and raw_val[0] in ("'", '"'):
                    raw_val = raw_val[1:-1]
                args[key] = raw_val
                i = j
                continue
        i += 1
    return args
