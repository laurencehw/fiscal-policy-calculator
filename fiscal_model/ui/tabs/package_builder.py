"""
Policy package builder tab renderer.
"""

from __future__ import annotations

import json
from typing import Any, Callable

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from ..helpers import build_scorable_policy_map


def render_policy_package_tab(
    st_module: Any,
    preset_policies: dict[str, dict[str, Any]],
    preset_packages: dict[str, dict[str, Any]],
    cbo_score_map: dict[str, dict[str, Any]],
    create_policy_from_preset: Callable[[dict[str, Any]], Any],
    fiscal_policy_scorer_cls: Any,
) -> None:
    """
    Render the Policy Package Builder tab.
    """
    st_module.header("📦 Policy Package Builder")

    st_module.markdown(
        """
    <div class="info-box">
    💡 <strong>Build comprehensive tax plans</strong> by combining multiple policies.
    See the total budget impact and breakdown by component.
    </div>
    """,
        unsafe_allow_html=True,
    )

    st_module.subheader("📋 Preset Policy Packages")

    col1, col2 = st_module.columns([1, 2])

    with col1:
        selected_package = st_module.selectbox(
            "Select a preset package",
            options=["Custom Package"] + list(preset_packages.keys()),
            help="Choose a predefined policy package or build your own",
        )

    if selected_package != "Custom Package":
        package_data = preset_packages[selected_package]
        with col2:
            st_module.info(f"**{selected_package}**: {package_data['description']}")

    st_module.markdown("---")
    st_module.subheader("🔧 Select Policies to Combine")

    all_scorable_policies = build_scorable_policy_map(preset_policies)

    if selected_package != "Custom Package":
        default_policies = preset_packages[selected_package]["policies"]
        default_policies = [p for p in default_policies if p in all_scorable_policies]
    else:
        default_policies = []

    selected_policies = st_module.multiselect(
        "Select policies to include in your package",
        options=list(all_scorable_policies.keys()),
        default=default_policies,
        help="Choose 2 or more policies to combine into a package",
    )

    if len(selected_policies) < 1:
        st_module.info("👆 Select at least 1 policy above to build a package")
        return

    st_module.markdown("---")
    st_module.subheader("📊 Package Results")

    package_results = []
    total_static = 0.0
    total_behavioral = 0.0
    total_net = 0.0

    with st_module.spinner("Calculating package impact..."):
        for policy_name in selected_policies:
            try:
                policy_info = all_scorable_policies.get(policy_name, {})
                policy_data = policy_info.get("data", {})

                policy = create_policy_from_preset(policy_data)

                if not policy:
                    continue

                scorer = fiscal_policy_scorer_cls(start_year=policy.start_year, use_real_data=False)
                result = scorer.score_policy(policy, dynamic=False)
                static = result.static_revenue_effect.sum()
                behavioral = result.behavioral_offset.sum()
                net = static + behavioral

                cbo_data = cbo_score_map.get(policy_name, {})
                official = cbo_data.get("official_score", None)

                package_results.append(
                    {
                        "name": policy_name,
                        "category": policy_info.get("category", "Other"),
                        "static": static,
                        "behavioral": behavioral,
                        "net": net,
                        "cbo_net": -net,
                        "official": official,
                    }
                )

                total_static += static
                total_behavioral += behavioral
                total_net += net

            except Exception as e:
                st_module.warning(f"Could not score {policy_name}: {e}")

    if not package_results:
        return

    col1, col2, col3, col4 = st_module.columns(4)
    total_cbo = -total_net

    with col1:
        st_module.metric(
            "Package Total (10-yr)",
            f"${total_cbo:,.0f}B",
            delta="Cost" if total_cbo > 0 else "Revenue",
            delta_color="inverse" if total_cbo > 0 else "normal",
        )

    with col2:
        st_module.metric(
            "Policies Included",
            f"{len(package_results)}",
        )

    with col3:
        avg_annual = total_cbo / 10
        st_module.metric(
            "Average Annual",
            f"${avg_annual:,.0f}B/yr",
        )

    with col4:
        if selected_package != "Custom Package":
            official_total = preset_packages[selected_package]["official_total"]
            error = ((total_cbo - official_total) / abs(official_total) * 100) if official_total != 0 else 0
            st_module.metric(
                "vs Official Est.",
                f"${official_total:,.0f}B",
                delta=f"{error:+.1f}% diff",
                delta_color="off",
            )

    st_module.markdown("---")
    st_module.subheader("📋 Component Breakdown")

    df_components = pd.DataFrame(package_results).copy()
    df_components.loc[:, "10-Year Impact"] = df_components["cbo_net"].apply(lambda x: f"${x:,.0f}B")
    df_components.loc[:, "Official Score"] = df_components["official"].apply(
        lambda x: f"${x:,.0f}B" if x is not None else "N/A"
    )
    df_components.loc[:, "Category"] = df_components["category"]
    df_components.loc[:, "Policy"] = df_components["name"]

    st_module.dataframe(
        df_components[["Policy", "Category", "10-Year Impact", "Official Score"]],
        use_container_width=True,
        hide_index=True,
    )

    st_module.subheader("📊 Visual Breakdown")

    fig_waterfall = go.Figure()
    df_sorted = df_components.sort_values("cbo_net", ascending=True)
    colors = ["#d62728" if x > 0 else "#2ca02c" for x in df_sorted["cbo_net"]]

    fig_waterfall.add_trace(
        go.Bar(
            y=df_sorted["name"],
            x=df_sorted["cbo_net"],
            orientation="h",
            marker_color=colors,
            text=df_sorted["10-Year Impact"],
            textposition="auto",
        )
    )

    fig_waterfall.update_layout(
        title="Policy Package Components (10-Year Impact)",
        xaxis_title="Budget Impact ($B, CBO Convention: + = Cost, - = Revenue)",
        height=max(300, len(package_results) * 50),
        showlegend=False,
    )

    st_module.plotly_chart(fig_waterfall, use_container_width=True)

    col1, col2 = st_module.columns(2)

    with col1:
        costs = df_components[df_components["cbo_net"] > 0]
        revenues = df_components[df_components["cbo_net"] < 0]

        if not costs.empty:
            fig_costs = px.pie(
                costs,
                values=costs["cbo_net"].abs(),
                names="name",
                title="Cost Components (Deficit Increases)",
                color_discrete_sequence=px.colors.sequential.Reds,
            )
            st_module.plotly_chart(fig_costs, use_container_width=True)
        else:
            st_module.info("No cost components in this package")

    with col2:
        if not revenues.empty:
            fig_revenues = px.pie(
                revenues,
                values=revenues["cbo_net"].abs(),
                names="name",
                title="Revenue Components (Deficit Decreases)",
                color_discrete_sequence=px.colors.sequential.Greens,
            )
            st_module.plotly_chart(fig_revenues, use_container_width=True)
        else:
            st_module.info("No revenue components in this package")

    st_module.markdown("---")
    st_module.subheader("📤 Export Package")

    export_data = {
        "package_name": selected_package,
        "total_10_year_impact_billions": total_cbo,
        "average_annual_billions": total_cbo / 10,
        "num_policies": len(package_results),
        "components": [
            {
                "policy": r["name"],
                "category": r["category"],
                "impact_billions": r["cbo_net"],
                "official_score": r["official"],
            }
            for r in package_results
        ],
    }

    col1, col2 = st_module.columns(2)
    with col1:
        st_module.download_button(
            "📥 Download as JSON",
            data=json.dumps(export_data, indent=2),
            file_name=f"policy_package_{selected_package.replace(' ', '_')}.json",
            mime="application/json",
        )

    with col2:
        csv_data = df_components[["Policy", "Category", "cbo_net", "official"]].copy()
        csv_data.columns = ["Policy", "Category", "10-Year Impact ($B)", "Official Score ($B)"]
        st_module.download_button(
            "📥 Download as CSV",
            data=csv_data.to_csv(index=False),
            file_name=f"policy_package_{selected_package.replace(' ', '_')}.csv",
            mime="text/csv",
        )
