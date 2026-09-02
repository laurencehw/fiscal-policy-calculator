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

    # Runtime: an out-of-range-but-functional interpreter (e.g. a contributor
    # on 3.14) is a *warning*, not a blocker — it boots and scores correctly.
    # A genuine runtime break ("error") still fails. The strict CI gate
    # (``strict_readiness_issues``) re-elevates the version-range warning to a
    # blocker, so release deploys still require a supported Python.
    runtime = health.get("runtime", {})
    if runtime.get("status") == "ok":
        checks.append(_check(
            "runtime",
            "pass",
            runtime.get("message", "Python runtime is supported."),
            details=runtime,
        ))
    elif runtime.get("status") == "error":
        checks.append(_check(
            "runtime",
            "fail",
            runtime.get("message", "Python runtime check failed."),
            details=runtime,
        ))
    else:
        checks.append(_check(
            "runtime",
            "warn",
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
            "FRED is using a degraded external-data path.",
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

    # Ask assistant — not required, so its absence never blocks deploy.
    # Skip entirely when the health payload doesn't carry the key (so
    # synthetic payloads and older callers stay backward-compatible).
    assistant = health.get("assistant")
    if assistant is None:
        return checks
    if assistant.get("status") == "ok":
        checks.append(_check(
            "assistant",
            "pass",
            (
                f"Ask assistant ready "
                f"({assistant.get('knowledge_corpus_files', 0)} knowledge snapshots, "
                f"usage db writable)."
            ),
            details=assistant,
            required=False,
        ))
    elif assistant.get("status") == "error":
        checks.append(_check(
            "assistant",
            "warn",
            "Ask assistant component raised an error.",
            details=assistant,
            required=False,
        ))
    else:
        # Degraded — break apart the reasons.
        reasons = []
        if not assistant.get("api_key_configured"):
            reasons.append("ANTHROPIC_API_KEY not set")
        if not assistant.get("knowledge_corpus_files"):
            reasons.append("knowledge corpus empty")
        if not assistant.get("usage_db_writable"):
            reasons.append("usage db not writable")
        msg = (
            "Ask assistant degraded: " + ", ".join(reasons)
            if reasons
            else "Ask assistant degraded."
        )
        checks.append(_check(
            "assistant",
            "warn",
            msg,
            details=assistant,
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
    from fiscal_model.validation.scorecard import GENERIC_CATEGORY

    entries = list(getattr(scorecard, "entries", []))
    # The Generic (out-of-sample) tier used to be exempt from this gate, which
    # left the *only* tier that claims predictive skill as the *only* ungated
    # one. Every entry is now held to the same bar: an Error rating or an
    # undocumented Poor outlier fails strict readiness regardless of tier; a
    # Poor entry that carries a known_limitations note is a warning, which is
    # how a documented out-of-sample miss (kept, not tuned away) is recorded.
    calibrated = [
        entry for entry in entries
        if getattr(entry, "category", None) != GENERIC_CATEGORY
    ]
    error_entries = [
        entry for entry in entries
        if getattr(entry, "rating", None) == "Error"
    ]
    undocumented_poor = [
        entry for entry in entries
        if (
            getattr(entry, "rating", None) == "Poor"
            and not getattr(entry, "known_limitations", [])
        )
    ]
    documented_poor = [
        entry for entry in entries
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
    elif error_entries or undocumented_poor:
        failing_entries = [*error_entries, *undocumented_poor]
        scorecard_check = _check(
            "revenue_scorecard",
            "fail",
            "At least one revenue benchmark is Error or an undocumented Poor outlier.",
            details={
                "total_entries": len(entries),
                "calibrated_entries": len(calibrated),
                "error_entries": len(error_entries),
                "undocumented_poor": len(undocumented_poor),
                "failing_policy_ids": [
                    getattr(entry, "policy_id", "unknown")
                    for entry in failing_entries
                ],
            },
        )
    elif documented_poor:
        # Split three ways, because "calibrated" covers two different things:
        #
        # 1. A *fitted* calibrated benchmark drifting to Poor is a real
        #    regression — its parameters exist to reproduce that target, so a
        #    miss means something broke. Strict-blocking.
        # 2. A calibrated-tier *reconstruction* the module was never fitted to
        #    (``calibrated_to_target=False``) is a finding about the module, not
        #    a regression: the Phase E sectoral runners score modules against
        #    published figures nobody had compared them to before. Exempt, for
        #    the same reason as (3) — blocking on it would make deleting the
        #    runner the cheapest way back to green.
        # 3. A documented *out-of-sample* miss is the honest tier doing its job.
        #    Exempt — see ``_is_documented_benchmark_warning``.
        documented_calibrated = [
            entry for entry in documented_poor
            if getattr(entry, "category", None) != GENERIC_CATEGORY
            and getattr(entry, "calibrated_to_target", True)
        ]
        documented_reconstruction = [
            entry for entry in documented_poor
            if getattr(entry, "category", None) != GENERIC_CATEGORY
            and not getattr(entry, "calibrated_to_target", True)
        ]
        documented_generic = [
            entry for entry in documented_poor
            if getattr(entry, "category", None) == GENERIC_CATEGORY
        ]
        scorecard_check = _check(
            "revenue_scorecard",
            "warn",
            "At least one revenue benchmark is a documented Poor outlier.",
            details={
                "total_entries": len(entries),
                "calibrated_entries": len(calibrated),
                "documented_poor": len(documented_poor),
                "documented_policy_ids": [
                    getattr(entry, "policy_id", "unknown")
                    for entry in documented_poor
                ],
                "documented_calibrated_policy_ids": [
                    getattr(entry, "policy_id", "unknown")
                    for entry in documented_calibrated
                ],
                "documented_reconstruction_policy_ids": [
                    getattr(entry, "policy_id", "unknown")
                    for entry in documented_reconstruction
                ],
                "documented_generic_policy_ids": [
                    getattr(entry, "policy_id", "unknown")
                    for entry in documented_generic
                ],
            },
        )
    else:
        scorecard_check = _check(
            "revenue_scorecard",
            "pass",
            "Revenue benchmarks are within readiness bounds.",
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
    elif holdout_details.get("documented_poor_policy_ids"):
        holdout_check = _check(
            "holdout_protocol",
            "warn",
            "Locked holdout protocol is covered; "
            f"{len(holdout_details['documented_poor_policy_ids'])} entry(ies) are "
            "documented Poor outliers: "
            + ", ".join(holdout_details["documented_poor_policy_ids"])
            + ".",
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
    """Return whether a warning is expected in offline CI data environments.

    Exempted (environmental — a property of the isolated runner, not the
    model): FRED on cache/fallback; the baseline riding a FRED fallback or
    a *fresh* bundled seed; the Ask assistant missing only its API key;
    and the microdata coverage-*overcount* warning (mirroring the
    validation dashboard's warn tier). A stale/expired bundled seed stays
    blocking — that is a repository-maintenance signal, not an
    environment one — as do microdata undercount/synthetic warnings.
    """
    if issue.severity != "warn":
        return False

    details = issue.details

    if issue.name == "fred":
        return (
            details.get("status") == "degraded"
            and details.get("source") in {"cache", "fallback"}
        )

    if issue.name == "assistant":
        # CI runners have no ANTHROPIC_API_KEY; only exempt when the key is
        # the sole problem — a missing knowledge corpus or unwritable usage
        # db is a real defect.
        return (
            details.get("status") == "degraded"
            and not details.get("api_key_configured")
            and details.get("knowledge_corpus_files", 0) > 0
            and bool(details.get("usage_db_writable"))
        )

    if issue.name == "microdata":
        # Overcount-only coverage (>110% of SOI returns) is a bundled-data
        # quality signal the dashboard gate already treats as warn-not-fail;
        # undercount and synthetic data still block.
        return (
            details.get("status") == "degraded"
            and bool(details.get("coverage_overcount"))
            and not details.get("coverage_undercount")
        )

    if issue.name != "baseline":
        return False

    if details.get("status") != "degraded" or details.get("load_error"):
        return False

    fred = details.get("fred", {})
    fred_source = fred.get("source") if isinstance(fred, dict) else None
    fred_expired = bool(fred.get("cache_is_expired")) if isinstance(fred, dict) else False
    if (
        details.get("source") == "real_data"
        and details.get("gdp_source") == "irs_ratio_proxy"
        and fred_source == "fallback"
    ):
        return True
    # A fresh bundled seed is the designed offline mode (the seed file
    # exists for exactly this); only an *expired* seed should block, so the
    # refresh workflow can turn the gate green rather than deadlock on it.
    return (
        details.get("source") == "real_data"
        and details.get("gdp_source") == "fred_bundled"
        and fred_source == "bundled"
        and not fred_expired
    )


def _is_documented_benchmark_warning(issue: ReadinessIssue) -> bool:
    """Return whether a warning is only documented, non-regression benchmark misses.

    The revenue scorecard holds every tier to the same bar, including the
    out-of-sample (Generic) one. Two kinds of entry are *expected* to contain
    large, honestly-reported misses:

    * **Out-of-sample (Generic)** — a top-rate target that is itself internally
      inconsistent, capital-gains cases whose published targets disagree by 42%.
    * **Calibrated-tier reconstructions** (``calibrated_to_target=False``) —
      the Phase E sectoral runners score the international, trade, pharma,
      enforcement and climate modules against figures those modules were
      never fitted to. A miss there is a finding about the module, which is
      the entire reason for adding the runner.

    Each carries a ``known_limitations`` note, which is what turns it from a
    hard failure into this warning. Blocking the release gate on either would
    create exactly the wrong incentive: the cheapest way to go green would be
    to delete the miss or tune it away, which the pre-registration manifest
    exists to forbid.

    A documented Poor entry on a benchmark the module *is* fitted to is **not**
    exempted: those parameters exist to reproduce that target, so drifting to
    Poor is a genuine regression. ``Error`` and undocumented ``Poor`` in either
    tier are already hard ``fail``s (see ``_scorecard_checks``) and reach this
    function with severity ``fail``.
    """
    if issue.severity != "warn":
        return False
    details = issue.details
    if issue.name == "revenue_scorecard":
        if details.get("documented_calibrated_policy_ids"):
            return False
        return bool(
            details.get("documented_generic_policy_ids")
            or details.get("documented_reconstruction_policy_ids")
        )
    if issue.name == "holdout_protocol":
        # A locked holdout entry can stop being a fitted benchmark: Wave 2's L1
        # deleted the capital-gains module's per-case tuples, so
        # ``pwbm_39_with_stepup`` is now scored by one frozen literature set and
        # rates Poor with the direction right. The rule above already says what
        # to do with that - a documented miss on a benchmark the module is *not*
        # fitted to is a finding, not a regression - and it applies here for the
        # same reason. A documented Poor holdout entry the module *is* still
        # fitted to, an undocumented one, an Error or a direction mismatch all
        # arrive as ``fail`` and are never exempted.
        if details.get("documented_poor_calibrated_policy_ids"):
            return False
        return bool(details.get("documented_poor_reconstruction_policy_ids"))
    return False


def strict_readiness_issues(report: ReadinessReport) -> list[ReadinessIssue]:
    """Return issues that should fail the strict CI readiness gate.

    The readiness payload still reports every warning. Strict CI exempts
    warnings caused by missing live external data in isolated build runners,
    plus documented benchmark misses that are not calibration regressions
    (see :func:`_is_documented_benchmark_warning`).
    """
    return [
        issue for issue in report.issues
        if issue.severity == "fail"
        or not (
            _is_environmental_data_warning(issue)
            or _is_documented_benchmark_warning(issue)
        )
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
