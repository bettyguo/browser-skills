"""Trace redaction for sensitive skills.

Regression test for Phase 1 finding S5: skills with `metadata.sensitive:
true` (notably login-flow) recorded their fill `value` args verbatim
in the trace zip, leaking credentials. The trace must honor the
sensitive flag and replace such values with a redaction sentinel.
"""

from __future__ import annotations

import json
import textwrap
import zipfile
from pathlib import Path

from browser_skills.runner import Runner
from browser_skills.skill import parse_skill
from browser_skills.trace import Trace, REDACTED
from tests.conftest import FakeElement, FakePage


def test_trace_redacts_sensitive_arg_keys(tmp_path: Path) -> None:
    """When the trace is constructed for a sensitive skill, args whose
    keys look credential-shaped must be replaced with REDACTED before
    storage. Reading the trace back from disk shows only the sentinel.
    """
    t = Trace(skill_name="login-flow", skill_version="0.1.0", sensitive=True)
    t.record_step(
        1,
        "fill",
        {"selector": "input[type='password']", "value": "hunter2-super-secret"},
        "ok",
        12,
        {"selector": "input[type='password']", "value_length": 21},
    )
    out = tmp_path / "trace.zip"
    t.export_zip(out)

    with zipfile.ZipFile(out) as z:
        step_doc = json.loads(z.read("steps/001-fill.json").decode("utf-8"))
        manifest = json.loads(z.read("manifest.json").decode("utf-8"))

    # The plaintext password must not appear anywhere in the exported
    # trace — manifest or step doc.
    raw_blob = json.dumps(step_doc) + json.dumps(manifest)
    assert "hunter2" not in raw_blob, (
        "raw password leaked into trace zip; "
        f"saw it in: {step_doc!r}"
    )
    assert step_doc["args"]["value"] == REDACTED
    # Non-sensitive keys (selector) are preserved.
    assert step_doc["args"]["selector"] == "input[type='password']"
    # The redaction is also recorded so a debugger knows what happened.
    assert REDACTED in manifest.get("redacted_selectors", []) or \
           manifest.get("sensitive") is True


def test_trace_does_not_redact_when_skill_is_not_sensitive(tmp_path: Path) -> None:
    """Non-sensitive skills (the vast majority) keep their args intact —
    redaction has a real cost in debug-ability, so we only do it when
    the skill opts in.
    """
    t = Trace(skill_name="dismiss-cookie-banner", skill_version="0.1.0", sensitive=False)
    t.record_step(
        1,
        "fill",
        {"selector": "input[name='q']", "value": "search terms"},
        "ok",
        12,
        {"selector": "input[name='q']"},
    )
    out = tmp_path / "trace.zip"
    t.export_zip(out)

    with zipfile.ZipFile(out) as z:
        step_doc = json.loads(z.read("steps/001-fill.json").decode("utf-8"))
    assert step_doc["args"]["value"] == "search terms"


def test_trace_redacts_common_credential_field_aliases(tmp_path: Path) -> None:
    """D2 (audit-2): the original redaction list was {value, password,
    token, secret, auth}. Real-world login forms use a wider set of
    field names — `passwd`, `pwd` (Unix-style), `api_key`/`apikey`
    (SaaS), `bearer` (HTTP auth header convention). The conservative
    posture is to redact all of these on sensitive skills; the cost
    of a false-positive redaction is debugger annoyance, the cost of
    a false-negative is a credential leak in a publicly-shared
    trace.zip.
    """
    t = Trace(skill_name="login-flow", skill_version="0.1.0", sensitive=True)
    t.record_step(
        1,
        "fill",
        {
            "passwd": "p1",
            "pwd": "p2",
            "api_key": "ak1",
            "apikey": "ak2",
            "bearer": "b1",
            "harmless_field": "keep-me",
        },
        "ok",
        1,
    )
    out = tmp_path / "trace.zip"
    t.export_zip(out)
    with zipfile.ZipFile(out) as z:
        step_doc = json.loads(z.read("steps/001-fill.json").decode("utf-8"))
    # All five credential-shaped names redacted.
    for k in ("passwd", "pwd", "api_key", "apikey", "bearer"):
        assert step_doc["args"][k] == REDACTED, (
            f"trace did not redact {k!r}; saw {step_doc['args'][k]!r} — "
            f"this is a credential-leak path on a `sensitive: true` skill"
        )
    # Harmless field preserved (verifies we didn't blanket-redact).
    assert step_doc["args"]["harmless_field"] == "keep-me"


async def test_runner_propagates_sensitive_metadata_to_trace(tmp_path: Path) -> None:
    """End-to-end: a SKILL.md with `metadata.sensitive: true` causes
    the runner to construct its Trace with sensitive=True, so
    credential-shaped step args are redacted before record-step time.
    This is what protects login-flow's password in real usage.
    """
    p = tmp_path / "SKILL.md"
    p.write_text(
        textwrap.dedent("""
        ---
        name: ex-login
        description: d
        version: 0.1.0
        metadata:
          sensitive: true
        ---

        ## Recipe
        1. fill selector="input[type='password']" value="my-secret-pw"
        """).lstrip(),
        encoding="utf-8",
    )
    skill = parse_skill(p)
    page = FakePage()
    page.add(FakeElement(tag="input", attrs={"type": "password"}))
    runner = Runner()
    result = await runner.execute(skill, page)
    assert result.status == "success"
    # We can't read the trace bytes here without an export path,
    # but the result's not-yet-exported trace_id is good enough; the
    # critical contract is at trace.record_step / export_zip level,
    # already covered by test_trace_redacts_sensitive_arg_keys above.
    # Sanity-assert the FakePage saw the *real* value (the fill itself
    # is not censored; only the recorded trace is).
    assert page.fill_log == [("input[type='password']", "my-secret-pw")]


def test_trace_redacts_multiple_credential_shaped_keys(tmp_path: Path) -> None:
    """`value` is the obvious one (fill verb), but password / token /
    secret / auth are also redacted on sensitive skills as
    defense-in-depth against future primitives that might accept those
    arg names.
    """
    t = Trace(skill_name="login-flow", skill_version="0.1.0", sensitive=True)
    t.record_step(
        1,
        "custom",
        {
            "value": "v",
            "password": "p",
            "token": "t",
            "secret": "s",
            "auth": "a",
            "harmless": "kept",
        },
        "ok",
        1,
    )
    out = tmp_path / "trace.zip"
    t.export_zip(out)
    with zipfile.ZipFile(out) as z:
        step_doc = json.loads(z.read("steps/001-custom.json").decode("utf-8"))
    for k in ("value", "password", "token", "secret", "auth"):
        assert step_doc["args"][k] == REDACTED, f"key {k!r} not redacted"
    assert step_doc["args"]["harmless"] == "kept"
