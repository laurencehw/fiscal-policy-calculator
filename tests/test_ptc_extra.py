"""
Focused coverage for premium tax credit policy branches.
"""

from __future__ import annotations

from math import isclose

import pytest

from fiscal_model.policies import PolicyType
from fiscal_model.ptc import (
    CBO_PTC_ESTIMATES,
    FPL_2025,
    PremiumTaxCreditPolicy,
    create_extend_enhanced_ptc,
    create_lower_premium_cap,
    create_repeal_ptc,
    estimate_ptc_cost,
    get_fpl,
)


def test_get_fpl_supports_large_households_and_year_growth():
    assert get_fpl(9, 2025) == FPL_2025[8] + 5_500
    assert get_fpl(4, 2026) > get_fpl(4, 2025)


def test_get_premium_cap_interpolates_enhanced_and_original_brackets():
    policy = PremiumTaxCreditPolicy(
        name="PTC",
        description="Test",
        policy_type=PolicyType.TAX_CREDIT,
    )

    assert isclose(policy.get_premium_cap(175, use_enhanced=True), 0.01, rel_tol=1e-6)
    assert isclose(policy.get_premium_cap(350, use_enhanced=False), 0.09735, rel_tol=1e-4)
    assert policy.get_premium_cap(600, use_enhanced=False) == 1.0


def test_calculate_subsidy_handles_ineligible_original_aca_case():
    policy = PremiumTaxCreditPolicy(
        name="PTC",
        description="Test",
        policy_type=PolicyType.TAX_CREDIT,
    )

    subsidy = policy.calculate_subsidy(
        income=100_000,
        family_size=1,
        benchmark_premium=12_000,
        year=2026,
        use_enhanced=False,
    )

    assert subsidy["eligible"] is False
    assert subsidy["subsidy"] == 0.0
    assert subsidy["expected_contribution"] == 12_000


def test_calculate_subsidy_applies_premium_cap_modifications():
    policy = PremiumTaxCreditPolicy(
        name="PTC",
        description="Test",
        policy_type=PolicyType.TAX_CREDIT,
        modify_premium_cap=True,
        new_premium_cap_max=0.05,
        premium_cap_change=-0.01,
    )

    subsidy = policy.calculate_subsidy(
        income=60_000,
        family_size=2,
        benchmark_premium=15_000,
        year=2026,
        use_enhanced=True,
    )

    assert subsidy["eligible"] is True
    assert isclose(subsidy["premium_cap"], 0.04, rel_tol=1e-6)
    assert isclose(subsidy["expected_contribution"], 2_400.0, rel_tol=1e-6)
    assert isclose(subsidy["subsidy"], 12_600.0, rel_tol=1e-6)


@pytest.mark.parametrize(
    ("policy", "coverage_change", "uninsured_change"),
    [
        (create_repeal_ptc(), -19.0, 15.2),
        (create_extend_enhanced_ptc(), 4.0, -4.0),
        (
            PremiumTaxCreditPolicy(
                name="Baseline",
                description="Baseline",
                policy_type=PolicyType.TAX_CREDIT,
            ),
            -4.0,
            4.0,
        ),
    ],
)
def test_estimate_coverage_effect_branches(policy, coverage_change, uninsured_change):
    effect = policy.estimate_coverage_effect()

    assert effect["coverage_change_millions"] == pytest.approx(coverage_change)
    assert effect["uninsured_change_millions"] == pytest.approx(uninsured_change)


def test_estimate_static_revenue_effect_handles_cap_change_branch():
    policy = PremiumTaxCreditPolicy(
        name="Cap change",
        description="Cap change",
        policy_type=PolicyType.TAX_CREDIT,
        modify_premium_cap=True,
        premium_cap_change=-0.02,
    )

    assert policy.estimate_static_revenue_effect(0) == pytest.approx(-20.0)


def test_estimate_behavioral_offset_flips_sign_for_savings_vs_costs():
    policy = PremiumTaxCreditPolicy(
        name="Behavior",
        description="Behavior",
        policy_type=PolicyType.TAX_CREDIT,
        coverage_elasticity=0.3,
        adverse_selection_factor=0.1,
    )

    assert policy.estimate_behavioral_offset(100.0) == pytest.approx(-13.0)
    assert policy.estimate_behavioral_offset(-100.0) == pytest.approx(3.0)


def test_factory_helpers_produce_expected_static_costs():
    policy = create_lower_premium_cap(new_max_cap=0.05)

    assert "5%" in policy.name
    assert policy.annual_revenue_change_billions == pytest.approx(-65.5)


def test_estimate_ptc_cost_applies_growth_curve():
    policy = create_extend_enhanced_ptc()

    cost = estimate_ptc_cost(policy)
    expected_static = sum(policy.annual_revenue_change_billions * (1.04**year) for year in range(10))

    assert cost["annual_static"] == pytest.approx(policy.annual_revenue_change_billions)
    assert cost["ten_year_static"] == pytest.approx(expected_static)
    assert cost["behavioral_offset"] == 0.0
    assert cost["net_effect"] == pytest.approx(expected_static)
    assert cost["coverage_change_millions"] == 4.0


def test_repeal_ptc_defaults_to_baseline_savings_when_not_calibrated():
    policy = PremiumTaxCreditPolicy(
        name="Repeal",
        description="Repeal",
        policy_type=PolicyType.TAX_CREDIT,
        repeal_ptc=True,
    )

    assert policy.estimate_static_revenue_effect(0) == CBO_PTC_ESTIMATES["baseline_enhanced_annual"]
