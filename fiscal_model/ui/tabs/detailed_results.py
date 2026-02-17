"""
Detailed results tab renderer.
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd


def render_detailed_results_tab(st_module: Any, result_data: dict[str, Any]) -> None:
    """
    Render detailed results tab content.
    """
    if result_data.get("is_microsim"):
        st_module.header("📋 Detailed Results")
        st_module.info("Microsimulation results are displayed in the Results Summary tab.")
        return

    policy = result_data["policy"]
    result = result_data["result"]
    is_spending_result = result_data.get("is_spending", False)

    policy_rate_change = getattr(policy, "rate_change", 0) * 100
    policy_threshold = getattr(policy, "affected_income_threshold", 0)
    policy_duration = getattr(policy, "duration_years", 10)
    policy_phase_in = getattr(policy, "phase_in_years", 0)
    policy_data_year = getattr(policy, "data_year", 2022)

    static_total = result.static_revenue_effect.sum()
    behavioral_total = result.behavioral_offset.sum()
    net_total = static_total + behavioral_total
    year1_net = result.static_revenue_effect[0] + result.behavioral_offset[0]
    years = result.baseline.years

    st_module.header("📋 Detailed Results")
    st_module.subheader("Policy Details")

    policy_details = {
        "Policy Name": policy.name,
        "Description": policy.description,
        "Policy Type": policy.policy_type.value,
    }

    if not is_spending_result and policy_rate_change != 0:
        policy_details["Rate Change"] = f"{policy_rate_change:+.1f} percentage points"
    if not is_spending_result and policy_threshold > 0:
        policy_details["Income Threshold"] = f"${policy_threshold:,}"

    policy_details["Duration"] = f"{policy_duration} years"
    if policy_phase_in > 0:
        policy_details["Phase-in Period"] = f"{policy_phase_in} years"
    policy_details["Data Year"] = policy_data_year

    st_module.table(pd.DataFrame.from_dict(policy_details, orient="index", columns=["Value"]))

    st_module.markdown("---")
    st_module.subheader("Year-by-Year Breakdown")

    detailed_df = pd.DataFrame(
        {
            "Year": years,
            "Static Revenue Effect ($B)": [f"${x:.2f}" for x in result.static_revenue_effect],
            "Behavioral Offset ($B)": [f"${x:.2f}" for x in result.behavioral_offset],
            "Net Deficit Effect ($B)": [f"${x:.2f}" for x in (result.static_deficit_effect + result.behavioral_offset)],
        }
    )
    st_module.dataframe(detailed_df, use_container_width=True, hide_index=True)

    st_module.markdown("---")
    st_module.subheader("💾 Export Results")

    col1, col2 = st_module.columns(2)
    with col1:
        csv = detailed_df.to_csv(index=False)
        st_module.download_button(
            label="📥 Download as CSV",
            data=csv,
            file_name=f"fiscal_impact_{policy.name.replace(' ', '_')}.csv",
            mime="text/csv",
        )

    with col2:
        export_data = {
            "policy": {
                "name": policy.name,
                "rate_change": policy_rate_change / 100,
                "threshold": policy_threshold,
                "duration": policy_duration,
            },
            "results": {
                "static_10yr": float(static_total),
                "behavioral_offset_10yr": float(behavioral_total),
                "net_10yr_effect": float(net_total),
                "year1_net_effect": float(year1_net),
                "by_year": detailed_df.to_dict("records"),
            },
        }

        json_str = json.dumps(export_data, indent=2)
        st_module.download_button(
            label="📥 Download as JSON",
            data=json_str,
            file_name=f"fiscal_impact_{policy.name.replace(' ', '_')}.json",
            mime="application/json",
        )
