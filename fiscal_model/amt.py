"""
Alternative Minimum Tax (AMT) Module

Models federal Alternative Minimum Tax policy changes including:
- Individual AMT exemption level changes
- Phase-out threshold changes
- AMT rate changes (26%/28%)
- Corporate AMT (CAMT - 15% book minimum)

Key data sources:
- CBO: Budget Options, Baseline Projections
- JCT: TCJA scores, revenue estimates
- Tax Policy Center: AMT taxpayer estimates

Current Law (TCJA, through 2025):
- Single exemption: $88,100 (2025), phased out above $626,350
- MFJ exemption: $137,000 (2025), phased out above $1,218,700
- Rates: 26% on first $232,600 (MFJ), 28% above
- Taxpayers affected: ~200,000/year
- Revenue: ~$5B/year

Scheduled 2026 (post-TCJA sunset):
- Single exemption: ~$60,000 (projected)
- MFJ exemption: ~$93,000 (projected)
- Phase-out thresholds drop significantly
- Taxpayers affected: ~7.3M (TPC estimate)
- Revenue: ~$60-75B/year by 2030

Corporate AMT (IRA 2022, permanent):
- 15% on adjusted financial statement income
- Applies to corps with $1B+ avg annual income
- Revenue: ~$22B/year
"""

from dataclasses import dataclass, field
from typing import Optional, Literal
from enum import Enum
import numpy as np

from .policies import Policy, TaxPolicy, PolicyType


class AMTType(Enum):
    """Type of AMT being modeled."""
    INDIVIDUAL = "individual"
    CORPORATE = "corporate"  # Book minimum tax from IRA


# =============================================================================
# CURRENT LAW PARAMETERS
# =============================================================================

# Individual AMT exemption levels under TCJA (inflation-indexed)
AMT_EXEMPTIONS_TCJA = {
    # (single, mfj, mfs)
    2024: (85_700, 133_300, 66_650),
    2025: (88_100, 137_000, 68_500),
    # Post-TCJA sunset (estimated)
    2026: (60_000, 93_000, 46_500),
    2027: (62_000, 96_000, 48_000),
    2028: (64_000, 99_000, 49_500),
    2029: (66_000, 102_000, 51_000),
    2030: (68_000, 105_000, 52_500),
    2031: (70_000, 108_000, 54_000),
    2032: (72_000, 111_000, 55_500),
    2033: (74_000, 114_000, 57_000),
    2034: (76_000, 117_000, 58_500),
}

# If TCJA is extended (keep higher exemptions)
AMT_EXEMPTIONS_TCJA_EXTENDED = {
    2026: (91_000, 141_000, 70_500),
    2027: (94_000, 145_000, 72_500),
    2028: (97_000, 150_000, 75_000),
    2029: (100_000, 155_000, 77_500),
    2030: (103_000, 160_000, 80_000),
    2031: (106_000, 165_000, 82_500),
    2032: (109_000, 170_000, 85_000),
    2033: (112_000, 175_000, 87_500),
    2034: (115_000, 180_000, 90_000),
}

# Phase-out thresholds under TCJA
AMT_PHASEOUT_TCJA = {
    # (single, mfj) - exemption phases out at 25 cents per dollar above these
    2024: (609_350, 1_218_700),
    2025: (626_350, 1_252_700),
    # Post-TCJA (reverts to lower thresholds)
    2026: (150_000, 200_000),  # Pre-TCJA levels (estimated with inflation)
    2027: (155_000, 206_000),
    2028: (160_000, 212_000),
    2029: (165_000, 218_000),
    2030: (170_000, 225_000),
}

# AMT rates (unchanged by TCJA)
AMT_RATES = {
    "first_tier": 0.26,  # 26% on AMTI up to threshold
    "second_tier": 0.28,  # 28% above threshold
    "tier_threshold_mfj": 232_600,  # 2025 MFJ
    "tier_threshold_single": 116_300,  # 2025 single
}

# Corporate AMT (CAMT) from Inflation Reduction Act 2022
CORPORATE_AMT = {
    "rate": 0.15,  # 15% book minimum tax
    "threshold": 1_000_000_000,  # $1B average annual income
    "revenue_per_year": 22.0,  # ~$22B/year (CBO)
}

