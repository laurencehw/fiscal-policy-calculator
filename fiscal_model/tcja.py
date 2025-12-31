"""
TCJA Extension Scoring Module

Models the cost of extending the Tax Cuts and Jobs Act (TCJA) of 2017 provisions
that are scheduled to sunset after 2025.

Key TCJA Individual Provisions (sunsetting 2026):
1. Individual rate cuts (10/12/22/24/32/35/37% vs pre-TCJA 10/15/25/28/33/35/39.6%)
2. Doubled standard deduction (~$27,700 MFJ vs ~$13,000 pre-TCJA)
3. Eliminated personal exemptions (~$4,150 per person)
4. $10,000 SALT cap (vs unlimited pre-TCJA)
5. Expanded Child Tax Credit ($2,000 vs $1,000)
6. 20% pass-through deduction (Section 199A)
7. Doubled estate tax exemption (~$12.92M vs ~$5.49M)
8. Increased AMT exemptions

References:
- CBO (May 2024): $4.6T cost over FY2025-2034 for full extension
- JCT (2017): Original TCJA score: $1.456T over FY2018-2027
- CBO Budget Options: https://www.cbo.gov/publication/59710
"""

from dataclasses import dataclass, field
from typing import Optional, Literal
import numpy as np

from .policies import TaxPolicy, PolicyPackage, PolicyType


@dataclass
class TCJAComponent:
    """
    Individual component of TCJA extension.

    Each component represents a specific provision with its
    estimated 10-year cost if extended.
    """
    name: str
    description: str
    ten_year_cost_billions: float  # Positive = increases deficit
    annual_cost_billions: Optional[float] = None  # First year cost
    growth_rate: float = 0.03  # Annual cost growth rate (nominal)

    # For validation
    source: str = "JCT/CBO"
    uncertainty_pct: float = 0.15  # Uncertainty range


# =============================================================================
# TCJA COMPONENT ESTIMATES
# =============================================================================

# Individual rate bracket changes
# Pre-TCJA: 10/15/25/28/33/35/39.6%
# TCJA: 10/12/22/24/32/35/37%
TCJA_RATE_CUTS = TCJAComponent(
    name="Individual Rate Cuts",
    description="Lower marginal tax rates across all brackets (12% vs 15%, 22% vs 25%, etc.)",
    ten_year_cost_billions=1800.0,  # Largest single component
    annual_cost_billions=150.0,
    growth_rate=0.035,
    source="CBO/JCT extrapolation",
    uncertainty_pct=0.12,
)

# Doubled standard deduction
# 2024: $29,200 MFJ, $14,600 single (TCJA) vs ~$13,000 MFJ pre-TCJA
TCJA_STANDARD_DEDUCTION = TCJAComponent(
    name="Doubled Standard Deduction",
    description="Nearly doubled standard deduction ($29,200 vs ~$14,600 MFJ)",
    ten_year_cost_billions=720.0,
    annual_cost_billions=60.0,
    growth_rate=0.03,
    source="JCT",
    uncertainty_pct=0.10,
)

# Personal exemption elimination (REVENUE GAIN - offsets above)
# Pre-TCJA: ~$4,150 per person × avg household size
# This REDUCES the cost of TCJA extension
TCJA_EXEMPTION_ELIMINATION = TCJAComponent(
    name="Personal Exemption Elimination",
    description="Elimination of $4,150 personal exemptions (OFFSETS other costs)",
    ten_year_cost_billions=-650.0,  # Negative = revenue gain
    annual_cost_billions=-55.0,
    growth_rate=0.03,
    source="JCT",
    uncertainty_pct=0.08,
)

# $10,000 SALT cap (REVENUE GAIN)
# Caps deduction for state/local taxes at $10,000
# This REDUCES the cost of TCJA extension
TCJA_SALT_CAP = TCJAComponent(
    name="SALT Deduction Cap",
    description="$10,000 cap on state and local tax deductions (OFFSETS other costs)",
    ten_year_cost_billions=-1100.0,  # Negative = revenue gain
    annual_cost_billions=-90.0,
    growth_rate=0.04,  # High-tax states growing faster
    source="JCT",
    uncertainty_pct=0.15,
)

# Child Tax Credit expansion
# TCJA: $2,000 per child, $1,400 refundable
# Pre-TCJA: $1,000 per child, less refundable
TCJA_CTC_EXPANSION = TCJAComponent(
    name="Child Tax Credit Expansion",
    description="Expanded CTC from $1,000 to $2,000 per child, higher refundability",
    ten_year_cost_billions=550.0,
    annual_cost_billions=50.0,
    growth_rate=0.02,
    source="JCT",
    uncertainty_pct=0.12,
)

