"""
Convenience constructors for common policy types.
"""

from typing import Literal

from .policies_core import PolicyType, SpendingPolicy, TaxPolicy
from .spending_outlays import IMMEDIATE


def create_income_tax_cut(
    name: str,
    rate_reduction: float,
    income_threshold: float = 0,
    start_year: int = 2025,
    duration: int = 10,
    affected_millions: float = 0,
) -> TaxPolicy:
    """Create a standard income tax cut policy."""
    return TaxPolicy(
        name=name,
        description=f"Reduce income tax rate by {rate_reduction*100:.1f} percentage points",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=-abs(rate_reduction),
        affected_income_threshold=income_threshold,
        affected_taxpayers_millions=affected_millions,
        start_year=start_year,
        duration_years=duration,
    )


def create_new_tax_credit(
    name: str,
    amount: float,
    refundable: bool,
    affected_millions: float,
    start_year: int = 2025,
    duration: int = 10,
) -> TaxPolicy:
    """Create a new tax credit policy."""
    return TaxPolicy(
        name=name,
        description=f"New {'refundable' if refundable else 'non-refundable'} tax credit of ${amount:,.0f}",
        policy_type=PolicyType.TAX_CREDIT,
        credit_amount=amount,
        credit_refundable=refundable,
        affected_taxpayers_millions=affected_millions,
        start_year=start_year,
        duration_years=duration,
    )


def create_spending_increase(
    name: str,
    annual_billions: float,
    category: Literal["defense", "nondefense", "mandatory"] = "nondefense",
    start_year: int = 2025,
    duration: int = 10,
    multiplier: float = 1.0,
    outlay_account_class: str = IMMEDIATE,
) -> SpendingPolicy:
    """Create a spending increase policy.

    ``outlay_account_class`` says how fast the authority becomes an outlay
    (:mod:`fiscal_model.spending_outlays`). It defaults to the identity so an
    existing caller is unmoved; callers that know the account type - the
    composer's per-goal builds do - pass their classification.
    """
    policy_type = (
        PolicyType.DISCRETIONARY_NONDEFENSE
        if category == "nondefense"
        else PolicyType.DISCRETIONARY_DEFENSE
        if category == "defense"
        else PolicyType.MANDATORY_SPENDING
    )
    return SpendingPolicy(
        name=name,
        description=f"Increase {category} spending by ${annual_billions:.1f}B annually",
        policy_type=policy_type,
        annual_spending_change_billions=annual_billions,
        category=category,
        gdp_multiplier=multiplier,
        outlay_account_class=outlay_account_class,
        start_year=start_year,
        duration_years=duration,
    )
