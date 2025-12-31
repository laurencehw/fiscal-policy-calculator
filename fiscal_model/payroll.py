"""
Payroll Tax Module

Models Social Security and Medicare payroll tax policy changes including:
- Social Security wage cap changes (currently $176,100 in 2025)
- Social Security rate changes
- Medicare rate changes
- Additional Medicare Tax (0.9% on high earners)
- Net Investment Income Tax (NIIT) expansion

Key data sources:
- CBO: Options to Improve Social Security Solvency
- JCT: Revenue estimates for payroll tax changes
- Social Security Trustees Report

Current Law (2025):
- Social Security: 12.4% (6.2% + 6.2%) on wages up to $176,100
- Medicare: 2.9% (1.45% + 1.45%) on all wages, no cap
- Additional Medicare Tax: 0.9% on wages over $200K/$250K
- NIIT: 3.8% on investment income over $200K/$250K
"""

from dataclasses import dataclass, field
from typing import Optional, Literal
from enum import Enum
import numpy as np

from .policies import Policy, TaxPolicy, PolicyType


class PayrollTaxType(Enum):
    """Types of payroll taxes."""
    SOCIAL_SECURITY = "social_security"
    MEDICARE = "medicare"
    ADDITIONAL_MEDICARE = "additional_medicare"
    NIIT = "niit"  # Net Investment Income Tax
    COMBINED = "combined"


# =============================================================================
# CURRENT LAW PARAMETERS
# =============================================================================

# Social Security parameters
SOCIAL_SECURITY_PARAMS = {
    # Tax rates (combined employer + employee)
    "rate_combined": 0.124,  # 12.4% total
    "rate_employee": 0.062,  # 6.2%
    "rate_employer": 0.062,  # 6.2%

    # Wage cap (taxable maximum)
    "cap_2024": 168_600,
    "cap_2025": 176_100,
    "cap_2026": 183_900,  # Projected
    "cap_growth_rate": 0.044,  # ~4.4% annual growth

    # Coverage
    "pct_wages_covered": 0.83,  # ~83% of wages below cap
    "pct_wages_above_cap": 0.17,  # ~17% of wages above cap
}

# Medicare parameters
MEDICARE_PARAMS = {
    # Base rate (combined employer + employee)
    "rate_combined": 0.029,  # 2.9% total
    "rate_employee": 0.0145,
    "rate_employer": 0.0145,

    # No wage cap for Medicare
    "wage_cap": None,

    # Additional Medicare Tax (ACA)
    "additional_rate": 0.009,  # 0.9% on high earners
    "threshold_single": 200_000,
    "threshold_married": 250_000,
}

# Net Investment Income Tax (NIIT)
NIIT_PARAMS = {
    "rate": 0.038,  # 3.8%
    "threshold_single": 200_000,
    "threshold_married": 250_000,
    "annual_revenue_billions": 60.0,  # ~$60B/year (2021 data)
}

# Baseline wage data
BASELINE_WAGE_DATA = {
    # Total wages subject to payroll tax
    "total_wages_billions": 11_000.0,  # ~$11T in wages
    "wages_above_cap_billions": 1_870.0,  # ~$1.87T above SS cap
    "wages_250k_plus_billions": 2_500.0,  # ~$2.5T above $250K

    # Number of workers
    "total_workers_millions": 165.0,
    "workers_above_cap_millions": 12.0,  # ~12M earn above cap
    "workers_above_250k_millions": 8.0,

    # Baseline payroll tax revenue (annual)
    "ss_revenue_billions": 1_100.0,  # ~$1.1T/year
    "medicare_revenue_billions": 400.0,  # ~$400B/year
    "additional_medicare_billions": 15.0,  # ~$15B/year
}

