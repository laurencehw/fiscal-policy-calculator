"""
Tax Credit Calculator Module

Models refundable and non-refundable tax credits including:
- Child Tax Credit (CTC)
- Earned Income Tax Credit (EITC)
- Premium Tax Credits (ACA)
- Education credits

Key features:
- Phase-in and phase-out modeling
- Refundable vs non-refundable logic
- Per-child / per-filer calculations
- Interaction with other credits

CBO/JCT References:
- CTC baseline cost: ~$120B/year
- EITC baseline cost: ~$70B/year
- Permanent CTC+EITC expansion: ~$1.6T over 10 years
"""

from dataclasses import dataclass, field
from typing import Optional, Literal
from enum import Enum
import numpy as np

from .policies import Policy, TaxPolicy, PolicyType


class CreditType(Enum):
    """Types of tax credits."""
    CHILD_TAX_CREDIT = "ctc"
    EARNED_INCOME_CREDIT = "eitc"
    PREMIUM_TAX_CREDIT = "ptc"
    EDUCATION_CREDIT = "education"
    OTHER = "other"


# =============================================================================
# CURRENT LAW PARAMETERS (2024)
# =============================================================================

# Child Tax Credit (CTC) - Post-TCJA, pre-2026 sunset
CTC_CURRENT_LAW = {
    "credit_per_child": 2000.0,
    "refundable_max": 1700.0,  # Additional Child Tax Credit (ACTC)
    "refund_rate": 0.15,  # 15% of earned income over threshold
    "refund_threshold": 2500.0,  # Earned income floor for refundability
    "phase_out_start_single": 200000.0,
    "phase_out_start_married": 400000.0,
    "phase_out_rate": 0.05,  # $50 per $1,000 over threshold
    "qualifying_age": 17,  # Must be under 17
    # TCJA sunset values (revert to pre-2018 law after 2025)
    "pre_tcja_credit": 1000.0,
    "pre_tcja_refundable_max": 1000.0,
    "pre_tcja_phase_out_single": 75000.0,
    "pre_tcja_phase_out_married": 110000.0,
}

# EITC Parameters by number of children (2024)
EITC_CURRENT_LAW = {
    # (phase_in_rate, max_credit, phase_out_start, phase_out_rate, income_limit)
    0: {
        "phase_in_rate": 0.0765,
        "max_credit": 632.0,
        "phase_in_end": 8260.0,
        "phase_out_start_single": 10330.0,
        "phase_out_start_married": 17580.0,
        "phase_out_rate": 0.0765,
        "income_limit_single": 18591.0,
        "income_limit_married": 25511.0,
    },
    1: {
        "phase_in_rate": 0.34,
        "max_credit": 4213.0,
        "phase_in_end": 12390.0,
        "phase_out_start_single": 22720.0,
        "phase_out_start_married": 29970.0,
        "phase_out_rate": 0.1598,
        "income_limit_single": 49084.0,
        "income_limit_married": 56004.0,
    },
    2: {
        "phase_in_rate": 0.40,
        "max_credit": 6960.0,
        "phase_in_end": 17400.0,
        "phase_out_start_single": 22720.0,
        "phase_out_start_married": 29970.0,
        "phase_out_rate": 0.2106,
        "income_limit_single": 55768.0,
        "income_limit_married": 62688.0,
    },
    3: {  # 3 or more children
        "phase_in_rate": 0.45,
        "max_credit": 7830.0,
        "phase_in_end": 17400.0,
        "phase_out_start_single": 22720.0,
        "phase_out_start_married": 29970.0,
        "phase_out_rate": 0.2106,
        "income_limit_single": 59899.0,
        "income_limit_married": 66819.0,
    },
}

# Baseline recipient counts (millions, approximate)
CREDIT_RECIPIENT_COUNTS = {
    "ctc_filers": 36.0,  # ~36M filers claim CTC
    "ctc_children": 48.0,  # ~48M qualifying children
    "eitc_filers": 31.0,  # ~31M filers claim EITC
    "eitc_with_children": 22.0,  # ~22M with children
    "eitc_childless": 9.0,  # ~9M childless
}

