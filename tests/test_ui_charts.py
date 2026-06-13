"""
Tests for the shared Plotly styling helpers in ``fiscal_model/ui/charts.py``.

The helper is pass-through by design, so the contract is: only supplied keys are
forwarded to ``update_layout`` (existing charts render identically), the legend
variants match what the tabs used verbatim, and ``**extra`` reaches the figure.
"""

import plotly.graph_objects as go

from fiscal_model.ui.charts import (
    COLOR_DEFICIT_DOWN,
    COLOR_DEFICIT_UP,
    apply_base_layout,
    horizontal_legend,
)


class TestHorizontalLegend:
    def test_center_alignment(self):
        legend = horizontal_legend(align="center")
        assert legend == {
            "orientation": "h", "yanchor": "bottom", "y": 1.02,
            "xanchor": "center", "x": 0.5,
        }

    def test_right_alignment(self):
        legend = horizontal_legend(align="right")
        assert legend["xanchor"] == "right"
        assert legend["x"] == 1.0
        assert legend["orientation"] == "h"


class TestApplyBaseLayout:
    def test_returns_same_figure(self):
        fig = go.Figure()
        assert apply_base_layout(fig, height=300) is fig

    def test_sets_height_and_titles(self):
        fig = apply_base_layout(
            go.Figure(), height=320, title="T", yaxis_title="Y",
        )
        assert fig.layout.height == 320
        assert fig.layout.title.text == "T"
        assert fig.layout.yaxis.title.text == "Y"

    def test_omitted_keys_are_not_forwarded(self):
        # Not passing showlegend/hovermode leaves them at Plotly defaults (None).
        fig = apply_base_layout(go.Figure(), height=300)
        assert fig.layout.showlegend is None
        assert fig.layout.hovermode is None  # untouched plotly default

    def test_explicit_none_xaxis_title_is_forwarded(self):
        # Passing xaxis_title=None must clear the axis title (distinct from
        # omitting it), which several tabs rely on.
        fig = apply_base_layout(go.Figure(), height=300, xaxis_title=None)
        assert fig.layout.xaxis.title.text is None

    def test_showlegend_false_is_applied(self):
        fig = apply_base_layout(go.Figure(), height=400, showlegend=False)
        assert fig.layout.showlegend is False

    def test_extra_kwargs_reach_layout(self):
        # Chart-specific keys (e.g. yaxis2, meta) flow through **extra.
        fig = apply_base_layout(
            go.Figure(), height=400,
            yaxis2={"title": "Secondary", "overlaying": "y", "side": "right"},
            meta={"description": "alt text"},
        )
        assert fig.layout.yaxis2.title.text == "Secondary"
        assert fig.layout.meta == {"description": "alt text"}

    def test_hovermode_and_legend_applied(self):
        fig = apply_base_layout(
            go.Figure(), height=400,
            hovermode="x unified", legend=horizontal_legend(align="center"),
        )
        assert fig.layout.hovermode == "x unified"
        assert fig.layout.legend.orientation == "h"


def test_color_palette_is_distinct():
    # The named palette should keep increase/decrease visually distinguishable.
    assert COLOR_DEFICIT_UP != COLOR_DEFICIT_DOWN
    assert COLOR_DEFICIT_UP.startswith("#")
