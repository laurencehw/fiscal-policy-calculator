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
import traceback
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
from fiscal_model.validation.loo import LOOSuite, run_leave_one_out  # noqa: E402

STATUS_DEGRADED = {"degraded", "error", "needs_improvement", "unknown"}
HEALTH_COMPONENTS = ("runtime", "baseline", "fred", "irs_soi", "model", "microdata")
CALIBRATION_AGI_RATIO_MIN = 0.60
UTC = timezone.utc

# Tier 2 (leave-one-out) ceiling. The observed aggregate mean absolute error
# over the derivable cases is ~59%; the gate sits at that x 1.25, rounded to
# the nearest 5, so it catches a regression in the structural machinery without
# tripping on ordinary re-calibration noise. This is a *held-out* number and is
# expected to be an order of magnitude worse than the by-construction ~5%.
DEFAULT_MAX_LOO_MEAN_ERROR = 75.0


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
        if gdp_fell_back or src_fell_back:
            return True
        # A fresh bundled FRED seed is the designed offline mode (mirrors
        # the strict readiness gate); an *expired* seed stays a gate
        # failure — that is the repository-maintenance signal.
        fred = info.get("fred", {})
        fred_bundled_fresh = (
            isinstance(fred, dict)
            and fred.get("source") == "bundled"
            and not fred.get("cache_is_expired")
        )
        return info.get("gdp_source") == "fred_bundled" and fred_bundled_fresh
    return False


