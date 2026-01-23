"""Direct Playwright adapter — the reference backend.

A real Playwright Page already satisfies our PageLike protocol almost as-is
(the methods we use have matching signatures). This module exists to:
  1. Provide a thin wrapper around the real Page so the runner and
     primitives can be tested against a FakePage without spinning up
     Chromium.
  2. Expose the exact subset of Page methods our primitives reach for
     (incl. screenshot + query_selector, used by vision_fallback and
     the screenshot recipe verb).

Future translation of Playwright's TimeoutError into our StepRetryable
vs StepFailed semantics is tracked as a Phase 3 roadmap item.
"""

from __future__ import annotations

from typing import Any

from browser_skills.primitives import PageLike


class PlaywrightPage(PageLike):  # type: ignore[misc]  # Protocol subclassing
    """Wraps playwright.async_api.Page. Methods delegate; errors translate."""

    def __init__(self, page: Any) -> None:  # pragma: no cover
        self._page = page

    @property
    def url(self) -> str:  # pragma: no cover
        return self._page.url

    async def wait_for_load_state(
        self, state: str = "load", *, timeout: int = 10000
    ) -> None:  # pragma: no cover
        await self._page.wait_for_load_state(state, timeout=timeout)

    async def wait_for_selector(
        self, selector: str, *, state: str = "visible", timeout: int = 5000
    ) -> Any:  # pragma: no cover
        return await self._page.wait_for_selector(selector, state=state, timeout=timeout)

    async def click(self, selector: str, *, timeout: int = 5000) -> None:  # pragma: no cover
        await self._page.click(selector, timeout=timeout)

    async def fill(
        self, selector: str, value: str, *, timeout: int = 5000
    ) -> None:  # pragma: no cover
        await self._page.fill(selector, value, timeout=timeout)

    async def evaluate(self, expression: str, *args: Any) -> Any:  # pragma: no cover
        return await self._page.evaluate(expression, *args)

    async def screenshot(self, **kwargs: Any) -> bytes:
        """Forward to the real page's screenshot. Vision fallback and the
        screenshot recipe verb both locate this via getattr; if it's
        missing they silently capture nothing.
        """
        return await self._page.screenshot(**kwargs)

    async def query_selector(self, selector: str) -> Any:
        """Forward to the real page's query_selector. The screenshot
        recipe verb uses this to scope capture to an element.
        """
        return await self._page.query_selector(selector)