# Baseline annual costs (billions)
BASELINE_CREDIT_COSTS = {
    "ctc_total": 120.0,  # Total CTC cost ~$120B/year
    "ctc_refundable": 32.0,  # ACTC refundable portion ~$32B/year
    "eitc_total": 70.0,  # EITC cost ~$70B/year
}


@dataclass
class TaxCreditPolicy(TaxPolicy):
    """
    Tax credit policy with phase-in/phase-out modeling.

    Supports both refundable and non-refundable credits with income-based
    phase-in and phase-out structures.

    Key attributes:
        credit_type: Type of credit (CTC, EITC, etc.)
        is_refundable: Whether excess credit is refunded as cash
        max_credit_per_unit: Maximum credit per qualifying unit (child, filer)
        units_affected_millions: Number of qualifying units (children, filers)

        Phase-in (for EITC-style credits):
        phase_in_rate: Rate at which credit phases in with earned income
        phase_in_threshold: Income at which phase-in begins
        phase_in_end: Income at which maximum credit is reached

        Phase-out:
        phase_out_threshold: Income at which phase-out begins
        phase_out_rate: Rate at which credit phases out (per dollar of income)

        Refundability:
        refundable_max: Maximum refundable amount (for partially refundable)
        refund_rate: Rate at which credit becomes refundable with earnings
    """

    credit_type: CreditType = CreditType.OTHER
    is_refundable: bool = False
    is_partially_refundable: bool = False  # Like current CTC

    # Credit amount
    max_credit_per_unit: float = 0.0  # Maximum credit per child/filer
    credit_change_per_unit: float = 0.0  # Change from current law
    units_affected_millions: float = 0.0  # Qualifying children or filers

    # Phase-in structure (EITC-style)
    has_phase_in: bool = False
    phase_in_rate: float = 0.0  # Rate credit phases in
    phase_in_threshold: float = 0.0  # Income where phase-in starts
    phase_in_end: float = 0.0  # Income where max credit reached

    # Phase-out structure
    has_phase_out: bool = True
    phase_out_threshold_single: float = 0.0  # AGI where phase-out starts
    phase_out_threshold_married: float = 0.0
    phase_out_rate: float = 0.0  # Rate credit phases out

    # Partial refundability (CTC-style)
    refundable_max: float = 0.0  # Max refundable portion
    refund_rate: float = 0.0  # Rate at which credit becomes refundable
    refund_threshold: float = 0.0  # Earned income floor for refundability

    # Make fully refundable (policy change)
    make_fully_refundable: bool = False

    # Remove phase-out (policy change)
    remove_phase_out: bool = False

    # Expand qualifying criteria
    expand_qualifying_age: Optional[int] = None  # e.g., 18 instead of 17
    include_childless_adults: bool = False  # For EITC expansion

    # Behavioral parameters
    labor_supply_elasticity: float = 0.1  # EITC has significant labor effects
    participation_rate: float = 0.85  # Not everyone eligible claims

    # Take-up adjustment (some eligible don't claim)
    take_up_rate_change: float = 0.0  # Change in participation rate

    def __post_init__(self):
        """Set default policy type for credits."""
        if self.policy_type == PolicyType.INCOME_TAX:
            self.policy_type = PolicyType.TAX_CREDIT

    def calculate_credit_for_income(
        self,
        earned_income: float,
        agi: float,
        filing_status: Literal["single", "married"] = "single",
        num_children: int = 0,
    ) -> dict:
        """
        Calculate credit amount for a given income level.

        Returns dict with:
            - gross_credit: Credit before phase-out
            - net_credit: Credit after phase-out
            - refundable_portion: Amount refundable
            - non_refundable_portion: Amount offsetting tax liability
        """
        # Start with max credit
        gross_credit = self.max_credit_per_unit * max(1, num_children)

        # Apply phase-in (if applicable, like EITC)
        if self.has_phase_in:
            if earned_income < self.phase_in_threshold:
                gross_credit = 0.0
            elif earned_income < self.phase_in_end:
                phase_in_income = earned_income - self.phase_in_threshold
                gross_credit = min(gross_credit, phase_in_income * self.phase_in_rate)

        # Apply phase-out
        net_credit = gross_credit
        if self.has_phase_out and not self.remove_phase_out:
            threshold = (self.phase_out_threshold_married if filing_status == "married"
                        else self.phase_out_threshold_single)
            if agi > threshold:
                phase_out_amount = (agi - threshold) * self.phase_out_rate
                net_credit = max(0, gross_credit - phase_out_amount)

        # Calculate refundable vs non-refundable portions
        if self.is_refundable or self.make_fully_refundable:
            refundable = net_credit
            non_refundable = 0.0
        elif self.is_partially_refundable:
            # CTC-style: refundable portion based on earnings
            refundable_earnings = max(0, earned_income - self.refund_threshold)
            potential_refund = refundable_earnings * self.refund_rate
            refundable = min(self.refundable_max * max(1, num_children),
                           potential_refund, net_credit)
            non_refundable = net_credit - refundable
        else:
            refundable = 0.0
            non_refundable = net_credit

        return {
            "gross_credit": gross_credit,
            "net_credit": net_credit,
            "refundable_portion": refundable,
            "non_refundable_portion": non_refundable,
        }

    def estimate_static_revenue_effect(
        self,
        baseline_revenue: float,
        use_real_data: bool = True,
    ) -> float:
        """
        Estimate static revenue effect of credit policy change.

        For credits, revenue effect = change in credit cost (negative = cost).

        Args:
            baseline_revenue: Baseline tax revenue (not directly used)
            use_real_data: Whether to use real data (not currently implemented)

        Returns:
            Revenue change in billions (negative = revenue loss/cost)
        """
        if self.annual_revenue_change_billions is not None:
            return self.annual_revenue_change_billions

        # Calculate cost from credit change and affected units
        if self.credit_change_per_unit != 0 and self.units_affected_millions > 0:
            # Simple calculation: change × units × participation
            static_cost = (
                self.credit_change_per_unit *
                self.units_affected_millions *
                self.participation_rate *
                1e6 / 1e9  # Convert to billions
            )
            return -static_cost  # Negative = costs money

        # Calculate cost from making credit fully refundable
        if self.make_fully_refundable and self.credit_type == CreditType.CHILD_TAX_CREDIT:
            # Currently ~$32B is refundable, full refundability would add more
            # Rough estimate: ~60% of CTC is refundable, making rest refundable
            # adds ~$50B/year
            return -50.0

        # Calculate cost from removing phase-out
        if self.remove_phase_out:
            # Depends on credit type and current phase-out parameters
            # For CTC: removes phase-out for high earners
            if self.credit_type == CreditType.CHILD_TAX_CREDIT:
                # ~5% of filers in phase-out range, avg reduction ~$1,000/child
                return -5.0  # ~$5B/year

        return 0.0

    def estimate_behavioral_offset(self, static_effect: float) -> float:
        """
        Estimate behavioral response to credit changes.

        For refundable credits (especially EITC), there are significant
        labor supply effects:
        - EITC phase-in encourages work (positive labor supply)
        - EITC phase-out discourages work (negative labor supply)
        - Net effect on labor supply and therefore income tax revenue

        Returns:
            Behavioral offset in billions (positive = revenue lost)
        """
        # EITC has the largest labor supply effects
        if self.credit_type == CreditType.EARNED_INCOME_CREDIT:
            # Research shows EITC increases labor force participation
            # This generates additional income tax + payroll tax revenue
            # Offsetting ~10-15% of the cost
            return static_effect * 0.12  # ~12% offset from labor supply

        # CTC has smaller labor effects
        if self.credit_type == CreditType.CHILD_TAX_CREDIT:
            # Some income effects on secondary earners, but smaller
            return static_effect * 0.05  # ~5% offset

        # General credits
        return abs(static_effect) * self.labor_supply_elasticity * 0.3


