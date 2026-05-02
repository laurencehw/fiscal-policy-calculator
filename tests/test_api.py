"""
Contract tests for FastAPI endpoints in api.py.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest
from fastapi.testclient import TestClient

import api as api_module
from fiscal_model.app_data import PRESET_POLICIES
from fiscal_model.readiness import (
    ReadinessCheck,
    ReadinessReport,
    readiness_issues_from_checks,
)


class _DummyScoringResult:
    def __init__(self) -> None:
        self.years = np.arange(2026, 2036)
        self.static_revenue_effect = np.full(10, 5.0)
        self.behavioral_offset = np.full(10, -1.0)
        self.final_deficit_effect = np.full(10, -4.0)
        self.baseline = SimpleNamespace(baseline_vintage_date="Feb 2026")
        self.dynamic_effects = SimpleNamespace(
            revenue_feedback=np.full(10, 0.5),
            gdp_percent_change=np.full(10, 0.02),
            employment_change=np.full(10, 120.0),
        )


class _DummyScorer:
    def __init__(self, *args, **kwargs) -> None:
        del args, kwargs

    def score_policy(self, policy, dynamic=False):
        del policy, dynamic
        return _DummyScoringResult()


class _RecordingScorer(_DummyScorer):
    last_policy = None

    def score_policy(self, policy, dynamic=False):
        type(self).last_policy = policy
        return super().score_policy(policy, dynamic=dynamic)


def _client() -> TestClient:
    return TestClient(api_module.app)


def test_root_endpoint_lists_routes():
    response = _client().get("/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == "Fiscal Policy Calculator API"
    assert "score_custom" in payload["endpoints"]


def test_health_endpoint_uses_health_payload(monkeypatch):
    monkeypatch.setattr(
        api_module,
        "check_health",
        lambda: {
            "overall": "ok",
            "timestamp": "2026-04-01T00:00:00Z",
            "fred": {"status": "ok"},
        },
    )

    response = _client().get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["overall"] == "ok"
    assert payload["components"]["fred"]["status"] == "ok"


def test_presets_endpoint_returns_count():
    response = _client().get("/presets")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == len(payload["presets"])


def test_benchmarks_endpoint_lists_distributional_accuracy():
    response = _client().get("/benchmarks")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == len(payload["benchmarks"])
    # At least the four mapped benchmarks should run.
    assert payload["count"] >= 4

    for entry in payload["benchmarks"]:
        assert entry["rating"] in {
            "excellent",
            "good",
            "acceptable",
            "needs_improvement",
            "no_overlap",
        }
        assert entry["matched_rows"] <= entry["benchmark_rows"]
        assert "source_document" in entry
        assert entry["analysis_year"] > 2000


def test_root_endpoint_advertises_benchmarks():
    response = _client().get("/")
    assert response.status_code == 200
    assert "benchmarks" in response.json()["endpoints"]
    assert "readiness" in response.json()["endpoints"]
    assert "summary" in response.json()["endpoints"]


def test_readiness_endpoint_returns_verdict(monkeypatch):
    checks = [
        ReadinessCheck(
            name="runtime",
            status="pass",
            required=True,
            summary="Runtime ok.",
            details={"python_version": "3.12.0"},
        ),
        ReadinessCheck(
            name="holdout_protocol",
            status="warn",
            required=False,
            summary="No holdout split yet.",
        ),
    ]
    monkeypatch.setattr(
        api_module,
        "build_readiness_report",
        lambda: ReadinessReport(
            verdict="ready_with_warnings",
            generated_at="2026-04-01T00:00:00Z",
            pass_count=1,
            warn_count=1,
            fail_count=0,
            checks=checks,
            issues=readiness_issues_from_checks(checks),
        ),
    )

    response = _client().get("/readiness")
    assert response.status_code == 200
    payload = response.json()
    assert payload["verdict"] == "ready_with_warnings"
    assert payload["pass_count"] == 1
    assert payload["warn_count"] == 1
    assert payload["checks"][0]["name"] == "runtime"
    assert payload["issues"][0]["name"] == "holdout_protocol"
    assert payload["issues"][0]["severity"] == "warn"


def test_summary_endpoint_combines_health_and_benchmarks():
    response = _client().get("/summary")
    assert response.status_code == 200
    payload = response.json()
    # Combined overview has every top-level section.
    for key in (
        "overall",
        "timestamp",
        "health",
        "benchmarks",
        "benchmarks_rating",
        "microdata_coverage",
        "auth_required",
        "issues",
    ):
        assert key in payload, f"Missing {key} in /summary response"
    # Overall is {ok, degraded, unknown} — the aggregate gate.
    assert payload["overall"] in {"ok", "degraded", "unknown"}
    # Benchmarks should run (at least the 6 mapped).
    assert payload["benchmarks_rating"] in {"ok", "degraded"}
    assert len(payload["benchmarks"]) >= 4
    assert isinstance(payload["issues"], list)


def test_summary_health_issues_flatten_non_ok_components():
    issues = api_module._summary_health_issues({
        "overall": "degraded",
        "timestamp": "2026-04-01T00:00:00Z",
        "runtime": {
            "status": "degraded",
            "message": "Python 3.14 is unsupported.",
        },
        "fred": {
            "status": "degraded",
            "source": "fallback",
        },
        "model": {"status": "ok"},
    })

    assert [issue.name for issue in issues] == ["runtime", "fred"]
    assert issues[0].severity == "fail"
    assert issues[0].message == "Python 3.14 is unsupported."
    assert issues[1].severity == "warn"


def test_summary_benchmark_issues_flatten_needs_improvement():
    issues = api_module._summary_benchmark_issues([
        api_module.BenchmarkResult(
            policy_id="ok_policy",
            policy_name="OK policy",
            source="CBO",
            source_document="doc",
            analysis_year=2026,
            rating="excellent",
            mean_absolute_share_error_pp=1.0,
            matched_rows=2,
            benchmark_rows=2,
        ),
        api_module.BenchmarkResult(
            policy_id="bad_policy",
            policy_name="Bad policy",
            source="CBO",
            source_document="doc",
            analysis_year=2026,
            rating="needs_improvement",
            mean_absolute_share_error_pp=12.0,
            matched_rows=2,
            benchmark_rows=4,
        ),
    ])

    assert len(issues) == 1
    assert issues[0].surface == "distributional_benchmarks"
    assert issues[0].severity == "fail"
    assert issues[0].name == "bad_policy"
    assert issues[0].details["mean_absolute_share_error_pp"] == 12.0


def test_score_endpoint_success(monkeypatch):
    monkeypatch.setattr(api_module, "FiscalPolicyScorer", _DummyScorer)

    response = _client().post(
        "/score",
        json={
            "name": "API Test Policy",
            "description": "Test payload",
            "rate_change": 0.01,
            "income_threshold": 400000,
            "dynamic": True,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["policy_name"] == "API Test Policy"
    assert payload["error_message"] is None
    assert payload["dynamic_scoring_enabled"] is True
    assert len(payload["year_by_year"]) == 10
    assert payload["revenue_feedback"] == pytest.approx(5.0)
    assert payload["gdp_effect"] == pytest.approx(0.2)
    assert payload["employment_effect"] == pytest.approx(120.0)
    assert payload["dynamic_adjusted_impact"] == pytest.approx(-40.0)
    assert payload["year_by_year"][0]["dynamic_feedback"] == pytest.approx(0.5)


def test_score_endpoint_validation_error():
    response = _client().post(
        "/score",
        json={"rate_change": 2.0, "income_threshold": 400000},
    )
    assert response.status_code == 422


def test_score_endpoint_invalid_policy_type_returns_400():
    response = _client().post(
        "/score",
        json={
            "rate_change": 0.01,
            "income_threshold": 400000,
            "policy_type": "tax_credit",
        },
    )
    assert response.status_code == 400
    assert "policy_type" in response.json()["detail"]


def test_score_endpoint_value_error_returns_400(monkeypatch):
    """Upstream ``ValueError`` from policy constructors should be surfaced
    as a 400 Bad Request, not swallowed into the generic 200 error path."""

    class _ExplodingScorer(_DummyScorer):
        def score_policy(self, policy, dynamic=False):
            del policy, dynamic
            raise ValueError("threshold must be non-negative")

    monkeypatch.setattr(api_module, "FiscalPolicyScorer", _ExplodingScorer)
    response = _client().post(
        "/score",
        json={"rate_change": 0.01, "income_threshold": 0},
    )
    assert response.status_code == 400
    assert "threshold must be non-negative" in response.json()["detail"]


def test_score_endpoint_internal_error_returns_500(monkeypatch):
    class _ExplodingScorer(_DummyScorer):
        def score_policy(self, policy, dynamic=False):
            del policy, dynamic
            raise RuntimeError("boom")

    monkeypatch.setattr(api_module, "FiscalPolicyScorer", _ExplodingScorer)
    response = _client().post(
        "/score",
        json={"rate_change": 0.01, "income_threshold": 0},
    )
    assert response.status_code == 500
    assert response.json()["detail"] == "Internal scoring error"


def test_score_preset_internal_error_returns_500(monkeypatch):
    class _ExplodingScorer(_DummyScorer):
        def score_policy(self, policy, dynamic=False):
            del policy, dynamic
            raise RuntimeError("boom")

    monkeypatch.setattr(api_module, "FiscalPolicyScorer", _ExplodingScorer)
    response = _client().post(
        "/score/preset",
        json={"preset_name": "Biden 2025 Proposal", "dynamic": False},
    )
    assert response.status_code == 500
    assert response.json()["detail"] == "Internal scoring error"


def test_score_preset_unknown_returns_400():
    response = _client().post(
        "/score/preset",
        json={"preset_name": "does-not-exist", "dynamic": False},
    )
    assert response.status_code == 400
    assert "Unknown preset" in response.json()["detail"]


@pytest.mark.parametrize(
    ("preset_name", "expected_class_name"),
    [
        (
            next(name for name, data in PRESET_POLICIES.items() if data.get("is_tcja")),
            "TCJAExtensionPolicy",
        ),
        (
            next(name for name, data in PRESET_POLICIES.items() if data.get("is_corporate")),
            "CorporateTaxPolicy",
        ),
        (
            next(name for name, data in PRESET_POLICIES.items() if data.get("is_credit")),
            "TaxCreditPolicy",
        ),
        (
            next(name for name, data in PRESET_POLICIES.items() if data.get("is_payroll")),
            "PayrollTaxPolicy",
        ),
        (
            next(name for name, data in PRESET_POLICIES.items() if data.get("is_ptc")),
            "PremiumTaxCreditPolicy",
        ),
        (
            next(name for name, data in PRESET_POLICIES.items() if data.get("is_trade")),
            "TariffPolicy",
        ),
    ],
)
def test_score_preset_routes_specialized_policies(monkeypatch, preset_name, expected_class_name):
    monkeypatch.setattr(api_module, "FiscalPolicyScorer", _RecordingScorer)
    response = _client().post(
        "/score/preset",
        json={"preset_name": preset_name, "dynamic": False},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["policy_name"] == preset_name
    assert len(payload["year_by_year"]) == 10
    assert _RecordingScorer.last_policy.__class__.__name__ == expected_class_name


def test_score_preset_routes_simple_income_tax_policy(monkeypatch):
    monkeypatch.setattr(api_module, "FiscalPolicyScorer", _RecordingScorer)
    response = _client().post(
        "/score/preset",
        json={"preset_name": "Biden 2025 Proposal", "dynamic": False},
    )
    assert response.status_code == 200
    assert _RecordingScorer.last_policy.__class__.__name__ == "TaxPolicy"


def test_score_tariff_contract():
    response = _client().post(
        "/score/tariff",
        json={
            "name": "10% universal tariff",
            "tariff_rate": 0.1,
            "import_base_billions": 3200.0,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["policy_name"] == "10% universal tariff"
    assert "trade_summary" in payload
    assert "uncertainty_range" in payload
