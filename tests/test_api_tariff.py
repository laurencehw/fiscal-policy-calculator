"""``POST /score/tariff`` — bounds, the sanity check, honest flags, error codes.

Reproduced before the fix: ``import_base_billions=1e12`` scored without a
bounds check; ``target_country`` was accepted and ignored;
``include_retaliation`` / ``include_consumer_cost`` changed only the echoed
summary while the response implied otherwise; and every failure, including
a model bug, came back as a 400.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest
from fastapi.testclient import TestClient

import api as api_module


def _client() -> TestClient:
    return TestClient(api_module.app)


def _post(**overrides):
    return _client().post("/score/tariff", json={"tariff_rate": 0.1, **overrides})


def test_import_base_is_bounded():
    for value in (1e12, 1e308, 20_001):
        response = _post(import_base_billions=value)
        assert response.status_code == 422, value
    assert _post(import_base_billions=20_000).status_code == 200
    assert _post().status_code == 200  # the 3,200 default


def test_target_country_is_rejected_not_silently_ignored():
    for value in ("CN", "china", ""):
        response = _post(target_country=value)
        assert response.status_code == 422, value
        assert "target_country" in response.text
    assert _post(target_country=None).status_code == 200


def test_the_flags_do_not_move_the_headline_and_the_response_says_so():
    full = _post().json()
    no_retaliation = _post(include_retaliation=False).json()
    no_consumer = _post(include_consumer_cost=False).json()
    neither = _post(include_retaliation=False, include_consumer_cost=False).json()

    for payload in (full, no_retaliation, no_consumer, neither):
        assert payload["headline_basis"] == "conventional"
        assert "include_retaliation" in payload["headline_note"]
        assert payload["ten_year_deficit_impact"] == pytest.approx(
            full["ten_year_deficit_impact"]
        )
        assert payload["uncertainty_range"] == full["uncertainty_range"]

    # What the flags do change is the reported column.
    assert full["trade_summary"]["retaliation_cost"] > 0
    assert no_retaliation["trade_summary"]["retaliation_cost"] == 0
    assert full["trade_summary"]["consumer_cost"] > 0
    assert no_consumer["trade_summary"]["consumer_cost"] == 0


class _ScorerReturning:
    """A scorer whose result is whatever the test hands it."""

    result: object = None
    error: Exception | None = None

    def __init__(self, *args, **kwargs) -> None:
        del args, kwargs

    def score_policy(self, policy, dynamic=False):
        del policy, dynamic
        if type(self).error is not None:
            raise type(self).error
        return type(self).result


def _result(values):
    arr = np.asarray(values, dtype=float)
    return SimpleNamespace(
        years=np.arange(2026, 2026 + arr.size),
        final_deficit_effect=arr,
        low_estimate=arr,
        high_estimate=arr,
    )


@pytest.fixture
def stub_scorer(monkeypatch):
    _ScorerReturning.result = None
    _ScorerReturning.error = None
    monkeypatch.setattr(api_module, "FiscalPolicyScorer", _ScorerReturning)
    return _ScorerReturning


def test_an_implausible_result_is_an_error_not_a_200(stub_scorer):
    stub_scorer.result = _result([-5e5] * 10)  # $500T a year
    response = _post()
    assert response.status_code == 400
    assert "plausible" in response.json()["detail"]


def test_a_non_finite_result_is_an_error_not_a_200(stub_scorer):
    stub_scorer.result = _result([float("nan")] * 10)
    assert _post().status_code == 400


def test_a_value_error_is_a_400(stub_scorer):
    stub_scorer.error = ValueError("bad input")
    response = _post()
    assert response.status_code == 400
    assert response.json()["detail"] == "bad input"


def test_an_unexpected_failure_is_a_500_without_leaking_the_message(stub_scorer):
    stub_scorer.error = RuntimeError("secret internals")
    response = _post()
    assert response.status_code == 500
    assert "secret internals" not in response.text
