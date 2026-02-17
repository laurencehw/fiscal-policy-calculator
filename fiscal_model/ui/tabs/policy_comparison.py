"""
Policy comparison tab renderer.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go


def render_policy_comparison_tab(
    st_module: Any,
    is_spending: bool,
    preset_policies: dict[str, dict[str, Any]],
    tax_policy_cls: Any,
    policy_type_income_tax: Any,
    fiscal_policy_scorer_cls: Any,
    data_year: int,
    use_real_data: bool,
    dynamic_scoring: bool,
) -> None:
    """
    Render policy comparison tab content.
    """
    st_module.header("🔀 Policy Comparison")

    if is_spending or not preset_policies:
        st_module.info(
            "📊 Policy comparison is available for tax policies. Select a tax policy category in the sidebar to use this feature."
        )
        policies_to_compare: list[str] = []
    else:
        st_module.markdown(
            """
            <div class="info-box">
            💡 <strong>Compare scenarios:</strong> Select 2-3 policies from the preset library to see how they compare side-by-side.
            </div>
            """,
            unsafe_allow_html=True,
        )

        comparison_options = [k for k in preset_policies.keys() if k != "Custom Policy"]
        policies_to_compare = st_module.multiselect(
            "Select policies to compare (2-3 recommended)",
            options=comparison_options,
            default=comparison_options[:2] if len(comparison_options) >= 2 else comparison_options,
            max_selections=4,
        )

    if len(policies_to_compare) < 2:
        st_module.info("👆 Select at least 2 policies above to see a comparison")
        return

    with st_module.spinner("Calculating and comparing policies..."):
        try:
            comparison_results = []

            for preset_name in policies_to_compare:
                preset = preset_policies[preset_name]
                comp_policy = tax_policy_cls(
                    name=preset_name,
                    description=preset["description"],
                    policy_type=policy_type_income_tax,
                    rate_change=preset["rate_change"] / 100,
                    affected_income_threshold=preset["threshold"],
                    data_year=data_year,
                    duration_years=10,
                    phase_in_years=0,
                    taxable_income_elasticity=0.25,
                )

                comp_scorer = fiscal_policy_scorer_cls(baseline=None, use_real_data=use_real_data)
                comp_result = comp_scorer.score_policy(comp_policy, dynamic=dynamic_scoring)

                comparison_results.append(
                    {
                        "name": preset_name,
                        "policy": comp_policy,
                        "result": comp_result,
                        "total_10yr": comp_result.static_revenue_effect.sum(),
                        "year1": comp_result.static_revenue_effect[0],
                        "affected_millions": comp_policy.affected_taxpayers_millions,
                        "avg_income": comp_policy.avg_taxable_income_in_bracket,
                    }
                )

            st_module.subheader("📊 Summary Comparison")
            comparison_df = pd.DataFrame(
                [
                    {
                        "Policy": r["name"],
                        "10-Year Effect ($B)": f"${r['total_10yr']:.1f}",
                        "Year 1 Effect ($B)": f"${r['year1']:.1f}",
                        "Affected (M)": f"{r['affected_millions']:.2f}",
                        "Avg Income": f"${r['avg_income']:,.0f}",
                        "Per Taxpayer": f"${(r['year1'] * 1e9 / (r['affected_millions'] * 1e6) if r['affected_millions'] > 0 else 0):,.0f}",
                    }
                    for r in comparison_results
                ]
            )
            st_module.dataframe(comparison_df, use_container_width=True, hide_index=True)

            st_module.markdown("---")
            st_module.subheader("10-Year Revenue Effect Comparison")
            fig_compare = go.Figure()
            for r in comparison_results:
                color = "#FF6B6B" if r["total_10yr"] > 0 else "#4ECDC4"
                fig_compare.add_trace(
                    go.Bar(
                        name=r["name"],
                        x=[r["name"]],
                        y=[r["total_10yr"]],
                        marker_color=color,
                        text=[f"${r['total_10yr']:.1f}B"],
                        textposition="outside",
                    )
                )
            fig_compare.update_layout(
                xaxis_title="Policy",
                yaxis_title="10-Year Revenue Effect (Billions)",
                showlegend=False,
                height=500,
                hovermode="x",
            )
            st_module.plotly_chart(fig_compare, use_container_width=True)

            st_module.markdown("---")
            st_module.subheader("Year-by-Year Comparison")
            fig_timeline_compare = go.Figure()
            for r in comparison_results:
                fig_timeline_compare.add_trace(
                    go.Scatter(
                        x=r["result"].baseline.years,
                        y=r["result"].static_revenue_effect,
                        mode="lines+markers",
                        name=r["name"],
                        line=dict(width=3),
                        marker=dict(size=8),
                    )
                )
            fig_timeline_compare.update_layout(
                xaxis_title="Year",
                yaxis_title="Revenue Effect (Billions)",
                hovermode="x unified",
                height=500,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st_module.plotly_chart(fig_timeline_compare, use_container_width=True)

            st_module.markdown("---")
            st_module.subheader("📝 Key Differences")
            max_revenue_policy = max(comparison_results, key=lambda x: x["total_10yr"])
            min_revenue_policy = min(comparison_results, key=lambda x: x["total_10yr"])

            col1, col2 = st_module.columns(2)
            with col1:
                st_module.success(
                    f"""
                        **Largest Revenue Raiser**

                        {max_revenue_policy['name']}

                        - **10-Year Effect:** ${max_revenue_policy['total_10yr']:.1f}B
                        - **Affected:** {max_revenue_policy['affected_millions']:.2f}M taxpayers
                        """
                )
            with col2:
                st_module.error(
                    f"""
                        **Largest Revenue Cost**

                        {min_revenue_policy['name']}

                        - **10-Year Effect:** ${min_revenue_policy['total_10yr']:.1f}B
                        - **Affected:** {min_revenue_policy['affected_millions']:.2f}M taxpayers
                        """
                )

        except Exception as e:
            st_module.error(f"Error comparing policies: {e}")
            import traceback

            st_module.code(traceback.format_exc())
