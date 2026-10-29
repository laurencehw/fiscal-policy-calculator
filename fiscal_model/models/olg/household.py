"""
Household Optimization — CRRA utility with Euler equations.

Each cohort j (age 21+j) maximizes discounted lifetime CRRA utility:

    max Σ_{k=j}^{N−1} β^{k−j} · u(c_k),   u(c) = c^{1−σ}/(1−σ)

subject to the per-period budget constraint:

    a_{k+1} = R · a_k + y_k − c_k

where R = 1 + r·(1−τ_k) is the after-tax gross return, y_k is disposable
income (after-tax wages for working cohorts; Social Security benefit for
retired cohorts), and terminal wealth a_N = 0.

Solution
--------
The Euler condition gives   c_{k+1} = φ · c_k  with φ = (β·R)^{1/σ}.

Combining with the lifetime budget constraint (sum over present values):

    c_0 = PV(income) / PV(consumption weights)

    PV(income)           = Σ_{k=0}^{N−1}  y_k  / R^k
    PV(consumption weights) = Σ_{k=0}^{N−1}  φ^k / R^k

This is a closed-form analytical solution — no numerical root-finding required.
The full asset path {a_j} is then recovered via forward iteration.
"""

from __future__ import annotations

import numpy as np

# ---------------------------------------------------------------------------
# Core household problem
# ---------------------------------------------------------------------------