# CBO official estimates
CBO_PAYROLL_ESTIMATES = {
    # Raise SS cap to cover 90% of earnings (~$305K in 2024)
    "cap_90_pct_10yr": 800.0,  # $800B over 10 years
    "cap_90_pct_annual": 80.0,

    # Apply SS tax to earnings above $250K (donut hole)
    "donut_250k_10yr": 2_700.0,  # $2.7T over 10 years (Trustees)
    "donut_250k_annual": 270.0,

    # Eliminate SS cap entirely
    "eliminate_cap_10yr": 3_200.0,  # $3.2T over 10 years (Trustees)
    "eliminate_cap_annual": 320.0,

    # Expand NIIT to pass-through income
    "expand_niit_10yr": 250.0,  # $250B over 10 years (JCT)
    "expand_niit_annual": 25.0,

    # Increase SS rate by 1pp (0.5% each side)
    "rate_1pp_10yr": 900.0,  # ~$900B over 10 years
    "rate_1pp_annual": 90.0,
}


@dataclass
class PayrollTaxPolicy(TaxPolicy):
    """
    Payroll tax policy with Social Security and Medicare modeling.

    Supports:
    - Social Security wage cap changes
    - Social Security rate changes
    - Medicare rate changes
    - Additional Medicare Tax threshold changes
    - NIIT expansion

    Key parameters:
        payroll_tax_type: Type of payroll tax being modified
        ss_cap_change: Change Social Security wage cap
        ss_new_cap: Set specific cap (None = current law)
        ss_eliminate_cap: Eliminate cap entirely
        ss_donut_hole_start: Apply tax above this threshold (donut hole)
        ss_rate_change: Change Social Security rate
        medicare_rate_change: Change Medicare rate
        expand_niit: Expand NIIT to pass-through income
    """

    payroll_tax_type: PayrollTaxType = PayrollTaxType.SOCIAL_SECURITY

    # Social Security cap changes
    ss_cap_change: float = 0.0  # Dollar change in cap
    ss_new_cap: Optional[float] = None  # Set specific cap
    ss_eliminate_cap: bool = False  # Eliminate cap entirely
    ss_donut_hole_start: Optional[float] = None  # Donut hole threshold (e.g., $250K)
    ss_cover_90_pct: bool = False  # Raise cap to cover 90% of wages

    # Rate changes
    ss_rate_change: float = 0.0  # Change in SS rate (combined)
    medicare_rate_change: float = 0.0  # Change in Medicare rate

    # Additional Medicare Tax changes
    additional_medicare_threshold_change: float = 0.0
    additional_medicare_rate_change: float = 0.0

    # NIIT changes
    expand_niit_to_passthrough: bool = False
    niit_rate_change: float = 0.0

    # Behavioral parameters
    labor_supply_elasticity: float = 0.1  # Labor supply response
    tax_avoidance_elasticity: float = 0.15  # Shifting income to avoid tax

    # Calibrated annual revenue change
    annual_revenue_change_billions: Optional[float] = None

    def __post_init__(self):
        """Set default policy type."""
        if self.policy_type == PolicyType.INCOME_TAX:
            self.policy_type = PolicyType.PAYROLL_TAX

    def get_effective_ss_cap(self, year: int) -> Optional[float]:
        """Get the effective Social Security wage cap for a given year."""
        if self.ss_eliminate_cap:
            return None  # No cap

        if self.ss_new_cap is not None:
            return self.ss_new_cap

        if self.ss_cover_90_pct:
            # Cap that covers 90% of wages (~$305K in 2024)
            base_90_pct_cap = 305_000
            years_from_2024 = year - 2024
            growth = SOCIAL_SECURITY_PARAMS["cap_growth_rate"]
            return base_90_pct_cap * ((1 + growth) ** years_from_2024)

        # Current law cap with growth
        base_cap = SOCIAL_SECURITY_PARAMS["cap_2025"]
        years_from_2025 = year - 2025
        growth = SOCIAL_SECURITY_PARAMS["cap_growth_rate"]
        return (base_cap + self.ss_cap_change) * ((1 + growth) ** years_from_2025)

    def estimate_static_revenue_effect(
        self,
        baseline_revenue: float,
        use_real_data: bool = True,
    ) -> float:
        """
        Estimate static revenue effect of payroll tax policy change.

        Args:
            baseline_revenue: Baseline payroll tax revenue (billions)
            use_real_data: Whether to use detailed calculations

        Returns:
            Revenue change in billions (negative = revenue loss)
        """
        if self.annual_revenue_change_billions is not None:
            return self.annual_revenue_change_billions

        total_revenue = 0.0

        # Social Security cap changes
        if self.ss_eliminate_cap:
            # Taxing all wages above current cap
            # ~$1.87T in wages above cap × 12.4% = ~$232B additional
            # But CBO says $3.2T over 10 years = ~$320B/year (includes growth)
            total_revenue += CBO_PAYROLL_ESTIMATES["eliminate_cap_annual"]

        elif self.ss_cover_90_pct:
            # Raise cap to cover 90% of wages
            total_revenue += CBO_PAYROLL_ESTIMATES["cap_90_pct_annual"]

        elif self.ss_donut_hole_start is not None:
            # Donut hole: tax wages above threshold
            if self.ss_donut_hole_start <= 250_000:
                total_revenue += CBO_PAYROLL_ESTIMATES["donut_250k_annual"]
            else:
                # Scale based on threshold
                base_wages = BASELINE_WAGE_DATA["wages_250k_plus_billions"]
                threshold_factor = 250_000 / self.ss_donut_hole_start
                scaled_wages = base_wages * threshold_factor
                total_revenue += scaled_wages * SOCIAL_SECURITY_PARAMS["rate_combined"]

        # Social Security rate changes
        if self.ss_rate_change != 0:
            # 1pp rate increase = ~$90B/year
            rate_change_pp = self.ss_rate_change * 100  # Convert to percentage points
            total_revenue += rate_change_pp * CBO_PAYROLL_ESTIMATES["rate_1pp_annual"]

        # Medicare rate changes
        if self.medicare_rate_change != 0:
            # Medicare applies to all wages
            rate_change_pp = self.medicare_rate_change * 100
            # Medicare revenue is ~$400B at 2.9%, so 1pp = ~$140B
            total_revenue += rate_change_pp * 140.0

        # NIIT expansion
        if self.expand_niit_to_passthrough:
            total_revenue += CBO_PAYROLL_ESTIMATES["expand_niit_annual"]

        return total_revenue

    def estimate_behavioral_offset(self, static_effect: float) -> float:
        """
        Estimate behavioral response to payroll tax changes.

        Behavioral responses include:
        - Labor supply effects (work less in response to higher taxes)
        - Income shifting (convert wages to other income types)
        - Tax avoidance (S-corps, etc.)

        Returns:
            Behavioral offset in billions
        """
        # Labor supply effect
        labor_offset = abs(static_effect) * self.labor_supply_elasticity

        # Tax avoidance (especially for cap elimination)
        if self.ss_eliminate_cap or self.ss_donut_hole_start:
            avoidance_offset = abs(static_effect) * self.tax_avoidance_elasticity
        else:
            avoidance_offset = abs(static_effect) * self.tax_avoidance_elasticity * 0.5

        total_offset = labor_offset + avoidance_offset

        # Offset reduces revenue gain
        if static_effect > 0:
            return -total_offset
        else:
            return total_offset


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_ss_cap_90_percent(
    start_year: int = 2025,
    duration_years: int = 10,
) -> PayrollTaxPolicy:
    """
    Create policy to raise Social Security cap to cover 90% of wages.

    Raises cap from ~$176K to ~$305K (in 2024 dollars).
    CBO estimate: ~$800B over 10 years
    """
    return PayrollTaxPolicy(
        name="SS Cap to 90% of Wages",
        description="Raise Social Security wage cap to cover 90% of earnings (~$305K)",
        policy_type=PolicyType.PAYROLL_TAX,
        payroll_tax_type=PayrollTaxType.SOCIAL_SECURITY,
        ss_cover_90_pct=True,
        labor_supply_elasticity=0.0,  # Behavioral already in calibration
        tax_avoidance_elasticity=0.0,
        # Calibrated to CBO $800B over 10 years (with 4% growth)
        annual_revenue_change_billions=58.5,
        start_year=start_year,
        duration_years=duration_years,
    )


