"""
Factory functions for tax expenditure reform policies.

Every factory carries a fitted ``annual_revenue_change_billions`` and defaults
to :data:`~fiscal_model.tax_expenditures_core.EXPENDITURE_APP_MODE`, which is
``reported`` -- so the shipped presets score the fitted constant. Passing
``mode="derived"`` ignores it and runs the module's own reform rules against
``JCT_TAX_EXPENDITURES`` and the base distributions instead; that is what
``validation/loo.py`` does, and it is the number that measures the machinery.
"""

from .policies import PolicyType
from .tax_expenditures_core import (
    EXPENDITURE_APP_MODE,
    CapUnit,
    TaxExpenditurePolicy,
    TaxExpenditureType,
)


def create_cap_employer_health_exclusion(
    cap_amount: float = 50_000,
    start_year: int = 2026,
    duration_years: int = 10,
    mode: str = EXPENDITURE_APP_MODE,
    caps_by_coverage_tier: dict[str, float] | None = None,
) -> TaxExpenditurePolicy:
    """
    Create policy to cap employer health insurance exclusion.

    ``cap_amount`` is a cap on excludable **premiums**, not on the tax benefit,
    which is why ``cap_unit`` is stated. Published designs of this option cap
    at a percentile of premiums rather than a round dollar figure -- CBO's
    Option 56 sets the 50th percentile at $10,000 individual / $24,400 family
    in 2028 -- and ``caps_by_coverage_tier`` is how such a design is written.
    """
    return TaxExpenditurePolicy(
        name=f"Cap Employer Health Exclusion at ${cap_amount/1000:.0f}K",
        description=f"Cap tax exclusion for employer health insurance at ${cap_amount:,.0f}",
        policy_type=PolicyType.TAX_DEDUCTION,
        expenditure_type=TaxExpenditureType.EMPLOYER_HEALTH,
        action="cap",
        cap_amount=cap_amount,
        cap_unit=CapUnit.BASE_DOLLARS,
        caps_by_coverage_tier=caps_by_coverage_tier,
        behavioral_elasticity=0.0,
        annual_revenue_change_billions=31.2,
        start_year=start_year,
        duration_years=duration_years,
        mode=mode,
    )


def create_eliminate_mortgage_deduction(
    start_year: int = 2026,
    duration_years: int = 10,
    mode: str = EXPENDITURE_APP_MODE,
) -> TaxExpenditurePolicy:
    """Create policy to eliminate the mortgage interest deduction."""
    return TaxExpenditurePolicy(
        name="Eliminate Mortgage Interest Deduction",
        description="Repeal the mortgage interest deduction for home purchases",
        policy_type=PolicyType.TAX_DEDUCTION,
        expenditure_type=TaxExpenditureType.MORTGAGE_INTEREST,
        action="eliminate",
        behavioral_elasticity=0.0,
        annual_revenue_change_billions=26.2,
        start_year=start_year,
        duration_years=duration_years,
        mode=mode,
    )


def create_repeal_salt_cap(
    start_year: int = 2026,
    duration_years: int = 10,
    mode: str = EXPENDITURE_APP_MODE,
) -> TaxExpenditurePolicy:
    """Create policy to repeal the SALT deduction cap."""
    return TaxExpenditurePolicy(
        name="Repeal SALT Cap",
        description="Remove $10,000 cap on state and local tax deduction",
        policy_type=PolicyType.TAX_DEDUCTION,
        expenditure_type=TaxExpenditureType.SALT,
        action="expand",
        behavioral_elasticity=0.0,
        annual_revenue_change_billions=-96.0,
        start_year=start_year,
        duration_years=duration_years,
        mode=mode,
    )


def create_eliminate_salt_deduction(
    start_year: int = 2026,
    duration_years: int = 10,
    mode: str = EXPENDITURE_APP_MODE,
) -> TaxExpenditurePolicy:
    """
    Create policy to eliminate the SALT deduction entirely.

    Scored over a window beginning in ``start_year``. The $10,000 cap expires
    after 2025 (IRC 164(b)(6)), so a 2026 window prices the *unlimited*
    deduction -- which is the baseline CBO's own Option 49 alternative uses.
    """
    return TaxExpenditurePolicy(
        name="Eliminate SALT Deduction",
        description="Completely eliminate state and local tax deduction",
        policy_type=PolicyType.TAX_DEDUCTION,
        expenditure_type=TaxExpenditureType.SALT,
        action="eliminate",
        behavioral_elasticity=0.0,
        annual_revenue_change_billions=104.7,
        start_year=start_year,
        duration_years=duration_years,
        mode=mode,
    )


