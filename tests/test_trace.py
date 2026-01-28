"""Trace zip export tests."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from browser_skills.trace import Trace


def test_trace_records_steps_and_exports_zip(tmp_path: Path) -> None:
    t = Trace(skill_name="ex", skill_version="0.1.0", url="https://example.test/")
    t.record_step(1, "wait", {"extra": 100}, "ok", 12, {"slept_ms": 100})
    t.record_step(2, "click", {"selector": "#go"}, "ok", 30, {"selector": "#go"})
    t.record_event("recipe_end", status="success")
    out = tmp_path / "trace.zip"
    t.export_zip(out)
    assert out.exists()
    with zipfile.ZipFile(out) as z:
        names = z.namelist()
        assert "manifest.json" in names
        assert "README.txt" in names
        assert "steps/001-wait.json" in names
        assert "steps/002-click.json" in names
        manifest = json.loads(z.read("manifest.json").decode("utf-8"))
    assert manifest["skill"] == "ex"
    assert manifest["step_count"] == 2
    assert any(e["kind"] == "recipe_end" for e in manifest["events"])
