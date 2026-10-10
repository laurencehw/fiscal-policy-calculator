"""
Impute state-and-local taxes and itemized deductions onto CPS-derived microdata.

The CPS ASEC tax-unit file carries income detail but no deduction detail, so the
microsimulation engine cannot model the SALT cap (everyone defaults to the
standard deduction). This module imputes, transparently and from published
state aggregates:

* ``state_and_local_taxes`` — AGI times IRS SOI Table 2.1's ratio of
  state-and-local taxes to AGI for the unit's AGI class (TY2023, itemizers),
  scaled by the unit's state rate relative to the national average
  (``state_salt_rates.csv``: income + local + property tax, so high-tax states
  impute more).
* ``itemized_deductions`` — SALT plus AGI times the same table's ratio of
  mortgage interest plus charitable gifts to AGI for the class. The engine
  itself decides whether each unit itemizes (max of standard vs. itemized).

Before R6c (``planning/lanes/R6c_salt_mechanism_and_calibration_default.md``)
both ratios were constants at every income: the state rate for SALT and 3% for
everything else, while SOI shows the SALT share rising and the mortgage plus
charitable share falling with income. Two approximations remain: Table 2.1 is
an itemizer panel, so applying its ratio to every return overstates SALT for
low-income non-itemizers (who mostly stay below the standard deduction
anyway), and the CPS's AGI-weighted mean state rate is 5.61% against the 5.76%
fallback the scaling divides by, which lowers imputed SALT by about 2.6%.

This is a reduced-form imputation, not return-level precision.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

#: IRS SOI Table 2.1, TY2023, "All returns" panel (returns with itemized
#: deductions by size of AGI), transcribed in Wave 2.
_SOI_ITEMIZED_PATH = (
    Path(__file__).resolve().parents[1]
    / "data_files"
    / "tax_expenditures"
    / "soi_2023_itemized_deductions_by_agi.csv"
)

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


@lru_cache(maxsize=1)
def soi_itemized_ratios() -> pd.DataFrame:
    """SOI Table 2.1 by AGI class: SALT / AGI and (mortgage + charitable) / AGI.

    Both numerator and denominator are in the table's own units (thousands of
    dollars), so the ratios are unit-free. Classes are ordered by ``agi_lower``.
    """
    table = pd.read_csv(_SOI_ITEMIZED_PATH, comment="#").sort_values("agi_lower")
    agi = table["agi_less_deficit"]
    return pd.DataFrame(
        {
            "agi_lower": table["agi_lower"].to_numpy(dtype=float),
            "salt_ratio": (table["salt_amount"] / agi).to_numpy(dtype=float),
            "other_ratio": (
                (table["mortgage_interest_amount"] + table["charitable_amount"]) / agi
            ).to_numpy(dtype=float),
        }
    )


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

    ratios = soi_itemized_ratios()
    agi = out["agi"].clip(lower=0)
    cls = np.searchsorted(ratios["agi_lower"].to_numpy(), agi.to_numpy(), side="right") - 1
    cls = np.clip(cls, 0, len(ratios) - 1)
    state_scale = salt_rate.to_numpy(dtype=float) / _FALLBACK_SALT_RATE
    salt_share = ratios["salt_ratio"].to_numpy()[cls] * state_scale
    other_share = ratios["other_ratio"].to_numpy()[cls]
    out.loc[:, "state_and_local_taxes"] = agi * salt_share
    out.loc[:, "itemized_deductions"] = out["state_and_local_taxes"] + agi * other_share
    return out
