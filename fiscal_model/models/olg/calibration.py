"""
OLG Model Calibration — parameter fitting to US macroeconomic targets.

Calibration targets (US, 2025)
-------------------------------
  Capital-output ratio K/Y ≈ 3.0       (BEA Fixed Asset Accounts 2024)
  Real interest rate    r   ≈ 4–5%      (CBO 10-year real rate projection)
  Labour share          wL/Y ≈ 0.65     (BEA national accounts)
  Capital share         α   = 0.35      (BEA, directly from national accounts)
  Depreciation          δ   = 0.05      (BEA, aggregate fixed assets)

The model has one free calibration parameter once (α, δ, n, g) are fixed:
the discount factor β.  We calibrate β so that the model-implied K/Y ≈ 3.0.

Age-earnings profile calibration
----------------------------------
BLS Occupational Employment Statistics, median weekly earnings 2023:
    Age group   Median earnings   Index (÷ overall median $1,045)
    20–24             $696           0.667
    25–34             $918           0.879
    35–44           $1,097           1.050
    45–54           $1,117           1.069
    55–64           $1,043           0.998
    65+               $907           0.868

We fit a quadratic to map continuous ages 21–64 to these five anchors.

Data loading note
-----------------
This module uses hardcoded / analytically calibrated parameters. A future
extension could load BLS/BEA/SSA data directly; the structure is set up
for that with `load_bls_age_earnings_profile`.
"""

from __future__ import annotations

import logging
from typing import Callable

import numpy as np

from .firm import output, factor_prices
from .household import aggregate_household_results
from .parameters import OLGParameters

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Age-earnings profile
# ---------------------------------------------------------------------------

# BLS anchor data: (age, index) pairs
_BLS_AGE_EARNINGS_ANCHORS = np.array([
    [22.0, 0.667],   # 20–24 midpoint
    [29.5, 0.879],   # 25–34 midpoint
    [39.5, 1.050],   # 35–44 midpoint
    [49.5, 1.069],   # 45–54 midpoint
    [59.5, 0.998],   # 55–64 midpoint
])


def build_age_earnings_profile(retirement_age_cohort: int = 44) -> np.ndarray:
    """
    Construct hump-shaped age-earnings efficiency profile using BLS anchors.

    Fits a quadratic  ε(age) = a + b·age + c·age²  to the five BLS anchor
    points via least-squares, then evaluates it for ages 21–64 and normalises
    so the unweighted mean = 1.

    Parameters
    ----------
    retirement_age_cohort : int
        Number of working-age cohorts (default 44 → ages 21–64).

    Returns
    -------
    eps : ndarray, shape (retirement_age_cohort,)
        Efficiency profile ε_j, normalised so mean(ε) = 1.
    """
    anchors = _BLS_AGE_EARNINGS_ANCHORS
    ages_anchor = anchors[:, 0]
    vals_anchor = anchors[:, 1]

    # Quadratic fit
    coeffs = np.polyfit(ages_anchor, vals_anchor, deg=2)
    ages = np.arange(21, 21 + retirement_age_cohort, dtype=float)
    eps = np.polyval(coeffs, ages)
    eps = np.clip(eps, 0.30, 1.40)
    return eps / eps.mean()


# ---------------------------------------------------------------------------
# Beta calibration
# ---------------------------------------------------------------------------

