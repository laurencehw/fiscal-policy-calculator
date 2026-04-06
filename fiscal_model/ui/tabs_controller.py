"""
Tab wiring and render orchestration helpers.

Consolidated tab layout (4 tabs):
  1. Results & Details — summary metrics, year-by-year breakdown, export
  2. Distribution — impact by income group
  3. Economic Effects — dynamic scoring + long-run growth
  4. Scoring Models — compare static vs dynamic model estimates
"""

from __future__ import annotations

from typing import Any

from fiscal_model.ui.helpers import TEXTBOOK_HOME


def build_main_tabs(
    st_module: Any,
    mode: str,
) -> dict[str, Any]:
    """
    Create main Calculator result tabs (4 tabs).
    Generational Analysis, State Analysis, Bill Tracker, and Methodology are
    top-level app tabs, not part of the Calculator tab set.

    In Compare Policies or Policy Packages mode, a 5th tab is appended for
    that workflow.
    """
    labels = [
        "📊 Results & Details",
        "👥 Distribution",
        "🌍 Economic Effects",
        "⚖️ Scoring Models",
    ]

    # Add workflow-specific tab when not in single-policy mode
    if mode == "🔀 Compare Policies":
        labels.append("🔀 Compare Policies")
    elif mode == "📦 Policy Packages":
        labels.append("📦 Package Builder")

    tabs = st_module.tabs(labels)
    tab_map = dict(zip(labels, tabs, strict=False))

    result = {
        "tab_summary": tab_map["📊 Results & Details"],
        "tab_distribution": tab_map["👥 Distribution"],
        "tab_economic": tab_map["🌍 Economic Effects"],
        "tab_scoring": tab_map["⚖️ Scoring Models"],
    }

    if "🔀 Compare Policies" in tab_map:
        result["tab_comparison"] = tab_map["🔀 Compare Policies"]
    if "📦 Package Builder" in tab_map:
        result["tab_packages"] = tab_map["📦 Package Builder"]

    return result


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
    Render post-calculation tabs for the Calculator section.
    """
    single_policy = mode == "📊 Single Policy"
    current_run_id = getattr(st_module.session_state, "current_run_id", None)
    results_run_id = getattr(st_module.session_state, "results_run_id", None) or getattr(
        st_module.session_state, "last_run_id", None
    )
    is_stale = bool(results_run_id and current_run_id and results_run_id != current_run_id)

    # ── Non-single-policy modes ─────────────────────────────────────────
    if not single_policy:
        with tabs["tab_summary"]:
            st_module.info("Switch to **Single Policy** mode to score an individual proposal.")
        with tabs["tab_distribution"]:
            st_module.info("Switch to **Single Policy** mode to see distributional analysis.")
        with tabs["tab_economic"]:
            st_module.info("Switch to **Single Policy** mode to see economic effects.")
        with tabs["tab_scoring"]:
            st_module.info("Switch to **Single Policy** mode to compare scoring models.")

        if "tab_comparison" in tabs:
            with tabs["tab_comparison"]:
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
                    "Extend all 2017 tax cut provisions  \n"
                    "*CBO: +$4.6T over 10 years*"
                )
            with col_b:
                st_module.markdown(
                    "**Biden $400K+ Tax**  \n"
                    "Restore 39.6% top rate  \n"
                    "*Treasury: −$252B over 10 years*"
                )
            with col_c:
                st_module.markdown(
                    "**Infrastructure $100B/yr**  \n"
                    "Select *Spending program* in sidebar  \n"
                    "*Model GDP effects with multipliers*"
                )
            st_module.markdown("---")
            st_module.caption(
                "This calculator uses CBO methodology with IRS Statistics of Income data. "
                "25+ policies validated within 15% of official CBO/JCT scores."
            )
        with tabs["tab_distribution"]:
            st_module.info(
                "Run a calculation to see how the policy affects different income groups."
            )
        with tabs["tab_economic"]:
            st_module.info(
                "Run a calculation to see GDP, employment, and long-run growth effects."
            )
        with tabs["tab_scoring"]:
            st_module.info(
                "Run a calculation to compare how different scoring models "
                "estimate the same policy."
            )
        return

    # ── Results with data ────────────────────────────────────────────────
    result_data = st_module.session_state.results
    policy = result_data.get("policy")

    # Tab 1: Results & Details (merged)
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
        # Detailed breakdown in an expander within the same tab
        with st_module.expander("📋 Detailed Year-by-Year Breakdown", expanded=False):
            deps.render_detailed_results_tab(
                st_module=st_module, result_data=result_data
            )

    # Tab 2: Distribution
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
            use_microsim=settings.get("use_microsim_distribution", False),
        )

    # Tab 3: Economic Effects (dynamic scoring + long-run growth)
    with tabs["tab_economic"]:
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
        # Long-run growth section within the same tab
        st_module.markdown("---")
        deps.render_long_run_growth_tab(
            st_module=st_module,
            session_results=result_data,
            solow_growth_model_cls=deps.SolowGrowthModel,
            run_id=results_run_id,
        )

    # Tab 4: Scoring Models
    with tabs["tab_scoring"]:
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


def render_footer(st_module: Any) -> None:
    """Render app footer with version and validation info."""
    st_module.markdown("---")
    st_module.caption(
        "**Fiscal Policy Impact Calculator** v1.0 · "
        "25 policies validated against CBO/JCT · "
        "Data: IRS SOI 2022, FRED, CBO Feb 2026 · "
        "[Methodology](https://github.com/laurencehw/fiscal-policy-calculator"
        "/blob/main/docs/METHODOLOGY.md) · "
        f"[Textbook]({TEXTBOOK_HOME}) · "
        "[Source code](https://github.com/laurencehw/fiscal-policy-calculator)"
    )
