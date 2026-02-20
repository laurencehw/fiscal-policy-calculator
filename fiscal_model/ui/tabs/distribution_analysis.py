"""
Distributional analysis tab renderer.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go


def render_distribution_tab(
    st_module: Any,
    model_available: bool,
    policy: Any,
    distribution_engine_cls: Any,
    income_group_type_cls: Any,
    format_distribution_table_fn: Any,
    winners_losers_summary_fn: Any,
    run_id: str | None = None,
) -> None:
    """
    Render distributional analysis tab content.
    """
    st_module.header("👥 Distributional Analysis")

    st_module.markdown(
        """
        <div class="info-box">
        💡 <strong>Who pays?</strong> This tab shows how the tax change affects different income groups,
        following Tax Policy Center (TPC) and Joint Committee on Taxation (JCT) methodology.
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not (model_available and hasattr(policy, "rate_change")):
        st_module.info("👆 Calculate a tax policy first to see distributional analysis")
        return

    dist_engine = distribution_engine_cls(data_year=2022)
    col1, col2 = st_module.columns([1, 3])
    with col1:
        group_type_choice = st_module.selectbox(
            "Income grouping",
            ["Quintiles (5 groups)", "Deciles (10 groups)", "JCT Dollar Brackets"],
            help="How to divide taxpayers into income groups",
        )

        if group_type_choice == "Quintiles (5 groups)":
            group_type = income_group_type_cls.QUINTILE
        elif group_type_choice == "Deciles (10 groups)":
            group_type = income_group_type_cls.DECILE
        else:
            group_type = income_group_type_cls.JCT_DOLLAR

    try:
        cache_key = f"dist:{run_id}:{group_type.name}" if run_id else None
        dist_analysis = st_module.session_state.get(cache_key) if cache_key else None
        if dist_analysis is None:
            dist_analysis = dist_engine.analyze_policy(policy, group_type=group_type)
            if cache_key:
                st_module.session_state[cache_key] = dist_analysis
        st_module.subheader("Summary")
        summary = winners_losers_summary_fn(dist_analysis)

        col1, col2, col3, col4 = st_module.columns(4)
        with col1:
            st_module.metric(
                "Total Tax Change (Year 1)",
                f"${dist_analysis.total_tax_change:.1f}B",
                delta="Tax increase" if dist_analysis.total_tax_change > 0 else "Tax cut",
            )
        with col2:
            st_module.metric(
                "% with Tax Increase",
                f"{summary['pct_with_increase']:.1f}%",
            )
        with col3:
            st_module.metric(
                "% with Tax Cut",
                f"{summary['pct_with_decrease']:.1f}%",
            )
        with col4:
            unchanged = 100 - summary["pct_with_increase"] - summary["pct_with_decrease"]
            st_module.metric(
                "% Unchanged",
                f"{unchanged:.1f}%",
            )

        st_module.subheader("Tax Change by Income Group")
        df_dist = format_distribution_table_fn(dist_analysis, style="tpc")
        st_module.dataframe(
            df_dist.style.format(
                {
                    "Returns (M)": "{:.1f}",
                    "Avg Tax Change ($)": "${:,.0f}",
                    "% of Income": "{:.2f}%",
                    "Share of Total": "{:.1f}%",
                    "% Tax Increase": "{:.0f}%",
                    "% Tax Decrease": "{:.0f}%",
                    "ETR Change (ppts)": "{:.2f}",
                }
            ),
            use_container_width=True,
            hide_index=True,
        )

        st_module.subheader("Average Tax Change by Income Group")
        fig_dist = go.Figure()
        groups = [r.income_group.name for r in dist_analysis.results]
        changes = [r.tax_change_avg for r in dist_analysis.results]
        colors = ["#28a745" if c < 0 else "#dc3545" for c in changes]
        fig_dist.add_trace(
            go.Bar(
                x=groups,
                y=changes,
                marker_color=colors,
                text=[f"${c:,.0f}" for c in changes],
                textposition="outside",
            )
        )
        fig_dist.update_layout(
            xaxis_title="Income Group",
            yaxis_title="Average Tax Change ($)",
            height=400,
            showlegend=False,
        )
        st_module.plotly_chart(fig_dist, use_container_width=True)

        col1, col2 = st_module.columns(2)
        with col1:
            st_module.subheader("Share of Total Tax Change")
            shares = [
                (r.income_group.name, abs(r.share_of_total_change) * 100)
                for r in dist_analysis.results
                if abs(r.share_of_total_change) > 0.01
            ]
            if shares:
                fig_pie = go.Figure(
                    data=[
                        go.Pie(
                            labels=[s[0] for s in shares],
                            values=[s[1] for s in shares],
                            hole=0.4,
                            textinfo="label+percent",
                        )
                    ]
                )
                fig_pie.update_layout(height=350, showlegend=False)
                st_module.plotly_chart(fig_pie, use_container_width=True)
            else:
                st_module.info("No significant tax change in any group")

        with col2:
            st_module.subheader("Winners & Losers")
            if summary["biggest_losers"]:
                st_module.markdown("**Largest tax increases:**")
                for item in summary["biggest_losers"][:3]:
                    st_module.markdown(f"- {item['group']}: +${item['avg_change']:,.0f} avg")

            if summary["biggest_winners"]:
                st_module.markdown("**Largest tax cuts:**")
                for item in summary["biggest_winners"][:3]:
                    st_module.markdown(f"- {item['group']}: ${item['avg_change']:,.0f} avg")

            if not summary["biggest_losers"] and not summary["biggest_winners"]:
                st_module.info("No significant tax changes")

        st_module.markdown("---")
        st_module.subheader("Top Income Group Detail")
        top_cache_key = f"dist_top:{run_id}" if run_id else None
        top_analysis = st_module.session_state.get(top_cache_key) if top_cache_key else None
        if top_analysis is None:
            top_analysis = dist_engine.create_top_income_breakout(policy)
            if top_cache_key:
                st_module.session_state[top_cache_key] = top_analysis
        st_module.markdown(
            """
                How the tax change affects the top of the income distribution:
                """
        )

        top_data = []
        for r in top_analysis.results:
            if r.share_of_total_change != 0:
                top_data.append(
                    {
                        "Income Group": r.income_group.name,
                        "Returns (M)": f"{r.income_group.num_returns/1e6:.2f}",
                        "Avg Tax Change": f"${r.tax_change_avg:,.0f}",
                        "Share of Total": f"{r.share_of_total_change*100:.1f}%",
                    }
                )

        if top_data:
            st_module.dataframe(pd.DataFrame(top_data), use_container_width=True, hide_index=True)
        else:
            st_module.info("This policy does not significantly affect top income groups")

    except Exception as e:
        st_module.error(f"Error running distributional analysis: {e}")
        import traceback

        st_module.code(traceback.format_exc())
