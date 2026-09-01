"""
Tests for the release-readiness evaluator.
"""

from __future__ import annotations

from types import SimpleNamespace

from fiscal_model.readiness import (
    build_readiness_report,
    readiness_issues_from_checks,
    readiness_to_dict,
    strict_readiness_issues,
)


def _healthy_payload() -> dict:
    return {
        "runtime": {
            "status": "ok",
            "python_version": "3.12.0",
            "supported_range": ">=3.10,<3.14",
            "message": "Python 3.12.0 is within supported range >=3.10,<3.14.",
        },
        "model": {"status": "ok", "test_score": -1.0},
        "baseline": {"status": "ok", "vintage": "February 2026"},
        "fred": {"status": "ok", "source": "live"},
        "irs_soi": {"status": "ok", "latest_year": 2022},
        "microdata": {
            "status": "ok",
            "calibration_year": 2022,
            "returns_coverage_pct": 100.0,
            "agi_coverage_pct": 100.0,
        },
    }


def _comparison(policy_id: str = "x", rating: str = "excellent"):
    return SimpleNamespace(
        overall_rating=rating,
        benchmark=SimpleNamespace(policy_id=policy_id),
    )


_HOLDOUT_ENTRIES = [
    ("Credits", "biden_eitc_childless"),
    ("Estate", "extend_tcja_exemption"),
    ("Payroll", "ss_cap_90_pct"),
    ("AMT", "repeal_individual_amt"),
    ("AMT", "repeal_corporate_amt"),
    ("PTC", "repeal_ptc"),
    ("CapitalGains", "pwbm_39_with_stepup"),
    ("Expenditures", "eliminate_mortgage"),
    ("Expenditures", "repeal_salt_cap"),
    ("Expenditures", "cap_charitable"),
]


def _scorecard(
    *,
    rating: str = "Good",
    known_limitations: list[str] | None = None,
    include_holdout: bool = True,
):
    entry = SimpleNamespace(
        category="TCJA",
        rating=rating,
        policy_id="tcja_full",
        known_limitations=known_limitations or [],
        direction_match=True,
    )
    holdout_entries = [
        SimpleNamespace(
            category=category,
            rating="Good",
            policy_id=policy_id,
            known_limitations=[],
            direction_match=True,
        )
        for category, policy_id in _HOLDOUT_ENTRIES
    ]
    return SimpleNamespace(
        entries=[entry, *holdout_entries] if include_holdout else [entry],
        within_15pct=1,
        median_abs_percent_difference=4.0,
    )


def test_readiness_ready_when_required_checks_and_holdout_protocol_pass():
    report = build_readiness_report(
        health=_healthy_payload(),
        distribution_comparisons=[_comparison()],
        scorecard=_scorecard(),
    )

    assert report.verdict == "ready"
    assert report.fail_count == 0
    assert report.issues == []
    holdout = next(check for check in report.checks if check.name == "holdout_protocol")
    assert holdout.status == "pass"
    assert holdout.details["holdout_entries"] >= 8


def test_readiness_fails_missing_locked_holdout_entries():
    report = build_readiness_report(
        health=_healthy_payload(),
        distribution_comparisons=[_comparison()],
        scorecard=_scorecard(include_holdout=False),
    )

    assert report.verdict == "not_ready"
    holdout = next(check for check in report.checks if check.name == "holdout_protocol")
    assert holdout.status == "fail"
    assert holdout.details["missing_policy_ids"]
    assert any(issue.name == "holdout_protocol" for issue in report.issues)


def test_readiness_warns_on_unsupported_runtime():
    """Out-of-range-but-functional runtime → warn, not a deploy blocker."""
    health = _healthy_payload()
    health["runtime"] = {
        "status": "degraded",
        "python_version": "3.14.0",
        "supported_range": ">=3.10,<3.14",
        "message": "unsupported",
    }

    report = build_readiness_report(
        health=health,
        distribution_comparisons=[_comparison()],
        scorecard=_scorecard(),
    )

    assert report.verdict == "ready_with_warnings"
    runtime = next(check for check in report.checks if check.name == "runtime")
    assert runtime.status == "warn"
    runtime_issue = next(issue for issue in report.issues if issue.name == "runtime")
    assert runtime_issue.severity == "warn"
    assert runtime_issue.required is True
    assert runtime_issue.summary == "unsupported"


