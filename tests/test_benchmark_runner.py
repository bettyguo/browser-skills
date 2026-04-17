"""Benchmark-runner-level tests.

Regression test for Phase 1 finding D4: quick-mode reports a
`matcher_recall_pct` metric that's meaningless — the input DOM is
synthesized from the `skills` list in sites.yaml, not real page HTML,
so a "100% recall" line is misleading marketing rather than a measure.
The runner must surface this limitation in its output.
"""

from __future__ import annotations

from benchmarks.run import _quick_mode


def test_quick_mode_aggregate_documents_synthetic_dom_limitation() -> None:
    """D4: the aggregate dict in quick-mode output must include a
    `notes` field that warns readers the recall metric is structural
    only, not a real measurement of matcher accuracy on live pages.
    """
    report = _quick_mode(limit=2)
    agg = report.aggregate
    assert "notes" in agg, (
        "quick-mode aggregate is missing the `notes` field that explains "
        "the matcher_recall metric is structural only (sites_with_matcher_hit)"
    )
    note_text = str(agg["notes"]).lower()
    assert "synthetic" in note_text or "structural" in note_text or "quick" in note_text, (
        f"notes field should mention the limitation; got: {agg['notes']!r}"
    )
