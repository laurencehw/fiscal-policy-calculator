"""
SALT (State and Local Tax) deduction interaction model.

The federal SALT deduction allows itemizing taxpayers to deduct state and local
taxes from federal taxable income, creating an implicit federal subsidy to
state-level taxation.  TCJA (2017) capped this deduction at $10,000; P.L. 119-21
sec. 70120 raised the cap to $40,000 for 2025-2029, phased down for incomes above
$500,000, before it returns to $10,000 in 2030.

``compute_salt_lift`` prices lifting the cap against that current-law path,
filer by filer through IRS SOI Table 2.1's SALT distribution.
``compute_salt_interaction`` is the older representative-itemizer method and
takes both caps as arguments.

Key calculations:
- For itemizing filers: federal_taxable_income -= min(actual_salt, salt_cap)
- Eliminating/raising the cap → more SALT deducted → lower federal taxable income
  → lower federal revenue (but lower effective state tax burden to the filer)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

import pandas as pd

from .database import StateTaxDatabase

if TYPE_CHECKING:
    from fiscal_model.tax_expenditures_core import SaltCapBaseline


@dataclass
class SALTInteractionResult:
    """Results from a SALT cap change analysis."""

    state: str
    baseline_cap: float | None        # None = uncapped
    reform_cap: float | None          # None = uncapped
    affected_filers: float            # Millions of filers whose deduction changes
    avg_deduction_change: float       # Average change in SALT deduction per affected filer ($)
    total_deduction_change_billions: float  # Total change in SALT deductions ($B)
    federal_revenue_change_billions: float  # Revenue effect (positive = revenue gain)
    effective_rate_change: float      # Change in effective marginal state tax burden (pp)

    @property
    def description(self) -> str:
        def cap_str(c):
            return f"${c:,.0f}" if c is not None else "uncapped"
        return (
            f"SALT cap {cap_str(self.baseline_cap)} → {cap_str(self.reform_cap)}: "
            f"{self.affected_filers:.1f}M filers, "
            f"${self.total_deduction_change_billions:.1f}B deduction change, "
            f"${self.federal_revenue_change_billions:.1f}B revenue effect"
        )


def compute_salt_interaction(
    state: str,
    baseline_cap: float | None = 10_000,
    reform_cap: float | None = None,
    federal_marginal_rate: float = 0.24,
    year: int = 2025,
    db: StateTaxDatabase | None = None,
) -> SALTInteractionResult:
    """
    Estimate the federal revenue effect of changing the SALT cap for a given state.

    Args:
        state: 2-letter state code
        baseline_cap: Current SALT cap ($). None = uncapped (pre-TCJA law).
        reform_cap: Proposed SALT cap ($). None = uncapped.
        federal_marginal_rate: Weighted average marginal federal rate for itemizers.
            Default 24% (roughly correct for high-income itemizers).
        year: Tax year
        db: Optional pre-loaded StateTaxDatabase (avoids repeated I/O)

    Returns:
        SALTInteractionResult with revenue and deduction change estimates.

    Methodology:
        1. Average SALT deduction per itemizer (from data) is used as a proxy
           for actual state taxes paid.
        2. Capped deduction = min(avg_salt, cap)
        3. Change in deduction = capped_baseline - capped_reform
        4. Revenue effect = change_in_deduction * num_itemizers * fed_marginal_rate
        5. Affected filers = those whose actual SALT exceeds the lower of the two caps.
    """
    if db is None:
        db = StateTaxDatabase(year)

    profile = db.get_state(state)

    # Approximate number of filers from IRS SOI data (rough: pct_itemizers * total filers)
    # We use total filers ≈ median_household_income / 60000 * population_scale
    # Better: use hardcoded approximate filer counts for top-10 states
    approx_filers_millions = _approx_filers_millions(state)
    itemizer_filers = approx_filers_millions * profile.pct_itemizers

    avg_salt = profile.avg_salt_deduction_itemizers  # Average SALT among itemizers

    # Capped deductions under baseline and reform
    def capped(amt: float, cap: float | None) -> float:
        return min(amt, cap) if cap is not None else amt

    deduction_baseline = capped(avg_salt, baseline_cap)
    deduction_reform = capped(avg_salt, reform_cap)

    avg_deduction_change = deduction_reform - deduction_baseline  # + means more deduction

    # Filers affected = those whose actual SALT exceeds the lower cap
    lower_cap = min(
        baseline_cap if baseline_cap is not None else float("inf"),
        reform_cap if reform_cap is not None else float("inf"),
    )
    # Rough estimate: fraction of itemizers with SALT > lower_cap
    # We assume SALT deductions are roughly log-normally distributed around the mean
    if lower_cap == float("inf"):
        affected_fraction = 1.0
    elif avg_salt > 0:
        affected_fraction = min(1.0, avg_salt / lower_cap * 0.65)  # heuristic scaling
    else:
        affected_fraction = 0.0

    affected_filers = itemizer_filers * affected_fraction

    total_deduction_change_billions = (
        avg_deduction_change * affected_filers * 1e6 / 1e9  # M filers * $ / 1e9 = $B
    )

    # Federal revenue changes in the opposite direction of deduction change
    # More deduction → less taxable income → less federal revenue
    federal_revenue_change_billions = (
        -total_deduction_change_billions * federal_marginal_rate
    )

    # Effective burden change on state filers:
    # When SALT cap is lifted, state tax is effectively subsidized by federal deduction
    # The subsidy = state_tax_rate * federal_marginal_rate
    subsidy_baseline = profile.effective_salt_rate * federal_marginal_rate * (
        deduction_baseline / avg_salt if avg_salt > 0 else 0
    )
    subsidy_reform = profile.effective_salt_rate * federal_marginal_rate * (
        deduction_reform / avg_salt if avg_salt > 0 else 0
    )
    effective_rate_change = -(subsidy_reform - subsidy_baseline)  # pp change in net state burden

    return SALTInteractionResult(
        state=state,
        baseline_cap=baseline_cap,
        reform_cap=reform_cap,
        affected_filers=affected_filers,
        avg_deduction_change=avg_deduction_change,
        total_deduction_change_billions=total_deduction_change_billions,
        federal_revenue_change_billions=federal_revenue_change_billions,
        effective_rate_change=effective_rate_change,
    )


def compute_salt_across_states(
    baseline_cap: float | None = 10_000,
    reform_cap: float | None = None,
    federal_marginal_rate: float = 0.24,
    year: int = 2025,
) -> pd.DataFrame:
    """
    Compute SALT interaction results for all supported states.

    Returns a DataFrame with one row per state, sorted by federal revenue impact.
    """
    from .database import SUPPORTED_STATES

    db = StateTaxDatabase(year)
    records = []
    for state in SUPPORTED_STATES:
        result = compute_salt_interaction(
            state=state,
            baseline_cap=baseline_cap,
            reform_cap=reform_cap,
            federal_marginal_rate=federal_marginal_rate,
            year=year,
            db=db,
        )
        records.append({
            "State": state,
            "State Name": _state_name(state),
            "Avg SALT (itemizers)": f"${result.affected_filers:.1f}M filers",
            "Affected Filers (M)": round(result.affected_filers, 2),
            "Avg Deduction Change ($)": round(result.avg_deduction_change, 0),
            "Total Deduction Change ($B)": round(result.total_deduction_change_billions, 1),
            "Federal Revenue Change ($B)": round(result.federal_revenue_change_billions, 1),
            "Effective Rate Change (pp)": round(result.effective_rate_change * 100, 2),
        })

    df = pd.DataFrame(records)
    df = df.sort_values("Federal Revenue Change ($B)")
    return df


def compute_salt_lift(
    state: str,
    year: int = 2025,
    baseline: SaltCapBaseline | None = None,
    db: StateTaxDatabase | None = None,
) -> SALTInteractionResult:
    """
    Federal cost of removing the SALT cap in one state, against ``baseline``.

    The baseline defaults to current law (``SaltCapBaseline.CURRENT_LAW``):
    $40,000 in 2025, indexed at 1% a year through 2029 and phased down by 30%
    of income above $500,000 (never below $10,000), then $10,000 from 2030.

    A representative itemizer cannot see that cap: the state averages here are
    all below $40,000, so ``compute_salt_interaction`` would report no effect
    at all, while the cap binds on the high-SALT tail and on every filer the
    phasedown reaches. This method keeps the tail. Each state's itemizers take
    the national SOI Table 2.1 SALT distribution -- its AGI classes, the
    within-class lognormal dispersion and the class marginal rates -- with
    claimed amounts and incomes scaled by the state's average SALT relative to
    the national average. The national distribution is what
    ``tax_expenditures_core.salt_expenditure_billions`` prices the SALT presets
    with, so the states and the national score read the same data.

    Returns a :class:`SALTInteractionResult` with ``reform_cap=None`` and
    ``baseline_cap`` set to the limitation amount before any phasedown.
    """
    from fiscal_model.tax_expenditure_distributions import (
        _lognormal_mean_min,
        _normal_cdf,
        load_capped_deduction_distribution,
    )
    from fiscal_model.tax_expenditures_core import (
        SaltCapBaseline,
        salt_cap_at,
        salt_cap_schedule,
    )

    if baseline is None:
        baseline = SaltCapBaseline.CURRENT_LAW
    if db is None:
        db = StateTaxDatabase(year)
    profile = db.get_state(state)

    distribution = load_capped_deduction_distribution()
    national_claimants = sum(c.claimants for c in distribution.classes)
    national_mean = (
        sum(c.claimants * c.mean_deduction for c in distribution.classes)
        / national_claimants
    )
    scale = profile.avg_salt_deduction_itemizers / national_mean
    itemizers = _approx_filers_millions(state) * 1e6 * profile.pct_itemizers

    claimed = deduction_gain = revenue_cost = affected = 0.0
    for c in distribution.classes:
        mean = c.mean_deduction * scale
        sigma = c.sigma
        for weight, agi in c.agi_slices():
            filers = itemizers * (c.claimants / national_claimants) * weight
            cap = salt_cap_at(baseline, year, agi * scale)
            gain = mean - _lognormal_mean_min(mean, sigma, cap)
            claimed += filers * mean
            deduction_gain += filers * gain
            revenue_cost += filers * gain * c.marginal_rate
            if math.isinf(cap):
                continue
            if sigma:
                mu = math.log(mean) - sigma * sigma / 2.0
                affected += filers * (1.0 - _normal_cdf((math.log(cap) - mu) / sigma))
            elif mean > cap:
                affected += filers

    if baseline is SaltCapBaseline.CURRENT_LAW:
        baseline_cap: float | None = salt_cap_schedule(year).limitation_amount
    else:
        baseline_cap = salt_cap_at(baseline, year, 0.0)
        if math.isinf(baseline_cap):
            baseline_cap = None

    average_rate = revenue_cost / deduction_gain if deduction_gain > 0 else 0.0
    share_denied = deduction_gain / claimed if claimed > 0 else 0.0
    return SALTInteractionResult(
        state=state,
        baseline_cap=baseline_cap,
        reform_cap=None,
        affected_filers=affected / 1e6,
        avg_deduction_change=deduction_gain / affected if affected > 0 else 0.0,
        total_deduction_change_billions=deduction_gain / 1e9,
        federal_revenue_change_billions=-revenue_cost / 1e9,
        effective_rate_change=-profile.effective_salt_rate * average_rate * share_denied,
    )


def _approx_filers_millions(state: str) -> float:
    """Approximate total filer count for each top-10 state (millions)."""
    # Source: IRS SOI State Data, ~2022
    filers = {
        "CA": 18.2,
        "TX": 13.4,
        "FL": 10.9,
        "NY": 9.8,
        "PA": 6.3,
        "IL": 6.1,
        "OH": 5.8,
        "GA": 5.0,
        "NC": 5.0,
        "MI": 4.8,
    }
    return filers.get(state, 5.0)


def _state_name(state: str) -> str:
    from .database import STATE_NAMES
    return STATE_NAMES.get(state, state)
