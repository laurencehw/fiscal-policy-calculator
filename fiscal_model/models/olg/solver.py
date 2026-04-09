"""
OLG Steady-State Solver — Gauss-Seidel (primary) + Broyden's (fallback).

The steady-state equilibrium is a fixed point in (K, L):

    F(K, L) = [(K_supply − K) / K_scale,
               (L_supply − L) / L_scale]  = 0

where K_supply and L_supply come from household optimisation given the
factor prices implied by (K, L).

With inelastic labour supply L is already determined by the demographic
structure, so in practice the system reduces to a scalar equation in K.
Nevertheless the solver is written for the 2D case to support future
extensions with elastic labour.

Gauss-Seidel (primary solver)
------------------------------
Simple dampened fixed-point iteration.  Robust for small-to-medium policy
changes.  Oscillation is detected by monitoring sign-changes in the
residual sequence; if the fraction of sign-changes in the last
``oscillation_window`` iterations exceeds ``oscillation_threshold``, the
solver returns a ``SolverStatus.OSCILLATING`` flag and the caller should
switch to Broyden's.

Broyden's quasi-Newton (fallback)
-----------------------------------
Good Broyden update (rank-1 update to the inverse Jacobian):

    J^{−1}_{new} = J^{−1}_{old}
                   + (Δx − J^{−1}·ΔF) · (Δx^T · J^{−1}) / (Δx^T · J^{−1} · ΔF)

Broyden's is used:
    1. As a direct call when the caller requests it.
    2. Automatically when ``auto_solve`` detects GS oscillation.

Transition path
---------------
The transition path is computed via myopic forward shooting:
households see current-period prices and form static expectations.
This is a first-order approximation; the steady states themselves
are exact.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

from .firm import factor_prices, output
from .government import (
    compute_closure_tax_rate,
    compute_gov_spending,
    compute_ss_benefit,
    compute_ss_outlays,
)
from .household import aggregate_household_results

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

class SolverStatus(Enum):
    CONVERGED = "converged"
    OSCILLATING = "oscillating"
    MAX_ITER = "max_iterations"
    FAILED = "failed"


@dataclass
class SteadyState:
    """
    Complete description of an OLG steady state.

    All quantities are in model units (normalised so the youngest cohort
    has population 1; wages and capital are in $T for US calibration).
    """
    # Factor market
    K: float          # Aggregate capital
    L: float          # Aggregate effective labour
    Y: float          # Aggregate output
    r: float          # Net interest rate
    w: float          # Wage per efficiency unit

    # Government
    tau_l: float      # Labour income tax rate (may be endogenous)
    tau_k: float      # Capital income tax rate
    tau_ss: float     # SS payroll tax rate
    ss_benefit: float # Per-retiree SS benefit
    debt: float       # Publicly-held government debt
    gov_spending: float

    # Fiscal aggregates
    total_revenue: float
    ss_outlays: float

    # Household
    consumption_path: np.ndarray   # c_j for j=0..N-1
    assets_path: np.ndarray        # a_j for j=0..N

    # Solver metadata
    iterations: int = 0
    status: SolverStatus = SolverStatus.CONVERGED
    residual: float = 0.0

    @property
    def capital_output_ratio(self) -> float:
        return self.K / max(self.Y, 1e-10)

    @property
    def debt_gdp(self) -> float:
        return self.debt / max(self.Y, 1e-10)

    @property
    def labor_share(self) -> float:
        return (self.w * self.L) / max(self.Y, 1e-10)


@dataclass
class TransitionPath:
    """Time path of key variables from baseline to reform steady state."""
    years: np.ndarray               # Calendar years
    K_path: np.ndarray              # Capital stock
    L_path: np.ndarray              # Effective labour
    Y_path: np.ndarray              # Output
    r_path: np.ndarray              # Interest rate
    w_path: np.ndarray              # Wage
    tau_l_path: np.ndarray          # Labour tax rate
    debt_path: np.ndarray           # Government debt
    consumption_paths: list[np.ndarray] = field(default_factory=list)  # Per-period cohort consumption


# ---------------------------------------------------------------------------
# Gauss-Seidel solver
# ---------------------------------------------------------------------------

class GaussSeidelSolver:
    """
    Dampened fixed-point iteration for OLG steady state.

    At each iteration:
      1. Given K (and L, which is fixed with inelastic supply), compute prices.
      2. Solve household problem to get K_new.
      3. Check convergence; update with dampening.
      4. Detect oscillation; signal if found.
    """

    def __init__(self, params):
        self.params = params

    def _one_step(
        self,
        K: float,
        L: float,
        debt: float,
        override_tau_l: float | None = None,
    ) -> tuple[float, float, float, float, float, float, float, np.ndarray, np.ndarray]:
        """
        Single GS step: prices → household → new K.

        Returns (K_new, L_new, r, w, tau_l, ss_benefit, gov_spending,
                 consumption_path, assets_path).
        """
        p = self.params
        r, w = factor_prices(K, L, p.alpha, p.delta, p.tfp)
        Y = output(K, L, p.alpha, p.tfp)
        ss_benefit = compute_ss_benefit(p.ss_replacement_rate, w)
        ss_out = compute_ss_outlays(ss_benefit, p.cohort_sizes, p.retirement_age_cohort)
        G = compute_gov_spending(p.gov_spending_gdp, Y)

        if override_tau_l is not None:
            tau_l = override_tau_l
        elif p.fiscal_closure == "labor_tax":
            tau_l = compute_closure_tax_rate(p, Y, w, L, r, K, debt, ss_out)
        else:
            tau_l = p.labor_tax_rate

        K_new, L_new, c_path, a_path = aggregate_household_results(
            p, r, w, tau_l, p.capital_tax_rate, p.ss_payroll_rate, ss_benefit
        )
        return K_new, L_new, r, w, tau_l, ss_benefit, G, c_path, a_path

    def solve(
        self,
        K_init: float,
        L_init: float,
        debt: float,
        override_tau_l: float | None = None,
    ) -> tuple[SteadyState, SolverStatus]:
        """
        Run Gauss-Seidel iteration to find steady-state K.

        Parameters
        ----------
        K_init, L_init : float
            Initial guesses.
        debt : float
            Government debt (treated as given for fiscal closure calculation).
        override_tau_l : float | None
            If provided, skip fiscal closure and use this fixed tax rate.

        Returns
        -------
        (SteadyState, SolverStatus)
        """
        p = self.params
        K, L = K_init, L_init
        theta = p.dampening_gs
        residuals: list[float] = []

        for it in range(p.max_iter_gs):
            K_new, L_new, r, w, tau_l, ss_benefit, G, c_path, a_path = \
                self._one_step(K, L, debt, override_tau_l)

            # Residual = relative change in K
            resid_K = (K_new - K) / max(abs(K), 1e-10)
            residuals.append(resid_K)

            if abs(resid_K) < p.tol:
                # Convergence
                return self._build_steady_state(
                    K_new, L_new, r, w, tau_l, ss_benefit, G, debt, c_path, a_path, it + 1
                ), SolverStatus.CONVERGED

            # Oscillation detection
            if (it >= p.oscillation_window and
                    _oscillation_fraction(residuals, p.oscillation_window)
                    >= p.oscillation_threshold):
                logger.info(
                    "GS oscillation detected at iteration %d (resid=%.2e). "
                    "Switching to Broyden's.", it, resid_K
                )
                return self._build_steady_state(
                    K, L, r, w, tau_l, ss_benefit, G, debt, c_path, a_path, it + 1
                ), SolverStatus.OSCILLATING

            # Dampened update
            K = (1.0 - theta) * K + theta * K_new
            # L is fixed with inelastic labour; update anyway for future use
            L = L_new

        # Max iterations reached
        r, w = factor_prices(K, L, p.alpha, p.delta, p.tfp)
        Y = output(K, L, p.alpha, p.tfp)
        ss_benefit = compute_ss_benefit(p.ss_replacement_rate, w)
        G = compute_gov_spending(p.gov_spending_gdp, Y)
        _, _, _, _, tau_l, ss_benefit, G, c_path, a_path = \
            self._one_step(K, L, debt, override_tau_l)

        return self._build_steady_state(
            K, L, r, w, tau_l, ss_benefit, G, debt, c_path, a_path, p.max_iter_gs
        ), SolverStatus.MAX_ITER

    def _build_steady_state(
        self, K, L, r, w, tau_l, ss_benefit, G, debt, c_path, a_path, iters
    ) -> SteadyState:
        p = self.params
        Y = output(K, L, p.alpha, p.tfp)
        ss_out = compute_ss_outlays(ss_benefit, p.cohort_sizes, p.retirement_age_cohort)
        from .government import compute_tax_revenues
        total_rev = compute_tax_revenues(w, L, r, K, tau_l, p.capital_tax_rate, p.ss_payroll_rate)
        resid = abs((aggregate_household_results(
            p, r, w, tau_l, p.capital_tax_rate, p.ss_payroll_rate, ss_benefit
        )[0] - K) / max(abs(K), 1e-10))
        return SteadyState(
            K=K, L=L, Y=Y, r=r, w=w,
            tau_l=tau_l, tau_k=p.capital_tax_rate, tau_ss=p.ss_payroll_rate,
            ss_benefit=ss_benefit, debt=debt, gov_spending=G,
            total_revenue=total_rev, ss_outlays=ss_out,
            consumption_path=c_path, assets_path=a_path,
            iterations=iters, residual=resid,
        )


# ---------------------------------------------------------------------------
# Broyden's quasi-Newton solver
# ---------------------------------------------------------------------------

class BroydenSolver:
    """
    Good Broyden update for OLG steady-state.

    Treats x = [K] as the unknown (scalar for inelastic labour).
    For elastic labour generalisation, extend to x = [K, L].
    """

    def __init__(self, params):
        self.params = params
        self._gs = GaussSeidelSolver(params)

    def _F(
        self,
        x: np.ndarray,
        debt: float,
        override_tau_l: float | None,
    ) -> np.ndarray:
        """Residual function F(x) = K_supply(x) - x[0]."""
        K = float(x[0])
        p = self.params
        r, w = factor_prices(K, p._L_labour, p.alpha, p.delta, p.tfp)
        ss_benefit = compute_ss_benefit(p.ss_replacement_rate, w)
        Y = output(K, p._L_labour, p.alpha, p.tfp)
        ss_out = compute_ss_outlays(ss_benefit, p.cohort_sizes, p.retirement_age_cohort)
        compute_gov_spending(p.gov_spending_gdp, Y)

        if override_tau_l is not None:
            tau_l = override_tau_l
        elif p.fiscal_closure == "labor_tax":
            tau_l = compute_closure_tax_rate(
                p, Y, w, p._L_labour, r, K, debt, ss_out
            )
        else:
            tau_l = p.labor_tax_rate

        K_new, _, _, _ = aggregate_household_results(
            p, r, w, tau_l, p.capital_tax_rate, p.ss_payroll_rate, ss_benefit
        )
        return np.array([K_new - K])

    def solve(
        self,
        K_init: float,
        L_init: float,
        debt: float,
        override_tau_l: float | None = None,
    ) -> tuple[SteadyState, SolverStatus]:
        """
        Run Broyden's method starting from (K_init, L_init).
        """
        p = self.params
        # Store L as a side-channel (inelastic labour is fixed)
        p._L_labour = L_init

        x = np.array([K_init], dtype=float)
        F_old = self._F(x, debt, override_tau_l)

        # Initial approximate Jacobian inverse (scalar: dK/dF ≈ 1)
        J_inv = np.eye(1)

        for it in range(p.max_iter_broyden):
            dx = -J_inv @ F_old
            x_new = x + dx
            x_new[0] = max(x_new[0], 1e-6)  # K must be positive

            F_new = self._F(x_new, debt, override_tau_l)

            # Convergence check
            if np.max(np.abs(F_new)) < p.tol:
                K_sol = float(x_new[0])
                return self._build_ss(K_sol, L_init, debt, override_tau_l, it + 1,
                                      SolverStatus.CONVERGED)

            # Good Broyden update of J^{-1}
            delta_x = x_new - x
            delta_F = F_new - F_old
            denom = float(delta_x @ J_inv @ delta_F)
            if abs(denom) > 1e-15:
                J_inv = J_inv + np.outer(
                    delta_x - J_inv @ delta_F, delta_x @ J_inv
                ) / denom

            x = x_new
            F_old = F_new

        # Max iterations
        K_sol = float(x[0])
        return self._build_ss(K_sol, L_init, debt, override_tau_l,
                              p.max_iter_broyden, SolverStatus.MAX_ITER)

    def _build_ss(self, K, L, debt, override_tau_l, iters, status) -> tuple[SteadyState, SolverStatus]:
        p = self.params
        r, w = factor_prices(K, L, p.alpha, p.delta, p.tfp)
        Y = output(K, L, p.alpha, p.tfp)
        ss_benefit = compute_ss_benefit(p.ss_replacement_rate, w)
        ss_out = compute_ss_outlays(ss_benefit, p.cohort_sizes, p.retirement_age_cohort)
        G = compute_gov_spending(p.gov_spending_gdp, Y)
        if override_tau_l is not None:
            tau_l = override_tau_l
        elif p.fiscal_closure == "labor_tax":
            tau_l = compute_closure_tax_rate(p, Y, w, L, r, K, debt, ss_out)
        else:
            tau_l = p.labor_tax_rate
        K_new, _, c_path, a_path = aggregate_household_results(
            p, r, w, tau_l, p.capital_tax_rate, p.ss_payroll_rate, ss_benefit
        )
        from .government import compute_tax_revenues
        total_rev = compute_tax_revenues(w, L, r, K, tau_l, p.capital_tax_rate, p.ss_payroll_rate)
        resid = abs(K_new - K) / max(abs(K), 1e-10)
        return SteadyState(
            K=K, L=L, Y=Y, r=r, w=w,
            tau_l=tau_l, tau_k=p.capital_tax_rate, tau_ss=p.ss_payroll_rate,
            ss_benefit=ss_benefit, debt=debt, gov_spending=G,
            total_revenue=total_rev, ss_outlays=ss_out,
            consumption_path=c_path, assets_path=a_path,
            iterations=iters, residual=resid,
            status=status,
        ), status


# ---------------------------------------------------------------------------
# Auto solver: GS → Broyden on oscillation
# ---------------------------------------------------------------------------

class OLGSolver:
    """
    Unified solver that runs Gauss-Seidel first and auto-switches to
    Broyden's quasi-Newton if GS detects oscillation.

    This handles both small/marginal policy changes (GS is sufficient)
    and large shocks (SS repeal, full TCJA expiration) where GS may fail
    to converge.
    """

    def __init__(self, params):
        self.params = params
        self._gs = GaussSeidelSolver(params)
        self._broyden = BroydenSolver(params)

    def solve_steady_state(
        self,
        K_init: float | None = None,
        debt: float | None = None,
        override_tau_l: float | None = None,
        force_broyden: bool = False,
    ) -> SteadyState:
        """
        Solve for OLG steady state.

        Parameters
        ----------
        K_init : float | None
            Initial capital guess.  Defaults to 3× labour-weighted output.
        debt : float | None
            Government debt.  Defaults to params.initial_debt_gdp × Y.
        override_tau_l : float | None
            Fix labour tax rate (bypass fiscal closure).
        force_broyden : bool
            Skip GS and go straight to Broyden's (useful for large shocks).

        Returns
        -------
        SteadyState (converged or best available).
        """
        p = self.params

        # Compute labour (inelastic — fixed by demographics)
        L = float(np.dot(p.cohort_sizes[:p.retirement_age_cohort], p.earnings_profile))

        # Initial capital guess
        if K_init is None:
            # K/Y ≈ 3 target; Y ≈ A·K^α·L^(1−α), use approximate Y ~ 1
            # Start with capital-labour ratio implied by modified golden rule
            from .firm import modified_golden_rule_capital
            K_init = modified_golden_rule_capital(
                L, p.alpha, p.delta, p.beta, p.sigma, p.tfp
            )
        K_init = max(K_init, 1e-3)

        # Initial debt
        if debt is None:
            # Use a rough output estimate to set initial debt
            from .firm import output
            Y_approx = output(K_init, L, p.alpha, p.tfp)
            debt = p.initial_debt_gdp * Y_approx

        if force_broyden:
            ss, status = self._broyden.solve(K_init, L, debt, override_tau_l)
            logger.info("Broyden (forced): status=%s, K=%.4f, iter=%d", status, ss.K, ss.iterations)
            return ss

        # Try Gauss-Seidel first
        ss_gs, status_gs = self._gs.solve(K_init, L, debt, override_tau_l)
        logger.info("GS: status=%s, K=%.4f, iter=%d, resid=%.2e",
                    status_gs, ss_gs.K, ss_gs.iterations, ss_gs.residual)

        if status_gs == SolverStatus.CONVERGED:
            return ss_gs

        # GS oscillated or hit max iterations → switch to Broyden's
        logger.info("Switching to Broyden's (GS status=%s).", status_gs)
        ss_br, status_br = self._broyden.solve(
            ss_gs.K, ss_gs.L, debt, override_tau_l
        )
        logger.info("Broyden: status=%s, K=%.4f, iter=%d, resid=%.2e",
                    status_br, ss_br.K, ss_br.iterations, ss_br.residual)
        return ss_br

    def compute_transition_path(
        self,
        baseline_ss: SteadyState,
        reform_policy_fn: Callable[[int], dict],
        start_year: int = 2026,
    ) -> TransitionPath:
        """
        Compute the transition path from the baseline steady state after a
        policy reform, using myopic expectations (households see current prices
        and assume they persist).

        Parameters
        ----------
        baseline_ss : SteadyState
            Starting point of the transition.
        reform_policy_fn : callable(t) → dict
            Returns a dict with override fiscal parameters at transition period t.
            Keys: 'tau_l', 'tau_k', 'tau_ss', 'ss_replacement_rate', etc.
            Values of None mean "use baseline params".
        start_year : int
            Calendar year of the first transition period.

        Returns
        -------
        TransitionPath
        """
        p = self.params
        T = p.transition_years
        years = np.arange(start_year, start_year + T)

        K_path = np.empty(T)
        L_path = np.empty(T)
        Y_path = np.empty(T)
        r_path = np.empty(T)
        w_path = np.empty(T)
        tau_l_path = np.empty(T)
        debt_path = np.empty(T)

        K = baseline_ss.K
        L = baseline_ss.L
        debt = baseline_ss.debt

        # Dampening factor for transition updates — same principle as the
        # Gauss-Seidel steady-state solver.  Without dampening, myopic
        # forward-shooting can produce wild K oscillations.
        theta = p.dampening_gs
        # Maximum relative step size per period (prevents explosive jumps)
        _MAX_REL_STEP = 0.25

        for t in range(T):
            overrides = reform_policy_fn(t)
            tau_l_ov = overrides.get("tau_l")
            tau_k = overrides.get("tau_k", p.capital_tax_rate)
            tau_ss = overrides.get("tau_ss", p.ss_payroll_rate)
            ss_rep = overrides.get("ss_replacement_rate", p.ss_replacement_rate)

            from .firm import factor_prices as fp
            from .firm import output as out
            r, w = fp(K, L, p.alpha, p.delta, p.tfp)
            Y = out(K, L, p.alpha, p.tfp)
            ss_benefit = w * ss_rep
            ss_out = compute_ss_outlays(ss_benefit, p.cohort_sizes, p.retirement_age_cohort)
            G = compute_gov_spending(p.gov_spending_gdp, Y)

            if tau_l_ov is not None:
                tau_l = tau_l_ov
            elif p.fiscal_closure == "labor_tax":
                tau_l = compute_closure_tax_rate(p, Y, w, L, r, K, debt, ss_out)
            else:
                tau_l = p.labor_tax_rate

            K_new, L_new, _c_path, _a_path = aggregate_household_results(
                p, r, w, tau_l, tau_k, tau_ss, ss_benefit
            )

            # Debt dynamics
            from .government import compute_debt_next_period, compute_tax_revenues
            total_rev = compute_tax_revenues(w, L, r, K, tau_l, tau_k, tau_ss)
            debt_new = compute_debt_next_period(debt, r, G, ss_out, total_rev)

            K_path[t] = K
            L_path[t] = L
            Y_path[t] = Y
            r_path[t] = r
            w_path[t] = w
            tau_l_path[t] = tau_l
            debt_path[t] = debt

            # Dampened update with step-size limiter to prevent oscillation.
            # Guard against non-finite K values so NaN/Inf cannot propagate.
            if not np.isfinite(K_new):
                logger.warning(
                    "Transition t=%d: non-finite K_new=%s; keeping prior K=%.6g",
                    t, K_new, K,
                )
                K_new = K
            # 1. Apply dampening: blend old and new K.
            K_blended = (1.0 - theta) * K + theta * K_new
            # 2. Clamp the relative step to ±_MAX_REL_STEP of current K.
            K_floor = K * (1.0 - _MAX_REL_STEP)
            K_ceil = K * (1.0 + _MAX_REL_STEP)
            K_next = max(np.clip(K_blended, K_floor, K_ceil), 1e-6)
            if not np.isfinite(K_next):
                logger.error(
                    "Transition t=%d: non-finite K_next after clamp; "
                    "falling back to prior K=%.6g", t, K,
                )
                K_next = max(K, 1e-6)
            elif abs(K_new - K) / max(abs(K), 1e-10) > 1.0:
                logger.warning(
                    "Transition t=%d: K_new=%.2f vs K=%.2f (>100%% step), "
                    "clamped to %.2f", t, K_new, K, K_next,
                )
            K = K_next
            L = L_new
            debt = debt_new

        return TransitionPath(
            years=years,
            K_path=K_path,
            L_path=L_path,
            Y_path=Y_path,
            r_path=r_path,
            w_path=w_path,
            tau_l_path=tau_l_path,
            debt_path=debt_path,
        )


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _oscillation_fraction(residuals: list[float], window: int) -> float:
    """
    Fraction of sign-changes in the last ``window`` residuals.

    A high fraction (near 0.5) indicates the iteration is oscillating
    rather than converging monotonically.
    """
    recent = residuals[-window:]
    if len(recent) < 2:
        return 0.0
    signs = np.sign(recent)
    n_changes = int(np.sum(signs[1:] != signs[:-1]))
    return n_changes / max(len(recent) - 1, 1)
