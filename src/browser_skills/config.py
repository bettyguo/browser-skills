"""Process-wide runtime configuration. Module-level mutable state, kept
small on purpose. Tests reset via reset_for_test().
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from browser_skills.primitives.vision_fallback import VisionAdapter


vision_adapter: VisionAdapter | None = None
forbid_headed: bool = False


def set_vision_adapter(adapter: VisionAdapter | None) -> None:
    """Install (or clear) the vision adapter."""
    global vision_adapter
    vision_adapter = adapter


def reset_for_test() -> None:
    """Clear all process-wide state. Called from pytest fixtures."""
    global vision_adapter, forbid_headed
    vision_adapter = None
    forbid_headed = False
