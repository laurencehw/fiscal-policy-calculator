"""
Detailed results renderer — the year-by-year breakdown inside the result panel.

Sign convention, as everywhere else in the app: **positive increases the
deficit**. This module used to mix conventions in a single table — it summed
``static_revenue_effect`` (revenue convention) with ``behavioral_offset``
(deficit convention) and labelled the result "Net Deficit Effect", so the
headline number and this table disagreed for every policy. Both the table and
the JSON export are now deficit-convention throughout, and the conventional
total here equals the panel headline by construction.
"""

from __future__ import annotations

import json
from typing import Any

import numpy as np
import pandas as pd

from .results_summary import ensure_summary


def render_detailed_results_tab(
    st_module: Any,
    result_data: dict[str, Any],
    scored: Any = None,
) -> None:
    """
    Render the detailed year-by-year breakdown and its exports.
    """
    if result_data.get("is_microsim"):
        st_module.header("📋 Detailed Results")
        st_module.info("Microsimulation results are displayed in the Results Summary tab.")
        return

    policy = result_data["policy"]
    result = result_data["result"]
    scored = ensure_summary(result_data, scored)
    is_spending_result = result_data.get("is_spending", False)

    policy_rate_change = getattr(policy, "rate_change", 0) * 100
    policy_threshold = getattr(policy, "affected_income_threshold", 0)
    policy_duration = getattr(policy, "duration_years", 10)
    policy_phase_in = getattr(policy, "phase_in_years", 0)
    policy_data_year = getattr(policy, "data_year", 2022)

    static_deficit = np.asarray(result.static_deficit_effect)
    behavioral = np.asarray(result.behavioral_offset)
    conventional = static_deficit + behavioral
    years = result.baseline.years

    st_module.header("📋 Detailed Results")
    st_module.caption(
        "All figures in the deficit convention: **+ increases the deficit**, "
        "− reduces it. The conventional total below is the panel headline."
    )
    st_module.subheader("Policy Details")

    policy_details = {
        "Policy Name": policy.name,
        "Description": policy.description,
        "Policy Type": policy.policy_type.value,
        "Tier": scored.tier_label,
        "Baseline": f"{scored.baseline_vintage}, {scored.window}",
        "Policy status": scored.policy_status,
    }

    if not is_spending_result and policy_rate_change != 0:
        policy_details["Rate Change"] = f"{policy_rate_change:+.1f} percentage points"
    if not is_spending_result and policy_threshold > 0:
        policy_details["Income Threshold"] = f"${policy_threshold:,}"

    policy_details["Duration"] = f"{policy_duration} years"
    if policy_phase_in > 0:
        policy_details["Phase-in Period"] = f"{policy_phase_in} years"
    # Every other entry is a string; ``data_year`` is an int, and a mixed-type
    # object column makes pyarrow fail its serialization and log a warning on
    # every render. The column is display-only, so cast it.
    policy_details["Data Year"] = "" if policy_data_year is None else str(policy_data_year)

    details_df = pd.DataFrame.from_dict(policy_details, orient="index", columns=["Value"])
    st_module.table(details_df.astype(str))

    st_module.markdown("---")
    st_module.subheader("Year-by-Year Breakdown")

    detailed_df = pd.DataFrame(
        {
            "Year": years,
            "Static Deficit Effect ($B)": [f"${value:+,.2f}" for value in static_deficit],
            "Behavioral Offset ($B)": [f"${value:+,.2f}" for value in behavioral],
            "Conventional Deficit Effect ($B)": [f"${value:+,.2f}" for value in conventional],
        }
    )
    try:
        st_module.dataframe(detailed_df, width="stretch", hide_index=True)
    except TypeError:  # pragma: no cover — older Streamlit / test fakes
        st_module.dataframe(detailed_df, hide_index=True)

    st_module.markdown("---")
    st_module.subheader("💾 Export Results")

    meta_header = (
        f"# Policy: {scored.display_name}\n"
        f"# Policy status: {scored.policy_status}\n"
        f"# Baseline vintage: {scored.baseline_vintage}\n"
        f"# Window: {scored.window}\n"
        f"# Tier: {scored.tier} ({scored.tier_label})\n"
        f"# Mode: {scored.mode}\n"
        "# Sign convention: positive = increases the deficit\n"
        "#\n"
    )

    col1, col2 = st_module.columns(2)
    with col1:
        st_module.download_button(
            label="📥 Download as CSV",
            data=meta_header + detailed_df.to_csv(index=False),
            file_name=f"fiscal_impact_{policy.name.replace(' ', '_')}.csv",
            mime="text/csv",
        )

    with col2:
        export_data = {
            "policy": {
                "name": scored.display_name,
                "status": scored.policy_status,
                "rate_change": policy_rate_change / 100,
                "threshold": policy_threshold,
                "duration": policy_duration,
            },
            "provenance": {
                "baseline_vintage": scored.baseline_vintage,
                "window": scored.window,
                "tier": scored.tier,
                "mode": scored.mode,
                "sign_convention": "positive = increases the deficit",
            },
            "results": {
                "static_deficit_10yr": float(scored.static),
                "behavioral_offset_10yr": float(scored.behavioral),
                "conventional_deficit_10yr": float(scored.headline),
                "year1_conventional_effect": float(conventional[0]),
                "by_year": detailed_df.to_dict("records"),
            },
        }
        if scored.mode == "dynamic":
            export_data["results"]["dynamic_view"] = {
                "model": scored.macro_model,
                "revenue_feedback_10yr": float(scored.feedback),
                "debt_service_10yr": float(scored.debt_service),
                "dynamic_total_10yr": float(scored.dynamic_total),
            }

        st_module.download_button(
            label="📥 Download as JSON",
            data=json.dumps(export_data, indent=2),
            file_name=f"fiscal_impact_{policy.name.replace(' ', '_')}.json",
            mime="application/json",
        )
