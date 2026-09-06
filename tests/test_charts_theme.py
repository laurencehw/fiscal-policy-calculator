"""
Pins the light-mode Plotly layout ``fiscal_model/ui/charts.py`` produces, and
checks the dark one.

The light half of this file was committed **before** the dark-mode work landed.
Its job is to be the "before" photograph: the dark-mode change is only allowed
to add behaviour on the dark branch, so whatever ``apply_base_layout`` writes
for a light page has to survive the change byte for byte.

The pinned dict excludes ``layout.template``, which is not ours — Plotly puts
``plotly.io.templates.default`` there at construction time, and inside a
Streamlit process that default is Streamlit's own ``streamlit`` template. A
separate test asserts that light mode leaves it exactly as constructed, which
is the other half of "light is untouched".

The representative figure is the Results waterfall (``results_summary``'s
``fig_waterfall``), widened to exercise every keyword ``apply_base_layout``
accepts — including ``xaxis_title=None`` (the explicit-clear sentinel),
``legend=``, ``hovermode=`` and two ``**extra`` keys.
"""

from __future__ import annotations

from typing import Any

import plotly.express as px
import plotly.graph_objects as go
import pytest

from fiscal_model.ui.charts import (
    COLOR_DEFICIT_DOWN,
    COLOR_DEFICIT_UP,
    COLOR_PRIMARY,
    COLOR_SECONDARY,
    DARK_AXIS_LINE,
    DARK_BACKGROUND,
    DARK_COLORWAY,
    DARK_GRID,
    DARK_INK,
    DARK_MUTED_INK,
    DARK_SURFACE,
    TRANSPARENT,
    apply_base_layout,
    dark_template,
    horizontal_legend,
    is_dark_mode,
    theme_figure,
)

# ---------------------------------------------------------------------------
# The pinned "before" layout
# ---------------------------------------------------------------------------

PINNED_LIGHT_LAYOUT: dict[str, Any] = {
    "height": 320,
    "hovermode": "x unified",
    "legend": {
        "orientation": "h",
        "x": 1.0,
        "xanchor": "right",
        "y": 1.02,
        "yanchor": "bottom",
    },
    "margin": {"b": 10, "l": 20, "r": 20, "t": 10},
    "meta": {"description": "alt"},
    "showlegend": False,
    "title": {"text": "Deficit Impact Decomposition"},
    "xaxis": {"title": {}},
    "yaxis": {"title": {"text": "Deficit Impact ($B, + = increases deficit)"}},
    "yaxis2": {
        "overlaying": "y",
        "side": "right",
        "title": {"text": "Secondary"},
    },
}


def representative_figure() -> go.Figure:
    """A stand-in for the Results waterfall, before any layout is applied."""
    return go.Figure(
        go.Waterfall(
            orientation="v",
            measure=["absolute", "relative", "total"],
            x=["Static", "Behavioral", "Conventional"],
            y=[-400.0, 50.0, -350.0],
            text=["$-400B", "$+50B", "$-350B"],
            textposition="outside",
            increasing={"marker": {"color": "#dc3545"}},
            decreasing={"marker": {"color": "#28a745"}},
            totals={"marker": {"color": "#1f77b4"}},
        )
    )


def apply_representative_layout(fig: go.Figure, **kwargs: Any) -> go.Figure:
    """Call ``apply_base_layout`` with every keyword a real caller uses."""
    return apply_base_layout(
        fig,
        margin=dict(l=20, r=20, t=10, b=10),
        height=320,
        title="Deficit Impact Decomposition",
        xaxis_title=None,
        yaxis_title="Deficit Impact ($B, + = increases deficit)",
        showlegend=False,
        hovermode="x unified",
        legend=horizontal_legend(align="right"),
        yaxis2={"title": "Secondary", "overlaying": "y", "side": "right"},
        meta={"description": "alt"},
        **kwargs,
    )


def layout_without_template(fig: go.Figure) -> dict[str, Any]:
    layout = dict(fig.to_plotly_json()["layout"])
    layout.pop("template", None)
    return layout


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestLightModeInvariance:
    """A light page must render exactly what it rendered before dark mode."""

    def test_layout_dict_matches_the_pinned_snapshot(self):
        fig = apply_representative_layout(representative_figure())
        assert layout_without_template(fig) == PINNED_LIGHT_LAYOUT

    def test_no_theme_keys_are_written(self):
        # The dark branch works by setting these at *layout* level (they beat
        # the template, which Streamlit's frontend rewrites). Light mode must
        # leave every one of them unset so the Streamlit theme still owns them.
        fig = apply_representative_layout(representative_figure())
        assert fig.layout.paper_bgcolor is None
        assert fig.layout.plot_bgcolor is None
        assert fig.layout.font.color is None
        assert fig.layout.xaxis.gridcolor is None
        assert fig.layout.yaxis.gridcolor is None
        assert fig.layout.hoverlabel.bgcolor is None

    def test_template_is_left_as_constructed(self):
        # ``go.Figure()`` stamps ``plotly.io.templates.default`` onto the
        # layout; light mode must not swap it for one of ours.
        untouched = go.Figure().to_plotly_json()["layout"]["template"]
        fig = apply_representative_layout(representative_figure())
        assert fig.to_plotly_json()["layout"]["template"] == untouched

    def test_theme_figure_is_a_no_op_when_light(self):
        before = go.Figure().to_plotly_json()
        fig = go.Figure()
        assert theme_figure(fig, dark=False) is fig
        assert fig.to_plotly_json() == before


