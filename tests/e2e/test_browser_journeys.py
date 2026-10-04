"""Real-browser journeys (ROUTE_TO_9 priority 6): drive the live Streamlit app in Chromium.

Opt-in. The default ``pytest tests/`` run excludes these (``addopts = ... -m "not e2e"`` in
pyproject.toml), so the main CI job never needs a browser. Select them explicitly:

    ANTHROPIC_API_KEY= python -m pytest -m e2e tests/e2e -q

(Naming the file without ``-m e2e`` deselects every test in it -- that is the exclusion working.)

Environment overrides:

* ``E2E_BASE_URL``       test an already-running app (e.g. the deployed one) instead of booting
                         ``streamlit run app.py`` on a free port, with ``ANTHROPIC_API_KEY=""``.
                         ``E2E_BASE_URL=https://fiscal-policy-calculator.streamlit.app``
* ``E2E_LATENCY_SCALE``  multiply every latency budget (use ``3`` or more against a remote app).
* ``E2E_CHROMIUM``       path to a Chromium/Chrome binary; otherwise Playwright's own browser is
                         tried, then ``PLAYWRIGHT_BROWSERS_PATH`` / ``/opt/pw-browsers`` /
                         ``~/.cache/ms-playwright``. A browser is never downloaded from here.

Skips cleanly when ``playwright`` or a browser binary is missing -- except under ``CI`` (any
non-empty value), where a missing browser or a server that never boots is a *failure*, so the
dedicated CI job cannot go green by skipping everything.

Budgets and their observed ranges live in ``support.BUDGET``; the run prints measured latency
against budget at the end.
"""
from __future__ import annotations

import re
import time

import pytest

pytest.importorskip("playwright.sync_api", reason="playwright not installed")

from .support import (
    contrast,
    go,
    headline,
    record,
    rgb,
    settle,
)

pytestmark = pytest.mark.e2e


def test_ask_landing(desktop, base_url):
    v = go(desktop, base_url, "/", "ask")
    assert "Ask a public-finance question" in v.text
    assert v.page.locator("h1").count() == 1


def test_explore_preset_renders_result(desktop, base_url):
    v = go(desktop, base_url, "/explore?preset=tcja-full-extension&run=1", "explore")
    assert "Calculation complete!" in v.text
    # pinned loosely: the model figure may move with the baseline
    assert "+$4,581.9B" in v.text or headline(v.text)
    assert "Share URL:" in v.text


def test_explore_unknown_preset_degrades_with_message(desktop, base_url):
    v = go(desktop, base_url, "/explore?preset=nope-not-real&run=1", "explore")
    assert "No proposal matches nope-not-real" in v.text


def test_tailor_deeplink_scores(desktop, base_url):
    # NB: rate is in percentage points (2.6 = +2.6pp); rate=0.026 is +0.026pp, about -$3B.
    v = go(desktop, base_url, "/tailor?type=income&rate=2.6&who=top400k&run=1", "tailor")
    assert "Calculation complete!" in v.text and "Deficit Reduction" in v.text
    # rescore after keyboard edit of the slider
    sl = v.page.locator('[role="slider"][aria-label="Rate change (percentage points)"]')
    before = headline(v.text)[0]
    sl.focus()
    v.page.keyboard.press("ArrowRight")
    t0 = time.time()
    v.page.get_by_role("button", name=re.compile("Score this policy")).click()
    v.page.wait_for_timeout(400)
    settle(v.page)
    record("tailor rescore", time.time() - t0, "rerun")
    assert headline(v.text)[0] != before


def test_build_values_and_policies_links(desktop, base_url):
    v = go(desktop, base_url, "/build?values=growth-first&load=1", "build")
    assert "Your package (" in v.text
    v = go(desktop, base_url, "/build?policies=tcja-full-extension,corporate-28pct", "build")
    assert "Your package (2 policies)" in v.text


def test_methodology(desktop, base_url):
    v = go(desktop, base_url, "/methodology", "methodology")
    assert "calibrated" in v.text.lower()


@pytest.mark.parametrize(
    "path",
    [
        "/explore?preset=tcja-full-extension&run=1",
        "/tailor?type=income&rate=2.6&who=top400k&run=1",
        "/explore?preset=corporate-28pct&dynamic=1&run=1",
    ],
)
def test_share_link_round_trip(desktop, base_url, path):
    key = "explore" if path.startswith("/explore") else "tailor"
    first = go(desktop, base_url, path, key)
    url = re.search(r"Share URL: (\S+)", first.text).group(1)
    replay_path = re.sub(r"^https?://[^/]+", "", url)  # emitted host is the public app; replay here
    second = go(desktop, base_url, replay_path, key)
    assert headline(second.text) == headline(first.text)
    assert re.search(r"Share URL: (\S+)", second.text).group(1) == url  # link is a fixed point


