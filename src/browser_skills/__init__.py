"""browser-skills — reusable site-pattern recipes for browser-using agents.

Conforms to the agentskills.io specification. See docs/skill-recipe-format.md
for the recipe convention used inside SKILL.md bodies.
"""

__version__ = "0.3.0"

from browser_skills.skill import (
    BrowserSkillsError,
    Recipe,
    Skill,
    SkillParseError,
    SkillResult,
    Step,
)
from browser_skills.runner import Runner

__all__ = [
    "BrowserSkillsError",
    "Recipe",
    "Runner",
    "Skill",
    "SkillParseError",
    "SkillResult",
    "Step",
    "__version__",
]
