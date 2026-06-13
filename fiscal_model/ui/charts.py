"""
Shared Plotly styling helpers.

Chart construction is already centralised for accessibility via
``render_accessible_chart`` (see ``fiscal_model/ui/a11y.py``). This module
centralises the *visual* boilerplate that was duplicated across the chart-heavy
tabs (results, dynamic scoring, distribution): the repeated horizontal-legend
dict, the recurring deficit colour palette, and a single ``apply_base_layout``
entry point so every chart routes its layout through one place.

The helper is intentionally pass-through: callers still supply their own
height/margins/titles, so existing charts render identically — the win is one
styling vocabulary instead of nine ad-hoc ``update_layout`` calls.
"""

from __future__ import annotations

from typing import Any

# Shared palette. These hex values were previously hard-coded across tabs; name
# them once so a deficit increase is always the same red, a decrease the same
# green, etc.
COLOR_DEFICIT_UP = "#dc3545"    # red — increases the deficit
COLOR_DEFICIT_DOWN = "#28a745"  # green — decreases the deficit
COLOR_PRIMARY = "#1f77b4"       # blue — neutral / totals
COLOR_SECONDARY = "#ff7f0e"     # orange — secondary series

# Sentinel so callers can pass ``xaxis_title=None`` explicitly (Plotly treats an
# explicit None as "clear the title") while omission leaves the axis untouched.
_UNSET: Any = object()


def horizontal_legend(*, align: str = "center") -> dict[str, Any]:
    """
    Return a horizontal legend anchored just above the plot area.

    ``align`` is ``"center"`` (default) or ``"right"`` — the two variants that
    were duplicated verbatim across the tabs.
    """
    x, anchor = {"center": (0.5, "center"), "right": (1.0, "right")}[align]
    return {"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": anchor, "x": x}


def apply_base_layout(
    fig: Any,
    *,
    height: int,
    margin: dict[str, Any] | None = None,
    title: str | None = None,
    xaxis_title: Any = _UNSET,
    yaxis_title: str | None = None,
    showlegend: bool | None = None,
    legend: dict[str, Any] | None = None,
    hovermode: str | None = None,
    **extra: Any,
) -> Any:
    """
    Apply a chart's layout through a single, consistent entry point.

    Only the keyword arguments a caller supplies are forwarded to
    ``fig.update_layout`` (plus any ``extra`` for chart-specific keys such as
    ``yaxis2`` or ``meta``), so this is behaviour-preserving for existing
    charts. Returns ``fig`` for chaining.
    """
    layout: dict[str, Any] = {"height": height}
    if margin is not None:
        layout["margin"] = margin
    if title is not None:
        layout["title"] = title
    if xaxis_title is not _UNSET:
        layout["xaxis_title"] = xaxis_title
    if yaxis_title is not None:
        layout["yaxis_title"] = yaxis_title
    if showlegend is not None:
        layout["showlegend"] = showlegend
    if legend is not None:
        layout["legend"] = legend
    if hovermode is not None:
        layout["hovermode"] = hovermode
    layout.update(extra)
    fig.update_layout(**layout)
    return fig
