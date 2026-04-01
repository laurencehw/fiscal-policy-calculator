"""
OLGModel — Orchestrator for the 55-cohort Auerbach-Kotlikoff model.

Usage
-----
    from fiscal_model.models.olg import OLGModel, OLGParameters

    params = OLGParameters()
    model = OLGModel(params)

    # Compute baseline steady state
    baseline = model.compute_steady_state()

    # Score a reform: e.g. +5 pp corporate tax (modelled as +5 pp capital tax)
    reform_ss = model.compute_steady_state(override_tau_k=0.35)

    # Full OLG result with transition path + generational accounts
    result = model.analyze_policy(
        reform_overrides={"tau_k": 0.35},
        start_year=2026,
    )
    print(result.summary())
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .calibration import calibrate_beta
from .firm import factor_prices, output
from .generational_accounting import GenerationalAccounting, GenerationalAccounts
from .parameters import OLGParameters
from .solver import OLGSolver, SolverStatus, SteadyState, TransitionPath

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# OLG Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class OLGPolicyResult:
    """
    Complete OLG analysis result: steady states + transition + gen accounts.

    Confidence label
    ----------------
    All OLG outputs carry a "Model estimate — wide uncertainty band" label
    to distinguish them from CBO-calibrated static scores.
    """

    baseline: SteadyState
    reform: SteadyState
    transition: TransitionPath
    gen_accounts: GenerationalAccounts | None

    policy_name: str = "OLG Reform"
    confidence_label: str = "Model estimate — wide uncertainty band"

    # ---------------------------------------------------------------------------
    # Derived metrics
    # ---------------------------------------------------------------------------

    @property
    def long_run_gdp_pct_change(self) -> float:
        """Percent change in steady-state GDP (reform vs baseline)."""
        return (self.reform.Y - self.baseline.Y) / max(self.baseline.Y, 1e-10) * 100.0

    @property
    def long_run_capital_pct_change(self) -> float:
        """Percent change in steady-state capital stock."""
        return (self.reform.K - self.baseline.K) / max(self.baseline.K, 1e-10) * 100.0

    @property
    def long_run_wage_pct_change(self) -> float:
        """Percent change in steady-state wage."""
        return (self.reform.w - self.baseline.w) / max(self.baseline.w, 1e-10) * 100.0

    @property
    def long_run_interest_rate_change(self) -> float:
        """Change in steady-state interest rate (percentage points)."""
        return (self.reform.r - self.baseline.r) * 100.0

    def gdp_transition_pct_change(self) -> np.ndarray:
        """
        GDP percent change from baseline along the transition path.
        Uses baseline steady-state GDP as the reference.
        """
        return (self.transition.Y_path - self.baseline.Y) / max(self.baseline.Y, 1e-10) * 100.0

    def year_10_gdp_effect(self) -> float:
        """GDP effect in year 10 of the transition (percent)."""
        path = self.gdp_transition_pct_change()
        return float(path[min(9, len(path) - 1)])

    def year_30_gdp_effect(self) -> float:
        """GDP effect in year 30 of the transition (percent)."""
        path = self.gdp_transition_pct_change()
        return float(path[min(29, len(path) - 1)])

    # ---------------------------------------------------------------------------
    # Summary and export
    # ---------------------------------------------------------------------------

    def summary(self) -> str:
        lines = [
            f"OLG Policy Analysis: {self.policy_name}",
            f"[{self.confidence_label}]",
            "",
            "Long-Run Steady-State Effects:",
            f"  GDP:           {self.long_run_gdp_pct_change:+.2f}%",
            f"  Capital stock: {self.long_run_capital_pct_change:+.2f}%",
            f"  Wage:          {self.long_run_wage_pct_change:+.2f}%",
            f"  Interest rate: {self.long_run_interest_rate_change:+.2f} pp",
            "",
            f"  Baseline K/Y ratio: {self.baseline.capital_output_ratio:.2f}",
            f"  Reform   K/Y ratio: {self.reform.capital_output_ratio:.2f}",
            "",
            "Transition Path:",
            f"  Year-10 GDP effect:  {self.year_10_gdp_effect():+.2f}%",
            f"  Year-30 GDP effect:  {self.year_30_gdp_effect():+.2f}%",
        ]
        if self.gen_accounts is not None:
            newborn_change = self.gen_accounts.newborn_burden_change
            lines += [
                "",
                "Generational Burden (change vs baseline, PV):",
                f"  Newborn (age 21) burden change: {newborn_change:+.4f} (model units)",
                f"  Generational imbalance: {self.gen_accounts.generational_imbalance:+.4f}",
            ]
        return "\n".join(lines)

    def to_transition_dataframe(self) -> pd.DataFrame:
        """Export transition path to DataFrame."""
        pct_change = self.gdp_transition_pct_change()
        return pd.DataFrame({
            "Year": self.transition.years,
            "K": self.transition.K_path,
            "L": self.transition.L_path,
            "Y": self.transition.Y_path,
            "r (%)": self.transition.r_path * 100,
            "w": self.transition.w_path,
            "tau_l (%)": self.transition.tau_l_path * 100,
            "Debt": self.transition.debt_path,
            "GDP_pct_change": pct_change,
        })


# ---------------------------------------------------------------------------
# OLGModel
# ---------------------------------------------------------------------------

class OLGModel:
    """
    55-cohort Auerbach-Kotlikoff Overlapping Generations Model.

    Computes steady states and transition paths for fiscal policy analysis.
    All outputs carry a "wide uncertainty band" confidence label.

    Parameters
    ----------
    params : OLGParameters
        Model parameters.  Default calibration targets the US 2025 economy.
    auto_calibrate_beta : bool
        If True, re-calibrate β to hit K/Y = 3.0 target before solving.
        Useful when params are far from default.
    """

    CONFIDENCE_LABEL = "Model estimate — wide uncertainty band"

    def __init__(
        self,
        params: OLGParameters | None = None,
        auto_calibrate_beta: bool = False,
    ):
        self.params = params or OLGParameters()
        if auto_calibrate_beta:
            self.params.beta = calibrate_beta(self.params)
        self.solver = OLGSolver(self.params)
        self._baseline_ss: SteadyState | None = None

    # ------------------------------------------------------------------
    # Steady state
    # ------------------------------------------------------------------

    def compute_steady_state(
        self,
        K_init: float | None = None,
        debt_override: float | None = None,
        override_tau_l: float | None = None,
        override_tau_k: float | None = None,
        override_tau_ss: float | None = None,
        override_ss_replacement: float | None = None,
        force_broyden: bool = False,
    ) -> SteadyState:
        """
        Compute steady-state equilibrium.

        Override parameters are used to model policy reforms.

        Parameters
        ----------
        K_init : float | None
            Initial capital guess (default: from modified golden rule).
        debt_override : float | None
            Fix government debt (default: params.initial_debt_gdp × Y).
        override_tau_l : float | None
            Fix labour tax (bypasses fiscal closure).
        override_tau_k : float | None
            Capital tax rate for the reform (e.g. 0.35 for a +5 pp hike).
        override_tau_ss : float | None
            SS payroll rate (e.g. 0.0 for SS repeal).
        override_ss_replacement : float | None
            SS replacement rate.
        force_broyden : bool
            Bypass GS and run Broyden's directly.

        Returns
        -------
        SteadyState
        """
        # Apply parameter overrides by temporarily mutating a copy
        p_orig = self.params
        if any(v is not None for v in [
            override_tau_k, override_tau_ss, override_ss_replacement
        ]):
            import copy
            p = copy.copy(self.params)
            if override_tau_k is not None:
                p.capital_tax_rate = override_tau_k
            if override_tau_ss is not None:
                p.ss_payroll_rate = override_tau_ss
            if override_ss_replacement is not None:
                p.ss_replacement_rate = override_ss_replacement
            self.params = p
            self.solver = OLGSolver(p)

        try:
            ss = self.solver.solve_steady_state(
                K_init=K_init,
                debt=debt_override,
                override_tau_l=override_tau_l,
                force_broyden=force_broyden,
            )
        finally:
            self.params = p_orig
            self.solver = OLGSolver(p_orig)

        return ss

    def get_baseline(self) -> SteadyState:
        """Return cached baseline steady state (compute once)."""
        if self._baseline_ss is None:
            logger.info("Computing OLG baseline steady state...")
            self._baseline_ss = self.compute_steady_state()
            logger.info(
                "Baseline: K=%.3f, Y=%.3f, r=%.3f%%, w=%.4f, K/Y=%.2f",
                self._baseline_ss.K, self._baseline_ss.Y,
                self._baseline_ss.r * 100, self._baseline_ss.w,
                self._baseline_ss.capital_output_ratio,
            )
        return self._baseline_ss

    # ------------------------------------------------------------------
    # Full policy analysis
    # ------------------------------------------------------------------

    def analyze_policy(
        self,
        reform_overrides: dict | None = None,
        policy_name: str = "Unnamed Reform",
        compute_gen_accounts: bool = True,
        compute_transition: bool = True,
        start_year: int = 2026,
    ) -> OLGPolicyResult:
        """
        Full OLG policy analysis: baseline + reform steady states,
        transition path, and generational accounts.

        Parameters
        ----------
        reform_overrides : dict | None
            Fiscal parameter overrides for the reform:
            {'tau_l', 'tau_k', 'tau_ss', 'ss_replacement_rate'}.
        policy_name : str
            Label for the reform (shown in UI and summaries).
        compute_gen_accounts : bool
            Whether to compute generational accounts (adds ~1–2 seconds).
        compute_transition : bool
            Whether to compute the transition path (adds ~10–20 seconds
            for T=75 path).
        start_year : int
            Calendar year for the transition path.

        Returns
        -------
        OLGPolicyResult
        """
        reform_overrides = reform_overrides or {}
        baseline = self.get_baseline()

        logger.info("Computing OLG reform steady state for '%s'...", policy_name)
        reform = self.compute_steady_state(
            K_init=baseline.K,  # Warm start from baseline
            debt_override=baseline.debt,
            override_tau_l=reform_overrides.get("tau_l"),
            override_tau_k=reform_overrides.get("tau_k"),
            override_tau_ss=reform_overrides.get("tau_ss"),
            override_ss_replacement=reform_overrides.get("ss_replacement_rate"),
            force_broyden=self._is_large_shock(reform_overrides),
        )
        logger.info("Reform: K=%.3f, Y=%.3f, r=%.3f%%", reform.K, reform.Y, reform.r * 100)

        # Transition path
        transition: TransitionPath | None = None
        if compute_transition:
            def _policy_fn(t: int) -> dict:
                # Policy takes effect immediately at t=0
                return reform_overrides

            transition = self.solver.compute_transition_path(
                baseline_ss=baseline,
                reform_policy_fn=_policy_fn,
                start_year=start_year,
            )

        if transition is None:
            # Dummy flat transition (baseline forever)
            T = self.params.transition_years
            years = np.arange(start_year, start_year + T)
            transition = TransitionPath(
                years=years,
                K_path=np.full(T, baseline.K),
                L_path=np.full(T, baseline.L),
                Y_path=np.full(T, baseline.Y),
                r_path=np.full(T, baseline.r),
                w_path=np.full(T, baseline.w),
                tau_l_path=np.full(T, baseline.tau_l),
                debt_path=np.full(T, baseline.debt),
            )

        # Generational accounts
        gen_accounts = None
        if compute_gen_accounts:
            ga = GenerationalAccounting(self.params)
            gen_accounts = ga.compute(baseline, reform)

        return OLGPolicyResult(
            baseline=baseline,
            reform=reform,
            transition=transition,
            gen_accounts=gen_accounts,
            policy_name=policy_name,
            confidence_label=self.CONFIDENCE_LABEL,
        )

    # ------------------------------------------------------------------
    # Helper
    # ------------------------------------------------------------------

    def _is_large_shock(self, overrides: dict) -> bool:
        """
        Heuristic: flag reforms as "large" if they change capital or SS tax
        by more than 5 percentage points.  Large shocks may need Broyden's.
        """
        p = self.params
        k_change = abs(overrides.get("tau_k", p.capital_tax_rate) - p.capital_tax_rate)
        ss_change = abs(overrides.get("tau_ss", p.ss_payroll_rate) - p.ss_payroll_rate)
        rep_change = abs(
            overrides.get("ss_replacement_rate", p.ss_replacement_rate)
            - p.ss_replacement_rate
        )
        return k_change > 0.05 or ss_change > 0.05 or rep_change > 0.10
