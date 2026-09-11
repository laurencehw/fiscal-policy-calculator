"""
Tests for tax expenditure models and factory helpers.
"""

from __future__ import annotations

import pytest

from fiscal_model.policies import PolicyType
from fiscal_model.tax_expenditures import (
    JCT_TAX_EXPENDITURES,
    CapUnit,
    SaltCapBaseline,
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
    uncapped_salt_expenditure_billions,
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
        # A $1,000 per-return cap on charitable deductions denies 96.1% of the
        # deduction's value: SOI TY2023 puts the average claimed contribution
        # at about $18,000 per claiming return, so almost the whole deduction
        # sits above $1,000. Before the base distribution existed this returned
        # 39.0, from a share-affected rule that compared the cap with
        # `avg_benefit` -- a *tax benefit* of $2,800, not a deduction.
        ("cap", {"cap_amount": 1_000}, pytest.approx(67.272, rel=1e-4)),
        # A 28% ceiling on the deduction's value denies 15.47% of it: the share
        # of charitable deductions claimed by filers whose statutory marginal
        # rate exceeds 28%. Previously a flat 0.15 with no distribution behind
        # it, which landed near the right answer by coincidence.
        ("cap", {"cap_rate": 0.28}, pytest.approx(10.831, rel=1e-4)),
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
        # The identity below is the one that holds against a **permanent
        # $10,000 cap**, which is what "the limitation's own value" meant
        # before P.L. 119-21 sec. 70120 made the live cap $40,400 through
        # 2029. The dataclass default is current law, where the same repeal is
        # worth about -$49.8B/yr rather than -$64.5B, so the baseline is
        # stated here rather than assumed.
        # See planning/lanes/SALT_current_law_baseline.md.
        salt_baseline=SaltCapBaseline.PERMANENT_10K,
    )
    generic_policy = TaxExpenditurePolicy(
        name="Generic Expansion",
        description="Expand charitable benefit",
        policy_type=PolicyType.TAX_DEDUCTION,
        expenditure_type=TaxExpenditureType.CHARITABLE,
        action="expand",
    )

    # Repealing a limitation is worth the limitation's own value: the
    # difference between the uncapped and capped levels. The uncapped level is
    # derived from SOI rather than carried, so this asserts the identity and
    # not a literal -- the literal it replaced (-95.0) was -(120.0 - 25.0),
    # built from a constant that was the eliminate_salt target restated.
    salt_record = JCT_TAX_EXPENDITURES["salt"]
    assert salt_policy.estimate_static_revenue_effect(0) == pytest.approx(
        -(salt_record["annual_cost_no_cap"] - salt_record["annual_cost"]),
        # The capped leg is now the SOI `salt_limited` column rather than the
        # record's rounded 25.0, and the two agree to 0.1% by construction.
        rel=1e-3,
    )
    assert generic_policy.estimate_static_revenue_effect(0) == pytest.approx(-14.0)


def test_behavioral_offset_signs_follow_the_reform_not_the_module():
    """The direction is a property of the reform, and it has two values here.

    This test used to assert the module-wide magnify convention: it built two
    ``CHARITABLE`` policies at the dataclass defaults and required an
    opposite-signed offset from both. Lane W7 replaced that convention with a
    per-reform table read off the sources, and the two policies below are the
    same class in the same expenditure with **opposite** directions — which is
    the point, and is why one blanket sign could not have been right.

    * A ceiling on the deduction's **value** magnifies: CBO's extended
      discussion of Option 49 (``budget-options/58635``), third alternative —
      taxpayers "spend less than they currently do on deductible items, an
      effect that would increase tax revenues."
    * Eliminating the **mortgage interest** deduction erodes: Poterba & Sinai
      (NBER WP 14253, Table 8) price repeal at $72.4B with no behavioural
      response and $61.9B once households sell taxable assets to pay down
      mortgage debt — "about 85 percent".
    """
    magnifying = TaxExpenditurePolicy(
        name="Cap charitable deduction at 28%",
        description="A benefit-rate ceiling: CBO says the response raises revenue",
        policy_type=PolicyType.TAX_DEDUCTION,
        expenditure_type=TaxExpenditureType.CHARITABLE,
        action="cap",
        cap_rate=0.28,
        cap_unit=CapUnit.BENEFIT_RATE,
    )
    eroding = TaxExpenditurePolicy(
        name="Eliminate mortgage interest deduction",
        description="Portfolio adjustment leaks part of the mechanical gain away",
        policy_type=PolicyType.TAX_DEDUCTION,
        expenditure_type=TaxExpenditureType.MORTGAGE_INTEREST,
        action="eliminate",
    )

    # Magnify: opposite sign to static, so the engine's
    # ``deficit = -revenue + behavioural`` adds to the static effect.
    assert magnifying.estimate_behavioral_offset(10.0) < 0
    assert magnifying.estimate_behavioral_offset(-10.0) > 0

    # Erode: same sign as static, the contract every other policy class keeps.
    assert eroding.estimate_behavioral_offset(10.0) > 0
    assert eroding.estimate_behavioral_offset(-10.0) < 0


def test_estimate_expenditure_revenue_returns_consistent_totals():
    """The helper is revenue-signed, so the offset comes off with a minus.

    The engine works in deficit space — ``deficit = -revenue + behavioural`` —
    and this dict does not, so adding the offset to the static effect here is
    the *opposite* of what the engine does with the same number. The assertion
    used to be ``+``, which agreed with the engine for neither the module's old
    magnify convention nor its new per-reform one. Both directions are checked
    below, because a tautology on one policy would pass either way.
    """
    magnifying = create_cap_employer_health_exclusion()
    estimate = estimate_expenditure_revenue(magnifying)

    assert set(estimate) == {
        "annual_static",
        "ten_year_static",
        "behavioral_offset",
        "net_effect",
    }
    assert estimate["net_effect"] == pytest.approx(
        estimate["ten_year_static"] - estimate["behavioral_offset"]
    )
    # A cap on the exclusion raises revenue, and CBO's two behavioural channels
    # raise more of it, so the net exceeds the static effect.
    assert estimate["net_effect"] > estimate["ten_year_static"] > 0

    eroding = estimate_expenditure_revenue(create_eliminate_mortgage_deduction())
    assert eroding["net_effect"] == pytest.approx(
        eroding["ten_year_static"] - eroding["behavioral_offset"]
    )
    # Repeal raises revenue, and portfolio adjustment leaks part of it away.
    assert 0 < eroding["net_effect"] < eroding["ten_year_static"]


def test_get_all_expenditure_estimates_contains_major_categories():
    estimates = get_all_expenditure_estimates()
    assert estimates["Employer Health Insurance"] == 250.0
    assert estimates["SALT (no cap)"] == pytest.approx(
        uncapped_salt_expenditure_billions()
    )
    assert "Like-Kind Exchange" in estimates
