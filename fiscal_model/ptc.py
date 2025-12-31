"""
Premium Tax Credit (ACA) Module

Models Affordable Care Act premium subsidies including:
- Enhanced PTCs (ARPA 2021 / IRA 2022 extension through 2025)
- Original ACA structure (post-2025 if not extended)
- Income eligibility and premium cap calculations
- Coverage effects

Key data sources:
- CBO: Budget and Economic Outlook, Health Insurance projections
- HHS: Marketplace enrollment data
- KFF: Premium subsidy calculations

Current Law (Enhanced PTCs through 2025):
- Income range: 100%+ FPL (no upper limit under enhanced)
- Premium cap: 0-8.5% of income based on FPL
- Enrollees: ~22M on marketplace (~19M receiving PTCs)
- Average subsidy: ~$7,000/year per subsidized enrollee

After 2025 sunset (Original ACA):
- Income range: 100-400% FPL
- Premium cap: 2%-9.86% of income at 400% FPL
- ~4 million projected to lose coverage
- Premium increase: ~114% avg (~$1,016/year)

CBO Estimates:
- Permanent extension of enhanced PTCs: $350B over 2026-2035
- IRA extension (2023-2025): ~$64B over 10 years
- Original ACA baseline: ~$95B/year in credits
"""

from dataclasses import dataclass, field
from typing import Optional, Literal
from enum import Enum
import numpy as np

from .policies import Policy, TaxPolicy, PolicyType


class PTCScenario(Enum):
    """PTC policy scenarios."""
    EXTEND_ENHANCED = "extend_enhanced"  # Extend ARPA/IRA enhanced credits
    ORIGINAL_ACA = "original_aca"  # Let enhanced expire, return to original
    PERMANENT_ENHANCED = "permanent_enhanced"  # Make enhanced credits permanent
    REPEAL_PTC = "repeal_ptc"  # Eliminate PTCs entirely


# =============================================================================
# FEDERAL POVERTY LEVEL GUIDELINES (2025)
# =============================================================================

# 2025 Federal Poverty Level by family size (contiguous 48 states)
FPL_2025 = {
    1: 15_650,
    2: 21_150,
    3: 26_650,
    4: 32_150,
    5: 37_650,
    6: 43_150,
    7: 48_650,
    8: 54_150,
}

# Add $5,500 per additional person above 8
def get_fpl(family_size: int, year: int = 2025) -> float:
    """Get Federal Poverty Level for family size."""
    base_fpl = FPL_2025.get(min(family_size, 8), FPL_2025[8])
    if family_size > 8:
        base_fpl += (family_size - 8) * 5_500
    # Adjust for year (FPL grows ~3%/year)
    years_diff = year - 2025
    return base_fpl * (1.03 ** years_diff)


# =============================================================================
# PREMIUM CAP SCHEDULES
# =============================================================================

# Enhanced PTC premium caps (ARPA/IRA through 2025)
ENHANCED_PTC_CAPS = {
    # FPL%: (min_cap%, max_cap%)
    # Below 150% FPL: 0% of income
    (0, 150): (0.0, 0.0),
    # 150-200% FPL: 0-2% of income
    (150, 200): (0.0, 0.02),
    # 200-250% FPL: 2-4% of income
    (200, 250): (0.02, 0.04),
    # 250-300% FPL: 4-6% of income
    (250, 300): (0.04, 0.06),
    # 300-400% FPL: 6-8.5% of income
    (300, 400): (0.06, 0.085),
    # Above 400% FPL (enhanced): 8.5% of income
    (400, 9999): (0.085, 0.085),
}

# Original ACA premium caps (pre-ARPA / post-2025 if not extended)
ORIGINAL_ACA_CAPS = {
    # FPL%: (min_cap%, max_cap%)
    (100, 133): (0.0206, 0.0206),
    (133, 150): (0.0306, 0.0406),
    (150, 200): (0.0406, 0.0644),
    (200, 250): (0.0644, 0.0806),
    (250, 300): (0.0806, 0.0961),
    (300, 400): (0.0961, 0.0986),
    # Above 400% FPL: No subsidy under original ACA
    (400, 9999): (1.0, 1.0),  # Full premium
}


# =============================================================================
# BASELINE DATA
# =============================================================================

