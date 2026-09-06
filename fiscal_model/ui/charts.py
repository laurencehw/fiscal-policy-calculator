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

Dark mode
---------

The app's dark mode is a CSS overlay (``components/chrome.py``), not a real
Streamlit theme, so Streamlit still believes the page is light and paints its
charts accordingly: white canvas on a dark page. :func:`theme_figure` is the
Python-side half of the overlay.

**How the theme is detected.** The single source of truth is the session flag
``st.session_state["dark_mode"]`` — the ⚙ popover's toggle, written by
``ui/settings_controller.py`` and read by ``chrome.render_chrome`` to decide
whether to inject the overlay. ``st.context.theme`` exists in the pinned
Streamlit (1.56) but reports the *Streamlit* theme, which for this deployment
is always light; using it would make the charts disagree with the page. It is
read only as a fallback, so a deployment that one day ships a genuinely dark
Streamlit config still gets dark charts. Chrome renders before every page body,
so the flag is settled before any figure is built.

**Why the styling is applied at layout level, not only via a template.**
``st.plotly_chart(..., theme="streamlit")`` — the default, used by every call
site — makes Streamlit's frontend merge *its own* layout (fonts, gridcolours,
``paper_bgcolor``, ``plot_bgcolor``) into ``figure.layout.template.layout``
before rendering. A custom template alone is therefore overwritten. Plotly
resolves ``layout.X`` ahead of ``layout.template.layout.X``, so the values that
must survive are set on the layout itself; the registered ``fpc_dark`` template
carries what Streamlit does not touch (``colorway``, annotation and shape
defaults, trace-level colourscales). Between them no ``theme=`` argument has to
change at any call site.

