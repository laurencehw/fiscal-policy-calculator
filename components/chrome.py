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

Widget keys: the dynamic-scoring toggle keeps its historical key
``sidebar_setting_dynamic_scoring`` (share links encode it), and the
microdata preview keeps ``augmentation_preview_toggle``; the other model
settings use the ``setting_*`` keys introduced in the widget-keys commit
(``setting_dark_mode``, ``setting_macro_model``, ``setting_use_real_data``,
``setting_data_year``, ``setting_use_microsim``,
``setting_use_microsim_distribution``), all registered in
``fiscal_model/ui/session_state.py`` so cross-page state survives.
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


#: Session flag: the quiet degraded notice has already been shown this session.
_DEGRADATION_NOTICE_KEY = "_degradation_notice_shown"

#: Headline of the quiet notice, for one source and for several. Named so the
#: tests can assert on the exact strings the user reads.
DEGRADED_NOTICE_LABEL = "🟡 A data source is past its refresh window — details"
DEGRADED_NOTICE_LABEL_PLURAL = "🟡 {n} data sources are past their refresh window — details"


def _sources_past_tolerance(health: dict[str, Any]) -> list[str]:
    """Data sources that are *late*, not merely running on a snapshot.

    ``summarize_data_degradation`` is deliberately generous: it reports every
    caveat worth knowing, including ones that say nothing about whether the
    numbers on screen are current — microdata coverage against SOI, and the
    Python interpreter version. Neither is a data vintage, yet either alone
    used to raise a page-level "some data sources are running on older
    snapshots" notice, which is how a healthy deployment came to read as
    broken before anyone had scored anything (external UI review, 2026-09-01).

    A page-level notice is earned only when a source has fallen back to
    hardcoded values or has passed *its own* release-calendar tolerance — the
    ``is_stale`` flag each freshness payload computes, and FRED's expired-cache
    flag. IRS SOI three years behind is not late: that is the publication lag,
    and ``fiscal_model.freshness`` scores it ``level: "aging"``,
    ``is_stale: False``. Everything else stays a caveat, one click away in the
    data-status pill, which carries the amber dot either way.
    """
    late: list[str] = []

    baseline = health.get("baseline") or {}
    baseline_freshness = baseline.get("freshness") or {}
    if baseline.get("source") == "hardcoded_fallback" or baseline_freshness.get(
        "is_stale"
    ):
        late.append("baseline")

    # Only the two FRED states ``summarize_data_degradation`` writes a reason
    # for. An *expired cache* is stale too, and the Data Status panel says so
    # ("Stale cache (N days)"), but the summary emits no reason line for it —
    # counting it here would headline a late source the reasons never mention
    # (Cursor review, 2026-09-01). Add it once the summary grows that line.
    fred = health.get("fred") or {}
    if fred.get("source") == "fallback" or (
        fred.get("source") == "bundled" and fred.get("cache_is_expired")
    ):
        late.append("fred")

    irs = health.get("irs_soi") or {}
    if (irs.get("freshness") or {}).get("is_stale"):
        late.append("irs_soi")

    return late


def _claim_notice_slot(st_module: Any) -> bool:
    """True the first time a session asks to draw the quiet notice.

    Under ``st.navigation`` every page change is a full script rerun, so a
    per-page banner re-fires on every click of the top nav. Once per session is
    enough: the condition has not changed between clicks, and the data-status
    pill still shows amber on every page.
    """
    session_state = getattr(st_module, "session_state", None)
    if session_state is None:  # pragma: no cover — exotic test doubles
        return True
    try:
        if session_state.get(_DEGRADATION_NOTICE_KEY):
            return False
        session_state[_DEGRADATION_NOTICE_KEY] = True
    except Exception:  # pragma: no cover — exotic session_state stand-ins
        return True
    return True


def _render_degradation_banner(st_module: Any, health: dict[str, Any]) -> None:
    """Raise a page-level notice only when a data source is actually late.

    An *error* interrupts every page — a component that failed to load means
    the numbers cannot be trusted, and that bears repeating. The amber case is
    shown once per session, and only for the sources
    :func:`_sources_past_tolerance` accepts.
    """
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
        return

    late = _sources_past_tolerance(health)
    if not late:
        # Caveats, not staleness. The pill's amber dot and the Data Status
        # popover carry them; a page-level notice would overstate the problem.
        return

    if not _claim_notice_slot(st_module):
        return

    # Deliberately quiet (owner request, 2026-09-01): a collapsed, muted
    # disclosure rather than a full-width warning box — people should notice
    # it without discounting the whole exercise. The pill already carries the
    # amber dot; the reasons live one click away.
    label = (
        DEGRADED_NOTICE_LABEL
        if len(late) == 1
        else DEGRADED_NOTICE_LABEL_PLURAL.format(n=len(late))
    )
    with st_module.expander(label, expanded=False):
        st_module.caption(reason_lines)


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

    # Layout and brand first, health second. Streamlit streams each element to
    # the browser as it is created, and ``get_health_snapshot`` costs ~3s on the
    # first request of a container (it probes the baseline, FRED, SOI and the
    # microdata calibration; every later run is a memo hit). Computing it before
    # the title meant three seconds of blank page on a cold start, which is what
    # an external reviewer saw as a grey skeleton (2026-09-01). Nothing above
    # depends on the payload, so the title, subtitle and column frame can paint
    # while the probe runs.
    brand_col, status_col, settings_col = st_module.columns([6, 3, 1])

    with brand_col:
        if show_brand:
            st_module.markdown(f"### {APP_TITLE}")
            st_module.caption(APP_SUBTITLE)

    try:
        health = get_health_snapshot()
    except Exception:  # pragma: no cover — health must never break a page
        health = {}
    pill = data_status_pill(health)

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


# ── Cross-page links ─────────────────────────────────────────────────────
#
# ``st.page_link`` resolves a *string* argument by matching it against the
# ``script_path`` of every registered page — but ``app.build_navigation``
# registers pages from callables (``st.Page(fn, …)``), and Streamlit records an
# empty ``script_path`` for those (``commands/navigation.py``), so
# ``st.page_link("app_pages/methodology.py")`` raises ``StreamlitPageNotFound``.
# Passing the ``StreamlitPage`` object works, so the router hands its pages to
# this registry on every run and page bodies look siblings up by ``url_path``.
#
# Sharing the registry across sessions is safe: ``page_link`` reads only
# ``_script_hash`` (``md5(url_path)``) and ``url_path``, both derived from the
# path alone, so one session's page object links the same place as another's.
_PAGE_REGISTRY: dict[str, Any] = {}


def register_pages(pages: dict[str, Any]) -> None:
    """Record ``url_path -> StreamlitPage`` for :func:`page_link`."""
    _PAGE_REGISTRY.update(pages)


def page_link(st_module: Any, url_path: str, *, label: str, **kwargs: Any) -> None:
    """Link to a sibling page, falling back to a plain Markdown link.

    The fallback covers the surfaces that have no registry to read — the
    hand-rolled ``st_module`` fakes in the UI tests, and any run where the page
    body renders before the router has registered its pages.
    """
    target = _PAGE_REGISTRY.get(url_path)
    render_link = getattr(st_module, "page_link", None)
    if target is not None and render_link is not None:
        try:
            render_link(target, label=label, **kwargs)
            return
        except Exception:  # pragma: no cover — a link must never break a page
            pass
    st_module.markdown(f"[{label}](/{url_path})")
