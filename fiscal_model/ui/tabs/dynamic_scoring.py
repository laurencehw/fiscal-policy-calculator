"""
Dynamic scoring tab renderer.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import plotly.graph_objects as go


def render_dynamic_scoring_tab(
    st_module: Any,
    dynamic_scoring: bool,
    result_data: Any,
    macro_model_name: str | None,
    macro_scenario_cls: Any,
    frbus_adapter_lite_cls: Any,
    simple_multiplier_adapter_cls: Any,
    build_macro_scenario_fn: Any,
) -> None:
    """
    Render dynamic scoring analysis tab content.
    """
    st_module.header("🌍 Dynamic Scoring")

    if not dynamic_scoring:
        st_module.markdown(
            """
            <div class="info-box">
            💡 <strong>Dynamic scoring is disabled.</strong> Enable it in the sidebar to see macroeconomic effects
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

            **Enable dynamic scoring** in the sidebar to see these effects for your policy.
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

        use_simple = macro_model_name == "Simple Multiplier"
        if use_simple:
            adapter = simple_multiplier_adapter_cls()
            model_name = "Simple Keynesian Multiplier"
        else:
            adapter = frbus_adapter_lite_cls()
            model_name = "FRB/US-Lite (Federal Reserve calibrated)"

        macro_result = adapter.run(scenario)
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

        static_total = result.static_revenue_effect.sum()
        behavioral_total = result.behavioral_offset.sum()
        conventional_total = static_total + behavioral_total
        dynamic_total = conventional_total + macro_result.cumulative_revenue_feedback

        col1, col2, col3 = st_module.columns(3)

        with col1:
            st_module.metric(
                "Conventional Score",
                f"${conventional_total:.0f}B",
                help="Static + behavioral (no macro feedback)",
            )

        with col2:
            st_module.metric(
                "Revenue Feedback",
                f"${macro_result.cumulative_revenue_feedback:+.0f}B",
                help="Additional revenue from GDP growth",
            )

        with col3:
            st_module.metric(
                "Dynamic Score",
                f"${dynamic_total:.0f}B",
                delta=(
                    f"{(macro_result.cumulative_revenue_feedback / abs(conventional_total) * 100):+.1f}% vs conventional"
                    if conventional_total != 0
                    else "N/A"
                ),
                delta_color="normal" if macro_result.cumulative_revenue_feedback > 0 else "inverse",
            )

        sign_conv = "+" if conventional_total >= 0 else "-"
        sign_fb = "+" if macro_result.cumulative_revenue_feedback >= 0 else "-"
        sign_dyn = "+" if dynamic_total >= 0 else "-"
        st_module.markdown(
            f"""
                    **Calculation:** ${sign_conv}${abs(conventional_total):.0f}B (conventional) {sign_fb} ${abs(macro_result.cumulative_revenue_feedback):.0f}B (feedback) = **{sign_dyn}${abs(dynamic_total):.0f}B (dynamic)**
                    """
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
        fig_gdp.update_layout(
            title="GDP Effects by Year",
            xaxis_title="Year",
            yaxis_title="GDP Level Effect (%)",
            yaxis2=dict(
                title="Cumulative (%-years)",
                overlaying="y",
                side="right",
            ),
            height=400,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
            hovermode="x unified",
        )
        st_module.plotly_chart(fig_gdp, use_container_width=True)

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
            fig_emp.update_layout(
                title="Employment Effect (Millions of Jobs)",
                xaxis_title="Year",
                yaxis_title="Jobs (Millions)",
                height=350,
                hovermode="x",
            )
            st_module.plotly_chart(fig_emp, use_container_width=True)

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
            fig_rev.update_layout(
                title="Revenue Feedback by Year ($B)",
                xaxis_title="Year",
                yaxis_title="Revenue Feedback ($B)",
                height=350,
                hovermode="x",
            )
            st_module.plotly_chart(fig_rev, use_container_width=True)

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
        st_module.dataframe(macro_df, use_container_width=True, hide_index=True)

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
