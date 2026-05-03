"""
Release-readiness gate for deployments and monitoring.

``/health`` reports raw component status. This module turns those signals plus
distributional and revenue validation checks into one machine-readable verdict:

- ``ready``: every required check passes and no warnings are present
- ``ready_with_warnings``: required checks pass, but caveats remain
- ``not_ready``: at least one required check fails
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from fiscal_model.time_utils import utc_isoformat

CheckStatus = str  # pass | warn | fail
ReadinessVerdict = str  # ready | ready_with_warnings | not_ready


@dataclass(frozen=True)
class ReadinessCheck:
    """One readiness criterion."""

    name: str
    status: CheckStatus
    required: bool
    summary: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ReadinessIssue:
    """Flattened readiness blocker or warning for clients and CI artifacts."""

    name: str
    severity: CheckStatus
    required: bool
    summary: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ReadinessReport:
    """Aggregate release-readiness verdict."""

    verdict: ReadinessVerdict
    generated_at: str
    pass_count: int
    warn_count: int
    fail_count: int
    checks: list[ReadinessCheck]
    issues: list[ReadinessIssue] = field(default_factory=list)


def _check(
    name: str,
    status: CheckStatus,
    summary: str,
    *,
    required: bool = True,
    details: dict[str, Any] | None = None,
) -> ReadinessCheck:
    return ReadinessCheck(
        name=name,
        status=status,
        required=required,
        summary=summary,
        details=details or {},
    )


def _health_checks(health: dict[str, Any]) -> list[ReadinessCheck]:
    checks: list[ReadinessCheck] = []

    runtime = health.get("runtime", {})
    if runtime.get("status") == "ok":
        checks.append(_check(
            "runtime",
            "pass",
            runtime.get("message", "Python runtime is supported."),
            details=runtime,
        ))
    else:
        checks.append(_check(
            "runtime",
            "fail",
            runtime.get("message", "Python runtime is outside the supported range."),
            details=runtime,
        ))

    model = health.get("model", {})
    if model.get("status") == "ok":
        checks.append(_check(
            "model",
            "pass",
            "Scoring engine health check passed.",
            details=model,
        ))
    else:
        checks.append(_check(
            "model",
            "fail",
            "Scoring engine health check failed.",
            details=model,
        ))

    baseline = health.get("baseline", {})
    if baseline.get("status") == "error" or baseline.get("load_error"):
        checks.append(_check(
            "baseline",
            "fail",
            "CBO baseline failed to load.",
            details=baseline,
        ))
    elif baseline.get("status") == "ok":
        checks.append(_check(
            "baseline",
            "pass",
            "CBO baseline is available.",
            details=baseline,
        ))
    else:
        checks.append(_check(
            "baseline",
            "warn",
            "CBO baseline is using a degraded data path.",
            details=baseline,
        ))

    fred = health.get("fred", {})
    if fred.get("status") == "error":
        checks.append(_check(
            "fred",
            "fail",
            "FRED data layer raised an error.",
            details=fred,
        ))
    elif fred.get("status") == "ok":
        checks.append(_check(
            "fred",
            "pass",
            "FRED data layer is available.",
            details=fred,
        ))
    else:
        checks.append(_check(
            "fred",
            "warn",
            "FRED is using cache or fallback data.",
            details=fred,
            required=False,
        ))

    irs = health.get("irs_soi", {})
    if irs.get("status") == "error" or not irs.get("latest_year"):
        checks.append(_check(
            "irs_soi",
            "fail",
            "IRS SOI data is unavailable.",
            details=irs,
        ))
    elif irs.get("status") == "ok":
        checks.append(_check(
            "irs_soi",
            "pass",
            "IRS SOI data is available.",
            details=irs,
        ))
    else:
        checks.append(_check(
            "irs_soi",
            "warn",
            "IRS SOI data is present but freshness is degraded.",
            details=irs,
        ))

    microdata = health.get("microdata", {})
    if microdata.get("status") in {"error", "missing", "malformed"}:
        checks.append(_check(
            "microdata",
            "fail",
            "Microdata is missing, malformed, or failed to load.",
            details=microdata,
        ))
    elif microdata.get("status") == "ok":
        checks.append(_check(
            "microdata",
            "pass",
            "Microdata calibration is within readiness bounds.",
            details=microdata,
        ))
    else:
        checks.append(_check(
            "microdata",
            "warn",
            "Microdata is available but calibration is degraded.",
            details=microdata,
            required=False,
        ))

    return checks


def _distribution_benchmark_check(comparisons: list[Any]) -> ReadinessCheck:
    if not comparisons:
        return _check(
            "distribution_benchmarks",
            "fail",
            "No distributional benchmarks ran.",
            details={"count": 0},
        )

    failing = [
        c for c in comparisons
        if getattr(c, "overall_rating", None) == "needs_improvement"
    ]
    details = {
        "count": len(comparisons),
        "needs_improvement": len(failing),
    }
    if failing:
        details["failing_policy_ids"] = [
            getattr(getattr(c, "benchmark", None), "policy_id", "unknown")
            for c in failing
        ]
        return _check(
            "distribution_benchmarks",
            "fail",
            "At least one distributional benchmark needs improvement.",
            details=details,
        )
    return _check(
        "distribution_benchmarks",
        "pass",
        "Distributional benchmarks are within readiness bounds.",
        details=details,
    )


def _scorecard_checks(scorecard: Any) -> list[ReadinessCheck]:
    from fiscal_model.validation.holdout import summarize_holdout_protocol

    entries = list(getattr(scorecard, "entries", []))
    calibrated = [entry for entry in entries if getattr(entry, "category", None) != "Generic"]
    calibrated_error = [
        entry for entry in calibrated
        if getattr(entry, "rating", None) == "Error"
    ]
    undocumented_poor = [
        entry for entry in calibrated
        if (
            getattr(entry, "rating", None) == "Poor"
            and not getattr(entry, "known_limitations", [])
        )
    ]
    documented_poor = [
        entry for entry in calibrated
        if (
            getattr(entry, "rating", None) == "Poor"
            and getattr(entry, "known_limitations", [])
        )
    ]

    if not entries:
        scorecard_check = _check(
            "revenue_scorecard",
            "fail",
            "Revenue validation scorecard has no entries.",
            details={"total_entries": 0},
        )
    elif not calibrated:
        scorecard_check = _check(
            "revenue_scorecard",
            "fail",
            "Revenue validation scorecard has no calibrated specialized entries.",
            details={"total_entries": len(entries), "calibrated_entries": 0},
        )
    elif calibrated_error or undocumented_poor:
        failing_entries = [*calibrated_error, *undocumented_poor]
        scorecard_check = _check(
            "revenue_scorecard",
            "fail",
            "At least one calibrated revenue benchmark is Error or an undocumented Poor outlier.",
            details={
                "total_entries": len(entries),
                "calibrated_entries": len(calibrated),
                "calibrated_error": len(calibrated_error),
                "undocumented_poor": len(undocumented_poor),
                "failing_policy_ids": [
                    getattr(entry, "policy_id", "unknown")
                    for entry in failing_entries
                ],
            },
        )
    elif documented_poor:
        scorecard_check = _check(
            "revenue_scorecard",
            "warn",
            "At least one calibrated revenue benchmark is a documented Poor outlier.",
            details={
                "total_entries": len(entries),
                "calibrated_entries": len(calibrated),
                "documented_poor": len(documented_poor),
                "documented_policy_ids": [
                    getattr(entry, "policy_id", "unknown")
                    for entry in documented_poor
                ],
            },
        )
    else:
        scorecard_check = _check(
            "revenue_scorecard",
            "pass",
            "Calibrated revenue benchmarks are within readiness bounds.",
            details={
                "total_entries": len(entries),
                "calibrated_entries": len(calibrated),
                "within_15pct": getattr(scorecard, "within_15pct", None),
                "median_abs_percent_difference": getattr(
                    scorecard,
                    "median_abs_percent_difference",
                    None,
                ),
            },
        )

    holdout_details = summarize_holdout_protocol(entries)
    holdout_failures: list[str] = []
    if holdout_details["missing_policy_ids"]:
        holdout_failures.append("one or more locked holdout policy IDs are missing")
    if holdout_details["missing_categories"]:
        holdout_failures.append("one or more required categories lack holdout coverage")
    if holdout_details["holdout_entries"] < holdout_details["minimum_holdout_entries"]:
        holdout_failures.append("too few holdout entries are available")
    if holdout_details["failing_policy_ids"]:
        holdout_failures.append("one or more holdout entries are Poor, Error, or direction-mismatched")

    if holdout_failures:
        holdout_check = _check(
            "holdout_protocol",
            "fail",
            "Locked holdout protocol failed: " + "; ".join(holdout_failures) + ".",
            details=holdout_details,
        )
    else:
        holdout_check = _check(
            "holdout_protocol",
            "pass",
            "Locked post-change holdout protocol is covered and within readiness bounds.",
            details=holdout_details,
        )
    return [scorecard_check, holdout_check]


def _verdict(checks: list[ReadinessCheck]) -> ReadinessVerdict:
    if any(check.required and check.status == "fail" for check in checks):
        return "not_ready"
    if any(check.status == "warn" for check in checks):
        return "ready_with_warnings"
    return "ready"


def readiness_issues_from_checks(checks: list[ReadinessCheck]) -> list[ReadinessIssue]:
    """Flatten non-passing checks into artifact-friendly issue records."""
    return [
        ReadinessIssue(
            name=check.name,
            severity=check.status,
            required=check.required,
            summary=check.summary,
            details=check.details,
        )
        for check in checks
        if check.status in {"warn", "fail"}
    ]


def _is_environmental_data_warning(issue: ReadinessIssue) -> bool:
    """Return whether a warning is expected in offline CI data environments."""
    if issue.severity != "warn":
        return False

    if issue.name == "fred":
        return (
            issue.details.get("status") == "degraded"
            and issue.details.get("source") in {"cache", "fallback"}
        )

    if issue.name != "baseline":
        return False

    details = issue.details
    if details.get("status") != "degraded" or details.get("load_error"):
        return False

    fred = details.get("fred", {})
    fred_source = fred.get("source") if isinstance(fred, dict) else None
    return (
        details.get("source") == "real_data"
        and details.get("gdp_source") == "irs_ratio_proxy"
        and fred_source == "fallback"
    )


def strict_readiness_issues(report: ReadinessReport) -> list[ReadinessIssue]:
    """Return issues that should fail the strict CI readiness gate.

    The readiness payload still reports every warning. Strict CI only exempts
    warnings caused by missing live external data in isolated build runners.
    """
    return [
        issue for issue in report.issues
        if issue.severity == "fail" or not _is_environmental_data_warning(issue)
    ]


def build_readiness_report(
    *,
    health: dict[str, Any] | None = None,
    distribution_comparisons: list[Any] | None = None,
    scorecard: Any | None = None,
) -> ReadinessReport:
    """Run every readiness check and return one aggregate verdict."""
    if health is None:
        from fiscal_model.health import check_health

        health = check_health()

    if distribution_comparisons is None:
        from fiscal_model.validation.benchmark_runners import default_model_runner
        from fiscal_model.validation.cbo_distributions import run_full_cbo_jct_validation

        distribution_comparisons = run_full_cbo_jct_validation(default_model_runner)

    if scorecard is None:
        from fiscal_model.validation.scorecard import cached_default_scorecard

        scorecard = cached_default_scorecard()

    checks = [
        *_health_checks(health),
        _distribution_benchmark_check(distribution_comparisons),
        *_scorecard_checks(scorecard),
    ]
    issues = readiness_issues_from_checks(checks)

    return ReadinessReport(
        verdict=_verdict(checks),
        generated_at=utc_isoformat(),
        pass_count=sum(1 for check in checks if check.status == "pass"),
        warn_count=sum(1 for check in checks if check.status == "warn"),
        fail_count=sum(1 for check in checks if check.status == "fail"),
        checks=checks,
        issues=issues,
    )


def readiness_to_dict(report: ReadinessReport) -> dict[str, Any]:
    """Serialize readiness report to a plain dict."""
    return asdict(report)


__all__ = [
    "ReadinessCheck",
    "ReadinessIssue",
    "ReadinessReport",
    "build_readiness_report",
    "readiness_issues_from_checks",
    "readiness_to_dict",
    "strict_readiness_issues",
]
