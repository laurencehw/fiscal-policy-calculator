#!/usr/bin/env python3
"""
Leave-one-out cross-validation for the calibrated (Tier 2) modules.

Tier 2's headline ~5% mean error is true by construction: each module carries
one hard-coded annual per benchmark, so it reproduces its own targets because
it was told the answer. This script drops one benchmark's constant at a time
and asks whether the module's structural machinery — calibrated on the others
— can put it back.

Examples
--------
    python scripts/run_loo.py
    python scripts/run_loo.py --json
    python scripts/run_loo.py --donor-matrix
    python scripts/run_loo.py --max-mean-error 75

Cases the machinery genuinely cannot derive (independent constants with no
second benchmark, or a base constant that *is* the published target restated)
are reported as ``not cross-validatable`` with a reason and are never folded
into the aggregate.

Exit code is 0 unless ``--max-mean-error`` is given and the aggregate mean
absolute error exceeds it.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fiscal_model.validation.loo import (  # noqa: E402
    LOOSuite,
    capital_gains_donor_matrix,
    run_leave_one_out,
)


def _fmt(value: float | None, spec: str = ",.1f") -> str:
    return "—" if value is None else format(value, spec)


def print_report(suite: LOOSuite) -> None:
    """Print the per-module LOO table and the aggregate."""
    print()
    print("=" * 108)
    print("  Tier 2 (leave-one-out) — can each module rebuild a held-out benchmark?")
    print("=" * 108)

    header = (
        f"  {'Module':<13} {'Case':<24} {'Kind':<11} "
        f"{'Official':>10} {'By-constr':>10} {'LOO':>10} {'Err':>9}"
    )
    for report in suite.reports:
        print()
        print(f"  {report.module}  —  {report.derivation_kind}")
        print(f"    mechanism: {report.mechanism}")
        print()
        print(header)
        print(f"  {'-' * 13} {'-' * 24} {'-' * 11} {'-' * 10} {'-' * 10} {'-' * 10} {'-' * 9}")
        for case in report.cases:
            kind = {
                "structural": "structural",
                "bottom_up": "bottom-up",
                "not_cross_validatable": "not x-val",
            }.get(case.derivation, case.derivation)
            err = (
                f"{case.percent_error:+.1f}%"
                if case.percent_error is not None
                else "—"
            )
            print(
                f"  {report.module:<13} {case.case_id:<24} {kind:<11} "
                f"{_fmt(case.official_10yr):>10} {_fmt(case.calibrated_10yr):>10} "
                f"{_fmt(case.loo_10yr):>10} {err:>9}"
            )
            if case.exclusion_reason:
                print(f"      excluded: {case.exclusion_reason}")
        mean = report.mean_abs_percent_error
        print(
            f"    module mean abs error: {_fmt(mean)}%"
            f"  (n={len(report.included_cases)} derivable, "
            f"{len(report.excluded_cases)} not cross-validatable)"
        )

    print()
    print("=" * 108)
    print("  Aggregate — Tier 2 (LOO), derivable cases only")
    print("=" * 108)
    included = len(suite.included_cases)
    print(f"  cases in aggregate:        {included}")
    print(f"  not cross-validatable:     {len(suite.excluded_cases)}  (reported, never folded in)")
    print(f"  mean abs percent error:    {_fmt(suite.mean_abs_percent_error)}%")
    print(f"  median abs percent error:  {_fmt(suite.median_abs_percent_error)}%")
    share = f" ({suite.within_15pct / included:.0%})" if included else ""
    print(f"  within 15%:                {suite.within_15pct}/{included}{share}")
    print()
    print("  Compare with the by-construction Tier 2 number (~5%): that one measures")
    print("  bookkeeping, this one measures whether the machinery predicts.")


def print_donor_matrix() -> None:
    """Print the capital-gains elasticity donor matrix."""
    matrix = capital_gains_donor_matrix()
    cases = list(next(iter(matrix.values())))
    print()
    print("=" * 108)
    print("  Capital gains — which elasticity tuple is the answer key?")
    print("=" * 108)
    print("  Signed percent error when the row's scenario donates its behavioural")
    print("  parameters (unset fields fall back to the dataclass defaults).")
    print()
    print(f"  {'donor tuple':<24}" + "".join(f"{c:>24}" for c in cases) + f"{'mean|others|':>14}")
    print(f"  {'-' * 24}" + "".join(f"{'-' * 23:>24}" for c in cases) + f"{'-' * 13:>14}")
    for donor, row in matrix.items():
        others = [abs(v) for cid, v in row.items() if cid != donor]
        mean_others = sum(others) / len(others) if others else float("nan")
        print(
            f"  {donor:<24}"
            + "".join(f"{row[c]:>+24.1f}" for c in cases)
            + f"{mean_others:>14.1f}"
        )
    print()
    print("  The donor with the lowest mean|others| is the module's de facto answer key.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the suite as JSON instead of a human-readable table.",
    )
    parser.add_argument(
        "--donor-matrix",
        action="store_true",
        help=(
            "Also print the capital-gains donor matrix: every case scored under "
            "every scenario's elasticity tuple."
        ),
    )
    parser.add_argument(
        "--max-mean-error",
        type=float,
        default=None,
        help=(
            "Fail (exit 1) when the aggregate mean absolute LOO error over the "
            "derivable cases exceeds this percentage."
        ),
    )
    args = parser.parse_args()

    suite = run_leave_one_out()

    if args.json:
        payload = suite.to_dict()
        if args.donor_matrix:
            payload["capital_gains_donor_matrix"] = capital_gains_donor_matrix()
        print(json.dumps(payload, indent=2, default=str))
    else:
        print_report(suite)
        if args.donor_matrix:
            print_donor_matrix()

    mean = suite.mean_abs_percent_error
    if args.max_mean_error is not None and mean is not None and mean > args.max_mean_error:
        print(
            f"\n  [FAIL] Tier 2 (LOO) mean abs error {mean:.1f}% exceeds "
            f"the {args.max_mean_error:.1f}% ceiling.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
