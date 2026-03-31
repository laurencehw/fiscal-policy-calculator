"""
Deficit target tool — build a policy package to hit a fiscal target.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go


def render_deficit_target_tab(
    st_module: Any,
    cbo_score_map: dict[str, dict[str, Any]],
    fiscal_policy_scorer_cls: Any,
    use_real_data: bool = False,
) -> None:
    """Interactive deficit reduction target builder."""

    st_module.header("Deficit Reduction Planner")
    st_module.markdown(
        "Build a package of policies to bring the deficit below a target. "
        "The baseline CBO projection shows deficits of ~\\$1.4-1.7 trillion/year "
        "(4-5% of GDP) over the next decade."
    )

    # Target selector
    col_target, col_metric = st_module.columns(2)
    with col_target:
        target_type = st_module.radio(
            "Target metric",
            ["Deficit as % of GDP", "Deficit in dollars"],
            horizontal=True,
        )
    with col_metric:
        if target_type == "Deficit as % of GDP":
            target_value = st_module.slider(
                "Target deficit (% of GDP)",
                min_value=0.0,
                max_value=6.0,
                value=3.0,
                step=0.5,
                help="Current: ~4.8%. Economists often cite 3% as sustainable.",
            )
        else:
            target_value = st_module.slider(
                "Target deficit (\\$B/year)",
                min_value=0,
                max_value=2000,
                value=1000,
                step=100,
                help="Current: ~\\$1,400B/year.",
            )

    st_module.markdown("---")
    st_module.subheader("Select policies for your package")
    st_module.markdown(
        "Check the policies you'd like to include. "
        "The chart below updates to show progress toward your target."
    )

    # Build policy menu grouped by category
    scorable_policies: dict[str, float] = {}
    for name, data in cbo_score_map.items():
        score = data.get("official_score", 0)
        if score != 0:
            scorable_policies[name] = score

    # Group by rough category using emoji prefix
    categories: dict[str, list[tuple[str, float]]] = {}
    for name, score in scorable_policies.items():
        if name.startswith("\U0001f3db"):
            cat = "TCJA / Individual"
        elif name.startswith("\U0001f3e2"):
            cat = "Corporate"
        elif name.startswith("\U0001f30d"):
            cat = "International"
        elif name.startswith("\U0001f476") or name.startswith("\U0001f4bc"):
            cat = "Tax Credits"
        elif name.startswith("\U0001f3e0"):
            cat = "Estate"
        elif name.startswith("\U0001f4b0"):
            cat = "Payroll / SS"
        elif name.startswith("\u2696"):
            cat = "AMT"
        elif name.startswith("\U0001f3e5"):
            cat = "Healthcare"
        elif name.startswith("\U0001f4cb"):
            cat = "Tax Expenditures"
        elif name.startswith("\U0001f50d"):
            cat = "IRS Enforcement"
        elif name.startswith("\U0001f48a"):
            cat = "Drug Pricing"
        elif name.startswith("\U0001f3ed"):
            cat = "Trade / Tariffs"
        elif name.startswith("\U0001f331"):
            cat = "Climate / Energy"
        else:
            cat = "Other"
        categories.setdefault(cat, []).append((name, score))

    # Display checkboxes by category
    selected_policies: list[str] = []
    total_impact = 0.0

    for cat_name, policies in sorted(categories.items()):
        with st_module.expander(
            f"**{cat_name}** ({len(policies)} options)", expanded=False
        ):
            for policy_name, score in policies:
                direction = "reduces deficit by" if score < 0 else "increases deficit by"
                label = f"{policy_name} — {direction} \\${abs(score):,.0f}B"
                if st_module.checkbox(label, key=f"dt_{policy_name}"):
                    selected_policies.append(policy_name)
                    total_impact += score

    # Warn about overlapping policies
    _overlap_groups = {
        "Biden International Package": ["Biden GILTI Reform", "Repeal FDII"],
    }
    for package, components in _overlap_groups.items():
        pkg_selected = any(package in p for p in selected_policies)
        component_selected = [c for c in components if any(c in p for p in selected_policies)]
        if pkg_selected and component_selected:
            st_module.warning(
                f"**Overlap detected:** You selected both the *{package}* "
                f"and its component(s) ({', '.join(component_selected)}). "
                f"The package already includes these — selecting both double-counts."
            )

    # Calculate results
    st_module.markdown("---")

    # Get baseline — use 10-year average for more accurate comparison
    scorer = fiscal_policy_scorer_cls(use_real_data=use_real_data)
    baseline = scorer.baseline

    if len(baseline.deficit) == 0 or len(baseline.nominal_gdp) == 0:
        st_module.error("Baseline data unavailable.")
        return

    baseline_deficit_avg = float(baseline.deficit.mean())
    baseline_gdp_avg = float(baseline.nominal_gdp.mean())
    baseline_deficit_pct = (
        baseline_deficit_avg / baseline_gdp_avg * 100
        if baseline_gdp_avg > 0
        else 0.0
    )

    # Compute adjusted deficit using 10-year averages
    annual_impact = total_impact / len(baseline.years)
    adjusted_deficit = baseline_deficit_avg + annual_impact
    adjusted_pct = (
        adjusted_deficit / baseline_gdp_avg * 100 if baseline_gdp_avg > 0 else 0.0
    )

    if target_type == "Deficit as % of GDP":
        target_deficit = target_value / 100 * baseline_gdp_avg
        target_label = f"{target_value}% of GDP"
    else:
        target_deficit = float(target_value)
        target_label = f"\\${target_value:,}B"

    remaining = adjusted_deficit - target_deficit

    # Summary metrics
    c1, c2, c3, c4 = st_module.columns(4)
    with c1:
        st_module.metric(
            "Avg baseline deficit",
            f"\\${baseline_deficit_avg:,.0f}B/yr",
            delta=f"{baseline_deficit_pct:.1f}% of GDP",
            delta_color="off",
        )
    with c2:
        st_module.metric(
            "Your package (10yr)",
            f"\\${total_impact:+,.0f}B",
            delta=f"{len(selected_policies)} policies",
            delta_color="off",
        )
    with c3:
        st_module.metric(
            "Adjusted deficit",
            f"\\${adjusted_deficit:,.0f}B/yr",
            delta=f"{adjusted_pct:.1f}% of GDP",
            delta_color="off",
        )
    with c4:
        if remaining <= 0:
            st_module.metric(
                "Target status",
                "Target met!",
                delta=f"\\${abs(remaining):,.0f}B below target",
                delta_color="normal",
            )
        else:
            st_module.metric(
                "Remaining gap",
                f"\\${remaining:,.0f}B/yr",
                delta="More cuts needed",
                delta_color="inverse",
            )

    # Progress bar
    denominator = baseline_deficit_avg - target_deficit
    if denominator > 0:
        progress = max(
            0.0,
            min(1.0, (baseline_deficit_avg - adjusted_deficit) / denominator),
        )
    else:
        progress = 1.0
    st_module.progress(
        progress, text=f"Progress toward {target_label}: {progress * 100:.0f}%"
    )

    # Waterfall chart
    if selected_policies:
        labels = ["Baseline"]
        values: list[float] = [baseline_deficit_avg]
        measures = ["absolute"]

        for pname in selected_policies:
            score = scorable_policies.get(pname, 0)
            annual = score / len(baseline.years)
            labels.append(pname[:30] + "..." if len(pname) > 30 else pname)
            values.append(annual)
            measures.append("relative")

        labels.append("Adjusted")
        values.append(adjusted_deficit)
        measures.append("total")

        fig = go.Figure(
            go.Waterfall(
                orientation="v",
                measure=measures,
                x=labels,
                y=values,
                text=[
                    f"\\${v:+,.0f}B" if m == "relative" else f"\\${v:,.0f}B"
                    for v, m in zip(values, measures)
                ],
                textposition="outside",
                increasing={"marker": {"color": "#dc3545"}},
                decreasing={"marker": {"color": "#28a745"}},
                totals={"marker": {"color": "#1f77b4"}},
            )
        )
        fig.add_hline(
            y=target_deficit,
            line_dash="dash",
            line_color="orange",
            annotation_text=f"Target: {target_label}",
            annotation_position="top right",
        )
        fig.update_layout(
            margin=dict(l=20, r=20, t=40, b=100),
            height=400,
            yaxis_title="Average Annual Deficit (\\$B)",
            xaxis_tickangle=-45,
            showlegend=False,
        )
        st_module.plotly_chart(fig, use_container_width=True)

    # Selected policies table (use plain $ — st.dataframe renders raw text, not markdown)
    if selected_policies:
        n_years = len(baseline.years)
        st_module.subheader("Selected policies")
        rows = []
        for pname in selected_policies:
            score = scorable_policies.get(pname, 0)
            source = cbo_score_map.get(pname, {}).get("source", "")
            rows.append(
                {
                    "Policy": pname,
                    "10-Year Impact": f"${score:+,.0f}B",
                    "Annual": f"${score / n_years:+,.0f}B",
                    "Source": source,
                }
            )
        df_table = pd.DataFrame(rows)
        st_module.dataframe(df_table, hide_index=True, use_container_width=True)

        # CSV export
        csv_data = df_table.to_csv(index=False)
        st_module.download_button(
            label="Download package as CSV",
            data=csv_data,
            file_name="deficit_reduction_package.csv",
            mime="text/csv",
        )