# Marketplace enrollment data
MARKETPLACE_DATA = {
    # Current enrollment (2025 estimates)
    "total_enrollees_millions": 22.0,  # Total marketplace enrollees
    "receiving_ptc_millions": 19.0,  # Enrollees receiving PTCs
    "receiving_csr_millions": 12.0,  # Also receiving Cost-Sharing Reductions

    # Average subsidy values
    "avg_subsidy_enhanced": 7_000,  # Average annual subsidy under enhanced
    "avg_subsidy_original": 5_500,  # Average under original ACA
    "avg_benchmark_premium": 12_000,  # Average benchmark (second-lowest silver)

    # Distribution by FPL
    "below_150_fpl_pct": 0.35,  # 35% below 150% FPL
    "150_200_fpl_pct": 0.20,
    "200_300_fpl_pct": 0.25,
    "300_400_fpl_pct": 0.12,
    "above_400_fpl_pct": 0.08,  # Only eligible under enhanced

    # Coverage loss if enhanced expires
    "coverage_loss_millions": 4.0,  # CBO estimate
    "uninsured_increase_millions": 14.0,  # By 2034 if no extension
}

# Baseline credit costs (billions per year)
BASELINE_PTC_COSTS = {
    "enhanced_annual": 95.0,  # Enhanced PTC annual cost
    "original_aca_annual": 60.0,  # Original ACA annual cost
    "csr_annual": 15.0,  # Cost-Sharing Reductions
}

# CBO official estimates
CBO_PTC_ESTIMATES = {
    # Cost of extending enhanced PTCs permanently
    "extend_enhanced_10yr": 350.0,  # $350B over 2026-2035 (CBO 2024)
    "extend_enhanced_annual": 30.5,  # Calibrated average annual

    # IRA 3-year extension (2023-2025)
    "ira_extension_10yr": 64.0,  # $64B over 10 years

    # Baseline enhanced PTC spending
    "baseline_enhanced_annual": 95.0,  # ~$95B/year under enhanced

    # Baseline original ACA spending (if enhanced expires)
    "baseline_original_annual": 60.0,  # ~$60B/year under original

    # Full repeal savings (loses all PTC spending)
    "repeal_ptc_10yr": -1100.0,  # Would save ~$1.1T but lose coverage
}