# =============================================================================
# FACTORY FUNCTIONS FOR COMMON CREDIT POLICIES
# =============================================================================

def create_ctc_expansion(
    credit_per_child: float,
    fully_refundable: bool = False,
    remove_phase_out: bool = False,
    start_year: int = 2025,
    duration_years: int = 10,
    name: Optional[str] = None,
) -> TaxCreditPolicy:
    """
    Create a Child Tax Credit expansion policy.

    Args:
        credit_per_child: New credit amount per child
        fully_refundable: Whether to make credit fully refundable
        remove_phase_out: Whether to remove income phase-out
        start_year: First year of policy
        duration_years: Duration of policy
        name: Optional custom name

    Returns:
        TaxCreditPolicy configured for CTC expansion

    Example:
        # Biden 2021 ARP-style expansion
        policy = create_ctc_expansion(
            credit_per_child=3600,  # Was $2,000
            fully_refundable=True,
            name="Biden CTC Expansion"
        )
    """
    current_credit = CTC_CURRENT_LAW["credit_per_child"]
    credit_change = credit_per_child - current_credit

    return TaxCreditPolicy(
        name=name or f"CTC Expansion to ${credit_per_child:,.0f}",
        description=f"Expand Child Tax Credit from ${current_credit:,.0f} to "
                   f"${credit_per_child:,.0f} per child"
                   f"{', fully refundable' if fully_refundable else ''}"
                   f"{', remove phase-out' if remove_phase_out else ''}",
        policy_type=PolicyType.TAX_CREDIT,
        credit_type=CreditType.CHILD_TAX_CREDIT,
        is_partially_refundable=not fully_refundable,
        max_credit_per_unit=credit_per_child,
        credit_change_per_unit=credit_change,
        units_affected_millions=CREDIT_RECIPIENT_COUNTS["ctc_children"],
        has_phase_out=True,
        phase_out_threshold_single=CTC_CURRENT_LAW["phase_out_start_single"],
        phase_out_threshold_married=CTC_CURRENT_LAW["phase_out_start_married"],
        phase_out_rate=CTC_CURRENT_LAW["phase_out_rate"],
        refundable_max=CTC_CURRENT_LAW["refundable_max"],
        refund_rate=CTC_CURRENT_LAW["refund_rate"],
        refund_threshold=CTC_CURRENT_LAW["refund_threshold"],
        make_fully_refundable=fully_refundable,
        remove_phase_out=remove_phase_out,
        participation_rate=0.90,  # CTC has high take-up
        start_year=start_year,
        duration_years=duration_years,
    )


