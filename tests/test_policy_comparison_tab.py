from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from fiscal_model.app_data import PRESET_POLICIES
from fiscal_model.models.base import CBOStyleModel
from fiscal_model.policies import PolicyType, TaxPolicy
from fiscal_model.ui.tabs.policy_comparison import _build_policy_for_comparison, _score_model


def test_build_policy_for_tcja_preset_uses_valid_phase_in():
    preset_name = "🏛️ TCJA Full Extension (CBO: $4.6T)"
    policy = _build_policy_for_comparison(
        preset_name=preset_name,
        preset=PRESET_POLICIES[preset_name],
        tax_policy_cls=TaxPolicy,
        policy_type_income_tax=PolicyType.INCOME_TAX,
        data_year=2022,
    )

    assert policy is not None
    assert getattr(policy, "phase_in_years", 1) >= 1


def test_build_policy_for_climate_preset_returns_climate_policy():
    preset_name = "🌱 Carbon Tax \\$50/ton (-$1.7T)"
    policy = _build_policy_for_comparison(
        preset_name=preset_name,
        preset=PRESET_POLICIES[preset_name],
        tax_policy_cls=TaxPolicy,
        policy_type_income_tax=PolicyType.INCOME_TAX,
        data_year=2022,
    )

    assert type(policy).__name__ == "ClimateEnergyPolicy"


def test_score_model_uses_final_deficit_effect_sum():
    class DummyScorer:
        def __init__(self, baseline=None, use_real_data=True):
            del baseline, use_real_data

        def score_policy(self, policy, dynamic=False):
            del policy, dynamic
            return SimpleNamespace(
                final_deficit_effect=np.array([1.0, 2.0, 3.0]),
                baseline=SimpleNamespace(years=np.array([2025, 2026, 2027])),
            )

    scored = _score_model(
        policy_name="Test Policy",
        model_name="CBO-Style (Static + ETI)",
        policy=object(),
        scorer=DummyScorer(),
        dynamic=False,
    )

    assert scored["ten_year_cost"] == 6.0
    assert scored["years"].tolist() == [2025, 2026, 2027]


def test_score_model_uses_policy_duration_when_baseline_years_missing():
    class DummyScorer:
        def score_policy(self, policy, dynamic=False):
            del dynamic
            return SimpleNamespace(
                final_deficit_effect=None,
                static_revenue_effect=None,
                baseline=None,
                policy=policy,
            )

    policy = SimpleNamespace(start_year=2030, duration_years=4)
    scored = _score_model(
        policy_name="Test Policy",
        model_name="CBO-Style (Static + ETI)",
        policy=policy,
        scorer=DummyScorer(),
        dynamic=False,
    )

    assert scored["ten_year_cost"] == 0.0
    assert scored["years"].tolist() == [2030, 2031, 2032, 2033]
    assert scored["annual_effects"].tolist() == [0.0, 0.0, 0.0, 0.0]


def test_cbo_style_model_reuses_single_scorer_instance():
    class CountingScorer:
        init_calls = 0

        def __init__(self, use_real_data=True):
            del use_real_data
            CountingScorer.init_calls += 1

        def score_policy(self, policy, dynamic=False):
            del policy, dynamic
            return SimpleNamespace(
                final_deficit_effect=np.array([1.0, 2.0]),
                baseline=SimpleNamespace(years=np.array([2025, 2026])),
            )

    model = CBOStyleModel(CountingScorer, use_real_data=True)
    model.score(SimpleNamespace(name="First", duration_years=2))
    model.score(SimpleNamespace(name="Second", duration_years=2))

    assert CountingScorer.init_calls == 1


def test_cbo_style_model_aggregates_uncertainty_range():
    class DummyScorer:
        def __init__(self, use_real_data=True):
            del use_real_data

        def score_policy(self, policy, dynamic=False):
            del policy, dynamic
            return SimpleNamespace(
                final_deficit_effect=np.array([1.0, 2.0]),
                low_estimate=np.array([0.5, 1.5]),
                high_estimate=np.array([1.5, 2.5]),
                baseline=SimpleNamespace(years=np.array([2025, 2026])),
            )

    model = CBOStyleModel(DummyScorer, use_real_data=True)
    scored = model.score(SimpleNamespace(name="With Range", duration_years=2))

    assert scored.uncertainty_range == (2.0, 4.0)
