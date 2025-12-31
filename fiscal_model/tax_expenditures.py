"""
Tax Expenditure Scoring Module

Models changes to major tax expenditures (deductions, exclusions, credits).
Tax expenditures are provisions that reduce tax liability through the tax code
rather than through direct spending.

Key tax expenditures (JCT 2024 estimates):
1. Defined-contribution plans (401k): ~$251B/year
2. Capital gains preferential rates: ~$225B/year (see capital_gains.py)
3. Employer health insurance exclusion: ~$190-250B/year
4. Defined-benefit pension plans: ~$122B/year
5. Child Tax Credit: ~$120B/year (see credits.py)
6. ACA Premium Tax Credits: ~$80B/year (see ptc.py)
7. EITC: ~$73B/year (see credits.py)
8. Charitable contribution deduction: ~$55-80B/year
9. SALT deduction: ~$25B (with cap), ~$120B (without cap)
10. Mortgage interest deduction: ~$25B (with TCJA), ~$100B (without)

Data sources:
- JCT: Estimates of Federal Tax Expenditures (JCX-48-24)
- Treasury: Tax Expenditures report
- CBO: Budget Options
"""

from dataclasses import dataclass, field
from typing import Optional, Literal, List
from enum import Enum
import numpy as np

from .policies import Policy, TaxPolicy, PolicyType


class TaxExpenditureType(Enum):
    """Categories of tax expenditures."""
    # Exclusions (income never taxed)
    EMPLOYER_HEALTH = "employer_health"  # Employer-paid health insurance
    RETIREMENT_CONTRIBUTIONS = "retirement_contrib"  # 401k, IRA contributions
    RETIREMENT_EARNINGS = "retirement_earnings"  # Tax-free growth in accounts

    # Deductions (reduce taxable income)
    MORTGAGE_INTEREST = "mortgage_interest"
    SALT = "salt"  # State and local taxes
    CHARITABLE = "charitable"
    MEDICAL_EXPENSES = "medical"

    # Preferential rates
    CAPITAL_GAINS = "capital_gains"  # Lower rates (see capital_gains.py)
    DIVIDENDS = "dividends"  # Qualified dividends

    # Credits (direct reduction in tax)
    CHILD_TAX_CREDIT = "ctc"  # See credits.py
    EITC = "eitc"  # See credits.py

    # Other
    STEP_UP_BASIS = "step_up"  # Basis reset at death
    LIKE_KIND_EXCHANGE = "like_kind"  # 1031 exchanges
    PASS_THROUGH_DEDUCTION = "pass_through"  # Section 199A (see tcja.py)


# =============================================================================
# CURRENT LAW PARAMETERS (2024-2025)
# =============================================================================

# JCT tax expenditure estimates (billions per year, 2024)
JCT_TAX_EXPENDITURES = {
    # Exclusions
    "employer_health": {
        "annual_cost": 250.0,  # ~$250B/year (JCT/Treasury range $190-250B)
        "affected_millions": 155.0,  # ~155M covered by employer plans
        "avg_benefit": 1_600,  # Average tax benefit per covered person
        "growth_rate": 0.04,  # Healthcare cost growth
    },
    "retirement_401k": {
        "annual_cost": 251.0,  # Defined contribution plans
        "affected_millions": 70.0,  # ~70M participants
        "avg_benefit": 3_600,
        "growth_rate": 0.03,
    },
    "retirement_db": {
        "annual_cost": 122.0,  # Defined benefit plans
        "affected_millions": 35.0,
        "avg_benefit": 3_500,
        "growth_rate": 0.02,  # Declining
    },
    "retirement_ira": {
        "annual_cost": 27.0,  # Traditional + Roth IRAs
        "affected_millions": 50.0,
        "avg_benefit": 540,
        "growth_rate": 0.03,
    },

    # Deductions (with TCJA limits in effect)
    "mortgage_interest": {
        "annual_cost": 25.0,  # With $750K cap
        "annual_cost_no_limit": 100.0,  # Without cap (post-2025 if TCJA expires)
        "affected_millions": 20.0,  # Down from 33M pre-TCJA
        "avg_benefit": 1_250,
        "growth_rate": 0.03,
    },
    "salt": {
        "annual_cost": 25.0,  # With $10K cap
        "annual_cost_no_cap": 120.0,  # Without cap
        "affected_millions": 15.0,  # Down from 45M pre-TCJA
        "avg_benefit": 1_700,
        "growth_rate": 0.03,
    },
    "charitable": {
        "annual_cost": 70.0,  # JCT ~$55B, Treasury ~$82B, use midpoint
        "affected_millions": 25.0,  # Itemizers who deduct
        "avg_benefit": 2_800,
        "growth_rate": 0.03,
    },

    # Preferential rates (for reference - detailed in capital_gains.py)
    "capital_gains_dividends": {
        "annual_cost": 225.0,  # JCT estimate
        "affected_millions": 25.0,
        "avg_benefit": 9_000,
        "growth_rate": 0.04,
    },

    # Other
    "step_up_basis": {
        "annual_cost": 50.0,  # Estimates range $40-60B
        "affected_millions": 2.5,  # Estates with appreciated assets
        "avg_benefit": 20_000,
        "growth_rate": 0.04,
    },
    "like_kind_exchange": {
        "annual_cost": 7.0,  # Real estate 1031 exchanges
        "affected_millions": 0.5,
        "avg_benefit": 14_000,
        "growth_rate": 0.03,
    },
}

