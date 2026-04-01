"""
OLG Model Package — Auerbach-Kotlikoff 55-cohort overlapping generations.

Quick start
-----------
    from fiscal_model.models.olg import OLGModel, OLGParameters

    model = OLGModel()
    baseline = model.get_baseline()
    result = model.analyze_policy(
        reform_overrides={"tau_k": 0.35},  # +5 pp capital tax
        policy_name="Biden Corporate 28%",
    )
    print(result.summary())

Module layout
-------------
parameters.py          — OLGParameters dataclass
household.py           — CRRA household optimization (Euler equation)
firm.py                — Cobb-Douglas firm, factor prices
government.py          — Government budget, SS, fiscal closure
solver.py              — Gauss-Seidel + Broyden quasi-Newton solvers
model.py               — OLGModel orchestrator
generational_accounting.py — AKG generational accounts
calibration.py         — Beta calibration, BLS age-earnings, validation
"""

from .calibration import (
    build_age_earnings_profile,
    calibrate_beta,
    print_calibration_report,
    validate_calibration,
)
from .firm import factor_prices, output
from .generational_accounting import GenerationalAccounting, GenerationalAccounts
from .household import aggregate_household_results, solve_household
from .model import OLGModel, OLGPolicyResult
from .parameters import OLGParameters
from .pwbm_model import OLGMacroResult, PWBMModel
from .solver import (
    BroydenSolver,
    GaussSeidelSolver,
    OLGSolver,
    SolverStatus,
    SteadyState,
    TransitionPath,
)

__all__ = [
    "BroydenSolver",
    "GaussSeidelSolver",
    # Generational accounting
    "GenerationalAccounting",
    "GenerationalAccounts",
    "OLGMacroResult",
    # Entry points
    "OLGModel",
    "OLGParameters",
    "OLGPolicyResult",
    # Solver
    "OLGSolver",
    # PWBMModel adapter
    "PWBMModel",
    "SolverStatus",
    "SteadyState",
    "TransitionPath",
    "aggregate_household_results",
    # Calibration utilities
    "build_age_earnings_profile",
    "calibrate_beta",
    "factor_prices",
    "output",
    "print_calibration_report",
    # Sub-components (useful for testing)
    "solve_household",
    "validate_calibration",
]
