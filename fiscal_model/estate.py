"""
Estate Tax Module

Models federal estate and gift tax policy changes including:
- Exemption level changes
- Rate changes
- Portability provisions
- Behavioral responses (estate planning, gifts)

Key data sources:
- CBO: Understanding Federal Estate and Gift Taxes (2021)
- JCT: Revenue estimates for TCJA estate provisions
- Tax Policy Center: Taxable estates estimates

Current Law (TCJA, through 2025):
- Exemption: $13.99M per person (2025), indexed to inflation
- Top rate: 40%
- Taxable estates: ~7,000/year
- Revenue: ~$32B/year

Scheduled 2026 (post-TCJA sunset):
- Exemption: ~$6.4M per person (inflation-adjusted)
- Taxable estates: ~19,000/year
- Revenue projected to increase to ~$50B/year
"""

from dataclasses import dataclass, field
from typing import Optional, Literal
from enum import Enum
import numpy as np

from .policies import Policy, TaxPolicy, PolicyType


class EstateTaxScenario(Enum):
    """Common estate tax policy scenarios."""
    CURRENT_LAW = "current_law"  # TCJA expires 2026
    EXTEND_TCJA = "extend_tcja"  # Keep $14M+ exemption
    LOWER_EXEMPTION = "lower_exemption"  # e.g., $3.5M
    INCREASE_RATE = "increase_rate"
    ELIMINATE = "eliminate"


# =============================================================================
# CURRENT LAW PARAMETERS
# =============================================================================

# Current law exemption levels (indexed to inflation)
ESTATE_TAX_EXEMPTIONS = {
    2024: 13_610_000,  # Per person
    2025: 13_990_000,  # Per person (estimated)
    2026: 6_400_000,   # Post-TCJA sunset (estimated, inflation-adjusted)
    2027: 6_600_000,   # Projected
    2028: 6_800_000,
    2029: 7_000_000,
    2030: 7_200_000,
    2031: 7_400_000,
    2032: 7_600_000,
    2033: 7_800_000,
    2034: 8_000_000,
}

# TCJA-extended exemption levels (if made permanent)
TCJA_EXTENDED_EXEMPTIONS = {
    2026: 14_400_000,
    2027: 14_800_000,
    2028: 15_200_000,
    2029: 15_600_000,
    2030: 16_000_000,
    2031: 16_400_000,
    2032: 16_800_000,
    2033: 17_200_000,
    2034: 17_600_000,
}

# Estate tax rate (unchanged by TCJA)
CURRENT_ESTATE_TAX_RATE = 0.40

# Baseline data
BASELINE_ESTATE_DATA = {
    # Annual revenue (billions)
    "revenue_2024": 32.0,  # FY2024 actual
    "revenue_baseline_2026": 50.0,  # CBO projection if exemption drops

    # Taxable estates per year
    "taxable_estates_tcja": 7_000,  # Under TCJA high exemption
    "taxable_estates_post_tcja": 19_000,  # After exemption drop

    # Average taxable estate (over exemption)
    "avg_taxable_amount_tcja": 8_000_000,  # ~$8M average for top estates
    "avg_taxable_amount_post_tcja": 4_000_000,  # More estates but smaller avg

    # Total deaths per year
    "annual_deaths": 2_800_000,

    # Behavioral parameters
    "planning_elasticity": 0.15,  # Response to exemption/rate changes
    "gift_shifting_rate": 0.10,  # Fraction shifted to gifts
}

# CBO/JCT official estimates
CBO_ESTATE_ESTIMATES = {
    # Cost of extending TCJA exemption
    "extend_tcja_10yr": 167.0,  # Billions over 10 years (CBO)
    "extend_tcja_annual": 16.7,  # Average annual cost

    # JCT estimate for permanent extension
    "permanent_extension_10yr": 201.0,  # FY2025-2034

    # Revenue projections (2021-2031)
    "total_revenue_10yr": 372.0,  # Combined estate + gift
}


