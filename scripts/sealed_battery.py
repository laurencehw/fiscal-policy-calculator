#!/usr/bin/env python3
"""
Report the sealed battery (``fiscal_model/validation/sealed.py``).

Rows whose scoring is still off are listed as entered and not scored, which is
the state every row is in during the commit that enters it. Scored rows are
reported one by one, with their own mean, and never pooled with the 44-row
out-of-sample tier.

Usage:
    python scripts/sealed_battery.py
    python scripts/sealed_battery.py --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fiscal_model.validation.core import validate_policy  # noqa: E402
from fiscal_model.validation.sealed import (  # noqa: E402
    LOCK_DATE,
    RETIRED,
    SEALED_CASES,
    sealed_cases,
)


def build_report() -> dict:
    rows = []
    for case in sealed_cases():
        row = {
            "case_id": case.case_id,
            "name": case.score.name,
            "published_10yr_billions": case.score.ten_year_cost,
            "source": case.score.source.value,
            "window": case.score.budget_window,
            "entered_date": case.entered_date,
            "scoring_enabled": case.scoring_enabled,
            "direction": "cut" if case.score.ten_year_cost > 0 else "rise",
            "limitations": list(case.limitations),
        }
        if case.scoring_enabled:
            result = validate_policy(case.score)
            if result is None:
                row["error"] = "no constructible shape"
            else:
                row["model_10yr_billions"] = round(result.model_10yr, 1)
                row["abs_percent_error"] = round(abs(result.percent_difference), 1)
                row["direction_match"] = bool(result.direction_match)
        rows.append(row)
    # Rule 3: a retired row left the battery, but its result is still shown,
    # beside the reason and outside the battery's own mean.
    retired = []
    for case in SEALED_CASES:
        if case.case_id not in RETIRED:
            continue
        entry = {
            "case_id": case.case_id,
            "published_10yr_billions": case.score.ten_year_cost,
            "reason": RETIRED[case.case_id],
        }
        result = validate_policy(case.score)
        if result is not None and result.accuracy_rating != "Error":
            entry["model_10yr_billions"] = round(result.model_10yr, 1)
            entry["abs_percent_error"] = round(abs(result.percent_difference), 1)
        retired.append(entry)
    scored = [r for r in rows if "abs_percent_error" in r]
    summary = {
        "lock_date": LOCK_DATE,
        "entered": len(rows),
        "scored": len(scored),
        "tax_cuts_entered": sum(1 for r in rows if r["direction"] == "cut"),
        "mean_abs_error": (
            round(sum(r["abs_percent_error"] for r in scored) / len(scored), 1)
            if scored
            else None
        ),
    }
    return {"summary": summary, "rows": rows, "retired": retired}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = build_report()
    if args.json:
        print(json.dumps(report, indent=2))
        return 0
    s = report["summary"]
    print("=" * 72)
    print(f"SEALED BATTERY (locked {s['lock_date']}; never pooled with the 44 rows)")
    print("=" * 72)
    print(
        f"  {s['entered']} rows entered, {s['tax_cuts_entered']} of them tax cuts; "
        f"{s['scored']} scored."
    )
    for r in report["rows"]:
        if "abs_percent_error" in r:
            tail = (
                f"model {r['model_10yr_billions']:+.1f}  "
                f"err {r['abs_percent_error']:.1f}%"
                + ("" if r["direction_match"] else "  WRONG SIGN")
            )
        else:
            tail = "entered, not yet scored"
        print(f"  {r['case_id']:<28}{r['published_10yr_billions']:>+9.1f}  {tail}")
    if s["mean_abs_error"] is not None:
        print(f"  Mean abs error over {s['scored']} sealed rows: {s['mean_abs_error']}%")
    for r in report["retired"]:
        model = (
            f"model {r['model_10yr_billions']:+.1f}  err {r['abs_percent_error']:.1f}%"
            if "model_10yr_billions" in r
            else "model error"
        )
        print(f"  RETIRED {r['case_id']:<20}{r['published_10yr_billions']:>+9.1f}  {model}")
        print(f"          {r['reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