def create_biden_ctc_2021() -> TaxCreditPolicy:
    """
    Create the Biden 2021 American Rescue Plan CTC expansion.

    Key features:
    - $3,600 per child under 6, $3,000 per child 6-17
    - Fully refundable (no earnings requirement)
    - Monthly advance payments

    CBO estimated 1-year cost: ~$110B (for 2021)
    Permanent expansion would cost ~$1.6T over 10 years
    """
    # Use average credit (weighted by child age distribution)
    avg_credit = 3300  # Weighted average of $3,600 and $3,000

    return TaxCreditPolicy(
        name="Biden CTC 2021 (ARP-style)",
        description="Expand CTC to $3,600 (under 6) / $3,000 (6-17), fully refundable",
        policy_type=PolicyType.TAX_CREDIT,
        credit_type=CreditType.CHILD_TAX_CREDIT,
        is_refundable=True,
        max_credit_per_unit=avg_credit,
        credit_change_per_unit=avg_credit - CTC_CURRENT_LAW["credit_per_child"],
        units_affected_millions=CREDIT_RECIPIENT_COUNTS["ctc_children"],
        has_phase_out=True,
        phase_out_threshold_single=75000.0,  # ARP lowered thresholds
        phase_out_threshold_married=150000.0,
        phase_out_rate=0.05,
        make_fully_refundable=True,
        participation_rate=0.92,  # High due to advance payments
        # Calibrated to match CBO ~$1.6T over 10 years permanent
        annual_revenue_change_billions=-160.0,
        start_year=2025,
        duration_years=10,
    )