# Baseline data
BASELINE_AMT_DATA = {
    # Taxpayers affected
    "taxpayers_tcja": 200_000,  # Under high TCJA exemptions
    "taxpayers_post_tcja": 7_300_000,  # After exemptions drop (TPC)

    # Revenue (billions per year)
    "revenue_tcja": 5.0,  # Under TCJA (~$5B/year)
    "revenue_post_tcja_2030": 75.0,  # Projected after sunset (~$75B by 2030)

    # Average AMT liability
    "avg_amt_tcja": 25_000,  # Higher-income taxpayers under TCJA
    "avg_amt_post_tcja": 10_000,  # More taxpayers, lower average

    # Behavioral parameters
    "timing_elasticity": 0.15,  # Income timing response
    "avoidance_elasticity": 0.10,  # Tax planning response
}

# CBO/JCT official estimates
CBO_AMT_ESTIMATES = {
    # Cost of extending TCJA AMT relief
    "extend_tcja_10yr": 450.0,  # ~$450B over 10 years (from TCJA component)
    "extend_tcja_annual": 39.3,  # Average annual (calibrated with 3% growth)

    # Revenue from letting TCJA expire (baseline)
    "tcja_expiration_10yr": 450.0,  # Revenue GAIN if TCJA expires

    # Current individual AMT revenue
    "current_individual_annual": 5.0,  # ~$5B/year under TCJA

    # Corporate AMT (permanent, not affected by TCJA sunset)
    "camt_annual": 22.0,  # ~$22B/year from IRA 2022
    "camt_10yr": 220.0,

    # Repeal individual AMT entirely
    "repeal_individual_10yr": 450.0,  # Cost if repealed (loses $450B revenue)
}


