"""
Pins the light-mode Plotly layout ``fiscal_model/ui/charts.py`` produces.

This file is deliberately committed **before** the dark-mode work lands. Its
job is to be the "before" photograph: the dark-mode change is only allowed to
add behaviour on the dark branch, so whatever ``apply_base_layout`` writes for
a light page has to survive the change byte for byte.

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

import plotly.graph_objects as go

from fiscal_model.ui.charts import apply_base_layout, horizontal_legend

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
