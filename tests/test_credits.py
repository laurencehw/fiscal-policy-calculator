"""
Focused tests for tax credit calculation helpers.
"""

from __future__ import annotations

import pytest

from fiscal_model.credits import (
    CreditType,
    TaxCreditPolicy,
    create_biden_ctc_2021,
    create_biden_eitc_childless,
    create_ctc_expansion,
    create_ctc_permanent_extension,
    create_eitc_expansion,
    estimate_credit_cost,
)
from fiscal_model.policies import PolicyType


@pytest.fixture
def partially_refundable_ctc():
    return TaxCreditPolicy(
        name="Partial CTC",
        description="Partially refundable CTC",
        policy_type=PolicyType.TAX_CREDIT,
        credit_type=CreditType.CHILD_TAX_CREDIT,
        is_partially_refundable=True,
        max_credit_per_unit=2000.0,
        refundable_max=1700.0,
        refund_rate=0.15,
        refund_threshold=2500.0,
        phase_out_threshold_single=200000.0,
        phase_out_threshold_married=400000.0,
        phase_out_rate=0.05,
    )


def test_income_tax_credit_policy_is_normalized():
    policy = TaxCreditPolicy(
        name="Normalize Credit Type",
        description="Should normalize policy type",
        policy_type=PolicyType.INCOME_TAX,
        credit_type=CreditType.OTHER,
    )
    assert policy.policy_type == PolicyType.TAX_CREDIT


def test_calculate_credit_for_income_phase_in_below_threshold():
    policy = TaxCreditPolicy(
        name="Phase-in credit",
        description="EITC-style phase in",
        policy_type=PolicyType.TAX_CREDIT,
        credit_type=CreditType.EARNED_INCOME_CREDIT,
        is_refundable=True,
        max_credit_per_unit=1000.0,
        has_phase_in=True,
        phase_in_rate=0.5,
        phase_in_threshold=1000.0,
        phase_in_end=3000.0,
        has_phase_out=False,
    )
    result = policy.calculate_credit_for_income(earned_income=500.0, agi=500.0)
    assert result["gross_credit"] == 0.0
    assert result["net_credit"] == 0.0


def test_calculate_credit_for_income_phase_in_partial_credit():
    policy = TaxCreditPolicy(
        name="Phase-in credit",
        description="EITC-style phase in",
        policy_type=PolicyType.TAX_CREDIT,
        credit_type=CreditType.EARNED_INCOME_CREDIT,
        is_refundable=True,
        max_credit_per_unit=1000.0,
        has_phase_in=True,
        phase_in_rate=0.5,
        phase_in_threshold=1000.0,
        phase_in_end=3000.0,
        has_phase_out=False,
    )
    result = policy.calculate_credit_for_income(earned_income=2000.0, agi=2000.0)
    assert result["gross_credit"] == pytest.approx(500.0)
    assert result["refundable_portion"] == pytest.approx(500.0)


def test_calculate_credit_for_income_applies_married_phase_out(partially_refundable_ctc):
    result = partially_refundable_ctc.calculate_credit_for_income(
        earned_income=50000.0,
        agi=405000.0,
        filing_status="married",
        num_children=1,
    )
    assert result["net_credit"] < result["gross_credit"]


def test_calculate_credit_for_income_partial_refund_split(partially_refundable_ctc):
    result = partially_refundable_ctc.calculate_credit_for_income(
        earned_income=10000.0,
        agi=10000.0,
        num_children=1,
    )
    assert result["refundable_portion"] == pytest.approx(1125.0)
    assert result["non_refundable_portion"] == pytest.approx(875.0)


