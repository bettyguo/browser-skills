"""Shared pytest fixtures and the FakePage used to test primitives without
spinning up a real Chromium.

FakePage implements PageLike against an in-memory DOM model that's just
expressive enough to exercise the v1 verbs: selectors are dict-keyed
strings, evaluate() consults a small lookup table. Tests describe the
"page" as a small dataclass; the fake page renders it on demand.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from typing import Any, Callable

import pytest

from browser_skills import config


@dataclass
class FakeElement:
    """A minimal in-memory DOM element."""
    tag: str
    attrs: dict[str, str] = field(default_factory=dict)
    text: str = ""
    visible: bool = True
    children: list["FakeElement"] = field(default_factory=list)

    def matches(self, selector: str) -> bool:
        """Tiny CSS-ish matcher: tag, #id, .class, [attr=val], :has-text()."""
        # Strip pseudo :has-text() first so a single rule survives downstream.
        m = re.search(r":has-text\(['\"]?([^'\")]+)['\"]?\)", selector)
        has_text_substr: str | None = m.group(1).lower() if m else None
        if m:
            selector = selector[: m.start()] + selector[m.end():]

        s = selector.strip()
        if s.startswith("#"):
            if self.attrs.get("id") != s[1:]:
                return False
        elif s.startswith("."):
            classes = self.attrs.get("class", "").split()
            if s[1:] not in classes:
                return False
        elif s.startswith("["):
            inner = s.strip("[]")
            if "=" in inner:
                key, _, val = inner.partition("=")
                key = key.strip().rstrip("*").rstrip("^").rstrip("$").rstrip(" i")
                val = val.strip().strip("'\"").rstrip(" i").lower()
                attr_val = self.attrs.get(key, "").lower()
                if val not in attr_val:
                    return False
            else:
                if inner not in self.attrs:
                    return False
        else:
            tag_part = s.split(":")[0].split("[")[0].split(".")[0]
            if tag_part and tag_part != self.tag:
                return False

        if has_text_substr and has_text_substr not in self.text.lower():
            return False
        return True


