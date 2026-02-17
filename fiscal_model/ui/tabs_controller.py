"""
Tab wiring and render orchestration helpers.
"""

from __future__ import annotations

from typing import Any


def build_nested_tabs(st_module: Any, main_tabs: Any) -> dict[str, Any]:
    """
    Create nested tab layout and return named tab references.
    """
    with main_tabs[0]:
        tab1, tab2 = st_module.tabs(["⚙️ Policy Input", "📝 Results Summary"])
    with main_tabs[1]:
        tab3, tab4, tab9 = st_module.tabs(["🌍 Dynamic Scoring", "👥 Distribution", "⏳ Long-Run Growth"])
    with main_tabs[2]:
        tab5, tab6 = st_module.tabs(["🔀 Compare Policies", "📦 Policy Packages"])
    with main_tabs[3]:
        tab7, tab8 = st_module.tabs(["📋 Detailed Results", "ℹ️ Methodology"])

    return {
        "tab1": tab1,
        "tab2": tab2,
        "tab3": tab3,
        "tab4": tab4,
        "tab5": tab5,
        "tab6": tab6,
        "tab7": tab7,
        "tab8": tab8,
        "tab9": tab9,
    }


def render_result_tabs(
    st_module: Any,
    deps: Any,
    tabs: dict[str, Any],
    settings: dict[str, Any],
    model_available: bool,
    is_spending: bool,
) -> None:
    """
    Render post-calculation tabs (results, analysis, tools, reference).
    """
    if st_module.session_state.results:
        result_data = st_module.session_state.results
        policy = result_data.get("policy")

        with tabs["tab2"]:
            deps.render_results_summary_tab(
                st_module=st_module,
                result_data=result_data,
                cbo_score_map=deps.CBO_SCORE_MAP,
            )
        with tabs["tab3"]:
            deps.render_dynamic_scoring_tab(
                st_module=st_module,
                dynamic_scoring=settings["dynamic_scoring"],
                result_data=st_module.session_state.results,
                macro_model_name=settings["macro_model"],
                macro_scenario_cls=deps.MacroScenario,
                frbus_adapter_lite_cls=deps.FRBUSAdapterLite,
                simple_multiplier_adapter_cls=deps.SimpleMultiplierAdapter,
                build_macro_scenario_fn=deps.build_macro_scenario,
            )
        with tabs["tab4"]:
            deps.render_distribution_tab(
                st_module=st_module,
                model_available=model_available,
                policy=policy,
                distribution_engine_cls=deps.DistributionalEngine,
                income_group_type_cls=deps.IncomeGroupType,
                format_distribution_table_fn=deps.format_distribution_table,
                winners_losers_summary_fn=deps.generate_winners_losers_summary,
            )
        with tabs["tab5"]:
            deps.render_policy_comparison_tab(
                st_module=st_module,
                is_spending=is_spending,
                preset_policies=deps.PRESET_POLICIES,
                tax_policy_cls=deps.TaxPolicy,
                policy_type_income_tax=deps.PolicyType.INCOME_TAX,
                fiscal_policy_scorer_cls=deps.FiscalPolicyScorer,
                data_year=settings["data_year"],
                use_real_data=settings["use_real_data"],
                dynamic_scoring=settings["dynamic_scoring"],
            )

    with tabs["tab6"]:
        deps.render_policy_package_tab(
            st_module=st_module,
            preset_policies=deps.PRESET_POLICIES,
            preset_packages=deps.PRESET_POLICY_PACKAGES,
            cbo_score_map=deps.CBO_SCORE_MAP,
            create_policy_from_preset=deps.create_policy_from_preset,
            fiscal_policy_scorer_cls=deps.FiscalPolicyScorer,
        )

    if st_module.session_state.results:
        result_data = st_module.session_state.results
        with tabs["tab7"]:
            deps.render_detailed_results_tab(st_module=st_module, result_data=result_data)
        with tabs["tab8"]:
            deps.render_methodology_tab(st_module=st_module)
        with tabs["tab9"]:
            deps.render_long_run_growth_tab(
                st_module=st_module,
                session_results=st_module.session_state.results,
                solow_growth_model_cls=deps.SolowGrowthModel,
            )


def render_footer(st_module: Any) -> None:
    """
    Render app footer.
    """
    st_module.markdown("---")
    st_module.caption(
        """
**Fiscal Policy Impact Calculator** | Built with Streamlit |
Data: IRS Statistics of Income, FRED, CBO |
Methodology: Congressional Budget Office scoring framework
"""
    )
