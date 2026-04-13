"""Tests for API bounds validation and typed error responses."""

from __future__ import annotations

import math

import pytest

from api import _MAX_ANNUAL_EFFECT_BILLIONS, _validate_serialized_result
from fiscal_model.exceptions import ScoringBoundsError


def _ok_payload() -> dict:
    return {
        "ten_year_deficit_impact": -250.0,
        "static_revenue_effect": 260.0,
        "behavioral_offset": -8.0,
        "final_static_effect": 252.0,
        "gdp_effect": 0.05,
        "employment_effect": 120.0,
        "revenue_feedback": 5.0,
        "dynamic_adjusted_impact": -245.0,
        "year_by_year": [
            {
                "year": 2026 + i,
                "revenue_effect": 25.0,
                "behavioral_offset": -0.8,
                "dynamic_feedback": 0.0,
                "final_effect": -24.2,
            }
            for i in range(10)
        ],
    }


def test_validate_accepts_reasonable_payload():
    _validate_serialized_result(_ok_payload(), policy_name="Test")


def test_validate_rejects_nan_scalar():
    payload = _ok_payload()
    payload["ten_year_deficit_impact"] = float("nan")
    with pytest.raises(ScoringBoundsError, match="non-finite"):
        _validate_serialized_result(payload, policy_name="NaN Policy")


def test_validate_rejects_infinite_scalar():
    payload = _ok_payload()
    payload["static_revenue_effect"] = math.inf
    with pytest.raises(ScoringBoundsError):
        _validate_serialized_result(payload, policy_name="Inf")


def test_validate_rejects_implausible_ten_year():
    payload = _ok_payload()
    payload["ten_year_deficit_impact"] = _MAX_ANNUAL_EFFECT_BILLIONS * 20
    with pytest.raises(ScoringBoundsError, match="plausible bounds"):
        _validate_serialized_result(payload, policy_name="Absurd")


def test_validate_rejects_implausible_year_by_year():
    payload = _ok_payload()
    payload["year_by_year"][0]["revenue_effect"] = _MAX_ANNUAL_EFFECT_BILLIONS * 2
    with pytest.raises(ScoringBoundsError, match="exceeds plausible"):
        _validate_serialized_result(payload, policy_name="Huge")


def test_validate_ignores_none_optional_fields():
    payload = _ok_payload()
    payload["gdp_effect"] = None
    payload["employment_effect"] = None
    payload["revenue_feedback"] = None
    payload["dynamic_adjusted_impact"] = None
    # Must not raise — these are optional dynamic fields.
    _validate_serialized_result(payload, policy_name="No dynamics")