def solve_household(
    n_cohorts: int,
    retirement_cohort: int,
    sigma: float,
    beta: float,
    gross_return: float,
    net_labor_income: np.ndarray,
    ss_benefit: float,
    initial_assets: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Solve a representative cohort's intertemporal optimization problem.

    Parameters
    ----------
    n_cohorts : int
        Total cohorts N alive simultaneously.
    retirement_cohort : int
        Cohort index R at which working life ends (age = 21 + R).
    sigma : float
        CRRA coefficient (risk aversion / inverse IES).
    beta : float
        Annual discount factor.
    gross_return : float
        R = 1 + r·(1−τ_k).  After-tax gross return on savings.
    net_labor_income : ndarray, shape (retirement_cohort,)
        Disposable labor income  ȳ_j = (1−τ_l−τ_ss)·w·ε_j  for j=0..R−1.
    ss_benefit : float
        Annual Social Security benefit for retired cohorts j=R..N−1.
    initial_assets : float
        Starting asset holdings a_0 (= 0 for newborns in steady state).

    Returns
    -------
    consumption : ndarray, shape (n_cohorts,)
        Optimal consumption c_j for cohort at lifecycle stage j.
    assets : ndarray, shape (n_cohorts + 1,)
        Asset holdings a_j.  a_0 = initial_assets; a_N ≈ 0 (terminal condition).
    """
    N = n_cohorts
    R = retirement_cohort
    R_gross = max(gross_return, 1e-8)

    # Income stream for all lifecycle stages
    income = np.empty(N)
    income[:R] = net_labor_income
    income[R:] = ss_benefit

    # Consumption growth factor per period from Euler equation
    phi = (beta * R_gross) ** (1.0 / sigma)

    # Phi vector: c_j = phi^j · c_0
    phi_vec = phi ** np.arange(N, dtype=float)

    # Present-value discount weights: 1/R^j
    pv_weights = R_gross ** (-np.arange(N, dtype=float))

    # Lifetime budget constraint:
    #   c_0 · Σ phi_j·pv_j = a_0 + Σ income_j·pv_j
    pv_income = initial_assets + float(np.dot(income, pv_weights))
    pv_phi = float(np.dot(phi_vec, pv_weights))

    c0 = max(pv_income / max(pv_phi, 1e-15), 1e-12)
    consumption = phi_vec * c0

    # Recover asset path via forward iteration
    assets = np.empty(N + 1)
    assets[0] = initial_assets
    for j in range(N):
        assets[j + 1] = R_gross * assets[j] + income[j] - consumption[j]

    return consumption, assets


def solve_remaining_life(
    sigma: float,
    beta: float,
    gross_returns: np.ndarray,
    income: np.ndarray,
    initial_assets: float,
) -> tuple[np.ndarray, np.ndarray]:
    """
    One cohort's plan for the rest of its life when prices change over time.

    Stage k of the remaining life (k = 0..M−1) has its own after-tax gross
    return ``R_k`` and income ``y_k``.  The budget is
    ``a_{k+1} = R_k·a_k + y_k − c_k`` with ``a_M = 0``, and the Euler equation
    is ``c_{k+1} = (β·R_{k+1})^{1/σ}·c_k``: savings made in stage k earn the
    next stage's return.

    Discounting by ``D_k = 1 / Π_{s≤k} R_s``, the budget sums to

        Σ_k c_k·D_k = a_0 + Σ_k y_k·D_k

    which fixes c_0.  With constant prices this is the steady-state plan of
    :func:`solve_household`, so a cohort that re-plans mid-life under
    unchanged prices keeps its old path (the plan is time-consistent).

    Returns ``(consumption, assets)`` of lengths M and M+1.
    """
    R = np.maximum(np.asarray(gross_returns, dtype=float), 1e-8)
    y = np.asarray(income, dtype=float)
    M = len(y)
    discount = 1.0 / np.cumprod(R)
    growth = np.ones(M)
    if M > 1:
        growth[1:] = np.cumprod((beta * R[1:]) ** (1.0 / sigma))
    wealth = initial_assets + float(np.dot(y, discount))
    c0 = max(wealth / max(float(np.dot(growth, discount)), 1e-15), 1e-12)
    consumption = growth * c0
    assets = np.empty(M + 1)
    assets[0] = initial_assets
    for k in range(M):
        assets[k + 1] = R[k] * assets[k] + y[k] - consumption[k]
    return consumption, assets


def lifetime_utility(consumption: np.ndarray, sigma: float, beta: float) -> float:
    """Discounted CRRA utility of a consumption stream, from its first stage."""
    c = np.maximum(np.asarray(consumption, dtype=float), 1e-12)
    weights = beta ** np.arange(len(c), dtype=float)
    if abs(sigma - 1.0) < 1e-12:
        return float(np.dot(weights, np.log(c)))
    return float(np.dot(weights, c ** (1.0 - sigma) / (1.0 - sigma)))


def consumption_equivalent(
    reform_consumption: np.ndarray,
    baseline_consumption: np.ndarray,
    sigma: float,
    beta: float,
) -> float:
    """
    Welfare change as the uniform percentage change in baseline consumption
    that gives the reform's lifetime utility: ``U((1+λ)·c_base) = U(c_reform)``.

    Returned as λ (0.01 = one percent).  CRRA utility is homogeneous, so
    ``U((1+λ)c) = (1+λ)^{1−σ}·U(c)`` and λ has a closed form.
    """
    u_reform = lifetime_utility(reform_consumption, sigma, beta)
    u_base = lifetime_utility(baseline_consumption, sigma, beta)
    if abs(sigma - 1.0) < 1e-12:
        weight = float(np.sum(beta ** np.arange(len(baseline_consumption), dtype=float)))
        return float(np.exp((u_reform - u_base) / weight) - 1.0)
    return float((u_reform / u_base) ** (1.0 / (1.0 - sigma)) - 1.0)


# ---------------------------------------------------------------------------
# Steady-state aggregation
# ---------------------------------------------------------------------------

def aggregate_household_results(
    params,
    r: float,
    w: float,
    tau_l: float,
    tau_k: float,
    tau_ss: float,
    ss_benefit: float,
) -> tuple[float, float, np.ndarray, np.ndarray]:
    """
    Solve the representative-cohort problem and aggregate to market quantities.

    In a stationary steady state all cohorts face the same constant prices
    (r, w).  The cross-sectional distribution of assets is obtained by
    recognising that cohort j has already accumulated a_j along the common
    optimal path.

    Aggregation (with cohort sizes n_j = (1+n)^{−j}):

        K_supply = Σ_{j=0}^{N−1}  n_j · a_{j+1}    (savings become next-period K)
        L_supply = Σ_{j=0}^{R−1}  n_j · ε_j         (inelastic working-age labour)

    Parameters
    ----------
    params : OLGParameters
    r : float
        Gross interest rate (pre-depreciation).  Net return = r·(1−τ_k).
    w : float
        Wage per unit of efficiency labour.
    tau_l : float
        Labour income tax rate (possibly endogenous under fiscal closure).
    tau_k : float
        Capital income tax rate.
    tau_ss : float
        Social Security payroll tax rate.
    ss_benefit : float
        Annual SS benefit for each retired cohort (in wage units).

    Returns
    -------
    K_supply : float
        Aggregate capital supplied to firms.
    L_supply : float
        Aggregate effective labour supply.
    consumption_path : ndarray, shape (n_cohorts,)
        Optimal per-cohort consumption along the lifecycle.
    assets_path : ndarray, shape (n_cohorts + 1,)
        Asset holdings a_j (a_0 = 0, a_N ≈ 0).
    """
    N = params.n_cohorts
    R = params.retirement_age_cohort
    gross_return = 1.0 + r * (1.0 - tau_k)

    # Disposable labour income for each working-age cohort
    net_wage = w * (1.0 - tau_l - tau_ss)
    net_labor_income = net_wage * params.earnings_profile  # shape (R,)

    consumption_path, assets_path = solve_household(
        n_cohorts=N,
        retirement_cohort=R,
        sigma=params.sigma,
        beta=params.beta,
        gross_return=gross_return,
        net_labor_income=net_labor_income,
        ss_benefit=ss_benefit,
        initial_assets=0.0,
    )

    cohort_sizes = params.cohort_sizes  # n_j = (1+n)^{-j}, shape (N,)

    # Capital supply: cohort j currently holds a_{j+1} in savings
    K_supply = float(np.dot(cohort_sizes, assets_path[1:N + 1]))

    # Labour supply: working cohorts only, weighted by efficiency
    L_supply = float(np.dot(cohort_sizes[:R], params.earnings_profile))

    return K_supply, L_supply, consumption_path, assets_path


# ---------------------------------------------------------------------------
# Cohort-level tax and transfer profiles (used in generational accounting)
# ---------------------------------------------------------------------------

def compute_cohort_tax_profile(
    params,
    r: float,
    w: float,
    tau_l: float,
    tau_k: float,
    tau_ss: float,
    ss_benefit: float,
    assets_path: np.ndarray,
) -> np.ndarray:
    """
    Compute the net tax payment at each lifecycle stage for a cohort.

    Net tax_j = labour_tax_j + capital_tax_j + SS_payroll_j − SS_benefit_j

    Parameters
    ----------
    assets_path : ndarray, shape (n_cohorts + 1,)
        Asset path from ``solve_household``.

    Returns
    -------
    net_taxes : ndarray, shape (n_cohorts,)
        Net taxes (positive = net payer, negative = net recipient).
    """
    N = params.n_cohorts
    R = params.retirement_age_cohort
    eps = params.earnings_profile

    net_taxes = np.zeros(N)
    for j in range(N):
        if j < R:
            labour_income = w * eps[j]
            net_taxes[j] = (
                tau_l * labour_income
                + tau_ss * labour_income
                + tau_k * r * assets_path[j]
            )
        else:
            net_taxes[j] = tau_k * r * assets_path[j] - ss_benefit

    return net_taxes