# Policy reform estimates (CBO Budget Options, Treasury, JCT)
REFORM_ESTIMATES = {
    # Employer health insurance
    "cap_employer_exclusion_50k": {
        "revenue_10yr": 450.0,  # Cap exclusion at $50K/family
        "source": "CBO",
        "notes": "Cap on excludable employer health contributions",
    },
    "eliminate_employer_exclusion": {
        "revenue_10yr": 2500.0,  # Full repeal
        "source": "CBO estimate",
        "notes": "Would be largest base broadener but disruptive",
    },

    # Retirement
    "cap_retirement_contrib_20k": {
        "revenue_10yr": 150.0,  # Cap all contributions at $20K/year
        "source": "CBO",
        "notes": "Equalizes treatment across plan types",
    },
    "require_roth_high_income": {
        "revenue_10yr": 100.0,  # Require Roth for >$400K income
        "source": "Biden proposal",
        "notes": "Shifts timing of revenue",
    },

    # Mortgage interest
    "eliminate_mortgage_deduction": {
        "revenue_10yr": 300.0,  # Full elimination (from current)
        "source": "CBO",
        "notes": "Controversial - affects homeownership",
    },
    "cap_mortgage_500k": {
        "revenue_10yr": 30.0,  # Lower cap from $750K to $500K
        "source": "CBO estimate",
        "notes": "Moderate reform",
    },

    # SALT
    "repeal_salt_cap": {
        "revenue_10yr": -1100.0,  # Cost of removing $10K cap
        "source": "JCT",
        "notes": "Popular bipartisan proposal - costs money",
    },
    "eliminate_salt": {
        "revenue_10yr": 1200.0,  # Full SALT elimination
        "source": "JCT estimate",
        "notes": "Very controversial - affects high-tax states",
    },

    # Charitable
    "cap_charitable_deduction": {
        "revenue_10yr": 200.0,  # Cap at 28% rate value
        "source": "Obama proposal",
        "notes": "Pease-style limit on high-income itemizers",
    },
    "eliminate_charitable_deduction": {
        "revenue_10yr": 700.0,
        "source": "Estimate",
        "notes": "Would significantly affect nonprofit sector",
    },

    # Step-up basis
    "eliminate_step_up": {
        "revenue_10yr": 500.0,  # With exemption
        "source": "Biden proposal",
        "notes": "Tax gains at death (with $1M+ exemption)",
    },

    # Like-kind exchange
    "eliminate_like_kind": {
        "revenue_10yr": 80.0,
        "source": "Biden proposal",
        "notes": "End 1031 exchange deferral",
    },
}


