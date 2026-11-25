"""The corporate capital channel in the dynamic view.

Lane SUPPLY (``planning/lanes/SUPPLY_corporate_capital_channel.md``). For a
``CorporateTaxPolicy`` with a statutory rate change, the change in output that
comes from the change in the C-corporation capital stock, as a share of GDP by
year. FRB/US-Lite adds it to its demand path.

Every input is a file or constant the repository already ships:

- ``EMTR_c``: CBO's effective marginal tax rate on C-corporation capital,
  ``tp_emtr_capital_business_c_corp`` (publication 53724, through
  ``cbo_tax_parameters``). A statutory change scales it proportionally,
  ``dEMTR = EMTR_c x dtau / tau0``. That is an approximation: CBO publishes the
  level, not the derivative.
- ``s``: the C-corporation share of the capital stock, read back from CBO's own
  capital-weighted aggregates, ``s = s_cb x s_bo`` with
  ``s_cb = (E_business - E_pass) / (E_c - E_pass)`` and
  ``s_bo = (E_overall - E_housing) / (E_business - E_housing)``.
- ``alpha``, ``delta``, ``K/Y``: ``constants.CAPITAL_SHARE`` and the OLG
  calibration's BEA targets. User cost ``c = alpha / (K/Y)``, required return
  ``rho = c - delta``.
- ``g``: the scored vintage's own mean real GDP growth over the window.

Then ``dln c = (rho / c) x dEMTR / (1 - EMTR_c)``, the long-run output effect is
``x* = -alpha / (1 - alpha) x s x dln c``, and capital closes the gap at the
Solow rate ``lambda = (1 - alpha)(g + delta)``.

Nothing here reads a scorecard target.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import numpy as np

_EMTR_VARIABLES = (
    "tp_emtr_capital_business_c_corp",
    "tp_emtr_capital_business_passthrough",
    "tp_emtr_capital_business",
    "tp_emtr_capital_housing",
    "tp_emtr_capital_overall",
)


def _capital_calibration() -> tuple[float, float, float]:
    """``(alpha, delta, K/Y)``, the repository's own calibration."""
    from fiscal_model.constants import CAPITAL_SHARE
    from fiscal_model.models.olg.parameters import OLGParameters

    params = OLGParameters()
    return float(CAPITAL_SHARE), float(params.delta), float(_target_ky_ratio())


def _target_ky_ratio() -> float:
    import inspect

    from fiscal_model.models.olg import calibration

    default = inspect.signature(calibration.calibrate_beta).parameters["target_ky_ratio"].default
    return float(default)


def _vintage(baseline: Any) -> str | None:
    from fiscal_model import cbo_tax_parameters as ctp

    if not ctp.is_available():
        return None
    key = str(getattr(baseline, "baseline_vintage_key", "") or "")
    vintages = ctp.schedule_vintages()
    if key in vintages:
        return key
    return ctp.DEFAULT_BASELINE_VINTAGE if ctp.DEFAULT_BASELINE_VINTAGE in vintages else None


@lru_cache(maxsize=8)
def emtr_years(vintage: str) -> tuple[int, ...]:
    """The calendar years for which this edition publishes all five EMTRs.

    CBO's schedule starts the EMTR series a year or two after the statutory
    rows, so this is narrower than ``years_available``.
    """
    from fiscal_model import cbo_tax_parameters as ctp

    out = []
    for year in ctp.years_available(vintage):
        try:
            for name in _EMTR_VARIABLES:
                ctp.parameter(vintage, name, year)
        except (KeyError, ctp.TaxParameterError):
            continue
        out.append(year)
    return tuple(out)


def _emtrs(vintage: str, year: int) -> tuple[float, ...] | None:
    """The five EMTRs for ``year``, held at the nearest published year outside."""
    from fiscal_model import cbo_tax_parameters as ctp

    years = emtr_years(vintage)
    if not years:
        return None
    y = min(max(year, years[0]), years[-1])
    return tuple(ctp.parameter(vintage, name, y) / 100.0 for name in _EMTR_VARIABLES)


def c_corp_capital_share(vintage: str, year: int) -> float | None:
    """C-corporation share of the capital stock implied by CBO's aggregates."""
    rates = _emtrs(vintage, year)
    if rates is None:
        return None
    e_c, e_pass, e_bus, e_house, e_all = rates
    if e_c == e_pass or e_bus == e_house:
        return None
    return ((e_bus - e_pass) / (e_c - e_pass)) * ((e_all - e_house) / (e_bus - e_house))


def applies_to(policy: Any) -> bool:
    """Whether the channel prices this policy: a corporate statutory rate change."""
    from fiscal_model.corporate import CorporateTaxPolicy

    return isinstance(policy, CorporateTaxPolicy) and float(policy.rate_change or 0.0) != 0.0


def corporate_supply_path(policy: Any, baseline: Any) -> np.ndarray | None:
    """Output change as a fraction of GDP, by year of ``baseline``.

    ``None`` when the channel does not apply or its data are missing.
    """
    if not applies_to(policy):
        return None
    vintage = _vintage(baseline)
    years = np.asarray(getattr(baseline, "years", []), dtype=int)
    real_gdp = np.asarray(getattr(baseline, "real_gdp", []), dtype=float)
    if vintage is None or len(years) == 0 or len(real_gdp) < 2 or np.any(real_gdp <= 0):
        return None

    alpha, delta, ky = _capital_calibration()
    user_cost = alpha / ky
    required_return = user_cost - delta
    growth = float(np.mean(real_gdp[1:] / real_gdp[:-1] - 1.0))
    speed = (1.0 - alpha) * (growth + delta)

    tau0 = float(policy.baseline_rate)
    dtau = float(policy.rate_change)
    start = int(getattr(policy, "start_year", years[0]) or years[0])
    duration = int(getattr(policy, "duration_years", len(years)) or len(years))

    path = np.zeros(len(years))
    gap = 0.0
    for t, year in enumerate(years):
        rates = _emtrs(vintage, int(year))
        share = c_corp_capital_share(vintage, int(year))
        if rates is None or share is None:
            return None
        e_c = rates[0]
        active = start <= int(year) < start + duration
        d_emtr = e_c * dtau / tau0 if active else 0.0
        d_ln_cost = (required_return / user_cost) * d_emtr / (1.0 - e_c)
        target = -alpha / (1.0 - alpha) * share * d_ln_cost
        gap += speed * (target - gap)
        path[t] = gap
    return path


def supply_feedback_caption(macro_result: Any) -> str | None:
    """Decision 6 caption for a dynamic view that carries the supply channel.

    The feedback without the channel is computed from the same run (total minus
    the supply part the adapter recorded), never stored. ``None`` when the run
    had no supply channel.
    """
    from fiscal_model.ui.formatting import format_money

    supply = getattr(macro_result, "supply_revenue_feedback_billions", None)
    if supply is None:
        return None
    total = float(np.sum(macro_result.revenue_feedback_billions))
    supply_total = float(np.sum(supply))
    demand_only = total - supply_total
    return (
        "Changed 2026-11-25: the dynamic view now includes a supply-side channel "
        "for corporate statutory rate changes, the change in the C-corporation "
        "capital stock, built from CBO's own effective marginal tax rates. It "
        f"adds {format_money(supply_total, decimals=1, thousands=False)} of revenue "
        "feedback; on demand alone the feedback would be "
        f"{format_money(demand_only, decimals=1, thousands=False)}, against "
        f"{format_money(total, decimals=1, thousands=False)} with it. The "
        "conventional score is unchanged."
    )
