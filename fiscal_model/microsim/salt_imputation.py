"""
Impute state-and-local taxes and itemized deductions onto CPS-derived microdata.

The CPS ASEC tax-unit file carries income detail but no deduction detail, so the
microsimulation engine cannot model the SALT cap (everyone defaults to the
standard deduction). This module imputes, transparently and from published
state aggregates:

* ``state_and_local_taxes`` — state + local income tax + property tax, as a
  per-state effective rate on AGI (``state_salt_rates.csv``). Property tax is
  treated as an income-scaled proxy; it is the deductible SALT base.
* ``itemized_deductions`` — SALT plus a mortgage-interest/charitable proxy. The
  engine itself decides whether each unit itemizes (max of standard vs.
  itemized), so over-imputing SALT for low earners is harmless — they take the
  standard deduction regardless.

This is deliberately a reduced-form imputation: it gets the *distribution* of
the SALT-cap benefit right (SALT scales with AGI; the $10K cap binds for high
earners) without claiming return-level precision.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

# Non-SALT itemized deductions (mortgage interest + charitable) as a share of
# AGI for would-be itemizers. Calibrated so the imputed itemizer share roughly
# tracks SOI (~10-12% nationally, higher in high-tax states).
_OTHER_ITEMIZED_RATE = 0.03

# Fallback SALT rate for states absent from state_salt_rates.csv (it covers the
# 10 largest states); the national average of income+local+property components.
_FALLBACK_SALT_RATE = 0.0576

_FIPS_TO_STATE = {
    1: "AL", 2: "AK", 4: "AZ", 5: "AR", 6: "CA", 8: "CO", 9: "CT", 10: "DE",
    11: "DC", 12: "FL", 13: "GA", 15: "HI", 16: "ID", 17: "IL", 18: "IN",
    19: "IA", 20: "KS", 21: "KY", 22: "LA", 23: "ME", 24: "MD", 25: "MA",
    26: "MI", 27: "MN", 28: "MS", 29: "MO", 30: "MT", 31: "NE", 32: "NV",
    33: "NH", 34: "NJ", 35: "NM", 36: "NY", 37: "NC", 38: "ND", 39: "OH",
    40: "OK", 41: "OR", 42: "PA", 44: "RI", 45: "SC", 46: "SD", 47: "TN",
    48: "TX", 49: "UT", 50: "VT", 51: "VA", 53: "WA", 54: "WV", 55: "WI",
    56: "WY",
}

_DEFAULT_SALT_PATH = (
    Path(__file__).resolve().parent.parent
    / "data_files"
    / "state_taxes"
    / "state_salt_rates.csv"
)


def _salt_rate_by_state(salt_path: Path) -> dict[str, float]:
    rates = pd.read_csv(salt_path)
    rate = (
        rates["state_income_tax_rate"]
        + rates["local_income_tax_rate"]
        + rates["property_tax_effective_rate"]
    )
    return dict(zip(rates["state"], rate))


def impute_salt_and_itemized(
    df: pd.DataFrame, *, salt_path: Path | None = None
) -> pd.DataFrame:
    """Return a copy of ``df`` with ``state_and_local_taxes`` and
    ``itemized_deductions`` imputed from ``state_fips`` and ``agi``.

    If both columns are already present, the frame is returned unchanged.
    """
    if "state_and_local_taxes" in df.columns and "itemized_deductions" in df.columns:
        return df
    if "agi" not in df.columns:
        return df

    out = df.copy()
    rate_by_state = _salt_rate_by_state(salt_path or _DEFAULT_SALT_PATH)

    if "state_fips" in out.columns:
        state = out["state_fips"].map(_FIPS_TO_STATE)
        salt_rate = state.map(rate_by_state).fillna(_FALLBACK_SALT_RATE)
    else:
        salt_rate = pd.Series(_FALLBACK_SALT_RATE, index=out.index)

    agi = out["agi"].clip(lower=0)
    out.loc[:, "state_and_local_taxes"] = agi * salt_rate
    out.loc[:, "itemized_deductions"] = out["state_and_local_taxes"] + agi * _OTHER_ITEMIZED_RATE
    return out
