"""Bracket-specific weight on the taxable-income behavioural offset.

Saez, Slemrod and Giertz (2012, *Journal of Economic Literature* 50(1), eq. 3):
when the marginal rate above a floor ``z*`` changes, the share of the change's
mechanical revenue lost to the taxable-income response is::

    e * tau / (1 - tau) * a,        a = z_m / (z_m - z*)

where ``e`` is the elasticity of taxable income, ``tau`` the marginal rate the
affected income already faces, and ``z_m`` the mean income of those above the
floor. This module computes ``tau / (1 - tau) * a``, replacing the flat 0.5 the
engine applied to every income-tax rate change. Lane:
``planning/lanes/SSG_bracket_behavioural_offset.md``.

Nothing here is typed in. Both terms come from data the repository already
ships:

- ``a`` comes from IRS SOI Table 1.1. It is apportioned across filing statuses
  exactly as the static base is (``IRSSOIData.get_bracket_distribution_by_status``
  and ``_shares_above_threshold``), and measured in the policy's own
  ``income_measure``. ``z*`` is the return-weighted mean of the per-status
  floors, and a $0 floor gives ``a = 1``.
- ``tau`` comes from CBO's statutory ordinary schedule (publication 53724, via
  ``cbo_tax_parameters``) for the SOI tax year. Each status-class's mean
  taxable income per return is placed in its own status's bracket, and the
  rates are weighted by that class's income above the floor, which is the base
  the rate change applies to.

No scorecard target is read.
"""

from __future__ import annotations

from functools import lru_cache

#: The weight the engine used before this lane, kept for every policy the
#: SSG weight does not apply to.
LEGACY_WEIGHT = 0.5


def _schedule_vintage(year: int) -> str | None:
    from fiscal_model import cbo_tax_parameters as ctp

    if not ctp.is_available():
        return None
    for vintage in ctp.schedule_vintages():
        if year in ctp.years_available(vintage):
            return vintage
    return None


def _statutory_marginal_rate(vintage: str, taxable_income: float, status: str, year: int) -> float:
    from fiscal_model import cbo_tax_parameters as ctp

    rate = 0.0
    for index in range(1, ctp.BRACKET_COUNT + 1):
        if taxable_income >= ctp.bracket_floor(vintage, index, status, year):
            rate = ctp.ordinary_rate(vintage, index, year)
    return rate


@lru_cache(maxsize=256)
def ssg_terms(
    thresholds: tuple[tuple[str, float], ...],
    income_measure: str,
    soi_year: int,
) -> tuple[float, float] | None:
    """``(tau, a)`` for per-status floors, or ``None`` if the data are missing."""
    from fiscal_model.data.irs_soi import FILING_STATUSES, IRSSOIData

    soi = IRSSOIData()
    status_years = soi.get_filing_status_years_available()
    if not status_years:
        return None
    year = soi_year if soi_year in status_years else max(status_years)
    vintage = _schedule_vintage(year)
    if vintage is None:
        return None

    floors = dict(thresholds)
    split = soi.get_bracket_distribution_by_status(year)

    rate_x_base = 0.0
    base = 0.0
    income_above = 0.0
    returns_above = 0.0
    floor_x_returns = 0.0
    for status in FILING_STATUSES:
        floor = max(0.0, float(floors[status]))
        for bracket in split[status]:
            share_returns, share_income = soi._shares_above_threshold(bracket, floor)
            if share_returns <= 0.0:
                continue
            returns = bracket.num_returns * share_returns
            if returns <= 0.0:
                continue
            column = bracket.total_agi if income_measure == "agi" else bracket.taxable_income
            income = column * 1e9 * share_income
            mean_taxable = bracket.taxable_income * 1e9 * share_income / returns
            marginal = _statutory_marginal_rate(vintage, mean_taxable, status, year)
            above_floor = max(income - floor * returns, 0.0)
            rate_x_base += marginal * above_floor
            base += above_floor
            income_above += income
            returns_above += returns
            floor_x_returns += floor * returns

    if base <= 0.0 or returns_above <= 0.0:
        return None
    tau = rate_x_base / base
    z_m = income_above / returns_above
    z_star = floor_x_returns / returns_above
    a = z_m / (z_m - z_star) if z_m > z_star else 1.0
    return tau, a


def ssg_weight(
    thresholds: dict[str, float],
    income_measure: str,
    soi_year: int,
) -> float | None:
    """``tau / (1 - tau) * a``, or ``None`` when it cannot be computed."""
    key = tuple(sorted((status, float(value)) for status, value in thresholds.items()))
    terms = ssg_terms(key, income_measure, int(soi_year))
    if terms is None:
        return None
    tau, a = terms
    if tau >= 1.0:
        return None
    return tau / (1.0 - tau) * a