def create_cap_charitable_deduction(
    cap_rate: float = 0.28,
    start_year: int = 2026,
    duration_years: int = 10,
    mode: str = EXPENDITURE_APP_MODE,
) -> TaxExpenditurePolicy:
    """
    Create policy to cap charitable deduction value at a fixed rate.

    A Pease-style rate ceiling: the deduction still reduces taxable income but
    its value is limited to ``cap_rate``, so filers above that rate lose the
    difference. Scored against the charitable-deduction distribution by AGI
    class rather than a flat share.
    """
    return TaxExpenditurePolicy(
        name=f"Cap Charitable Deduction at {cap_rate*100:.0f}%",
        description=f"Limit charitable deduction value to {cap_rate*100:.0f}% rate",
        policy_type=PolicyType.TAX_DEDUCTION,
        expenditure_type=TaxExpenditureType.CHARITABLE,
        action="cap",
        cap_rate=cap_rate,
        cap_unit=CapUnit.BENEFIT_RATE,
        behavioral_elasticity=0.0,
        annual_revenue_change_billions=12.5,
        start_year=start_year,
        duration_years=duration_years,
        mode=mode,
    )


def create_eliminate_step_up_basis(
    exemption: float = 1_000_000,
    start_year: int = 2026,
    duration_years: int = 10,
    mode: str = EXPENDITURE_APP_MODE,
) -> TaxExpenditurePolicy:
    """Create policy to eliminate step-up in basis at death."""
    return TaxExpenditurePolicy(
        name="Eliminate Step-Up Basis",
        description=f"Tax capital gains at death (${exemption/1e6:.0f}M exemption)",
        policy_type=PolicyType.TAX_DEDUCTION,
        expenditure_type=TaxExpenditureType.STEP_UP_BASIS,
        action="eliminate",
        cap_amount=exemption,
        behavioral_elasticity=0.0,
        annual_revenue_change_billions=43.6,
        start_year=start_year,
        duration_years=duration_years,
        mode=mode,
    )


def create_eliminate_like_kind_exchange(
    start_year: int = 2026,
    duration_years: int = 10,
    mode: str = EXPENDITURE_APP_MODE,
) -> TaxExpenditurePolicy:
    """Create policy to eliminate like-kind exchanges."""
    return TaxExpenditurePolicy(
        name="Eliminate Like-Kind Exchanges",
        description="Repeal Section 1031 like-kind exchange deferral",
        policy_type=PolicyType.TAX_DEDUCTION,
        expenditure_type=TaxExpenditureType.LIKE_KIND_EXCHANGE,
        action="eliminate",
        behavioral_elasticity=0.0,
        annual_revenue_change_billions=7.0,
        start_year=start_year,
        duration_years=duration_years,
        mode=mode,
    )


def create_cap_retirement_contributions(
    cap_amount: float = 20_000,
    start_year: int = 2026,
    duration_years: int = 10,
    mode: str = EXPENDITURE_APP_MODE,
) -> TaxExpenditurePolicy:
    """
    Create policy to cap tax-advantaged retirement contributions.

    ``cap_amount`` is a cap on annual **contributions**. No contribution
    distribution is transcribed for retirement plans, so ``mode="derived"``
    raises ``ExpenditureDistributionMissing`` rather than approximating the
    share affected -- that approximation is the bug this lane removed.
    """
    return TaxExpenditurePolicy(
        name=f"Cap Retirement Contributions at ${cap_amount/1000:.0f}K",
        description=f"Limit tax-advantaged retirement contributions to ${cap_amount:,.0f}/year",
        policy_type=PolicyType.TAX_DEDUCTION,
        expenditure_type=TaxExpenditureType.RETIREMENT_CONTRIBUTIONS,
        action="cap",
        cap_amount=cap_amount,
        cap_unit=CapUnit.BASE_DOLLARS,
        behavioral_elasticity=0.0,
        annual_revenue_change_billions=13.1,
        start_year=start_year,
        duration_years=duration_years,
        mode=mode,
    )