def test_csv_export(desktop, base_url):
    v = go(desktop, base_url, "/explore?preset=tcja-full-extension&run=1", "explore")
    with v.page.expect_download(timeout=30_000) as dl:
        v.page.get_by_role("button", name=re.compile("Download as CSV")).first.click()
    path = dl.value.path()
    with open(path, encoding="utf-8") as fh:
        assert fh.read().startswith("# Policy: TCJA Full Extension")


def test_result_tabs_switch(desktop, base_url):
    v = go(desktop, base_url, "/explore?preset=tcja-full-extension&run=1", "explore")
    for tab in ("👥 Distribution", "⚖️ Scoring Models", "📋 Details"):
        t0 = time.time()
        v.page.get_by_role("tab", name=tab).click()
        v.page.wait_for_timeout(300)
        settle(v.page)
        record(f"tab {tab}", time.time() - t0, "tab")
        assert v.page.locator('[data-testid="stException"]').count() == 0


def test_mobile_nav_reaches_every_page(mobile, base_url):
    page = go(mobile, base_url, "/", "ask").page
    for name, slug in (("Tailor", "tailor"), ("Explore", "explore"), ("Build", "build")):
        if page.locator('[data-testid="stSidebar"]').first.get_attribute("aria-expanded") != "true":
            page.locator('[data-testid="stExpandSidebarButton"]').first.click()
        page.locator('[data-testid="stSidebarNavLink"]', has_text=name).first.click()
        page.wait_for_url(re.compile(rf"/{slug}$"))
        settle(page)
        assert page.locator('[data-testid="stException"]').count() == 0


def test_mobile_sidebar_closes_after_navigation(mobile, base_url):
    """On a phone the top nav lives in a drawer; tapping a page must close it.

    Streamlit collapses the drawer on a nav tap only when *it* thinks the device is mobile,
    which it decides from the user agent (the ``mobile`` fixture sets one). Without a mobile UA
    this looks like an app defect -- the drawer stays over the page -- but it is a harness
    artefact (Playwright's ``is_mobile`` leaves the desktop UA). A narrow *desktop* window keeps
    the drawer open too; that is Streamlit's own behaviour and the sandboxed page cannot run
    JS to change it, so there is no app-side fix and none is attempted.
    """
    page = go(mobile, base_url, "/", "ask").page
    page.locator('[data-testid="stExpandSidebarButton"]').first.click()
    page.locator('[data-testid="stSidebarNavLink"]', has_text="Build").first.click()
    page.wait_for_url(re.compile(r"/build$"))
    settle(page)
    page.wait_for_function(
        "document.querySelector('[data-testid=\"stSidebar\"]')"
        ".getAttribute('aria-expanded') === 'false'",
        timeout=5000,
    )


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/explore?preset=tcja-full-extension&run=1",
        "/tailor?type=income&rate=2.6&who=top400k&run=1",
        "/build",
    ],
)
def test_mobile_no_page_level_overflow(mobile, base_url, path):
    key = "explore" if "explore" in path else "tailor" if "tailor" in path else "ask"
    go(mobile, base_url, path, key)  # asserts no horizontal scroll


def test_keyboard_tab_order_reaches_content_and_activates(desktop, base_url):
    page = go(desktop, base_url, "/", "ask").page
    stops = []
    for _ in range(25):
        page.keyboard.press("Tab")
        stops.append(page.evaluate(
            "(document.activeElement.innerText"
            "||document.activeElement.getAttribute('aria-label')||'').trim().slice(0,30)"
        ))
    assert stops[0] == "Skip to main content"  # see test_skip_link_is_first_tab_stop_...
    assert stops[1:5] == ["Ask", "Build", "Tailor", "Explore"]
    assert any("Open Build" in s for s in stops)
    assert any("Ask this" in s for s in stops)
    # Enter on a doorway card navigates
    page.get_by_role("link", name=re.compile("Open Build")).focus()
    page.keyboard.press("Enter")
    page.wait_for_url(re.compile(r"/build"))
    settle(page)


