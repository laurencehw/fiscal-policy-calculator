"""
Tab wiring and render orchestration helpers.
"""

from __future__ import annotations

from typing import Any


def build_main_tabs(st_module: Any, mode: str) -> dict[str, Any]:
    """
    Create main result tabs layout and return named tab references.
    """
    single_policy = mode == "📊 Single Policy"

    tab_labels = ["📊 Summary", "📈 Analysis", "🛠️ Tools"]
    ordered = tab_labels if single_policy else ["🛠️ Tools", "📊 Summary", "📈 Analysis"]
    tabs = st_module.tabs(ordered)
    tab_map = dict(zip(ordered, tabs, strict=False))

    return {
        "tab_summary": tab_map["📊 Summary"],
        "tab_analysis": tab_map["📈 Analysis"],
        "tab_tools": tab_map["🛠️ Tools"],
    }


def render_result_tabs(
    st_module: Any,
    deps: Any,
    tabs: dict[str, Any],
    settings: dict[str, Any],
    model_available: bool,
    is_spending: bool,
    mode: str,
) -> None:
    """
    Render post-calculation tabs (results, analysis, tools, reference).
    """
    single_policy = mode == "📊 Single Policy"
    current_run_id = getattr(st_module.session_state, "current_run_id", None)
    results_run_id = getattr(st_module.session_state, "results_run_id", None) or getattr(
        st_module.session_state, "last_run_id", None
    )
    is_stale = bool(results_run_id and current_run_id and results_run_id != current_run_id)

    with tabs["tab_tools"]:
        if mode == "🔀 Compare Policies":
            deps.render_policy_comparison_tab(
                st_module=st_module,
                is_spending=False,
                preset_policies=deps.PRESET_POLICIES,
                tax_policy_cls=deps.TaxPolicy,
                policy_type_income_tax=deps.PolicyType.INCOME_TAX,
                fiscal_policy_scorer_cls=deps.FiscalPolicyScorer,
                data_year=settings["data_year"],
                use_real_data=settings["use_real_data"],
                dynamic_scoring=settings["dynamic_scoring"],
            )
        elif mode == "📦 Policy Packages":
            deps.render_policy_package_tab(
                st_module=st_module,
                preset_policies=deps.PRESET_POLICIES,
                preset_packages=deps.PRESET_POLICY_PACKAGES,
                cbo_score_map=deps.CBO_SCORE_MAP,
                create_policy_from_preset=deps.create_policy_from_preset,
                fiscal_policy_scorer_cls=deps.FiscalPolicyScorer,
            )
        else:
            st_module.info("Select a mode in the sidebar to access comparison and packages.")

        with st_module.expander("ℹ️ Methodology", expanded=False):
            deps.render_methodology_tab(st_module=st_module)

    if not single_policy:
        with tabs["tab_summary"]:
            st_module.info("Use **📊 Single Policy** mode to view Summary and Analysis.")
        with tabs["tab_analysis"]:
            st_module.info("Use **📊 Single Policy** mode to view Summary and Analysis.")
        return

    if not st_module.session_state.results:
        with tabs["tab_summary"]:
            st_module.markdown("### Welcome to the Fiscal Policy Calculator")
            st_module.markdown(
                "Select a tax or spending proposal in the sidebar and click "
                "**Calculate Impact** to see its 10-year budgetary effect.\n\n"
                "**Quick examples to try:**"
            )
            col_a, col_b, col_c = st_module.columns(3)
            with col_a:
                st_module.markdown(
                    "**TCJA Extension**  \n"
                    "Extend all Tax Cuts and Jobs Act provisions  \n"
                    "*CBO estimate: +$4.6T*"
                )
            with col_b:
                st_module.markdown(
                    "**Biden Corporate 28%**  \n"
                    "Raise corporate rate from 21% to 28%  \n"
                    "*CBO estimate: -$1.35T*"
                )
            with col_c:
                st_module.markdown(
                    "**SS Donut Hole**  \n"
                    "Apply SS tax above $250K  \n"
                    "*CBO estimate: -$2.7T*"
                )
            st_module.markdown("---")
            st_module.caption(
                "This calculator uses CBO methodology with IRS Statistics of Income data. "
                "25+ policies validated within 15% of official CBO/JCT scores."
            )
        with tabs["tab_analysis"]:
            st_module.info("Run a calculation to unlock analysis views (distribution, dynamic scoring, long-run growth).")
        return

    result_data = st_module.session_state.results
    policy = result_data.get("policy")

    with tabs["tab_summary"]:
        if is_stale:
            st_module.warning("Inputs changed since the last run. Click **🚀 Calculate Impact** to refresh results.")
        deps.render_results_summary_tab(
            st_module=st_module,
            result_data=result_data,
            cbo_score_map=deps.CBO_SCORE_MAP,
        )

    with tabs["tab_analysis"]:
        if is_stale:
            st_module.warning("Inputs changed since the last run. Click **🚀 Calculate Impact** to refresh results.")
        view = st_module.radio(
            "Analysis view",
            options=["👥 Distribution", "🌍 Dynamic Scoring", "⏳ Long-Run Growth", "📋 Details"],
            horizontal=True,
            label_visibility="collapsed",
        )

        if view == "👥 Distribution":
            deps.render_distribution_tab(
                st_module=st_module,
                model_available=model_available,
                policy=policy,
                distribution_engine_cls=deps.DistributionalEngine,
                income_group_type_cls=deps.IncomeGroupType,
                format_distribution_table_fn=deps.format_distribution_table,
                winners_losers_summary_fn=deps.generate_winners_losers_summary,
                run_id=results_run_id,
            )
        elif view == "🌍 Dynamic Scoring":
            deps.render_dynamic_scoring_tab(
                st_module=st_module,
                dynamic_scoring=settings["dynamic_scoring"],
                result_data=result_data,
                macro_model_name=settings["macro_model"],
                macro_scenario_cls=deps.MacroScenario,
                frbus_adapter_lite_cls=deps.FRBUSAdapterLite,
                simple_multiplier_adapter_cls=deps.SimpleMultiplierAdapter,
                build_macro_scenario_fn=deps.build_macro_scenario,
                run_id=results_run_id,
            )
        elif view == "⏳ Long-Run Growth":
            deps.render_long_run_growth_tab(
                st_module=st_module,
                session_results=result_data,
                solow_growth_model_cls=deps.SolowGrowthModel,
                run_id=results_run_id,
            )
        else:
            deps.render_detailed_results_tab(st_module=st_module, result_data=result_data)


def render_footer(st_module: Any) -> None:
    """
    Render app footer with version and validation info.
    """
    st_module.markdown("---")
    st_module.caption(
        "**Fiscal Policy Impact Calculator** v1.0 · "
        "25 policies validated against CBO/JCT · "
        "302 unit tests · "
        "Data: IRS SOI 2022, FRED, CBO Feb 2024 · "
        "[Methodology](https://github.com/laurencehw/fiscal-policy-calculator/blob/main/docs/METHODOLOGY.md) · "
        "[Source code](https://github.com/laurencehw/fiscal-policy-calculator)"
    )
