"""Real-Playwright integration test.

Drives Chromium against a localhost synthetic HTML page through the
full pipeline: navigate → matcher → invoke_skill. Skipped if Chromium
isn't installed (CI installs it via `playwright install chromium`).

Marked `slow` so quick-feedback runs (`pytest tests/ -m 'not slow'`)
can opt out.
"""

from __future__ import annotations

import functools
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import pytest


pytest.importorskip("playwright")


# A page with a OneTrust-style cookie banner and a paginated table.
# Compact enough to embed inline; expressive enough to exercise the
# dismiss-cookie-banner and extract-table-pagination skills.
DEMO_HTML = b"""<!DOCTYPE html>
<html lang='en'>
<head><meta charset='utf-8'><title>browser-skills demo</title>
<style>
  body { font-family: sans-serif; padding: 1rem; }
  #onetrust-banner-sdk {
    position: fixed; bottom: 0; left: 0; right: 0;
    background: #222; color: #fff; padding: 1rem; z-index: 9999;
  }
  table { border-collapse: collapse; margin-top: 1rem; }
  th, td { border: 1px solid #ccc; padding: 0.4rem 0.8rem; }
</style></head>
<body>
  <main>
    <h1>Demo content</h1>
    <table>
      <thead><tr><th>id</th><th>name</th><th>score</th></tr></thead>
      <tbody>
        <tr><td>1</td><td>alpha</td><td>92</td></tr>
        <tr><td>2</td><td>bravo</td><td>87</td></tr>
        <tr><td>3</td><td>charlie</td><td>74</td></tr>
      </tbody>
    </table>
  </main>
  <div id='onetrust-banner-sdk' role='dialog' aria-label='cookie consent'>
    <span>We use cookies for analytics.</span>
    <button id='onetrust-accept-btn-handler'>Accept All Cookies</button>
  </div>
  <script>
    // Hide the banner once accepted so the success criterion passes.
    document.getElementById('onetrust-accept-btn-handler').addEventListener('click', () => {
      document.getElementById('onetrust-banner-sdk').style.display = 'none';
    });
  </script>
</body>
</html>
"""


class _SilentHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(DEMO_HTML)))
        self.end_headers()
        self.wfile.write(DEMO_HTML)

    def log_message(self, *args: Any) -> None:  # noqa: ARG002
        pass


# Chromium's net/base/port_util.cc rejects connections to certain
# ports as security-sensitive (SIP, IRC, NFS, X11, etc.). If the OS
# happens to allocate one to our test server, page.goto() fails with
# net::ERR_UNSAFE_PORT. This list is the subset above the typical
# ephemeral-port floor (~32768 on Linux, 49152 on Windows); under it
# we'd never get one allocated.
_CHROMIUM_UNSAFE_PORTS = frozenset({
    5060, 5061,        # SIP
    6000,              # X11
    6566,              # SANE
    6665, 6666, 6667, 6668, 6669, 6697,  # IRC variants
    10080,             # amanda
})


def _free_port() -> int:
    """Return a port the OS thinks is free AND that Chromium will let
    us connect to. Retries a few times if we land on a Chromium-banned
    port; gives up after 10 attempts because at that point something
    else is wrong with the system.
    """
    for _ in range(10):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        if port not in _CHROMIUM_UNSAFE_PORTS:
            return port
    raise RuntimeError("could not allocate a Chromium-safe port after 10 tries")


@pytest.fixture
def local_server():
    port = _free_port()
    server = ThreadingHTTPServer(("127.0.0.1", port), _SilentHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}/"
    finally:
        server.shutdown()
        thread.join(timeout=2)


@functools.lru_cache(maxsize=1)
def _chromium_available() -> bool:
    """Cheap, synchronous check for an installed Chromium.

    Delegates to browser_skills._chromium.chromium_install_path so the
    detection logic lives in exactly one place (shared with the
    `browser-skills doctor` command). Cached so all tests in the
    module share one result.
    """
    from browser_skills._chromium import chromium_install_path

    return chromium_install_path() is not None


skip_no_chromium = pytest.mark.skipif(
    not _chromium_available(),
    reason="Chromium browser not installed; run `python -m playwright install chromium`",
)


@pytest.mark.slow
@skip_no_chromium
async def test_dismiss_cookie_banner_against_real_chromium(local_server: str) -> None:
    from playwright.async_api import async_playwright

    from browser_skills.adapters.playwright_raw import PlaywrightPage
    from browser_skills.runner import Runner
    from browser_skills.skill import parse_skill

    skill = parse_skill("skills/dismiss-cookie-banner/SKILL.md")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            context = await browser.new_context(viewport={"width": 1280, "height": 800})
            page = await context.new_page()
            await page.goto(local_server, wait_until="domcontentloaded", timeout=10000)

            # Sanity: the banner should be visible before the skill runs.
            banner_visible_pre = await page.is_visible("#onetrust-banner-sdk")
            assert banner_visible_pre, "fixture is broken — banner not visible at start"

            wrapped = PlaywrightPage(page)
            runner = Runner()
            result = await runner.execute(skill, wrapped)

            assert result.status == "success", result.failure_reason
            assert result.deterministic_path is True
            assert result.model_calls == 0

            banner_visible_post = await page.is_visible("#onetrust-banner-sdk")
            assert not banner_visible_post, "banner still visible after skill ran"
        finally:
            await browser.close()


@pytest.mark.slow
@skip_no_chromium
async def test_extract_table_against_real_chromium(local_server: str) -> None:
    from playwright.async_api import async_playwright

    from browser_skills.adapters.playwright_raw import PlaywrightPage
    from browser_skills.runner import Runner
    from browser_skills.skill import parse_skill

    skill = parse_skill("skills/extract-table-pagination/SKILL.md")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        try:
            context = await browser.new_context(viewport={"width": 1280, "height": 800})
            page = await context.new_page()
            await page.goto(local_server, wait_until="domcontentloaded", timeout=10000)

            wrapped = PlaywrightPage(page)
            runner = Runner()
            result = await runner.execute(skill, wrapped)

            assert result.status == "success", result.failure_reason
            rows = result.extracted.get("rows_page_1")
            assert isinstance(rows, list)
            assert len(rows) == 3
            assert rows[0]["name"] == "alpha"
            assert rows[0]["score"] == "92"
        finally:
            await browser.close()