# Section 199A pass-through deduction (20% QBI deduction)
# New deduction for pass-through business income
TCJA_PASSTHROUGH_DEDUCTION = TCJAComponent(
    name="Pass-Through Deduction (199A)",
    description="20% deduction for qualified business income from pass-throughs",
    ten_year_cost_billions=700.0,
    annual_cost_billions=60.0,
    growth_rate=0.04,  # Growing as more businesses use it
    source="JCT",
    uncertainty_pct=0.20,  # Higher uncertainty due to behavioral response
)

# Estate tax exemption doubling
# TCJA: ~$12.92M per person (2023)
# Pre-TCJA: ~$5.49M adjusted
TCJA_ESTATE_EXEMPTION = TCJAComponent(
    name="Estate Tax Exemption Increase",
    description="Doubled estate tax exemption (~$12.9M vs ~$5.5M per person)",
    ten_year_cost_billions=130.0,
    annual_cost_billions=10.0,
    growth_rate=0.05,  # Indexed to inflation + wealth growth
    source="JCT",
    uncertainty_pct=0.25,  # High uncertainty for estate tax
)

# AMT exemption increase
# Reduced number of taxpayers subject to AMT
TCJA_AMT_RELIEF = TCJAComponent(
    name="AMT Exemption Increase",
    description="Higher AMT exemptions, fewer taxpayers subject to AMT",
    ten_year_cost_billions=450.0,
    annual_cost_billions=40.0,
    growth_rate=0.03,
    source="JCT",
    uncertainty_pct=0.15,
)


# All components
TCJA_COMPONENTS = [
    TCJA_RATE_CUTS,
    TCJA_STANDARD_DEDUCTION,
    TCJA_EXEMPTION_ELIMINATION,  # Offset (negative)
    TCJA_SALT_CAP,  # Offset (negative)
    TCJA_CTC_EXPANSION,
    TCJA_PASSTHROUGH_DEDUCTION,
    TCJA_ESTATE_EXEMPTION,
    TCJA_AMT_RELIEF,
]


def get_tcja_component_summary() -> dict:
    """
    Get summary of all TCJA components.

    Returns dict with:
    - components: List of component details
    - gross_costs: Total costs before offsets
    - offsets: Revenue gains from SALT cap and exemption elimination
    - net_cost: Net 10-year cost
    """
    gross_costs = sum(c.ten_year_cost_billions for c in TCJA_COMPONENTS if c.ten_year_cost_billions > 0)
    offsets = sum(c.ten_year_cost_billions for c in TCJA_COMPONENTS if c.ten_year_cost_billions < 0)
    net_cost = sum(c.ten_year_cost_billions for c in TCJA_COMPONENTS)

    return {
        "components": [
            {
                "name": c.name,
                "ten_year_cost": c.ten_year_cost_billions,
                "annual_cost": c.annual_cost_billions,
                "is_offset": c.ten_year_cost_billions < 0,
            }
            for c in TCJA_COMPONENTS
        ],
        "gross_costs": gross_costs,
        "offsets": offsets,
        "net_cost": net_cost,
        "cbo_target": 4600.0,
        "calibration_factor": 4600.0 / net_cost if net_cost != 0 else 1.0,
    }


