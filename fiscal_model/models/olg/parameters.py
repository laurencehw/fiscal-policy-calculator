"""
OLGParameters — calibrated parameters for the 55-cohort Auerbach-Kotlikoff OLG model.

References:
  Auerbach & Kotlikoff (1987), *Dynamic Fiscal Policy*, Cambridge University Press.
  Kotlikoff (2000), "The A-K OLG Model", in *Using a New Macroeconomic Model*, NBER.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np


@dataclass
class OLGParameters:
    """
    Parameters for the Auerbach-Kotlikoff 55-cohort overlapping-generations model.

    Demographic coverage
    --------------------
    - 55 cohorts alive simultaneously (model ages 21–75)
    - Working ages 21–64 → cohort indices 0–43 (retirement_age_cohort = 44)
    - Retired ages 65–75 → cohort indices 44–54

    Calibration targets (US, 2025)
    ------------------------------
    - Capital-output ratio  K/Y ≈ 3.0    (BEA Fixed Asset Accounts)
    - Labor share          1−α = 0.65    (BEA National Income Accounts)
    - Real interest rate       r ≈ 4–5%  (long-run CBO baseline)
    - Debt/GDP ratio             ≈ 99%   (CBO February 2026)
    """

    # ------------------------------------------------------------------
    # Demographic structure
    # ------------------------------------------------------------------
    n_cohorts: int = 55
    """Number of cohorts alive simultaneously (ages 21–75)."""

    retirement_age_cohort: int = 44
    """
    Cohort index at which retirement begins.
    Age = 21 + retirement_age_cohort = 65 under the default 21–75 span.
    """

    transition_years: int = 75
    """Years on the transition path from baseline to reform steady state."""

    pop_growth: float = 0.005
    """Annual population growth rate (SSA intermediate projection, 2025–2055)."""

    # ------------------------------------------------------------------
    # Preferences — CRRA utility u(c) = c^(1−σ)/(1−σ)
    # ------------------------------------------------------------------
    sigma: float = 1.5
    """Coefficient of relative risk aversion (= inverse of IES). Standard range 1.0–2.0."""

    beta: float = 0.960
    """
    Annual household discount factor.
    Calibrated jointly with sigma and alpha so that K/Y ≈ 3 in steady state.
    """

    # ------------------------------------------------------------------
    # Production — Cobb-Douglas Y = A · K^α · L^(1−α)
    # ------------------------------------------------------------------
    alpha: float = 0.350
    """Capital income share (BEA national accounts, 2015–2024 average)."""

    delta: float = 0.050
    """Annual capital depreciation rate (BEA Fixed Asset Accounts)."""

    tfp: float = 1.000
    """Total factor productivity level (normalized to 1 in the baseline)."""

    tfp_growth: float = 0.015
    """Annual TFP growth rate (CBO potential-GDP methodology)."""

    # ------------------------------------------------------------------
    # Government fiscal parameters
    # ------------------------------------------------------------------
    labor_tax_rate: float = 0.280
    """
    Effective marginal tax rate on labor income (combined federal income +
    employer-side payroll, excluding SS payroll modelled separately).
    Source: OECD Tax Wedge; Penn Wharton OLG calibration.
    """

    capital_tax_rate: float = 0.300
    """
    Effective tax rate on capital income (corporate tax + individual dividend/
    interest/capital-gains taxes, integrated statutory approach).
    """

    ss_payroll_rate: float = 0.124
    """
    Combined employee + employer Social Security Old Age payroll tax rate.
    (12.4 pp of covered wages up to the cap; modelled as flat rate on average).
    """

    ss_replacement_rate: float = 0.400
    """
    Social Security benefit as fraction of the economy-wide average wage.
    Approximates the primary insurance amount for median earner.
    """

    gov_spending_gdp: float = 0.175
    """Non-SS government purchases as fraction of GDP (defence + non-defence disc.)."""

    initial_debt_gdp: float = 0.990
    """Initial publicly-held federal debt / GDP ratio (CBO February 2026 projection)."""

    # Fiscal closure
    fiscal_closure: str = "labor_tax"
    """
    How to satisfy the government's intertemporal budget constraint in the long run:

    - ``'labor_tax'``  : adjust τ_l endogenously to keep debt/GDP ≤ debt_target_gdp
    - ``'spending'``   : cut government purchases G proportionally
    - ``'debt_accum'`` : let debt accumulate without closure (open-ended deficit)
    """

    debt_target_gdp: float = 1.00
    """Long-run debt / GDP target under fiscal closure rules (default: hold at 100%)."""

    # ------------------------------------------------------------------
    # Age-earnings profile
    # ------------------------------------------------------------------
    earnings_profile: Optional[np.ndarray] = field(default=None, repr=False)
    """
    Labor efficiency ε_j for working-age cohorts, shape ``(retirement_age_cohort,)``.

    Hump-shaped, peaks around age 47, normalized so that the unweighted mean = 1.
    Based on BLS Occupational Employment Statistics median weekly earnings by age group
    (2023): 20–24 ≈ 0.67×, 25–34 ≈ 0.84×, 35–44 ≈ 1.00×, 45–54 ≈ 1.08×, 55–64 ≈ 1.03×.

    If ``None`` at construction, the quadratic approximation below is used.
    """

    # ------------------------------------------------------------------
    # Solver
    # ------------------------------------------------------------------
    tol: float = 1e-6
    """Convergence tolerance (sup-norm of relative change in K between iterations)."""

    max_iter_gs: int = 500
    """Maximum Gauss-Seidel iterations before declaring non-convergence."""

    max_iter_broyden: int = 100
    """Maximum Broyden quasi-Newton iterations."""

    dampening_gs: float = 0.50
    """
    Gauss-Seidel update dampening factor θ:
    ``K ← (1 − θ)·K + θ·K_new``.
    Smaller = more stable but slower; typically 0.3–0.6.
    """

    oscillation_window: int = 20
    """Number of recent GS iterations inspected for oscillation detection."""

    oscillation_threshold: float = 0.40
    """
    If the fraction of sign-reversals in the residual sequence exceeds this
    threshold over the last ``oscillation_window`` iterations, the solver
    declares oscillation and triggers an auto-switch to Broyden's method.
    """

    # ------------------------------------------------------------------
    # Post-init
    # ------------------------------------------------------------------
    def __post_init__(self) -> None:
        if self.earnings_profile is None:
            ages = np.arange(21, 21 + self.retirement_age_cohort, dtype=float)
            # Quadratic approximation to BLS age-earnings hump, peak ≈ age 47
            raw = 1.0 - 0.00055 * (ages - 47.0) ** 2
            raw = np.clip(raw, 0.30, 1.20)
            self.earnings_profile = raw / raw.mean()

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------
    @property
    def working_cohorts(self) -> int:
        """Number of working-age cohorts."""
        return self.retirement_age_cohort

    @property
    def retired_cohorts(self) -> int:
        """Number of retired cohorts."""
        return self.n_cohorts - self.retirement_age_cohort

    @property
    def cohort_sizes(self) -> np.ndarray:
        """
        Relative cohort sizes with the youngest cohort (j = 0) normalized to 1.

        Older cohorts were born when population was smaller:
        ``n_j = (1 + pop_growth)^{−j}``.

        Shape: ``(n_cohorts,)``, dtype float64.
        """
        j = np.arange(self.n_cohorts, dtype=float)
        return (1.0 + self.pop_growth) ** (-j)

    def get_normalized_cohort_sizes(self) -> np.ndarray:
        """Cohort sizes normalized so they sum to 1."""
        s = self.cohort_sizes
        return s / s.sum()