def test_calculate_credit_for_income_remove_phase_out_bypasses_reduction():
    policy = TaxCreditPolicy(
        name="No phase-out",
        description="Remove phase-out",
        policy_type=PolicyType.TAX_CREDIT,
        credit_type=CreditType.CHILD_TAX_CREDIT,
        max_credit_per_unit=2000.0,
        remove_phase_out=True,
        phase_out_threshold_single=1000.0,
        phase_out_threshold_married=2000.0,
        phase_out_rate=1.0,
    )
    result = policy.calculate_credit_for_income(earned_income=0.0, agi=5000.0, num_children=1)
    assert result["net_credit"] == 2000.0


@pytest.mark.parametrize(
    ("policy", "expected"),
    [
        (
            TaxCreditPolicy(
                name="Per-unit change",
                description="Per-unit static cost",
                policy_type=PolicyType.TAX_CREDIT,
                credit_type=CreditType.CHILD_TAX_CREDIT,
                credit_change_per_unit=1000.0,
                units_affected_millions=10.0,
                participation_rate=0.8,
            ),
            -8.0,
        ),
        (
            TaxCreditPolicy(
                name="Full refundability",
                description="Make CTC fully refundable",
                policy_type=PolicyType.TAX_CREDIT,
                credit_type=CreditType.CHILD_TAX_CREDIT,
                make_fully_refundable=True,
            ),
            -50.0,
        ),
        (
            TaxCreditPolicy(
                name="Remove phase-out",
                description="Remove CTC phase-out",
                policy_type=PolicyType.TAX_CREDIT,
                credit_type=CreditType.CHILD_TAX_CREDIT,
                remove_phase_out=True,
            ),
            -5.0,
        ),
    ],
)
def test_estimate_static_revenue_effect_branches(policy, expected):
    assert policy.estimate_static_revenue_effect(0) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("policy", "expected"),
    [
        (
            TaxCreditPolicy(
                name="EITC behavior",
                description="EITC behavior",
                policy_type=PolicyType.TAX_CREDIT,
                credit_type=CreditType.EARNED_INCOME_CREDIT,
            ),
            -1.2,
        ),
        (
            TaxCreditPolicy(
                name="CTC behavior",
                description="CTC behavior",
                policy_type=PolicyType.TAX_CREDIT,
                credit_type=CreditType.CHILD_TAX_CREDIT,
            ),
            -0.5,
        ),
        (
            TaxCreditPolicy(
                name="Other behavior",
                description="Other credit behavior",
                policy_type=PolicyType.TAX_CREDIT,
                credit_type=CreditType.OTHER,
                labor_supply_elasticity=0.2,
            ),
            0.6,
        ),
    ],
)
def test_estimate_behavioral_offset_branches(policy, expected):
    assert policy.estimate_behavioral_offset(-10.0) == pytest.approx(expected)


def test_factory_helpers_return_expected_credit_types():
    assert create_ctc_expansion(credit_per_child=3000).credit_type == CreditType.CHILD_TAX_CREDIT
    assert create_biden_ctc_2021().credit_type == CreditType.CHILD_TAX_CREDIT
    assert create_ctc_permanent_extension().credit_type == CreditType.CHILD_TAX_CREDIT
    assert create_eitc_expansion(childless_max_increase=500).credit_type == CreditType.EARNED_INCOME_CREDIT
    assert create_biden_eitc_childless().credit_type == CreditType.EARNED_INCOME_CREDIT


def test_create_eitc_expansion_combines_cost_components():
    policy = create_eitc_expansion(
        childless_max_increase=1000.0,
        with_children_increase_pct=0.10,
        expand_age_range=True,
    )
    assert policy.annual_revenue_change_billions == pytest.approx(-(7.65 + 6.6 + 1.5))
    assert "expand age 19-24/65+" in policy.description


def test_estimate_credit_cost_returns_consistent_totals():
    policy = create_biden_ctc_2021()
    estimate = estimate_credit_cost(policy)
    assert estimate["annual_cost"] > 0
    assert estimate["ten_year_cost"] > estimate["annual_cost"]
    assert estimate["net_cost"] == pytest.approx(
        estimate["ten_year_cost"] - estimate["behavioral_offset"]
    )
