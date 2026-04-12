"""
Focused coverage for remaining payroll policy branches.
"""

from __future__ import annotations

import pytest

from fiscal_model.payroll import (
    BASELINE_WAGE_DATA,
    CBO_PAYROLL_ESTIMATES,
    PayrollTaxPolicy,
    create_biden_payroll_proposal,
    create_expand_niit,
    create_medicare_rate_increase,
    create_ss_cap_90_percent,
    create_ss_eliminate_cap,
    create_ss_rate_increase,
    estimate_payroll_revenue,
)
from fiscal_model.policies import PolicyType


def test_get_effective_ss_cap_branches():
    eliminate_cap = PayrollTaxPolicy(
        name="Eliminate",
        description="Eliminate",
        policy_type=PolicyType.PAYROLL_TAX,
        ss_eliminate_cap=True,
    )
    new_cap = PayrollTaxPolicy(
        name="New cap",
        description="New cap",
        policy_type=PolicyType.PAYROLL_TAX,
        ss_new_cap=250_000,
    )
    cover_90 = PayrollTaxPolicy(
        name="90 pct",
        description="90 pct",
        policy_type=PolicyType.PAYROLL_TAX,
        ss_cover_90_pct=True,
    )
    shifted_cap = PayrollTaxPolicy(
        name="Shifted cap",
        description="Shifted cap",
        policy_type=PolicyType.PAYROLL_TAX,
        ss_cap_change=10_000,
    )

    assert eliminate_cap.get_effective_ss_cap(2026) is None
    assert new_cap.get_effective_ss_cap(2026) == 250_000
    assert cover_90.get_effective_ss_cap(2025) == pytest.approx(305_000 * 1.044)
    assert shifted_cap.get_effective_ss_cap(2026) == pytest.approx((176_100 + 10_000) * 1.044)


def test_estimate_static_revenue_effect_combines_unmodeled_branches():
    policy = PayrollTaxPolicy(
        name="Combined",
        description="Combined",
        policy_type=PolicyType.PAYROLL_TAX,
        ss_donut_hole_start=500_000,
        ss_rate_change=0.01,
        medicare_rate_change=0.005,
        expand_niit_to_passthrough=True,
    )

    effect = policy.estimate_static_revenue_effect(0)
    expected_donut = (
        BASELINE_WAGE_DATA["wages_250k_plus_billions"] * (250_000 / 500_000) * 0.124
    )
    expected_total = expected_donut + 90.0 + 70.0 + CBO_PAYROLL_ESTIMATES["expand_niit_annual"]

    assert effect == pytest.approx(expected_total)


def test_estimate_static_revenue_effect_prefers_calibrated_value():
    policy = PayrollTaxPolicy(
        name="Calibrated",
        description="Calibrated",
        policy_type=PolicyType.PAYROLL_TAX,
        annual_revenue_change_billions=12.5,
        ss_eliminate_cap=True,
    )

    assert policy.estimate_static_revenue_effect(0) == 12.5


def test_estimate_behavioral_offset_sign_and_avoidance_branches():
    high_avoidance = PayrollTaxPolicy(
        name="Donut",
        description="Donut",
        policy_type=PolicyType.PAYROLL_TAX,
        ss_donut_hole_start=250_000,
        labor_supply_elasticity=0.1,
        tax_avoidance_elasticity=0.15,
    )
    low_avoidance = PayrollTaxPolicy(
        name="Medicare",
        description="Medicare",
        policy_type=PolicyType.PAYROLL_TAX,
        payroll_tax_type=high_avoidance.payroll_tax_type.MEDICARE,
        labor_supply_elasticity=0.1,
        tax_avoidance_elasticity=0.15,
    )

    assert high_avoidance.estimate_behavioral_offset(100.0) == pytest.approx(-25.0)
    assert low_avoidance.estimate_behavioral_offset(-100.0) == pytest.approx(17.5)


def test_factory_helpers_keep_expected_policy_shapes():
    assert create_ss_cap_90_percent().annual_revenue_change_billions == pytest.approx(58.5)
    assert create_ss_eliminate_cap().annual_revenue_change_billions == pytest.approx(234.0)
    assert create_expand_niit().annual_revenue_change_billions == pytest.approx(18.3)

    ss_rate = create_ss_rate_increase(0.01)
    medicare_rate = create_medicare_rate_increase(0.005)
    biden = create_biden_payroll_proposal()

    assert ss_rate.name == "SS Rate +1.0pp"
    assert ss_rate.annual_revenue_change_billions == pytest.approx(78.5)
    assert medicare_rate.payroll_tax_type.name == "MEDICARE"
    assert medicare_rate.annual_revenue_change_billions == pytest.approx(61.0)
    assert biden.ss_donut_hole_start == 400_000
    assert biden.annual_revenue_change_billions == pytest.approx(122.0)


def test_estimate_payroll_revenue_applies_growth_and_behavior():
    policy = PayrollTaxPolicy(
        name="Revenue summary",
        description="Revenue summary",
        policy_type=PolicyType.PAYROLL_TAX,
        annual_revenue_change_billions=100.0,
        labor_supply_elasticity=0.1,
        tax_avoidance_elasticity=0.15,
    )

    result = estimate_payroll_revenue(policy)
    growth_factor_sum = sum(1.04**year for year in range(10))

    assert result["annual_static"] == 100.0
    assert result["ten_year_static"] == pytest.approx(100.0 * growth_factor_sum)
    assert result["behavioral_offset"] == pytest.approx(-17.5 * growth_factor_sum)
    assert result["net_effect"] == pytest.approx((100.0 - 17.5) * growth_factor_sum)
