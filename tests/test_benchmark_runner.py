"""Benchmark-runner tests.

quick-mode reports a `matcher_recall_pct` derived from DOMs synthesized
from sites.yaml, not real page HTML. The aggregate must flag that.
"""
from __future__ import annotations

from benchmarks.run import _quick_mode


def test_quick_mode_aggregate_has_notes_field() -> None:
    """The aggregate must include a `notes` field warning that the
    recall metric is structural only, not measured against live pages.
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
