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
from .helpers import TEXTBOOK_HOME
from .settings_controller import render_settings_tab
from .tabs_controller import build_main_tabs, render_footer, render_result_tabs


def render_data_status(st_module: Any, deps: Any) -> None:
    """
    Render a data status indicator in the sidebar showing:
    - CBO baseline vintage (green/yellow/red)
    - FRED data status (live/cached/fallback)
    - Last update timestamp
    - Details expander
    """
    try:
        # Get FRED data status if available
        fred_status = "Unknown"
        fred_source = None
        last_updated = None
        cache_age_days = None

        # Try to access FRED data module if available
        try:
            from fiscal_model.data.fred_data import FREDData
            fred_instance = FREDData()
            data_status = fred_instance.data_status
            fred_source = data_status.get("source", "unknown")
            last_updated = data_status.get("last_updated")
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

        # Get baseline vintage
        try:
            from fiscal_model.baseline import BaselineVintage
            baseline_vintage = BaselineVintage.CBO_FEB_2026.value
            baseline_display = "CBO Feb 2026"
            vintage_color = "green"
        except Exception:
            baseline_display = "Unknown"
            vintage_color = "gray"

        # Render the status section
        st_module.markdown("---")
        st_module.markdown("**📊 Data Status**")

        # Color-coded vintage
        if vintage_color == "green":
            st_module.markdown(f"🟢 **Baseline:** {baseline_display}")
        elif vintage_color == "yellow":
            st_module.markdown(f"🟡 **Baseline:** {baseline_display}")
        else:
            st_module.markdown(f"⚪ **Baseline:** {baseline_display}")

        # FRED status
        st_module.markdown(f"📡 **Data:** {fred_status}")

        # Details expander
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
        # Silently fail if there's any issue with status rendering
        pass


def render_quick_start(st_module: Any) -> None:
    """
    Render a dismissible quick-start guide at the top of the main area.
    Uses session state to track dismissal.
    """
    if "quick_start_dismissed" not in st_module.session_state:
        st_module.session_state.quick_start_dismissed = False

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
    """
    st_module.title("Fiscal Policy Impact Calculator")
    st_module.caption(
        "Estimate the 10-year budgetary and economic effects of U.S. tax and "
        "spending proposals. Powered by IRS data, FRED, and CBO methodology. "
        f"Companion to the [Public Economics textbook]({TEXTBOOK_HOME})."
    )

    # Sidebar
    with st_module.sidebar:
        st_module.header("Policy Configuration")
        render_data_status(st_module=st_module, deps=deps)
        calc_context = render_sidebar_inputs(st_module=st_module, deps=deps)

        st_module.markdown("---")
        settings = render_settings_tab(
            st_module=st_module,
            settings_tab=st_module.expander("Model settings", expanded=False),
        )

    calc_context["run_id"] = compute_run_id(calc_context=calc_context, settings=settings)
    st_module.session_state.current_run_id = calc_context["run_id"]

    # Main area
    render_quick_start(st_module=st_module)
    state_mode = settings.get("state_mode", False)
    selected_state = settings.get("selected_state", "CA")
    tabs = build_main_tabs(
        st_module=st_module,
        mode=calc_context["mode"],
        state_mode=state_mode,
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
        state_mode=state_mode,
        selected_state=selected_state,
    )

    render_footer(st_module=st_module)
