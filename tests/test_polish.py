"""Phase 6a polish guards: one degraded banner per page, and tracker copy.

Two things that are easy to regress and invisible in unit tests:

1. **The degraded-data banner renders at most once per page.** The shared
   chrome raises it above the fold and the Data Status popover repeats the
   same conditions as detail lines; before the fix both drew the banner, so a
   user on fallback data saw the identical warning twice on every surface.
   Asserted through the real router with ``AppTest`` on ``/``, ``/explore``
   and ``/build`` — a unit test against a fake ``st`` cannot see the popover
   body execute.

2. **User-facing tracker copy states the condition, not the shell command.**
   ``python scripts/update_bills.py`` is only actionable by whoever runs the
   deployment; visitors get "data refresh pending" and operators get the
   runbook behind ``?admin=<token>``.
"""

from __future__ import annotations

import time

import pytest

from fiscal_model.ui import cache as ui_cache
from fiscal_model.ui.tabs import bill_tracker

# The two banner headlines rendered by ``components.chrome`` and (previously,
# also) by ``app_controller.render_data_status``.
# Since 2026-09-01 the degraded (non-error) notice is a collapsed expander
# rather than an ``st.warning`` box — deliberately quieter, per the owner.
DEGRADED_BANNER = "Some data sources are running on older snapshots"
ERROR_BANNER = "**Data error — results may be unreliable**"

# A health payload that is unambiguously degraded for exactly one reason, so
# the banner must appear and the count is easy to reason about.
DEGRADED_HEALTH: dict = {
    "runtime": {"status": "ok", "python_version": "3.12.0"},
    "baseline": {
        "status": "degraded",
        "vintage": "February 2026",
        "vintage_key": "cbo_feb_2026",
        "source": "hardcoded_fallback",
        "start_year": 2025,
        "freshness": {
            "level": "fresh",
            "age_days": 209,
            "message": "Current CBO baseline (209d since publication; no newer release)",
            "emoji": "🟢",
            "is_stale": False,
        },
    },
    "fred": {"status": "ok", "source": "live", "cache_is_expired": False},
    "irs_soi": {
        "status": "ok",
        "latest_year": 2023,
        "freshness": {"level": "aging", "is_stale": False, "message": "lag 3y"},
    },
    "model": {"status": "ok"},
    "microdata": {"status": "ok"},
    "assistant": {"status": "ok"},
    "overall": "degraded",
}


@pytest.fixture(scope="module")
def _degraded_health_snapshot():
    """Seed the TTL health cache so every page sees the same degraded payload.

    Seeding the cache rather than monkeypatching ``get_health_snapshot``
    reaches every caller regardless of how it imported the function, and keeps
    the AppTest runs off the real (slow) ``check_health`` probe.
    """
    ui_cache.clear_health_snapshot()
    ui_cache._health_snapshot["value"] = DEGRADED_HEALTH
    ui_cache._health_snapshot["at"] = time.monotonic()
    yield
    ui_cache.clear_health_snapshot()


def _run_page(page: str | None):
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("app.py", default_timeout=300)
    if page is not None:
        at.switch_page(page)
    at.run()
    return at


def _banner_count(at) -> int:
    alerts = [element.value for element in at.warning]
    alerts += [element.value for element in at.error]
    # The quiet variant: an expander whose label carries the headline.
    alerts += [getattr(element, "label", "") for element in at.expander]
    return sum(
        1
        for text in alerts
        if DEGRADED_BANNER in str(text) or ERROR_BANNER in str(text)
    )


@pytest.mark.parametrize(
    "page",
    [
        pytest.param(None, id="ask-home"),
        pytest.param("app_pages/explore.py", id="explore"),
        pytest.param("app_pages/build.py", id="build"),
    ],
)
def test_degraded_banner_renders_at_most_once_per_page(page, _degraded_health_snapshot):
    at = _run_page(page)
    assert not at.exception, [e.message for e in at.exception]
    assert _banner_count(at) <= 1, (
        "the degraded-data banner is duplicated; the chrome raises it and the "
        "Data Status panel must render its detail with show_banner=False"
    )


def test_degraded_banner_is_actually_raised_when_data_is_degraded(
    _degraded_health_snapshot,
):
    """Guards the guard: a test that only asserts ``<= 1`` would still pass if
    the banner disappeared entirely."""
    at = _run_page(None)
    assert not at.exception, [e.message for e in at.exception]
    assert _banner_count(at) == 1


# ---------------------------------------------------------------------------
# Bill tracker copy
# ---------------------------------------------------------------------------


class _FakeExpander:
    def __init__(self, sink: list[str], label: str) -> None:
        self.sink = sink
        self.label = label

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeStreamlit:
    """Minimal ``st`` stand-in recording what the tracker renders."""

    def __init__(self, query_params: dict | None = None) -> None:
        self.warnings: list[str] = []
        self.markdowns: list[str] = []
        self.expanders: list[str] = []
        if query_params is not None:
            self.query_params = query_params

    def warning(self, text, *args, **kwargs):
        del args, kwargs
        self.warnings.append(str(text))

    def markdown(self, text="", *args, **kwargs):
        del args, kwargs
        self.markdowns.append(str(text))

    def expander(self, label, *args, **kwargs):
        del args, kwargs
        self.expanders.append(str(label))
        return _FakeExpander(self.markdowns, str(label))

    def all_text(self) -> str:
        return "\n".join(self.warnings + self.markdowns + self.expanders)


def test_no_db_state_says_refresh_pending_not_a_shell_command():
    st = _FakeStreamlit()
    bill_tracker._render_no_db_state(st)

    assert st.warnings
    assert "data refresh pending" in st.warnings[0].lower()
    assert "scripts/update_bills.py" not in st.all_text()
    assert "update pipeline" not in st.all_text().lower()


def test_operator_runbook_is_hidden_from_ordinary_visitors():
    st = _FakeStreamlit(query_params={})
    bill_tracker._render_update_instructions(st)

    assert st.expanders == []
    assert "scripts/update_bills.py" not in st.all_text()


def test_operator_runbook_is_visible_behind_the_admin_token(monkeypatch):
    monkeypatch.setenv("ASSISTANT_ADMIN_TOKEN", "s3cret")
    st = _FakeStreamlit(query_params={"admin": "s3cret"})
    bill_tracker._render_update_instructions(st)

    assert st.expanders, "operator runbook should render for an admin request"
    assert "scripts/update_bills.py" in st.all_text()


def test_stale_data_banner_says_refresh_pending_without_a_command():
    class _DB:
        def get_last_update(self):
            from datetime import datetime, timedelta, timezone

            return datetime.now(timezone.utc) - timedelta(days=30)

    st = _FakeStreamlit()
    assert bill_tracker._render_global_freshness_banner(st, _DB()) is True
    assert "data refresh pending" in st.warnings[0].lower()
    assert "scripts/" not in st.all_text()
