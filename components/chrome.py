"""
Shared page chrome: brand line, data-status pill, and the settings popover.

Replaces the global sidebar. Every page in ``app_pages/`` calls
:func:`render_chrome` first and :func:`render_page_footer` last, so the three
things the sidebar used to own — Model settings, Data Status, and the dark-mode
CSS — are reachable from every surface instead of only the Calculator.

Owner decisions this implements (``planning/redesign/DECISIONS.md``):

- **#1** the compact ``CBO Feb 2026 · SOI 2023`` pill opens an ``st.popover``
  holding the full Data Status panel;
- **#2** no sidebar anywhere; dark mode and dynamic scoring live in a small ⚙
  popover (Phase 4 additionally surfaces the dynamic toggle inline next to
  Calculate).

Widget keys are unchanged from the sidebar implementation
(``sidebar_setting_dynamic_scoring``, ``dark_mode``, ``augmentation_preview_toggle``)
so share links and existing session state keep working.
"""

from __future__ import annotations

from typing import Any

from fiscal_model.ui.app_controller import (
    bootstrap_page,
    data_status_pill,
    render_data_status,
)
from fiscal_model.ui.cache import get_health_snapshot
from fiscal_model.ui.helpers import TEXTBOOK_HOME
from fiscal_model.ui.settings_controller import render_settings_tab
from fiscal_model.ui.tabs_controller import render_footer

APP_TITLE = "Fiscal Policy Impact Calculator"
APP_SUBTITLE = (
    "Estimate the 10-year budgetary and economic effects of U.S. tax and "
    "spending proposals. Powered by IRS data, FRED, and CBO methodology. "
    f"Companion to the [Public Economics textbook]({TEXTBOOK_HOME})."
)

# ── Dark mode ────────────────────────────────────────────────────────────
#
# Streamlit has no runtime theme-switch API, so dark mode is a CSS overlay.
# The overlay paints the page dark and forces light text; every Streamlit
# surface it does *not* repaint keeps its light-theme background and inherits
# that light text — i.e. renders white-on-white.
#
# Phase 6 browser verification found exactly that on the surfaces the redesign
# promoted out of the sidebar: the top-nav header, the data-status pill and ⚙
# popover triggers, the Build segmented control, the search input and the
# expander headers were all unreadable. Each block below repaints one of those,
# addressed by ``data-testid`` (stable across minor upgrades; a missed selector
# degrades to the old light surface rather than breaking layout).
#
# ``_DARK_SURFACE``/``_DARK_INK`` match Streamlit's own dark theme tokens, so
# the overlay and any natively dark surface agree.
_DARK_BG = "#0e1117"
_DARK_SURFACE = "#262730"
_DARK_INK = "#fafafa"

_DARK_MODE_CSS = f"""<style>
body, .stApp {{background-color: {_DARK_BG} !important; color: {_DARK_INK} !important;}}
section[data-testid="stSidebar"], section[data-testid="stSidebar"] > div
    {{background-color: {_DARK_SURFACE} !important;}}
.stMarkdown, p, h1, h2, h3, label {{color: {_DARK_INK} !important;}}
.metric-card {{background-color: {_DARK_SURFACE} !important;}}

/* Top navigation. The header is the one chrome element outside .stApp's
   paint, and on mobile it also hosts the collapsed-sidebar toggle. */
header[data-testid="stHeader"] {{background-color: {_DARK_BG} !important;}}
[data-testid="stTopNavLink"],
[data-testid="stTopNavDropdownLink"],
[data-testid="stTopNavSection"] {{color: {_DARK_INK} !important;}}

/* Chrome popovers (data-status pill, ⚙ settings), the Build segmented
   control, text/number inputs, select menus and expander headers. */
[data-testid="stPopoverBody"],
[data-testid="stPopoverButton"],
[data-testid="stBaseButton-secondary"],
[data-testid="stBaseButton-segmented_control"],
[data-testid="stBaseButton-segmented_controlActive"],
[data-testid="stTextInputRootElement"],
[data-testid="stTextInputRootElement"] > div,
[data-testid="stTextAreaRootElement"],
[data-testid="stNumberInputContainer"],
[data-testid="stElementToolbarButtonContainer"],
[data-testid="stExpander"] summary,
[data-baseweb="select"] > div,
[data-baseweb="popover"] [role="listbox"]
    {{background-color: {_DARK_SURFACE} !important; color: {_DARK_INK} !important;}}

/* Alerts tint a translucent panel and pair it with deliberately dark ink;
   over a dark page both vanish. Brightening the composite lifts them off the
   background while preserving the severity hue (amber warn vs red error). */
[data-testid="stAlertContainer"] {{filter: brightness(1.75) saturate(0.85);}}

/* App-owned cards. Their light palette is in ui/styles.py; without these the
   text rule above paints white ink onto a pale card. The impact colours are
   lifted rather than reused so red/green keep their contrast on a dark
   ground — the headline number must stay legible *and* keep its direction. */
.fpc-result-card {{background-color: {_DARK_SURFACE} !important;}}
.fpc-result-card-title, .fpc-result-card-note {{color: #c9ccd6 !important;}}
.fpc-impact-up {{color: #ff6b7a !important;}}
.fpc-impact-down {{color: #4ade80 !important;}}
.fpc-impact-flat {{color: #c9ccd6 !important;}}
.fpc-evidence-card
    {{background-color: #1b1e26 !important; border-color: #3d4048 !important;}}
.fpc-evidence-card-title {{color: #9aa4b2 !important;}}
.info-box
    {{background-color: #1e3a5f !important; border-left-color: #4da6ff !important;}}
</style>"""


