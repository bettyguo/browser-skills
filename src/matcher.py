"""Matcher — scores skill applicability given a PageState.

See docs/matcher-design.md for the rationale and scoring rules.
"""
from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from typing import Literal

from browser_skills.skill import Skill


_QUOTED_STR_RE = re.compile(r"""['"]([^'"]+)['"]""")


def _marker_signatures(marker: str) -> list[str]:
    """Reduce a SKILL.md `dom_markers:` entry to a list of substrings
    that are likely to actually appear in a page's HTML.

    Authors write markers as CSS selectors (`[class*='newsletter' i]`,
    `iframe[src*='challenges.cloudflare.com']`, `#onetrust-banner-sdk`),
    but the matcher's `dom_summary` is raw HTML, where those selectors
    don't appear as literal text. We pick out:
      - the marker as-is (in case authors wrote a literal substring),
      - any content inside quotes (the discriminating value),
      - the marker stripped of non-alnum chars (legacy id/class style).
    Caller takes the union and substring-tests each.
    """
    sigs: list[str] = [marker.lower()]
    for q in _QUOTED_STR_RE.findall(marker):
        if q:
            sigs.append(q.lower())
    stripped = "".join(c for c in marker if c.isalnum() or c in ("-", "_")).lower()
    if stripped:
        sigs.append(stripped)
    # Deduplicate while preserving order.
    seen: set[str] = set()
    out: list[str] = []
    for s in sigs:
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


THRESHOLD = 20.0


@dataclass
class PageState:
    url: str
    title: str | None = None
    dom_summary: str = ""
    visible_text_sample: str = ""
    cookies_present: bool = False
    is_initial_load: bool = True


@dataclass
class SkillMatch:
    name: str
    score: float
    confidence: Literal["high", "medium", "low"]
    signals: list[str] = field(default_factory=list)


@dataclass
class MatchResult:
    skills: list[SkillMatch]
    rationale: str
    matched_in_ms: int


def match(skills: list[Skill], state: PageState) -> MatchResult:
    import time

    t = time.perf_counter()
    results: list[SkillMatch] = []
    for skill in skills:
        score, signals = _score(skill, state)
        if score >= THRESHOLD:
            results.append(
                SkillMatch(
                    name=skill.name,
                    score=score,
                    confidence=_confidence(score),
                    signals=signals,
                )
            )
    results.sort(key=lambda m: m.score, reverse=True)
    elapsed = int((time.perf_counter() - t) * 1000)
    return MatchResult(
        skills=results[:10],
        rationale=_rationale(results, state),
        matched_in_ms=elapsed,
    )


def _score(skill: Skill, state: PageState) -> tuple[float, list[str]]:
    score = 0.0
    signals: list[str] = []

    # URL-pattern match
    for pattern in skill.url_patterns:
        if fnmatch.fnmatch(state.url, pattern) and pattern != "*":
            score += 100
            signals.append(f"url_pattern:{pattern}")
            break
    else:
        if "*" in skill.url_patterns:
            score += 5  # very mild — `*` is the catch-all
            signals.append("url_pattern:wildcard")

    # DOM-marker match
    if skill.dom_markers:
        haystack = state.dom_summary.lower()
        for marker in skill.dom_markers:
            signatures = _marker_signatures(marker)
            literal = signatures[0]  # the marker itself, lowercased
            if literal in haystack:
                score += 50
                signals.append(f"dom_marker:{marker[:32]}")
                continue
            # Try each weaker signature (quoted-string content, stripped form)
            for sig in signatures[1:]:
                if sig in haystack:
                    score += 20
                    signals.append(f"dom_marker_partial:{sig[:32]}")
                    break

    # Page-state signals (per-skill hand-tuned bumps)
    if skill.name == "verify-page-loaded" and state.is_initial_load:
        score += 30
        signals.append("is_initial_load")
    if (
        skill.name == "dismiss-cookie-banner"
        and state.is_initial_load
        and state.cookies_present
    ):
        # +80 (not +30) because the cookie banner skill is more
        # *specific* than the generic handle-modal-dialog skill, but
        # nearly every modern banner ALSO uses aria-modal markup —
        # without this bump, modal-dialog's two strong-marker hits
        # leapfrog cookie-banner on a banner-bearing page. The matcher
        # design doc calls out "hand-tuned scoring rules per skill
        # type" specifically for cases like this.
        score += 80
        signals.append("is_initial_load+cookies")
    if skill.name == "detect-captcha":
        dom_lower = state.dom_summary.lower()
        # Recognize the major providers' distinct iframe / class
        # signatures, not just the literal word "captcha." Cloudflare
        # Turnstile pages don't mention "captcha" by name.
        captcha_signals = (
            "captcha",
            "challenges.cloudflare.com",
            "g-recaptcha",
            "h-captcha",
            "cf-turnstile",
        )
        if any(sig in dom_lower for sig in captcha_signals):
            score += 80
            signals.append("captcha_marker")

    # Description keyword nudge
    desc = skill.description.lower()
    for kw in _extract_keywords(state):
        if kw in desc:
            score += 10
            signals.append(f"desc_keyword:{kw}")

    # Penalize over-applicability
    applies_to = skill.metadata.get("applies_to")
    if applies_to == "any-website":
        score *= 0.9
        signals.append("applies_to_any_penalty")

    return score, signals


def _confidence(score: float) -> Literal["high", "medium", "low"]:
    if score >= 100:
        return "high"
    if score >= 50:
        return "medium"
    return "low"


def _extract_keywords(state: PageState) -> list[str]:
    """Heuristic keyword pull from the visible text sample."""
    words: set[str] = set()
    for token in state.visible_text_sample.lower().split():
        t = token.strip(".,;:!?()[]'\"")
        if len(t) > 4 and t.isalpha():
            words.add(t)
    return sorted(words)[:50]


def _rationale(matches: list[SkillMatch], state: PageState) -> str:
    if not matches:
        return f"No skills scored above threshold ({THRESHOLD}) for {state.url}."
    top = matches[0]
    return (
        f"{len(matches)} skill(s) above threshold for {state.url}. "
        f"Top: {top.name} (score={top.score:.1f}, signals={', '.join(top.signals)})."
    )