@dataclass
class EstateTaxPolicy(TaxPolicy):
    """
    Estate tax policy modeling exemption and rate changes.

    Models the federal estate (and gift) tax which applies to transfers
    of wealth at death above the exemption amount.

    Key parameters:
        exemption_change: Change in exemption level (dollars)
        new_exemption: New exemption level (overrides exemption_change)
        rate_change: Change in estate tax rate (e.g., 0.05 for 5pp increase)
        new_rate: New estate tax rate (overrides rate_change)

    Behavioral responses:
        - Higher exemptions reduce taxable estates
        - Lower rates reduce planning/avoidance
        - Lock-in effects similar to capital gains
    """

    # Exemption changes
    exemption_change: float = 0.0  # Dollar change in exemption
    new_exemption: Optional[float] = None  # Set specific exemption level
    extend_tcja_exemption: bool = False  # Keep ~$14M exemption beyond 2025

    # Rate changes
    rate_change: float = 0.0  # Change in estate tax rate
    new_rate: Optional[float] = None  # Set specific rate

    # Portability (unused exemption transfers to surviving spouse)
    modify_portability: bool = False
    portability_cap: Optional[float] = None  # Cap on portable amount

    # Behavioral parameters
    planning_elasticity: float = 0.15  # Response to policy changes
    gift_shifting_elasticity: float = 0.10  # Shifting to inter vivos gifts

    # Valuation discounts (family-owned businesses, etc.)
    limit_valuation_discounts: bool = False
    discount_limit_pct: float = 0.0  # Cap discounts at this percent

    # Base year for calculations
    base_year: int = 2024

    # Calibration
    annual_revenue_change_billions: Optional[float] = None

    def __post_init__(self):
        """Set default policy type."""
        if self.policy_type == PolicyType.INCOME_TAX:
            self.policy_type = PolicyType.ESTATE_TAX

    def get_exemption_for_year(self, year: int, policy_active: bool = True) -> float:
        """
        Get the effective exemption for a given year.

        Args:
            year: Tax year
            policy_active: Whether policy is in effect

        Returns:
            Exemption amount in dollars
        """
        if not policy_active:
            # Return baseline (current law)
            return ESTATE_TAX_EXEMPTIONS.get(year, ESTATE_TAX_EXEMPTIONS[2034])

        if self.new_exemption is not None:
            # Specific exemption set
            return self.new_exemption

        if self.extend_tcja_exemption:
            # Keep TCJA-level exemptions
            return TCJA_EXTENDED_EXEMPTIONS.get(year, TCJA_EXTENDED_EXEMPTIONS[2034])

        # Apply exemption change to baseline
        baseline = ESTATE_TAX_EXEMPTIONS.get(year, ESTATE_TAX_EXEMPTIONS[2034])
        return baseline + self.exemption_change

    def get_rate_for_year(self, year: int) -> float:
        """Get the effective estate tax rate."""
        if self.new_rate is not None:
            return self.new_rate
        return CURRENT_ESTATE_TAX_RATE + self.rate_change

    def estimate_taxable_estates(
        self,
        exemption: float,
        year: int = 2025,
    ) -> tuple[int, float]:
        """
        Estimate number of taxable estates and average taxable amount.

        Uses relationship between exemption level and taxable estates.
        Higher exemption = fewer estates pay tax.

        Args:
            exemption: Effective exemption level
            year: Tax year

        Returns:
            Tuple of (number of taxable estates, average taxable amount)
        """
        # Reference points
        tcja_exemption = 14_000_000
        tcja_estates = BASELINE_ESTATE_DATA["taxable_estates_tcja"]
        tcja_avg = BASELINE_ESTATE_DATA["avg_taxable_amount_tcja"]

        post_tcja_exemption = 6_400_000
        post_tcja_estates = BASELINE_ESTATE_DATA["taxable_estates_post_tcja"]
        post_tcja_avg = BASELINE_ESTATE_DATA["avg_taxable_amount_post_tcja"]

        # Interpolate based on exemption level
        if exemption >= tcja_exemption:
            # Very high exemption - fewer estates
            scale = tcja_exemption / exemption
            estates = int(tcja_estates * scale)
            avg_amount = tcja_avg * (1 + (exemption - tcja_exemption) / tcja_exemption)
        elif exemption <= post_tcja_exemption:
            # Low exemption - more estates
            scale = post_tcja_exemption / exemption
            estates = int(post_tcja_estates * scale)
            avg_amount = post_tcja_avg * (exemption / post_tcja_exemption)
        else:
            # Linear interpolation
            frac = (exemption - post_tcja_exemption) / (tcja_exemption - post_tcja_exemption)
            estates = int(post_tcja_estates + frac * (tcja_estates - post_tcja_estates))
            avg_amount = post_tcja_avg + frac * (tcja_avg - post_tcja_avg)

        return estates, avg_amount

    def estimate_static_revenue_effect(
        self,
        baseline_revenue: float,
        use_real_data: bool = True,
    ) -> float:
        """
        Estimate static revenue effect of estate tax policy change.

        Args:
            baseline_revenue: Baseline estate tax revenue (billions)
            use_real_data: Whether to use detailed calculations

        Returns:
            Revenue change in billions (negative = revenue loss)
        """
        if self.annual_revenue_change_billions is not None:
            return self.annual_revenue_change_billions

        # Use CBO estimate for TCJA extension
        if self.extend_tcja_exemption:
            return -CBO_ESTATE_ESTIMATES["extend_tcja_annual"]

        # Calculate from exemption/rate changes
        baseline_exemption = ESTATE_TAX_EXEMPTIONS.get(
            self.start_year + 1,  # First full year
            ESTATE_TAX_EXEMPTIONS[2026]
        )
        policy_exemption = self.get_exemption_for_year(self.start_year + 1)

        # Get taxable estates under each scenario
        baseline_estates, baseline_avg = self.estimate_taxable_estates(baseline_exemption)
        policy_estates, policy_avg = self.estimate_taxable_estates(policy_exemption)

        # Calculate revenue
        baseline_rate = CURRENT_ESTATE_TAX_RATE
        policy_rate = self.get_rate_for_year(self.start_year + 1)

        baseline_revenue = baseline_estates * baseline_avg * baseline_rate / 1e9
        policy_revenue = policy_estates * policy_avg * policy_rate / 1e9

        return policy_revenue - baseline_revenue

    def estimate_behavioral_offset(self, static_effect: float) -> float:
        """
        Estimate behavioral response to estate tax changes.

        Behavioral responses include:
        - Estate planning (trusts, family partnerships)
        - Inter vivos gifts to reduce estate
        - Valuation discounts
        - Charitable giving

        Returns:
            Behavioral offset in billions
        """
        # Planning response
        planning_offset = abs(static_effect) * self.planning_elasticity

        # Gift shifting response
        gift_offset = abs(static_effect) * self.gift_shifting_elasticity

        total_offset = planning_offset + gift_offset

        # Offset reduces revenue gain or loss
        if static_effect > 0:
            return -total_offset  # Reduces revenue gain
        else:
            return total_offset  # Reduces revenue loss


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_tcja_estate_extension(
    start_year: int = 2026,
    duration_years: int = 10,
) -> EstateTaxPolicy:
    """
    Create policy to extend TCJA estate tax exemption.

    Keeps the ~$14M exemption (indexed) instead of reverting
    to ~$6.4M in 2026.

    CBO estimate: $167B cost over 10 years
    """
    return EstateTaxPolicy(
        name="Extend TCJA Estate Exemption",
        description="Extend doubled estate tax exemption (~$14M vs ~$6.4M) beyond 2025",
        policy_type=PolicyType.ESTATE_TAX,
        extend_tcja_exemption=True,
        planning_elasticity=0.0,  # Behavioral response already in calibration
        # Calibrated to CBO $167B over 10 years (with 3% annual growth)
        annual_revenue_change_billions=-14.6,
        start_year=start_year,
        duration_years=duration_years,
    )


