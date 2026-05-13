"""Regression test for an earlier audit.

The integration-test module used to call `asyncio.run(_chromium_available())`
at module-import time, launching Chromium during pytest collection
just to decide whether to skip. That added ~2s to every test run and
broke under nested event loops.

This test just verifies the collection of `test_integration_playwright`
doesn't trigger a Chromium launch — we check by ensuring the module
can be imported without an event loop running (the old code raised
`RuntimeError: asyncio.run() cannot be called from a running event loop`
in that scenario).
"""
from __future__ import annotations

import importlib


def test_integration_module_imports_without_launching_chromium() -> None:
    """Importing the module must not eagerly launch a real browser.

    If `asyncio.run(...)` runs at import time, this test (which is
    itself running under pytest-asyncio's event loop in a separate
    test) wouldn't notice — pytest-asyncio uses a per-test loop. The
    real protection is that the import itself is fast and doesn't
    require any network or browser to succeed. We assert on the
    presence of a lazy-skip decorator instead of an eager constant.
    """
    mod = importlib.import_module("tests.test_integration_playwright")
    # The module should NOT carry a module-level `CHROMIUM_AVAILABLE`
    # constant — that was the symptom of eager evaluation. It should
    # expose a `skip_no_chromium` decorator that defers the check.
    assert hasattr(mod, "skip_no_chromium"), (
        "expected lazy chromium-skip decorator on integration module"
    )
    assert not hasattr(mod, "CHROMIUM_AVAILABLE"), (
        "test_integration_playwright still has a module-level "
        "CHROMIUM_AVAILABLE constant — chromium-availability detection "
        "is happening eagerly at import time (an earlier audit)."
    )