def _disclosure(st_module: Any, label: str, *, help_text: str | None = None) -> Any:
    """Return a popover when the runtime has one, else an expander.

    ``st.popover`` landed in Streamlit 1.32; the app pins ``>=1.50`` so the
    fallback exists only for the hand-rolled ``st_module`` fakes the UI tests
    inject.
    """
    popover = getattr(st_module, "popover", None)
    if popover is not None:
        try:
            # ``width="stretch"`` rather than the deprecated
            # ``use_container_width=True`` — the latter renders a deprecation
            # notice in the app itself from Streamlit 1.56.
            return popover(label, width="stretch", help=help_text)
        except TypeError:  # pragma: no cover — older signature / test fakes
            return popover(label)
    return st_module.expander(label, expanded=False)


def _render_degradation_banner(st_module: Any, health: dict[str, Any]) -> None:
    """Render the degraded-data banner once per page, above the fold."""
    try:
        from fiscal_model.health import summarize_data_degradation
    except Exception:  # pragma: no cover — defensive
        return

    degradation = summarize_data_degradation(health)
    if not degradation.get("is_degraded"):
        return

    reason_lines = "\n".join(f"- {reason}" for reason in degradation.get("reasons", []))
    if degradation.get("severity") == "error":
        st_module.error("🔴 **Data error — results may be unreliable**\n\n" + reason_lines)
    else:
        st_module.warning(
            "🟡 **Some data sources are running on older snapshots**\n\n" + reason_lines
        )


def render_chrome(
    st_module: Any,
    deps: Any,
    *,
    show_brand: bool = True,
) -> dict[str, Any]:
    """Render the shared chrome and return the model-settings dict.

    Returns the same mapping ``render_settings_tab`` has always returned
    (``use_real_data``, ``dynamic_scoring``, ``macro_model``, ``use_microsim``,
    ``use_microsim_distribution``, ``data_year``, ``dark_mode``), so the scoring
    pages can pass it straight into the calculation pipeline.
    """
    bootstrap_page(st_module)

    try:
        health = get_health_snapshot()
    except Exception:  # pragma: no cover — health must never break a page
        health = {}
    pill = data_status_pill(health)

    brand_col, status_col, settings_col = st_module.columns([6, 3, 1])

    with brand_col:
        if show_brand:
            st_module.markdown(f"### {APP_TITLE}")
            st_module.caption(APP_SUBTITLE)

    # The chrome surfaces the degraded-data reasons inline below, so the panel
    # inside the popover renders its detail without repeating the banner.
    with status_col, _disclosure(
        st_module,
        f"{pill['dot']} {pill['label']}",
        help_text="Data vintages behind every number on this page.",
    ):
        render_data_status(
            st_module=st_module,
            deps=deps,
            health=health or None,
            show_banner=False,
        )

    with settings_col:
        settings = render_settings_tab(
            st_module=st_module,
            settings_tab=_disclosure(
                st_module, "⚙", help_text="Model settings, dark mode, and data options."
            ),
        )

    if settings.get("dark_mode", False):
        st_module.markdown(_DARK_MODE_CSS, unsafe_allow_html=True)

    _render_degradation_banner(st_module, health)
    st_module.markdown("---")

    return settings


def render_page_footer(st_module: Any) -> None:
    """Render the app footer once per page.

    Under the old tab layout this fired six or seven times per render (once per
    tab body). One page, one footer.
    """
    render_footer(st_module=st_module)
