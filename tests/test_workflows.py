"""Workflow file invariants — small static checks that protect the
CI/cron pipelines from silent regressions where the YAML still parses
but doesn't do what its name promises.

Regression tests for Phase 2 audit findings C1, C4, C5, plus a D4
metric-honesty test on the benchmark runner.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
BENCHMARK_YML = REPO_ROOT / ".github" / "workflows" / "benchmark.yml"
DCO_YML = REPO_ROOT / ".github" / "workflows" / "dco.yml"


def _load_workflow() -> dict:
    with BENCHMARK_YML.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def _step_run_commands(workflow: dict) -> list[str]:
    """Return the `run:` block of every step across all jobs, as strings."""
    runs: list[str] = []
    for job in workflow.get("jobs", {}).values():
        for step in job.get("steps", []):
            run = step.get("run")
            if isinstance(run, str):
                runs.append(run)
    return runs


def test_weekly_benchmark_deploys_to_github_pages() -> None:
    """C5: publish.py generates benchmarks/_site/index.html locally on
    the runner, but the previous workflow had no step to upload or
    deploy it. Without an upload-pages-artifact step (or equivalent),
    the HTML is discarded with the runner.
    """
    wf = _load_workflow()
    uses_actions: list[str] = []
    for job in wf.get("jobs", {}).values():
        for step in job.get("steps", []):
            uses = step.get("uses")
            if isinstance(uses, str):
                uses_actions.append(uses)
    # Any one of these is acceptable:
    #  - actions/upload-pages-artifact + actions/deploy-pages
    #  - peaceiris/actions-gh-pages
    #  - JamesIves/github-pages-deploy-action
    deploy_actions = (
        "actions/upload-pages-artifact",
        "actions/deploy-pages",
        "peaceiris/actions-gh-pages",
        "JamesIves/github-pages-deploy-action",
    )
    assert any(
        any(u.startswith(d) for d in deploy_actions) for u in uses_actions
    ), (
        f"benchmark workflow generates _site/ but never deploys it; "
        f"expected one of {deploy_actions}, got uses: {uses_actions}"
    )


def test_weekly_benchmark_archives_results_into_history() -> None:
    """C4: file_issues.py diffs the current run against the latest file in
    benchmarks/_runs/. If the workflow never writes into _runs/, the diff
    is always against nothing and regression detection is a no-op.

    The workflow must copy benchmarks/results.json into
    benchmarks/_runs/results-<somethingdated>.json after the run.
    """
    wf = _load_workflow()
    runs = _step_run_commands(wf)
    archive_present = any(
        "benchmarks/_runs" in r and "results.json" in r for r in runs
    )
    assert archive_present, (
        "benchmark workflow must archive results.json into benchmarks/_runs/ "
        "so file_issues.py has history to diff against"
    )


def test_weekly_benchmark_runs_full_mode_not_quick() -> None:
    """C1: the workflow header advertises a real-site benchmark, but
    `python benchmarks/run.py` defaults to --mode=quick (no network).
    The cron must explicitly opt into --mode=full.
    """
    wf = _load_workflow()
    runs = _step_run_commands(wf)
    benchmark_runs = [r for r in runs if "benchmarks/run.py" in r]
    assert benchmark_runs, "expected at least one `benchmarks/run.py` invocation"
    # At least one of them must specify --mode=full (the actual benchmark).
    assert any("--mode=full" in r or "--mode full" in r for r in benchmark_runs), (
        f"weekly cron must invoke benchmarks/run.py with --mode=full; "
        f"got: {benchmark_runs}"
    )


# --- DCO workflow ---------------------------------------------------------


def test_dco_workflow_present_and_triggers_on_pull_request() -> None:
    """F9: every PR must enforce the DCO sign-off line the
    CONTRIBUTING.md requires. A workflow file alone isn't enough — it
    must trigger on pull_request and run a check, not just a noop job.
    """
    assert DCO_YML.exists(), "missing .github/workflows/dco.yml"
    with DCO_YML.open(encoding="utf-8") as f:
        wf = yaml.safe_load(f)
    # `yaml` parses the `on:` key as Python True for some shapes — the
    # canonical YAML loader maps `on:` to the boolean True. Tolerate both.
    triggers = wf.get("on") or wf.get(True)
    assert triggers, "dco.yml must declare an `on:` trigger block"
    assert "pull_request" in triggers, (
        "dco.yml must trigger on pull_request events"
    )
    # Sanity: the job runs at least one step that greps for sign-off.
    runs = _step_run_commands(wf)
    assert any("signed-off-by" in r.lower() for r in runs), (
        "dco.yml must actually check for `Signed-off-by:` in commit messages"
    )
