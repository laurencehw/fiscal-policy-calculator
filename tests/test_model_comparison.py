from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from fiscal_model.models.comparison import (
    PWBMScoringModel,
    TPCMicrosimModel,
    UnsupportedModelPolicyError,
    build_default_comparison_models,
    compare_policy_models,
)
from fiscal_model.policies import PolicyType, TaxPolicy


def _pilot_policy(rate_change: float = 0.02) -> TaxPolicy:
    return TaxPolicy(
        name="Pilot Top Rate",
        description="Pilot comparison policy",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=rate_change,
        affected_income_threshold=500_000,
        duration_years=3,
        phase_in_years=1,
        taxable_income_elasticity=0.25,
        data_year=2022,
    )


def test_tpc_microsim_model_scores_supported_policy():
    population = pd.DataFrame(
        [
            {
                "id": 1,
                "weight": 1.0,
                "wages": 1_000_000,
                "interest_income": 0.0,
                "dividend_income": 0.0,
                "capital_gains": 0.0,
                "social_security": 0.0,
                "unemployment": 0.0,
                "children": 0,
                "married": 0,
                "age_head": 45,
                "agi": 1_000_000,
            },
            {
                "id": 2,
                "weight": 1.0,
                "wages": 40_000,
                "interest_income": 0.0,
                "dividend_income": 0.0,
                "capital_gains": 0.0,
                "social_security": 0.0,
                "unemployment": 0.0,
                "children": 1,
                "married": 1,
                "age_head": 39,
                "agi": 40_000,
            },
        ]
    )
    model = TPCMicrosimModel(population=population)

    result = model.score(_pilot_policy())

    assert result.model_name == "TPC-Microsim Pilot"
    assert len(result.annual_effects) == 3
    assert result.ten_year_cost < 0
    assert result.distributional is not None
    assert result.metadata["annualization_assumption"] == "flat_by_year"
    assert result.metadata["reforms"]["income_rate_change"] == pytest.approx(0.02)
    assert result.metadata["reforms"]["income_rate_change_threshold"] == pytest.approx(500_000)
    assert any("policy threshold" in note for note in result.metadata["notes"])


def test_tpc_microsim_model_can_apply_top_tail_augmentation():
    population = pd.DataFrame(
        [
            {
                "id": 1,
                "weight": 1.0,
                "wages": 1_000_000,
                "interest_income": 0.0,
                "dividend_income": 0.0,
                "capital_gains": 0.0,
                "social_security": 0.0,
                "unemployment": 0.0,
                "children": 0,
                "married": 0,
                "age_head": 45,
                "agi": 1_000_000,
            }
        ]
    )

    def fake_augmenter(frame, *, year):
        augmented = pd.concat(
            [
                frame,
                pd.DataFrame(
                    [
                        {
                            "id": 2,
                            "weight": 10.0,
                            "wages": 5_000_000,
                            "interest_income": 0.0,
                            "dividend_income": 0.0,
                            "capital_gains": 0.0,
                            "social_security": 0.0,
                            "unemployment": 0.0,
                            "children": 0,
                            "married": 1,
                            "age_head": 55,
                            "agi": 5_000_000,
                        }
                    ]
                ),
            ],
            ignore_index=True,
        )
        return augmented, SimpleNamespace(year=year, synthetic_records=1)

    baseline_model = TPCMicrosimModel(population=population)
    augmented_model = TPCMicrosimModel(
        population=population,
        augment_top_tail_enabled=True,
        augmentation_year=2023,
        top_tail_augmenter=fake_augmenter,
    )

    baseline_result = baseline_model.score(_pilot_policy())
    augmented_result = augmented_model.score(_pilot_policy())

    assert augmented_result.ten_year_cost < baseline_result.ten_year_cost
    assert augmented_result.metadata["augmentation"] == {
        "year": 2023,
        "synthetic_records": 1,
    }
    assert any("top-tail augmentation" in note for note in augmented_result.metadata["notes"])


def test_tpc_microsim_model_rejects_unsupported_policy():
    population = pd.DataFrame(
        [
            {
                "id": 1,
                "weight": 1.0,
                "wages": 50_000,
                "children": 0,
                "married": 0,
                "age_head": 35,
                "agi": 50_000,
            }
        ]
    )
    model = TPCMicrosimModel(population=population)

    with pytest.raises(UnsupportedModelPolicyError):
        model.score(_pilot_policy(rate_change=0.0))


def test_pwbm_scoring_model_combines_static_and_macro_paths():
    class DummyScorer:
        def __init__(self, use_real_data=False):
            del use_real_data

        def score_policy(self, policy, dynamic=False):
            del policy, dynamic
            return SimpleNamespace(
                final_deficit_effect=np.array([10.0, 20.0]),
            )

    class DummyMacroModel:
        name = "Dummy PWBM"

        def run(self, scenario):
            del scenario
            return SimpleNamespace(
                revenue_feedback_billions=np.array([1.0, 2.0]),
                interest_cost_billions=np.array([0.5, 0.25]),
                confidence_label="wide uncertainty band",
                olg_overrides={"tau_k": 0.31},
            )

    model = PWBMScoringModel(
        DummyScorer,
        macro_model=DummyMacroModel(),
        use_real_data=False,
    )

    result = model.score(_pilot_policy())

    assert result.annual_effects == pytest.approx([9.5, 18.25])
    assert result.ten_year_cost == pytest.approx(27.75)
    assert result.metadata["macro_model"] == "Dummy PWBM"
    assert result.metadata["olg_overrides"] == {"tau_k": 0.31}
    assert "confidence_label" in result.metadata


def test_default_comparison_models_exclude_experimental_pwbm():
    default_models = build_default_comparison_models(lambda **kwargs: None)
    opt_in_models = build_default_comparison_models(
        lambda **kwargs: None,
        include_experimental_pwbm=True,
    )

    assert [model.name for model in default_models] == ["CBO-Style", "TPC-Microsim Pilot"]
    assert default_models[1]._augment_top_tail_enabled is True
    assert [model.name for model in opt_in_models] == [
        "CBO-Style",
        "TPC-Microsim Pilot",
        "PWBM-OLG Pilot",
    ]


def test_compare_policy_models_collects_errors_when_requested():
    class GoodModel:
        name = "Good"

        def score(self, policy):
            return SimpleNamespace(
                model_name="Good",
                policy_name=policy.name,
                ten_year_cost=1.0,
                annual_effects=[1.0],
                uncertainty_range=None,
                distributional=None,
                metadata={"methodology": "good"},
            )

    class BadModel:
        name = "Bad"

        def score(self, policy):
            del policy
            raise UnsupportedModelPolicyError("not supported")

    bundle = compare_policy_models(_pilot_policy(), [GoodModel(), BadModel()], continue_on_error=True)

    assert len(bundle.results) == 1
    assert bundle.errors == {"Bad": "not supported"}
    assert bundle.to_dataframe().iloc[0]["Model"] == "Good"