**Light mode is untouched.** :func:`theme_figure` returns immediately on a
light page: no template swap, no layout keys, so the light theme stays exactly
what Streamlit's own ``streamlit`` template renders today. Substituting
``plotly_white`` would have changed every light chart — different gridline
colour, different fonts, x-grid on — and light is the half being held fixed.
``tests/test_charts_theme.py`` pins that dict.
"""

from __future__ import annotations

import copy
from typing import Any

# Shared palette. These hex values were previously hard-coded across tabs; name
# them once so a deficit increase is always the same red, a decrease the same
# green, etc.
COLOR_DEFICIT_UP = "#dc3545"    # red — increases the deficit
COLOR_DEFICIT_DOWN = "#28a745"  # green — decreases the deficit
COLOR_PRIMARY = "#1f77b4"       # blue — neutral / totals
COLOR_SECONDARY = "#ff7f0e"     # orange — secondary series

# ── Dark palette ─────────────────────────────────────────────────────────
#
# These mirror ``components/chrome.py``'s ``_DARK_BG`` / ``_DARK_SURFACE`` /
# ``_DARK_INK`` so a chart and the card behind it agree; the mirror is a test
# (``test_charts_theme.py::test_dark_palette_matches_the_chrome_overlay``)
# rather than an import, to keep this module free of a UI-chrome dependency.
DARK_BACKGROUND = "#0e1117"   # the page colour the overlay paints
DARK_SURFACE = "#262730"      # cards, popovers — and the hover label
DARK_INK = "#fafafa"          # primary text
DARK_MUTED_INK = "#c9ccd6"    # axis ticks, legend entries, axis titles
DARK_GRID = "#3d4048"         # gridlines — deliberately quiet
DARK_AXIS_LINE = "#5a5f6b"    # zero lines and axis spines, one step louder

#: Transparent, so the page colour (light *or* dark) shows through instead of
#: a painted rectangle that has to be kept in sync with the overlay.
TRANSPARENT = "rgba(0,0,0,0)"

#: Qualitative series colours for charts that do not set their own (Plotly
#: Express mostly). Lightened from the default D3 wheel so each clears 3:1
#: against :data:`DARK_BACKGROUND` — the WCAG 2.1 non-text contrast floor.
DARK_COLORWAY = (
    "#63a8e8",  # blue
    "#ffa24d",  # orange
    "#4ade80",  # green
    "#ff6b7a",  # red
    "#c39bf5",  # purple
    "#d1a06a",  # brown
    "#f79edb",  # pink
    "#a5adba",  # grey
    "#dede5a",  # olive
    "#5fd6e0",  # cyan
)

#: Registered name of the dark template. Registration is lazy (see
#: :func:`dark_template`) so importing this module does not touch
#: ``plotly.io.templates``.
DARK_TEMPLATE_NAME = "fpc_dark"

#: Session-state key the ⚙ settings popover writes. ``setting_dark_mode`` is
#: the *widget* key; this is the code key the rest of the app reads.
DARK_MODE_SESSION_KEY = "dark_mode"

# Sentinel so callers can pass ``xaxis_title=None`` explicitly (Plotly treats an
# explicit None as "clear the title") while omission leaves the axis untouched.
_UNSET: Any = object()


# ---------------------------------------------------------------------------
# Theme detection
# ---------------------------------------------------------------------------


def is_dark_mode() -> bool:
    """Return whether the current page is being rendered in dark mode.

    Reads the ⚙ popover's ``dark_mode`` session flag — the same value
    ``chrome.render_chrome`` uses to decide whether to inject the CSS overlay,
    so the charts and the page can never disagree. Falls back to
    ``st.context.theme`` for a deployment whose *Streamlit* theme is dark.

    Returns ``False`` outside a script run (unit tests, scripts, imports),
    which is the safe default: light mode is the untouched path.
    """
    try:
        from streamlit.runtime.scriptrunner_utils.script_run_context import (
            get_script_run_ctx,
        )

        if get_script_run_ctx(suppress_warning=True) is None:
            return False
    except Exception:  # pragma: no cover — Streamlit internals moved
        return False

    try:
        import streamlit as st
    except Exception:  # pragma: no cover — Streamlit not installed
        return False

    try:
        if bool(st.session_state.get(DARK_MODE_SESSION_KEY, False)):
            return True
    except Exception:  # pragma: no cover — session state unavailable
        pass

    try:
        return getattr(st.context.theme, "type", None) == "dark"
    except Exception:  # pragma: no cover — no context (older/odd runtimes)
        return False


# ---------------------------------------------------------------------------
# The dark template
# ---------------------------------------------------------------------------


def dark_template() -> Any:
    """Return (registering on first call) the app's dark Plotly template.

    Derived from ``plotly_dark`` so the trace-level defaults — colourscales,
    marker outlines, waterfall connectors — come from a template that was
    designed for a dark ground, then overridden with the app's own palette and
    a transparent canvas.
    """
    import plotly.graph_objects as go
    import plotly.io as pio

    # ``TemplatesConfig`` is dict-like but has no ``.get``.
    if DARK_TEMPLATE_NAME in pio.templates:
        return pio.templates[DARK_TEMPLATE_NAME]

    template = copy.deepcopy(pio.templates["plotly_dark"])
    template.layout.update(
        paper_bgcolor=TRANSPARENT,
        plot_bgcolor=TRANSPARENT,
        colorway=list(DARK_COLORWAY),
        font=go.layout.Font(color=DARK_INK),
        title=go.layout.Title(font=go.layout.title.Font(color=DARK_INK)),
        legend=go.layout.Legend(
            bgcolor=TRANSPARENT,
            bordercolor=DARK_GRID,
            font=go.layout.legend.Font(color=DARK_MUTED_INK),
        ),
        hoverlabel=go.layout.Hoverlabel(
            bgcolor=DARK_SURFACE,
            bordercolor=DARK_GRID,
            font=go.layout.hoverlabel.Font(color=DARK_INK),
        ),
        xaxis=go.layout.XAxis(**_dark_axis_kwargs(showgrid=False)),
        yaxis=go.layout.YAxis(**_dark_axis_kwargs(showgrid=True)),
        annotationdefaults=go.layout.Annotation(
            arrowcolor=DARK_MUTED_INK,
            font=go.layout.annotation.Font(color=DARK_MUTED_INK),
        ),
        shapedefaults=go.layout.Shape(line=go.layout.shape.Line(color=DARK_GRID)),
    )
    pio.templates[DARK_TEMPLATE_NAME] = template
    return template


def _dark_axis_kwargs(*, showgrid: bool | None = None) -> dict[str, Any]:
    """Axis colours for a dark ground, as ``update_axes``-shaped keywords."""
    kwargs: dict[str, Any] = {
        "gridcolor": DARK_GRID,
        "zerolinecolor": DARK_AXIS_LINE,
        "linecolor": DARK_AXIS_LINE,
        "tickcolor": DARK_AXIS_LINE,
        "tickfont": {"color": DARK_MUTED_INK},
        "title": {"font": {"color": DARK_MUTED_INK}},
    }
    if showgrid is not None:
        kwargs["showgrid"] = showgrid
    return kwargs


def _dark_layout_kwargs() -> dict[str, Any]:
    """The layout keys Streamlit's frontend would otherwise repaint light.

    Everything here is set on ``layout`` rather than on the template because
    ``theme="streamlit"`` rewrites ``layout.template.layout`` client-side.
    Plotly resolves ``layout`` first, so these win.
    """
    return {
        "paper_bgcolor": TRANSPARENT,
        "plot_bgcolor": TRANSPARENT,
        "font": {"color": DARK_INK},
        "title": {"font": {"color": DARK_INK}},
        "legend": {
            "bgcolor": TRANSPARENT,
            "bordercolor": DARK_GRID,
            "font": {"color": DARK_MUTED_INK},
        },
        "hoverlabel": {
            "bgcolor": DARK_SURFACE,
            "bordercolor": DARK_GRID,
            "font": {"color": DARK_INK},
        },
    }


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def horizontal_legend(*, align: str = "center") -> dict[str, Any]:
    """
    Return a horizontal legend anchored just above the plot area.

    ``align`` is ``"center"`` (default) or ``"right"`` — the two variants that
    were duplicated verbatim across the tabs.
    """
    x, anchor = {"center": (0.5, "center"), "right": (1.0, "right")}[align]
    return {"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": anchor, "x": x}


def theme_figure(fig: Any, *, dark: bool | None = None) -> Any:
    """Apply the page's theme to ``fig``. A no-op on a light page.

    Call this *last*, after the chart's own ``update_layout`` and after any
    title has been set (``a11y._ensure_figure_title``), so the theme's colours
    land on the final layout rather than being overwritten by it.

    ``dark`` overrides the detection, which is what the tests use. Tolerates
    figure-like stubs that do not expose the Plotly API, as ``a11y`` does.
    """
    if dark is None:
        dark = is_dark_mode()
    if not dark:
        return fig

    # Duck-type rather than swallow exceptions: a stub that is not a Plotly
    # figure is skipped here, but a real failure inside the block below is a
    # bug and must not be silently turned into a light chart.
    if not all(
        callable(getattr(fig, name, None))
        for name in ("update_layout", "update_xaxes", "update_yaxes")
    ):
        return fig

    fig.update_layout(template=dark_template(), **_dark_layout_kwargs())
    # ``update_?axes`` rather than ``layout={"xaxis": …}`` so secondary and
    # subplot axes (``yaxis2`` in the generational chart) are covered too.
    axis_kwargs = _dark_axis_kwargs()
    fig.update_xaxes(**axis_kwargs)
    fig.update_yaxes(**axis_kwargs)
    return fig


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
    dark: bool | None = None,
    **extra: Any,
) -> Any:
    """
    Apply a chart's layout through a single, consistent entry point.

    Only the keyword arguments a caller supplies are forwarded to
    ``fig.update_layout`` (plus any ``extra`` for chart-specific keys such as
    ``yaxis2`` or ``meta``), so this is behaviour-preserving for existing
    charts. The page theme is applied afterwards via :func:`theme_figure`,
    which does nothing on a light page. Returns ``fig`` for chaining.
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
    return theme_figure(fig, dark=dark)


__all__ = [
    "COLOR_DEFICIT_DOWN",
    "COLOR_DEFICIT_UP",
    "COLOR_PRIMARY",
    "COLOR_SECONDARY",
    "DARK_AXIS_LINE",
    "DARK_BACKGROUND",
    "DARK_COLORWAY",
    "DARK_GRID",
    "DARK_INK",
    "DARK_MODE_SESSION_KEY",
    "DARK_MUTED_INK",
    "DARK_SURFACE",
    "DARK_TEMPLATE_NAME",
    "TRANSPARENT",
    "apply_base_layout",
    "dark_template",
    "horizontal_legend",
    "is_dark_mode",
    "theme_figure",
]
