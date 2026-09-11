"""
Helpers for mapping fiscal policy scores into macro model scenarios.
"""

import numpy as np

from .macro_adapter_core import MacroScenario


def policy_to_scenario(
    policy,
    scoring_result,
    scenario_name: str | None = None,
) -> MacroScenario:
    """
    Convert a scored fiscal policy to a MacroScenario.

    Args:
        policy: Policy object (TaxPolicy, SpendingPolicy, etc.)
        scoring_result: ScoringResult from FiscalPolicyScorer
        scenario_name: Optional name for the scenario

    Returns:
        MacroScenario ready for macro model simulation
    """
    if scenario_name is None:
        scenario_name = policy.name

    # Extract fiscal paths from scoring result
    # Revenue changes (negative = tax cut = less revenue)
    if hasattr(scoring_result, "final_deficit_effect"):
        # Deficit effect includes behavioral adjustments
        deficit_effect = scoring_result.final_deficit_effect
    else:
        deficit_effect = np.zeros(10)

    # Split into receipts and outlays based on policy type
    policy_type = getattr(policy, "policy_type", None)

    impulse_fn = getattr(policy, "macro_demand_impulse", None)
    if callable(impulse_fn):
        # A policy that knows its own demand impulse supplies it, because for
        # some instruments the impulse is not the budget effect. A tariff is
        # the case that motivated this (lane H8): the duty-inclusive price
        # rises by the whole tariff while the Treasury collects only
        # `tau/(1+tau)` of it, and the imports that stop arriving cost surplus
        # and raise no duty at all, so the real income withdrawn exceeds the
        # receipts booked -- by 68% for the 10% universal preset. Every other
        # policy family defines no such method and takes the branch below
        # unchanged.
        impulse = float(impulse_fn())
        receipts_change = np.full(len(deficit_effect), impulse, dtype=float)
        outlays_change = np.zeros_like(receipts_change)
    elif policy_type and "SPENDING" in str(policy_type.name):
        # Spending policy - affects outlays
        outlays_change = deficit_effect  # Higher deficit = more spending
        receipts_change = np.zeros_like(deficit_effect)
    else:
        # Tax policy - affects receipts
        receipts_change = -deficit_effect  # Deficit increase = revenue loss
        outlays_change = np.zeros_like(deficit_effect)

    return MacroScenario(
        name=scenario_name,
        description=f"Dynamic scoring scenario for {policy.name}",
        start_year=getattr(policy, "start_year", 2025),
        horizon_years=len(deficit_effect),
        receipts_change=receipts_change,
        outlays_change=outlays_change,
    )


__all__ = ["policy_to_scenario"]