def create_biden_estate_proposal(
    exemption: float = 3_500_000,
    rate: float = 0.45,
    start_year: int = 2025,
    duration_years: int = 10,
) -> EstateTaxPolicy:
    """
    Create Biden-style estate tax reform.

    Key features:
    - Lower exemption to $3.5M (from $14M)
    - Increase rate to 45% (from 40%)

    This would dramatically increase taxable estates and revenue.
    Treasury estimate: ~$450B over 10 years
    """
    return EstateTaxPolicy(
        name="Biden Estate Tax Reform",
        description=f"Lower exemption to ${exemption/1e6:.1f}M, raise rate to {rate*100:.0f}%",
        policy_type=PolicyType.ESTATE_TAX,
        new_exemption=exemption,
        new_rate=rate,
        planning_elasticity=0.0,  # Behavioral response in calibration
        # Calibrated to Treasury ~$450B over 10 years (with 3% growth)
        annual_revenue_change_billions=39.3,
        start_year=start_year,
        duration_years=duration_years,
    )


def create_warren_estate_proposal(
    start_year: int = 2025,
    duration_years: int = 10,
) -> EstateTaxPolicy:
    """
    Create Warren-style progressive estate tax.

    Key features:
    - $3.5M exemption
    - Progressive rates: 45% up to $10M, 55% up to $50M, 65% over $1B
    - Limit valuation discounts

    For simplicity, we use the effective average rate.
    """
    return EstateTaxPolicy(
        name="Warren Progressive Estate Tax",
        description="$3.5M exemption, progressive rates up to 65% on billionaires",
        policy_type=PolicyType.ESTATE_TAX,
        new_exemption=3_500_000,
        new_rate=0.55,  # Effective average rate
        limit_valuation_discounts=True,
        discount_limit_pct=0.10,
        planning_elasticity=0.25,  # High response to aggressive policy
        # Penn Wharton estimated ~$2.6T over 10 years
        annual_revenue_change_billions=260.0,
        start_year=start_year,
        duration_years=duration_years,
    )


