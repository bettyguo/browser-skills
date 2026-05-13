"""Vision fallback adapter interface.

Adapters are loaded via entry points or set programmatically:

    browser_skills.config.set_vision_adapter(my_adapter)

Reference adapters for Anthropic / OpenAI / Gemini ship as optional extras
in v1 milestone 2; see 
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from browser_skills.primitives import PageLike, StepFailed, register


@dataclass
class VisionAction:
    verb: str                       # one of the registered primitive verbs
    args: dict[str, Any]
    rationale: str
    tokens_in: int = 0
    tokens_out: int = 0


class VisionAdapter(Protocol):
    async def describe(
        self,
        *,
        image_b64: str,
        intent: str,
        allowed_actions: list[str],
        context: dict[str, Any] | None = None,
    ) -> VisionAction: ...


@register("vision")
async def vision(
    page: PageLike,
    *,
    intent: str,
    scope: str = "viewport",
    allowed_actions: list[str] | None = None,
    **_: Any,
) -> dict[str, Any]:
    """Invoke the configured vision adapter. Raises StepFailed when no adapter
    is configured — caller is expected to detect this and return a clean
    `failed` SkillResult with `failure_reason="no_vision_adapter"`.
    """
    from browser_skills import config

    adapter = config.vision_adapter
    if adapter is None:
        raise StepFailed("vision: no adapter configured")

    # Real implementation will capture a screenshot via Playwright;
    # for now we punt the capture to the runner so this primitive stays
    # testable against a fake page.
    img_b64 = await _capture(page, scope)
    action = await adapter.describe(
        image_b64=img_b64,
        intent=intent,
        allowed_actions=allowed_actions or [],
        context={"url": page.url},
    )
    return {
        "action_proposed": {"verb": action.verb, "args": action.args},
        "rationale": action.rationale,
        "tokens_in": action.tokens_in,
        "tokens_out": action.tokens_out,
    }


async def _capture(page: PageLike, scope: str) -> str:
    """Capture a base64 PNG of the viewport.

    Falls back to an empty string when the page protocol doesn't support
    screenshots (e.g., test fakes). The runner inspects `tokens_in` to
    decide whether vision was meaningfully invoked.
    """
    screenshot = getattr(page, "screenshot", None)
    if screenshot is None:
        return ""
    try:
        png_bytes = await screenshot(full_page=False)
    except Exception:  # noqa: BLE001
        return ""
    import base64

    return base64.b64encode(png_bytes).decode("ascii")
