"""
Reusable UI-facing helpers that keep app.py focused on rendering.
"""

from __future__ import annotations

from typing import Any

import numpy as np


def build_macro_scenario(policy: Any, result: Any, is_spending_policy: bool, macro_scenario_cls: Any) -> Any:
    """
    Build a MacroScenario from a scored policy result.

    Spending policy impacts map to outlays, while tax policies map to receipts.
    """
    net_revenue = result.static_revenue_effect + result.behavioral_offset
    horizon = len(net_revenue)

    if is_spending_policy:
        receipts_change = np.zeros(horizon)
        outlays_change = np.array([-net_revenue[i] for i in range(horizon)])
    else:
        receipts_change = np.array(net_revenue)
        outlays_change = np.zeros(horizon)

    return macro_scenario_cls(
        name=policy.name,
        description=f"Dynamic scoring for {policy.name}",
        start_year=int(result.baseline.years[0]),
        horizon_years=horizon,
        receipts_change=receipts_change,
        outlays_change=outlays_change,
    )


def build_scorable_policy_map(preset_policies: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """
    Index scorable preset policies by display category.
    """
    all_scorable_policies: dict[str, dict[str, Any]] = {}

    category_flags = [
        ("is_tcja", "TCJA"),
        ("is_corporate", "Corporate"),
        ("is_credit", "Tax Credits"),
        ("is_estate", "Estate Tax"),
        ("is_payroll", "Payroll Tax"),
        ("is_amt", "AMT"),
        ("is_ptc", "Premium Tax Credits"),
        ("is_expenditure", "Tax Expenditures"),
    ]

    for name, data in preset_policies.items():
        if name == "Custom Policy":
            continue

        for flag_name, category in category_flags:
            if data.get(flag_name):
                all_scorable_policies[name] = {"category": category, "data": data}
                break

    return all_scorable_policies