@dataclass
class TaxExpenditurePolicy(TaxPolicy):
    """
    Tax expenditure policy modeling changes to deductions, exclusions, and credits.

    Models reform options including:
    - Elimination (full repeal)
    - Caps (dollar or rate limits)
    - Income phase-outs
    - Conversion to credits

    Key parameters:
        expenditure_type: Category of tax expenditure
        action: Type of reform (eliminate, cap, phase_out, convert)
        cap_amount: Dollar cap (if action is 'cap')
        phase_out_start: Income where phase-out begins
        convert_to_credit: Convert deduction to credit (if applicable)
    """

    # Expenditure identification
    expenditure_type: TaxExpenditureType = field(default=TaxExpenditureType.CHARITABLE)

    # Reform action
    action: Literal["eliminate", "cap", "phase_out", "convert", "expand"] = "cap"

    # Cap parameters
    cap_amount: Optional[float] = None  # Dollar cap on deduction/exclusion
    cap_rate: Optional[float] = None  # Rate cap (e.g., 28% for itemized)

    # Phase-out parameters
    phase_out_start: Optional[float] = None  # Income where phase-out begins
    phase_out_end: Optional[float] = None  # Income where fully phased out
    phase_out_rate: float = 0.03  # 3% reduction per $1,000 (Pease-style)

    # Conversion parameters
    convert_to_credit: bool = False  # Convert deduction to credit
    credit_rate: float = 0.15  # Credit rate if converting

    # Expansion parameters (for policies like SALT cap repeal)
    expand_limit: Optional[float] = None  # New higher limit

    # Behavioral parameters
    behavioral_elasticity: float = 0.2  # Response to incentive changes
    participation_change: float = 0.0  # Change in take-up rate

    # Calibration
    annual_revenue_change_billions: Optional[float] = None

    def __post_init__(self):
        """Set policy type."""
        if self.policy_type == PolicyType.INCOME_TAX:
            self.policy_type = PolicyType.TAX_DEDUCTION

    def get_expenditure_data(self) -> dict:
        """Get baseline data for this expenditure type."""
        type_map = {
            TaxExpenditureType.EMPLOYER_HEALTH: "employer_health",
            TaxExpenditureType.RETIREMENT_CONTRIBUTIONS: "retirement_401k",
            TaxExpenditureType.MORTGAGE_INTEREST: "mortgage_interest",
            TaxExpenditureType.SALT: "salt",
            TaxExpenditureType.CHARITABLE: "charitable",
            TaxExpenditureType.CAPITAL_GAINS: "capital_gains_dividends",
            TaxExpenditureType.STEP_UP_BASIS: "step_up_basis",
            TaxExpenditureType.LIKE_KIND_EXCHANGE: "like_kind_exchange",
        }
        key = type_map.get(self.expenditure_type, "charitable")
        return JCT_TAX_EXPENDITURES.get(key, {})

    def estimate_static_revenue_effect(
        self,
        baseline_revenue: float,
        use_real_data: bool = True,
    ) -> float:
        """
        Estimate static revenue effect of tax expenditure reform.

        For tax expenditures:
        - Elimination = full revenue gain
        - Caps = partial revenue gain
        - Expansion = revenue loss

        Returns:
            Revenue change in billions (negative = revenue loss)
        """
        if self.annual_revenue_change_billions is not None:
            return self.annual_revenue_change_billions

        data = self.get_expenditure_data()
        baseline_cost = data.get("annual_cost", 50.0)

        if self.action == "eliminate":
            # Full elimination = recapture all expenditure
            return baseline_cost

        elif self.action == "cap":
            if self.cap_amount is not None:
                # Estimate share affected by cap
                avg_benefit = data.get("avg_benefit", 2000)
                if self.cap_amount >= avg_benefit:
                    # Cap above average = small effect
                    share_affected = 0.1 * (avg_benefit / self.cap_amount)
                else:
                    # Cap below average = larger effect
                    share_affected = 0.3 + 0.4 * (1 - self.cap_amount / avg_benefit)
                return baseline_cost * share_affected

            if self.cap_rate is not None:
                # Rate cap (e.g., 28% limit on deductions)
                # Affects high-bracket taxpayers
                return baseline_cost * 0.15  # Rough estimate

        elif self.action == "phase_out":
            # Income-based phase-out
            # Affects high earners
            return baseline_cost * 0.20

        elif self.action == "convert":
            # Converting deduction to credit
            # Generally more progressive, modest revenue effect
            return baseline_cost * 0.10

        elif self.action == "expand":
            # Expansion (like SALT cap repeal)
            if self.expenditure_type == TaxExpenditureType.SALT:
                no_cap_cost = data.get("annual_cost_no_cap", 120.0)
                current_cost = data.get("annual_cost", 25.0)
                return -(no_cap_cost - current_cost)  # Revenue loss

            return -baseline_cost * 0.20  # General expansion

        return 0.0

    def estimate_behavioral_offset(self, static_effect: float) -> float:
        """
        Estimate behavioral response to tax expenditure changes.

        Responses include:
        - Reduced activity (less charitable giving if deduction limited)
        - Timing shifts
        - Restructuring (e.g., retirement account choices)

        Returns:
            Behavioral offset in billions
        """
        # Different elasticities by expenditure type
        type_elasticities = {
            TaxExpenditureType.CHARITABLE: 0.4,  # Giving responds to incentives
            TaxExpenditureType.MORTGAGE_INTEREST: 0.1,  # Housing less elastic
            TaxExpenditureType.RETIREMENT_CONTRIBUTIONS: 0.3,
            TaxExpenditureType.EMPLOYER_HEALTH: 0.2,
            TaxExpenditureType.SALT: 0.05,  # Can't easily change state taxes
        }

        elasticity = type_elasticities.get(
            self.expenditure_type,
            self.behavioral_elasticity
        )

        # Behavioral offset reduces revenue gain or loss
        offset = abs(static_effect) * elasticity

        if static_effect > 0:
            return -offset  # Reduces revenue gain
        else:
            return offset  # Reduces revenue loss


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_cap_employer_health_exclusion(
    cap_amount: float = 50_000,
    start_year: int = 2026,
    duration_years: int = 10,
) -> TaxExpenditurePolicy:
    """
    Create policy to cap employer health insurance exclusion.

    The exclusion of employer-paid health insurance from income is the
    third-largest tax expenditure (~$250B/year). Capping it would raise
    significant revenue while maintaining incentive for coverage.

    Args:
        cap_amount: Maximum excludable amount (e.g., $50,000 for family)
        start_year: First year
        duration_years: Duration

    CBO estimate: Capping at ~$50K raises ~$45B/year (~$450B/10yr)
    """
    return TaxExpenditurePolicy(
        name=f"Cap Employer Health Exclusion at ${cap_amount/1000:.0f}K",
        description=f"Cap tax exclusion for employer health insurance at ${cap_amount:,.0f}",
        policy_type=PolicyType.TAX_DEDUCTION,
        expenditure_type=TaxExpenditureType.EMPLOYER_HEALTH,
        action="cap",
        cap_amount=cap_amount,
        behavioral_elasticity=0.0,  # In calibration
        # Calibrated to CBO ~$450B over 10 years (with 4% healthcare growth)
        annual_revenue_change_billions=31.2,
        start_year=start_year,
        duration_years=duration_years,
    )


