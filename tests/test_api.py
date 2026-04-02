"""
Contract tests for FastAPI endpoints in api.py.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
from fastapi.testclient import TestClient

import api as api_module
from fiscal_model.app_data import PRESET_POLICIES


class _DummyScoringResult:
    def __init__(self) -> None:
        self.years = np.arange(2026, 2036)
        self.static_revenue_effect = np.full(10, 5.0)
        self.behavioral_offset = np.full(10, -1.0)
        self.final_deficit_effect = np.full(10, -4.0)
        self.revenue_feedback = np.full(10, 0.5)
        self.baseline = SimpleNamespace(baseline_vintage_date="Feb 2026")
        self.gdp_effect = 0.2
        self.employment_effect = 120.0


class _DummyScorer:
    def __init__(self, *args, **kwargs) -> None:
        del args, kwargs

    def score_policy(self, policy, dynamic=False):  # noqa: ANN001
        del policy, dynamic
        return _DummyScoringResult()


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
    assert payload["count"] > 0


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


def test_score_endpoint_validation_error():
    response = _client().post(
        "/score",
        json={"rate_change": 2.0, "income_threshold": 400000},
    )
    assert response.status_code == 422


def test_score_endpoint_internal_error_returns_error_payload(monkeypatch):
    class _ExplodingScorer(_DummyScorer):
        def score_policy(self, policy, dynamic=False):  # noqa: ANN001
            del policy, dynamic
            raise RuntimeError("boom")

    monkeypatch.setattr(api_module, "FiscalPolicyScorer", _ExplodingScorer)
    response = _client().post(
        "/score",
        json={"rate_change": 0.01, "income_threshold": 0},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["baseline_vintage"] == "error"
    assert "boom" in payload["error_message"]


def test_score_preset_unknown_returns_400():
    response = _client().post(
        "/score/preset",
        json={"preset_name": "does-not-exist", "dynamic": False},
    )
    assert response.status_code == 400
    assert "Unknown preset" in response.json()["detail"]


def test_score_preset_supported_contract(monkeypatch):
    monkeypatch.setattr(api_module, "FiscalPolicyScorer", _DummyScorer)
    preset_name = next(
        name for name, data in PRESET_POLICIES.items()
        if name != "Custom Policy"
        and not data.get("is_tcja")
        and not data.get("is_corporate")
    )

    response = _client().post(
        "/score/preset",
        json={"preset_name": preset_name, "dynamic": False},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["policy_name"] == preset_name
    assert len(payload["year_by_year"]) == 10


def test_score_preset_tcja_returns_400():
    tcja_name = next(name for name, data in PRESET_POLICIES.items() if data.get("is_tcja"))
    response = _client().post(
        "/score/preset",
        json={"preset_name": tcja_name, "dynamic": False},
    )
    assert response.status_code == 400
    assert "TCJA presets require specialized scoring" in response.json()["detail"]


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