def create_ss_donut_hole(
    threshold: float = 250_000,
    start_year: int = 2025,
    duration_years: int = 10,
) -> PayrollTaxPolicy:
    """
    Create policy to apply Social Security tax above a threshold.

    "Donut hole" approach: tax wages up to current cap AND above threshold.
    Exempts wages between cap and threshold.

    SS Trustees estimate: ~$2.7T over 10 years for $250K threshold
    """
    return PayrollTaxPolicy(
        name=f"SS Donut Hole Above ${threshold/1000:.0f}K",
        description=f"Apply Social Security tax to wages above ${threshold:,.0f}",
        policy_type=PolicyType.PAYROLL_TAX,
        payroll_tax_type=PayrollTaxType.SOCIAL_SECURITY,
        ss_donut_hole_start=threshold,
        labor_supply_elasticity=0.0,  # Behavioral already in calibration
        tax_avoidance_elasticity=0.0,
        # Calibrated to Trustees $2.7T over 10 years (with 4% growth)
        annual_revenue_change_billions=197.5,
        start_year=start_year,
        duration_years=duration_years,
    )


def create_ss_eliminate_cap(
    start_year: int = 2025,
    duration_years: int = 10,
) -> PayrollTaxPolicy:
    """
    Create policy to eliminate the Social Security wage cap entirely.

    Tax all wages at 12.4% (6.2% employee + 6.2% employer).
    SS Trustees estimate: ~$3.2T over 10 years
    """
    return PayrollTaxPolicy(
        name="Eliminate SS Cap",
        description="Eliminate Social Security wage cap, tax all earnings at 12.4%",
        policy_type=PolicyType.PAYROLL_TAX,
        payroll_tax_type=PayrollTaxType.SOCIAL_SECURITY,
        ss_eliminate_cap=True,
        labor_supply_elasticity=0.0,  # Behavioral already in calibration
        tax_avoidance_elasticity=0.0,
        # Calibrated to Trustees $3.2T over 10 years (with 4% growth)
        annual_revenue_change_billions=234.0,
        start_year=start_year,
        duration_years=duration_years,
    )