def create_eliminate_mortgage_deduction(
    start_year: int = 2026,
    duration_years: int = 10,
) -> TaxExpenditurePolicy:
    """
    Create policy to eliminate mortgage interest deduction.

    The mortgage interest deduction costs ~$25B/year under TCJA limits,
    ~$100B/year without limits. Full elimination would raise significant
    revenue but is politically difficult.

    CBO estimate: Full elimination raises ~$30B/year (~$300B/10yr)
    """
    return TaxExpenditurePolicy(
        name="Eliminate Mortgage Interest Deduction",
        description="Repeal the mortgage interest deduction for home purchases",
        policy_type=PolicyType.TAX_DEDUCTION,
        expenditure_type=TaxExpenditureType.MORTGAGE_INTEREST,
        action="eliminate",
        behavioral_elasticity=0.0,
        # Calibrated to CBO ~$300B over 10 years
        annual_revenue_change_billions=26.2,
        start_year=start_year,
        duration_years=duration_years,
    )


def create_repeal_salt_cap(
    start_year: int = 2026,
    duration_years: int = 10,
) -> TaxExpenditurePolicy:
    """
    Create policy to repeal SALT deduction cap.

    The TCJA $10K SALT cap expires after 2025. This policy explicitly
    repeals the cap, restoring unlimited SALT deductions.

    JCT estimate: Costs ~$110B/year (~$1.1T over 10 years)
    """
    return TaxExpenditurePolicy(
        name="Repeal SALT Cap",
        description="Remove $10,000 cap on state and local tax deduction",
        policy_type=PolicyType.TAX_DEDUCTION,
        expenditure_type=TaxExpenditureType.SALT,
        action="expand",
        behavioral_elasticity=0.0,
        # Calibrated to JCT ~$1.1T over 10 years
        annual_revenue_change_billions=-96.0,
        start_year=start_year,
        duration_years=duration_years,
    )


def create_eliminate_salt_deduction(
    start_year: int = 2026,
    duration_years: int = 10,
) -> TaxExpenditurePolicy:
    """
    Create policy to eliminate SALT deduction entirely.

    Full elimination of SALT (state and local tax) deduction would raise
    ~$120B/year but is very controversial in high-tax states.

    JCT estimate: ~$1.2T over 10 years
    """
    return TaxExpenditurePolicy(
        name="Eliminate SALT Deduction",
        description="Completely eliminate state and local tax deduction",
        policy_type=PolicyType.TAX_DEDUCTION,
        expenditure_type=TaxExpenditureType.SALT,
        action="eliminate",
        behavioral_elasticity=0.0,
        # Calibrated to JCT ~$1.2T over 10 years
        annual_revenue_change_billions=104.7,
        start_year=start_year,
        duration_years=duration_years,
    )


