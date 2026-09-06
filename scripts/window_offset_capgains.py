#!/usr/bin/env python3
"""
Quantify the target-window offset on the two Green Book capital-gains rows.

``treasury_capgains_39_plus_stepup_elim`` carries the FY2022 Green Book's
combined "Reform the taxation of capital income" row, published over
**FY2022-2031** on a 2021 baseline. Tier 1's default window is **FY2025-2034**
(``DEFAULT_VALIDATION_START_YEAR``), and both of this shape's channels grow with
the same constant - ``household_net_worth_growth_rate`` in
``fiscal_model/data_files/capital_gains/accrued_gains_parameters.csv`` - so a
window three years later mechanically scores higher. This script measures how
much of the row's error that is. It is the evidence behind
``planning/memos/FY2022_TARGET_WINDOW.md`` and behind the manifest row that
moved this case onto its own decade
(``treasury_capgains_39_plus_stepup_elim.v2``), so the "default decade" column
is now the **counterfactual** for that row and the live scorecard reports the
"own window" one.

``biden_capital_gains_39`` is the control: same policy shape, same module, same
elasticities, but its FY2025 Green Book target is published over FY2025-2034,
which is exactly the default window. Its offset must be zero, and the script
prints it so the measurement on the first row is not a claim about the
mechanism in general.

The measurement is a **re-score, not a discount**: the policy is scored again on
a scorer whose baseline window opens in the target's own first year. That works
without a 2021 baseline vintage because ``CapitalGainsPolicy`` reads no baseline
at all - ``estimate_static_revenue_effect`` opens with ``_ = baseline_revenue``
and the death channel is priced off Financial Accounts net worth. The analytic
``(1+g)^-3`` discount is printed beside it as a check on that reasoning, and the
gap between the two is the death channel's per-donor exclusion and rate steps,
which are not homogeneous in the growth factor.

Usage:
    python scripts/window_offset_capgains.py
    python scripts/window_offset_capgains.py --json
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fiscal_model.data.capital_gains import CapitalGainsBaseline  # noqa: E402
from fiscal_model.validation.cbo_scores import KNOWN_SCORES  # noqa: E402
from fiscal_model.validation.core import (  # noqa: E402
    DEFAULT_VALIDATION_START_YEAR,
    build_scorer_for_vintage,
    create_policy_from_score,
)

#: The rows this script measures, with the first fiscal year of the window
#: *their own document* published. Both are transcribed from the record's
#: ``budget_window`` field, which has carried them since the records were
#: entered; nothing here is chosen.
CASES: dict[str, int] = {
    "treasury_capgains_39_plus_stepup_elim": 2022,  # FY2022-2031
    "biden_capital_gains_39": 2025,  # FY2025-2034 - the control
}


@dataclass(frozen=True)
class WindowScore:
    """One policy scored over one ten-year window."""

    first_year: int
    total: float
    rate_channel: float
    death_channel: float
    annual: tuple[float, ...]


def _score_channels(policy, first_year: int) -> WindowScore:
    """Score ``policy`` over the decade opening in ``first_year``.

    The rate and death channels are separate addends of the same score, so the
    split is exact: re-scoring with ``score_gains_at_death=False`` leaves the
    lock-in wedge (which ``eliminate_step_up`` sets) in place and removes only
    the death addend.
    """
    scorer = build_scorer_for_vintage(None, start_year=first_year)

    windowed = copy.deepcopy(policy)
    windowed.start_year = first_year
    total_result = scorer.score_policy(windowed, dynamic=False)

    rate_only = copy.deepcopy(windowed)
    rate_only.score_gains_at_death = False
    rate_result = scorer.score_policy(rate_only, dynamic=False)

    total = float(total_result.total_10_year_cost)
    rate = float(rate_result.total_10_year_cost)
    return WindowScore(
        first_year=first_year,
        total=total,
        rate_channel=-rate,
        death_channel=-(total - rate),
        annual=tuple(float(x) for x in total_result.final_deficit_effect),
    )


def growth_rate() -> float:
    """The one constant both channels grow at."""
    data = CapitalGainsBaseline()
    return float(data._parameters["household_net_worth_growth_rate"])


def build_report() -> dict:
    g = growth_rate()
    rows = []
    for policy_id, source_first_year in CASES.items():
        score = KNOWN_SCORES[policy_id]
        policy = create_policy_from_score(score)
        if policy is None:  # pragma: no cover - shape is constructible today
            raise SystemExit(f"{policy_id}: no constructible shape")

        scored = _score_channels(policy, DEFAULT_VALIDATION_START_YEAR)
        on_source = _score_channels(policy, source_first_year)
        shift = DEFAULT_VALIDATION_START_YEAR - source_first_year
        discount = (1.0 + g) ** (-shift)

        official = float(score.ten_year_cost)
        rows.append(
            {
                "policy_id": policy_id,
                "official_10yr_billions": official,
                "source_window": score.budget_window,
                "source_first_year": source_first_year,
                "scored_first_year": DEFAULT_VALIDATION_START_YEAR,
                "window_shift_years": shift,
                "scored": {
                    "total": round(scored.total, 1),
                    "rate_channel": round(scored.rate_channel, 2),
                    "death_channel": round(scored.death_channel, 2),
                    "abs_percent_error": round(
                        abs((scored.total - official) / official) * 100, 1
                    ),
                    "annual": [round(x, 2) for x in scored.annual],
                },
                "on_source_window": {
                    "total": round(on_source.total, 1),
                    "rate_channel": round(on_source.rate_channel, 2),
                    "death_channel": round(on_source.death_channel, 2),
                    "abs_percent_error": round(
                        abs((on_source.total - official) / official) * 100, 1
                    ),
                    "annual": [round(x, 2) for x in on_source.annual],
                },
                "analytic_discount_factor": round(discount, 6),
                "analytic_total_both_channels": round(scored.total * discount, 1),
                "analytic_total_rate_channel_only": round(
                    -(scored.rate_channel * discount + scored.death_channel), 1
                ),
            }
        )

    return {"growth_rate": g, "cases": rows}


def _print_human(report: dict) -> None:
    g = report["growth_rate"]
    print("=" * 74)
    print("TARGET-WINDOW OFFSET - the two Green Book capital-gains rows")
    print("=" * 74)
    print(
        f"  Both channels grow at household_net_worth_growth_rate = {g:.6f}\n"
        f"  ({g * 100:.2f}%/yr): the rate channel through "
        f"realizations_projection_factor,\n"
        f"  the death channel through gains_at_death_billions. A window k years\n"
        f"  later therefore scores about (1+g)^k higher, mechanically."
    )
    for row in report["cases"]:
        print()
        print("-" * 74)
        print(f"  {row['policy_id']}")
        print("-" * 74)
        print(
            f"  official {row['official_10yr_billions']:+.1f}B over "
            f"{row['source_window']}; default decade FY"
            f"{row['scored_first_year']}-{row['scored_first_year'] + 9}"
        )
        for key, label in (
            ("scored", f"on the default decade (FY{row['scored_first_year']})"),
            ("on_source_window", f"on its own window (FY{row['source_first_year']})"),
        ):
            block = row[key]
            print(
                f"    {label:<34}{block['total']:>+10.1f}B  "
                f"rate {block['rate_channel']:>8.2f}  "
                f"death {block['death_channel']:>7.2f}  "
                f"err {block['abs_percent_error']:>5.1f}%"
            )
        print(
            f"    analytic (1+g)^-{row['window_shift_years']} on both channels"
            f"      {row['analytic_total_both_channels']:>+10.1f}B"
        )
        print(
            f"    analytic on the rate channel only    "
            f"      {row['analytic_total_rate_channel_only']:>+10.1f}B"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a table.")
    args = parser.parse_args(argv)

    report = build_report()
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        _print_human(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
