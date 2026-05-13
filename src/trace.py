"""Trace recording. One trace per skill execution. Zip export on demand."""
from __future__ import annotations

import json
import secrets
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# Sentinel substituted into the trace in place of credential-shaped
# values when the skill is marked `sensitive: true` in its metadata.
# Stable string so consumers can detect redaction unambiguously.
REDACTED = "[REDACTED]"

# Arg keys that look credential-shaped. Redacted on sensitive skills.
# Be deliberately conservative — false-positive redaction is a debug
# annoyance; false-negative redaction is a credential leak in a
# publicly-shared trace zip. Includes common Unix (`passwd`, `pwd`)
# and SaaS (`api_key`, `apikey`, `bearer`) aliases as well as the
# canonical names.
_REDACT_ARG_KEYS = frozenset(
    {
        # Generic credential containers
        "value",
        "password", "passwd", "pwd",
        # Tokens / keys / secrets / auth
        "token", "secret", "auth", "bearer",
        "api_key", "apikey", "api-key",
    }
)


def _new_trace_id() -> str:
    return f"tr_{secrets.token_hex(6)}"


def _maybe_redact(args: dict[str, Any], sensitive: bool) -> dict[str, Any]:
    """Return a shallow copy of `args` with credential-shaped values
    replaced by REDACTED, if `sensitive` is True. Non-sensitive traces
    pass through unchanged.
    """
    if not sensitive:
        return args
    return {
        k: (REDACTED if k.lower() in _REDACT_ARG_KEYS else v)
        for k, v in args.items()
    }


@dataclass
class Trace:
    trace_id: str = field(default_factory=_new_trace_id)
    started_at: float = field(default_factory=time.time)
    steps: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    skill_name: str | None = None
    skill_version: str | None = None
    url: str | None = None
    sensitive: bool = False
    redacted_selectors: list[str] = field(default_factory=list)

    def record_step(
        self,
        index: int,
        verb: str,
        args: dict[str, Any],
        outcome: str,
        duration_ms: int,
        detail: dict[str, Any] | None = None,
    ) -> None:
        recorded_args = _maybe_redact(args, self.sensitive)
        # `detail` may also carry the same credential-shaped keys (e.g.,
        # fill returns `{"value_length": N}` which is fine, but a custom
        # primitive might echo a value). Redact symmetrically.
        recorded_detail = _maybe_redact(detail, self.sensitive) if detail else {}
        self.steps.append(
            {
                "index": index,
                "verb": verb,
                "args": recorded_args,
                "outcome": outcome,
                "duration_ms": duration_ms,
                "detail": recorded_detail,
                "t_offset_ms": int((time.time() - self.started_at) * 1000),
            }
        )

    def record_event(self, kind: str, **fields: Any) -> None:
        self.events.append(
            {
                "kind": kind,
                "t_offset_ms": int((time.time() - self.started_at) * 1000),
                **fields,
            }
        )

    def to_manifest(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "skill": self.skill_name,
            "skill_version": self.skill_version,
            "url": self.url,
            "started_at": self.started_at,
            "duration_ms": int((time.time() - self.started_at) * 1000),
            "step_count": len(self.steps),
            "events": self.events,
            "sensitive": self.sensitive,
            "redacted_selectors": self.redacted_selectors,
        }

    def export_zip(self, out_path: str | Path) -> Path:
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr("manifest.json", json.dumps(self.to_manifest(), indent=2))
            for step in self.steps:
                fname = f"steps/{step['index']:03d}-{step['verb']}.json"
                z.writestr(fname, json.dumps(step, indent=2))
            z.writestr("README.txt", self._readme_text())
        return out_path

    def _readme_text(self) -> str:
        lines = [
            f"browser-skills trace {self.trace_id}",
            f"skill: {self.skill_name} v{self.skill_version}",
            f"url: {self.url}",
            f"started: {self.started_at}",
            f"steps: {len(self.steps)}",
            "",
            "Step summary:",
        ]
        for s in self.steps:
            lines.append(
                f"  {s['index']:03d} {s['verb']:24s} -> {s['outcome']:8s} ({s['duration_ms']}ms)"
            )
        return "\n".join(lines) + "\n"
