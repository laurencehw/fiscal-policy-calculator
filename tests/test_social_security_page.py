"""Rendering tests for the Social Security page (``/social-security``).

Driven through the real router with ``AppTest``, like the About page tests.
"""

from __future__ import annotations

import time

import pytest

from fiscal_model.ui import cache as ui_cache
from tests.test_dollar_rendering import HEALTHY_HEALTH, latex_risk


@pytest.fixture(autouse=True)
def _offline_and_healthy(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    ui_cache.clear_health_snapshot()
    ui_cache._health_snapshot["value"] = HEALTHY_HEALTH
    ui_cache._health_snapshot["at"] = time.monotonic()
    yield
    ui_cache.clear_health_snapshot()


@pytest.fixture()
def page():
    from streamlit.testing.v1 import AppTest
    from streamlit.util import calc_md5

    from app_pages import social_security

    at = AppTest.from_file("app.py", default_timeout=300)
    # ``AppTest.switch_page`` hashes the file's display name ("social security"),
    # but a callable-registered page is keyed by the hash of its url_path, and
    # this one is hyphenated. Select it by that hash directly.
    at._page_hash = calc_md5(social_security.URL_PATH)
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    return at


def _metric(at, label):
    return next(m for m in at.metric if m.label == label)


def test_current_law_headline(page):
    assert _metric(page, "Trust funds depleted").value == "2034"
    assert _metric(page, "Benefit cut at depletion").value == "17%"
    assert _metric(page, "75-year shortfall closed").value == "0%"
    assert _metric(page, "75-year actuarial balance").value == "-4.42%"


def test_choosing_options_moves_the_headline(page):
    page.radio(key="ss_group_taxable_maximum").set_value(
        "Eliminate the taxable maximum (no benefit credit)"
    ).run()
    assert not page.exception
    assert _metric(page, "Trust funds depleted").value == "2058"
    assert _metric(page, "75-year shortfall closed").value == "58%"


def test_page_states_the_tier_and_the_framing(page):
    text = "\n".join(e.value for e in [*page.info, *page.caption, *page.markdown])
    assert "not a model estimate" in text
    assert "without interactions" in text
    assert "OASI" in text
    assert "How this compares with CRFB" in text


def test_no_markdown_currency_turns_into_math(page):
    rendered = [e.value for e in [*page.markdown, *page.caption, *page.info]]
    rendered += [o for r in page.radio for o in r.options]
    rendered += [c.label for c in page.checkbox]
    risky = [t for t in rendered if latex_risk(t)]
    assert not risky, risky