@dataclass
class PremiumTaxCreditPolicy(TaxPolicy):
    """
    Premium Tax Credit policy modeling ACA marketplace subsidies.

    Models premium subsidy changes including:
    - Enhanced vs original ACA credit structure
    - Income eligibility thresholds
    - Premium cap changes
    - Coverage effects

    Key parameters:
        scenario: Type of PTC policy change
        extend_enhanced: Extend enhanced PTCs past 2025
        make_permanent: Make enhanced PTCs permanent
        repeal_ptc: Eliminate PTCs entirely
        modify_premium_cap: Change premium cap percentages
        modify_income_limit: Change FPL eligibility limits
    """

    # Policy scenario
    scenario: PTCScenario = field(default=PTCScenario.EXTEND_ENHANCED)

    # Extension options
    extend_enhanced: bool = False  # Extend enhanced PTCs past 2025
    make_permanent: bool = False  # Make permanent (vs temporary extension)
    extension_years: int = 10  # Years to extend if not permanent

    # Repeal option
    repeal_ptc: bool = False  # Eliminate PTCs entirely

    # Premium cap modifications
    modify_premium_cap: bool = False
    new_premium_cap_max: Optional[float] = None  # New max cap (e.g., 0.085)
    premium_cap_change: float = 0.0  # Change to all caps

    # Income limit modifications
    modify_income_limit: bool = False
    new_upper_fpl_limit: Optional[float] = None  # New upper limit (e.g., 600% FPL)
    new_lower_fpl_limit: Optional[float] = None  # New lower limit

    # Behavioral parameters
    coverage_elasticity: float = 0.3  # Coverage response to subsidy changes
    take_up_rate: float = 0.85  # Eligible population that enrolls
    adverse_selection_factor: float = 0.1  # Premium spiral from losing healthy

    # Healthcare cost growth
    healthcare_growth_rate: float = 0.04  # 4%/year premium growth

    # Calibration
    annual_revenue_change_billions: Optional[float] = None

    def __post_init__(self):
        """Set default policy type."""
        if self.policy_type == PolicyType.INCOME_TAX:
            self.policy_type = PolicyType.TAX_CREDIT

    def get_premium_cap(
        self,
        fpl_percentage: float,
        use_enhanced: bool = True,
    ) -> float:
        """
        Get premium cap as percentage of income for given FPL level.

        Args:
            fpl_percentage: Household income as % of FPL (e.g., 250 = 250% FPL)
            use_enhanced: Use enhanced (ARPA/IRA) caps vs original ACA

        Returns:
            Premium cap as decimal (e.g., 0.085 = 8.5%)
        """
        caps = ENHANCED_PTC_CAPS if use_enhanced else ORIGINAL_ACA_CAPS

        for (low, high), (min_cap, max_cap) in caps.items():
            if low <= fpl_percentage < high:
                # Linear interpolation within bracket
                if high == low:
                    return min_cap
                bracket_pct = (fpl_percentage - low) / (high - low)
                return min_cap + bracket_pct * (max_cap - min_cap)

        # Above all brackets
        if use_enhanced:
            return 0.085  # Enhanced caps at 8.5%
        else:
            return 1.0  # No subsidy under original ACA above 400%

    def calculate_subsidy(
        self,
        income: float,
        family_size: int = 1,
        benchmark_premium: float = 12000.0,
        year: int = 2026,
        use_enhanced: bool = True,
    ) -> dict:
        """
        Calculate PTC subsidy for a household.

        Args:
            income: Household income
            family_size: Number of people in household
            benchmark_premium: Second-lowest silver plan premium
            year: Tax year
            use_enhanced: Use enhanced credit structure

        Returns:
            Dict with subsidy amount, premium cap, and expected contribution
        """
        fpl = get_fpl(family_size, year)
        fpl_pct = (income / fpl) * 100

        # Check eligibility
        if use_enhanced:
            eligible = fpl_pct >= 100  # No upper limit under enhanced
        else:
            eligible = 100 <= fpl_pct <= 400  # Original ACA limits

        if not eligible:
            return {
                "eligible": False,
                "fpl_percentage": fpl_pct,
                "premium_cap": 1.0,
                "expected_contribution": benchmark_premium,
                "subsidy": 0.0,
            }

        # Get premium cap
        premium_cap = self.get_premium_cap(fpl_pct, use_enhanced)

        # Apply policy modifications
        if self.modify_premium_cap and self.new_premium_cap_max is not None:
            premium_cap = min(premium_cap, self.new_premium_cap_max)
        premium_cap += self.premium_cap_change

        # Calculate expected contribution and subsidy
        expected_contribution = income * premium_cap
        subsidy = max(0, benchmark_premium - expected_contribution)

        return {
            "eligible": True,
            "fpl_percentage": fpl_pct,
            "premium_cap": premium_cap,
            "expected_contribution": expected_contribution,
            "subsidy": subsidy,
        }

    def estimate_coverage_effect(self) -> dict:
        """
        Estimate coverage effects of policy change.

        Returns:
            Dict with coverage gains/losses
        """
        if self.repeal_ptc:
            # Full repeal loses all subsidized coverage
            return {
                "coverage_change_millions": -MARKETPLACE_DATA["receiving_ptc_millions"],
                "uninsured_change_millions": MARKETPLACE_DATA["receiving_ptc_millions"] * 0.8,
            }

        if self.extend_enhanced or self.make_permanent:
            # Extending prevents coverage loss
            return {
                "coverage_change_millions": MARKETPLACE_DATA["coverage_loss_millions"],
                "uninsured_change_millions": -MARKETPLACE_DATA["coverage_loss_millions"],
            }

        # Letting enhanced expire (current law baseline)
        return {
            "coverage_change_millions": -MARKETPLACE_DATA["coverage_loss_millions"],
            "uninsured_change_millions": MARKETPLACE_DATA["coverage_loss_millions"],
        }

    def estimate_static_revenue_effect(
        self,
        baseline_revenue: float,
        use_real_data: bool = True,
    ) -> float:
        """
        Estimate static revenue effect of PTC policy change.

        For PTCs, revenue effect = change in outlays (negative = costs money).

        Args:
            baseline_revenue: Baseline revenue (not used)
            use_real_data: Whether to use detailed calculations

        Returns:
            Revenue change in billions (negative = cost increase)
        """
        if self.annual_revenue_change_billions is not None:
            return self.annual_revenue_change_billions

        if self.repeal_ptc:
            # Repealing PTCs saves all PTC spending
            return CBO_PTC_ESTIMATES["baseline_enhanced_annual"]

        if self.extend_enhanced or self.make_permanent:
            # Cost of extending enhanced PTCs
            # Difference between enhanced and original ACA baseline
            enhanced_cost = CBO_PTC_ESTIMATES["baseline_enhanced_annual"]
            original_cost = CBO_PTC_ESTIMATES["baseline_original_annual"]
            return -(enhanced_cost - original_cost)  # Additional cost

        # Premium cap modifications
        if self.modify_premium_cap and self.premium_cap_change != 0:
            # Lower caps = higher subsidies = more cost
            # Rough estimate: 1pp cap reduction = ~$10B/year
            return self.premium_cap_change * 1000  # Billions per 1pp

        return 0.0

    def estimate_behavioral_offset(self, static_effect: float) -> float:
        """
        Estimate behavioral response to PTC changes.

        Behavioral responses include:
        - Coverage changes (more/fewer insured)
        - Premium spiral effects (adverse selection)
        - Labor supply effects (subsidy cliff)

        Returns:
            Behavioral offset in billions
        """
        # Coverage effects affect healthcare costs elsewhere
        coverage_offset = abs(static_effect) * self.coverage_elasticity * 0.1

        # Adverse selection if coverage drops
        if static_effect > 0:  # Saving money = losing coverage
            adverse_selection = abs(static_effect) * self.adverse_selection_factor
        else:
            adverse_selection = 0.0

        total_offset = coverage_offset + adverse_selection

        # Direction: if saving money (cutting subsidies), costs go up elsewhere
        if static_effect > 0:
            return -total_offset  # Reduces savings
        else:
            return total_offset  # Reduces cost


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_extend_enhanced_ptc(
    start_year: int = 2026,
    duration_years: int = 10,
    make_permanent: bool = False,
) -> PremiumTaxCreditPolicy:
    """
    Create policy to extend enhanced PTCs beyond 2025.

    The enhanced PTCs from ARPA 2021 (extended by IRA 2022) expire end of 2025.
    This policy extends them to prevent premium spikes and coverage loss.

    CBO estimate: ~$350B over 2026-2035

    Args:
        start_year: First year of extension (2026 after current expiration)
        duration_years: Years to extend
        make_permanent: Whether to make permanent vs temporary

    Returns:
        PremiumTaxCreditPolicy for enhanced PTC extension
    """
    return PremiumTaxCreditPolicy(
        name="Extend Enhanced PTCs" + (" (Permanent)" if make_permanent else ""),
        description="Extend ARPA/IRA enhanced premium tax credits beyond 2025",
        policy_type=PolicyType.TAX_CREDIT,
        scenario=PTCScenario.EXTEND_ENHANCED,
        extend_enhanced=True,
        make_permanent=make_permanent,
        extension_years=duration_years,
        coverage_elasticity=0.0,  # Behavioral in calibration
        adverse_selection_factor=0.0,
        # Calibrated to CBO ~$350B over 10 years (with 4% healthcare growth)
        annual_revenue_change_billions=-30.5,
        start_year=start_year,
        duration_years=duration_years,
    )


