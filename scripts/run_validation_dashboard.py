#!/usr/bin/env python3
"""
Print a validation dashboard for the Fiscal Policy Calculator.

Runs every diagnostic surface the app exposes and prints a single human-
readable report: health check (baseline / FRED / IRS / model / microdata),
CBO score benchmarks, and the SOI calibration of the current microdata
file. Useful for CI, release-readiness checks, and debugging before a
paper submission.

Examples
--------
    python scripts/run_validation_dashboard.py
    python scripts/run_validation_dashboard.py --json
    python scripts/run_validation_dashboard.py --calibration-year 2022

Exit code is 0 when every surface reports ``ok``/``excellent`` and
non-zero when any component degrades, so this can be a CI gate.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fiscal_model.data.cps_asec import describe_microdata, load_tax_microdata  # noqa: E402
from fiscal_model.health import check_health  # noqa: E402
from fiscal_model.microsim.soi_calibration import calibrate_to_soi  # noqa: E402


STATUS_DEGRADED = {"degraded", "error", "needs_improvement", "unknown"}


def _fmt_billion(value: float | None) -> str:
    if value is None:
        return "—"
    if abs(value) >= 1000:
        return f"${value / 1000:+.2f}T"
    return f"${value:+.1f}B"


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.1f}%"


def collect_health() -> dict[str, Any]:
    return check_health()


def collect_microdata(calibration_year: int) -> dict[str, Any]:
    descriptor = describe_microdata()
    if descriptor.get("status") not in {"synthetic", "real"}:
        return {"descriptor": descriptor, "report": None}
    df, _ = load_tax_microdata()
    report = calibrate_to_soi(df, year=calibration_year)
    return {"descriptor": descriptor, "report": report}


def print_banner(title: str) -> None:
    print()
    print("=" * 72)
    print(f"  {title}")
    print("=" * 72)


def print_health(health: dict[str, Any]) -> bool:
    """Return True if every component is ok/warning is acceptable."""
    print_banner("Health check")
    all_ok = True
    for component in ("baseline", "fred", "irs_soi", "model", "microdata"):
        info = health.get(component, {})
        status = info.get("status", "unknown")
        if status in STATUS_DEGRADED:
            all_ok = False
        details: list[str] = []
        if component == "baseline":
            details.append(str(info.get("vintage") or info.get("source", "")))
        elif component == "fred":
            details.append(str(info.get("source", "")))
        elif component == "irs_soi":
            details.append(f"latest {info.get('latest_year', '?')}")
        elif component == "model":
            score = info.get("test_score")
            details.append(f"test_score={score}" if score is not None else "")
        elif component == "microdata":
            returns_pct = info.get("returns_coverage_pct")
            agi_pct = info.get("agi_coverage_pct")
            if returns_pct is not None and agi_pct is not None:
                details.append(
                    f"SOI {info.get('calibration_year', '?')}: "
                    f"returns {returns_pct:.0f}% / AGI {agi_pct:.0f}%"
                )
        rendered = " | ".join(d for d in details if d) or "—"
        print(f"  {component:<10} [{status:>10}]   {rendered}")
    print(f"  overall    [{health.get('overall', 'unknown'):>10}]")
    return all_ok


def print_calibration(calibration: dict[str, Any]) -> bool:
    """Return True if no bracket is flagged as badly miscalibrated."""
    print_banner("SOI calibration")
    descriptor = calibration["descriptor"]
    report = calibration["report"]
    if report is None:
        print(f"  status:   {descriptor.get('status')}")
        print(f"  message:  {descriptor.get('message', 'no report')}")
        return False
    summary = report.summary()
    print(f"  year:                    {int(summary['year'])}")
    print(f"  microsim returns (M):    {summary['total_microsim_returns_millions']:.1f}")
    print(f"  SOI returns (M):         {summary['total_soi_returns_millions']:.1f}")
    print(f"  returns coverage:        {_fmt_pct(summary['returns_coverage_pct'])}")
    print(f"  microsim AGI (T):        {summary['total_microsim_agi_trillions']:.2f}")
    print(f"  SOI AGI (T):             {summary['total_soi_agi_trillions']:.2f}")
    print(f"  AGI coverage:            {_fmt_pct(summary['agi_coverage_pct'])}")
    print()
    print("  Per-bracket ratios (sim/SOI):")
    print(f"    {'AGI bracket':<24} {'returns':>10} {'AGI':>10}")
    print(f"    {'-' * 24} {'-' * 10:>10} {'-' * 10:>10}")
    worst_ratio = 1.0
    for bracket in report.brackets:
        label = (
            f"${bracket.lower:>9,.0f}+"
            if bracket.upper is None
            else f"${bracket.lower:>9,.0f}–${bracket.upper:>9,.0f}"
        )
        r_r = bracket.returns_ratio
        r_a = bracket.agi_ratio
        if r_a is not None and 0 < r_a < 1:
            worst_ratio = min(worst_ratio, r_a)
        print(
            f"    {label:<24} "
            f"{r_r if r_r is not None else 0:>10.2f} "
            f"{r_a if r_a is not None else 0:>10.2f}"
        )
    # Flag as degraded if any bracket's AGI coverage is <60%.
    return worst_ratio >= 0.60


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the raw dashboard as JSON instead of a human-readable report.",
    )
    parser.add_argument(
        "--calibration-year",
        type=int,
        default=None,
        help="SOI year to calibrate against (default: latest available).",
    )
    args = parser.parse_args()

    health = collect_health()
    calibration_year = (
        args.calibration_year
        or health.get("irs_soi", {}).get("latest_year")
        or 2022
    )
    calibration = collect_microdata(calibration_year)

    if args.json:
        report = calibration.get("report")
        payload = {
            "health": {
                k: v
                for k, v in health.items()
                if k != "timestamp"
            },
            "calibration": {
                "year": calibration_year,
                "descriptor": calibration["descriptor"],
                "summary": report.summary() if report else None,
                "brackets": (
                    [
                        {
                            "lower": b.lower,
                            "upper": b.upper,
                            "returns_ratio": b.returns_ratio,
                            "agi_ratio": b.agi_ratio,
                        }
                        for b in report.brackets
                    ]
                    if report
                    else None
                ),
            },
        }
        print(json.dumps(payload, indent=2, default=str))
        return 0

    health_ok = print_health(health)
    calibration_ok = print_calibration(calibration)

    print_banner("Summary")
    if health_ok and calibration_ok:
        print("  [OK] All surfaces nominal.")
        return 0
    if health_ok:
        print("  [WARN] Calibration has at least one bracket with <60% AGI coverage.")
        return 2
    print("  [FAIL] One or more health components degraded.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