def test_readiness_fails_broken_runtime_error():
    """A genuinely broken runtime ('error') still hard-fails the gate."""
    health = _healthy_payload()
    health["runtime"] = {
        "status": "error",
        "python_version": "3.14.0",
        "message": "runtime check raised",
    }

    report = build_readiness_report(
        health=health,
        distribution_comparisons=[_comparison()],
        scorecard=_scorecard(),
    )

    assert report.verdict == "not_ready"
    runtime = next(check for check in report.checks if check.name == "runtime")
    assert runtime.status == "fail"
    assert next(issue for issue in report.issues if issue.name == "runtime").severity == "fail"


def test_strict_readiness_fails_on_unsupported_runtime():
    """Strict CI gate re-elevates the version-range warning to a blocker."""
    health = _healthy_payload()
    health["runtime"] = {
        "status": "degraded",
        "python_version": "3.14.0",
        "supported_range": ">=3.10,<3.14",
        "message": "Python 3.14.0 is outside supported range.",
    }

    report = build_readiness_report(
        health=health,
        distribution_comparisons=[_comparison()],
        scorecard=_scorecard(),
    )

    assert report.verdict == "ready_with_warnings"
    blocking = strict_readiness_issues(report)
    assert any(issue.name == "runtime" for issue in blocking)


def test_readiness_fails_distribution_benchmark_regression():
    report = build_readiness_report(
        health=_healthy_payload(),
        distribution_comparisons=[_comparison("bad", "needs_improvement")],
        scorecard=_scorecard(),
    )

    assert report.verdict == "not_ready"
    dist = next(check for check in report.checks if check.name == "distribution_benchmarks")
    assert dist.status == "fail"
    assert dist.details["failing_policy_ids"] == ["bad"]
    issue = next(issue for issue in report.issues if issue.name == "distribution_benchmarks")
    assert issue.details["failing_policy_ids"] == ["bad"]


def test_readiness_warns_on_documented_calibrated_revenue_poor_rating():
    report = build_readiness_report(
        health=_healthy_payload(),
        distribution_comparisons=[_comparison()],
        scorecard=_scorecard(rating="Poor", known_limitations=["Known outlier."]),
    )

    assert report.verdict == "ready_with_warnings"
    scorecard = next(check for check in report.checks if check.name == "revenue_scorecard")
    assert scorecard.status == "warn"
    issue = next(issue for issue in report.issues if issue.name == "revenue_scorecard")
    assert issue.severity == "warn"


def test_readiness_fails_undocumented_calibrated_revenue_poor_rating():
    report = build_readiness_report(
        health=_healthy_payload(),
        distribution_comparisons=[_comparison()],
        scorecard=_scorecard(rating="Poor"),
    )

    assert report.verdict == "not_ready"
    scorecard = next(check for check in report.checks if check.name == "revenue_scorecard")
    assert scorecard.status == "fail"


def _scorecard_with_generic(*, rating: str, known_limitations: list[str] | None = None):
    """Healthy calibrated set plus one Generic (out-of-sample) entry."""
    base = _scorecard()
    generic = SimpleNamespace(
        category="Generic",
        rating=rating,
        policy_id="top_rate_45",
        known_limitations=known_limitations or [],
        direction_match=True,
    )
    return SimpleNamespace(
        entries=[*base.entries, generic],
        within_15pct=base.within_15pct,
        median_abs_percent_difference=base.median_abs_percent_difference,
    )


def test_readiness_fails_generic_revenue_error_rating():
    """The out-of-sample tier used to be exempt from this gate, which left the
    only tier claiming predictive skill as the only ungated one."""
    report = build_readiness_report(
        health=_healthy_payload(),
        distribution_comparisons=[_comparison()],
        scorecard=_scorecard_with_generic(rating="Error"),
    )

    assert report.verdict == "not_ready"
    scorecard = next(check for check in report.checks if check.name == "revenue_scorecard")
    assert scorecard.status == "fail"
    assert "top_rate_45" in scorecard.details["failing_policy_ids"]