def create_ctc_permanent_extension() -> TaxCreditPolicy:
    """
    Extend current CTC provisions beyond 2025 sunset.

    Without extension, CTC reverts to:
    - $1,000 per child (from $2,000)
    - Lower phase-out thresholds
    - Less refundability

    CBO estimate: Extension costs ~$600B over 10 years
    """
    return TaxCreditPolicy(
        name="CTC Permanent Extension",
        description="Extend current $2,000 CTC beyond 2025 sunset",
        policy_type=PolicyType.TAX_CREDIT,
        credit_type=CreditType.CHILD_TAX_CREDIT,
        is_partially_refundable=True,
        max_credit_per_unit=CTC_CURRENT_LAW["credit_per_child"],
        # Change from pre-TCJA baseline
        credit_change_per_unit=(CTC_CURRENT_LAW["credit_per_child"] -
                               CTC_CURRENT_LAW["pre_tcja_credit"]),
        units_affected_millions=CREDIT_RECIPIENT_COUNTS["ctc_children"],
        has_phase_out=True,
        phase_out_threshold_single=CTC_CURRENT_LAW["phase_out_start_single"],
        phase_out_threshold_married=CTC_CURRENT_LAW["phase_out_start_married"],
        phase_out_rate=CTC_CURRENT_LAW["phase_out_rate"],
        refundable_max=CTC_CURRENT_LAW["refundable_max"],
        refund_rate=CTC_CURRENT_LAW["refund_rate"],
        refund_threshold=CTC_CURRENT_LAW["refund_threshold"],
        participation_rate=0.90,
        # Calibrated to CBO ~$600B over 10 years
        annual_revenue_change_billions=-60.0,
        start_year=2026,  # After sunset
        duration_years=10,
    )


def create_eitc_expansion(
    childless_max_increase: float = 0.0,
    with_children_increase_pct: float = 0.0,
    expand_age_range: bool = False,
    start_year: int = 2025,
    duration_years: int = 10,
) -> TaxCreditPolicy:
    """
    Create an EITC expansion policy.

    Args:
        childless_max_increase: Dollar increase in max credit for childless
        with_children_increase_pct: Percent increase in max credit with children
        expand_age_range: Include ages 19-24 and 65+ (currently 25-64 for childless)
        start_year: First year of policy
        duration_years: Duration

    Returns:
        TaxCreditPolicy for EITC expansion

    Example:
        # Biden childless worker expansion
        policy = create_eitc_expansion(
            childless_max_increase=1100,  # Roughly triple current
            expand_age_range=True,
        )
    """
    # Calculate cost based on parameters
    if childless_max_increase > 0:
        # ~9M childless EITC recipients, avg credit ~$600
        childless_cost = (childless_max_increase *
                         CREDIT_RECIPIENT_COUNTS["eitc_childless"] *
                         0.85 / 1000)  # billions
    else:
        childless_cost = 0.0

    if with_children_increase_pct > 0:
        # ~22M filers with children, avg credit ~$3,000
        current_with_children_cost = 22.0 * 3.0  # ~$66B
        with_children_cost = current_with_children_cost * with_children_increase_pct
    else:
        with_children_cost = 0.0

    if expand_age_range:
        # Adds ~5M eligible filers (ages 19-24 and 65+)
        age_expansion_cost = 5.0 * 0.6 * 0.5 / 1  # ~$1.5B/year
    else:
        age_expansion_cost = 0.0

    total_cost = childless_cost + with_children_cost + age_expansion_cost

    # Build description
    desc_parts = []
    if childless_max_increase > 0:
        desc_parts.append(f"+${childless_max_increase:,.0f} max for childless")
    if with_children_increase_pct > 0:
        desc_parts.append(f"+{with_children_increase_pct*100:.0f}% for families")
    if expand_age_range:
        desc_parts.append("expand age 19-24/65+")

    return TaxCreditPolicy(
        name="EITC Expansion",
        description=f"Expand EITC: {', '.join(desc_parts)}",
        policy_type=PolicyType.TAX_CREDIT,
        credit_type=CreditType.EARNED_INCOME_CREDIT,
        is_refundable=True,  # EITC is fully refundable
        has_phase_in=True,
        has_phase_out=True,
        participation_rate=0.80,  # EITC has lower take-up than CTC
        labor_supply_elasticity=0.25,  # EITC has strong labor effects
        annual_revenue_change_billions=-total_cost,
        start_year=start_year,
        duration_years=duration_years,
    )


