"""
Generational Accounting — Auerbach-Gokhale-Kotlikoff (AKG) methodology.

References
----------
Auerbach, A., Gokhale, J., & Kotlikoff, L. (1991). "Generational Accounts:
  A Meaningful Alternative to Deficit Accounting." NBER Tax Policy and the
  Economy, 5, 55–110.

Auerbach, A., Gokhale, J., & Kotlikoff, L. (1994). "Generational Accounting:
  A Meaningful Way to Evaluate Fiscal Policy." Journal of Economic Perspectives,
  8(1), 73–94.

Methodology
-----------
The **generational account** of a cohort born in year s is the present value
of its lifetime net tax payments (taxes minus transfers):

    GA(s) = Σ_{k=0}^{D} [τ_{net,k} / (1+r)^k]

where τ_{net,k} = net taxes paid in lifecycle stage k (age 21+k).

Net taxes at stage k:
    - Working (k < R): τ_l·w·ε_k + τ_ss·w·ε_k + τ_k·r·a_k
    - Retired (k ≥ R):  τ_k·r·a_k − SS_benefit

**Generational imbalance** (Auerbach-Kotlikoff 2012):
    If the government's intertemporal budget constraint is satisfied for
    current living generations, the residual burden falls on future cohorts.
    The imbalance = GA(future newborn) − GA(current newborn), measured in
    comparable units.

We report:
    1. ``lifetime_burden[j]``: GA for the cohort currently at lifecycle stage j.
       j=0 → just entering the labour market (age 21).
    2. ``newborn_burden_baseline`` vs ``newborn_burden_reform``: how the
       reform changes the burden on new entrants.
    3. ``generational_imbalance``: reform burden on newborns minus baseline
       burden (positive = future cohorts bear more).
    4. ``burden_by_age``: DataFrame for plotting the cohort-incidence chart.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .household import compute_cohort_tax_profile

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class GenerationalAccounts:
    """
    Generational accounting results: baseline vs reform.

    All values in model units (normalised so the aggregate economy ≈ O(1)).
    To convert to dollars, multiply by the calibrated aggregate output Y.
    """

    # Lifetime net tax burden for each cohort at lifecycle stage j=0..N-1
    # j=0 = just born (age 21); j=N-1 = oldest (age 75)
    lifetime_burden_baseline: np.ndarray   # shape (n_cohorts,)
    lifetime_burden_reform: np.ndarray     # shape (n_cohorts,)

    # Annualised cohort sizes (for weighted averages)
    cohort_sizes: np.ndarray               # shape (n_cohorts,)

    # Discount rate used (= r from the baseline steady state)
    discount_rate: float

    @property
    def burden_change(self) -> np.ndarray:
        """Change in lifetime burden: reform − baseline, shape (n_cohorts,)."""
        return self.lifetime_burden_reform - self.lifetime_burden_baseline

    @property
    def newborn_burden_baseline(self) -> float:
        """Lifetime burden of a newborn (j=0) in the baseline."""
        return float(self.lifetime_burden_baseline[0])

    @property
    def newborn_burden_reform(self) -> float:
        """Lifetime burden of a newborn (j=0) in the reform scenario."""
        return float(self.lifetime_burden_reform[0])

    @property
    def newborn_burden_change(self) -> float:
        """Change in newborn lifetime burden: reform − baseline."""
        return self.newborn_burden_reform - self.newborn_burden_baseline

    @property
    def generational_imbalance(self) -> float:
        """
        Simple imbalance measure: change in newborn burden relative to
        the absolute size of the baseline burden.

        Positive → reform increases burden on future cohorts.
        Negative → reform lightens the burden on future cohorts.
        """
        denom = max(abs(self.newborn_burden_baseline), 1e-10)
        return self.newborn_burden_change / denom

    def to_dataframe(self, start_age: int = 21) -> pd.DataFrame:
        """Export burden profiles to DataFrame."""
        n = len(self.lifetime_burden_baseline)
        ages = np.arange(start_age, start_age + n)
        return pd.DataFrame({
            "age": ages,
            "cohort_index": np.arange(n),
            "baseline_burden": self.lifetime_burden_baseline,
            "reform_burden": self.lifetime_burden_reform,
            "burden_change": self.burden_change,
            "cohort_size": self.cohort_sizes,
        })

    def weighted_burden_change(self) -> float:
        """Population-weighted average change in lifetime burden."""
        weights = self.cohort_sizes / self.cohort_sizes.sum()
        return float(np.dot(weights, self.burden_change))


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

class GenerationalAccounting:
    """
    Computes AKG generational accounts comparing two steady states.

    Parameters
    ----------
    params : OLGParameters
    """

    def __init__(self, params):
        self.params = params

    def compute(
        self,
        baseline_ss,
        reform_ss,
    ) -> GenerationalAccounts:
        """
        Compute generational accounts for all currently-living cohorts.

        For each lifecycle stage j (cohort currently age 21+j), we compute:
            GA_j = PV of net taxes over the *remaining* lifetime (from stage j to N-1)

        This represents the burden borne by a cohort that is currently at
        stage j, given the (constant) steady-state prices.

        Parameters
        ----------
        baseline_ss, reform_ss : SteadyState
        """
        p = self.params

        burden_baseline = self._compute_burden_profile(
            ss=baseline_ss,
            r=baseline_ss.r,
        )
        burden_reform = self._compute_burden_profile(
            ss=reform_ss,
            r=baseline_ss.r,  # Discount at baseline rate for comparability
        )

        return GenerationalAccounts(
            lifetime_burden_baseline=burden_baseline,
            lifetime_burden_reform=burden_reform,
            cohort_sizes=p.cohort_sizes,
            discount_rate=baseline_ss.r,
        )

    def _compute_burden_profile(
        self,
        ss,
        r: float,
    ) -> np.ndarray:
        """
        Compute the lifetime net-tax burden for each currently-living cohort.

        Cohort at stage j has already lived j periods.  Its *remaining*
        lifetime burden is the PV of net taxes from stage j to N-1.

        Full lifetime burden (for j=0, a newborn) uses stages 0..N-1.
        """
        p = self.params
        N = p.n_cohorts
        1.0 + r * (1.0 - ss.tau_k)

        # Get the full lifetime tax profile for a cohort born today
        full_tax_profile = compute_cohort_tax_profile(
            params=p,
            r=ss.r,
            w=ss.w,
            tau_l=ss.tau_l,
            tau_k=ss.tau_k,
            tau_ss=ss.tau_ss,
            ss_benefit=ss.ss_benefit,
            assets_path=ss.assets_path,
        )

        # PV discount factors: 1 / (1+r)^k  (using baseline r)
        discount_factors = (1.0 + r) ** (-np.arange(N, dtype=float))

        # For each current lifecycle stage j, compute remaining lifetime burden
        burden = np.empty(N)
        for j in range(N):
            # Remaining stages: j, j+1, ..., N-1
            remaining_taxes = full_tax_profile[j:]
            remaining_discounts = discount_factors[:N - j]
            burden[j] = float(np.dot(remaining_taxes, remaining_discounts))

        return burden

    def compute_intertemporal_balance(
        self,
        baseline_ss,
        r: float | None = None,
        g: float | None = None,
    ) -> dict[str, float]:
        """
        Compute the government's intertemporal budget constraint.

        Intertemporal budget constraint:
            PV(future taxes) = PV(future spending) + current debt

        The residual — if positive — represents the burden that must fall
        on future (unborn) generations.

        Returns
        -------
        dict with keys:
            'pv_taxes': PV of future tax revenues
            'pv_spending': PV of future G + SS
            'current_debt': B_0
            'imbalance': pv_taxes − pv_spending − current_debt
                         (positive = sustainable; negative = unsustainable)
        """
        p = self.params
        if r is None:
            r = baseline_ss.r
        if g is None:
            g = p.pop_growth + p.tfp_growth

        # For a simple estimate, use a geometric sum:
        # PV(taxes) = T / (r − g) for a growing economy
        growth_adj_rate = max(r - g, 0.001)

        pv_taxes = baseline_ss.total_revenue / growth_adj_rate
        pv_spending = (baseline_ss.gov_spending + baseline_ss.ss_outlays) / growth_adj_rate
        debt = baseline_ss.debt

        imbalance = pv_taxes - pv_spending - debt
        return {
            "pv_taxes": pv_taxes,
            "pv_spending": pv_spending,
            "current_debt": debt,
            "imbalance": imbalance,
            "sustainable": imbalance >= 0.0,
        }