def create_cap_charitable_deduction(
    cap_rate: float = 0.28,
    start_year: int = 2026,
    duration_years: int = 10,
) -> TaxExpenditurePolicy:
    """
    Create policy to cap charitable deduction value at 28% rate.

    Limits the tax benefit of charitable deductions for high-bracket
    taxpayers to 28% regardless of their marginal rate.

    Obama/Biden proposal estimate: ~$200B over 10 years
    """
    return TaxExpenditurePolicy(
        name=f"Cap Charitable Deduction at {cap_rate*100:.0f}%",
        description=f"Limit charitable deduction value to {cap_rate*100:.0f}% rate",
        policy_type=PolicyType.TAX_DEDUCTION,
        expenditure_type=TaxExpenditureType.CHARITABLE,
        action="cap",
        cap_rate=cap_rate,
        behavioral_elasticity=0.0,
        # Calibrated to ~$200B over 10 years (with 3% growth)
        annual_revenue_change_billions=12.5,
        start_year=start_year,
        duration_years=duration_years,
    )


def create_eliminate_step_up_basis(
    exemption: float = 1_000_000,
    start_year: int = 2026,
    duration_years: int = 10,
) -> TaxExpenditurePolicy:
    """
    Create policy to eliminate step-up in basis at death.

    Currently, capital gains are forgiven when assets pass to heirs
    (basis "steps up" to fair market value). Eliminating this would
    require heirs to pay tax on unrealized gains.

    Biden proposal: Eliminate with $1M exemption, raises ~$500B/10yr
    """
    return TaxExpenditurePolicy(
        name="Eliminate Step-Up Basis",
        description=f"Tax capital gains at death (${exemption/1e6:.0f}M exemption)",
        policy_type=PolicyType.TAX_DEDUCTION,
        expenditure_type=TaxExpenditureType.STEP_UP_BASIS,
        action="eliminate",
        cap_amount=exemption,  # Using cap_amount for exemption
        behavioral_elasticity=0.0,
        # Calibrated to Biden ~$500B over 10 years
        annual_revenue_change_billions=43.6,
        start_year=start_year,
        duration_years=duration_years,
    )


def create_eliminate_like_kind_exchange(
    start_year: int = 2026,
    duration_years: int = 10,
) -> TaxExpenditurePolicy:
    """
    Create policy to eliminate like-kind (1031) exchanges.

    Section 1031 allows deferral of gains on real estate exchanges.
    Biden proposal would eliminate this deferral.

    Biden proposal estimate: ~$80B over 10 years
    """
    return TaxExpenditurePolicy(
        name="Eliminate Like-Kind Exchanges",
        description="Repeal Section 1031 like-kind exchange deferral",
        policy_type=PolicyType.TAX_DEDUCTION,
        expenditure_type=TaxExpenditureType.LIKE_KIND_EXCHANGE,
        action="eliminate",
        behavioral_elasticity=0.0,
        # Calibrated to ~$80B over 10 years
        annual_revenue_change_billions=7.0,
        start_year=start_year,
        duration_years=duration_years,
    )


def create_cap_retirement_contributions(
    cap_amount: float = 20_000,
    start_year: int = 2026,
    duration_years: int = 10,
) -> TaxExpenditurePolicy:
    """
    Create policy to cap tax-advantaged retirement contributions.

    Would equalize treatment across 401k, IRA, and DB plans by
    limiting total annual tax-advantaged contributions.

    CBO estimate: Cap at $20K raises ~$150B over 10 years
    """
    return TaxExpenditurePolicy(
        name=f"Cap Retirement Contributions at ${cap_amount/1000:.0f}K",
        description=f"Limit tax-advantaged retirement contributions to ${cap_amount:,.0f}/year",
        policy_type=PolicyType.TAX_DEDUCTION,
        expenditure_type=TaxExpenditureType.RETIREMENT_CONTRIBUTIONS,
        action="cap",
        cap_amount=cap_amount,
        behavioral_elasticity=0.0,
        # Calibrated to CBO ~$150B over 10 years
        annual_revenue_change_billions=13.1,
        start_year=start_year,
        duration_years=duration_years,
    )


