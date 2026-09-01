"""
Tab wiring and render orchestration helpers.

Calculator nested tab layout (6 tabs):
  1. Results & Details — summary metrics, year-by-year breakdown, export
  2. Distribution — impact by income group
  3. Economic Effects — dynamic scoring + long-run growth
  4. Scoring Models — model comparison + side-by-side presets
  5. Generational — OLG / generational accounting
  6. State — combined federal + state analysis
"""

from __future__ import annotations

import logging
from typing import Any

from fiscal_model.data.irs_soi import IRSSOIData
from fiscal_model.ui.helpers import TEXTBOOK_HOME, validated_policy_count

_logger = logging.getLogger(__name__)


def _benchmark_count_clause() -> str:
    """"N policies benchmarked against ..." — or the count-free wording.

    ``validated_policy_count()`` returns 0 when the scorecard could not be
    built. Printing "0 policies benchmarked" would be worse than saying
    nothing, and printing a hard-coded fallback — which is what this used to
    do — would be worse still: it asserted coverage at exactly the moment the
    thing that measures coverage had failed.
    """
    n = validated_policy_count()
    if not n:
        return "Policies are benchmarked against official CBO/JCT/Treasury scores — "
    return f"{n} policies benchmarked against official CBO/JCT/Treasury scores — "


def _footer_validation_clause() -> str:
    """Footer variant of :func:`_benchmark_count_clause`, separator included.

    Returns an empty string at a zero count, so the footer simply loses the
    clause rather than showing an empty one.
    """
    n = validated_policy_count()
    if not n:
        return ""
    return f"{n} policies validated against CBO/JCT · "

# Nested Calculator tab labels (order matters for build_main_tabs).
CALCULATOR_TAB_LABELS: tuple[str, ...] = (
    "📊 Results & Details",
    "👥 Distribution",
    "🌍 Economic Effects",
    "⚖️ Scoring Models",
    "🌐 Generational",
    "🗺️ State",
)

# Deep-view labels used by the shared result panel (``components/results.py``).
# The panel renders the headline, Key Metrics and exports itself, so the
# summary tab is replaced by a "Details" tab holding the charts, assumptions,
# comparison and sensitivity blocks.
CALCULATOR_DEEP_TAB_LABELS: tuple[str, ...] = (
    "👥 Distribution",
    "🌍 Economic Effects",
    "⚖️ Scoring Models",
    "🌐 Generational",
    "🗺️ State",
    "📋 Details",
)

_LABEL_TO_SLOT: dict[str, str] = {
    "📊 Results & Details": "tab_summary",
    "👥 Distribution": "tab_distribution",
    "🌍 Economic Effects": "tab_economic",
    "⚖️ Scoring Models": "tab_scoring",
    "🌐 Generational": "tab_generational",
    "🗺️ State": "tab_state",
    "📋 Details": "tab_details",
}


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
    *,
    include_summary: bool = True,
) -> dict[str, Any]:
    """
    Create the nested result tabs.

    ``include_summary=True`` (default, legacy layout) opens with
    "Results & Details". ``include_summary=False`` is the shared result panel:
    the headline lives above the tabs, so the summary slot becomes "Details".
    """
    del mode  # reserved for future mode-specific tab sets
    labels = list(CALCULATOR_TAB_LABELS if include_summary else CALCULATOR_DEEP_TAB_LABELS)

    tabs = st_module.tabs(labels)
    return {
        _LABEL_TO_SLOT[label]: tab
        for label, tab in zip(labels, tabs, strict=False)
    }


def _render_side_by_side_section(
    st_module: Any,
    deps: Any,
    settings: dict[str, Any],
) -> None:
    """Side-by-side preset comparison (formerly its own nested tab)."""
    st_module.subheader("Compare presets side-by-side")
    st_module.caption(
        "Score two preset proposals with the same settings and compare "
        "10-year deficit impact."
    )
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


def _session_get(session: Any, key: str, default: Any = None) -> Any:
    """Read a session key from dict-like or attribute-style session state."""
    if hasattr(session, "get"):
        return session.get(key, default)
    return getattr(session, key, default)


def _render_generational(st_module: Any, deps: Any) -> None:
    """Render Generational Analysis (Calculator nested tab)."""
    session = st_module.session_state
    result_data = _session_get(session, "results")
    run_id = _session_get(session, "results_run_id") or _session_get(
        session, "last_run_id"
    )
    deps.render_generational_analysis_tab(
        st_module=st_module,
        result_data=result_data,
        run_id=run_id,
    )


def _render_state(st_module: Any, deps: Any) -> None:
    """Render State Analysis with its own state selector (Calculator nested tab)."""
    from fiscal_model.models.state.database import STATE_NAMES, SUPPORTED_STATES

    state_selection = st_module.selectbox(
        "State",
        options=SUPPORTED_STATES,
        format_func=lambda code: f"{code} — {STATE_NAMES[code]}",
        key="calculator_state_select",
        help="Select a state for combined federal + state analysis.",
    )
    selected_state = state_selection if state_selection else "CA"

    session = st_module.session_state
    result_data = _session_get(session, "results")
    run_id = _session_get(session, "results_run_id") or _session_get(
        session, "last_run_id"
    )
    deps.render_state_analysis_tab(
        st_module=st_module,
        state=selected_state,
        result_data=result_data,
        run_id=run_id,
    )


