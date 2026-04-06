"""
Distributional analysis tab renderer.
"""

from __future__ import annotations

import re
from datetime import date
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
    use_microsim: bool = False,
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
        cache_key = f"dist:{run_id}:{group_type.name}:microsim={use_microsim}" if run_id else None
        dist_analysis = st_module.session_state.get(cache_key) if cache_key else None
        if dist_analysis is None:
            with st_module.spinner("Analyzing distributional impact..."):
                if use_microsim:
                    dist_analysis = dist_engine.analyze_policy_microsim(policy, group_type=group_type)
                else:
                    dist_analysis = dist_engine.analyze_policy(policy, group_type=group_type)
            if use_microsim:
                st_module.info("📊 Using microsimulation (individual-level tax calculation)")
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
        dist_meta = (
            f"# Policy: {policy.name}\n"
            f"# Export Date: {date.today().isoformat()}\n"
            f"# Model Version: 1.0.0\n"
            f"# Income Grouping: {group_type_choice}\n"
            f"# Methodology: TPC/JCT-style distributional analysis\n"
            f"#\n"
        )
        st_module.download_button(
            label="📊 Download Distribution Table as CSV",
            data=dist_meta + df_dist.to_csv(index=False),
            file_name="distribution_{}.csv".format(
                re.sub(r"[^\w\-]", "_", policy.name).strip("_").lower()
            ),
            mime="text/csv",
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
            meta={"description": "Bar chart showing average tax change in dollars by income group, with green bars for tax cuts and red bars for tax increases"},
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
                fig_pie.update_layout(
                    height=350,
                    showlegend=False,
                    meta={"description": "Pie chart showing each income group's share of the total tax change"},
                )
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
            with st_module.spinner("Analyzing top income group detail..."):
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

        # Tariff policy consumer impact section
        try:
            from fiscal_model.trade import TariffPolicy
            if isinstance(policy, TariffPolicy):
                _render_tariff_consumer_impact(st_module, policy)
        except ImportError:
            pass

    except Exception as e:
        st_module.error(f"Error running distributional analysis: {e}")
        import traceback

        st_module.code(traceback.format_exc())


def _render_tariff_consumer_impact(st_module: Any, policy: Any) -> None:
    """
    Render consumer impact section for tariff policies.

    Shows consumer cost estimates, household impact, retaliation costs,
    and distributional effects by income quintile.
    """
    st_module.markdown("---")
    st_module.subheader("🏷️ Consumer Price Impact")

    st_module.markdown(
        "<div class='info-box'>"
        "💡 <strong>How tariffs affect consumers:</strong> Tariffs increase consumer prices. "
        "The pass-through rate determines how much of the tariff cost falls on consumers vs. importers. "
        "Tariffs are regressive — lower-income households spend a larger share of income on tariff-affected goods."
        "</div>",
        unsafe_allow_html=True,
    )

    # Get tariff metrics
    consumer_cost = policy.estimate_consumer_cost()
    household_impact = policy.get_household_impact()
    retaliation_cost = policy.estimate_retaliation_cost()
    pass_through_rate = policy.pass_through_rate

    # Display three metric columns
    col1, col2, col3 = st_module.columns(3)
    with col1:
        st_module.metric(
            "Annual Consumer Cost",
            f"${consumer_cost:.1f}B",
            help="Total annual cost to consumers from higher import prices",
        )
    with col2:
        st_module.metric(
            "Cost per Household",
            f"${household_impact:,.0f}/year",
            help="Average annual tariff cost per U.S. household",
        )
    with col3:
        st_module.metric(
            "Annual Export Loss (Retaliation)",
            f"${retaliation_cost:.1f}B",
            help="Estimated export losses from trading partner retaliation",
        )

    # Quintile distribution of consumer costs (regressive impact)
    st_module.subheader("Consumer Cost by Income Quintile")
    st_module.markdown(
        "Tariffs are regressive: lower-income households spend a larger share of income on tariff-affected goods "
        "(clothing, footwear, appliances, vehicles)."
    )

    # Define quintile characteristics
    # Median incomes by quintile (approximate from IRS SOI 2022)
    median_incomes = {
        "Lowest Quintile": 15_000,
        "Second Quintile": 35_000,
        "Middle Quintile": 55_000,
        "Fourth Quintile": 85_000,
        "Top Quintile": 200_000,
    }

    # Regressivity: share of income spent on tariff-affected goods
    # (Conservative: tariffs mainly affect consumer goods, not services)
    spending_shares = {
        "Lowest Quintile": 0.035,      # 3.5% of income
        "Second Quintile": 0.028,      # 2.8%
        "Middle Quintile": 0.022,      # 2.2%
        "Fourth Quintile": 0.017,      # 1.7%
        "Top Quintile": 0.009,         # 0.9%
    }

    # Calculate household consumer costs by quintile
    quintile_costs = {}
    for quintile_name, median_income in median_incomes.items():
        share = spending_shares[quintile_name]
        cost = median_income * share
        quintile_costs[quintile_name] = cost

    # Create bar chart
    fig_quintile = go.Figure()
    quintile_names = list(quintile_costs.keys())
    costs = list(quintile_costs.values())

    fig_quintile.add_trace(
        go.Bar(
            x=quintile_names,
            y=costs,
            marker_color="#e74c3c",
            text=[f"${c:,.0f}" for c in costs],
            textposition="outside",
            showlegend=False,
        )
    )

    fig_quintile.update_layout(
        xaxis_title="Income Group",
        yaxis_title="Annual Consumer Cost ($)",
        height=350,
        meta={"description": "Bar chart showing tariff consumer costs by income quintile, demonstrating regressive impact on lower-income households"},
    )

    st_module.plotly_chart(fig_quintile, use_container_width=True)

    # Pass-through rate caption
    st_module.caption(
        f"Consumer cost estimates assume {pass_through_rate*100:.0f}% tariff pass-through to prices "
        "(Amiti, Redding & Weinstein 2019)."
    )
