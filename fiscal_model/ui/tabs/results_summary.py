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

    static_total = result.static_revenue_effect.sum()
    behavioral_total = result.behavioral_offset.sum()
    net_total = static_total + behavioral_total
    year1_static = result.static_revenue_effect[0]
    year1_behavioral = result.behavioral_offset[0]
    year1_net = year1_static + year1_behavioral

    st_module.markdown(
        f"""
        <div style="background-color: #f0f2f6; padding: 1rem; border-radius: 0.5rem; text-align: center; margin-bottom: 1rem;">
            <h3 style="margin:0; color: #555;">10-Year Final Budget Impact</h3>
            <h1 style="margin:0; font-size: 3rem; color: {'#28a745' if (net_total > 0 and not is_spending_result) or (net_total > 0 and is_spending_result) else '#dc3545'};">
                ${abs(net_total):,.1f} Billion
            </h1>
            <p style="margin:0; color: #666;">
                {("Deficit Reduction" if net_total > 0 else "Deficit Increase") if not is_spending_result else ("Spending Increase" if net_total > 0 else "Spending Cut")}
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
                "Static Estimate",
                f"${abs(static_total):.1f}B",
                help="Direct effect before behavioral changes",
            )
        with m2:
            behavioral_pct = (abs(behavioral_total) / abs(static_total) * 100) if static_total != 0 else 0
            st_module.metric(
                "Behavioral Offset",
                f"${abs(behavioral_total):.1f}B",
                delta=f"{behavioral_pct:.0f}% of static",
                delta_color="off",
                help="Revenue lost/gained due to behavioral changes (ETI)",
            )

        m3, m4 = st_module.columns(2)
        with m3:
            st_module.metric("Avg Annual Cost", f"${abs(net_total/10):.1f}B")
        with m4:
            st_module.metric("Year 1 Impact", f"${abs(year1_net):.1f}B")

    with col_context:
        policy_name = result_data.get("policy_name", "")
        cbo_data = cbo_score_map.get(policy_name)

        if cbo_data:
            st_module.subheader("🏛️ Official Benchmark")
            official = cbo_data["official_score"]
            model_score = -net_total
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
                    f"${official:,.0f}B",
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
        st_module.subheader("Year-by-Year Net Effect")
        years = result.baseline.years
        df_timeline = pd.DataFrame(
            {
                "Year": years,
                "Net Effect": result.static_revenue_effect + result.behavioral_offset,
            }
        )

        fig_timeline = go.Figure()
        fig_timeline.add_trace(
            go.Bar(
                x=df_timeline["Year"],
                y=df_timeline["Net Effect"],
                marker_color="#1f77b4",
            )
        )
        fig_timeline.update_layout(
            margin=dict(l=20, r=20, t=20, b=20),
            height=300,
            xaxis_title=None,
            yaxis_title="$ Billions",
        )
        st_module.plotly_chart(fig_timeline, use_container_width=True)

    with c_chart2:
        st_module.subheader("Cumulative Impact")
        df_timeline["Cumulative"] = df_timeline["Net Effect"].cumsum()

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
            yaxis_title="Cumulative $ Billions",
        )
        st_module.plotly_chart(fig_cum, use_container_width=True)
