"""
Dynamic scoring tab renderer — and the app's single source of truth for
macroeconomic feedback.

Phase 4 of the redesign resolved the three-way disagreement documented in
``planning/redesign/NOTES.md`` §4.4 with one rule:

* **The headline is always the conventional score** — ``static_deficit +
  behavioral``, positive = increases the deficit. It never moves when the
  dynamic-scoring toggle is flipped, so a calibrated preset keeps matching its
  official benchmark either way.
* **Dynamic scoring adds a clearly-labeled "Dynamic view"**, never a different
  headline: revenue feedback, debt service, and the dynamic total.
* **One feedback number, one model.** Every surface that prints revenue
  feedback (Results Key Metrics, the Economic Effects tab, Copy Summary, CSV)
  reads :func:`compute_dynamic_view`, which is driven by the macro adapter the
  Economic Effects tab already used (FRB/US-Lite or Simple Multiplier, per the
  model setting). The engine's *internal* ``EconomicModel`` feedback
  (``ScoringResult.dynamic_effects.revenue_feedback``) is no longer displayed
  anywhere; it stays on the result object for the API and validation suites.
* **Debt service is included in both places or neither** — here, in both.
  CBO's dynamic analyses net the interest cost of the added deficit against
  growth feedback, and a "dynamic total" that ignores it overstates the offset.
  The old headline had no interest term, which is exactly how the same policy
  ended up with two different dynamic totals.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Any

import numpy as np
import plotly.graph_objects as go

from fiscal_model.ui.a11y import (
    ChartDescription,
    format_currency_rows,
    render_accessible_chart,
)
from fiscal_model.ui.charts import apply_base_layout, horizontal_legend

#: Value of the "Macro model" setting that selects the simple Keynesian path.
SIMPLE_MULTIPLIER_SETTING = "Simple Multiplier"
#: Display names for the two adapters (used in captions, exports and metadata).
FRBUS_LITE_MODEL_LABEL = "FRB/US-Lite (Federal Reserve calibrated)"
SIMPLE_MULTIPLIER_MODEL_LABEL = "Simple Keynesian Multiplier"


@dataclass(frozen=True)
class DynamicView:
    """The dynamic decomposition of one scored policy.

    Every field is in the deficit convention: **positive increases the
    deficit**. ``feedback`` is subtracted (extra revenue shrinks the deficit)
    and ``debt_service`` is added, so::

        dynamic_total = conventional - feedback + debt_service
    """

    model_name: str
    conventional: float
    feedback: float
    debt_service: float
    dynamic_total: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "conventional": self.conventional,
            "feedback": self.feedback,
            "debt_service": self.debt_service,
            "dynamic_total": self.dynamic_total,
        }


def conventional_total(result: Any) -> float:
    """Return the conventional (static + behavioral) 10-year deficit effect.

    This is the headline number on every surface, in every mode. It is
    deliberately *not* ``result.final_deficit_effect``: with dynamic scoring on,
    the engine subtracts its internal feedback there, which pushed calibrated
    presets off their benchmark purely because a toggle was flipped.
    """
    return float(
        (np.asarray(result.static_deficit_effect) + np.asarray(result.behavioral_offset)).sum()
    )


def resolve_macro_adapter(
    macro_model_name: str | None,
    frbus_adapter_lite_cls: Any,
    simple_multiplier_adapter_cls: Any,
) -> tuple[Any, str]:
    """Instantiate the macro adapter named by the model setting.

    Shared by the calculation pipeline and the Economic Effects tab so both
    always run the *same* model — the precondition for the two surfaces
    printing the same feedback number.
    """
    if macro_model_name == SIMPLE_MULTIPLIER_SETTING:
        return simple_multiplier_adapter_cls(), SIMPLE_MULTIPLIER_MODEL_LABEL
    return frbus_adapter_lite_cls(), FRBUS_LITE_MODEL_LABEL


def compute_dynamic_view(result: Any, macro_result: Any, model_name: str) -> DynamicView:
    """Build the one dynamic decomposition every surface renders."""
    conventional = conventional_total(result)
    feedback = float(macro_result.cumulative_revenue_feedback)
    debt_service = float(np.sum(macro_result.interest_cost_billions))
    return DynamicView(
        model_name=model_name,
        conventional=conventional,
        feedback=feedback,
        debt_service=debt_service,
        dynamic_total=conventional - feedback + debt_service,
    )


def render_dynamic_scoring_tab(
    st_module: Any,
    dynamic_scoring: bool,
    result_data: Any,
    macro_model_name: str | None,
    macro_scenario_cls: Any,
    frbus_adapter_lite_cls: Any,
    simple_multiplier_adapter_cls: Any,
    build_macro_scenario_fn: Any,
    run_id: str | None = None,
) -> None:
    """
    Render dynamic scoring analysis tab content.
    """
    st_module.header("🌍 Dynamic Scoring")

    if not dynamic_scoring:
        st_module.markdown(
            """
            <div class="info-box">
            💡 <strong>Dynamic scoring is disabled.</strong> Enable it in the ⚙ settings menu to see macroeconomic effects
            (GDP impact, employment changes, interest rates, and revenue feedback).
            </div>
            """,
            unsafe_allow_html=True,
        )

        st_module.info(
            """
            **What is Dynamic Scoring?**

            Dynamic scoring estimates how fiscal policies affect the broader economy, beyond direct budget effects:

            - **GDP Effects**: Tax cuts can stimulate growth; tax increases can slow it
            - **Employment**: Policies affect job creation and labor force participation
            - **Interest Rates**: Deficits can raise rates through crowding out
            - **Revenue Feedback**: GDP growth generates additional tax revenue

            **Enable dynamic scoring** in the settings menu to see these effects for your policy.
            """
        )
        return

    st_module.markdown(
        """
        <div class="info-box">
        💡 <strong>Macroeconomic Feedback:</strong> These estimates show how your policy affects
        GDP, employment, and generates revenue feedback through economic growth.
        </div>
        """,
        unsafe_allow_html=True,
    )

    if result_data is None:
        st_module.info("👆 Calculate a policy first to see dynamic scoring results")
        return

    policy = result_data["policy"]
    result = result_data["result"]

    try:
        is_spending_policy = result_data.get("is_spending", False)
        scenario = build_macro_scenario_fn(
            policy=policy,
            result=result,
            is_spending_policy=is_spending_policy,
            macro_scenario_cls=macro_scenario_cls,
        )

        adapter, model_name = resolve_macro_adapter(
            macro_model_name, frbus_adapter_lite_cls, simple_multiplier_adapter_cls
        )

        cache_key = f"macro:{run_id}:{macro_model_name}" if run_id else None
        macro_result = st_module.session_state.get(cache_key) if cache_key else None
        if macro_result is None:
            with st_module.spinner("Running macroeconomic model..."):
                macro_result = adapter.run(scenario)
            if cache_key:
                st_module.session_state[cache_key] = macro_result
        st_module.caption(f"Model: **{model_name}**")
        st_module.subheader("10-Year Macroeconomic Effects")

        col1, col2, col3, col4 = st_module.columns(4)

        with col1:
            gdp_effect = macro_result.cumulative_gdp_effect
            st_module.metric(
                "Cumulative GDP Effect",
                f"{gdp_effect:.2f}%-years",
                delta="Growth boost" if gdp_effect > 0 else "Growth drag",
                delta_color="normal" if gdp_effect > 0 else "inverse",
            )

        with col2:
            revenue_fb = macro_result.cumulative_revenue_feedback
            st_module.metric(
                "Revenue Feedback",
                f"${revenue_fb:.0f}B",
                delta="Additional revenue" if revenue_fb > 0 else "Revenue loss",
                delta_color="normal" if revenue_fb > 0 else "inverse",
            )

        with col3:
            avg_employment = np.mean(macro_result.employment_change_millions)
            st_module.metric(
                "Avg Employment Effect",
                f"{avg_employment:+.2f}M jobs",
                delta="Job creation" if avg_employment > 0 else "Job losses",
            )

        with col4:
            net_budget = macro_result.net_budget_effect
            st_module.metric(
                "Net Budget Effect",
                f"${net_budget:.0f}B",
                help="Revenue feedback minus interest costs",
            )

        st_module.markdown("---")
        st_module.subheader("Budget Impact with Dynamic Feedback")

        # Deficit convention throughout (positive = increases the deficit),
        # matching the Results tab headline — the previous revenue-convention
        # block made the same policy flip sign between tabs, and showed $0B
        # conventional for spending policies (their impulse is not in
        # static_revenue_effect).
        #
        # One function, one set of numbers: the Results tab's Key Metrics and
        # Copy Summary render this same DynamicView (NOTES §4.4).
        view = compute_dynamic_view(result, macro_result, model_name)
        conventional_score = view.conventional
        feedback_total = view.feedback
        interest_total = view.debt_service
        dynamic_total = view.dynamic_total

        col1, col2, col3, col4 = st_module.columns(4)

        with col1:
            st_module.metric(
                "Conventional Score",
                f"${conventional_score:+.0f}B",
                help=(
                    "Static + behavioral, before macro feedback "
                    "(positive = increases the deficit — this is the Results "
                    "tab headline, in every mode)."
                ),
            )

        with col2:
            st_module.metric(
                "Revenue Feedback",
                f"${feedback_total:+.0f}B",
                help=(
                    "Additional revenue from (temporary) demand-side GDP "
                    "effects. Positive feedback reduces the deficit impact."
                ),
            )

        with col3:
            st_module.metric(
                "Debt Service",
                f"${interest_total:+.0f}B",
                help=(
                    "Interest cost of the added deficit (positive = adds to "
                    "the deficit) — nets against feedback."
                ),
            )

        with col4:
            net_dynamic_delta = interest_total - feedback_total
            st_module.metric(
                "Dynamic Score",
                f"${dynamic_total:+.0f}B",
                delta=(
                    f"{(net_dynamic_delta / abs(conventional_score) * 100):+.1f}% vs conventional"
                    if conventional_score != 0
                    else "N/A"
                ),
                # A positive delta means the dynamic score adds deficit
                # relative to conventional — color it as bad news.
                delta_color="inverse" if net_dynamic_delta != 0 else "off",
            )

        sign_conv = "+" if conventional_score >= 0 else "-"
        # Feedback is subtracted (it offsets the deficit) and debt service is
        # added; sign each printed term so the arithmetic always matches the
        # Dynamic Score, including when a deficit-reducing policy earns
        # negative feedback or interest savings.
        sign_fb = "-" if feedback_total >= 0 else "+"
        sign_int = "+" if interest_total >= 0 else "-"
        sign_dyn = "+" if dynamic_total >= 0 else "-"
        st_module.markdown(
            f"**Calculation:** {sign_conv}\\${abs(conventional_score):.0f}B (conventional) "
            f"{sign_fb} \\${abs(feedback_total):.0f}B (feedback) "
            f"{sign_int} \\${abs(interest_total):.0f}B (debt service) "
            f"= **{sign_dyn}\\${abs(dynamic_total):.0f}B (dynamic)** "
            f"— positive = increases the deficit"
        )
        st_module.caption(
            f"ℹ️ The Results headline stays at the conventional "
            f"{sign_conv}\\${abs(conventional_score):.0f}B in every mode — dynamic "
            f"scoring adds this view, it does not move the headline. The "
            f"feedback and debt-service figures above are the same numbers the "
            f"Results tab's Key Metrics, Copy Summary and CSV export print, "
            f"computed here from {model_name}."
        )
        st_module.caption(
            "⚠️ Demand-side model only: GDP effects come from temporary "
            "fiscal-impulse multipliers that fade as the Fed responds and "
            "output returns to potential. There is no supply-side channel "
            "(labor supply, capital deepening, potential GDP), which is where "
            "CBO's dynamic analyses locate most long-run effects of permanent "
            "tax changes — treat the dynamic score as illustrative, not a "
            "CBO-comparable dynamic estimate."
        )

        st_module.markdown("---")
        st_module.subheader("Year-by-Year Macroeconomic Effects")

        fig_gdp = go.Figure()
        fig_gdp.add_trace(
            go.Bar(
                x=macro_result.years,
                y=macro_result.gdp_level_pct,
                name="GDP Effect (%)",
                marker_color="#1f77b4",
            )
        )
        fig_gdp.add_trace(
            go.Scatter(
                x=macro_result.years,
                y=np.cumsum(macro_result.gdp_level_pct),
                name="Cumulative GDP (%-years)",
                mode="lines+markers",
                yaxis="y2",
                line=dict(color="#ff7f0e", width=2),
            )
        )
        apply_base_layout(
            fig_gdp,
            title="GDP Effects by Year",
            xaxis_title="Year",
            yaxis_title="GDP Level Effect (%)",
            yaxis2=dict(
                title="Cumulative (%-years)",
                overlaying="y",
                side="right",
            ),
            height=400,
            legend=horizontal_legend(align="center"),
            hovermode="x unified",
        )
        gdp_rows = [
            (str(int(year)), f"{level:+.2f}%")
            for year, level in zip(macro_result.years, macro_result.gdp_level_pct)
        ]
        render_accessible_chart(
            st_module,
            fig_gdp,
            ChartDescription(
                title="GDP Effects by Year",
                summary=(
                    "Combined bar and line chart: annual GDP level effect "
                    "in percent (bars) and cumulative GDP effect in "
                    "percent-years (line)."
                ),
                data_rows=gdp_rows,
            ),
        )

        col1, col2 = st_module.columns(2)
        with col1:
            fig_emp = go.Figure()
            fig_emp.add_trace(
                go.Scatter(
                    x=macro_result.years,
                    y=macro_result.employment_change_millions,
                    mode="lines+markers",
                    name="Employment Change",
                    fill="tozeroy",
                    line=dict(color="#2ca02c", width=2),
                )
            )
            apply_base_layout(
                fig_emp,
                title="Employment Effect (Millions of Jobs)",
                xaxis_title="Year",
                yaxis_title="Jobs (Millions)",
                height=350,
                hovermode="x",
            )
            emp_rows = [
                (str(int(year)), f"{jobs:+,.2f}M")
                for year, jobs in zip(
                    macro_result.years, macro_result.employment_change_millions
                )
            ]
            render_accessible_chart(
                st_module,
                fig_emp,
                ChartDescription(
                    title="Employment Effect",
                    summary=(
                        "Area chart showing the employment effect in millions "
                        "of jobs across the budget window."
                    ),
                    data_rows=emp_rows,
                ),
            )

        with col2:
            fig_rev = go.Figure()
            fig_rev.add_trace(
                go.Bar(
                    x=macro_result.years,
                    y=macro_result.revenue_feedback_billions,
                    name="Revenue Feedback",
                    marker_color="#9467bd",
                )
            )
            apply_base_layout(
                fig_rev,
                title="Revenue Feedback by Year ($B)",
                xaxis_title="Year",
                yaxis_title="Revenue Feedback ($B)",
                height=350,
                hovermode="x",
            )
            rev_rows = format_currency_rows(
                (str(int(year)), float(val))
                for year, val in zip(
                    macro_result.years, macro_result.revenue_feedback_billions
                )
            )
            render_accessible_chart(
                st_module,
                fig_rev,
                ChartDescription(
                    title="Revenue Feedback by Year",
                    summary=(
                        "Bar chart showing annual revenue feedback from "
                        "macroeconomic effects, in billions of dollars."
                    ),
                    data_rows=rev_rows,
                ),
            )

        st_module.markdown("---")
        st_module.subheader("Interest Rate Effects")

        col1, col2 = st_module.columns(2)
        with col1:
            avg_short = np.mean(macro_result.short_rate_ppts)
            st_module.metric(
                "Avg Short-Term Rate Change",
                f"{avg_short:+.2f} ppts",
                help="Federal funds rate effect (basis points)",
            )
        with col2:
            avg_long = np.mean(macro_result.long_rate_ppts)
            st_module.metric(
                "Avg Long-Term Rate Change",
                f"{avg_long:+.2f} ppts",
                help="10-year Treasury rate effect",
            )

        st_module.markdown("---")
        st_module.subheader("Detailed Year-by-Year Results")

        macro_df = macro_result.to_dataframe()
        try:
            st_module.dataframe(macro_df, width="stretch", hide_index=True)
        except TypeError:  # pragma: no cover - older Streamlit / test fakes
            st_module.dataframe(macro_df, hide_index=True)
        dynamic_meta = (
            f"# Policy: {policy.name}\n"
            f"# Export Date: {date.today().isoformat()}\n"
            f"# Model Version: 1.0.0\n"
            f"# Dynamic Model: {model_name}\n"
            f"# Methodology: FRB/US-calibrated macroeconomic multipliers\n"
            f"#\n"
        )
        st_module.download_button(
            label="📊 Download Dynamic Scoring as CSV",
            data=dynamic_meta + macro_df.to_csv(index=False),
            file_name="dynamic_scoring_{}.csv".format(
                re.sub(r"[^\w\-]", "_", policy.name).strip("_").lower()
            ),
            mime="text/csv",
        )

        st_module.markdown("---")
        with st_module.expander("📖 Methodology Notes"):
            if isinstance(adapter, frbus_adapter_lite_cls):
                st_module.markdown(
                    """
                            **FRB/US-Lite Model**

                            This model uses multipliers calibrated to the Federal Reserve's FRB/US model:

                            | Parameter | Value | Source |
                            |-----------|-------|--------|
                            | Spending Multiplier | 1.4 (year 1) | FRB/US simulations |
                            | Tax Multiplier | -0.7 (year 1) | FRB/US simulations |
                            | Multiplier Decay | 0.75/year | Standard assumption |
                            | Crowding Out | 15% of deficit | Interest rate response |
                            | Marginal Tax Rate | 25% | For revenue feedback |

                            **Key Assumptions:**
                            - Monetary policy follows Taylor rule (not at zero lower bound)
                            - Fiscal closure via surplus ratio targeting
                            - No supply-side effects on potential GDP

                            **References:**
                            - Coenen et al. (2012). "Effects of Fiscal Stimulus in Structural Models"
                            - CBO (2019). "The Effects of Automatic Stabilizers on the Federal Budget"
                            """
                )
            else:
                st_module.markdown(
                    """
                            **Simple Multiplier Model**

                            This model uses basic Keynesian fiscal multipliers:

                            | Parameter | Value |
                            |-----------|-------|
                            | Spending Multiplier | 1.0 |
                            | Tax Multiplier | -0.5 |
                            | Multiplier Decay | 0.9/year |
                            | Marginal Tax Rate | 25% |

                            This is a simplified model. For more accurate results, use FRB/US-Lite.
                            """
                )

    except Exception as e:
        st_module.error(f"Error running dynamic scoring: {e}")
        import traceback

        st_module.code(traceback.format_exc())
