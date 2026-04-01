"""
Firm Production — Cobb-Douglas with competitive factor markets.

Representative firm maximises profits subject to:

    Y = A · K^α · L^{1−α}

Factor market clearing (perfect competition):

    r + δ = MPK = α · Y / K    →    r = α · A · (L/K)^{1−α} − δ
    w     = MPL = (1−α) · Y / L = (1−α) · A · (K/L)^α

These are the standard relations from Cobb-Douglas production with
constant returns to scale.
"""

from __future__ import annotations

import numpy as np


# ---------------------------------------------------------------------------
# Factor prices
# ---------------------------------------------------------------------------

def factor_prices(
    K: float,
    L: float,
    alpha: float,
    delta: float,
    tfp: float = 1.0,
) -> tuple[float, float]:
    """
    Compute competitive factor prices from aggregate K and L.

    Parameters
    ----------
    K : float
        Aggregate capital stock.
    L : float
        Aggregate effective labour (efficiency-weighted).
    alpha : float
        Capital income share.
    delta : float
        Capital depreciation rate.
    tfp : float
        Total factor productivity (default 1).

    Returns
    -------
    r : float
        Net interest rate (= MPK − δ).
    w : float
        Wage per unit of efficiency labour (= MPL).
    """
    K = max(K, 1e-10)
    L = max(L, 1e-10)
    KL = K / L
    r = alpha * tfp * KL ** (alpha - 1.0) - delta
    w = (1.0 - alpha) * tfp * KL ** alpha
    return r, w


def output(
    K: float,
    L: float,
    alpha: float,
    tfp: float = 1.0,
) -> float:
    """Aggregate output Y = A · K^α · L^{1−α}."""
    K = max(K, 1e-10)
    L = max(L, 1e-10)
    return tfp * (K ** alpha) * (L ** (1.0 - alpha))


def capital_labour_ratio(K: float, L: float) -> float:
    """Capital per unit of effective labour k = K/L."""
    return K / max(L, 1e-10)


# ---------------------------------------------------------------------------
# Golden-rule and Modified Golden-rule capital
# ---------------------------------------------------------------------------

def golden_rule_capital(
    L: float,
    alpha: float,
    delta: float,
    pop_growth: float = 0.005,
    tfp_growth: float = 0.015,
    tfp: float = 1.0,
) -> float:
    """
    Golden-rule capital: maximises steady-state consumption per worker.

    MPK = δ + n + g   →   K* = (α·A / (δ + n + g))^{1/(1−α)} · L
    """
    effective_growth = delta + pop_growth + tfp_growth
    k_golden = (alpha * tfp / effective_growth) ** (1.0 / (1.0 - alpha))
    return k_golden * L


def modified_golden_rule_capital(
    L: float,
    alpha: float,
    delta: float,
    beta: float,
    sigma: float,
    tfp: float = 1.0,
) -> float:
    """
    Modified golden-rule capital: satisfies the Ramsey optimal condition.

    In a Ramsey model, r* = (1/β − 1) + σ·g  (approximately).
    Here we use the simple approximation r* = 1/β − 1.

    MPK = r* + δ = 1/β − 1 + δ
    K* = (α·A / (1/β − 1 + δ))^{1/(1−α)} · L
    """
    r_star = 1.0 / beta - 1.0
    k_star = (alpha * tfp / (r_star + delta)) ** (1.0 / (1.0 - alpha))
    return k_star * L