@dataclass
class AMTPolicy(TaxPolicy):
    """
    Alternative Minimum Tax policy modeling exemption, rate, and threshold changes.

    Models both individual AMT and corporate AMT (book minimum tax).

    Key parameters:
        amt_type: Whether modeling individual or corporate AMT
        extend_tcja_relief: Extend TCJA's higher exemptions past 2025
        exemption_change: Change in exemption levels (dollars)
        new_exemption_single: Specific new exemption (single)
        new_exemption_mfj: Specific new exemption (MFJ)
        repeal_individual_amt: Fully repeal individual AMT
        rate_change: Change in AMT rates

    Behavioral responses:
        - Income timing (defer income to avoid AMT)
        - Tax planning (restructure to minimize AMTI)
    """

    # AMT type
    amt_type: AMTType = field(default=AMTType.INDIVIDUAL)

    # TCJA extension
    extend_tcja_relief: bool = False  # Keep TCJA's high exemptions post-2025

    # Exemption changes (individual AMT)
    exemption_change: float = 0.0  # Dollar change in exemption
    new_exemption_single: Optional[float] = None
    new_exemption_mfj: Optional[float] = None

    # Full repeal options
    repeal_individual_amt: bool = False
    repeal_corporate_amt: bool = False

    # Rate changes
    rate_change: float = 0.0  # Change to both tiers
    new_first_tier_rate: Optional[float] = None  # 26% default
    new_second_tier_rate: Optional[float] = None  # 28% default

    # Phase-out changes
    phase_out_threshold_change: float = 0.0  # Change to phase-out start

    # Behavioral parameters
    timing_elasticity: float = 0.15
    avoidance_elasticity: float = 0.10

    # Base year for calculations
    base_year: int = 2024

    # Calibration
    annual_revenue_change_billions: Optional[float] = None

    def __post_init__(self):
        """Set default policy type."""
        if self.policy_type == PolicyType.INCOME_TAX:
            self.policy_type = PolicyType.INCOME_TAX  # AMT is part of income tax

    def get_exemption_for_year(
        self,
        year: int,
        filing_status: str = "mfj"
    ) -> float:
        """
        Get the effective AMT exemption for a given year.

        Args:
            year: Tax year
            filing_status: 'single', 'mfj', or 'mfs'

        Returns:
            Exemption amount in dollars
        """
        if self.repeal_individual_amt:
            return float('inf')  # No AMT = infinite exemption

        # Specific exemption overrides
        if filing_status == "single" and self.new_exemption_single is not None:
            return self.new_exemption_single
        if filing_status == "mfj" and self.new_exemption_mfj is not None:
            return self.new_exemption_mfj
        if filing_status == "mfs" and self.new_exemption_mfj is not None:
            return self.new_exemption_mfj / 2  # MFS is half of MFJ

        # TCJA extension
        if self.extend_tcja_relief:
            if year in AMT_EXEMPTIONS_TCJA_EXTENDED:
                exemptions = AMT_EXEMPTIONS_TCJA_EXTENDED[year]
            else:
                exemptions = AMT_EXEMPTIONS_TCJA_EXTENDED[2034]
        else:
            # Current law baseline
            if year in AMT_EXEMPTIONS_TCJA:
                exemptions = AMT_EXEMPTIONS_TCJA[year]
            else:
                exemptions = AMT_EXEMPTIONS_TCJA[2034]

        # Extract by filing status
        idx = {"single": 0, "mfj": 1, "mfs": 2}.get(filing_status, 1)
        base = exemptions[idx]

        return base + self.exemption_change

    def get_rate_for_tier(self, tier: int = 1) -> float:
        """
        Get AMT rate for a tier (1 = 26%, 2 = 28%).

        Args:
            tier: 1 for first tier, 2 for second tier

        Returns:
            Tax rate as decimal
        """
        if tier == 1:
            if self.new_first_tier_rate is not None:
                return self.new_first_tier_rate
            return AMT_RATES["first_tier"] + self.rate_change
        else:
            if self.new_second_tier_rate is not None:
                return self.new_second_tier_rate
            return AMT_RATES["second_tier"] + self.rate_change

    def estimate_affected_taxpayers(self, year: int = 2026) -> int:
        """
        Estimate number of taxpayers affected by AMT.

        Under TCJA high exemptions: ~200,000
        After TCJA sunset: ~7.3M
        """
        if self.repeal_individual_amt:
            return 0

        # Get exemption level to estimate taxpayers
        exemption = self.get_exemption_for_year(year, "mfj")

        # Reference points
        tcja_exemption = 137_000
        post_tcja_exemption = 93_000

        tcja_taxpayers = BASELINE_AMT_DATA["taxpayers_tcja"]
        post_tcja_taxpayers = BASELINE_AMT_DATA["taxpayers_post_tcja"]

        # Higher exemption = fewer affected taxpayers
        if exemption >= tcja_exemption:
            # Scale down from TCJA baseline
            ratio = tcja_exemption / exemption
            return int(tcja_taxpayers * ratio)
        elif exemption <= post_tcja_exemption:
            # Scale up from post-TCJA baseline
            ratio = post_tcja_exemption / exemption
            return int(post_tcja_taxpayers * ratio)
        else:
            # Interpolate
            frac = (exemption - post_tcja_exemption) / (tcja_exemption - post_tcja_exemption)
            return int(post_tcja_taxpayers + frac * (tcja_taxpayers - post_tcja_taxpayers))

    def estimate_static_revenue_effect(
        self,
        baseline_revenue: float,
        use_real_data: bool = True,
    ) -> float:
        """
        Estimate static revenue effect of AMT policy change.

        Args:
            baseline_revenue: Baseline revenue (not used; we use calibrated values)
            use_real_data: Whether to use detailed calculations

        Returns:
            Revenue change in billions (negative = revenue loss)
        """
        if self.annual_revenue_change_billions is not None:
            return self.annual_revenue_change_billions

        # Handle corporate AMT
        if self.amt_type == AMTType.CORPORATE:
            if self.repeal_corporate_amt:
                return -CORPORATE_AMT["revenue_per_year"]
            # Rate changes for corporate AMT
            if self.rate_change != 0:
                base_revenue = CORPORATE_AMT["revenue_per_year"]
                pct_change = self.rate_change / CORPORATE_AMT["rate"]
                return base_revenue * pct_change
            return 0.0

        # Individual AMT
        if self.repeal_individual_amt:
            # Cost of full repeal (lose all individual AMT revenue)
            # Under current law, this is ~$5B/year but grows significantly
            return -CBO_AMT_ESTIMATES["current_individual_annual"]

        if self.extend_tcja_relief:
            # Cost of extending TCJA relief (foregone revenue)
            return -CBO_AMT_ESTIMATES["extend_tcja_annual"]

        # Calculate from exemption changes
        baseline_exemption = AMT_EXEMPTIONS_TCJA.get(
            self.start_year + 1,
            AMT_EXEMPTIONS_TCJA[2026]
        )[1]  # MFJ

        policy_exemption = self.get_exemption_for_year(self.start_year + 1, "mfj")

        # Estimate revenue based on taxpayer count and average liability
        baseline_taxpayers = self.estimate_affected_taxpayers(self.start_year + 1)
        # Approximate new taxpayer count
        old_policy = AMTPolicy(amt_type=AMTType.INDIVIDUAL)  # Default policy
        policy_taxpayers = self.estimate_affected_taxpayers(self.start_year + 1)

        # Get average liability (inversely related to exemption for those affected)
        avg_liability = BASELINE_AMT_DATA["avg_amt_post_tcja"]  # ~$10K average

        # Revenue = taxpayers × avg liability
        baseline_revenue = baseline_taxpayers * avg_liability / 1e9
        policy_revenue = policy_taxpayers * avg_liability / 1e9

        return policy_revenue - baseline_revenue

    def estimate_behavioral_offset(self, static_effect: float) -> float:
        """
        Estimate behavioral response to AMT changes.

        Behavioral responses include:
        - Income timing (accelerate/defer income)
        - Tax planning (restructure to minimize AMTI)
        - Charitable giving timing

        Returns:
            Behavioral offset in billions
        """
        # Timing response
        timing_offset = abs(static_effect) * self.timing_elasticity

        # Avoidance response
        avoidance_offset = abs(static_effect) * self.avoidance_elasticity

        total_offset = timing_offset + avoidance_offset

        # Offset reduces revenue gain or loss
        if static_effect > 0:
            return -total_offset  # Reduces revenue gain
        else:
            return total_offset  # Reduces revenue loss


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_extend_tcja_amt_relief(
    start_year: int = 2026,
    duration_years: int = 10,
) -> AMTPolicy:
    """
    Create policy to extend TCJA AMT relief beyond 2025.

    Keeps the higher exemptions ($88K single, $137K MFJ) instead of
    reverting to pre-TCJA levels (~$60K single, ~$93K MFJ).

    CBO/JCT estimate: ~$450B cost over 10 years
    """
    return AMTPolicy(
        name="Extend TCJA AMT Relief",
        description="Extend higher AMT exemptions beyond 2025 sunset",
        policy_type=PolicyType.INCOME_TAX,
        amt_type=AMTType.INDIVIDUAL,
        extend_tcja_relief=True,
        timing_elasticity=0.0,  # Behavioral already in calibration
        avoidance_elasticity=0.0,
        # Calibrated to ~$450B over 10 years (with 3% annual growth)
        annual_revenue_change_billions=-39.3,
        start_year=start_year,
        duration_years=duration_years,
    )