def create_let_enhanced_expire() -> PremiumTaxCreditPolicy:
    """
    Create policy representing enhanced PTCs expiring (current law baseline).

    Under current law, enhanced PTCs expire end of 2025, reverting to
    original ACA structure:
    - 100-400% FPL eligibility only
    - Higher premium caps
    - ~4 million lose coverage

    This is the baseline for comparison - zero budget cost but coverage effects.
    """
    return PremiumTaxCreditPolicy(
        name="Let Enhanced PTCs Expire",
        description="Current law: enhanced PTCs expire end of 2025",
        policy_type=PolicyType.TAX_CREDIT,
        scenario=PTCScenario.ORIGINAL_ACA,
        extend_enhanced=False,
        make_permanent=False,
        coverage_elasticity=0.3,
        # No budget cost - this is the baseline
        annual_revenue_change_billions=0.0,
        start_year=2026,
        duration_years=10,
    )


def create_repeal_ptc(
    start_year: int = 2026,
    duration_years: int = 10,
) -> PremiumTaxCreditPolicy:
    """
    Create policy to repeal PTCs entirely.

    This would eliminate all ACA premium subsidies, saving ~$95B/year
    but causing ~19 million to lose subsidized coverage.

    CBO estimate: Saves ~$1.1T over 10 years but major coverage loss.
    """
    return PremiumTaxCreditPolicy(
        name="Repeal Premium Tax Credits",
        description="Eliminate ACA premium subsidies entirely",
        policy_type=PolicyType.TAX_CREDIT,
        scenario=PTCScenario.REPEAL_PTC,
        repeal_ptc=True,
        coverage_elasticity=0.0,  # Not modeling coverage offset
        # Calibrated: ~$1.1T savings over 10 years (with growth)
        annual_revenue_change_billions=83.0,  # Saves money
        start_year=start_year,
        duration_years=duration_years,
    )


