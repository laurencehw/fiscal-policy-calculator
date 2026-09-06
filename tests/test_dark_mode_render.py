"""Guard: no chart paints a light canvas on a dark page.

``tests/test_charts_theme.py`` proves the helper does the right thing. This
file proves the app *uses* it — the failure mode being guarded is not a broken
helper but a chart that never met one, which is exactly how the bug got in
(nine call sites routed through ``apply_base_layout``, twelve that did not).

So the check runs the real router through ``AppTest``, toggles the ⚙ popover's
dark-mode checkbox the way a visitor would, and inspects the Plotly spec
Streamlit actually serialises for the browser — ``proto.spec``, after every
``update_layout`` in the app has run. A grep over sources could not do this:
whether a figure is themed depends on which helper its render path calls, and
that is only decided at run time.

Light mode is checked on the same pages, asserting the inverse: no chart
carries a theme colour, because on a light page the helper returns before
touching anything and Streamlit's own template still owns the canvas.
"""

from __future__ import annotations

import json
import time

import pytest

from fiscal_model.ui import cache as ui_cache
from fiscal_model.ui.charts import DARK_GRID, DARK_INK, TRANSPARENT

#: The Build waterfall (``ui/tabs/deficit_target.py::_render_waterfall``) was
#: the app's one un-routed chart, waived here while the Build lane owned the
#: file; it now goes through ``apply_base_layout`` like every other site, so the
#: waiver is gone and the prefix is kept only to *name* the chart in
#: :func:`test_build_renders_no_light_canvas_chart` — the guard would otherwise
#: pass just as happily if the waterfall stopped rendering at all.
WATERFALL_TITLE_PREFIX = "Waterfall — baseline"

HEALTHY_HEALTH: dict = {
    "runtime": {"status": "ok", "python_version": "3.12.0"},
    "baseline": {
        "status": "ok",
        "vintage": "February 2026",
        "vintage_key": "cbo_feb_2026",
        "start_year": 2025,
        "freshness": {"level": "fresh", "is_stale": False, "message": "current"},
    },
    "fred": {"status": "ok", "source": "live", "cache_is_expired": False},
    "irs_soi": {
        "status": "ok",
        "latest_year": 2023,
        "freshness": {"level": "ok", "is_stale": False, "message": "lag 3y"},
    },
    "model": {"status": "ok"},
    "microdata": {"status": "ok"},
    "assistant": {"status": "ok"},
    "overall": "ok",
}