class TestThemeDetection:
    """The theme comes from the app's own flag, not Streamlit's."""

    def test_false_outside_a_script_run(self):
        # Every unit test, script and import path lands here, and light is the
        # branch that changes nothing.
        assert is_dark_mode() is False

    def test_reads_the_dark_mode_session_flag(self, monkeypatch):
        import streamlit as st

        import fiscal_model.ui.charts as charts

        monkeypatch.setattr(charts, "_script_run_context", lambda: object())
        monkeypatch.setattr(st, "session_state", {"dark_mode": True})
        assert charts.is_dark_mode() is True

        monkeypatch.setattr(st, "session_state", {"dark_mode": False})
        assert charts.is_dark_mode() is False

    def test_falls_back_to_the_streamlit_theme(self, monkeypatch):
        """A deployment whose *Streamlit* config is dark still gets dark charts.

        This is the fallback, never the primary signal: on this deployment
        ``st.context.theme`` always reports light, because the app's dark mode
        is a CSS overlay Streamlit knows nothing about.
        """
        import streamlit as st

        import fiscal_model.ui.charts as charts

        monkeypatch.setattr(charts, "_script_run_context", lambda: object())
        monkeypatch.setattr(st, "session_state", {})

        class _Ctx:
            theme = type("T", (), {"type": "dark"})()

        monkeypatch.setattr(st, "context", _Ctx())
        assert charts.is_dark_mode() is True


class TestDarkModeLayout:
    """The dark branch has to beat Streamlit's frontend, which rewrites the
    template. Everything asserted here is therefore on ``layout``."""

    def test_canvas_is_transparent_not_repainted(self):
        fig = apply_representative_layout(representative_figure(), dark=True)
        assert fig.layout.paper_bgcolor == TRANSPARENT
        assert fig.layout.plot_bgcolor == TRANSPARENT

    def test_text_is_light(self):
        fig = apply_representative_layout(representative_figure(), dark=True)
        assert fig.layout.font.color == DARK_INK
        assert fig.layout.title.font.color == DARK_INK
        assert fig.layout.legend.font.color == DARK_MUTED_INK
        assert fig.layout.xaxis.tickfont.color == DARK_MUTED_INK
        assert fig.layout.yaxis.title.font.color == DARK_MUTED_INK

    def test_grid_and_axis_lines_are_dark(self):
        fig = apply_representative_layout(representative_figure(), dark=True)
        assert fig.layout.xaxis.gridcolor == DARK_GRID
        assert fig.layout.yaxis.gridcolor == DARK_GRID
        assert fig.layout.xaxis.zerolinecolor == DARK_AXIS_LINE
        assert fig.layout.yaxis.linecolor == DARK_AXIS_LINE

    def test_hover_label_sits_on_the_card_colour(self):
        fig = apply_representative_layout(representative_figure(), dark=True)
        assert fig.layout.hoverlabel.bgcolor == DARK_SURFACE
        assert fig.layout.hoverlabel.font.color == DARK_INK

    def test_secondary_axes_are_covered(self):
        """``update_?axes`` rather than ``layout={"yaxis": …}`` — the
        generational chart's ``yaxis2`` would otherwise keep light gridlines."""
        fig = apply_representative_layout(representative_figure(), dark=True)
        assert fig.layout.yaxis2.gridcolor == DARK_GRID
        assert fig.layout.yaxis2.tickfont.color == DARK_MUTED_INK

    def test_the_callers_own_layout_survives(self):
        """Theming runs last, so it must merge rather than replace."""
        fig = apply_representative_layout(representative_figure(), dark=True)
        assert fig.layout.height == 320
        assert fig.layout.title.text == "Deficit Impact Decomposition"
        assert fig.layout.legend.orientation == "h"
        assert fig.layout.legend.x == 1.0
        assert fig.layout.hovermode == "x unified"
        assert fig.layout.yaxis2.side == "right"
        assert fig.layout.meta == {"description": "alt"}

    def test_template_carries_what_layout_cannot(self):
        fig = apply_representative_layout(representative_figure(), dark=True)
        template = fig.layout.template
        assert tuple(template.layout.colorway) == DARK_COLORWAY
        assert template.layout.annotationdefaults.font.color == DARK_MUTED_INK

    def test_plotly_express_figures_are_themed_too(self):
        """PX charts (long_run_growth, generational, package pies) never meet
        ``apply_base_layout``; they go through ``theme_figure`` directly."""
        fig = theme_figure(px.line(x=[1, 2, 3], y=[1, 4, 9]), dark=True)
        assert fig.layout.paper_bgcolor == TRANSPARENT
        assert fig.layout.xaxis.gridcolor == DARK_GRID

    def test_a_stub_figure_is_skipped_rather_than_crashing(self):
        class Stub:
            pass

        stub = Stub()
        assert theme_figure(stub, dark=True) is stub

    def test_the_template_registers_once(self):
        assert dark_template() is dark_template()