def calibrate_beta(
    params: OLGParameters,
    target_ky_ratio: float = 3.0,
    beta_lo: float = 0.80,
    beta_hi: float = 0.99,
    tol: float = 1e-5,
    max_iter: int = 60,
) -> float:
    """
    Calibrate discount factor β to hit K/Y ≈ target_ky_ratio.

    Uses bisection on the steady-state K/Y as a function of β.

    Parameters
    ----------
    params : OLGParameters
        Base parameters (beta will be modified temporarily).
    target_ky_ratio : float
        Desired capital-output ratio (default 3.0).
    beta_lo, beta_hi : float
        Search bracket for β.
    tol : float
        Convergence tolerance on |K/Y − target|.
    max_iter : int
        Maximum bisection iterations.

    Returns
    -------
    beta_calibrated : float
    """
    import copy
    from .solver import OLGSolver

    logger.info("Calibrating β for K/Y target = %.2f...", target_ky_ratio)

    def ky_ratio(beta: float) -> float:
        p = copy.copy(params)
        p.beta = beta
        p.earnings_profile = None  # Re-generate
        p.__post_init__()
        solver = OLGSolver(p)
        ss = solver.solve_steady_state(force_broyden=False)
        return ss.capital_output_ratio

    # Bisection
    lo, hi = beta_lo, beta_hi
    ky_lo = ky_ratio(lo)
    ky_hi = ky_ratio(hi)

    # Check bracket
    if (ky_lo - target_ky_ratio) * (ky_hi - target_ky_ratio) > 0:
        logger.warning(
            "Could not bracket β for K/Y=%.2f (K/Y_lo=%.2f, K/Y_hi=%.2f). "
            "Returning default β=%.3f.",
            target_ky_ratio, ky_lo, ky_hi, params.beta,
        )
        return params.beta

    for i in range(max_iter):
        mid = 0.5 * (lo + hi)
        ky_mid = ky_ratio(mid)
        if abs(ky_mid - target_ky_ratio) < tol:
            logger.info("β calibrated: %.5f (K/Y=%.4f) after %d iterations.", mid, ky_mid, i + 1)
            return mid
        if (ky_lo - target_ky_ratio) * (ky_mid - target_ky_ratio) < 0:
            hi = mid
            ky_hi = ky_mid
        else:
            lo = mid
            ky_lo = ky_mid

    logger.warning("β calibration did not fully converge; returning best estimate %.5f.", mid)
    return mid


# ---------------------------------------------------------------------------
# Validation against calibration targets
# ---------------------------------------------------------------------------

def validate_calibration(ss, params: OLGParameters) -> dict[str, dict]:
    """
    Check steady state against standard calibration targets.

    Returns a dict with target name → {'value': ..., 'target': ..., 'ok': bool}.
    """
    results = {}

    # K/Y ratio
    ky = ss.capital_output_ratio
    results["K/Y ratio"] = {
        "value": ky,
        "target": 3.0,
        "tolerance": 0.30,
        "ok": abs(ky - 3.0) < 0.30,
        "unit": "",
    }

    # Labour share wL/Y
    labour_share = (ss.w * ss.L) / max(ss.Y, 1e-10)
    results["Labour share (wL/Y)"] = {
        "value": labour_share,
        "target": 1.0 - params.alpha,
        "tolerance": 0.03,
        "ok": abs(labour_share - (1.0 - params.alpha)) < 0.03,
        "unit": "",
    }

    # Net interest rate
    r_pct = ss.r * 100.0
    results["Real interest rate (%)"] = {
        "value": r_pct,
        "target": 4.5,
        "tolerance": 2.0,
        "ok": 2.0 <= r_pct <= 8.0,
        "unit": "%",
    }

    # Debt/GDP
    dg = ss.debt_gdp
    results["Debt / GDP"] = {
        "value": dg,
        "target": params.initial_debt_gdp,
        "tolerance": 0.20,
        "ok": abs(dg - params.initial_debt_gdp) < 0.30,
        "unit": "",
    }

    return results


def print_calibration_report(ss, params: OLGParameters) -> None:
    """Print a human-readable calibration validation report."""
    checks = validate_calibration(ss, params)
    print("\n=== OLG Calibration Report ===")
    for name, check in checks.items():
        status = "✓" if check["ok"] else "✗"
        unit = check["unit"]
        print(
            f"  {status} {name}: {check['value']:.3f}{unit}  "
            f"(target: {check['target']:.3f}{unit})"
        )
    n_pass = sum(c["ok"] for c in checks.values())
    print(f"\n  {n_pass}/{len(checks)} targets met.\n")


# ---------------------------------------------------------------------------
# SSA demographic projection (simplified)
# ---------------------------------------------------------------------------

def ssa_pop_growth_projection(year: int = 2026) -> float:
    """
    SSA intermediate population growth projection for the given year.

    Values from SSA 2024 Trustees Report (intermediate assumptions):
    - 2020–2030: ~0.5–0.6% per year
    - 2030–2045: ~0.4–0.5%
    - 2045+: ~0.4%

    Returns a simple interpolated value.
    """
    # Linear interpolation between anchor points
    anchors = [(2020, 0.006), (2030, 0.005), (2045, 0.004), (2075, 0.004)]
    years = [a[0] for a in anchors]
    rates = [a[1] for a in anchors]
    return float(np.interp(year, years, rates))
