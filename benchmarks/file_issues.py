"""Open `stale-selector` issues for skills that newly failed in the latest
benchmark run.

Heuristic: any (site × skill) pair whose status flipped from success → failed
since the previous published results becomes an issue. We don't re-file for
already-open issues with the same `site_id:skill_name` label combination.

Designed for the weekly benchmark cron in .github/workflows/benchmark.yml.
Locally, this script is a no-op unless GITHUB_TOKEN is set and the
benchmarks/_runs/ history is present.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any


HISTORY_DIR = Path("benchmarks/_runs")


def _read(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _previous_report() -> dict[str, Any] | None:
    if not HISTORY_DIR.exists():
        return None
    runs = sorted(HISTORY_DIR.glob("results-*.json"))
    if not runs:
        return None
    return _read(runs[-1])


def _flatten(report: dict[str, Any]) -> dict[tuple[str, str], str]:
    """{(site_id, skill_name): status}"""
    out: dict[tuple[str, str], str] = {}
    for site in report.get("sites", []):
        site_id = site.get("site_id", "?")
        for skill, sresult in site.get("skill_results", {}).items():
            out[(site_id, skill)] = sresult.get("status", "?")
    return out


def _diff_regressions(prev: dict, current: dict) -> list[tuple[str, str]]:
    prev_map = _flatten(prev) if prev else {}
    curr_map = _flatten(current)
    regressions: list[tuple[str, str]] = []
    for key, status in curr_map.items():
        if status != "success" and prev_map.get(key) == "success":
            regressions.append(key)
    return regressions


def _existing_issue_titles(token: str, repo: str) -> set[str]:
    """Fetch open issues with the `stale-selector` label."""
    import urllib.request

    url = (
        f"https://api.github.com/repos/{repo}/issues?"
        f"state=open&labels=stale-selector&per_page=100"
    )
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
        data = json.loads(resp.read().decode("utf-8"))
    return {item["title"] for item in data}


def _create_issue(token: str, repo: str, title: str, body: str) -> None:
    import urllib.request

    payload = json.dumps(
        {"title": title, "body": body, "labels": ["stale-selector", "ci"]}
    ).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.github.com/repos/{repo}/issues",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
        if resp.status not in (200, 201):
            raise RuntimeError(f"create_issue failed: HTTP {resp.status}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="File issues for newly-failing skills")
    p.add_argument("--input", default="benchmarks/results.json")
    p.add_argument(
        "--repo",
        default=os.environ.get("GITHUB_REPOSITORY", "browser-skills/browser-skills"),
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be filed without calling the API",
    )
    args = p.parse_args(argv)

    in_path = Path(args.input)
    if not in_path.exists():
        print(f"missing {in_path}; nothing to compare", file=sys.stderr)
        return 0  # graceful no-op

    current = _read(in_path)
    prev = _previous_report()
    regressions = _diff_regressions(prev, current)

    if not regressions:
        print("no regressions detected")
        return 0

    print(f"detected {len(regressions)} regression(s):")
    for site_id, skill in regressions:
        print(f"  - {site_id} × {skill}")

    if args.dry_run:
        return 0

    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("no GITHUB_TOKEN; skipping issue creation", file=sys.stderr)
        return 0

    existing = _existing_issue_titles(token, args.repo)
    filed = 0
    for site_id, skill in regressions:
        title = f"stale selector: {skill} on {site_id}"
        if title in existing:
            print(f"already filed: {title}")
            continue
        body = (
            f"`{skill}` failed on site `{site_id}` in the latest benchmark run.\n\n"
            f"This was a regression from the previous run. The selector list in "
            f"`skills/{skill}/SKILL.md` likely needs an update.\n\n"
            f"Run `python benchmarks/run.py --mode=full` to reproduce, then "
            f"`browser-skills test {skill} --headed --fixture <path>` against a "
            f"local copy of the page.\n\n"
            f"Filed automatically by `benchmarks/file_issues.py`."
        )
        _create_issue(token, args.repo, title, body)
        filed += 1
    print(f"filed {filed} new issue(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
