"""Fixtures for the browser journeys: a booted Streamlit app, a Chromium, two contexts.

See ``test_browser_journeys.py`` for how to run these and the ``E2E_*`` overrides.

Everything Playwright-related is imported lazily inside fixtures: this file is collected on
every ``pytest tests/`` run, including machines with no Playwright, and must not fail there.
"""
from __future__ import annotations

import glob
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

import pytest

from .support import LATENCIES, MOBILE_UA, SCALE

ROOT = Path(__file__).resolve().parents[2]
#: Under CI a missing browser / dead server is a failure, so the e2e job cannot pass by skipping.
IN_CI = bool(os.environ.get("CI"))


def _unavailable(reason: str) -> None:
    if IN_CI:
        pytest.fail(reason)
    pytest.skip(reason)


def _chromium_candidates() -> list[str | None]:
    """Explicit binary, then Playwright's own, then well-known locations. Never downloads."""
    if os.environ.get("E2E_CHROMIUM"):
        return [os.environ["E2E_CHROMIUM"]]
    found: list[str | None] = [None]  # Playwright's own managed browser
    roots = [
        os.environ.get("PLAYWRIGHT_BROWSERS_PATH", ""),
        "/opt/pw-browsers",
        os.path.expanduser("~/.cache/ms-playwright"),
    ]
    for root in filter(None, roots):
        for pat in (
            "chromium-*/chrome-linux/chrome",
            "chromium-*/chrome-linux64/chrome",
            "chromium-*/chrome-mac*/Chromium.app/Contents/MacOS/Chromium",
        ):
            found.extend(reversed(sorted(glob.glob(os.path.join(root, pat)))))
    return found


def _healthy(url: str) -> bool:
    try:
        return urllib.request.urlopen(url + "/_stcore/health", timeout=2).status == 200
    except Exception:
        return False


@pytest.fixture(scope="session")
def base_url():
    if os.environ.get("E2E_BASE_URL"):
        yield os.environ["E2E_BASE_URL"].rstrip("/")
        return
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    env = {**os.environ, "ANTHROPIC_API_KEY": ""}  # CI never sets it
    log = tempfile.NamedTemporaryFile(  # noqa: SIM115 -- closed in the finally below
        "w+", prefix="e2e-streamlit-", suffix=".log", delete=False)
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py", "--server.headless", "true",
         "--server.port", str(port), "--browser.gatherUsageStats", "false"],
        cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
    )
    url = f"http://127.0.0.1:{port}"
    try:
        deadline = time.time() + 90
        while time.time() < deadline and proc.poll() is None and not _healthy(url):
            time.sleep(0.5)
        if proc.poll() is not None or not _healthy(url):
            log.flush()
            tail = Path(log.name).read_text(errors="replace")[-1500:]
            _unavailable(f"streamlit did not start on {url} (log {log.name}):\n{tail}")
        yield url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:  # pragma: no cover
            proc.kill()
        log.close()


@pytest.fixture(scope="session")
def browser():
    sync_api = pytest.importorskip("playwright.sync_api", reason="playwright not installed")
    with sync_api.sync_playwright() as p:
        b, errors = None, []
        for exe in _chromium_candidates():
            try:
                b = p.chromium.launch(executable_path=exe, headless=True)
                break
            except Exception as e:  # no browser binary at this path
                errors.append(f"{exe or 'playwright default'}: {str(e).splitlines()[0]}")
        if b is None:
            _unavailable("chromium unavailable (set E2E_CHROMIUM): " + "; ".join(errors[:3]))
        yield b
        b.close()


@pytest.fixture
def desktop(browser):
    ctx = browser.new_context(viewport={"width": 1280, "height": 900}, accept_downloads=True)
    yield ctx
    ctx.close()


@pytest.fixture
def mobile(browser):
    ctx = browser.new_context(
        viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True,
        has_touch=True, user_agent=MOBILE_UA,
    )
    yield ctx
    ctx.close()


def pytest_terminal_summary(terminalreporter):
    """Measured latency against budget, so a slow drift is visible before it fails."""
    if not LATENCIES:
        return
    tr = terminalreporter
    tr.section(f"e2e latency vs budget (scale x{SCALE:g})")
    for label, secs, bud in sorted(LATENCIES, key=lambda r: -r[1] / r[2]):
        tr.write_line(f"{secs:6.2f}s / {bud:5.1f}s  {label}")
