from __future__ import annotations

import numpy as np
from types import SimpleNamespace

from fiscal_model.app_data import PRESET_POLICIES
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
        fiscal_policy_scorer_cls=DummyScorer,
        use_real_data=True,
    )

    assert scored["ten_year_cost"] == 6.0
    assert scored["years"].tolist() == [2025, 2026, 2027]
