"""Cheap, browser-launch-free check for an installed Chromium.

Asks `python -m playwright install --dry-run chromium` to print the
path it would install to, then checks whether that path exists on
disk. This is the same logic that `doctor` and the integration-test
skip decorator both need; this module is the single source of truth.

Public:
  chromium_install_path() -> Path | None
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


_INSTALL_LOCATION_RE = re.compile(
    r"install location:\s*(.+)$", re.IGNORECASE | re.MULTILINE
)


def chromium_install_path() -> Path | None:
    """Return the Path where Playwright has Chromium installed, or None
    if the binary is missing / Playwright itself isn't installed / the
    subprocess timed out.

    Synchronous; no event loop required. Subprocess timeout: 10s.
    Caller is responsible for caching if they invoke repeatedly.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "--dry-run", "chromium"],
            capture_output=True,
            timeout=10,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if result.returncode != 0:
        return None
    out = (result.stdout + result.stderr).decode("utf-8", errors="replace")
    m = _INSTALL_LOCATION_RE.search(out)
    if not m:
        return None
    candidate = Path(m.group(1).strip())
    return candidate if candidate.exists() else None
