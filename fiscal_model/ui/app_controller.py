"""
Top-level Streamlit app orchestration.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .calculation_controller import (
    ensure_results_state,
    execute_calculation_if_requested,
    render_sidebar_inputs,
)
from .controller_utils import compute_run_id
from .helpers import TEXTBOOK_HOME, TEXTBOOK_LINKS
from .settings_controller import render_settings_tab
from .tabs_controller import build_main_tabs, render_footer, render_result_tabs

_HOW_SCORED_MARKDOWN = (
    "The calculator applies three steps:\n\n"
    "1. **Static scoring** — direct revenue effect of the policy change\n"
    "2. **Behavioral response** — how taxpayers adjust based on the Elasticity of "
    "Taxable Income (ETI = 0.25, "
    "[Saez et al. 2012](https://eml.berkeley.edu/~saez/saez-slemrod-giertzJEL12.pdf))\n"
    "3. **Dynamic feedback** *(optional)* — GDP and employment effects using "
    "FRB/US-calibrated multipliers\n\n"
    "Data: IRS Statistics of Income, FRED, CBO Baseline Projections. "
    "25+ policies validated within 15% of official CBO/JCT scores.\n\n"
    "For background, see "
    f"[Optimal Taxation (Ch 16)]({TEXTBOOK_LINKS['optimal_taxation']}) and "
    f"[The Federal Budget (Ch 22)]({TEXTBOOK_LINKS['federal_budget']}) in the textbook."
)

_PENDING_SIDEBAR_UPDATES_KEY = "_pending_sidebar_updates"


def _queue_sidebar_updates(st_module: Any, **updates: Any) -> None:
    """Queue sidebar widget state updates for the next rerun."""
    st_module.session_state[_PENDING_SIDEBAR_UPDATES_KEY] = updates
    st_module.session_state["qs_calculate"] = True


def _apply_pending_sidebar_updates(st_module: Any) -> None:
    """Apply deferred sidebar widget state before sidebar widgets are created."""
    updates = st_module.session_state.pop(_PENDING_SIDEBAR_UPDATES_KEY, None)
    if not updates:
        return

    for key, value in updates.items():
        st_module.session_state[key] = value


def render_data_status(st_module: Any, deps: Any) -> None:
    """
    Render a data status indicator in the sidebar showing CBO baseline vintage
    and FRED data status. Placed at the bottom of the sidebar.
    """
    try:
        fred_status = "Unknown"
        fred_source = None
        cache_age_days = None

        try:
            from fiscal_model.data.fred_data import FREDData
            fred_instance = FREDData()
            data_status = fred_instance.data_status
            fred_source = data_status.get("source", "unknown")
            cache_age_days = data_status.get("cache_age_days")
            cache_is_expired = data_status.get("cache_is_expired", False)

            if fred_source == "live":
                fred_status = "🟢 Live (FRED API)"
            elif fred_source == "cache" and cache_is_expired:
                fred_status = f"🟠 Stale cache ({cache_age_days} days old)"
            elif fred_source == "cache":
                fred_status = f"🟡 Cached ({cache_age_days} days old)"
            elif fred_source == "fallback":
                fred_status = "🔴 Fallback (hardcoded values)"
            else:
                fred_status = None
        except Exception:
            fred_status = None

        try:
            baseline_display = "CBO Feb 2026"
            vintage_color = "green"
        except Exception:
            baseline_display = "Unknown"
            vintage_color = "gray"

        st_module.markdown("---")
        st_module.markdown("**📊 Data Status**")

        if vintage_color == "green":
            st_module.markdown(f"🟢 **Baseline:** {baseline_display}")
        elif vintage_color == "yellow":
            st_module.markdown(f"🟡 **Baseline:** {baseline_display}")
        else:
            st_module.markdown(f"⚪ **Baseline:** {baseline_display}")

        if fred_status:
            st_module.markdown(f"📡 **FRED:** {fred_status}")
        else:
            st_module.markdown("📋 **Data:** IRS SOI 2022, CBO Feb 2026")

        with st_module.expander("ℹ️ Data details", expanded=False):
            st_module.markdown(
                "**Baseline:** Uses CBO February 2026 economic assumptions for "
                "projections (inflation, GDP growth, unemployment).\n\n"
                "**FRED Data:** Automatically fetches recent macro series "
                "(GDP, unemployment, interest rates) when API key is available. "
                "Falls back to cache or hardcoded values if needed.\n\n"
                "**Last Updated:** Baseline assumptions are updated quarterly "
                "with new CBO publications."
            )
    except Exception:
        pass


def render_quick_start(st_module: Any) -> None:
    """
    Render a dismissible quick-start guide with clickable policy cards.
    Auto-dismissed once results exist.
    """
    if "quick_start_dismissed" not in st_module.session_state:
        st_module.session_state.quick_start_dismissed = False

    # Auto-dismiss once results have been calculated
    if st_module.session_state.get("results"):
        st_module.session_state.quick_start_dismissed = True

    if not st_module.session_state.quick_start_dismissed:
        col1, col2 = st_module.columns([20, 1])
        with col1:
            st_module.markdown(
                "👋 Estimate the 10-year budget impact of any U.S. tax or spending proposal, "
                "backed by IRS data and CBO methodology. "
                "Click a card below to load a preset and run a calculation instantly."
            )
        with col2:
            if st_module.button("✕", key="dismiss_quick_start"):
                st_module.session_state.quick_start_dismissed = True
                st_module.rerun()

        c1, c2, c3 = st_module.columns(3)

        with c1, st_module.container(border=True):
            st_module.markdown("**TCJA Extension**")
            st_module.caption("Extend all individual TCJA provisions beyond the 2025 sunset")
            st_module.markdown(
                '<span style="color:#d9534f;font-weight:600">▲ +$4.6T to deficit</span>'
                " &nbsp;*(10-yr, CBO)*",
                unsafe_allow_html=True,
            )
            if st_module.button("Try this →", key="qs_btn_tcja", use_container_width=True):
                _queue_sidebar_updates(
                    st_module=st_module,
                    sidebar_analysis_mode="📋 Tax proposal (preset)",
                    sidebar_policy_area="TCJA / Individual",
                    sidebar_preset_choice="TCJA Full Extension",
                )
                st_module.rerun()

        with c2, st_module.container(border=True):
            st_module.markdown("**Biden 400K+ Tax**")
            st_module.caption("Restore 39.6% top rate on income above $400K")
            st_module.markdown(
                '<span style="color:#5cb85c;font-weight:600">▼ −$252B from deficit</span>'
                " &nbsp;*(10-yr, Treasury)*",
                unsafe_allow_html=True,
            )
            if st_module.button("Try this →", key="qs_btn_biden", use_container_width=True):
                _queue_sidebar_updates(
                    st_module=st_module,
                    sidebar_analysis_mode="📋 Tax proposal (preset)",
                    sidebar_policy_area="Income Tax",
                    sidebar_preset_choice="Biden 2025 Proposal",
                )
                st_module.rerun()

        with c3, st_module.container(border=True):
            st_module.markdown("**Infrastructure $100B/yr**")
            st_module.caption("Federal investment in roads, broadband, and water systems")
            st_module.markdown(
                '<span style="color:#d9534f;font-weight:600">▲ +$1.0T to deficit</span>'
                " &nbsp;*(10-yr, est.)*",
                unsafe_allow_html=True,
            )
            if st_module.button("Try this →", key="qs_btn_infra", use_container_width=True):
                _queue_sidebar_updates(
                    st_module=st_module,
                    sidebar_analysis_mode="💰 Spending program",
                    sidebar_spending_preset="Infrastructure Investment ($100B/yr)",
                )
                st_module.rerun()

        st_module.markdown("---")


def run_main_app(st_module: Any, deps: Any, model_available: bool, app_root: Path) -> None:
    """
    Render and orchestrate the full Streamlit app flow.
    Top-level tabs: Calculator | Budget Builder | Generational | State | Bill Tracker | Methodology
    """
    st_module.title("Fiscal Policy Impact Calculator")
    st_module.markdown(
        "Estimate the 10-year budgetary and economic effects of U.S. tax and "
        "spending proposals. Powered by IRS data, FRED, and CBO methodology. "
        f"Companion to the [Public Economics textbook]({TEXTBOOK_HOME}). "
        "🎓 [**Classroom Mode**](?mode=classroom) — interactive assignments for Public Economics courses.\n\n"
        "🆕 **Can you balance the budget?** Try the **⚖️ Budget Builder** tab →"
    )

    top_tabs = st_module.tabs([
        "📊 Calculator",
        "⚖️ Budget Builder",
        "🌐 Generational",
        "🗺️ State",
        "📋 Bill Tracker",
        "📖 Methodology",
    ])

    with top_tabs[0]:
        _render_calculator(
            st_module=st_module,
            deps=deps,
            model_available=model_available,
            app_root=app_root,
        )
        render_footer(st_module=st_module)

    _logger = logging.getLogger(__name__)

    with top_tabs[1]:
        try:
            _render_budget_builder(st_module=st_module, deps=deps)
        except Exception:
            _logger.exception("Budget Builder error")
            st_module.error(
                "The Budget Builder encountered an issue. "
                "Please try reloading the page or clearing your inputs."
            )
        render_footer(st_module=st_module)

    with top_tabs[2]:
        try:
            _render_generational(st_module=st_module, deps=deps)
        except Exception:
            _logger.exception("Generational analysis error")
            st_module.error(
                "The Generational analysis encountered an issue. "
                "Please try adjusting your parameters or reloading the page."
            )
        render_footer(st_module=st_module)

    with top_tabs[3]:
        try:
            _render_state(st_module=st_module, deps=deps)
        except Exception:
            _logger.exception("State analysis error")
            st_module.error(
                "The State analysis encountered an issue. "
                "Please try reloading the page."
            )
        render_footer(st_module=st_module)

    with top_tabs[4]:
        try:
            deps.render_bill_tracker_tab(st_module=st_module)
        except Exception:
            _logger.exception("Bill Tracker error")
            st_module.error(
                "The Bill Tracker encountered an issue. "
                "Please try reloading the page."
            )
        render_footer(st_module=st_module)

    with top_tabs[5]:
        try:
            deps.render_methodology_tab(st_module=st_module)
        except Exception:
            _logger.exception("Methodology tab error")
            st_module.error(
                "The Methodology tab encountered an issue. "
                "Please try reloading the page."
            )
        render_footer(st_module=st_module)


def _render_calculator(
    st_module: Any,
    deps: Any,
    model_available: bool,
    app_root: Path,
) -> None:
    """Render the Calculator tab: sidebar inputs + results tabs."""
    # ── Sidebar ──────────────────────────────────────────────────────────
    _apply_pending_sidebar_updates(st_module=st_module)

    with st_module.sidebar:
        st_module.header("Policy Configuration")

        # 1. Policy inputs (no Calculate button yet)
        calc_context = render_sidebar_inputs(st_module=st_module, deps=deps)

        # 2. Model settings expander (above Calculate button)
        settings = render_settings_tab(
            st_module=st_module,
            settings_tab=st_module.expander("⚙️ Model settings", expanded=False),
        )

        # Apply dark mode via CSS class (better compatibility)
        if settings.get("dark_mode", False):
            st_module.markdown(
                '<style>'
                'body, .stApp {background-color: #0e1117 !important; color: #fafafa !important;} '
                '.stMarkdown, p, h1, h2, h3, label {color: #fafafa !important;} '
                '.metric-card {background-color: #262730 !important;}'
                '</style>',
                unsafe_allow_html=True,
            )

        # 3. Calculate button
        st_module.markdown("---")
        calculate = st_module.button(
            "Calculate Impact",
            type="primary",
            use_container_width=True,
        )
        # Auto-trigger from quick-start card click
        if getattr(st_module.session_state, "qs_calculate", False):
            del st_module.session_state["qs_calculate"]
            calculate = True
        calc_context["calculate"] = calculate

        # 4. Data Status (bottom of sidebar — infrastructure, not decision-relevant)
        render_data_status(st_module=st_module, deps=deps)

        with st_module.expander("🎓 Classroom Mode", expanded=False):
            st_module.markdown(
                "**Interactive assignments for Public Economics courses.**\n\n"
                "7 guided assignments with hints, auto-grading, and PDF export for student submissions. "
                "Covers Laffer curves, TCJA, distributional analysis, and more.\n\n"
                "[➡️ Open Classroom Mode](?mode=classroom)"
            )

    # ── Main content ─────────────────────────────────────────────────────
    calc_context["run_id"] = compute_run_id(calc_context=calc_context, settings=settings)
    st_module.session_state.current_run_id = calc_context["run_id"]

    # Dismissible welcome guide (auto-hides after first calculation)
    render_quick_start(st_module=st_module)

    # "How is this scored?" — prominent in main content below title
    with st_module.expander("🔍 How is this scored?", expanded=False):
        st_module.markdown(_HOW_SCORED_MARKDOWN)

    tabs = build_main_tabs(
        st_module=st_module,
        mode=calc_context["mode"],
    )

    ensure_results_state(st_module=st_module)
    execute_calculation_if_requested(
        st_module=st_module,
        deps=deps,
        app_root=app_root,
        model_available=model_available,
        calc_context=calc_context,
        settings=settings,
    )

    render_result_tabs(
        st_module=st_module,
        deps=deps,
        tabs=tabs,
        settings=settings,
        model_available=model_available,
        is_spending=calc_context["is_spending"],
        mode=calc_context["mode"],
    )


def _render_budget_builder(st_module: Any, deps: Any) -> None:
    """Render the Budget Builder tab — standalone deficit reduction planner."""
    from fiscal_model.ui.tabs.deficit_target import render_deficit_target_tab

    render_deficit_target_tab(
        st_module=st_module,
        cbo_score_map=deps.CBO_SCORE_MAP,
        fiscal_policy_scorer_cls=deps.FiscalPolicyScorer,
        use_real_data=True,
    )


def _render_generational(st_module: Any, deps: Any) -> None:
    """Render the top-level Generational Analysis tab."""
    result_data = st_module.session_state.get("results")
    run_id = st_module.session_state.get("results_run_id") or st_module.session_state.get("last_run_id")
    deps.render_generational_analysis_tab(
        st_module=st_module,
        result_data=result_data,
        run_id=run_id,
    )


def _render_state(st_module: Any, deps: Any) -> None:
    """Render the top-level State Analysis tab with its own state selector."""
    from fiscal_model.models.state.database import STATE_NAMES, SUPPORTED_STATES

    state_selection = st_module.selectbox(
        "State",
        options=SUPPORTED_STATES,
        format_func=lambda code: f"{code} — {STATE_NAMES[code]}",
        key="top_level_state_select",
        help="Select a state for combined federal + state analysis.",
    )
    selected_state = state_selection if state_selection else "CA"

    result_data = st_module.session_state.get("results")
    run_id = st_module.session_state.get("results_run_id") or st_module.session_state.get("last_run_id")
    deps.render_state_analysis_tab(
        st_module=st_module,
        state=selected_state,
        result_data=result_data,
        run_id=run_id,
    )
