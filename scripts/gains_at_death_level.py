#!/usr/bin/env python3
"""Measure the gains-at-death level against the death rate used everywhere else.

Prints a JSON record. Changes no score. See planning/memos/GAINS_AT_DEATH_LEVEL.md.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def measure(year: int = 2025) -> dict[str, float | int]:
    """The flow, the stock, and the factor between the two death rates.

    ``factor`` is the NCHS wealth-weighted death rate divided by the share of
    the accrued-gains stock the Poterba & Weisbenner flow removes in a year.
    """
    from fiscal_model.data.capital_gains import CapitalGainsBaseline

    baseline = CapitalGainsBaseline()
    parameters = baseline._parameters
    flow = float(baseline.gains_at_death_billions(year))
    stock = float(baseline.accrued_gains_stock_billions(year))
    net_worth = float(baseline.household_net_worth_billions(year))
    death_exit = float(baseline.death_exit_rate())
    implied_exit = flow / stock
    return {
        "year": year,
        "flow_billions": flow,
        "accrued_stock_billions": stock,
        "net_worth_billions": net_worth,
        "gains_at_death_share_of_net_worth": float(parameters["gains_at_death_share_of_net_worth"]),
        "estate_flow_rate": float(parameters["estate_flow_rate"]),
        "gain_share_of_estates": float(parameters["gain_share_of_estates"]),
        "accrued_gain_share_of_net_worth": float(parameters["accrued_gain_share_of_net_worth"]),
        "death_exit_rate": death_exit,
        "implied_exit_of_stock": implied_exit,
        "factor": death_exit / implied_exit,
        "mortality_times_stock_billions": death_exit * stock,
    }


def main() -> None:
    print(json.dumps(measure(), indent=2))


if __name__ == "__main__":
    main()