def render_result_tabs(
    st_module: Any,
    deps: Any,
    tabs: dict[str, Any],
    settings: dict[str, Any],
    model_available: bool,
    is_spending: bool,
    mode: str,
    *,
    include_summary: bool = True,
    scored: Any = None,
) -> None:
    """
    Render post-calculation tabs.

    ``include_summary=False`` is the shared-result-panel layout: the headline,
    Key Metrics and exports are rendered above these tabs by
    ``components.results.render_results``, and the summary slot is replaced by
    a "Details" tab. ``scored`` is the run's single
    :class:`~components.results.ScoredResult`, threaded through so the tab
    bodies read the same numbers as the panel above them.
    """
    del mode
    current_run_id = getattr(st_module.session_state, "current_run_id", None)
    results_run_id = getattr(st_module.session_state, "results_run_id", None) or getattr(
        st_module.session_state, "last_run_id", None
    )
    is_stale = bool(results_run_id and current_run_id and results_run_id != current_run_id)

    # ── Onboarding state (no results yet) ────────────────────────────────
    if not st_module.session_state.results:
        with tabs.get("tab_summary") or tabs.get("tab_details"):
            st_module.markdown("### Welcome to the Fiscal Policy Calculator")
            st_module.markdown(
                "Choose a proposal above (or define your own on **Tailor**) and click "
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
                    "*Treasury: raises \\~$252B over 10 years*"
                )
            with col_c:
                st_module.markdown(
                    "**Infrastructure $100B/yr**  \n"
                    "Choose *Spending program* on **Tailor**  \n"
                    "*Model GDP effects with multipliers*"
                )
            st_module.markdown("---")
            st_module.caption(
                "This calculator uses CBO methodology with IRS Statistics of Income data. "
                f"{_benchmark_count_clause()}calibrated "
                "models reproduce official scores; uncalibrated predictions are directional (\\~±20%)."
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
                "estimate the same policy — or compare presets below without a prior run."
            )
            st_module.markdown("---")
            _render_side_by_side_section(
                st_module=st_module, deps=deps, settings=settings
            )
        with tabs["tab_generational"]:
            _render_guarded_tab(
                st_module,
                "Generational",
                lambda: _render_generational(st_module=st_module, deps=deps),
            )
        with tabs["tab_state"]:
            _render_guarded_tab(
                st_module,
                "State",
                lambda: _render_state(st_module=st_module, deps=deps),
            )
        return

    # ── Results with data ────────────────────────────────────────────────
    result_data = st_module.session_state.results
    policy = result_data.get("policy")

    # Tab 1: Results & Details (legacy layout) or Details (panel layout)
    if include_summary:
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
                        st_module=st_module, result_data=result_data, scored=scored
                    )

            _render_guarded_tab(st_module, "Results & Details", _render_summary_body)
    elif "tab_details" in tabs:
        with tabs["tab_details"]:
            def _render_details_body() -> None:
                from fiscal_model.ui.tabs.results_summary import (
                    ensure_summary,
                    render_details_block,
                )

                summary = ensure_summary(
                    result_data, scored, cbo_score_map=deps.CBO_SCORE_MAP
                )
                render_details_block(
                    st_module, summary, result_data, deps.CBO_SCORE_MAP
                )
                with st_module.expander("📋 Detailed Year-by-Year Breakdown", expanded=False):
                    deps.render_detailed_results_tab(
                        st_module=st_module, result_data=result_data, scored=scored
                    )

            _render_guarded_tab(st_module, "Details", _render_details_body)

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
                use_microsim=settings.get("use_microsim_distribution", True),
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

    # Tab 4: Scoring Models (+ multi-model pilot + side-by-side compare)
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
            st_module.subheader("Multi-model comparison (pilot)")
            st_module.caption(
                "Same policy through CBO-style and TPC-microsim backends. "
                "Disagreement is informative — not an official range. "
                "Exploratory tier: useful for robustness, not a validated estimate."
            )
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

            st_module.markdown("---")
            _render_side_by_side_section(
                st_module=st_module, deps=deps, settings=settings
            )

        _render_guarded_tab(st_module, "Scoring Models", _render_scoring_body)

    # Tab 5: Generational
    with tabs["tab_generational"]:
        _render_guarded_tab(
            st_module,
            "Generational",
            lambda: _render_generational(st_module=st_module, deps=deps),
        )

    # Tab 6: State
    with tabs["tab_state"]:
        _render_guarded_tab(
            st_module,
            "State",
            lambda: _render_state(st_module=st_module, deps=deps),
        )


def render_footer(st_module: Any) -> None:
    """Render app footer: credit, cross-links, version and data vintages.

    One ``st.caption`` line, so it stays theme-neutral (the caption colour is
    Streamlit's own muted ink, which the dark-mode overlay in
    ``components/chrome.py`` already repaints).

    ``About`` and ``Methodology`` are plain ``/about`` and ``/methodology``
    links rather than ``st.page_link`` widgets: a widget is its own block
    element and would break the single line. ``components.chrome.page_link``
    is the widget-shaped route, used inside page bodies.
    """
    st_module.markdown("---")
    st_module.caption(
        "Built by Laurence Wilse-Samson · "
        "[About](/about) · "
        "[GitHub](https://github.com/laurencehw/fiscal-policy-calculator) · "
        "[Methodology](/methodology) · "
        f"[Textbook]({TEXTBOOK_HOME}) · "
        f"{_footer_validation_clause()}"
        f"Data: IRS SOI {_latest_soi_year()}, FRED, CBO Feb 2026"
    )
