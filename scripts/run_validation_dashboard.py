#!/usr/bin/env python3
"""
Print a validation dashboard for the Fiscal Policy Calculator.

Runs every diagnostic surface the app exposes and prints a single human-
readable report: health check (runtime / baseline / FRED / IRS / model /
microdata), CBO score benchmarks, and the SOI calibration of the current microdata
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
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fiscal_model.data.cps_asec import describe_microdata, load_tax_microdata  # noqa: E402
from fiscal_model.health import check_health  # noqa: E402
from fiscal_model.microsim.filing_threshold import filter_to_filers  # noqa: E402
from fiscal_model.microsim.soi_calibration import calibrate_to_soi  # noqa: E402
from fiscal_model.microsim.top_tail import augment_top_tail  # noqa: E402
from fiscal_model.validation.benchmark_runners import default_model_runner  # noqa: E402
from fiscal_model.validation.cbo_distributions import (  # noqa: E402
    run_full_cbo_jct_validation,
)

STATUS_DEGRADED = {"degraded", "error", "needs_improvement", "unknown"}
HEALTH_COMPONENTS = ("runtime", "baseline", "fred", "irs_soi", "model", "microdata")
CALIBRATION_AGI_RATIO_MIN = 0.60
UTC = timezone.utc


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


def collect_microdata(
    calibration_year: int,
    *,
    augment_top_tail_flag: bool = False,
    filter_to_filers_flag: bool = False,
) -> dict[str, Any]:
    descriptor = describe_microdata()
    if descriptor.get("status") not in {"synthetic", "real"}:
        return {
            "descriptor": descriptor,
            "report": None,
            "augmentation": None,
            "filter": None,
        }
    df, _ = load_tax_microdata()
    augmentation_report = None
    if augment_top_tail_flag:
        df, augmentation_report = augment_top_tail(df, year=calibration_year)
    filter_report = None
    if filter_to_filers_flag:
        df, filter_report = filter_to_filers(df, year=calibration_year)
    report = calibrate_to_soi(df, year=calibration_year)
    return {
        "descriptor": descriptor,
        "report": report,
        "augmentation": augmentation_report,
        "filter": filter_report,
    }


def _serialize_operation_report(report: Any) -> dict[str, Any] | None:
    """Serialize optional microdata operation reports for JSON artifacts."""
    if report is None:
        return None
    data = asdict(report) if is_dataclass(report) else dict(vars(report))
    if hasattr(report, "rows_removed"):
        data["rows_removed"] = report.rows_removed
    if hasattr(report, "weighted_removed"):
        data["weighted_removed"] = report.weighted_removed
    return data


def print_banner(title: str) -> None:
    print()
    print("=" * 72)
    print(f"  {title}")
    print("=" * 72)


def _is_environmental_degradation(component: str, info: dict[str, Any]) -> bool:
    """
    True when a health component's ``degraded`` / ``unknown`` status is
    environmental — i.e. expected on a CI runner without API keys —
    rather than a model regression.

    Two sources of legitimate env-degradation:

    - FRED: without ``FRED_API_KEY``, FRED calls can use cache or documented
      fallback data and report ``status=degraded``. This is env-ok for CI,
      but a stale bundled seed is a repository-maintenance issue and should
      fail the gate until the tracked seed is refreshed.
    - Baseline: depends on FRED, so it inherits the same pattern.
      ``source=hardcoded_fallback`` or ``gdp_source=irs_ratio_proxy``
      both indicate env-driven fallback. An explicit ``load_error``
      means the baseline module crashed on its own — that does fail.
    """
    status = info.get("status")
    if component == "fred":
        if status == "error":
            return False
        return info.get("source") in {"cache", "fallback"}
    if component == "baseline":
        if status == "error" or info.get("load_error"):
            return False
        gdp_fell_back = info.get("gdp_source") == "irs_ratio_proxy"
        src_fell_back = info.get("source") == "hardcoded_fallback"
        return gdp_fell_back or src_fell_back
    return False


def print_health(health: dict[str, Any]) -> bool:
    """
    Return True unless a *non-environmental* health component degraded.

    Environmental degradations (FRED fallback without API key, baseline
    GDP proxy) are reported as ``[env-ok]`` but don't trip the gate.
    When a component *does* trip, we print its full payload at the end
    of the section so the CI log shows exactly what regressed.
    """
    print_banner("Health check")
    all_ok = True
    failing_components: list[tuple[str, dict[str, Any]]] = []
    for component in HEALTH_COMPONENTS:
        info = health.get(component, {})
        status = info.get("status", "unknown")
        if status in STATUS_DEGRADED:
            if _is_environmental_degradation(component, info):
                status = f"env-ok ({status})"
            else:
                all_ok = False
                failing_components.append((component, info))
        details: list[str] = []
        if component == "runtime":
            details.append(
                f"Python {info.get('python_version', '?')} "
                f"(supported {info.get('supported_range', '?')})"
            )
        elif component == "baseline":
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

    if failing_components:
        print()
        print("Failing-component diagnostics (what tripped the gate):")
        for name, info in failing_components:
            print(f"  --- {name} ---")
            for k, v in sorted(info.items()):
                rendered_v = str(v)
                if len(rendered_v) > 200:
                    rendered_v = rendered_v[:200] + "…"
                print(f"    {k}: {rendered_v}")

    return all_ok


def health_gate_ok(health: dict[str, Any]) -> bool:
    """Silent equivalent of print_health for JSON/reporting paths."""
    return not health_gate_issues(health)


def _health_issue_message(component: str, info: dict[str, Any]) -> str:
    if info.get("message"):
        return str(info["message"])
    if info.get("error"):
        return str(info["error"])
    if info.get("load_error"):
        return str(info["load_error"])
    if component == "runtime":
        return (
            f"Python {info.get('python_version', '?')} is outside supported range "
            f"{info.get('supported_range', '?')}."
        )
    if component == "microdata":
        returns_pct = info.get("returns_coverage_pct")
        agi_pct = info.get("agi_coverage_pct")
        if returns_pct is not None and agi_pct is not None:
            return f"SOI coverage degraded: returns {returns_pct}% / AGI {agi_pct}%."
    return f"{component} health status is {info.get('status', 'unknown')}."


def health_gate_issues(health: dict[str, Any]) -> list[dict[str, Any]]:
    """Return non-environmental health degradations in artifact-friendly form."""
    issues: list[dict[str, Any]] = []
    for component in HEALTH_COMPONENTS:
        info = health.get(component, {})
        status = info.get("status", "unknown")
        if status in STATUS_DEGRADED and not _is_environmental_degradation(component, info):
            issues.append(
                {
                    "surface": "health",
                    "severity": "fail",
                    "component": component,
                    "status": status,
                    "message": _health_issue_message(component, info),
                }
            )
    return issues


def print_benchmarks() -> bool:
    """Return True if no benchmark is rated needs_improvement."""
    print_banner("CBO/JCT distributional benchmarks")
    try:
        comparisons = run_full_cbo_jct_validation(default_model_runner)
    except Exception as exc:
        print(f"  [ERROR] Benchmark runner crashed: {exc}")
        return False
    if not comparisons:
        print("  (no benchmarks ran — no mapped policies)")
        return True

    all_ok = True
    print(f"    {'Source':<9} {'Rating':<17} {'Err (pp)':>9}  Benchmark")
    print(f"    {'-' * 9} {'-' * 17} {'-' * 9}  {'-' * 40}")
    for c in comparisons:
        source = c.benchmark.source.value.split()[0]
        rating = c.overall_rating
        err = c.mean_absolute_share_error_pp
        err_str = f"{err:.2f}" if err is not None else "—"
        name = c.benchmark.policy_name[:50]
        print(f"    {source:<9} {rating:<17} {err_str:>9}  {name}")
        if rating == "needs_improvement":
            all_ok = False
    return all_ok


def calibration_gate_ok(calibration: dict[str, Any]) -> bool:
    """Silent equivalent of print_calibration for JSON/reporting paths."""
    return not calibration_gate_issues(calibration)


def _format_agi_bracket(lower: float, upper: float | None) -> str:
    if upper is None:
        return f"${lower:,.0f}+"
    return f"${lower:,.0f}-${upper:,.0f}"


def calibration_gate_issues(calibration: dict[str, Any]) -> list[dict[str, Any]]:
    """Return calibration brackets whose SOI AGI coverage is below threshold."""
    report = calibration["report"]
    if report is None:
        descriptor = calibration.get("descriptor", {})
        return [
            {
                "surface": "calibration",
                "severity": "warn",
                "message": descriptor.get("message", "SOI calibration report unavailable."),
                "status": descriptor.get("status"),
            }
        ]
    issues: list[dict[str, Any]] = []
    for bracket in report.brackets:
        agi_ratio = bracket.agi_ratio
        if agi_ratio is None or agi_ratio >= CALIBRATION_AGI_RATIO_MIN:
            continue
        label = _format_agi_bracket(bracket.lower, bracket.upper)
        issues.append(
            {
                "surface": "calibration",
                "severity": "warn",
                "lower": bracket.lower,
                "upper": bracket.upper,
                "returns_ratio": bracket.returns_ratio,
                "agi_ratio": agi_ratio,
                "threshold": CALIBRATION_AGI_RATIO_MIN,
                "message": (
                    f"AGI coverage ratio {agi_ratio:.2f} is below "
                    f"{CALIBRATION_AGI_RATIO_MIN:.2f} for bracket {label}."
                ),
            }
        )
    return issues


def benchmarks_gate_ok(benchmarks: list[dict[str, Any]]) -> bool:
    """Return False when a benchmark failed to run or needs improvement."""
    return not benchmark_gate_issues(benchmarks)


def benchmark_gate_issues(benchmarks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return distributional benchmark failures in artifact-friendly form."""
    issues: list[dict[str, Any]] = []
    for benchmark in benchmarks:
        if "error" in benchmark:
            issues.append(
                {
                    "surface": "distributional_benchmarks",
                    "severity": "fail",
                    "message": f"Benchmark runner failed: {benchmark['error']}",
                }
            )
            continue
        if benchmark.get("rating") == "needs_improvement":
            issues.append(
                {
                    "surface": "distributional_benchmarks",
                    "severity": "fail",
                    "policy_id": benchmark.get("policy_id"),
                    "rating": benchmark.get("rating"),
                    "mean_absolute_share_error_pp": benchmark.get(
                        "mean_absolute_share_error_pp"
                    ),
                    "message": (
                        "Distributional benchmark needs improvement: "
                        f"{benchmark.get('policy_id', 'unknown policy')}."
                    ),
                }
            )
    return issues


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
        if r_a is not None and r_a < worst_ratio:
            worst_ratio = min(worst_ratio, r_a)
        print(
            f"    {label:<24} "
            f"{r_r if r_r is not None else 0:>10.2f} "
            f"{r_a if r_a is not None else 0:>10.2f}"
        )
    # Flag as degraded if any bracket's AGI coverage is <60%.
    return worst_ratio >= CALIBRATION_AGI_RATIO_MIN


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
    parser.add_argument(
        "--augment-top-tail",
        action="store_true",
        help=(
            "Inject SOI-derived synthetic high-income records (>$2M) "
            "before calibrating. Fixes the CPS top-coding gap at the "
            "$10M+ bracket. Changes distributional-analysis results."
        ),
    )
    parser.add_argument(
        "--filter-to-filers",
        action="store_true",
        help=(
            "Drop CPS tax units that are clearly non-filers (no income, "
            "no children, below statutory threshold). Aligns aggregate "
            "microdata totals with SOI's filed-return counts."
        ),
    )
    args = parser.parse_args()

    health = collect_health()
    calibration_year = (
        args.calibration_year
        or health.get("irs_soi", {}).get("latest_year")
        or 2022
    )
    calibration = collect_microdata(
        calibration_year,
        augment_top_tail_flag=args.augment_top_tail,
        filter_to_filers_flag=args.filter_to_filers,
    )

    if args.json:
        report = calibration.get("report")
        try:
            comparisons = run_full_cbo_jct_validation(default_model_runner)
            benchmarks_json = [
                {
                    "policy_id": c.benchmark.policy_id,
                    "source": c.benchmark.source.value,
                    "rating": c.overall_rating,
                    "mean_absolute_share_error_pp": c.mean_absolute_share_error_pp,
                    "matched_rows": len(c.per_group),
                    "benchmark_rows": len(c.benchmark.rows),
                }
                for c in comparisons
            ]
        except Exception as exc:  # pragma: no cover - best-effort diagnostic
            benchmarks_json = [{"error": str(exc)}]

        payload = {
            "health": {
                k: v
                for k, v in health.items()
                if k != "timestamp"
            },
            "calibration": {
                "year": calibration_year,
                "descriptor": calibration["descriptor"],
                "augmentation": _serialize_operation_report(
                    calibration.get("augmentation")
                ),
                "filter": _serialize_operation_report(calibration.get("filter")),
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
            "distributional_benchmarks": benchmarks_json,
        }
        gates = {
            "health": health_gate_ok(health),
            "calibration": calibration_gate_ok(calibration),
            "distributional_benchmarks": benchmarks_gate_ok(benchmarks_json),
        }
        issues = [
            *health_gate_issues(health),
            *calibration_gate_issues(calibration),
            *benchmark_gate_issues(benchmarks_json),
        ]
        if not gates["health"] or not gates["distributional_benchmarks"]:
            overall = "fail"
        elif not gates["calibration"]:
            overall = "warn"
        else:
            overall = "ok"
        payload.update({
            "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "overall": overall,
            "gates": gates,
            "issues": issues,
        })
        print(json.dumps(payload, indent=2, default=str))
        return 0

    health_ok = print_health(health)
    calibration_ok = print_calibration(calibration)
    benchmarks_ok = print_benchmarks()

    print_banner("Summary")
    if health_ok and calibration_ok and benchmarks_ok:
        print("  [OK] All surfaces nominal.")
        return 0
    if not health_ok:
        print("  [FAIL] One or more health components degraded.")
        return 1
    if not benchmarks_ok:
        print("  [FAIL] At least one distributional benchmark flagged needs_improvement.")
        return 1
    print("  [WARN] Calibration has at least one bracket with <60% AGI coverage.")
    return 2


if __name__ == "__main__":
    sys.exit(main())
