"""
Results summary tab renderer.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def render_results_summary_tab(
    st_module: Any,
    result_data: dict[str, Any],
    cbo_score_map: dict[str, dict[str, Any]],
) -> None:
    """
    Render tab2 results summary for microsim or aggregate runs.
    """
    if result_data.get("is_microsim"):
        st_module.header("🔬 Microsimulation Results")
        st_module.markdown(result_data["source_msg"])

        col1, col2, col3 = st_module.columns(3)
        rev_change = result_data["revenue_change_billions"]

        with col1:
            st_module.metric(
                "Revenue Change (Year 1)",
                f"${rev_change:+.1f}B",
                delta="Revenue Gain" if rev_change > 0 else "Revenue Loss",
                delta_color="normal" if rev_change > 0 else "inverse",
            )
        with col2:
            st_module.metric("Baseline Revenue", f"${result_data['baseline_revenue']:,.1f}B")
        with col3:
            st_module.metric("Reform Revenue", f"${result_data['reform_revenue']:,.1f}B")

        st_module.markdown("---")
        st_module.subheader("👨‍👩‍👧‍👦 Impact by Family Size")
        st_module.caption("Average tax change per household by number of children. (Negative = Tax Cut)")

        dist_kids = result_data["distribution_kids"]
        fig = px.bar(
            dist_kids,
            x="children",
            y="avg_tax_change",
            labels={"children": "Number of Children", "avg_tax_change": "Average Tax Change ($)"},
            color="avg_tax_change",
            color_continuous_scale="RdBu_r",
        )
        st_module.plotly_chart(fig, use_container_width=True)

        st_module.info(
            """
            **Why Microsimulation?**
            Aggregate models use average incomes. Microsimulation calculates taxes for *individual households*,
            capturing complex interactions like how the Child Tax Credit phase-out overlaps with other provisions.
            """
        )
        return

    policy = result_data["policy"]
    result = result_data["result"]
    is_spending_result = result_data.get("is_spending", False)

    st_module.header("📈 Results Summary")

    static_deficit_total = float(result.static_deficit_effect.sum())
    behavioral_total = float(result.behavioral_offset.sum())
    dynamic_revenue_feedback_total = (
        float(result.dynamic_effects.revenue_feedback.sum()) if result.dynamic_effects else 0.0
    )
    final_deficit_total = float(result.final_deficit_effect.sum())
    year1_final = float(result.final_deficit_effect[0])

    if final_deficit_total < 0:
        impact_color = "#28a745"
        impact_label = "Deficit Reduction"
    elif final_deficit_total > 0:
        impact_color = "#dc3545"
        impact_label = "Deficit Increase"
    else:
        impact_color = "#555"
        impact_label = "No Change"

    st_module.markdown(
        f"""
        <div style="background-color: #f0f2f6; padding: 1rem; border-radius: 0.5rem; text-align: center; margin-bottom: 1rem;">
            <h3 style="margin:0; color: #555;">10-Year Final Deficit Impact</h3>
            <h1 style="margin:0; font-size: 3rem; color: {impact_color};">
                ${final_deficit_total:+,.1f}B
            </h1>
            <p style="margin:0; color: #666;">
                {impact_label}{' (Spending Policy)' if is_spending_result else ''}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_metrics, col_context = st_module.columns([1, 1])

    with col_metrics:
        st_module.subheader("📊 Key Metrics")
        m1, m2 = st_module.columns(2)
        with m1:
            st_module.metric(
                "Static Deficit Effect (10Y)",
                f"${static_deficit_total:+.1f}B",
                help="Static effect on the deficit before behavioral and macro feedback (positive = deficit increase).",
            )
        with m2:
            behavioral_pct = (abs(behavioral_total) / abs(static_deficit_total) * 100) if static_deficit_total != 0 else 0
            st_module.metric(
                "Behavioral Response (10Y)",
                f"${behavioral_total:+.1f}B",
                delta=f"{behavioral_pct:.0f}% of static",
                delta_color="off",
                help="Micro behavioral response (e.g., ETI / realizations). Positive increases deficit vs static.",
            )

        m3, m4 = st_module.columns(2)
        with m3:
            st_module.metric(
                "Revenue Feedback (10Y)",
                f"${dynamic_revenue_feedback_total:+.1f}B",
                help="Additional revenue from macro feedback (reduces deficit impact in dynamic scoring).",
            )
        with m4:
            st_module.metric(
                "Year 1 Deficit Impact",
                f"${year1_final:+.1f}B",
                help="Final deficit impact in the first budget year.",
            )

        st_module.subheader("🧮 Decomposition (10-Year)")
        steps_x = ["Static", "Behavioral", "Final"]
        steps_measure = ["relative", "relative", "total"]
        steps_y = [static_deficit_total, behavioral_total, final_deficit_total]

        if result.dynamic_effects:
            steps_x = ["Static", "Behavioral", "Dynamic Feedback", "Final"]
            steps_measure = ["relative", "relative", "relative", "total"]
            steps_y = [
                static_deficit_total,
                behavioral_total,
                -dynamic_revenue_feedback_total,
                final_deficit_total,
            ]

        fig_waterfall = go.Figure(
            go.Waterfall(
                orientation="v",
                measure=steps_measure,
                x=steps_x,
                y=steps_y,
                text=[f"${v:+.0f}B" for v in steps_y],
                textposition="outside",
                increasing={"marker": {"color": "#dc3545"}},
                decreasing={"marker": {"color": "#28a745"}},
                totals={"marker": {"color": "#1f77b4"}},
            )
        )
        fig_waterfall.update_layout(
            margin=dict(l=20, r=20, t=10, b=10),
            height=320,
            yaxis_title="Deficit Impact ($B, + = increases deficit)",
            showlegend=False,
        )
        st_module.plotly_chart(fig_waterfall, use_container_width=True)

    with col_context:
        policy_name = result_data.get("policy_name", "")
        cbo_data = cbo_score_map.get(policy_name)

        if cbo_data:
            st_module.subheader("🏛️ Official Benchmark")
            official = cbo_data["official_score"]
            model_score = final_deficit_total
            error_pct = ((model_score - official) / abs(official)) * 100 if official != 0 else 0
            abs_error = abs(error_pct)

            if abs_error <= 5:
                icon, rating = "🎯", "Excellent"
            elif abs_error <= 10:
                icon, rating = "✅", "Good"
            elif abs_error <= 15:
                icon, rating = "⚠️", "Acceptable"
            else:
                icon, rating = "❌", "Needs Review"

            c1, c2 = st_module.columns(2)
            with c1:
                st_module.metric(
                    f"Official ({cbo_data['source']})",
                    f"${official:+,.0f}B",
                    delta=f"{error_pct:+.1f}% error",
                    delta_color="off",
                )
            with c2:
                st_module.markdown(f"**Accuracy:** {icon} {rating}")
                st_module.caption(cbo_data["notes"])
        else:
            st_module.subheader("👥 Distribution Context")
            if policy.affected_taxpayers_millions > 0:
                st_module.metric("Affected Taxpayers", f"{policy.affected_taxpayers_millions:.2f} Million")
                if hasattr(policy, "avg_taxable_income_in_bracket"):
                    st_module.metric("Avg Income of Affected", f"${policy.avg_taxable_income_in_bracket:,.0f}")
            else:
                st_module.info("No distribution data available for this policy type.")

    st_module.markdown("---")
    c_chart1, c_chart2 = st_module.columns(2)

    with c_chart1:
        st_module.subheader("Year-by-Year Deficit Impact")
        years = result.baseline.years
        df_timeline = pd.DataFrame(
            {
                "Year": years,
                "Deficit Impact": result.final_deficit_effect,
            }
        )

        fig_timeline = go.Figure()
        fig_timeline.add_trace(
            go.Bar(
                x=df_timeline["Year"],
                y=df_timeline["Deficit Impact"],
                marker_color=[
                    "#dc3545" if v > 0 else "#28a745" if v < 0 else "#999"
                    for v in df_timeline["Deficit Impact"]
                ],
            )
        )
        fig_timeline.update_layout(
            margin=dict(l=20, r=20, t=20, b=20),
            height=300,
            xaxis_title=None,
            yaxis_title="Deficit Impact ($B)",
        )
        st_module.plotly_chart(fig_timeline, use_container_width=True)

    with c_chart2:
        st_module.subheader("Cumulative Deficit Impact")
        df_timeline["Cumulative"] = df_timeline["Deficit Impact"].cumsum()

        fig_cum = go.Figure()
        fig_cum.add_trace(
            go.Scatter(
                x=df_timeline["Year"],
                y=df_timeline["Cumulative"],
                fill="tozeroy",
                mode="lines+markers",
                line=dict(color="#2ca02c", width=3),
            )
        )
        fig_cum.update_layout(
            margin=dict(l=20, r=20, t=20, b=20),
            height=300,
            xaxis_title=None,
            yaxis_title="Cumulative Deficit Impact ($B)",
        )
        st_module.plotly_chart(fig_cum, use_container_width=True)