def create_estate_rate_change(
    rate_change: float,
    start_year: int = 2025,
    duration_years: int = 10,
    name: Optional[str] = None,
) -> EstateTaxPolicy:
    """
    Create a simple estate tax rate change.

    Args:
        rate_change: Change in rate (e.g., 0.05 for 5pp increase)
        start_year: First year of policy
        duration_years: Duration
        name: Optional custom name

    Returns:
        EstateTaxPolicy for rate change
    """
    direction = "increase" if rate_change > 0 else "decrease"
    new_rate = CURRENT_ESTATE_TAX_RATE + rate_change

    # Estimate revenue effect
    # ~$32B baseline revenue, rate change proportional
    baseline_revenue = BASELINE_ESTATE_DATA["revenue_2024"]
    static_pct_change = rate_change / CURRENT_ESTATE_TAX_RATE
    annual_change = baseline_revenue * static_pct_change

    return EstateTaxPolicy(
        name=name or f"Estate Tax Rate {direction.title()} to {new_rate*100:.0f}%",
        description=f"Change estate tax rate from 40% to {new_rate*100:.0f}%",
        policy_type=PolicyType.ESTATE_TAX,
        rate_change=rate_change,
        planning_elasticity=0.15,
        annual_revenue_change_billions=annual_change,
        start_year=start_year,
        duration_years=duration_years,
    )


def create_estate_exemption_change(
    new_exemption: float,
    start_year: int = 2025,
    duration_years: int = 10,
    name: Optional[str] = None,
) -> EstateTaxPolicy:
    """
    Create an estate tax exemption change policy.

    Args:
        new_exemption: New exemption level in dollars
        start_year: First year of policy
        duration_years: Duration
        name: Optional custom name

    Returns:
        EstateTaxPolicy for exemption change
    """
    policy = EstateTaxPolicy(
        name=name or f"Estate Exemption to ${new_exemption/1e6:.1f}M",
        description=f"Set estate tax exemption to ${new_exemption:,.0f}",
        policy_type=PolicyType.ESTATE_TAX,
        new_exemption=new_exemption,
        planning_elasticity=0.15,
        start_year=start_year,
        duration_years=duration_years,
    )

    # Calculate annual revenue change
    annual_change = policy.estimate_static_revenue_effect(0)
    policy.annual_revenue_change_billions = annual_change

    return policy


def create_eliminate_estate_tax(
    start_year: int = 2025,
    duration_years: int = 10,
) -> EstateTaxPolicy:
    """
    Create policy to eliminate the estate tax entirely.

    Estimated cost: ~$350B over 10 years (foregone revenue)
    """
    return EstateTaxPolicy(
        name="Eliminate Estate Tax",
        description="Repeal the federal estate tax entirely",
        policy_type=PolicyType.ESTATE_TAX,
        new_exemption=float('inf'),  # Effectively no tax
        new_rate=0.0,
        planning_elasticity=0.0,  # No behavioral offset needed
        # Calibrated: ~$350B over 10 years (with 3% growth)
        annual_revenue_change_billions=-30.6,
        start_year=start_year,
        duration_years=duration_years,
    )


# =============================================================================
# VALIDATION SCENARIOS
# =============================================================================

ESTATE_VALIDATION_SCENARIOS = {
    "extend_tcja_exemption": {
        "description": "Extend TCJA estate exemption",
        "policy_factory": "create_tcja_estate_extension",
        "expected_10yr": 167.0,  # CBO estimate (cost = positive)
        "source": "CBO",
        "notes": "Keep $14M+ exemption instead of reversion to $6.4M",
    },
    "biden_estate_reform": {
        "description": "Biden estate tax reform ($3.5M, 45%)",
        "policy_factory": "create_biden_estate_proposal",
        "expected_10yr": -450.0,  # Revenue gain (negative = deficit reduction)
        "source": "Treasury estimate",
        "notes": "Lower exemption + higher rate raises significant revenue",
    },
}


def estimate_estate_revenue(policy: EstateTaxPolicy) -> dict:
    """
    Estimate total revenue effect of an estate tax policy.

    Returns dict with:
        - annual_static: Average annual static effect
        - ten_year_static: Total 10-year static effect
        - behavioral_offset: Total behavioral offset
        - net_effect: Final effect after behavioral response
    """
    annual_static = policy.estimate_static_revenue_effect(0)
    behavioral = policy.estimate_behavioral_offset(annual_static)

    # Apply growth (~3%/year for wealth growth)
    years = np.arange(10)
    annual_effects = annual_static * (1.03 ** years)
    behavioral_effects = behavioral * (1.03 ** years)

    ten_year_static = np.sum(annual_effects)
    ten_year_behavioral = np.sum(behavioral_effects)

    return {
        "annual_static": annual_static,
        "ten_year_static": ten_year_static,
        "behavioral_offset": ten_year_behavioral,
        "net_effect": ten_year_static + ten_year_behavioral,
    }