class TestAccessibleChartWrapperThemes:
    def test_render_accessible_chart_themes_the_figure(self, monkeypatch):
        """The a11y wrapper is the safety net for figures that bypass
        ``apply_base_layout`` — the family-size ``px.bar``, mainly."""
        import fiscal_model.ui.charts as charts
        from fiscal_model.ui.a11y import ChartDescription, render_accessible_chart

        monkeypatch.setattr(charts, "is_dark_mode", lambda: True)

        fig = px.bar(x=["a", "b"], y=[1, 2])
        rendered: list = []

        class FakeSt:
            def caption(self, *_a, **_k):
                pass

            def plotly_chart(self, figure, **_k):
                rendered.append(figure)

            def markdown(self, *_a, **_k):
                pass

        render_accessible_chart(
            FakeSt(), fig, ChartDescription(title="T", summary="S")
        )
        assert rendered == [fig]
        assert fig.layout.paper_bgcolor == TRANSPARENT
        # The title is set by the wrapper *before* theming, so its colour has
        # to have been written afterwards or Streamlit repaints it dark ink.
        assert fig.layout.title.text == "T"
        assert fig.layout.title.font.color == DARK_INK


# ---------------------------------------------------------------------------
# Contrast — the palette has to be legible on the ground the overlay paints
# ---------------------------------------------------------------------------


def relative_luminance(hex_colour: str) -> float:
    """WCAG 2.1 relative luminance of a ``#rrggbb`` colour."""
    raw = hex_colour.lstrip("#")
    channels = [int(raw[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(a: str, b: str) -> float:
    la, lb = relative_luminance(a), relative_luminance(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


#: Every series colour the chart modules hard-code at the trace. These are
#: *not* swapped in dark mode — a trace colour beats a template colourway, and
#: recolouring red/green by theme would make the deficit direction mean two
#: different things. They only have to stay legible, and they do: the worst is
#: ``#2563EB`` at 3.66:1, above WCAG 2.1's 3:1 floor for non-text graphics.
HARD_CODED_SERIES_COLOURS = (
    COLOR_DEFICIT_UP,
    COLOR_DEFICIT_DOWN,
    COLOR_PRIMARY,
    COLOR_SECONDARY,
    "#2563EB",  # side_by_side policy A
    "#DC2626",  # side_by_side policy B
    "#aec7e8",  # generational baseline burden
    "#d62728",  # generational burden increase
    "#2ca02c",  # generational burden decrease / cumulative central estimate
    "#e74c3c",  # tariff consumer cost
)


@pytest.mark.parametrize("colour", HARD_CODED_SERIES_COLOURS)
def test_series_colours_clear_the_non_text_floor_on_dark(colour):
    assert contrast_ratio(colour, DARK_BACKGROUND) >= 3.0


@pytest.mark.parametrize("colour", DARK_COLORWAY)
def test_dark_colorway_clears_the_non_text_floor(colour):
    assert contrast_ratio(colour, DARK_BACKGROUND) >= 3.0


@pytest.mark.parametrize("colour", [DARK_INK, DARK_MUTED_INK])
def test_chart_text_clears_the_text_floor_on_dark(colour):
    # Axis ticks and legend entries are text: WCAG AA wants 4.5:1.
    assert contrast_ratio(colour, DARK_BACKGROUND) >= 4.5


def test_grid_is_visible_but_subordinate():
    grid = contrast_ratio(DARK_GRID, DARK_BACKGROUND)
    axis = contrast_ratio(DARK_AXIS_LINE, DARK_BACKGROUND)
    assert 1.5 < grid < 3.0, "gridlines must read as structure, not as data"
    assert grid < axis, "the zero line has to be louder than the gridlines"


def test_dark_palette_matches_the_chrome_overlay():
    """The chart canvas and the card behind it must agree.

    ``components/chrome.py`` owns the CSS overlay and ``ui/charts.py`` the
    figure JSON; neither imports the other, so this is the seam that keeps
    them in step.
    """
    from components import chrome

    assert DARK_BACKGROUND == chrome._DARK_BG
    assert DARK_SURFACE == chrome._DARK_SURFACE
    assert DARK_INK == chrome._DARK_INK
