"""Shared helpers for the browser journeys: budgets, page loading, contrast maths.

Stdlib-only on purpose -- ``conftest.py`` imports this, and a conftest that imported Playwright
would break collection of the whole ``tests/`` tree on a machine without it.
"""
from __future__ import annotations

import os
import re
import time
from typing import Any

SCALE = float(os.environ.get("E2E_LATENCY_SCALE", "1"))

# Streamlit decides "mobile" (and so whether a nav tap collapses the sidebar) from the *user
# agent*, not the viewport; Playwright's ``is_mobile`` does not set one.
MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
)

#: Seconds, local warm-ish run (measured 2026-10-03, Streamlit 1.56, py3.11), at roughly 2.5x the
#: observed value. The observed range is beside each. Multiply with ``E2E_LATENCY_SCALE``.
BUDGET = {
    "ask": 15,  # 2.5-7.0
    "explore": 25,  # 4.1-4.9 warm, 12.4 first scored run in a fresh server
    "tailor": 15,  # 5.1-6.6
    "build": 10,  # 2.5-3.9
    "methodology": 12,  # 4.2-4.5
    "rerun": 8,  # slider/Score again 2.9, Calculate 3.4
    "tab": 4,  # 1.2-1.3
}

#: Console noise that is Streamlit's, not the app's (document each; do not widen casually).
BENIGN = re.compile(
    r"Unrecognized feature|LaTeX-incompatible|_stcore/(health|host-config)|"  # 404s, nested paths
    r"Failed to load resource: the server responded with a status of 404"  # same, text only
)

#: ``(label, seconds, budget_seconds)`` for every timed step; printed by conftest at the end.
LATENCIES: list[tuple[str, float, float]] = []


def budget(key: str) -> float:
    return BUDGET[key] * SCALE


def record(label: str, seconds: float, key: str) -> None:
    LATENCIES.append((label, seconds, budget(key)))
    assert seconds <= budget(key), f"{label}: {seconds:.1f}s > {budget(key):.1f}s budget"


class Visit:
    def __init__(self, page: Any, seconds: float) -> None:
        self.page, self.seconds = page, seconds
        self.console: list[str] = page._e2e_console

    @property
    def text(self) -> str:
        return self.page.inner_text("body")


def settle(page: Any, timeout_ms: int = 120_000) -> None:
    """App rendered and Streamlit idle for ~1s (no running status widget)."""
    page.wait_for_selector('[data-testid="stApp"]', timeout=timeout_ms)
    quiet, t0 = 0, time.time()
    while time.time() - t0 < timeout_ms / 1000:
        quiet = quiet + 1 if page.locator('[data-testid="stStatusWidget"]').count() == 0 else 0
        if quiet >= 4:
            return
        page.wait_for_timeout(250)
    raise AssertionError("app never went idle")


def go(ctx: Any, base: str, path: str, budget_key: str) -> Visit:
    page = ctx.new_page()
    page._e2e_console = []
    page.on("console", lambda m: page._e2e_console.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: page._e2e_console.append("pageerror: " + str(e)))
    t0 = time.time()
    page.goto(base + path, wait_until="domcontentloaded")
    settle(page)
    v = Visit(page, time.time() - t0)
    record(path, v.seconds, budget_key)
    assert page.locator('[data-testid="stException"]').count() == 0, "st.exception block on page"
    for bad in ("Traceback", "StreamlitAPIException"):
        assert bad not in v.text
    assert not [c for c in v.console if not BENIGN.search(c)], v.console
    overflow = page.evaluate(
        "document.documentElement.scrollWidth - document.documentElement.clientWidth"
    )
    assert overflow <= 1, "page-level horizontal scroll"
    return v


def headline(text: str) -> list[str]:
    return re.findall(r"\$[+\-−]?[\d,]+\.\d[BT]", text)[:3]


# -- WCAG contrast -------------------------------------------------------------------------


def _lum(rgb: tuple[int, int, int]) -> float:
    def ch(c: float) -> float:
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def contrast(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    hi, lo = sorted((_lum(a), _lum(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def rgb(css: str) -> tuple[int, int, int]:
    r, g, b = (int(float(x)) for x in re.findall(r"[\d.]+", css)[:3])
    return r, g, b