def create_repeal_individual_amt(
    start_year: int = 2025,
    duration_years: int = 10,
) -> AMTPolicy:
    """
    Create policy to fully repeal the individual AMT.

    This eliminates all individual AMT revenue.
    Under TCJA, this is ~$5B/year, growing to ~$75B/year after sunset.

    If starting post-2025 (after sunset), the 10-year cost is ~$450B.
    If starting in 2025 (before sunset), cost is lower (~$50B over 10 years).
    """
    # Cost depends on whether TCJA is still in effect
    if start_year <= 2025:
        # TCJA still in effect - lower revenue to lose
        annual_cost = -5.0  # ~$5B/year under TCJA
    else:
        # Post-TCJA - more revenue at stake
        annual_cost = -39.3  # Growing to ~$75B by 2030

    return AMTPolicy(
        name="Repeal Individual AMT",
        description="Fully repeal the individual Alternative Minimum Tax",
        policy_type=PolicyType.INCOME_TAX,
        amt_type=AMTType.INDIVIDUAL,
        repeal_individual_amt=True,
        timing_elasticity=0.0,
        avoidance_elasticity=0.0,
        annual_revenue_change_billions=annual_cost,
        start_year=start_year,
        duration_years=duration_years,
    )


def create_repeal_corporate_amt(
    start_year: int = 2025,
    duration_years: int = 10,
) -> AMTPolicy:
    """
    Create policy to repeal the corporate AMT (book minimum tax).

    The 15% corporate AMT was enacted in IRA 2022 and is permanent.
    Repealing would cost ~$22B/year in lost revenue.
    """
    return AMTPolicy(
        name="Repeal Corporate AMT",
        description="Repeal the 15% book minimum tax (CAMT) from IRA 2022",
        policy_type=PolicyType.CORPORATE_TAX,
        amt_type=AMTType.CORPORATE,
        repeal_corporate_amt=True,
        timing_elasticity=0.0,
        avoidance_elasticity=0.0,
        # Calibrated: ~$220B over 10 years
        annual_revenue_change_billions=-19.2,
        start_year=start_year,
        duration_years=duration_years,
    )


