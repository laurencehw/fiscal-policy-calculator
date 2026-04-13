"""
Accessibility helpers for the Streamlit app.

Streamlit renders Plotly charts inside an iframe, which prevents us from
attaching custom ``aria-label`` attributes directly from Python. This module
gets as close as possible to a compliant experience by combining three
tactics:

* **Title + meta on the Plotly figure** — screen readers that understand
  SVG use the chart ``title`` for the accessible name; ``meta.description``
  adds extra context.
* **Visible caption above the chart** — short, plain-language description
  that sighted users read too. Good UX and accessible by default.
* **Hidden screen-reader description + data table below the chart** — a
  ``sr-only`` block and optional expandable fallback table so non-visual
  users can consume the same information as the bar/line/waterfall view.

Any code that draws a chart should prefer :func:`render_accessible_chart`
over calling ``st.plotly_chart`` directly.
"""

from __future__ import annotations

import html
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# CSS injected by :func:`inject_a11y_styles`
# ---------------------------------------------------------------------------
#
# ``sr-only`` is the standard visually-hidden utility class used by Bootstrap,
# Tailwind, and the W3C accessibility guides. It keeps the element in the
# DOM (and therefore in the screen reader tree) without rendering it.
#
# The skip-link styles match the common pattern: hidden until keyboard focus,
# then anchored to the top-left corner with a high-contrast background.

A11Y_STYLES = """
<style>
    /* Visually hidden content for screen readers only.
       Matches the W3C recommended sr-only utility. */
    .sr-only {
        position: absolute !important;
        width: 1px !important;
        height: 1px !important;
        padding: 0 !important;
        margin: -1px !important;
        overflow: hidden !important;
        clip: rect(0, 0, 0, 0) !important;
        white-space: nowrap !important;
        border: 0 !important;
    }
    /* Skip-to-main-content link — hidden until focused via keyboard. */
    .skip-nav {
        position: absolute;
        left: -10000px;
        top: auto;
        width: 1px;
        height: 1px;
        overflow: hidden;
        z-index: 1000;
    }
    .skip-nav:focus {
        position: fixed;
        left: 8px;
        top: 8px;
        width: auto;
        height: auto;
        padding: 8px 12px;
        background: #1f77b4;
        color: #ffffff;
        border-radius: 4px;
        text-decoration: none;
        font-weight: 600;
        outline: 3px solid #ffbf47;
    }
    /* Make tab focus rings obvious for keyboard users. */
    .stTabs [data-baseweb="tab"]:focus-visible,
    .stButton button:focus-visible,
    .stSelectbox div[data-baseweb="select"]:focus-within {
        outline: 3px solid #ffbf47 !important;
        outline-offset: 2px !important;
    }
</style>
"""


SKIP_NAV_HTML = (
    '<a class="skip-nav" href="#main-content">Skip to main content</a>'
    '<a id="main-content" tabindex="-1"></a>'
)


