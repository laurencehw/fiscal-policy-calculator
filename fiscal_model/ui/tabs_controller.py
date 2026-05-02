"""
Tab wiring and render orchestration helpers.

Consolidated tab layout (5 tabs):
  1. Results & Details — summary metrics, year-by-year breakdown, export
  2. Distribution — impact by income group
  3. Economic Effects — dynamic scoring + long-run growth
  4. Scoring Models — compare static vs dynamic model estimates
  5. Compare Policies — side-by-side preset comparison
"""

from __future__ import annotations

import logging
from typing import Any

from fiscal_model.data.irs_soi import IRSSOIData
from fiscal_model.ui.helpers import TEXTBOOK_HOME

_logger = logging.getLogger(__name__)


def _render_tab_error(st_module: Any, tab_label: str, exc: Exception) -> None:
    """Render a user-safe tab failure without breaking sibling tabs."""
    _logger.exception("Failed to render %s tab", tab_label)
    st_module.error(
        f"{tab_label} could not be rendered. "
        "The rest of the calculator is still available."
    )
    st_module.caption(
        "If this persists, include the tab name and current policy in a bug report."
    )
    if hasattr(st_module, "expander") and hasattr(st_module, "code"):
        with st_module.expander("Technical details", expanded=False):
            st_module.code(f"{type(exc).__name__}: {exc}", language="text")


def _render_guarded_tab(st_module: Any, tab_label: str, render_fn: Any) -> None:
    """Execute a tab body behind a small error boundary."""
    try:
        render_fn()
    except Exception as exc:
        _render_tab_error(st_module, tab_label, exc)


def _latest_soi_year() -> int:
    """Return the most recent IRS SOI data year available."""
    try:
        years = IRSSOIData().get_data_years_available()
        return max(years) if years else 2022
    except Exception:
        return 2022


def build_main_tabs(
    st_module: Any,
    mode: str,
) -> dict[str, Any]:
    """
    Create main Calculator result tabs (5 tabs).
    Generational Analysis, State Analysis, Bill Tracker, and Methodology are
    top-level app tabs, not part of the Calculator tab set.
    """
    labels = [
        "📊 Results & Details",
        "👥 Distribution",
        "🌍 Economic Effects",
        "⚖️ Scoring Models",
        "🔀 Compare Policies",
    ]

    tabs = st_module.tabs(labels)
    tab_map = dict(zip(labels, tabs, strict=False))

    return {
        "tab_summary": tab_map["📊 Results & Details"],
        "tab_distribution": tab_map["👥 Distribution"],
        "tab_economic": tab_map["🌍 Economic Effects"],
        "tab_scoring": tab_map["⚖️ Scoring Models"],
        "tab_compare": tab_map["🔀 Compare Policies"],
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
    Render post-calculation tabs for the Calculator section.
    """
    current_run_id = getattr(st_module.session_state, "current_run_id", None)
    results_run_id = getattr(st_module.session_state, "results_run_id", None) or getattr(
        st_module.session_state, "last_run_id", None
    )
    is_stale = bool(results_run_id and current_run_id and results_run_id != current_run_id)

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
                    "**Biden 400K+ Tax**  \n"
                    "Restore 39.6% top rate  \n"
                    "*Treasury: raises ~$252B over 10 years*"
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
        with tabs["tab_compare"]:
            deps.render_side_by_side_tab(
                st_module=st_module,
                preset_policies=deps.PRESET_POLICIES,
                tax_policy_cls=deps.TaxPolicy,
                policy_type_income_tax=deps.PolicyType.INCOME_TAX,
                fiscal_policy_scorer_cls=deps.FiscalPolicyScorer,
                data_year=settings["data_year"],
                use_real_data=settings["use_real_data"],
                dynamic_scoring=settings["dynamic_scoring"],
            )
        return

    # ── Results with data ────────────────────────────────────────────────
    result_data = st_module.session_state.results
    policy = result_data.get("policy")

    # Tab 1: Results & Details (merged)
    with tabs["tab_summary"]:
        def _render_summary_body() -> None:
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

        _render_guarded_tab(st_module, "Results & Details", _render_summary_body)

    # Tab 2: Distribution
    with tabs["tab_distribution"]:
        def _render_distribution_body() -> None:
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

        _render_guarded_tab(st_module, "Distribution", _render_distribution_body)

    # Tab 3: Economic Effects (dynamic scoring + long-run growth)
    with tabs["tab_economic"]:
        def _render_economic_body() -> None:
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

        _render_guarded_tab(st_module, "Economic Effects", _render_economic_body)

    # Tab 4: Scoring Models
    with tabs["tab_scoring"]:
        def _render_scoring_body() -> None:
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

            st_module.markdown("---")
            with st_module.expander(
                "🔀 Multi-model pilot (CBO × TPC-Microsim × PWBM-OLG)",
                expanded=False,
            ):
                deps.render_multi_model_tab(
                    st_module=st_module,
                    is_spending=is_spending,
                    preset_policies=deps.PRESET_POLICIES,
                    tax_policy_cls=deps.TaxPolicy,
                    policy_type_income_tax=deps.PolicyType.INCOME_TAX,
                    fiscal_policy_scorer_cls=deps.FiscalPolicyScorer,
                    data_year=settings["data_year"],
                    use_real_data=settings["use_real_data"],
                )

        _render_guarded_tab(st_module, "Scoring Models", _render_scoring_body)

    # Tab 5: Side-by-Side Policy Comparison
    with tabs["tab_compare"]:
        def _render_compare_body() -> None:
            deps.render_side_by_side_tab(
                st_module=st_module,
                preset_policies=deps.PRESET_POLICIES,
                tax_policy_cls=deps.TaxPolicy,
                policy_type_income_tax=deps.PolicyType.INCOME_TAX,
                fiscal_policy_scorer_cls=deps.FiscalPolicyScorer,
                data_year=settings["data_year"],
                use_real_data=settings["use_real_data"],
                dynamic_scoring=settings["dynamic_scoring"],
            )

        _render_guarded_tab(st_module, "Compare Policies", _render_compare_body)


def render_footer(st_module: Any) -> None:
    """Render app footer with version and validation info."""
    st_module.markdown("---")
    st_module.caption(
        "**Fiscal Policy Impact Calculator** v1.0 · "
        "25 policies validated against CBO/JCT · "
        f"Data: IRS SOI {_latest_soi_year()}, FRED, CBO Feb 2026 · "
        "[Methodology](https://github.com/laurencehw/fiscal-policy-calculator"
        "/blob/main/docs/METHODOLOGY.md) · "
        f"[Textbook]({TEXTBOOK_HOME}) · "
        "[Source code](https://github.com/laurencehw/fiscal-policy-calculator)"
    )