def test_readiness_fails_undocumented_generic_revenue_poor_rating():
    report = build_readiness_report(
        health=_healthy_payload(),
        distribution_comparisons=[_comparison()],
        scorecard=_scorecard_with_generic(rating="Poor"),
    )

    assert report.verdict == "not_ready"
    scorecard = next(check for check in report.checks if check.name == "revenue_scorecard")
    assert scorecard.status == "fail"


def test_readiness_warns_on_documented_generic_revenue_poor_rating():
    """A documented out-of-sample miss is kept and reported, not tuned away."""
    report = build_readiness_report(
        health=_healthy_payload(),
        distribution_comparisons=[_comparison()],
        scorecard=_scorecard_with_generic(
            rating="Poor",
            known_limitations=["Target is secondhand and internally inconsistent."],
        ),
    )

    assert report.verdict == "ready_with_warnings"
    scorecard = next(check for check in report.checks if check.name == "revenue_scorecard")
    assert scorecard.status == "warn"
    assert "top_rate_45" in scorecard.details["documented_policy_ids"]


def test_strict_gate_exempts_documented_benchmark_outliers():
    """A documented out-of-sample miss must not block the release gate —
    otherwise the cheapest way to go green is to delete or tune away the miss,
    which the pre-registration manifest exists to forbid."""
    report = build_readiness_report(
        health=_healthy_payload(),
        distribution_comparisons=[_comparison()],
        scorecard=_scorecard_with_generic(
            rating="Poor",
            known_limitations=["Target is secondhand and internally inconsistent."],
        ),
    )

    assert report.verdict == "ready_with_warnings"
    assert any(issue.name == "revenue_scorecard" for issue in report.issues)
    assert strict_readiness_issues(report) == []


def test_strict_gate_still_blocks_undocumented_benchmark_outliers():
    report = build_readiness_report(
        health=_healthy_payload(),
        distribution_comparisons=[_comparison()],
        scorecard=_scorecard_with_generic(rating="Poor"),
    )

    blocking = strict_readiness_issues(report)
    assert [issue.name for issue in blocking] == ["revenue_scorecard"]
    assert blocking[0].severity == "fail"


def test_readiness_to_dict_serializes_nested_checks():
    report = build_readiness_report(
        health=_healthy_payload(),
        distribution_comparisons=[_comparison()],
        scorecard=_scorecard(),
    )
    payload = readiness_to_dict(report)

    assert payload["verdict"] == "ready"
    assert isinstance(payload["checks"], list)
    assert isinstance(payload["issues"], list)
    assert "name" in payload["checks"][0]


def test_readiness_issues_from_checks_filters_passes():
    report = build_readiness_report(
        health=_healthy_payload(),
        distribution_comparisons=[_comparison()],
        scorecard=_scorecard(rating="Poor", known_limitations=["Known outlier."]),
    )

    issues = readiness_issues_from_checks(report.checks)

    assert [issue.name for issue in issues] == ["revenue_scorecard"]
    assert issues[0].severity == "warn"


def test_strict_readiness_issues_exempts_offline_external_data_warnings():
    health = _healthy_payload()
    health["baseline"] = {
        "status": "degraded",
        "source": "real_data",
        "gdp_source": "irs_ratio_proxy",
        "load_error": None,
        "fred": {"source": "fallback"},
    }
    health["fred"] = {"status": "degraded", "source": "fallback"}

    report = build_readiness_report(
        health=health,
        distribution_comparisons=[_comparison()],
        scorecard=_scorecard(),
    )

    assert report.verdict == "ready_with_warnings"
    assert [issue.name for issue in report.issues] == ["baseline", "fred"]
    assert strict_readiness_issues(report) == []


