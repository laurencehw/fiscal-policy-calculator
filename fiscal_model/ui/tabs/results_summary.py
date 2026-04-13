"""
Results summary tab renderer.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from fiscal_model.ui.a11y import (
    ChartDescription,
    format_currency_rows,
    render_accessible_chart,
)
from fiscal_model.ui.share_links import build_share_url


def _build_interpretation_html(
    *,
    final_deficit_total: float,
    n_years: int,
    annual_avg: float,
    pct_of_gdp: float,
) -> str:
    """Build plain-English interpretation HTML without markdown currency parsing."""
    if final_deficit_total > 100:
        return (
            "This policy would <strong>add approximately "
            f"${final_deficit_total:,.0f} billion</strong> "
            f"to the federal deficit over {n_years} years, roughly "
            f"<strong>${abs(annual_avg):,.0f}B per year</strong>, or about "
            f"<strong>{pct_of_gdp:.1f}% of GDP annually</strong>."
        )
    if final_deficit_total < -100:
        return (
            "This policy would <strong>reduce the federal deficit by approximately "
            f"${abs(final_deficit_total):,.0f} billion</strong> over {n_years} years, "
            f"roughly <strong>${abs(annual_avg):,.0f}B per year</strong> "
            "in new revenue or savings, or about "
            f"<strong>{pct_of_gdp:.1f}% of GDP annually</strong>."
        )
    if abs(final_deficit_total) > 1:
        direction = "increase" if final_deficit_total > 0 else "decrease"
        return (
            f"This policy would <strong>{direction} the deficit by about "
            f"${abs(final_deficit_total):,.0f} billion</strong> over {n_years} years "
            f"(<strong>${abs(annual_avg):,.0f}B/year</strong>) "
            "with a relatively modest fiscal impact."
        )
    return f"This policy has <strong>negligible fiscal impact</strong> over the {n_years}-year window."


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
        kids_rows = [
            (f"{int(row['children'])} children", f"${row['avg_tax_change']:+,.0f}")
            for _, row in dist_kids.iterrows()
        ]
        render_accessible_chart(
            st_module,
            fig,
            ChartDescription(
                title="Average Tax Change by Family Size",
                summary=(
                    "Average tax change per household by number of children "
                    "(negative values indicate a tax cut)."
                ),
                data_rows=kids_rows,
            ),
        )

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
    # Quick-copy headline (code block provides built-in copy button)
    headline_copy = (
        f"{policy.name}: ${final_deficit_total:+,.1f}B over 10 years "
        f"({impact_label}) — Fiscal Policy Calculator, {date.today().strftime('%Y-%m-%d')}"
    )
    st_module.code(headline_copy, language=None)

    # Sensitivity range (ETI ± 0.1)
    if hasattr(policy, "taxable_income_elasticity") and not is_spending_result:
        base_eti = getattr(policy, "taxable_income_elasticity", 0.25)
        eti_low = max(0.05, base_eti - 0.1)
        eti_high = base_eti + 0.1

        # Scale behavioral response proportionally to ETI change
        scale_low = eti_low / base_eti if base_eti > 0 else 1.0
        scale_high = eti_high / base_eti if base_eti > 0 else 1.0

        low_estimate = static_deficit_total + (behavioral_total * scale_low) - dynamic_revenue_feedback_total
        high_estimate = static_deficit_total + (behavioral_total * scale_high) - dynamic_revenue_feedback_total

        if abs(high_estimate - low_estimate) >= 0.1:
            st_module.markdown(
                f"<small><b>Sensitivity range:</b> ${low_estimate:+.1f}B to ${high_estimate:+.1f}B "
                f"(ETI {eti_low:.2f} to {eti_high:.2f})</small>",
                unsafe_allow_html=True,
            )
        elif not result.dynamic_effects:
            st_module.markdown(
                "<small><i>Enable dynamic scoring for sensitivity analysis.</i></small>",
                unsafe_allow_html=True,
            )

    # CBO comparison note (if available)
    policy_name = result_data.get("policy_name", "")
    cbo_data = cbo_score_map.get(policy_name)
    if cbo_data:
        official = cbo_data["official_score"]
        error_pct = ((final_deficit_total - official) / abs(official)) * 100 if official != 0 else 0
        st_module.markdown(
            f"<p><small>📌 <b>CBO/JCT estimate:</b> ${official:+,.0f}B &nbsp;·&nbsp; "
            f"<b>Model:</b> ${final_deficit_total:+,.0f}B &nbsp;·&nbsp; "
            f"<b>Difference:</b> {error_pct:+.1f}%</small></p>",
            unsafe_allow_html=True,
        )

    # Plain-English interpretation
    n_years = len(result.years)
    annual_avg = final_deficit_total / n_years
    gdp_baseline = float(result.baseline.nominal_gdp[0]) if result.baseline.nominal_gdp[0] > 0 else 30_000
    pct_of_gdp = abs(annual_avg) / gdp_baseline * 100

    interpretation = _build_interpretation_html(
        final_deficit_total=final_deficit_total,
        n_years=n_years,
        annual_avg=annual_avg,
        pct_of_gdp=pct_of_gdp,
    )
    st_module.markdown(f"<p>{interpretation}</p>", unsafe_allow_html=True)

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
        waterfall_rows = format_currency_rows(zip(steps_x, steps_y))
        render_accessible_chart(
            st_module,
            fig_waterfall,
            ChartDescription(
                title="Deficit Impact Decomposition",
                summary=(
                    "Waterfall chart decomposing the deficit impact from static "
                    "scoring through behavioral and dynamic effects. Positive "
                    "bars increase the deficit; negative bars decrease it."
                ),
                data_rows=waterfall_rows,
            ),
        )

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
        timeline_rows = format_currency_rows(
            (str(int(year)), float(val))
            for year, val in zip(df_timeline["Year"], df_timeline["Deficit Impact"])
        )
        render_accessible_chart(
            st_module,
            fig_timeline,
            ChartDescription(
                title="Year-by-Year Deficit Impact",
                summary=(
                    "Bar chart showing the annual deficit impact in billions of "
                    "dollars across the 10-year budget window."
                ),
                data_rows=timeline_rows,
            ),
        )

    with c_chart2:
        st_module.subheader("Cumulative Deficit Impact")
        df_timeline = df_timeline.assign(
            Cumulative=df_timeline["Deficit Impact"].cumsum(),
            Cum_Low=result.low_estimate.cumsum(),
            Cum_High=result.high_estimate.cumsum(),
        )

        fig_cum = go.Figure()

        # Uncertainty band
        fig_cum.add_trace(
            go.Scatter(
                x=list(df_timeline["Year"]) + list(df_timeline["Year"][::-1]),
                y=list(df_timeline["Cum_High"]) + list(df_timeline["Cum_Low"][::-1]),
                fill="toself",
                fillcolor="rgba(44, 160, 44, 0.15)",
                line=dict(color="rgba(255,255,255,0)"),
                name="Uncertainty range",
                showlegend=True,
            )
        )

        # Central estimate
        fig_cum.add_trace(
            go.Scatter(
                x=df_timeline["Year"],
                y=df_timeline["Cumulative"],
                mode="lines+markers",
                line=dict(color="#2ca02c", width=3),
                name="Central estimate",
            )
        )

        fig_cum.update_layout(
            margin=dict(l=20, r=20, t=20, b=20),
            height=300,
            xaxis_title=None,
            yaxis_title="Cumulative Deficit Impact ($B)",
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02,
                xanchor="right", x=1,
            ),
        )
        cum_rows = format_currency_rows(
            (str(int(year)), float(val))
            for year, val in zip(df_timeline["Year"], df_timeline["Cumulative"])
        )
        render_accessible_chart(
            st_module,
            fig_cum,
            ChartDescription(
                title="Cumulative Deficit Impact",
                summary=(
                    "Line chart with a shaded uncertainty band showing the "
                    "running total deficit impact across the budget window."
                ),
                data_rows=cum_rows,
            ),
        )
        st_module.caption(
            "Shaded area shows uncertainty range. "
            "Uncertainty grows over time, consistent with CBO methodology."
        )

    # Assumptions panel
    st_module.markdown("---")
    with st_module.expander("Assumptions and data sources"):
        a1, a2, a3 = st_module.columns(3)
        with a1:
            st_module.markdown("**Behavioral**")
            if hasattr(policy, "taxable_income_elasticity"):
                st_module.markdown(f"- ETI: {policy.taxable_income_elasticity}")
            if hasattr(policy, "short_run_elasticity") and hasattr(policy, "long_run_elasticity"):
                st_module.markdown(
                    f"- CG elasticity: {policy.short_run_elasticity} "
                    f"(short) / {policy.long_run_elasticity} (long)"
                )
        with a2:
            st_module.markdown("**Data**")
            st_module.markdown("- IRS Statistics of Income")
            st_module.markdown("- FRED Economic Data")
            baseline_year = result.baseline.start_year
            st_module.markdown(f"- CBO Baseline (FY{baseline_year})")
        with a3:
            st_module.markdown("**Methodology**")
            st_module.markdown("- Static + behavioral scoring")
            if result.dynamic_effects:
                st_module.markdown("- FRB/US-calibrated multipliers")
            st_module.markdown("- 10-year budget window")
            st_module.markdown("- [Full docs](https://github.com/laurencehw/fiscal-policy-calculator/blob/main/docs/METHODOLOGY.md)")

    # Export section
    st_module.markdown("---")
    with st_module.expander("📥 Export Results", expanded=True):
        years = result.baseline.years
        export_data = {
            "Year": years,
            "Static Revenue Effect ($B)": result.static_revenue_effect,
            "Static Spending Effect ($B)": result.static_spending_effect,
            "Static Deficit Effect ($B)": result.static_deficit_effect,
            "Behavioral Offset ($B)": result.behavioral_offset,
            "Final Deficit Effect ($B)": result.final_deficit_effect,
            "Low Estimate ($B)": result.low_estimate,
            "High Estimate ($B)": result.high_estimate,
        }
        if result.dynamic_effects:
            export_data["GDP Effect ($B)"] = result.dynamic_effects.gdp_level_change
            export_data["GDP Effect (%)"] = result.dynamic_effects.gdp_percent_change
            export_data["Employment (thousands)"] = result.dynamic_effects.employment_change
            export_data["Revenue Feedback ($B)"] = result.dynamic_effects.revenue_feedback

        df_export = pd.DataFrame(export_data)
        meta_header = (
            f"# Policy: {policy.name}\n"
            f"# Export Date: {date.today().isoformat()}\n"
            f"# Model Version: 1.0.0\n"
            f"# Baseline: CBO Feb 2026\n"
            f"# Methodology: Static + behavioral scoring with FRB/US-calibrated dynamic effects\n"
            f"#\n"
        )
        csv_data = meta_header + df_export.to_csv(index=False)

        col1, col2, col3 = st_module.columns(3)

        with col1:
            st_module.download_button(
                label="📊 Download as CSV",
                data=csv_data,
                file_name="fiscal_results_{}.csv".format(
                    re.sub(r"[^\w\-]", "_", policy.name).strip("_").lower()
                ),
                mime="text/csv",
            )

        with col2:
            share_url = build_share_url(result_data=result_data)
            share_btn = st_module.button(
                "🔗 Generate share link",
                key=f"share_btn_{policy.name.replace(' ', '_')}",
                help="Generate a deep link for supported preset tax proposals and preset spending programs.",
            )
            if share_btn:
                if share_url:
                    st_module.code(share_url, language=None)
                    st_module.caption(
                        "Opening this link restores the supported preset configuration and runs the calculation automatically."
                    )
                else:
                    st_module.info(
                        "Share links currently support preset tax proposals and preset spending programs. "
                        "Custom policies and microsimulation results still require local export."
                    )

        # Generate formatted text summary for copy-paste
        baseline_year = result.baseline.start_year
        cbo_vintage = "CBO Feb 2026"
        today = date.today().strftime("%B %d, %Y")

        text_summary = f"""FISCAL POLICY IMPACT ANALYSIS