# -- keyboard focus is visible -------------------------------------------------------------

FOCUS_JS = """e => { const c = getComputedStyle(e);
  return {style: c.outlineStyle, width: parseFloat(c.outlineWidth), color: c.outlineColor,
          page: getComputedStyle(document.querySelector('[data-testid="stApp"]')).backgroundColor,
          visible: e.matches(':focus-visible')}; }"""


def _assert_visible_ring(el, label):
    el.focus()
    ring = el.evaluate(FOCUS_JS)
    assert ring["visible"], f"{label}: not :focus-visible after focus()"
    assert ring["style"] != "none" and ring["width"] >= 2, f"{label}: no focus outline {ring}"
    ratio = contrast(rgb(ring["color"]), rgb(ring["page"]))
    assert ratio >= 3.0, f"{label}: focus ring {ratio:.2f}:1 < 3:1 against the page ({ring})"


def test_doorway_links_show_visible_focus(desktop, base_url):
    page = go(desktop, base_url, "/", "ask").page
    page.keyboard.press("Tab")  # keyboard modality, so :focus-visible matches
    for name in ("Open Build", "Open Tailor"):
        _assert_visible_ring(page.get_by_role("link", name=re.compile(name)), name)


def test_top_nav_links_show_visible_focus(desktop, base_url):
    page = go(desktop, base_url, "/", "ask").page
    page.keyboard.press("Tab")
    for name in ("Build", "Tailor", "Explore"):
        link = page.locator('[data-testid="stTopNavLink"]', has_text=name).first
        _assert_visible_ring(link, f"top nav {name}")


def test_focus_ring_survives_dark_mode(desktop, base_url):
    page = go(desktop, base_url, "/", "ask").page
    page.get_by_role("button", name=re.compile("Settings")).first.click()
    page.get_by_text("🌙 Dark mode").first.click()
    settle(page)
    page.keyboard.press("Escape")
    page.keyboard.press("Tab")
    app_bg = page.evaluate(
        "getComputedStyle(document.querySelector('[data-testid=\"stApp\"]')).backgroundColor")
    assert rgb(app_bg) != (255, 255, 255), "dark mode did not engage"
    _assert_visible_ring(page.get_by_role("link", name=re.compile("Open Build")), "Open Build")


def test_chrome_popovers_have_real_accessible_names(desktop, base_url):
    """The settings trigger is a word, not a bare gear glyph.

    NOT asserted: absence of the ``expand_more`` ligature word. Streamlit renders its chevron as
    Material-icon text with no ``aria-hidden`` and ships ``aria-label=""`` on popover buttons,
    so it reaches every popover/expander name ("... expand_more"); that lives in Streamlit's
    frontend and cannot be removed from app code.
    """
    page = go(desktop, base_url, "/", "ask").page
    assert page.get_by_role("button", name=re.compile(r"Settings")).count() >= 1
    assert page.get_by_role("button", name=re.compile(r"CBO Feb 2026")).count() >= 1
    bare = page.get_by_role("button", name=re.compile(r"^\s*⚙\s*(expand_more)?\s*$"))
    assert bare.count() == 0, "settings trigger has no word in its accessible name"


def test_skip_link_is_first_tab_stop_and_skips_the_nav(desktop, base_url):
    """The skip link is the first Tab stop, and Enter on it jumps past the top nav.

    Streamlit renders its header (top nav, Deploy, menu) as a DOM sibling *before*
    ``stMain``, and every ``st.markdown`` -- even one emitted before ``st.navigation`` --
    lands inside ``stMain``, so no app-side ordering can put the link first in the DOM.
    ``tabindex="1"`` on the one skip link (``fiscal_model/ui/a11y.py``) puts it first in
    the *sequential focus order* instead; every other element keeps the default order.
    """
    page = go(desktop, base_url, "/", "ask").page
    active = (
        "(()=>{const e=document.activeElement;"
        "return (e.id?'#'+e.id+' ':'')+(e.innerText||'').trim().slice(0,30)})()"
    )
    page.keyboard.press("Tab")
    assert "Skip to main content" in page.evaluate(active)
    page.keyboard.press("Enter")
    page.wait_for_function("document.activeElement && document.activeElement.id === 'main-content'")
    after = []
    for _ in range(3):
        page.keyboard.press("Tab")
        after.append(page.evaluate(active))
    assert not {"Ask", "Build", "Tailor", "Explore", "More"} & {s.strip() for s in after}, after