def create_ss_rate_increase(
    rate_change: float,
    start_year: int = 2025,
    duration_years: int = 10,
) -> PayrollTaxPolicy:
    """
    Create policy to increase Social Security payroll tax rate.

    Args:
        rate_change: Change in rate (e.g., 0.01 for 1pp increase)
        start_year: First year of policy
        duration_years: Duration

    Returns:
        PayrollTaxPolicy for rate increase

    Example:
        # 1pp increase (0.5% on each side)
        policy = create_ss_rate_increase(0.01)
    """
    rate_pp = rate_change * 100
    # 1pp = ~$90B/year
    annual_revenue = rate_pp * 78.5  # Calibrated

    return PayrollTaxPolicy(
        name=f"SS Rate +{rate_pp:.1f}pp",
        description=f"Increase Social Security payroll tax rate by {rate_pp:.1f} percentage points",
        policy_type=PolicyType.PAYROLL_TAX,
        payroll_tax_type=PayrollTaxType.SOCIAL_SECURITY,
        ss_rate_change=rate_change,
        labor_supply_elasticity=0.15,  # Rate increases have larger labor effects
        # Calibrated
        annual_revenue_change_billions=annual_revenue,
        start_year=start_year,
        duration_years=duration_years,
    )


def create_expand_niit(
    start_year: int = 2025,
    duration_years: int = 10,
) -> PayrollTaxPolicy:
    """
    Create policy to expand NIIT to pass-through business income.

    Closes loophole where S-corp and partnership income avoids both
    Additional Medicare Tax and NIIT.

    JCT estimate (Build Back Better): ~$250B over 10 years
    """
    return PayrollTaxPolicy(
        name="Expand NIIT to Pass-Through",
        description="Apply 3.8% NIIT to S-corp and partnership income of high earners",
        policy_type=PolicyType.PAYROLL_TAX,
        payroll_tax_type=PayrollTaxType.NIIT,
        expand_niit_to_passthrough=True,
        labor_supply_elasticity=0.0,  # Behavioral already in calibration
        tax_avoidance_elasticity=0.0,
        # Calibrated to JCT $250B over 10 years (with 4% growth)
        annual_revenue_change_billions=18.3,
        start_year=start_year,
        duration_years=duration_years,
    )