@pytest.fixture(autouse=True)
def _offline_and_healthy(monkeypatch):
    """Seed the health cache and keep the run off the network."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    ui_cache.clear_health_snapshot()
    ui_cache._health_snapshot["value"] = HEALTHY_HEALTH
    ui_cache._health_snapshot["at"] = time.monotonic()
    yield
    ui_cache.clear_health_snapshot()


EXPLORE_RUN = {"preset": "tcja-full-extension", "run": "1"}
BUILD_PACKAGE = {"policies": "ss-donut-250k,corporate-28pct"}


def _run(page: str, query: dict[str, str], *, dark: bool):
    """Render ``page`` with the dark-mode toggle in the requested position.

    The toggle is driven as a widget rather than written into session state:
    ``settings_controller`` reconciles ``dark_mode`` against the checkbox's own
    key on every run, so a bare ``session_state["dark_mode"] = True`` is
    reverted on the next script run. Driving the widget is also what a visitor
    does.
    """
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file("app.py", default_timeout=300)
    at.query_params.update(query)
    at.switch_page(page)
    at.run()
    assert not at.exception, [e.message for e in at.exception]
    if dark:
        at.checkbox(key="setting_dark_mode").set_value(True)
        at.run()
        assert not at.exception, [e.message for e in at.exception]
        assert at.session_state["dark_mode"] is True
    return at


def _chart_layouts(at) -> list[dict]:
    """The layout of every Plotly spec Streamlit serialised for the browser."""
    return [json.loads(element.proto.spec)["layout"] for element in at.get("plotly_chart")]


def _title(layout: dict) -> str:
    return str((layout.get("title") or {}).get("text") or "")


def _is_light_canvas(layout: dict) -> bool:
    """True when the figure leaves its canvas to Streamlit's light theme.

    A figure with no explicit ``paper_bgcolor`` is painted by the frontend
    with the *Streamlit* theme's background — white, since the app's dark mode
    is a CSS overlay Streamlit cannot see. That is the bug, and an explicitly
    white or ``#fff`` canvas is the same bug written down.
    """
    paper = str(layout.get("paper_bgcolor") or "").lower()
    return paper in {"", "white", "#fff", "#ffffff", "rgb(255,255,255)"}


PAGES = [
    ("app_pages/explore.py", EXPLORE_RUN, "explore-after-a-run"),
    ("app_pages/build.py", BUILD_PACKAGE, "build-with-a-package"),
]


@pytest.mark.parametrize(("page", "query", "label"), PAGES)
def test_dark_mode_leaves_no_light_canvas(page, query, label):
    at = _run(page, query, dark=True)
    layouts = _chart_layouts(at)
    assert layouts, f"{label}: no chart rendered — the guard would pass vacuously"

    offenders = [_title(layout) or "<untitled>" for layout in layouts if _is_light_canvas(layout)]

    assert not offenders, (
        f"{label}: {len(offenders)} chart(s) keep a light canvas in dark mode. "
        "Route them through fiscal_model.ui.charts.apply_base_layout (or "
        "theme_figure, for a Plotly Express figure that sets its own layout). "
        f"First offender: {offenders[0]!r}"
    )


@pytest.mark.parametrize(("page", "query", "label"), PAGES)
def test_themed_charts_carry_the_dark_ink_and_grid(page, query, label):
    """Transparency alone is not enough — light text on a dark page is what
    the overlay would otherwise leave behind."""
    at = _run(page, query, dark=True)
    themed = [
        layout
        for layout in _chart_layouts(at)
        if layout.get("paper_bgcolor") == TRANSPARENT
    ]
    if not themed:
        pytest.skip(f"{label}: no themed chart on this page")

    for layout in themed:
        assert (layout.get("font") or {}).get("color") == DARK_INK, _title(layout)
        assert layout["plot_bgcolor"] == TRANSPARENT, _title(layout)
        axes = [layout[key] for key in layout if key.startswith(("xaxis", "yaxis"))]
        assert axes, _title(layout)
        for axis in axes:
            assert axis.get("gridcolor") == DARK_GRID, _title(layout)


@pytest.mark.parametrize(("page", "query", "label"), PAGES)
def test_light_mode_writes_no_theme_colours(page, query, label):
    """The other half of the invariance claim, measured on the real pages."""
    at = _run(page, query, dark=False)
    layouts = _chart_layouts(at)
    assert layouts, f"{label}: no chart rendered"

    for layout in layouts:
        assert "paper_bgcolor" not in layout, _title(layout)
        assert "plot_bgcolor" not in layout, _title(layout)
        assert "color" not in (layout.get("font") or {}), _title(layout)
        for key, axis in layout.items():
            if key.startswith(("xaxis", "yaxis")) and isinstance(axis, dict):
                assert "gridcolor" not in axis, f"{_title(layout)} / {key}"


def test_build_renders_no_light_canvas_chart():
    """The inverse of the carry-over this file used to pin.

    ``/build`` once rendered exactly one light-canvas chart and that chart was
    the waterfall; it now renders none. The assertion is deliberately stated
    twice over — the waterfall is *present* and it is *themed* — because "no
    light canvas on Build" is also true of a Build page that draws no waterfall,
    and that is a regression this test should catch rather than reward.
    """
    at = _run("app_pages/build.py", BUILD_PACKAGE, dark=True)
    layouts = _chart_layouts(at)

    waterfalls = [
        layout for layout in layouts if _title(layout).startswith(WATERFALL_TITLE_PREFIX)
    ]
    assert len(waterfalls) == 1, (
        f"expected exactly one Build waterfall, got {len(waterfalls)}: "
        f"{[_title(layout) for layout in layouts]}"
    )
    assert waterfalls[0].get("paper_bgcolor") == TRANSPARENT, "the waterfall is not themed"

    unthemed = [_title(layout) or "<untitled>" for layout in layouts if _is_light_canvas(layout)]
    assert not unthemed, f"/build keeps {len(unthemed)} light canvas(es): {unthemed}"
