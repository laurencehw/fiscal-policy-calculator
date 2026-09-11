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
        # Lane HSD/H11 moved these off ``MARKETPLACE_DATA``'s uncited "19
        # million" and "4 million" and onto CBO's own tables. The repeal removes
        # publication 51298 Table 1's subsidized marketplace enrolment averaged
        # over the policy's window — 11.06M on February 2026 over FY2026-2035,
        # against the 19.0M this test used to pin, which is nearer calendar
        # 2025's 20.9M, the last year of the ARPA/IRA enhancement — and the
        # uninsured leg is publication 60437 p. 5's own destination share rather
        # than an uncited 0.8.
        (create_repeal_ptc(), -11.06, 11.06 * 3.4 / 7.4),
        (create_extend_enhanced_ptc(), 7.4, -3.4),
        (
            PremiumTaxCreditPolicy(
                name="Baseline",
                description="Baseline",
                policy_type=PolicyType.TAX_CREDIT,
            ),
            -7.4,
            3.4,
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


def test_estimate_behavioral_offset_erodes_both_ways_and_stays_asymmetric():
    """Signed with the static effect, and still bigger when subsidies are cut.

    The module returned the *negation* of these numbers until the offset-sign
    sweep (2026-09-05) — a PTC repeal booked 13% more saving than its own
    static effect, and the fitted ``repeal_ptc`` benchmark read 0.3% through
    that. The magnitudes are unchanged and stay asymmetric on purpose:
    ``adverse_selection_factor`` fires only when subsidies are taken away,
    because the premium spiral has no mirror image when they are extended.
    """
    policy = PremiumTaxCreditPolicy(
        name="Behavior",
        description="Behavior",
        policy_type=PolicyType.TAX_CREDIT,
        coverage_elasticity=0.3,
        adverse_selection_factor=0.1,
    )

    assert policy.estimate_behavioral_offset(100.0) == pytest.approx(13.0)
    assert policy.estimate_behavioral_offset(-100.0) == pytest.approx(-3.0)


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
    # Publication 60437 p. 5's own subsidized marketplace line, since lane
    # HSD/H11; it was ``MARKETPLACE_DATA``'s uncited 4.0.
    assert cost["coverage_change_millions"] == pytest.approx(7.4)


def test_repeal_removes_the_vintages_own_credit_path_not_a_level():
    """An uncalibrated repeal reads CBO's projection for the year it is asked about.

    Before lane W7 this branch returned ``CBO_PTC_ESTIMATES``'
    ``baseline_enhanced_annual``, an unsourced "~$95B/year" that no factory ever
    reached — ``create_repeal_ptc`` pinned an annual of 83.0 on top of it. The
    constant is left in the module for the other branches; nothing in the
    scoring path reads it any more.
    """
    policy = PremiumTaxCreditPolicy(
        name="Repeal",
        description="Repeal",
        policy_type=PolicyType.TAX_CREDIT,
        repeal_ptc=True,
    )

    assert policy.uses_baseline_credit_path() is True
    # Publication 51298 (February 2026) Table 2: FY2028 outlays 66 + revenue
    # reductions 8. Not a level, and not 95.0.
    assert policy.estimate_static_revenue_effect(0, year=2028) == pytest.approx(74.0)
    assert policy.estimate_static_revenue_effect(0, year=2034) == pytest.approx(113.0)
    assert (
        policy.estimate_static_revenue_effect(0, year=2028)
        != CBO_PTC_ESTIMATES["baseline_enhanced_annual"]
    )