def test_strict_readiness_issues_blocks_stale_bundled_seed():
    health = _healthy_payload()
    health["fred"] = {
        "status": "degraded",
        "source": "bundled",
        "cache_age_days": 150,
        "cache_is_expired": True,
        "source_max_age_days": 120,
    }

    report = build_readiness_report(
        health=health,
        distribution_comparisons=[_comparison()],
        scorecard=_scorecard(),
    )

    assert report.verdict == "ready_with_warnings"
    assert [issue.name for issue in strict_readiness_issues(report)] == ["fred"]


def test_strict_readiness_issues_blocks_model_validation_warnings():
    report = build_readiness_report(
        health=_healthy_payload(),
        distribution_comparisons=[_comparison()],
        scorecard=_scorecard(rating="Poor", known_limitations=["Known outlier."]),
    )

    assert [issue.name for issue in strict_readiness_issues(report)] == [
        "revenue_scorecard"
    ]


def test_strict_readiness_issues_exempts_fresh_bundled_seed_baseline():
    """A fresh bundled seed is the designed offline mode — the refresh
    workflow's own strict gate must not deadlock on it."""
    health = _healthy_payload()
    health["baseline"] = {
        "status": "degraded",
        "source": "real_data",
        "gdp_source": "fred_bundled",
        "load_error": None,
        "fred": {"source": "bundled", "cache_is_expired": False, "cache_age_days": 0},
    }

    report = build_readiness_report(
        health=health,
        distribution_comparisons=[_comparison()],
        scorecard=_scorecard(),
    )

    assert [issue.name for issue in report.issues] == ["baseline"]
    assert strict_readiness_issues(report) == []


def test_strict_readiness_issues_blocks_expired_bundled_seed_baseline():
    health = _healthy_payload()
    health["baseline"] = {
        "status": "degraded",
        "source": "real_data",
        "gdp_source": "fred_bundled",
        "load_error": None,
        "fred": {"source": "bundled", "cache_is_expired": True, "cache_age_days": 150},
    }

    report = build_readiness_report(
        health=health,
        distribution_comparisons=[_comparison()],
        scorecard=_scorecard(),
    )

    assert [issue.name for issue in strict_readiness_issues(report)] == ["baseline"]


def test_strict_readiness_issues_exempts_assistant_missing_key_only():
    health = _healthy_payload()
    health["assistant"] = {
        "status": "degraded",
        "api_key_configured": False,
        "knowledge_corpus_files": 19,
        "usage_db_writable": True,
    }

    report = build_readiness_report(
        health=health,
        distribution_comparisons=[_comparison()],
        scorecard=_scorecard(),
    )

    assert [issue.name for issue in report.issues] == ["assistant"]
    assert strict_readiness_issues(report) == []


def test_strict_readiness_issues_blocks_assistant_missing_corpus():
    health = _healthy_payload()
    health["assistant"] = {
        "status": "degraded",
        "api_key_configured": False,
        "knowledge_corpus_files": 0,
        "usage_db_writable": True,
    }

    report = build_readiness_report(
        health=health,
        distribution_comparisons=[_comparison()],
        scorecard=_scorecard(),
    )

    assert [issue.name for issue in strict_readiness_issues(report)] == ["assistant"]


def test_strict_readiness_issues_exempts_microdata_overcount_only():
    health = _healthy_payload()
    health["microdata"] = {
        "status": "degraded",
        "coverage_overcount": True,
        "coverage_undercount": False,
        "returns_coverage_pct": 119.0,
    }

    report = build_readiness_report(
        health=health,
        distribution_comparisons=[_comparison()],
        scorecard=_scorecard(),
    )

    assert [issue.name for issue in report.issues] == ["microdata"]
    assert strict_readiness_issues(report) == []


def test_strict_readiness_issues_blocks_microdata_undercount():
    health = _healthy_payload()
    health["microdata"] = {
        "status": "degraded",
        "coverage_overcount": False,
        "coverage_undercount": True,
        "returns_coverage_pct": 55.0,
    }

    report = build_readiness_report(
        health=health,
        distribution_comparisons=[_comparison()],
        scorecard=_scorecard(),
    )

    assert [issue.name for issue in strict_readiness_issues(report)] == ["microdata"]