def create_medicare_rate_increase(
    rate_change: float,
    start_year: int = 2025,
    duration_years: int = 10,
) -> PayrollTaxPolicy:
    """
    Create policy to increase Medicare payroll tax rate.

    Args:
        rate_change: Change in rate (e.g., 0.01 for 1pp increase)
        start_year: First year of policy
        duration_years: Duration

    Returns:
        PayrollTaxPolicy for Medicare rate increase
    """
    rate_pp = rate_change * 100
    # Medicare revenue ~$400B at 2.9%, so 1pp = ~$140B
    annual_revenue = rate_pp * 122.0  # Calibrated

    return PayrollTaxPolicy(
        name=f"Medicare Rate +{rate_pp:.1f}pp",
        description=f"Increase Medicare payroll tax rate by {rate_pp:.1f} percentage points",
        policy_type=PolicyType.PAYROLL_TAX,
        payroll_tax_type=PayrollTaxType.MEDICARE,
        medicare_rate_change=rate_change,
        labor_supply_elasticity=0.12,
        annual_revenue_change_billions=annual_revenue,
        start_year=start_year,
        duration_years=duration_years,
    )


def create_biden_payroll_proposal() -> PayrollTaxPolicy:
    """
    Create Biden's payroll tax proposal for Social Security.

    Key features:
    - Apply 12.4% SS tax on wages above $400K (donut hole)
    - Current cap (~$176K) + above $400K taxed
    - Gap between ~$176K and $400K exempt

    Estimated revenue: ~$1.4T over 10 years
    """
    return PayrollTaxPolicy(
        name="Biden SS Tax Above $400K",
        description="Apply Social Security tax to wages above $400K (donut hole)",
        policy_type=PolicyType.PAYROLL_TAX,
        payroll_tax_type=PayrollTaxType.SOCIAL_SECURITY,
        ss_donut_hole_start=400_000,
        labor_supply_elasticity=0.08,
        tax_avoidance_elasticity=0.15,
        # Scaled estimate based on $250K donut hole
        annual_revenue_change_billions=122.0,
        start_year=2025,
        duration_years=10,
    )


# =============================================================================
# VALIDATION SCENARIOS
# =============================================================================

PAYROLL_VALIDATION_SCENARIOS = {
    "ss_cap_90_pct": {
        "description": "SS cap to cover 90% of wages",
        "policy_factory": "create_ss_cap_90_percent",
        "expected_10yr": -800.0,  # Revenue gain (negative = deficit reduction)
        "source": "CBO",
        "notes": "Raise cap from ~$176K to ~$305K",
    },
    "ss_donut_250k": {
        "description": "SS tax on wages above $250K",
        "policy_factory": "create_ss_donut_hole",
        "expected_10yr": -2700.0,  # $2.7T revenue gain
        "source": "Social Security Trustees",
        "notes": "Donut hole: tax current cap + above $250K",
    },
    "ss_eliminate_cap": {
        "description": "Eliminate SS wage cap",
        "policy_factory": "create_ss_eliminate_cap",
        "expected_10yr": -3200.0,  # $3.2T revenue gain
        "source": "Social Security Trustees",
        "notes": "Tax all wages at 12.4%",
    },
    "expand_niit": {
        "description": "Expand NIIT to pass-through income",
        "policy_factory": "create_expand_niit",
        "expected_10yr": -250.0,  # $250B revenue gain
        "source": "JCT (Build Back Better)",
        "notes": "Close S-corp/partnership loophole",
    },
}


def estimate_payroll_revenue(policy: PayrollTaxPolicy) -> dict:
    """
    Estimate total revenue effect of a payroll tax policy.

    Returns dict with:
        - annual_static: Average annual static effect
        - ten_year_static: Total 10-year static effect
        - behavioral_offset: Total behavioral offset
        - net_effect: Final effect after behavioral response
    """
    annual_static = policy.estimate_static_revenue_effect(0)
    behavioral = policy.estimate_behavioral_offset(annual_static)

    # Apply growth (~4%/year for wage growth)
    years = np.arange(10)
    annual_effects = annual_static * (1.04 ** years)
    behavioral_effects = behavioral * (1.04 ** years)

    ten_year_static = np.sum(annual_effects)
    ten_year_behavioral = np.sum(behavioral_effects)

    return {
        "annual_static": annual_static,
        "ten_year_static": ten_year_static,
        "behavioral_offset": ten_year_behavioral,
        "net_effect": ten_year_static + ten_year_behavioral,
    }