def _is_coverage_overcount_warning(component: str, info: dict[str, Any]) -> bool:
    """Microdata degraded *only* because coverage exceeds SOI (>110%).

    Overcounting (e.g. 119% of SOI returns) is a bundled-data quality
    signal, the same class as the calibration warning (exit 2): it must
    not render a green health check, but it isn't a per-PR regression, so
    it warns instead of hard-failing the gate. Undercount (<70%) and
    synthetic data still fail.
    """
    if component != "microdata" or info.get("status") != "degraded":
        return False
    if info.get("coverage_undercount"):
        return False
    return bool(info.get("coverage_overcount"))


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
            elif _is_coverage_overcount_warning(component, info):
                status = f"warn ({status})"
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
    return not any(
        issue["severity"] == "fail" for issue in health_gate_issues(health)
    )


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
            severity = (
                "warn"
                if _is_coverage_overcount_warning(component, info)
                else "fail"
            )
            issues.append(
                {
                    "surface": "health",
                    "severity": severity,
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
    print(
        f"    {'Source':<9} {'Universe (scored)':<21} {'Rating':<17} "
        f"{'Err (pp)':>9}  Benchmark"
    )
    print(f"    {'-' * 9} {'-' * 21} {'-' * 17} {'-' * 9}  {'-' * 40}")
    fell_back = []
    for c in comparisons:
        source = c.benchmark.source.value.split()[0]
        # Two rows with the same error mean different things if they were
        # scored on different populations, so the universe travels with it —
        # and it is the universe actually *ranked*, not the one the source
        # ranks. "registered->scored" marks a request that could not be met.
        universe = c.universe_label
        rating = c.overall_rating
        err = c.mean_absolute_share_error_pp
        err_str = f"{err:.2f}" if err is not None else "—"
        name = c.benchmark.policy_name[:50]
        print(f"    {source:<9} {universe:<21} {rating:<17} {err_str:>9}  {name}")
        if c.universe_fell_back:
            fell_back.append(c)
        if rating == "needs_improvement":
            all_ok = False
    if fell_back:
        print()
        print(
            f"    {len(fell_back)} benchmark(s) scored on a universe their "
            "source does not rank ('registered->scored' above): the policy"
        )
        print(
            "    takes the synthetic bracket path, which aggregates IRS return "
            "counts and has no household layer."
        )
        for c in fell_back:
            print(f"      - {c.benchmark.policy_id} ({c.universe_label})")
    return all_ok


# --- Phase A: out-of-sample tier + pre-registration ------------------------
# Informational only. The numeric ceiling on this tier lives in its own CI step
# (`scripts/cold_holdout.py --max-mean-error ... --min-within-25pct ...`), so
# this block never changes the dashboard's exit code.


def print_out_of_sample_tier() -> None:
    """Print the honest (uncalibrated) tier and its pre-registration status."""
    print_banner("Out-of-sample tier (pre-registered)")
    try:
        from fiscal_model.validation.preregistered import (
            manifest_problems,
            summarize_preregistration,
        )
        from scripts.cold_holdout import build_report

        report = build_report()
        summary = report["out_of_sample"]["summary"]
        manifest = summarize_preregistration()
    except Exception as exc:  # pragma: no cover - best-effort diagnostic
        print(f"  [ERROR] Out-of-sample report unavailable: {exc}")
        return

    print(
        f"  {summary['n']} out-of-sample cases | mean abs error "
        f"{summary['mean_abs_error']}% | within 15%: "
        f"{summary['within_15pct']}/{summary['n']} | within 25%: "
        f"{summary['within_25pct']}/{summary['n']}"
    )
    print(f"  pre-registered rows:     {manifest['live_cases']}")

    try:
        from fiscal_model.validation import cached_default_scorecard

        problems = manifest_problems(cached_default_scorecard())
    except Exception as exc:  # pragma: no cover - best-effort diagnostic
        print(f"  [ERROR] Pre-registration check failed: {exc}")
        return

    if problems:
        for problem in problems:
            print(f"  [WARN] {problem}")
    else:
        print("  [OK] Every out-of-sample case has a matching pre-registration row.")


# --- The calibrated tiers -------------------------------------------------
# Informational, like the out-of-sample block above: this changes no gate and
# no exit code.
#
# It exists because the dashboard could not see them. `SWEEP_offset_sign.md`
# §7.5 records this whole report coming back **byte-identical** across PR #119,
# a change that moved the fitted tier 1.7% -> 1.8%, the reconstruction tier
# 57.6% -> 57.4%, and reclassified two rows out of the fitted set - because the
# dashboard printed Tier 1 and leave-one-out and nothing about the 55 calibrated
# rows in between. A report that cannot distinguish a change to two-thirds of
# the benchmark population is not evidence that nothing moved.
#
# Every number below is **read** from ``cold_holdout.py``'s ``build_report()``
# and from the scorecard summary, never recomputed from model output. Only the
# grouping - held-in-place, and the reconstruction tier's sub-populations - is
# done here, and it is grouping of rows those objects already carry.


def collect_calibrated_tiers() -> dict[str, Any]:
    """The two calibrated tiers, their composition, and the provenance counts."""
    try:
        from fiscal_model.validation import cached_default_scorecard
        from fiscal_model.validation.scorecard import GENERIC_CATEGORY
        from scripts.cold_holdout import build_report
    except Exception as exc:  # pragma: no cover - best-effort diagnostic
        return {"error": f"calibrated tiers unavailable: {exc}"}

    try:
        report = build_report()
        summary = cached_default_scorecard()
    except Exception as exc:  # pragma: no cover - best-effort diagnostic
        return {"error": f"calibrated tiers unavailable: {exc}"}

    specialized = [e for e in summary.entries if e.category != GENERIC_CATEGORY]
    fitted = [e for e in specialized if e.calibrated_to_target]
    # A row the ledger revised left the fitted tier mechanically, because the
    # constant reproduces the *superseded* figure. Held in place is that tier
    # with those rows put back - and only those: a sectoral row the runner
    # never declared fitted was not in the tier to be moved out of it.
    revised_from_fitted = [
        e
        for e in specialized
        if e.target_revision_id and e.declared_calibrated_to_target
    ]
    # A withdrawn target is neither fitted nor a reconstruction; ``build_report``
    # splits it out for the same reason. Kept here only to compute the
    # sub-populations off the same population the tier mean uses.
    retired = [e for e in specialized if getattr(e, "target_retired", False)]
    reconstruction = [
        e
        for e in specialized
        if not e.calibrated_to_target
        and not getattr(e, "target_retired", False)
    ]

    def _agg(entries: list[Any]) -> dict[str, Any]:
        errs = sorted(e.abs_percent_difference for e in entries)
        if not errs:
            return {"n": 0, "mean_abs_error": 0.0, "median_abs_error": 0.0,
                    "within_15pct": 0, "within_25pct": 0}
        mid = len(errs) // 2
        median = errs[mid] if len(errs) % 2 else (errs[mid - 1] + errs[mid]) / 2
        return {
            "n": len(errs),
            "mean_abs_error": round(sum(errs) / len(errs), 1),
            "median_abs_error": round(median, 1),
            "within_15pct": sum(1 for e in errs if e <= 15.0),
            "within_25pct": sum(1 for e in errs if e <= 25.0),
        }

    sub_populations: dict[str, dict[str, Any]] = {}
    for category in sorted({e.category for e in reconstruction}):
        sub_populations[category] = _agg(
            [e for e in reconstruction if e.category == category]
        )

    return {
        # Straight from build_report(), so the dashboard and cold_holdout.py
        # cannot disagree about the two headline tiers.
        "fitted": report["calibrated_reference"]["summary"],
        "reconstruction": report["uncalibrated_reconstruction"]["summary"],
        "fitted_held_in_place": _agg(fitted + revised_from_fitted),
        # Straight from build_report() again, so a withdrawal cannot read one
        # way here and another way in cold_holdout.py.
        "retired": report["retired_targets"]["summary"],
        "reconstruction_retired_held_in_place": report[
            "uncalibrated_reconstruction_retired_held_in_place"
        ]["summary"],
        "retired_target_ids": sorted(e.policy_id for e in retired),
        "revised_target_entries": summary.revised_target_entries,
        "revised_from_fitted_tier": sorted(
            e.policy_id for e in revised_from_fitted
        ),
        "reconstruction_sub_populations": sub_populations,
        "provenance_breakdown": dict(summary.provenance_breakdown),
        "calibrated_provenance_breakdown": dict(
            summary.calibrated_provenance_breakdown
        ),
        "published_entries": summary.published_entries,
        "model_estimate_entries": summary.model_estimate_entries,
        "transcribed_entries": summary.transcribed_entries,
        "line_item_differs_entries": summary.line_item_differs_entries,
        "total_entries": summary.total_entries,
    }


def print_calibrated_tiers(tiers: dict[str, Any]) -> None:
    """Print the fitted and unfitted calibrated tiers. Never changes a gate."""
    print_banner("Calibrated tiers (low error expected by construction)")
    if "error" in tiers:
        print(f"  [ERROR] {tiers['error']}")
        return

    fitted = tiers["fitted"]
    held = tiers["fitted_held_in_place"]
    recon = tiers["reconstruction"]

    print(
        f"  fitted:              n={fitted['n']:<3} mean {fitted['mean_abs_error']}% | "
        f"median {fitted['median_abs_error']}% | "
        f"within 15%: {fitted['within_15pct']}/{fitted['n']}"
    )
    print(
        f"  ... held in place:   n={held['n']:<3} mean {held['mean_abs_error']}% | "
        f"median {held['median_abs_error']}% | "
        f"within 15%: {held['within_15pct']}/{held['n']}"
    )
    print(
        f"  reconstructions:     n={recon['n']:<3} mean {recon['mean_abs_error']}% | "
        f"median {recon['median_abs_error']}% | "
        f"within 15%: {recon['within_15pct']}/{recon['n']}"
    )
    retired = tiers.get("retired", {"n": 0})
    if retired["n"]:
        held_recon = tiers["reconstruction_retired_held_in_place"]
        print(
            f"  ... retired held in: n={held_recon['n']:<3} mean "
            f"{held_recon['mean_abs_error']}% | "
            f"median {held_recon['median_abs_error']}% | "
            f"within 15%: {held_recon['within_15pct']}/{held_recon['n']}"
        )
        print(
            f"  retired targets:     n={retired['n']:<3} mean "
            f"{retired['mean_abs_error']}% at withdrawal  "
            f"({', '.join(tiers['retired_target_ids'])})"
        )
    print(f"  revised targets:     {tiers['revised_target_entries']}")
    print(
        "  Fitted rows reproduce their own targets by construction, so their mean "
        "is not\n  accuracy. A revised target leaves the fitted tier because the "
        "constant is fitted\n  to the figure that was superseded; 'held in place' "
        "puts back only those rows,\n  never a row the runner declared unfitted "
        "in the first place."
    )
    if retired["n"]:
        print(
            "  A RETIRED target was withdrawn with nothing to replace it, so its "
            "row has no\n  benchmark and leaves the reconstruction mean. "
            "'... retired held in' is that\n  tier with those rows put back at "
            "the error they carried on the day they were\n  withdrawn — a tier "
            "that improved because a row was withdrawn is not a tier\n  that "
            "improved."
        )

    subs = tiers["reconstruction_sub_populations"]
    if subs:
        print()
        print("  Reconstruction sub-populations (never quote the tier as one number):")
        print(f"    {'Category':<16} {'n':>3} {'mean':>8} {'median':>8} {'w/in 15':>8}")
        print(f"    {'-' * 16} {'-' * 3} {'-' * 8} {'-' * 8} {'-' * 8}")
        for category, agg in sorted(
            subs.items(), key=lambda kv: (-kv[1]["n"], kv[0])
        ):
            print(
                f"    {category:<16} {agg['n']:>3} "
                f"{agg['mean_abs_error']:>7.1f}% {agg['median_abs_error']:>7.1f}% "
                f"{agg['within_15pct']:>4}/{agg['n']:<3}"
            )

    prov = tiers["provenance_breakdown"]
    print()
    print(
        "  provenance (both tiers): "
        + " | ".join(f"{label} {count}" for label, count in sorted(prov.items()))
    )
    print(
        f"  published targets:   {tiers['published_entries']}/{tiers['total_entries']}"
        f" | transcribed {tiers['transcribed_entries']}"
        f" | line_item_differs {tiers['line_item_differs_entries']}"
        f" | model_estimate {tiers['model_estimate_entries']}"
    )


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


# ---------------------------------------------------------------------------
# Tier 2 (leave-one-out) — see fiscal_model/validation/loo.py
# ---------------------------------------------------------------------------


def collect_loo() -> LOOSuite | None:
    """
    Run the leave-one-out suite, returning ``None`` if it crashed.

    Prints the full traceback: a crash here fails the gate, and a bare
    ``str(exc)`` in a CI log is rarely enough to act on.
    """
    try:
        return run_leave_one_out()
    except Exception as exc:  # pragma: no cover - best-effort diagnostic
        print(f"  [ERROR] Leave-one-out suite crashed: {exc}")
        traceback.print_exc()
        return None


def print_loo(suite: LOOSuite | None, ceiling: float) -> bool:
    """Print the Tier 2 (LOO) section. Return True when under the ceiling."""
    print_banner("Tier 2 (leave-one-out) — held-out calibrated modules")
    if suite is None:
        print("  [FAIL] Leave-one-out suite unavailable.")
        return False

    print(f"    {'Module':<14} {'Kind':<11} {'n':>3} {'not x-val':>10} {'mean err':>10}")
    print(f"    {'-' * 14} {'-' * 11} {'-' * 3} {'-' * 10} {'-' * 10}")
    for report in suite.reports:
        mean = report.mean_abs_percent_error
        print(
            f"    {report.module:<14} {report.derivation_kind:<11} "
            f"{len(report.included_cases):>3} {len(report.excluded_cases):>10} "
            f"{_fmt_pct(mean):>10}"
        )
    included = len(suite.included_cases)
    print()
    print(f"  aggregate mean:     {_fmt_pct(suite.mean_abs_percent_error)} (n={included})")
    print(f"  aggregate median:   {_fmt_pct(suite.median_abs_percent_error)}")
    print(f"  within 15%:         {suite.within_15pct}/{included}")
    print(f"  not cross-validatable: {len(suite.excluded_cases)} (never folded into the aggregate)")
    print(f"  ceiling:            {ceiling:.1f}%")
    return not loo_gate_issues(suite, ceiling)


def loo_gate_ok(suite: LOOSuite | None, ceiling: float) -> bool:
    """Silent equivalent of print_loo for JSON/reporting paths."""
    return not loo_gate_issues(suite, ceiling)


def loo_gate_issues(suite: LOOSuite | None, ceiling: float) -> list[dict[str, Any]]:
    """Return Tier 2 (LOO) ceiling breaches in artifact-friendly form."""
    if suite is None:
        return [
            {
                "surface": "loo",
                "severity": "fail",
                "message": "Leave-one-out suite failed to run.",
            }
        ]
    mean = suite.mean_abs_percent_error
    if mean is None:
        return [
            {
                "surface": "loo",
                "severity": "fail",
                "message": "Leave-one-out suite produced no derivable cases.",
            }
        ]
    if mean > ceiling:
        return [
            {
                "surface": "loo",
                "severity": "fail",
                "mean_abs_percent_error": mean,
                "ceiling": ceiling,
                "message": (
                    f"Tier 2 (LOO) mean absolute error {mean:.1f}% exceeds the "
                    f"{ceiling:.1f}% ceiling."
                ),
            }
        ]
    return []


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
    parser.add_argument(
        "--max-loo-mean-error",
        type=float,
        default=DEFAULT_MAX_LOO_MEAN_ERROR,
        help=(
            "Ceiling on the Tier 2 (leave-one-out) aggregate mean absolute error, "
            f"in percent (default: {DEFAULT_MAX_LOO_MEAN_ERROR:.0f})."
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
                    # The universe the source ranks (requested) vs the one the
                    # model actually ranked; they differ when a household
                    # request falls back to the synthetic bracket path.
                    "ranking_universe": c.benchmark.ranking_universe,
                    "scored_universe": c.scored_universe,
                    "universe_fell_back": c.universe_fell_back,
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
            # Informational, like the human report's block: gates none of the
            # exit codes below, and read from build_report() and the scorecard
            # summary rather than recomputed.
            "calibrated_tiers": collect_calibrated_tiers(),
        }
        loo_suite = collect_loo()
        payload["leave_one_out"] = (
            {**loo_suite.to_dict(), "ceiling": args.max_loo_mean_error}
            if loo_suite is not None
            else {"error": "leave-one-out suite failed to run"}
        )
        gates = {
            "health": health_gate_ok(health),
            "calibration": calibration_gate_ok(calibration),
            "distributional_benchmarks": benchmarks_gate_ok(benchmarks_json),
            "leave_one_out": loo_gate_ok(loo_suite, args.max_loo_mean_error),
        }
        issues = [
            *health_gate_issues(health),
            *calibration_gate_issues(calibration),
            *benchmark_gate_issues(benchmarks_json),
            *loo_gate_issues(loo_suite, args.max_loo_mean_error),
        ]
        has_warn_issues = any(issue["severity"] == "warn" for issue in issues)
        if (
            not gates["health"]
            or not gates["distributional_benchmarks"]
            or not gates["leave_one_out"]
        ):
            overall = "fail"
        elif not gates["calibration"] or has_warn_issues:
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
    print_out_of_sample_tier()
    print_calibrated_tiers(collect_calibrated_tiers())
    loo_suite = collect_loo()
    loo_ok = print_loo(loo_suite, args.max_loo_mean_error)

    health_warnings = [
        issue for issue in health_gate_issues(health) if issue["severity"] == "warn"
    ]

    print_banner("Summary")
    if health_ok and calibration_ok and benchmarks_ok and loo_ok and not health_warnings:
        print("  [OK] All surfaces nominal.")
        return 0
    if not health_ok:
        print("  [FAIL] One or more health components degraded.")
        return 1
    if not benchmarks_ok:
        print("  [FAIL] At least one distributional benchmark flagged needs_improvement.")
        return 1
    if not loo_ok:
        for issue in loo_gate_issues(loo_suite, args.max_loo_mean_error):
            print(f"  [FAIL] {issue['message']}")
        return 1
    if not calibration_ok:
        print("  [WARN] Calibration has at least one bracket with <60% AGI coverage.")
    for issue in health_warnings:
        print(f"  [WARN] {issue['message']}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