Policy: {policy.name}
Baseline: {cbo_vintage}
Date: {today}

10-Year Deficit Impact: ${final_deficit_total:+,.1f}B
  Static Revenue Effect: ${static_deficit_total:+,.1f}B
  Behavioral Offset: ${behavioral_total:+,.1f}B
  Revenue Feedback: ${dynamic_revenue_feedback_total:+,.1f}B

Year-by-Year Breakdown:
"""
        for year, deficit_impact in zip(result.years, result.final_deficit_effect):
            text_summary += f"  {year}: ${deficit_impact:+,.1f}B\n"

        text_summary += "\nAssumptions:\n"
        if hasattr(policy, "taxable_income_elasticity"):
            text_summary += f"  Elasticity of Taxable Income (ETI): {policy.taxable_income_elasticity}\n"
        if hasattr(policy, "rate_change"):
            text_summary += f"  Rate Change: {policy.rate_change * 100:+.2f}pp\n"
        if hasattr(policy, "affected_income_threshold"):
            text_summary += f"  Income Threshold: ${policy.affected_income_threshold:,.0f}\n"

        text_summary += f"\nData Sources:\n  - IRS Statistics of Income (2022)\n  - FRED Economic Data\n  - CBO Baseline (FY{baseline_year})\n"
        text_summary += "\nMethodology: Static + behavioral scoring with FRB/US-calibrated dynamic effects\n"

        with col3:
            st_module.download_button(
                label="📄 Download as Text",
                data=text_summary,
                file_name="fiscal_summary_{}.txt".format(
                    re.sub(r"[^\w\-]", "_", policy.name).strip("_").lower()
                ),
                mime="text/plain",
            )

        st_module.markdown("---")
        st_module.subheader("Copy Summary for Reports")
        st_module.caption("Select all text below and copy to paste into documents:")

        st_module.code(text_summary, language="text")

    # Side-by-side comparison
    st_module.markdown("---")
    st_module.subheader("Compare to another proposal")

    compare_presets = list(cbo_score_map.keys())
    if compare_presets:
        compare_choice = st_module.selectbox(
            "Select a proposal to compare against",
            options=["(none)", *compare_presets],
            key="compare_policy_select",
            help="See how this policy's fiscal impact compares to another.",
        )

        if compare_choice != "(none)":
            compare_data = cbo_score_map[compare_choice]
            compare_official = compare_data["official_score"]

            c1, c2, c3 = st_module.columns(3)
            with c1:
                st_module.markdown("**Current policy**")
                st_module.metric(
                    policy.name,
                    f"${final_deficit_total:+,.0f}B",
                )
            with c2:
                st_module.markdown("**Comparison**")
                st_module.metric(
                    compare_choice,
                    f"${compare_official:+,.0f}B",
                    help=f"Official {compare_data['source']} estimate",
                )
            with c3:
                delta = final_deficit_total - compare_official
                st_module.markdown("**Difference**")
                st_module.metric(
                    "Net difference",
                    f"${delta:+,.0f}B",
                    delta=f"{'More costly' if delta > 0 else 'Less costly'}",
                    delta_color="inverse" if delta > 0 else "normal",
                )

    # Sensitivity analysis (only for individual income tax policies)
    st_module.markdown("---")
    with st_module.expander("Sensitivity analysis"):
        # Only show ETI sensitivity for individual income tax policies
        is_individual_tax = (
            hasattr(policy, "rate_change")
            and policy.rate_change != 0
            and hasattr(policy, "policy_type")
            and str(getattr(policy.policy_type, "value", "")) == "income_tax"
        )

        if is_individual_tax:
            st_module.markdown(
                "How would results change with different behavioral assumptions? "
                "The Elasticity of Taxable Income (ETI) is the most influential "
                "parameter for individual income tax policies."
            )

            eti_values = [0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50]
            sensitivity_data = []

            for eti_val in eti_values:
                base_eti = getattr(policy, "taxable_income_elasticity", 0.25)
                if base_eti > 0:
                    scale = eti_val / base_eti
                else:
                    scale = 1.0
                adjusted_behavioral = behavioral_total * scale
                adjusted_final = (
                    static_deficit_total + adjusted_behavioral
                    - dynamic_revenue_feedback_total
                )
                sensitivity_data.append({
                    "ETI": eti_val,
                    "10-Year Impact ($B)": round(adjusted_final, 1),
                    "vs. Central": f"${adjusted_final - final_deficit_total:+,.0f}B",
                })

            df_sensitivity = pd.DataFrame(sensitivity_data)
            st_module.dataframe(
                df_sensitivity, hide_index=True, use_container_width=True
            )
            st_module.caption(
                "This is a simplified linear projection — actual model results "
                "may differ due to bracket effects and interaction terms. "
                "Central estimate uses ETI = 0.25 (Saez et al. 2012)."
            )
        else:
            st_module.info(
                "Sensitivity analysis is available for policies with rate "
                "changes. Preset policies use pre-calibrated models where "
                "ETI sensitivity is embedded in the calibration."
            )
