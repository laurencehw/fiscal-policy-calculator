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
from .settings_controller import render_settings_tab
from .tabs_controller import build_main_tabs, render_footer, render_result_tabs


def run_main_app(st_module: Any, deps: Any, model_available: bool, app_root: Path) -> None:
    """
    Render and orchestrate the full Streamlit app flow.
    """
    st_module.title("Fiscal Policy Impact Calculator")
    st_module.caption(
        "Estimate the budgetary and economic effects of tax and spending policies using real IRS and FRED data."
    )

    # Sidebar Inputs
    with st_module.sidebar:
        st_module.header("⚙️ Policy Configuration")
        calc_context = render_sidebar_inputs(st_module=st_module, deps=deps)

        st_module.markdown("---")
        settings = render_settings_tab(
            st_module=st_module,
            settings_tab=st_module.expander("⚙️ Global Settings"),
        )

    calc_context["run_id"] = compute_run_id(calc_context=calc_context, settings=settings)
    st_module.session_state.current_run_id = calc_context["run_id"]

    # Main Area Results
    tabs = build_main_tabs(st_module=st_module, mode=calc_context["mode"])
    
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
    render_footer(st_module=st_module)
