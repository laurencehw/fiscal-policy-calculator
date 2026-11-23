"""Request-model limits on free text and numbers, and the root's docs link."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

import api as api_module
from api import ClassroomCheckRequest, ScorePolicyRequest, ScoreTariffRequest


def test_root_docs_url_is_relative():
    payload = TestClient(api_module.app).get("/").json()
    assert payload["docs_url"] == "/docs"


def test_score_policy_caps_free_text():
    ScorePolicyRequest(rate_change=0.01, name="x" * 200, description="y" * 1000)
    with pytest.raises(ValidationError):
        ScorePolicyRequest(rate_change=0.01, name="x" * 201)
    with pytest.raises(ValidationError):
        ScorePolicyRequest(rate_change=0.01, description="y" * 1001)
    with pytest.raises(ValidationError):
        ScorePolicyRequest(rate_change=0.01, policy_type="z" * 65)


@pytest.mark.parametrize("field", ["rate_change", "income_threshold", "elasticity"])
@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_score_policy_refuses_non_finite_numbers(field, value):
    fields = {"rate_change": 0.01, field: value}
    with pytest.raises(ValidationError):
        ScorePolicyRequest(**fields)


def test_score_policy_bounds_income_threshold():
    ScorePolicyRequest(rate_change=0.01, income_threshold=10_000_000)
    ScorePolicyRequest(rate_change=0.01, income_threshold=100_000_000)
    with pytest.raises(ValidationError):
        ScorePolicyRequest(rate_change=0.01, income_threshold=1e12)


def test_score_tariff_caps_name_and_refuses_non_finite():
    ScoreTariffRequest(tariff_rate=0.1, name="t" * 200)
    with pytest.raises(ValidationError):
        ScoreTariffRequest(tariff_rate=0.1, name="t" * 201)
    with pytest.raises(ValidationError):
        ScoreTariffRequest(tariff_rate=float("nan"))
    with pytest.raises(ValidationError):
        ScoreTariffRequest(tariff_rate=0.1, import_base_billions=float("inf"))


def test_classroom_params_refuse_non_finite_values_and_long_names():
    ok = ClassroomCheckRequest(
        assignment_id="a", exercise_id="e", params={"rate": 0.3}, answer=1.0
    )
    assert ok.params == {"rate": 0.3}
    with pytest.raises(ValidationError):
        ClassroomCheckRequest(
            assignment_id="a", exercise_id="e", params={"rate": float("nan")}, answer=1.0
        )
    with pytest.raises(ValidationError):
        ClassroomCheckRequest(
            assignment_id="a", exercise_id="e", params={"p" * 65: 1.0}, answer=1.0
        )


def test_over_long_name_is_a_422_over_http():
    response = TestClient(api_module.app).post(
        "/score", json={"rate_change": 0.01, "name": "x" * 5000}
    )
    assert response.status_code == 422
