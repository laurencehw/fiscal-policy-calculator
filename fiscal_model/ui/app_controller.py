"""
Top-level Streamlit app orchestration.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .calculation_controller import (
    ensure_results_state,
    execute_calculation_if_requested,
    render_policy_input_tab,
)
from .settings_controller import render_settings_tab
from .tabs_controller import build_nested_tabs, render_footer, render_result_tabs


def run_main_app(st_module: Any, deps: Any, model_available: bool, app_root: Path) -> None:
    """
    Render and orchestrate the full Streamlit app flow.
    """
    st_module.markdown(
        '<div class="main-header">📊 Fiscal Policy Impact Calculator</div>',
        unsafe_allow_html=True,
    )
    st_module.markdown(
        '<div class="sub-header">Estimate the budgetary and economic effects of tax and spending policies using real IRS and FRED data</div>',
        unsafe_allow_html=True,
    )

    main_tabs = st_module.tabs(["📊 Calculator", "📈 Economic Analysis", "🛠️ Tools", "ℹ️ Reference", "⚙️ Settings"])
    settings = render_settings_tab(st_module=st_module, settings_tab=main_tabs[4])
    tabs = build_nested_tabs(st_module=st_module, main_tabs=main_tabs)

    calc_context = render_policy_input_tab(st_module=st_module, tab1=tabs["tab1"], deps=deps)
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
    )
    render_footer(st_module=st_module)
