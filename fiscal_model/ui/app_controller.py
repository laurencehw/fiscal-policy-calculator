"""
Top-level Streamlit app orchestration.
"""

from __future__ import annotations

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

            if fred_source == "live":
                fred_status = "🟢 Live (FRED API)"
            elif fred_source == "cache":
                fred_status = f"🟡 Cached ({cache_age_days} days old)"
            elif fred_source == "fallback":
                fred_status = "🔴 Fallback (hardcoded values)"
            else:
                fred_status = "⚪ Not available"
        except Exception:
            fred_status = "⚪ Not available"

        try:
            from fiscal_model.baseline import BaselineVintage
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

        st_module.markdown(f"📡 **Data:** {fred_status}")

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
    Render a dismissible quick-start guide. Auto-dismissed once results exist.
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
                """
                **👋 Welcome to the Fiscal Policy Calculator**

                Try one of these scenarios to get started:
                - **TCJA Extension** — What would extending the 2017 tax cuts cost?
                  Select 'TCJA Full Extension' from presets
                - **Biden High-Income Tax** — Score a 2.6pp increase on income above $400K
                - **Infrastructure Spending** — Model a $100B/year infrastructure program

                Select a preset from the sidebar, then click **Calculate** to see results.
                """
            )
        with col2:
            if st_module.button("✕", key="dismiss_quick_start"):
                st_module.session_state.quick_start_dismissed = True
                st_module.rerun()
        st_module.markdown("---")


def run_main_app(st_module: Any, deps: Any, model_available: bool, app_root: Path) -> None:
    """
    Render and orchestrate the full Streamlit app flow.
    Top-level tabs: Calculator | Generational | State | Bill Tracker | Methodology
    """
    st_module.title("Fiscal Policy Impact Calculator")
    st_module.caption(
        "Estimate the 10-year budgetary and economic effects of U.S. tax and "
        "spending proposals. Powered by IRS data, FRED, and CBO methodology. "
        f"Companion to the [Public Economics textbook]({TEXTBOOK_HOME})."
    )

    top_tabs = st_module.tabs([
        "📊 Calculator",
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

    with top_tabs[1]:
        _render_generational(st_module=st_module, deps=deps)
        render_footer(st_module=st_module)

    with top_tabs[2]:
        _render_state(st_module=st_module, deps=deps)
        render_footer(st_module=st_module)

    with top_tabs[3]:
        from .tabs.bill_tracker import render_bill_tracker_tab
        render_bill_tracker_tab(st_module=st_module)
        render_footer(st_module=st_module)

    with top_tabs[4]:
        deps.render_methodology_tab(st_module=st_module)
        render_footer(st_module=st_module)


def _render_calculator(
    st_module: Any,
    deps: Any,
    model_available: bool,
    app_root: Path,
) -> None:
    """Render the Calculator tab: sidebar inputs + results tabs."""
    # ── Sidebar ──────────────────────────────────────────────────────────
    with st_module.sidebar:
        st_module.header("Policy Configuration")

        # 1. Policy inputs (no Calculate button yet)
        calc_context = render_sidebar_inputs(st_module=st_module, deps=deps)

        # 2. Model settings expander (above Calculate button)
        settings = render_settings_tab(
            st_module=st_module,
            settings_tab=st_module.expander("⚙️ Model settings", expanded=False),
        )

        # 3. Calculate button
        st_module.markdown("---")
        calculate = st_module.button(
            "Calculate Impact",
            type="primary",
            use_container_width=True,
        )
        calc_context["calculate"] = calculate

        # 4. Data Status (bottom of sidebar — infrastructure, not decision-relevant)
        render_data_status(st_module=st_module, deps=deps)

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

    state_options = [f"{code} — {STATE_NAMES[code]}" for code in SUPPORTED_STATES]
    state_selection = st_module.selectbox(
        "State",
        state_options,
        key="top_level_state_select",
        help="Select a state for combined federal + state analysis.",
    )
    selected_state = state_selection.split(" — ")[0].strip() if state_selection else "CA"

    result_data = st_module.session_state.get("results")
    run_id = st_module.session_state.get("results_run_id") or st_module.session_state.get("last_run_id")
    deps.render_state_analysis_tab(
        st_module=st_module,
        state=selected_state,
        result_data=result_data,
        run_id=run_id,
    )