# =============================================================================
# VALIDATION SCENARIOS
# =============================================================================

TAX_EXPENDITURE_VALIDATION_SCENARIOS = {
    "cap_employer_health": {
        "description": "Cap employer health exclusion at $50K",
        "policy_factory": "create_cap_employer_health_exclusion",
        "expected_10yr": -450.0,  # Revenue GAIN (negative cost)
        "source": "CBO",
        "notes": "Third-largest tax expenditure",
    },
    "eliminate_mortgage": {
        "description": "Eliminate mortgage interest deduction",
        "policy_factory": "create_eliminate_mortgage_deduction",
        "expected_10yr": -300.0,  # Revenue gain
        "source": "CBO",
        "notes": "Controversial housing policy",
    },
    "repeal_salt_cap": {
        "description": "Repeal SALT $10K cap",
        "policy_factory": "create_repeal_salt_cap",
        "expected_10yr": 1100.0,  # COST (revenue loss)
        "source": "JCT",
        "notes": "Bipartisan proposal, benefits high-tax states",
    },
    "eliminate_salt": {
        "description": "Eliminate SALT deduction entirely",
        "policy_factory": "create_eliminate_salt_deduction",
        "expected_10yr": -1200.0,  # Revenue gain
        "source": "JCT estimate",
        "notes": "Very controversial",
    },
    "cap_charitable": {
        "description": "Cap charitable deduction at 28%",
        "policy_factory": "create_cap_charitable_deduction",
        "expected_10yr": -200.0,  # Revenue gain
        "source": "Obama/Biden proposal",
        "notes": "Pease-style limitation",
    },
    "eliminate_step_up": {
        "description": "Eliminate step-up in basis",
        "policy_factory": "create_eliminate_step_up_basis",
        "expected_10yr": -500.0,  # Revenue gain
        "source": "Biden proposal",
        "notes": "Tax gains at death with $1M exemption",
    },
}


def estimate_expenditure_revenue(policy: TaxExpenditurePolicy) -> dict:
    """
    Estimate total revenue effect of tax expenditure policy.

    Returns dict with:
        - annual_static: Average annual static effect
        - ten_year_static: Total 10-year static effect
        - behavioral_offset: Total behavioral offset
        - net_effect: Final effect after behavioral response
    """
    annual_static = policy.estimate_static_revenue_effect(0)
    behavioral = policy.estimate_behavioral_offset(annual_static)

    # Growth rate depends on type
    data = policy.get_expenditure_data()
    growth_rate = data.get("growth_rate", 0.03)

    years = np.arange(10)
    annual_effects = annual_static * ((1 + growth_rate) ** years)
    behavioral_effects = behavioral * ((1 + growth_rate) ** years)

    ten_year_static = np.sum(annual_effects)
    ten_year_behavioral = np.sum(behavioral_effects)

    return {
        "annual_static": annual_static,
        "ten_year_static": ten_year_static,
        "behavioral_offset": ten_year_behavioral,
        "net_effect": ten_year_static + ten_year_behavioral,
    }


def get_all_expenditure_estimates() -> dict:
    """
    Get summary of all tax expenditure baseline costs.

    Returns dict mapping expenditure type to annual cost.
    """
    return {
        "Employer Health Insurance": JCT_TAX_EXPENDITURES["employer_health"]["annual_cost"],
        "401(k) and DC Plans": JCT_TAX_EXPENDITURES["retirement_401k"]["annual_cost"],
        "Defined Benefit Plans": JCT_TAX_EXPENDITURES["retirement_db"]["annual_cost"],
        "IRAs": JCT_TAX_EXPENDITURES["retirement_ira"]["annual_cost"],
        "Capital Gains/Dividends": JCT_TAX_EXPENDITURES["capital_gains_dividends"]["annual_cost"],
        "SALT (with $10K cap)": JCT_TAX_EXPENDITURES["salt"]["annual_cost"],
        "SALT (no cap)": JCT_TAX_EXPENDITURES["salt"]["annual_cost_no_cap"],
        "Mortgage Interest": JCT_TAX_EXPENDITURES["mortgage_interest"]["annual_cost"],
        "Charitable Contributions": JCT_TAX_EXPENDITURES["charitable"]["annual_cost"],
        "Step-Up Basis": JCT_TAX_EXPENDITURES["step_up_basis"]["annual_cost"],
        "Like-Kind Exchange": JCT_TAX_EXPENDITURES["like_kind_exchange"]["annual_cost"],
    }
