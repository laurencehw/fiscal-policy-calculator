"""
Rendering tests for the About page (``/about``).

The page is static prose, so the risk is not arithmetic — it is Markdown. Two
repo-wide guards apply (``tests/test_tilde_rendering.py``,
``tests/test_dollar_rendering.py``) and this file adds the page-level checks
they cannot make from source alone: that all five sections actually reach the
browser, that the contact address survives Markdown, and that nothing on the
page renders as a footnote marker or a LaTeX span.

Driven through the real router with ``AppTest``, like the dollar guard, so a
routing regression shows up here rather than as a silently blank page.
"""

from __future__ import annotations

import re
import time

import pytest

from app_pages import about
from fiscal_model.ui import cache as ui_cache
from tests.test_dollar_rendering import HEALTHY_HEALTH, latex_risk

#: A bare footnote marker. The Ask assistant emits ``[^N]`` and strips the
#: unsupported ones; About is hand-written prose and must carry none at all.
FOOTNOTE_MARKER = re.compile(r"\[\^\d+\]")

EXPECTED_HEADINGS = (
    "About this calculator",
    "Who made it",
    "How to read the numbers",
    "Contact and links",
    "License",
)


@pytest.fixture(autouse=True)
def _offline_and_healthy(monkeypatch):
    """Seed the health cache and keep the assistant off the network."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    ui_cache.clear_health_snapshot()
    ui_cache._health_snapshot["value"] = HEALTHY_HEALTH
    ui_cache._health_snapshot["at"] = time.monotonic()
    yield
    ui_cache.clear_health_snapshot()


@pytest.fixture(scope="function")
def about_page():
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("app.py", default_timeout=300)
    at.switch_page("app_pages/about.py")
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    return at


def _rendered_text(at) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for name in ("markdown", "caption", "warning", "error", "info", "success"):
        for element in getattr(at, name, []):
            value = getattr(element, "value", None)
            if isinstance(value, str):
                out.append((name, value))
    return out


# ── Content ──────────────────────────────────────────────────────────────


def test_about_page_renders_the_five_sections(about_page):
    joined = "\n".join(text for _, text in _rendered_text(about_page))
    missing = [heading for heading in EXPECTED_HEADINGS if f"### {heading}" not in joined]
    assert not missing, f"About page is missing section heading(s): {missing}"


def test_about_page_has_no_extra_sections():
    """The brief names five sections; a sixth would be scope creep, not a typo."""
    headings = [block.splitlines()[0].lstrip("# ").strip() for block in about.SECTIONS]
    assert headings == list(EXPECTED_HEADINGS)


def test_about_page_shows_the_contact_address(about_page):
    joined = "\n".join(text for _, text in _rendered_text(about_page))
    assert about.CONTACT_EMAIL in joined
    assert f"mailto:{about.CONTACT_EMAIL}" in joined


def test_about_page_links_out_to_the_projects(about_page):
    joined = "\n".join(text for _, text in _rendered_text(about_page))
    for url in (about.REPO_URL, about.SA_POLICY_SPACE_URL, about.LINKEDIN_URL, about.APP_URL):
        assert url in joined, f"About page dropped the link to {url}"


def test_about_page_links_to_methodology(about_page):
    """The accuracy-tiers section points at the page that documents them."""
    targets = {getattr(link, "page", None) for link in about_page.get("page_link")}
    joined = "\n".join(text for _, text in _rendered_text(about_page))
    assert "methodology" in targets or "(/methodology)" in joined


# ── Markdown safety ──────────────────────────────────────────────────────


def test_about_page_carries_no_footnote_markers(about_page):
    offenders = [
        (name, text) for name, text in _rendered_text(about_page) if FOOTNOTE_MARKER.search(text)
    ]
    assert not offenders, f"bare footnote marker(s) on About: {offenders[:2]}"


def test_about_page_renders_no_latex_spans(about_page):
    offenders = [
        (name, text, risk)
        for name, text in _rendered_text(about_page)
        if (risk := latex_risk(text))
    ]
    assert not offenders, (
        "About carries a string Streamlit can render as inline math rather "
        f"than text. First offender: {offenders[0][0]} -> {offenders[0][1][:200]!r}"
    )


def test_accuracy_tildes_are_escaped():
    """``~5%`` … ``~8%`` in one block strikes the paragraph through."""
    from tests.test_tilde_rendering import UNESCAPED

    for block in about.SECTIONS:
        assert not UNESCAPED.search(block), f"unescaped tilde in: {block[:80]!r}"


# ── Footer credit (every page, not only About) ───────────────────────────


def test_footer_credits_the_author_and_links_to_about(about_page):
    captions = [text for name, text in _rendered_text(about_page) if name == "caption"]
    footer = [text for text in captions if "Built by Laurence Wilse-Samson" in text]
    assert footer, "the footer credit line is missing"
    assert "(/about)" in footer[0]
    assert "github.com/laurencehw/fiscal-policy-calculator" in footer[0]
    assert "(/methodology)" in footer[0]
