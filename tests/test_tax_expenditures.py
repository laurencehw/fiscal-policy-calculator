"""
Tests for tax expenditure models and factory helpers.
"""

from __future__ import annotations

import pytest

from fiscal_model.policies import PolicyType
from fiscal_model.tax_expenditures import (
    TaxExpenditurePolicy,
    TaxExpenditureType,
    create_cap_charitable_deduction,
    create_cap_employer_health_exclusion,
    create_cap_retirement_contributions,
    create_eliminate_like_kind_exchange,
    create_eliminate_mortgage_deduction,
    create_eliminate_salt_deduction,
    create_eliminate_step_up_basis,
    create_repeal_salt_cap,
    estimate_expenditure_revenue,
    get_all_expenditure_estimates,
)


@pytest.mark.parametrize(
    ("factory", "expected_sign"),
    [
        (create_cap_employer_health_exclusion, 1),
        (create_eliminate_mortgage_deduction, 1),
        (create_repeal_salt_cap, -1),
        (create_eliminate_salt_deduction, 1),
        (create_cap_charitable_deduction, 1),
        (create_eliminate_step_up_basis, 1),
        (create_eliminate_like_kind_exchange, 1),
        (create_cap_retirement_contributions, 1),
    ],
)
def test_factory_policies_produce_expected_sign(factory, expected_sign):
    policy = factory()
    effect = policy.estimate_static_revenue_effect(0)
    assert isinstance(policy, TaxExpenditurePolicy)
    assert effect != 0
    assert effect * expected_sign > 0


def test_income_tax_policy_type_is_normalized_to_tax_deduction():
    policy = TaxExpenditurePolicy(
        name="Normalize Type",
        description="Policy type should be normalized",
        policy_type=PolicyType.INCOME_TAX,
        expenditure_type=TaxExpenditureType.CHARITABLE,
    )
    assert policy.policy_type == PolicyType.TAX_DEDUCTION


def test_get_expenditure_data_defaults_to_charitable_for_unmapped_type():
    policy = TaxExpenditurePolicy(
        name="Fallback Data",
        description="Uses charitable fallback",
        policy_type=PolicyType.TAX_DEDUCTION,
        expenditure_type=TaxExpenditureType.DIVIDENDS,
    )
    data = policy.get_expenditure_data()
    assert data["annual_cost"] == 70.0


@pytest.mark.parametrize(
    ("action", "kwargs", "expected"),
    [
        ("cap", {"cap_amount": 1_000}, pytest.approx(39.0)),
        ("cap", {"cap_rate": 0.28}, pytest.approx(10.5)),
        ("phase_out", {}, pytest.approx(14.0)),
        ("convert", {}, pytest.approx(7.0)),
    ],
)
def test_static_revenue_effect_branches(action, kwargs, expected):
    policy = TaxExpenditurePolicy(
        name=f"Branch {action}",
        description="Branch coverage",
        policy_type=PolicyType.TAX_DEDUCTION,
        expenditure_type=TaxExpenditureType.CHARITABLE,
        action=action,
        **kwargs,
    )
    assert policy.estimate_static_revenue_effect(0) == expected


def test_expand_branch_handles_salt_and_generic_expansion():
    salt_policy = TaxExpenditurePolicy(
        name="SALT Expansion",
        description="Repeal SALT cap",
        policy_type=PolicyType.TAX_DEDUCTION,
        expenditure_type=TaxExpenditureType.SALT,
        action="expand",
    )
    generic_policy = TaxExpenditurePolicy(
        name="Generic Expansion",
        description="Expand charitable benefit",
        policy_type=PolicyType.TAX_DEDUCTION,
        expenditure_type=TaxExpenditureType.CHARITABLE,
        action="expand",
    )

    assert salt_policy.estimate_static_revenue_effect(0) == pytest.approx(-95.0)
    assert generic_policy.estimate_static_revenue_effect(0) == pytest.approx(-14.0)


def test_behavioral_offset_signs_follow_static_effect_direction():
    positive_policy = TaxExpenditurePolicy(
        name="Positive Offset",
        description="Revenue raiser",
        policy_type=PolicyType.TAX_DEDUCTION,
        expenditure_type=TaxExpenditureType.CHARITABLE,
    )
    negative_policy = TaxExpenditurePolicy(
        name="Negative Offset",
        description="Revenue loser",
        policy_type=PolicyType.TAX_DEDUCTION,
        expenditure_type=TaxExpenditureType.CHARITABLE,
    )

    assert positive_policy.estimate_behavioral_offset(10.0) < 0
    assert negative_policy.estimate_behavioral_offset(-10.0) > 0


def test_estimate_expenditure_revenue_returns_consistent_totals():
    policy = create_cap_employer_health_exclusion()
    estimate = estimate_expenditure_revenue(policy)

    assert set(estimate) == {
        "annual_static",
        "ten_year_static",
        "behavioral_offset",
        "net_effect",
    }
    assert estimate["net_effect"] == pytest.approx(
        estimate["ten_year_static"] + estimate["behavioral_offset"]
    )


def test_get_all_expenditure_estimates_contains_major_categories():
    estimates = get_all_expenditure_estimates()
    assert estimates["Employer Health Insurance"] == 250.0
    assert estimates["SALT (no cap)"] == 120.0
    assert "Like-Kind Exchange" in estimates
