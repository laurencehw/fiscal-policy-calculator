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
    SaltCapBaseline,
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


#: The baseline each SALT factory's fitted annual was fitted **on**.
#:
#: A fitted constant is an answer to a question, and a SALT question is not
#: complete without a baseline: -96.0/yr is the cost of repealing a *permanent*
#: $10,000 cap (PWBM's extended-TCJA baseline) and 104.7/yr is the value of an
#: *uncapped* deduction (CBO Option 49's lapsed-cap baseline). Neither is the
#: current-law answer to its own reform, because under P.L. 119-21 sec. 70120
#: the live cap is $40,404 in 2026 and $10,000 only from 2030.
#:
#: So a factory hands its constant over only when the caller asks for the
#: baseline it was fitted on. On any other baseline it passes ``None`` and the
#: existing ``reported`` branch falls through to the structural cap path -- no
#: new mode, no second constant, and nothing retuned.
SALT_FITTED_BASELINES: dict[str, SaltCapBaseline] = {
    "repeal_salt_cap": SaltCapBaseline.PERMANENT_10K,
    "eliminate_salt": SaltCapBaseline.LAPSED_CAP,
}


def _fitted_annual_on(
    reform: str, salt_baseline: SaltCapBaseline, annual: float
) -> float | None:
    """``annual`` if this is the baseline it was fitted on, else ``None``."""
    return annual if SALT_FITTED_BASELINES[reform] is salt_baseline else None


def create_repeal_salt_cap(
    start_year: int = 2026,
    duration_years: int = 10,
    mode: str = EXPENDITURE_APP_MODE,
    salt_baseline: SaltCapBaseline = SaltCapBaseline.CURRENT_LAW,
) -> TaxExpenditurePolicy:
    """
    Create policy to repeal the SALT deduction cap.

    Priced against ``salt_baseline``, which defaults to **current law**: under
    P.L. 119-21 sec. 70120 the cap is $40,400 in 2026 rising 1%/yr through
    2029 and $10,000 only from 2030, so repeal is worth far less than it is
    against the permanent $10,000 cap PWBM's Table 3 scores it on. The fitted
    -96.0/yr is that permanent-cap answer and travels only with that baseline.
    """
    return TaxExpenditurePolicy(
        name="Repeal SALT Cap",
        description="Remove the cap on the state and local tax deduction",
        policy_type=PolicyType.TAX_DEDUCTION,
        expenditure_type=TaxExpenditureType.SALT,
        action="expand",
        behavioral_elasticity=0.0,
        annual_revenue_change_billions=_fitted_annual_on(
            "repeal_salt_cap", salt_baseline, -96.0
        ),
        salt_baseline=salt_baseline,
        start_year=start_year,
        duration_years=duration_years,
        mode=mode,
    )


def create_eliminate_salt_deduction(
    start_year: int = 2026,
    duration_years: int = 10,
    mode: str = EXPENDITURE_APP_MODE,
    salt_baseline: SaltCapBaseline = SaltCapBaseline.CURRENT_LAW,
) -> TaxExpenditurePolicy:
    """
    Create policy to eliminate the SALT deduction entirely.

    Repeal is worth the deduction that is actually claimed under
    ``salt_baseline``, which defaults to **current law**. On CBO Option 49's
    own baseline the $10,000 cap lapsed after 2025 and a 2026 window prices the
    *unlimited* deduction; under P.L. 119-21 sec. 70120 it prices a deduction
    capped at $40,400 rising 1%/yr to 2029 and $10,000 thereafter, which is
    about a third as much. The fitted 104.7/yr is the uncapped answer and
    travels only with ``LAPSED_CAP``.
    """
    return TaxExpenditurePolicy(
        name="Eliminate SALT Deduction",
        description="Completely eliminate state and local tax deduction",
        policy_type=PolicyType.TAX_DEDUCTION,
        expenditure_type=TaxExpenditureType.SALT,
        action="eliminate",
        behavioral_elasticity=0.0,
        annual_revenue_change_billions=_fitted_annual_on(
            "eliminate_salt", salt_baseline, 104.7
        ),
        salt_baseline=salt_baseline,
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
