"""
Deficit target tool — build a policy package to hit a fiscal target.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go


def render_deficit_target_tab(
    st_module: Any,
    preset_policies: dict[str, dict[str, Any]],
    cbo_score_map: dict[str, dict[str, Any]],
    create_policy_from_preset_fn: Any,
    fiscal_policy_scorer_cls: Any,
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

    # Build policy menu grouped by category — only show policies with CBO scores
    # so we can compute the impact
    scorable_policies = {}
    for name, data in cbo_score_map.items():
        score = data.get("official_score", 0)
        if score != 0:
            scorable_policies[name] = score

    # Group by rough category using emoji prefix
    categories: dict[str, list[tuple[str, float]]] = {}
    for name, score in scorable_policies.items():
        # Determine category from emoji or first word
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
        with st_module.expander(f"**{cat_name}** ({len(policies)} options)", expanded=False):
            for policy_name, score in policies:
                direction = "raises" if score < 0 else "costs"
                label = f"{policy_name} — {direction} \\${abs(score):,.0f}B"
                if st_module.checkbox(label, key=f"dt_{policy_name}"):
                    selected_policies.append(policy_name)
                    total_impact += score

    # Calculate results
    st_module.markdown("---")

    # Get baseline
    scorer = fiscal_policy_scorer_cls(use_real_data=False)
    baseline = scorer.baseline
    baseline_deficit_yr1 = float(baseline.deficit[0])
    baseline_gdp_yr1 = float(baseline.nominal_gdp[0])
    baseline_deficit_pct = baseline_deficit_yr1 / baseline_gdp_yr1 * 100

    # Compute adjusted deficit
    # total_impact is 10-year; annual is /10
    annual_impact = total_impact / 10
    adjusted_deficit = baseline_deficit_yr1 + annual_impact  # positive score = more deficit
    adjusted_pct = adjusted_deficit / baseline_gdp_yr1 * 100

    if target_type == "Deficit as % of GDP":
        target_deficit = target_value / 100 * baseline_gdp_yr1
        target_label = f"{target_value}% of GDP"
    else:
        target_deficit = target_value
        target_label = f"\\${target_value:,}B"

    remaining = adjusted_deficit - target_deficit

    # Summary metrics
    c1, c2, c3, c4 = st_module.columns(4)
    with c1:
        st_module.metric(
            "Baseline deficit",
            f"\\${baseline_deficit_yr1:,.0f}B",
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
            f"\\${adjusted_deficit:,.0f}B",
            delta=f"{adjusted_pct:.1f}% of GDP",
            delta_color="off",
        )
    with c4:
        if remaining <= 0:
            st_module.metric(
                "Target status",
                "Target met!",
                delta=f"\\${abs(remaining):,.0f}B surplus",
                delta_color="normal",
            )
        else:
            st_module.metric(
                "Remaining gap",
                f"\\${remaining:,.0f}B",
                delta="More cuts needed",
                delta_color="inverse",
            )

    # Progress bar
    if baseline_deficit_yr1 > target_deficit:
        progress = max(
            0,
            min(
                1.0,
                (baseline_deficit_yr1 - adjusted_deficit)
                / (baseline_deficit_yr1 - target_deficit),
            ),
        )
    else:
        progress = 1.0
    st_module.progress(progress, text=f"Progress toward {target_label}: {progress * 100:.0f}%")

    # Waterfall chart
    if selected_policies:
        labels = ["Baseline"]
        values: list[float] = [baseline_deficit_yr1]
        measures = ["absolute"]

        for pname in selected_policies:
            score = scorable_policies.get(pname, 0)
            annual = score / 10
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
        # Add target line
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
            yaxis_title="Annual Deficit (\\$B)",
            xaxis_tickangle=-45,
            showlegend=False,
        )
        st_module.plotly_chart(fig, use_container_width=True)

    # Selected policies table
    if selected_policies:
        st_module.subheader("Selected policies")
        rows = []
        for pname in selected_policies:
            score = scorable_policies.get(pname, 0)
            source = cbo_score_map.get(pname, {}).get("source", "")
            rows.append(
                {
                    "Policy": pname,
                    "10-Year Impact": f"\\${score:+,.0f}B",
                    "Annual": f"\\${score / 10:+,.0f}B",
                    "Source": source,
                }
            )
        st_module.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