@dataclass
class FakePage:
    """In-memory PageLike. Tests build one with .add(element); primitives
    interact with it through the same interface a real Playwright Page
    exposes.
    """
    url: str = "https://example.test/"
    ready_state: str = "complete"
    elements: list[FakeElement] = field(default_factory=list)
    click_log: list[str] = field(default_factory=list)
    fill_log: list[tuple[str, str]] = field(default_factory=list)
    key_log: list[tuple] = field(default_factory=list)
    select_log: list[tuple[str, str]] = field(default_factory=list)
    _custom_eval: dict[str, Callable[[FakePage, tuple[Any, ...]], Any]] = field(
        default_factory=dict
    )

    def add(self, *els: FakeElement) -> None:
        self.elements.extend(els)

    def remove_visible(self, selector: str) -> None:
        for el in self.elements:
            if el.matches(selector):
                el.visible = False

    def _find_all(self, selector: str) -> list[FakeElement]:
        # Support `,`-separated multi-selectors used in some recipes
        sels = [s.strip() for s in selector.split(",")]
        out = []
        for el in self.elements:
            for s in sels:
                if el.matches(s):
                    out.append(el)
                    break
        return out

    # --- PageLike methods ------------------------------------------------

    async def wait_for_load_state(self, state: str = "load", *, timeout: int = 10000) -> None:
        # Pretend the page is always ready instantly.
        if self.ready_state == "complete":
            return
        await asyncio.sleep(0.001)
        return

    async def wait_for_selector(
        self, selector: str, *, state: str = "visible", timeout: int = 5000
    ) -> FakeElement:
        for el in self._find_all(selector):
            if state in ("attached",) or (state == "visible" and el.visible):
                return el
            if state == "hidden" and not el.visible:
                return el
            if state == "detached":
                continue
        raise TimeoutError(f"wait_for_selector({selector}, state={state}) timed out")

    async def click(self, selector: str, *, timeout: int = 5000) -> None:
        matches = [e for e in self._find_all(selector) if e.visible]
        if not matches:
            raise TimeoutError(f"click({selector}) found no visible element")
        matches[0].visible = False  # cookie banner-style dismissal default
        self.click_log.append(selector)

    async def fill(self, selector: str, value: str, *, timeout: int = 5000) -> None:
        matches = self._find_all(selector)
        if not matches:
            raise TimeoutError(f"fill({selector}): no match")
        matches[0].attrs["value"] = value
        self.fill_log.append((selector, value))

    async def evaluate(self, expression: str, *args: Any) -> Any:
        """Recognize the JS snippets our primitives use; route to Python.

        The pattern matches enough of the literal `evaluate` strings used in
        primitives/extract.py and primitives/assertions.py to make tests
        meaningful. Unknown expressions raise — we want to know when a
        primitive grows a new JS payload that needs fixture support.
        """
        # select_option JS payload — picks an <option> by value or label.
        # Routed before the textContent branch because the select_option JS
        # also reads textContent of option elements.
        if "tagName" in expression and "SELECT" in expression:
            sel, value, label = args[0]
            els = self._find_all(sel)
            if not els or els[0].tag != "select":
                return {"ok": False, "reason": "not_a_select"}
            chosen = value if value is not None else label
            if chosen is None:
                return {"ok": False, "reason": "option_not_found"}
            self.select_log.append((sel, chosen))
            return {"ok": True, "value": chosen}
        # extract_text: querySelector textContent
        if "querySelector" in expression and "textContent" in expression:
            (selector,) = args
            els = self._find_all(selector)
            return els[0].text if els else None
        # extract_table — return [] for fake page (real DOM-walk tested in
        # an integration test with a real browser).
        if "querySelectorAll('thead tr')" in expression or "tbody tr" in expression:
            return []
        # try_each.selector_present probe — `_selector_present` in click.py.
        # Must come BEFORE the assert no_visible_element branch (both check
        # getBoundingClientRect + display === 'none').
        if "try { const el = document.querySelector(sel)" in expression:
            (selector,) = args
            els = self._find_all(selector)
            return any(e.visible for e in els)
        # assert no_visible_element
        if "getBoundingClientRect" in expression and "display === 'none'" in expression:
            (selector,) = args
            els = self._find_all(selector)
            if not els:
                return True
            return not els[0].visible
        # main_content_present — check BEFORE the generic !document.querySelector
        # branch because that one would otherwise swallow this case.
        if "main, [role=main], article" in expression:
            return any(
                e.tag in ("main", "article") or e.attrs.get("role") == "main"
                for e in self.elements
            )
        # assert no_element (single-arg form)
        if "!document.querySelector" in expression and args:
            (selector,) = args
            return not self._find_all(selector)
        # readyState
        if "document.readyState" in expression:
            return self.ready_state == "complete"
        # scrollHeight
        if "scrollHeight" in expression:
            return 1000
        # scrollBy
        if "scrollBy" in expression:
            return 0
        # press_key JS payload — dispatches a KeyboardEvent. FakePage
        # records nothing visible to other primitives; we just confirm
        # the call shape and return the expected {ok: true} envelope.
        if "KeyboardEvent" in expression and "keydown" in expression:
            # args is [[selector, key]]; the JS wraps args in an array.
            self.key_log.append(tuple(args[0]) if args else ())
            return {"ok": True}
        # custom registered
        for key, fn in self._custom_eval.items():
            if key in expression:
                return fn(self, args)
        raise AssertionError(
            f"FakePage.evaluate got an unrecognized JS payload; "
            f"add a case in conftest.py: {expression!r}"
        )


@pytest.fixture(autouse=True)
def reset_config():
    config.reset_for_test()
    yield
    config.reset_for_test()


@pytest.fixture
def fake_page() -> FakePage:
    return FakePage()
