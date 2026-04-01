"""
Tab wiring and render orchestration helpers.
"""

from __future__ import annotations

from typing import Any

from fiscal_model.ui.helpers import TEXTBOOK_HOME

_ANALYSIS_CONTEXT = {
    "Distribution": "How does this policy affect different income groups?",
    "Dynamic Scoring": "GDP and employment effects using FRB/US-calibrated multipliers.",
    "Long-Run Growth": "Long-run growth projections using a Solow framework.",
    "Details": "Year-by-year breakdown of all scoring components.",
}


def build_main_tabs(st_module: Any, mode: str) -> dict[str, Any]:
    """
    Create main result tabs layout with progressive disclosure.
    Primary tabs are always visible; advanced tabs are in an expander.
    """
    # Primary tabs (always visible)
    primary_labels = ["📊 Results Summary", "👥 Distribution", "🌍 Dynamic Scoring", "📋 Detailed Results"]
    primary_tabs = st_module.tabs(primary_labels)
    tab_map = dict(zip(primary_labels, primary_tabs, strict=False))

    # Create mapping for primary tabs with icons
    primary_map = {
        "tab_summary": tab_map["📊 Results Summary"],
        "tab_distribution": tab_map["👥 Distribution"],
        "tab_dynamic": tab_map["🌍 Dynamic Scoring"],
        "tab_details": tab_map["📋 Detailed Results"],
    }

    # Advanced section (in expander)
    st_module.markdown("---")
    with st_module.expander("🔬 Advanced Analysis", expanded=False):
        advanced_labels = ["📈 Long-Run Growth", "⚖️ Policy Comparison", "📦 Package Builder", "📖 Methodology"]
        advanced_tabs = st_module.tabs(advanced_labels)
        advanced_map = dict(zip(advanced_labels, advanced_tabs, strict=False))

        primary_map.update({
            "tab_long_run": advanced_map["📈 Long-Run Growth"],
            "tab_comparison": advanced_map["⚖️ Policy Comparison"],
            "tab_packages": advanced_map["📦 Package Builder"],
            "tab_methodology": advanced_map["📖 Methodology"],
        })

    return primary_map


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
    Render post-calculation tabs with progressive disclosure.
    Primary tabs (Results, Distribution, Dynamic, Details) are always visible.
    Advanced tabs (Long-Run, Comparison, Packages, Methodology) are in an expander.
    """
    single_policy = mode == "📊 Single Policy"
    current_run_id = getattr(st_module.session_state, "current_run_id", None)
    results_run_id = getattr(st_module.session_state, "results_run_id", None) or getattr(
        st_module.session_state, "last_run_id", None
    )
    is_stale = bool(results_run_id and current_run_id and results_run_id != current_run_id)

    # ── Results and Analysis for non-single-policy modes ─────────────────
    if not single_policy:
        with tabs["tab_summary"]:
            st_module.info("Use **Single Policy** mode to view Results and Analysis.")
        with tabs["tab_distribution"]:
            st_module.info("Use **Single Policy** mode to view Results and Analysis.")
        with tabs["tab_dynamic"]:
            st_module.info("Use **Single Policy** mode to view Results and Analysis.")
        with tabs["tab_details"]:
            st_module.info("Use **Single Policy** mode to view Results and Analysis.")
        # Handle comparison/packages in advanced section if applicable
        if "tab_comparison" in tabs:
            with tabs["tab_comparison"]:
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
        if "tab_packages" in tabs:
            with tabs["tab_packages"]:
                if mode == "📦 Policy Packages":
                    deps.render_policy_package_tab(
                        st_module=st_module,
                        preset_policies=deps.PRESET_POLICIES,
                        preset_packages=deps.PRESET_POLICY_PACKAGES,
                        cbo_score_map=deps.CBO_SCORE_MAP,
                        create_policy_from_preset=deps.create_policy_from_preset,
                        fiscal_policy_scorer_cls=deps.FiscalPolicyScorer,
                    )
        return

    # ── Onboarding state (no results yet) ────────────────────────────────
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
        with tabs["tab_distribution"]:
            st_module.info(
                "Run a calculation to unlock distribution analysis "
                "(showing impacts by income group)."
            )
        with tabs["tab_dynamic"]:
            st_module.info(
                "Run a calculation to unlock dynamic scoring "
                "(GDP and employment effects)."
            )
        with tabs["tab_details"]:
            st_module.info(
                "Run a calculation to see detailed year-by-year results."
            )
        # Populate advanced tabs
        if "tab_long_run" in tabs:
            with tabs["tab_long_run"]:
                st_module.info(
                    "Run a calculation to unlock long-run growth projections."
                )
        if "tab_comparison" in tabs:
            with tabs["tab_comparison"]:
                st_module.info(
                    "Run a calculation, or switch to Compare Policies mode to compare multiple proposals."
                )
        if "tab_packages" in tabs:
            with tabs["tab_packages"]:
                st_module.info(
                    "Run a calculation, or switch to Policy Packages mode to build combined proposals."
                )
        if "tab_methodology" in tabs:
            with tabs["tab_methodology"]:
                deps.render_methodology_tab(st_module=st_module)
        return

    # ── Results with data ────────────────────────────────────────────────
    result_data = st_module.session_state.results
    policy = result_data.get("policy")

    with tabs["tab_summary"]:
        if is_stale:
            st_module.warning(
                "Inputs changed since the last run. "
                "Click **Calculate Impact** to refresh results."
            )
        deps.render_results_summary_tab(
            st_module=st_module,
            result_data=result_data,
            cbo_score_map=deps.CBO_SCORE_MAP,
        )

    with tabs["tab_distribution"]:
        if is_stale:
            st_module.warning(
                "Inputs changed since the last run. "
                "Click **Calculate Impact** to refresh results."
            )
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

    with tabs["tab_dynamic"]:
        if is_stale:
            st_module.warning(
                "Inputs changed since the last run. "
                "Click **Calculate Impact** to refresh results."
            )
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

    with tabs["tab_details"]:
        if is_stale:
            st_module.warning(
                "Inputs changed since the last run. "
                "Click **Calculate Impact** to refresh results."
            )
        deps.render_detailed_results_tab(
            st_module=st_module, result_data=result_data
        )

    # ── Advanced tabs (inside expander) ──────────────────────────────────
    if "tab_long_run" in tabs:
        with tabs["tab_long_run"]:
            if is_stale:
                st_module.warning(
                    "Inputs changed since the last run. "
                    "Click **Calculate Impact** to refresh results."
                )
            deps.render_long_run_growth_tab(
                st_module=st_module,
                session_results=result_data,
                solow_growth_model_cls=deps.SolowGrowthModel,
                run_id=results_run_id,
            )

    if "tab_comparison" in tabs:
        with tabs["tab_comparison"]:
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
            else:
                st_module.subheader("Policy Comparison")
                st_module.markdown(
                    "Switch to **Compare Policies** mode in the sidebar to compare "
                    "multiple policy proposals side-by-side."
                )

    if "tab_packages" in tabs:
        with tabs["tab_packages"]:
            if mode == "📦 Policy Packages":
                deps.render_policy_package_tab(
                    st_module=st_module,
                    preset_policies=deps.PRESET_POLICIES,
                    preset_packages=deps.PRESET_POLICY_PACKAGES,
                    cbo_score_map=deps.CBO_SCORE_MAP,
                    create_policy_from_preset=deps.create_policy_from_preset,
                    fiscal_policy_scorer_cls=deps.FiscalPolicyScorer,
                )
            else:
                st_module.subheader("Policy Package Builder")
                st_module.markdown(
                    "Switch to **Policy Packages** mode in the sidebar to combine "
                    "multiple policies into a comprehensive plan."
                )

    if "tab_methodology" in tabs:
        with tabs["tab_methodology"]:
            deps.render_methodology_tab(st_module=st_module)


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
        "[Methodology](https://github.com/laurencehw/fiscal-policy-calculator"
        "/blob/main/docs/METHODOLOGY.md) · "
        f"[Textbook]({TEXTBOOK_HOME}) · "
        "[Source code](https://github.com/laurencehw/fiscal-policy-calculator)"
    )
