"""Benchmark runner — exercise the v1 skills against the curated site list.

Two modes:
  --quick: skip-import-only (matcher recall against snapshotted page states)
  --full:  drive a real Chromium against the live sites

Quick mode is what runs in CI on every PR (deterministic, no network).
Full mode runs weekly via the GitHub Actions cron in .github/workflows/benchmark.yml.

Outputs a single JSON to --output (defaults to benchmarks/results.json) with
per-skill / per-site success and timing.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO_ROOT / "skills"
SITES_FILE = REPO_ROOT / "benchmarks" / "sites.yaml"


@dataclass
class SiteResult:
    site_id: str
    url: str
    skill_results: dict[str, dict[str, Any]] = field(default_factory=dict)
    matcher_top: list[str] = field(default_factory=list)
    error: str | None = None
    duration_ms: int = 0


@dataclass
class BenchmarkReport:
    mode: str
    ran_at: float
    python_version: str
    n_sites: int
    n_skills: int
    sites: list[SiteResult] = field(default_factory=list)
    aggregate: dict[str, Any] = field(default_factory=dict)


def _load_sites() -> list[dict[str, Any]]:
    with SITES_FILE.open(encoding="utf-8") as f:
        doc = yaml.safe_load(f)
    return doc.get("sites", [])


def _load_skills() -> list[Any]:
    from browser_skills.skill import load_bundle

    return load_bundle(SKILLS_DIR)


def _filter_sites(sites: list[dict], limit: int, site: str | None) -> list[dict]:
    if site:
        sites = [s for s in sites if s.get("id") == site]
    if limit and limit > 0:
        sites = sites[:limit]
    return sites


def _quick_mode(limit: int = 0, site: str | None = None) -> BenchmarkReport:
    """Matcher-only benchmark — STRUCTURAL CHECK, not real-world recall.

    For v0.1.0 we don't have DOM snapshots yet. Quick mode feeds the
    matcher a *synthesized* dom_summary built from each site's `skills`
    hint list in sites.yaml. So the resulting "matcher_recall_pct" is
    really "does our matcher reach threshold under the baseline scoring
    rules for the v1 skills?" — useful as a parser/load sanity check
    in CI, useless as an accuracy claim. The aggregate `notes` field
    surfaces this limitation in the output.

    For real-world measurement, use `--mode=full`.
    """
    from browser_skills.matcher import PageState, match

    sites = _filter_sites(_load_sites(), limit, site)
    skills = _load_skills()
    report = BenchmarkReport(
        mode="quick",
        ran_at=time.time(),
        python_version=sys.version.split()[0],
        n_sites=len(sites),
        n_skills=len(skills),
    )
    sites_with_match = 0
    for s in sites:
        sr = SiteResult(site_id=s["id"], url=s["url"])
        # Synthesize a minimal PageState from the sites.yaml `skills` hints
        synthetic_markers = " ".join(
            f"<{tag}>" for tag in s.get("skills", [])
        )
        state = PageState(
            url=s["url"],
            dom_summary=synthetic_markers,
            cookies_present=True,
            is_initial_load=True,
        )
        result = match(skills, state)
        sr.matcher_top = [m.name for m in result.skills[:3]]
        if sr.matcher_top:
            sites_with_match += 1
        report.sites.append(sr)

    report.aggregate = {
        "sites_with_matcher_hit": sites_with_match,
        "matcher_recall_pct": round(100.0 * sites_with_match / max(1, len(sites)), 1),
        "skills_loaded": [s.name for s in skills],
        # D4 honesty: quick mode feeds the matcher a *synthetic* DOM
        # built from the `skills` hints in sites.yaml, not real page
        # HTML. The recall number above is a structural sanity check
        # (does each skill at least score above threshold under
        # baseline conditions?), not a measurement of real-world
        # matcher accuracy. Use `--mode=full` for that.
        "notes": (
            "matcher_recall_pct is a structural check against synthetic DOM, "
            "not real-world recall. Use --mode=full for live measurement."
        ),
    }
    return report


async def _full_mode(limit: int = 0, site: str | None = None) -> BenchmarkReport:
    """Real-Chromium benchmark. Opens each site, runs the matcher, then
    invokes the top-2 deterministic skills, and records timing/success.
    """
    try:
        from playwright.async_api import async_playwright
    except ImportError as e:
        raise RuntimeError(
            "playwright not installed; pip install browser-skills[dev]"
        ) from e

    from browser_skills.adapters.playwright_raw import PlaywrightPage
    from browser_skills.matcher import PageState, match
    from browser_skills.runner import Runner

    sites = _filter_sites(_load_sites(), limit, site)
    skills = _load_skills()
    skills_by_name = {s.name: s for s in skills}
    report = BenchmarkReport(
        mode="full",
        ran_at=time.time(),
        python_version=sys.version.split()[0],
        n_sites=len(sites),
        n_skills=len(skills),
    )
    runner = Runner()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            for s in sites:
                t0 = time.perf_counter()
                sr = SiteResult(site_id=s["id"], url=s["url"])
                ctx = await browser.new_context(
                    viewport={"width": 1280, "height": 800}
                )
                page = await ctx.new_page()
                try:
                    await page.goto(s["url"], timeout=20000, wait_until="domcontentloaded")
                    dom = await page.content()
                    state = PageState(
                        url=page.url,
                        dom_summary=dom[:4000],
                        cookies_present=True,
                        is_initial_load=True,
                    )
                    match_result = match(skills, state)
                    sr.matcher_top = [m.name for m in match_result.skills[:3]]

                    wrapped = PlaywrightPage(page)
                    for m in match_result.skills[:2]:
                        skill = skills_by_name.get(m.name)
                        if skill is None:
                            continue
                        result = await runner.execute(skill, wrapped)
                        sr.skill_results[m.name] = {
                            "status": result.status,
                            "deterministic": result.deterministic_path,
                            "duration_ms": result.duration_ms,
                            "failure_reason": result.failure_reason,
                        }
                except Exception as e:  # noqa: BLE001
                    sr.error = f"{type(e).__name__}: {e}"
                finally:
                    await ctx.close()
                sr.duration_ms = int((time.perf_counter() - t0) * 1000)
                report.sites.append(sr)
        finally:
            await browser.close()

    # Aggregate
    total_runs = sum(len(s.skill_results) for s in report.sites)
    successes = sum(
        1
        for s in report.sites
        for r in s.skill_results.values()
        if r["status"] == "success"
    )
    report.aggregate = {
        "total_skill_runs": total_runs,
        "success_count": successes,
        "success_rate_pct": round(100.0 * successes / max(1, total_runs), 1),
        "sites_with_error": sum(1 for s in report.sites if s.error),
    }
    return report


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="browser-skills benchmark runner")
    p.add_argument("--mode", choices=["quick", "full"], default="quick")
    p.add_argument("--quick", action="store_true", help="alias for --mode=quick")
    p.add_argument("--output", default=str(REPO_ROOT / "benchmarks" / "results.json"))
    p.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Stop after the first N sites (0 = all). Useful for spot-checking --mode=full.",
    )
    p.add_argument(
        "--site",
        help="Restrict to a single site_id from benchmarks/sites.yaml.",
    )
    args = p.parse_args(argv)
    mode = "quick" if args.quick else args.mode

    if mode == "quick":
        report = _quick_mode(limit=args.limit, site=args.site)
    else:
        report = asyncio.run(_full_mode(limit=args.limit, site=args.site))

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(_to_dict(report), indent=2), encoding="utf-8")

    print(f"benchmark wrote {out} ({report.mode} mode)")
    print(f"  sites: {report.n_sites}")
    print(f"  skills: {report.n_skills}")
    for k, v in report.aggregate.items():
        print(f"  {k}: {v}")
    return 0


def _to_dict(report: BenchmarkReport) -> dict[str, Any]:
    return {
        "mode": report.mode,
        "ran_at": report.ran_at,
        "python_version": report.python_version,
        "n_sites": report.n_sites,
        "n_skills": report.n_skills,
        "aggregate": report.aggregate,
        "sites": [asdict(s) for s in report.sites],
    }


if __name__ == "__main__":
    raise SystemExit(main())