def inject_a11y_styles(st_module: Any) -> None:
    """Inject accessibility CSS + skip-nav link at the top of the page.

    Safe to call once per app bootstrap. Not wrapped in a session-state
    guard because Streamlit de-duplicates identical markdown blocks.
    """
    st_module.markdown(A11Y_STYLES, unsafe_allow_html=True)
    st_module.markdown(SKIP_NAV_HTML, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Chart rendering
# ---------------------------------------------------------------------------


@dataclass
class ChartDescription:
    """Accessible description payload for a chart.

    ``title`` becomes the SVG ``<title>`` element (screen-reader accessible
    name). ``summary`` is a plain-language sentence rendered visibly above
    the chart and embedded in the hidden description. ``data_rows`` is an
    optional list of ``(label, value)`` tuples rendered in a fallback table
    inside an expander so keyboard / screen-reader users can read the
    underlying numbers directly.
    """

    title: str
    summary: str
    data_rows: list[tuple[str, str]] = field(default_factory=list)
    data_table_label: str = "Show chart data as a table"

    def hidden_description(self) -> str:
        """Render the full description as a single string for sr-only use."""
        parts = [f"{self.title}. {self.summary}"]
        if self.data_rows:
            parts.append("Values: " + "; ".join(f"{k}: {v}" for k, v in self.data_rows))
        return " ".join(parts)


def _ensure_figure_title(figure: Any, description: ChartDescription) -> None:
    """Attach title + meta to a Plotly figure if not already set.

    Tolerates figure-like objects that don't expose the full Plotly API
    (``layout`` attribute missing or ``update_layout`` unavailable) so the
    sr-only fallback path still renders a useful description for tests
    that pass stub objects.
    """
    try:
        layout = figure.layout
        # Respect an existing title if the caller already set one.
        current_title = getattr(layout.title, "text", None) if getattr(layout, "title", None) else None
        updates: dict[str, Any] = {
            "meta": {
                "description": description.summary,
                "accessible_title": description.title,
            }
        }
        if not current_title:
            updates["title"] = {"text": description.title, "xanchor": "left", "x": 0.0}
        figure.update_layout(**updates)
    except AttributeError:
        # Non-Plotly figure-like object (e.g. a test stub). The sr-only
        # description still covers screen reader users.
        pass


def render_accessible_chart(
    st_module: Any,
    figure: Any,
    description: ChartDescription,
    *,
    use_container_width: bool = True,
    key: str | None = None,
) -> None:
    """Render a Plotly figure with accessibility affordances.

    Combines a visible caption, a hidden screen-reader description, and an
    optional fallback data table so non-visual users get full access.
    """
    _ensure_figure_title(figure, description)

    # Visible caption (also read by screen readers via normal flow).
    st_module.caption(description.summary)

    kwargs: dict[str, Any] = {"use_container_width": use_container_width}
    if key is not None:
        kwargs["key"] = key
    st_module.plotly_chart(figure, **kwargs)

    # Hidden, screen-reader-only description. Uses the sr-only utility
    # injected by :func:`inject_a11y_styles`. The description is escaped
    # because ChartDescription can carry user-provided text (policy names,
    # preset captions) — without escaping, a crafted policy name could
    # inject arbitrary HTML into the sidebar panel.
    safe_description = html.escape(description.hidden_description(), quote=True)
    st_module.markdown(
        f'<div class="sr-only" role="note">{safe_description}</div>',
        unsafe_allow_html=True,
    )

    # Optional expandable data table — visible fallback for keyboard users
    # who can't visually interpret the chart.
    if description.data_rows:
        with st_module.expander(description.data_table_label, expanded=False):
            try:
                import pandas as pd

                df = pd.DataFrame(description.data_rows, columns=["Label", "Value"])
                st_module.dataframe(df, use_container_width=True, hide_index=True)
            except Exception:
                for label, value in description.data_rows:
                    st_module.markdown(f"- **{label}:** {value}")


# ---------------------------------------------------------------------------
# Small helpers for building data rows from common result shapes
# ---------------------------------------------------------------------------


def format_currency_rows(pairs: Iterable[tuple[str, float]]) -> list[tuple[str, str]]:
    """Format ``(label, billions)`` pairs as display rows for a data table."""
    return [(label, f"${value:+,.1f}B") for label, value in pairs]


def landmark(st_module: Any, tag: str, html: str) -> None:
    """Emit a semantic HTML landmark (e.g. ``<nav>``, ``<main>``).

    Streamlit wraps every call in its own ``<div>``, so this helper exists
    mainly to make call sites self-documenting.
    """
    st_module.markdown(f"<{tag}>{html}</{tag}>", unsafe_allow_html=True)


__all__ = [
    "A11Y_STYLES",
    "SKIP_NAV_HTML",
    "ChartDescription",
    "format_currency_rows",
    "inject_a11y_styles",
    "landmark",
    "render_accessible_chart",
]