@dataclass
class TCJAExtensionPolicy(TaxPolicy):
    """
    Policy for extending TCJA provisions beyond 2025 sunset.

    This models the COST of extension relative to current-law baseline
    where TCJA provisions expire.

    Scoring methodology:
    - Uses CBO's $4.6T 10-year estimate as calibration target
    - Breaks down into components for analysis
    - Allows selective extension (e.g., extend rate cuts but not SALT cap)
    """

    # Which components to extend
    extend_rate_cuts: bool = True
    extend_standard_deduction: bool = True
    keep_exemption_elimination: bool = True  # Keep = maintain TCJA (no exemptions)
    keep_salt_cap: bool = True  # Keep = maintain TCJA ($10K cap)
    extend_ctc_expansion: bool = True
    extend_passthrough_deduction: bool = True
    extend_estate_exemption: bool = True
    extend_amt_relief: bool = True

    # Calibration to CBO estimate
    # Fixed calibration factor based on FULL extension matching CBO $4.6T
    # Raw component total for full extension: ~$2,600B
    # CBO target: $4,600B
    # Calibration factor: 4600 / 2600 = 1.77
    calibration_factor: float = 1.77  # Fixed multiplier to match CBO

    # Dynamic scoring adjustment (CBO estimates ~10% offset from growth)
    dynamic_offset_pct: float = 0.0  # Set >0 for dynamic scoring

    def _get_raw_10yr_cost(self) -> float:
        """Get raw 10-year cost from components (before calibration)."""
        total = 0.0

        if self.extend_rate_cuts:
            total += TCJA_RATE_CUTS.ten_year_cost_billions
        if self.extend_standard_deduction:
            total += TCJA_STANDARD_DEDUCTION.ten_year_cost_billions
        if self.keep_exemption_elimination:
            total += TCJA_EXEMPTION_ELIMINATION.ten_year_cost_billions
        if self.keep_salt_cap:
            total += TCJA_SALT_CAP.ten_year_cost_billions
        if self.extend_ctc_expansion:
            total += TCJA_CTC_EXPANSION.ten_year_cost_billions
        if self.extend_passthrough_deduction:
            total += TCJA_PASSTHROUGH_DEDUCTION.ten_year_cost_billions
        if self.extend_estate_exemption:
            total += TCJA_ESTATE_EXEMPTION.ten_year_cost_billions
        if self.extend_amt_relief:
            total += TCJA_AMT_RELIEF.ten_year_cost_billions

        return total

    def _get_annual_cost(self, year_index: int) -> float:
        """
        Get annual cost for a given year (0-indexed from start_year).

        Costs grow over time due to:
        - Income growth pushing more people into higher brackets
        - Population growth
        - Inflation indexing
        """
        total = 0.0

        components = [
            (self.extend_rate_cuts, TCJA_RATE_CUTS),
            (self.extend_standard_deduction, TCJA_STANDARD_DEDUCTION),
            (self.keep_exemption_elimination, TCJA_EXEMPTION_ELIMINATION),
            (self.keep_salt_cap, TCJA_SALT_CAP),
            (self.extend_ctc_expansion, TCJA_CTC_EXPANSION),
            (self.extend_passthrough_deduction, TCJA_PASSTHROUGH_DEDUCTION),
            (self.extend_estate_exemption, TCJA_ESTATE_EXEMPTION),
            (self.extend_amt_relief, TCJA_AMT_RELIEF),
        ]

        for include, component in components:
            if include and component.annual_cost_billions is not None:
                # Apply growth rate
                annual = component.annual_cost_billions * ((1 + component.growth_rate) ** year_index)
                total += annual

        # Apply calibration factor
        total *= self.calibration_factor

        # Apply dynamic offset if specified
        total *= (1 - self.dynamic_offset_pct)

        return total

    def estimate_static_revenue_effect(self, baseline_revenue: float,
                                       use_real_data: bool = True) -> float:
        """
        Estimate annual revenue effect for TCJA extension.

        TCJA extension is a COST (reduces revenue), so returns negative value.

        Note: This is called per-year by the scorer with no year index,
        so we return the average annual cost.
        """
        _ = baseline_revenue  # Not used for TCJA; uses component-based approach
        _ = use_real_data

        # Return negative of average annual cost (extension costs money)
        total_10yr = self._get_raw_10yr_cost() * self.calibration_factor * (1 - self.dynamic_offset_pct)
        return -total_10yr / 10

    def estimate_behavioral_offset(self, static_effect: float) -> float:
        """
        TCJA extension behavioral offset is embedded in the calibration.

        CBO's $4.6T estimate already incorporates behavioral responses.
        We don't apply additional ETI offset to avoid double-counting.
        """
        return 0.0

    def get_component_breakdown(self) -> dict:
        """
        Get detailed breakdown by component.

        Returns dict with annual and 10-year costs per component.
        """
        breakdown = {}

        components = [
            ("rate_cuts", self.extend_rate_cuts, TCJA_RATE_CUTS),
            ("standard_deduction", self.extend_standard_deduction, TCJA_STANDARD_DEDUCTION),
            ("exemption_elimination", self.keep_exemption_elimination, TCJA_EXEMPTION_ELIMINATION),
            ("salt_cap", self.keep_salt_cap, TCJA_SALT_CAP),
            ("ctc_expansion", self.extend_ctc_expansion, TCJA_CTC_EXPANSION),
            ("passthrough_deduction", self.extend_passthrough_deduction, TCJA_PASSTHROUGH_DEDUCTION),
            ("estate_exemption", self.extend_estate_exemption, TCJA_ESTATE_EXEMPTION),
            ("amt_relief", self.extend_amt_relief, TCJA_AMT_RELIEF),
        ]

        for key, include, component in components:
            if include:
                calibrated_10yr = component.ten_year_cost_billions * self.calibration_factor
                calibrated_annual = (component.annual_cost_billions or 0) * self.calibration_factor
                breakdown[key] = {
                    "name": component.name,
                    "description": component.description,
                    "ten_year_cost": calibrated_10yr,
                    "annual_cost": calibrated_annual,
                    "is_offset": component.ten_year_cost_billions < 0,
                }

        return breakdown


