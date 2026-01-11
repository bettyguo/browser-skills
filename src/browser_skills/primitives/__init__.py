"""Action-verb primitives. Each verb is registered in REGISTRY and resolved
by the runner.

Primitives are async; they accept a Playwright-like Page protocol so they
can be unit-tested against fakes. See tests/conftest.py for the test fake.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Protocol


class StepRetryable(RuntimeError):
    """Transient failure; runner may retry the step."""


class StepFailed(RuntimeError):
    """Permanent failure for this step; runner gives up on the recipe."""


class PageLike(Protocol):
    """The slice of Playwright's Page interface our primitives use.

    Defined as a Protocol so primitives can be tested against a fake page
    without spinning up a real browser.
    """

    async def wait_for_load_state(self, state: str = ..., *, timeout: int = ...) -> None: ...
    async def wait_for_selector(
        self, selector: str, *, state: str = ..., timeout: int = ...
    ) -> Any: ...
    async def click(self, selector: str, *, timeout: int = ...) -> None: ...
    async def fill(self, selector: str, value: str, *, timeout: int = ...) -> None: ...
    async def evaluate(self, expression: str, *args: Any) -> Any: ...
    @property
    def url(self) -> str: ...


PrimitiveFn = Callable[..., Awaitable[dict[str, Any]]]

REGISTRY: dict[str, PrimitiveFn] = {}


def register(name: str) -> Callable[[PrimitiveFn], PrimitiveFn]:
    def deco(fn: PrimitiveFn) -> PrimitiveFn:
        REGISTRY[name] = fn
        return fn

    return deco


# Importing the submodules registers their primitives.
from browser_skills.primitives import (  # noqa: E402,F401
    assertions,
    click,
    extract,
    form,
    scroll,
    vision_fallback,
    wait,
)

__all__ = [
    "REGISTRY",
    "register",
    "PageLike",
    "StepRetryable",
    "StepFailed",
]