def create_expand_ptc_eligibility(
    new_upper_limit: float = 600,  # 600% FPL
    start_year: int = 2026,
    duration_years: int = 10,
) -> PremiumTaxCreditPolicy:
    """
    Create policy to expand PTC eligibility above 400% FPL.

    The enhanced PTCs already extend above 400% FPL with 8.5% cap.
    This makes that expansion explicit/permanent and could go further.

    Args:
        new_upper_limit: New FPL % limit (e.g., 600 = 600% FPL)
        start_year: First year
        duration_years: Duration

    Returns:
        PremiumTaxCreditPolicy for eligibility expansion
    """
    # Estimate cost: each 100% FPL expansion adds ~1M enrollees at ~$3K avg
    additional_fpl = new_upper_limit - 400
    additional_enrollees = (additional_fpl / 100) * 1.0  # ~1M per 100% FPL
    additional_cost = additional_enrollees * 3.0  # ~$3B per million

    return PremiumTaxCreditPolicy(
        name=f"Expand PTC to {new_upper_limit:.0f}% FPL",
        description=f"Extend PTC eligibility to {new_upper_limit:.0f}% of Federal Poverty Level",
        policy_type=PolicyType.TAX_CREDIT,
        scenario=PTCScenario.EXTEND_ENHANCED,
        extend_enhanced=True,
        modify_income_limit=True,
        new_upper_fpl_limit=new_upper_limit,
        annual_revenue_change_billions=-additional_cost - 30.5,  # Plus base extension
        start_year=start_year,
        duration_years=duration_years,
    )


def create_lower_premium_cap(
    new_max_cap: float = 0.05,  # 5% of income
    start_year: int = 2026,
    duration_years: int = 10,
) -> PremiumTaxCreditPolicy:
    """
    Create policy to lower the maximum premium cap.

    Current enhanced cap is 8.5% of income. Lowering increases subsidies.

    Args:
        new_max_cap: New maximum premium cap (e.g., 0.05 = 5%)
        start_year: First year
        duration_years: Duration

    Returns:
        PremiumTaxCreditPolicy for lower premium cap
    """
    # Estimate cost: each 1pp reduction adds ~$10B/year
    cap_reduction = 0.085 - new_max_cap
    additional_cost = cap_reduction * 100 * 10  # $10B per percentage point

    return PremiumTaxCreditPolicy(
        name=f"Lower Premium Cap to {new_max_cap*100:.0f}%",
        description=f"Reduce maximum premium cap from 8.5% to {new_max_cap*100:.0f}% of income",
        policy_type=PolicyType.TAX_CREDIT,
        scenario=PTCScenario.EXTEND_ENHANCED,
        extend_enhanced=True,
        modify_premium_cap=True,
        new_premium_cap_max=new_max_cap,
        annual_revenue_change_billions=-30.5 - additional_cost,  # Base + additional
        start_year=start_year,
        duration_years=duration_years,
    )


# =============================================================================
# VALIDATION SCENARIOS
# =============================================================================

PTC_VALIDATION_SCENARIOS = {
    "extend_enhanced_ptc": {
        "description": "Extend enhanced PTCs (ARPA/IRA)",
        "policy_factory": "create_extend_enhanced_ptc",
        "expected_10yr": 350.0,  # Cost (increases deficit)
        "source": "CBO 2024",
        "notes": "Extend subsidies beyond 2025 sunset",
    },
    "repeal_ptc": {
        "description": "Repeal premium tax credits",
        "policy_factory": "create_repeal_ptc",
        "expected_10yr": -1100.0,  # Savings (reduces deficit)
        "source": "CBO estimate",
        "notes": "Eliminate all ACA subsidies - major coverage loss",
    },
}


def estimate_ptc_cost(policy: PremiumTaxCreditPolicy) -> dict:
    """
    Estimate total cost of a PTC policy over 10 years.

    Returns dict with:
        - annual_cost: Average annual cost
        - ten_year_cost: Total 10-year cost
        - coverage_effect: Coverage change (millions)
        - behavioral_offset: Behavioral adjustment
    """
    annual_static = policy.estimate_static_revenue_effect(0)
    behavioral = policy.estimate_behavioral_offset(annual_static)
    coverage = policy.estimate_coverage_effect()

    # Apply healthcare growth (~4%/year)
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
        "coverage_change_millions": coverage["coverage_change_millions"],
    }
