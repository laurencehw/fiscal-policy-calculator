"""
Tests for fiscal_model.api_serialization helper functions.
"""

from __future__ import annotations

import numpy as np

from fiscal_model import FiscalPolicyScorer, TaxPolicy
from fiscal_model.api_serialization import (
    DYNAMIC_VIEW_UNAVAILABLE_MESSAGE,
    _as_float_array,
    _sum_float,
    _value_at,
    serialize_scoring_result,
)
from fiscal_model.dynamic_view import FRBUS_LITE_MODEL_LABEL, run_dynamic_view
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


def _serialize_dynamic(policy, result):
    view, macro = run_dynamic_view(policy, result)
    assert view is not None and macro is not None
    payload = serialize_scoring_result(
        result,
        policy_name=policy.name,
        policy_description=policy.description,
        dynamic_scoring_enabled=True,
        dynamic_view=view,
        macro_result=macro,
    )
    return payload, view, macro


def test_dynamic_headline_stays_conventional():
    """The headline is static + behavioral in every mode, as in the app.

    Before 2026-09-29 a dynamic request moved ``ten_year_deficit_impact`` by
    the engine's EconomicModel feedback and repeated it as
    ``dynamic_adjusted_impact``.
    """
    policy, static_result = _score_simple_tax_increase(dynamic=False)
    static_payload = serialize_scoring_result(
        static_result,
        policy_name=policy.name,
        policy_description=policy.description,
        dynamic_scoring_enabled=False,
    )
    dynamic_payload, view, _macro = _serialize_dynamic(policy, static_result)

    assert np.isclose(
        dynamic_payload["ten_year_deficit_impact"], static_payload["ten_year_deficit_impact"]
    )
    assert np.isclose(dynamic_payload["ten_year_deficit_impact"], view.conventional)
    assert np.isclose(
        dynamic_payload["final_static_effect"],
        dynamic_payload["static_revenue_effect"] - dynamic_payload["behavioral_offset"],
    )
    assert np.isclose(
        dynamic_payload["dynamic_adjusted_impact"],
        dynamic_payload["ten_year_deficit_impact"]
        - dynamic_payload["revenue_feedback"]
        + dynamic_payload["debt_service"],
    )
    assert dynamic_payload["dynamic_model"] == FRBUS_LITE_MODEL_LABEL


def test_an_economic_model_run_is_never_reported():
    """Serializing a ``dynamic=True`` engine run reports the app's view.

    The engine subtracts EconomicModel feedback from ``final_deficit_effect``
    on such a run; the serializer reads the conventional path instead, and the
    dynamic fields come only from the view it is handed.
    """
    policy, engine_dynamic = _score_simple_tax_increase(dynamic=True)
    _, engine_static = _score_simple_tax_increase(dynamic=False)
    assert engine_dynamic.dynamic_effects is not None
    economic_model_feedback = float(np.sum(engine_dynamic.dynamic_effects.revenue_feedback))

    payload, view, _macro = _serialize_dynamic(policy, engine_dynamic)
    static_view, _ = run_dynamic_view(policy, engine_static)

    assert np.isclose(payload["ten_year_deficit_impact"], float(np.sum(engine_static.final_deficit_effect)))
    assert not np.isclose(payload["ten_year_deficit_impact"], engine_dynamic.total_10_year_cost)
    assert not np.isclose(payload["revenue_feedback"], economic_model_feedback)
    # The view needs only the conventional path, so how the engine was run
    # does not move it.
    assert static_view is not None
    assert np.isclose(view.dynamic_total, static_view.dynamic_total)
    assert np.isclose(payload["dynamic_adjusted_impact"], static_view.dynamic_total)


def test_display_flag_hides_a_view_and_a_missing_view_is_reported():
    policy, result = _score_simple_tax_increase(dynamic=False)
    view, macro = run_dynamic_view(policy, result)

    hidden = serialize_scoring_result(
        result,
        policy_name=policy.name,
        policy_description=policy.description,
        dynamic_scoring_enabled=False,
        dynamic_view=view,
        macro_result=macro,
    )
    assert hidden["revenue_feedback"] == 0.0
    assert hidden["dynamic_adjusted_impact"] is None
    assert hidden["error_message"] is None
    assert all(entry["dynamic_feedback"] == 0.0 for entry in hidden["year_by_year"])

    missing = serialize_scoring_result(
        result,
        policy_name=policy.name,
        policy_description=policy.description,
        dynamic_scoring_enabled=True,
    )
    assert missing["error_message"] == DYNAMIC_VIEW_UNAVAILABLE_MESSAGE
    assert missing["revenue_feedback"] is None
    assert missing["dynamic_adjusted_impact"] is None
    assert np.isclose(missing["ten_year_deficit_impact"], hidden["ten_year_deficit_impact"])


def test_dynamic_year_by_year_reconciles_with_the_ten_year_fields():
    policy, result = _score_simple_tax_increase(dynamic=False)
    payload, view, macro = _serialize_dynamic(policy, result)
    years = payload["year_by_year"]

    assert np.isclose(sum(e["final_effect"] for e in years), view.conventional)
    assert np.isclose(sum(e["dynamic_feedback"] for e in years), view.feedback)
    assert np.isclose(sum(e["debt_service"] for e in years), view.debt_service)
    assert np.isclose(sum(e["dynamic_effect"] for e in years), view.dynamic_total)
    assert np.isclose(payload["gdp_effect"], macro.cumulative_gdp_effect)
    # The adapters report millions of jobs; the API field is thousands.
    assert np.isclose(
        payload["employment_effect"], float(np.mean(macro.employment_change_millions)) * 1000.0
    )


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
    # Since Wave C's H4 the accuracy claim is the policy's own out-of-sample
    # class, not a mean over a scorecard category. ``uncertainty_low`` and
    # ``uncertainty_high`` keep their names and are now the class's mean error
    # applied to this figure; ``outer_low`` / ``outer_high`` are its worst row.
    assert credibility["evidence_type"] == "out_of_sample_class_distribution"
    assert credibility["policy_class"] in {"ordinary_rate_change", "agi_inclusive_surtax"}
    assert credibility["n_tier1_rows"] >= 1
    assert credibility["holdout_status"] == "not_applicable_generic"
    assert credibility["uncertainty_low"] <= payload["ten_year_deficit_impact"]
    assert credibility["uncertainty_high"] >= payload["ten_year_deficit_impact"]
    assert credibility["outer_low"] <= credibility["uncertainty_low"]
    assert credibility["outer_high"] >= credibility["uncertainty_high"]
    assert any("holdout" in item for item in credibility["limitations"])