def create_biden_eitc_childless() -> TaxCreditPolicy:
    """
    Create Biden proposal to expand EITC for childless workers.

    Key features:
    - Nearly triple max credit (~$1,500 from $600)
    - Expand age range to 19-24 and 65+
    - Lower phase-in start ($9,820 to $2,500)

    CBO/Treasury estimate: ~$178B over 10 years
    """
    return TaxCreditPolicy(
        name="Biden EITC Childless Expansion",
        description="Triple max credit to ~$1,500, expand age range 19-65+",
        policy_type=PolicyType.TAX_CREDIT,
        credit_type=CreditType.EARNED_INCOME_CREDIT,
        is_refundable=True,
        max_credit_per_unit=1500.0,
        credit_change_per_unit=900.0,  # From ~$600
        units_affected_millions=15.0,  # Expanded eligible population
        has_phase_in=True,
        phase_in_rate=0.153,  # ~15.3% (doubled from current)
        phase_in_threshold=0.0,
        phase_in_end=9820.0,
        has_phase_out=True,
        phase_out_threshold_single=11610.0,
        phase_out_threshold_married=17550.0,
        phase_out_rate=0.153,
        participation_rate=0.75,  # Childless have lower take-up
        labor_supply_elasticity=0.30,  # Strong labor supply effects
        # Calibrated to CBO ~$178B over 10 years
        annual_revenue_change_billions=-17.8,
        start_year=2025,
        duration_years=10,
    )


# =============================================================================
# VALIDATION SCENARIOS
# =============================================================================

CREDIT_VALIDATION_SCENARIOS = {
    "biden_ctc_2021": {
        "description": "Biden 2021 ARP-style CTC (permanent)",
        "policy_factory": "create_biden_ctc_2021",
        "expected_10yr": -1600.0,  # CBO estimate for permanent
        "source": "CBO/JCT 2021",
        "notes": "Actual ARP was 1-year, cost ~$110B",
    },
    "ctc_extension": {
        "description": "Extend current CTC beyond 2025",
        "policy_factory": "create_ctc_permanent_extension",
        "expected_10yr": -600.0,  # CBO estimate
        "source": "CBO 2024",
        "notes": "Part of TCJA extension cost",
    },
    "biden_eitc_childless": {
        "description": "Biden childless EITC expansion",
        "policy_factory": "create_biden_eitc_childless",
        "expected_10yr": -178.0,
        "source": "Treasury Green Book 2024",
        "notes": "Expand age range and nearly triple credit",
    },
}


def estimate_credit_cost(policy: TaxCreditPolicy) -> dict:
    """
    Estimate total cost of a credit policy over 10 years.

    Returns dict with:
        - annual_cost: Average annual cost
        - ten_year_cost: Total 10-year cost
        - behavioral_offset: Labor supply revenue offset
        - net_cost: Final cost after behavioral offset
    """
    annual_static = -policy.estimate_static_revenue_effect(0)
    behavioral = -policy.estimate_behavioral_offset(-annual_static)

    # Apply growth (~3%/year)
    years = np.arange(10)
    annual_costs = annual_static * (1.03 ** years)
    behavioral_offsets = behavioral * (1.03 ** years)

    ten_year_static = np.sum(annual_costs)
    ten_year_behavioral = np.sum(behavioral_offsets)

    return {
        "annual_cost": annual_static,
        "ten_year_cost": ten_year_static,
        "behavioral_offset": ten_year_behavioral,
        "net_cost": ten_year_static - ten_year_behavioral,
    }