def create_tcja_extension(
    extend_all: bool = True,
    keep_salt_cap: bool = True,
    extend_rate_cuts: bool = True,
    extend_standard_deduction: bool = True,
    keep_exemption_elimination: bool = True,
    extend_passthrough: bool = True,
    extend_ctc: bool = True,
    extend_estate: bool = True,
    extend_amt: bool = True,
    start_year: int = 2026,
    duration_years: int = 10,
) -> TCJAExtensionPolicy:
    """
    Create a TCJA extension policy.

    Args:
        extend_all: If True, extend all TCJA provisions (overrides individual flags)
        keep_salt_cap: If False, repeal SALT cap (COSTS more)
        extend_rate_cuts: Whether to extend rate bracket changes
        extend_standard_deduction: Whether to extend doubled standard deduction
        keep_exemption_elimination: Whether to maintain personal exemption elimination
        extend_passthrough: Whether to extend 199A deduction
        extend_ctc: Whether to extend CTC expansion
        extend_estate: Whether to extend estate tax exemption increase
        extend_amt: Whether to extend AMT relief
        start_year: Year extension takes effect (default 2026)
        duration_years: Duration of extension

    Returns:
        TCJAExtensionPolicy configured per parameters
    """
    if extend_all:
        return TCJAExtensionPolicy(
            name="TCJA Full Extension",
            description="Extend all TCJA individual provisions beyond 2025 sunset",
            policy_type=PolicyType.INCOME_TAX,
            start_year=start_year,
            duration_years=duration_years,
            extend_rate_cuts=True,
            extend_standard_deduction=True,
            keep_exemption_elimination=True,
            keep_salt_cap=keep_salt_cap,
            extend_ctc_expansion=True,
            extend_passthrough_deduction=True,
            extend_estate_exemption=True,
            extend_amt_relief=True,
        )
    else:
        return TCJAExtensionPolicy(
            name="TCJA Partial Extension",
            description="Extend selected TCJA provisions",
            policy_type=PolicyType.INCOME_TAX,
            start_year=start_year,
            duration_years=duration_years,
            extend_rate_cuts=extend_rate_cuts,
            extend_standard_deduction=extend_standard_deduction,
            keep_exemption_elimination=keep_exemption_elimination,
            keep_salt_cap=keep_salt_cap,
            extend_ctc_expansion=extend_ctc,
            extend_passthrough_deduction=extend_passthrough,
            extend_estate_exemption=extend_estate,
            extend_amt_relief=extend_amt,
        )


def create_tcja_repeal_salt_cap() -> TCJAExtensionPolicy:
    """
    Create TCJA extension WITHOUT the SALT cap.

    Popular bipartisan proposal to extend TCJA but repeal the $10K SALT cap.
    This INCREASES the cost of extension by ~$1.1T over 10 years.
    """
    policy = create_tcja_extension(extend_all=True, keep_salt_cap=False)
    policy.name = "TCJA Extension (No SALT Cap)"
    policy.description = "Extend TCJA provisions but repeal $10K SALT cap"
    return policy


def estimate_tcja_extension_cost(
    include_salt_cap: bool = True,
    include_passthrough: bool = True,
    dynamic: bool = False,
) -> dict:
    """
    Quick estimate of TCJA extension cost.

    Args:
        include_salt_cap: Keep SALT cap (reduces cost) or repeal (increases cost)
        include_passthrough: Include 199A pass-through deduction
        dynamic: Apply dynamic scoring offset (~10% reduction)

    Returns:
        Dict with 10-year cost and component breakdown
    """
    policy = TCJAExtensionPolicy(
        name="TCJA Extension",
        description="TCJA extension estimate",
        policy_type=PolicyType.INCOME_TAX,
        keep_salt_cap=include_salt_cap,
        extend_passthrough_deduction=include_passthrough,
        dynamic_offset_pct=0.10 if dynamic else 0.0,
    )

    total = policy._get_raw_10yr_cost() * policy.calibration_factor
    if dynamic:
        total *= 0.90  # 10% dynamic offset

    return {
        "ten_year_cost": total,
        "annual_average": total / 10,
        "breakdown": policy.get_component_breakdown(),
        "includes_salt_cap": include_salt_cap,
        "includes_passthrough": include_passthrough,
        "is_dynamic": dynamic,
        "cbo_target": 4600.0,
        "vs_cbo_pct": (total - 4600.0) / 4600.0 * 100 if include_salt_cap and include_passthrough else None,
    }