def create_increase_amt_exemption(
    exemption_increase: float = 25_000,
    start_year: int = 2026,
    duration_years: int = 10,
) -> AMTPolicy:
    """
    Create policy to increase AMT exemption levels.

    Args:
        exemption_increase: Dollar increase in exemption (e.g., $25,000)
        start_year: First year of policy
        duration_years: Duration

    Returns:
        AMTPolicy for exemption increase
    """
    # Rough estimate: each $25K exemption increase reduces affected taxpayers
    # and revenue by roughly 15%
    reduction_pct = 0.15 * (exemption_increase / 25_000)

    # Baseline post-TCJA revenue ~$39B/year (average)
    annual_cost = -39.3 * reduction_pct

    return AMTPolicy(
        name=f"AMT Exemption +${exemption_increase/1000:.0f}K",
        description=f"Increase AMT exemption by ${exemption_increase:,.0f}",
        policy_type=PolicyType.INCOME_TAX,
        amt_type=AMTType.INDIVIDUAL,
        exemption_change=exemption_increase,
        annual_revenue_change_billions=annual_cost,
        start_year=start_year,
        duration_years=duration_years,
    )


def create_amt_rate_change(
    rate_change: float,
    start_year: int = 2025,
    duration_years: int = 10,
) -> AMTPolicy:
    """
    Create AMT rate change policy.

    Args:
        rate_change: Change in rate (e.g., -0.02 for 2pp cut)
        start_year: First year
        duration_years: Duration

    Returns:
        AMTPolicy for rate change
    """
    # Revenue effect proportional to rate change
    # Current combined rate ~27% average, baseline ~$40B/year post-TCJA
    avg_rate = (AMT_RATES["first_tier"] + AMT_RATES["second_tier"]) / 2
    baseline_revenue = 39.3  # Average annual post-TCJA
    pct_change = rate_change / avg_rate
    annual_change = baseline_revenue * pct_change

    direction = "increase" if rate_change > 0 else "decrease"
    new_first = AMT_RATES["first_tier"] + rate_change
    new_second = AMT_RATES["second_tier"] + rate_change

    return AMTPolicy(
        name=f"AMT Rate {direction.title()} {abs(rate_change)*100:.0f}pp",
        description=f"Change AMT rates to {new_first*100:.0f}%/{new_second*100:.0f}%",
        policy_type=PolicyType.INCOME_TAX,
        amt_type=AMTType.INDIVIDUAL,
        rate_change=rate_change,
        annual_revenue_change_billions=annual_change,
        start_year=start_year,
        duration_years=duration_years,
    )


# =============================================================================
# VALIDATION SCENARIOS
# =============================================================================

AMT_VALIDATION_SCENARIOS = {
    "extend_tcja_amt": {
        "description": "Extend TCJA AMT relief",
        "policy_factory": "create_extend_tcja_amt_relief",
        "expected_10yr": 450.0,  # Cost (increases deficit)
        "source": "JCT/CBO",
        "notes": "Keep higher exemptions instead of sunset to pre-TCJA levels",
    },
    "repeal_individual_amt": {
        "description": "Repeal individual AMT (post-2025)",
        "policy_factory": "create_repeal_individual_amt",
        "kwargs": {"start_year": 2026},
        "expected_10yr": 450.0,  # Cost (lost revenue)
        "source": "CBO baseline",
        "notes": "Eliminate all individual AMT after TCJA expires",
    },
    "repeal_corporate_amt": {
        "description": "Repeal corporate AMT (CAMT)",
        "policy_factory": "create_repeal_corporate_amt",
        "expected_10yr": 220.0,  # Cost
        "source": "CBO",
        "notes": "Repeal 15% book minimum tax from IRA 2022",
    },
}


def estimate_amt_revenue(policy: AMTPolicy) -> dict:
    """
    Estimate total revenue effect of an AMT policy.

    Returns dict with:
        - annual_static: Average annual static effect
        - ten_year_static: Total 10-year static effect
        - behavioral_offset: Total behavioral offset
        - net_effect: Final effect after behavioral response
    """
    annual_static = policy.estimate_static_revenue_effect(0)
    behavioral = policy.estimate_behavioral_offset(annual_static)

    # Apply growth (~3%/year for income growth)
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
