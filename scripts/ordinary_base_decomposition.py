#!/usr/bin/env python3
"""
Split each ordinary-rate row's error into base error and behavioural error.

Lane B2a (``planning/lanes/B2a_cbo_income_path.md``). Reports; changes no score.

CBO's *Revenue Projections, by Category* publishes taxable income by statutory
bracket (``rev_iit_bracket_1..7``), so a **static** base for a bracket-rate
change can be read straight off CBO's own projection: one percentage point on
brackets ``k..7`` raises ``0.01 x sum(rev_iit_bracket_k..7)`` before anyone
responds. Printed beside the model's own static figure, its behavioural offset
and the published total, that separates "the model's base is wrong" from "the
model's response is wrong" before anyone touches the ETI.

Columns, ten-year sums in $B, revenue-raising shown positive:

* ``model_static``   - the scorer's ``static_revenue_effect``
* ``cbo_static``     - ``rate_change x sum of rev_iit_bracket_k..7`` over the
  row's window, on the edition its vintage reads; ``n/a`` for a row whose
  threshold is not a statutory bracket floor (no bracket series matches it)
* ``model_behav``    - the scorer's ``behavioral_offset`` (a reduction)
* ``model_total``    - the scored ten-year revenue (static minus behaviour)
* ``published``      - the official figure
* ``implied_offset`` - ``1 - published / cbo_static``: the behavioural share the
  published total implies if CBO's static base is right

The bracket series is used here only as a **level** for one year at a time,
never as a growth index: in the 2024-06 and 2025-01 editions the bracket
numbering changes meaning in CY2026 (TCJA reversion), which is the reform's own
bracket in that year and so the right static base, but a meaningless ratio.

Years a window reaches that the edition does not publish (CY2019-2020 for the
2018 volume on the 2024-06 edition) are left out and counted in ``years``.

USAGE
-----
    python scripts/ordinary_base_decomposition.py
    python scripts/ordinary_base_decomposition.py --json
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fiscal_model.validation.cbo_scores import get_score  # noqa: E402
from fiscal_model.validation.core import (  # noqa: E402
    _resolve_vintage,
    _resolve_window_start,
    build_scorer_for_vintage,
    create_policy_from_score,
)

DATA_DIR = PROJECT_ROOT / "fiscal_model" / "data_files" / "cbo_income_detail"

#: The eleven out-of-sample rows in the ``ordinary_rate_change`` class.
ORDINARY_ROWS = (
    "biden_high_income_tax",
    "cbo2019_opt1_all_rates_1pp",
    "cbo2019_opt1_top2_brackets_1pp",
    "cbo2019_opt1_top4_brackets_1pp",
    "cbo2021_opt1_all_rates_1pp",
    "cbo2021_opt1_top2_brackets_1pp",
    "cbo2021_opt1_top4_brackets_1pp",
    "cbo2023_opt13_top4_brackets_2pp",
    "cbo_opt45_all_rates_1pp",
    "cbo_opt45_top4_brackets_2pp",
    "illustrative_1pp_all",
)

#: Bracket count under both seven-bracket schedules.
TOP_BRACKET = 7


def _bracket_income() -> dict[tuple[str, int, int], float]:
    table: dict[tuple[str, int, int], float] = {}
    with (DATA_DIR / "cbo_income_detail.csv").open(encoding="utf-8") as fh:
        for row in csv.DictReader(line for line in fh if not line.startswith("#")):
            name = row["variable"]
            if name.startswith("rev_iit_bracket_"):
                k = int(name.rsplit("_", 1)[1])
                table[(row["vintage"], int(row["calendar_year"]), k)] = float(row["value"])
    return table


def _first_bracket(score) -> int | None:
    """The lowest bracket the reform's rate change applies in, if it is one."""
    if score.statutory_bracket_index:
        return int(score.statutory_bracket_index)
    if not score.income_threshold:
        return 1
    return None


def decompose(policy_id: str, brackets: dict) -> dict:
    score = get_score(policy_id)
    if score is None:
        raise SystemExit(f"{policy_id}: no score record")
    vintage = _resolve_vintage(score)
    start = _resolve_window_start(score)
    scorer = build_scorer_for_vintage(vintage, start_year=start)
    policy = create_policy_from_score(score)
    result = scorer.score_policy(policy, dynamic=False)

    model_static = float(result.static_revenue_effect.sum())
    model_behav = float(result.behavioral_offset.sum())
    years = [int(y) for y in result.years]
    vintage_key = vintage.value if vintage is not None else "cbo_feb_2026"

    first = _first_bracket(score)
    cbo_static = None
    covered = 0
    if first is not None and score.rate_change:
        total = 0.0
        for year in years:
            levels = [brackets.get((vintage_key, year, k)) for k in range(first, TOP_BRACKET + 1)]
            if any(level is None for level in levels):
                continue
            covered += 1
            total += sum(level for level in levels if level is not None)
        cbo_static = float(score.rate_change) * total

    published = -float(score.ten_year_cost)
    return {
        "policy_id": policy_id,
        "vintage": vintage_key,
        "window": f"{years[0]}-{years[-1]}",
        "brackets": f"{first}-{TOP_BRACKET}" if first is not None else "n/a",
        "years_with_cbo_base": covered,
        "model_static": round(model_static, 1),
        "cbo_static": None if cbo_static is None else round(cbo_static, 1),
        "model_behav": round(model_behav, 1),
        "model_total": round(-float(result.total_10_year_cost), 1),
        "published": round(published, 1),
        "implied_offset": (
            None if not cbo_static else round(1.0 - published / cbo_static, 3)
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    logging.disable(logging.WARNING)

    brackets = _bracket_income()
    rows = [decompose(pid, brackets) for pid in ORDINARY_ROWS]
    if args.json:
        print(json.dumps(rows, indent=2))
        return 0

    def fmt(value) -> str:
        return "n/a" if value is None else f"{value:,.1f}"

    print(f"{'policy':34s} {'window':9s} {'brk':4s} {'yrs':>3s} {'model_static':>12s} "
          f"{'cbo_static':>10s} {'model_behav':>11s} {'model_total':>11s} "
          f"{'published':>9s} {'impl_off':>8s}")
    for r in rows:
        implied = "n/a" if r["implied_offset"] is None else f"{r['implied_offset']:.3f}"
        print(f"{r['policy_id']:34s} {r['window']:9s} {r['brackets']:4s} "
              f"{r['years_with_cbo_base']:3d} {fmt(r['model_static']):>12s} "
              f"{fmt(r['cbo_static']):>10s} {fmt(r['model_behav']):>11s} "
              f"{fmt(r['model_total']):>11s} {fmt(r['published']):>9s} {implied:>8s}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
