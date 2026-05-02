"""
Tests for fiscal_model.api_serialization helper functions.
"""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from fiscal_model import FiscalPolicyScorer, TaxPolicy
from fiscal_model.api_serialization import (
    _as_float_array,
    _extract_dynamic_series,
    _sum_float,
    _value_at,
    serialize_scoring_result,
)
from fiscal_model.policies import PolicyType


def test_as_float_array_handles_none_scalar_and_invalid():
    assert _as_float_array(None) is None

    scalar = _as_float_array(3)
    assert scalar is not None
    assert scalar.shape == (1,)
    assert scalar[0] == 3.0

    assert _as_float_array(object()) is None


def test_sum_float_and_value_at_handle_empty_inputs():
    assert _sum_float(None) == 0.0
    assert _value_at(np.array([]), 0) == 0.0
    assert _value_at(np.array([1.5]), 3) == 1.5


def test_extract_dynamic_series_supports_legacy_result_shape():
    legacy_result = SimpleNamespace(
        revenue_feedback=[0.5, 0.75],
        gdp_effect=[0.1, 0.2],
        employment_effect=[100.0, 120.0],
    )

    dynamic = _extract_dynamic_series(legacy_result)

    assert np.allclose(dynamic["revenue_feedback"], [0.5, 0.75])
    assert np.allclose(dynamic["gdp_percent_change"], [0.1, 0.2])
    assert np.allclose(dynamic["employment_change"], [100.0, 120.0])


def _score_simple_tax_increase(*, dynamic: bool):
    policy = TaxPolicy(
        name="QA top rate",
        description="+5pp at $400K",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=0.05,
        affected_income_threshold=400_000,
        taxable_income_elasticity=0.25,
    )
    scorer = FiscalPolicyScorer(use_real_data=False)
    return policy, scorer.score_policy(policy, dynamic=dynamic)


def test_final_static_effect_is_revenue_net_of_behavior_static():
    """final_static_effect must equal revenue gain net of behavioral erosion.

    Regression for a sign bug where the serializer computed
    static + behavioral; for TaxPolicy the engine treats behavioral_offset
    as a positive magnitude that erodes the static gain, so the correct
    formulation is static - behavioral (equivalently: -ten_year_deficit_impact
    when dynamic scoring is off).
    """
    policy, result = _score_simple_tax_increase(dynamic=False)
    payload = serialize_scoring_result(
        result,
        policy_name=policy.name,
        policy_description=policy.description,
        dynamic_scoring_enabled=False,
    )

    assert payload["static_revenue_effect"] > 0
    assert payload["behavioral_offset"] > 0
    expected = payload["static_revenue_effect"] - payload["behavioral_offset"]
    assert np.isclose(payload["final_static_effect"], expected)
    # And it must be the negation of the deficit impact when dynamic is off.
    assert np.isclose(
        payload["final_static_effect"], -payload["ten_year_deficit_impact"]
    )


def test_final_static_effect_excludes_dynamic_feedback():
    """final_static_effect must report the pre-dynamic revenue impact.

    Even when dynamic scoring is enabled, this field captures only the
    static + behavioral revenue effect; revenue_feedback is reported
    separately. So for any dynamic run:
        final_static_effect = static_revenue - behavioral
                            = -ten_year_deficit_impact - revenue_feedback
    """
    policy, result = _score_simple_tax_increase(dynamic=True)
    payload = serialize_scoring_result(
        result,
        policy_name=policy.name,
        policy_description=policy.description,
        dynamic_scoring_enabled=True,
    )

    expected_from_components = (
        payload["static_revenue_effect"] - payload["behavioral_offset"]
    )
    expected_from_deficit = (
        -payload["ten_year_deficit_impact"] - payload["revenue_feedback"]
    )
    assert np.isclose(payload["final_static_effect"], expected_from_components)
    assert np.isclose(payload["final_static_effect"], expected_from_deficit)


def test_final_static_effect_ignores_display_flag_for_derivation():
    """Derived math must use the actual feedback in the result, not the
    display flag. If a caller serializes a dynamically-scored result with
    dynamic_scoring_enabled=False (rare but allowed by the contract), the
    static-impact scalar must still be the pre-dynamic revenue effect, not
    a stale ten_year minus zero."""
    policy, result = _score_simple_tax_increase(dynamic=True)

    shown = serialize_scoring_result(
        result,
        policy_name=policy.name,
        policy_description=policy.description,
        dynamic_scoring_enabled=True,
    )
    hidden = serialize_scoring_result(
        result,
        policy_name=policy.name,
        policy_description=policy.description,
        dynamic_scoring_enabled=False,
    )

    # The displayed revenue_feedback honors the flag.
    assert shown["revenue_feedback"] != 0.0
    assert hidden["revenue_feedback"] == 0.0
    # But the underlying static-impact derivation must not.
    assert np.isclose(hidden["final_static_effect"], shown["final_static_effect"])


def test_final_static_effect_matches_year_by_year_sum():
    """Summary scalar must agree with year_by_year aggregation."""
    policy, result = _score_simple_tax_increase(dynamic=False)
    payload = serialize_scoring_result(
        result,
        policy_name=policy.name,
        policy_description=policy.description,
        dynamic_scoring_enabled=False,
    )

    yearly_revenue_net = sum(
        entry["revenue_effect"] - entry["behavioral_offset"]
        for entry in payload["year_by_year"]
    )
    assert np.isclose(payload["final_static_effect"], yearly_revenue_net)
    yearly_final = sum(entry["final_effect"] for entry in payload["year_by_year"])
    assert np.isclose(payload["final_static_effect"], -yearly_final)


def test_serialized_result_includes_credibility_metadata():
    policy, result = _score_simple_tax_increase(dynamic=False)
    payload = serialize_scoring_result(
        result,
        policy_name=policy.name,
        policy_description=policy.description,
        dynamic_scoring_enabled=False,
    )

    credibility = payload["credibility"]
    assert credibility is not None
    assert credibility["category"] == "Generic"
    assert credibility["evidence_type"] == "generic_parameterized_estimate"
    assert credibility["holdout_status"] == "not_applicable_generic"
    assert credibility["uncertainty_low"] <= payload["ten_year_deficit_impact"]
    assert credibility["uncertainty_high"] >= payload["ten_year_deficit_impact"]
    assert any("holdout" in item for item in credibility["limitations"])
