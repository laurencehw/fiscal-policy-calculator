"""
Government Budget — taxes, transfers, debt accumulation, and fiscal closure.

Government budget constraint (flow, per period):

    G_t + SS_t + r_t · B_t = T_t + ΔB_t

where:
    G   = government purchases (non-SS)
    SS  = total Social Security outlays
    r·B = interest on public debt (B = publicly held debt)
    T   = total tax revenues
    ΔB  = new debt issued (= primary deficit)

Tax revenues:
    T = τ_l · w · L + τ_ss · w · L + τ_k · r · K

Fiscal closure rules
--------------------
- 'labor_tax'  : solve for τ_l that keeps B/Y ≤ debt_target_gdp
- 'spending'   : reduce G to close the budget gap
- 'debt_accum' : let B grow without constraint
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# ---------------------------------------------------------------------------
# Dataclass for government state
# ---------------------------------------------------------------------------

@dataclass
class GovState:
    """Single-period snapshot of government finances."""
    gdp: float
    capital_stock: float
    labour: float
    r: float
    w: float
    tau_l: float
    tau_k: float
    tau_ss: float
    ss_benefit: float        # Annual benefit per retiree
    n_retirees: float        # Number of retired cohort-equivalents (weighted)
    gov_spending: float      # G (non-SS)
    debt: float              # B (publicly held)

    # Derived
    @property
    def ss_revenue(self) -> float:
        """SS payroll tax receipts."""
        return self.tau_ss * self.w * self.labour

    @property
    def ss_outlays(self) -> float:
        """Total SS benefit payments."""
        return self.ss_benefit * self.n_retirees

    @property
    def income_tax_revenue(self) -> float:
        """Labour income tax revenue."""
        return self.tau_l * self.w * self.labour

    @property
    def capital_tax_revenue(self) -> float:
        """Capital income tax revenue."""
        return self.tau_k * self.r * self.capital_stock

    @property
    def total_revenue(self) -> float:
        return self.income_tax_revenue + self.capital_tax_revenue + self.ss_revenue

    @property
    def total_outlays(self) -> float:
        return self.gov_spending + self.ss_outlays + self.r * self.debt

    @property
    def primary_surplus(self) -> float:
        """Primary surplus (revenues minus non-interest outlays)."""
        return self.total_revenue - self.gov_spending - self.ss_outlays

    @property
    def deficit(self) -> float:
        """Total deficit (= ΔB = outlays - revenues)."""
        return self.total_outlays - self.total_revenue

    @property
    def debt_gdp(self) -> float:
        return self.debt / max(self.gdp, 1e-10)


# ---------------------------------------------------------------------------
# Government calculations
# ---------------------------------------------------------------------------

def compute_ss_benefit(
    ss_replacement_rate: float,
    w: float,
) -> float:
    """
    Social Security benefit = replacement_rate × average wage.

    The replacement rate is applied to the economy-wide average wage.
    Since the earnings profile is normalised to mean 1, average wage = w.
    """
    return ss_replacement_rate * w


def compute_gov_spending(
    gov_spending_gdp: float,
    gdp: float,
) -> float:
    """Non-SS government purchases G = g̃ · Y."""
    return gov_spending_gdp * gdp


def compute_tax_revenues(
    w: float,
    L: float,
    r: float,
    K: float,
    tau_l: float,
    tau_k: float,
    tau_ss: float,
) -> float:
    """Total tax revenues (labour + capital + payroll)."""
    labour_tax = tau_l * w * L
    capital_tax = tau_k * r * K
    payroll_tax = tau_ss * w * L
    return labour_tax + capital_tax + payroll_tax


def compute_ss_outlays(
    ss_benefit: float,
    cohort_sizes: np.ndarray,
    retirement_cohort: int,
) -> float:
    """Total SS outlays = benefit × Σ_{j≥R} n_j."""
    n_retirees = float(cohort_sizes[retirement_cohort:].sum())
    return ss_benefit * n_retirees


def compute_debt_next_period(
    debt: float,
    r: float,
    gov_spending: float,
    ss_outlays: float,
    tax_revenues: float,
) -> float:
    """
    Debt accumulation:
        B_{t+1} = (1+r)·B_t + G_t + SS_t − T_t
               = B_t + deficit_t
    """
    interest = r * debt
    deficit = gov_spending + ss_outlays + interest - tax_revenues
    return debt + deficit


# ---------------------------------------------------------------------------
# Fiscal closure: endogenous labor tax
# ---------------------------------------------------------------------------

def solve_labor_tax_closure(
    w: float,
    L: float,
    r: float,
    K: float,
    tau_k: float,
    tau_ss: float,
    gov_spending: float,
    ss_outlays: float,
    debt: float,
    target_primary_surplus: float = 0.0,
) -> float:
    """
    Solve for the labour tax rate τ_l that achieves a target primary surplus.

    Primary surplus = τ_l·w·L + τ_k·r·K + τ_ss·w·L − G − SS = target

    Solving for τ_l:
        τ_l = (target + G + SS − τ_k·r·K − τ_ss·w·L) / (w·L)
    """
    exogenous_revenue = tau_k * r * K + tau_ss * w * L
    required_total = gov_spending + ss_outlays + target_primary_surplus
    required_labour_tax = required_total - exogenous_revenue
    tau_l = required_labour_tax / max(w * L, 1e-10)
    # Clamp to [0.0, 0.70] to keep economically sensible
    return float(np.clip(tau_l, 0.0, 0.70))


def compute_closure_tax_rate(
    params,
    gdp: float,
    w: float,
    L: float,
    r: float,
    K: float,
    debt: float,
    ss_outlays: float,
) -> float:
    """
    Compute the endogenous labour tax rate consistent with fiscal closure.

    Under 'labor_tax' closure, τ_l is set so that the primary surplus
    stabilises debt/GDP at or below debt_target_gdp.

    Required primary surplus to stabilise debt:
        PS* = B · (r − g)   where g ≈ pop_growth + tfp_growth

    Parameters
    ----------
    params : OLGParameters
    """
    if params.fiscal_closure == "debt_accum":
        return params.labor_tax_rate

    g = params.pop_growth + params.tfp_growth
    # Debt-stabilising primary surplus: PS = B · (r − g)
    target_ps = debt * max(r - g, 0.0)

    G = compute_gov_spending(params.gov_spending_gdp, gdp)

    if params.fiscal_closure == "labor_tax":
        tau_l = solve_labor_tax_closure(
            w=w,
            L=L,
            r=r,
            K=K,
            tau_k=params.capital_tax_rate,
            tau_ss=params.ss_payroll_rate,
            gov_spending=G,
            ss_outlays=ss_outlays,
            debt=debt,
            target_primary_surplus=target_ps,
        )
        return tau_l

    # 'spending': adjust G; return baseline tau_l
    return params.labor_tax_rate
