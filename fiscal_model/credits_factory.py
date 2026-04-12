"""
Factory functions for common tax credit policies.
"""

from .credits_core import (
    CREDIT_RECIPIENT_COUNTS,
    CTC_CURRENT_LAW,
    CreditType,
    TaxCreditPolicy,
)
from .policies import PolicyType


def create_ctc_expansion(
    credit_per_child: float,
    fully_refundable: bool = False,
    remove_phase_out: bool = False,
    start_year: int = 2025,
    duration_years: int = 10,
    name: str | None = None,
) -> TaxCreditPolicy:
    """Create a Child Tax Credit expansion policy."""
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
        participation_rate=0.90,
        start_year=start_year,
        duration_years=duration_years,
    )


def create_biden_ctc_2021() -> TaxCreditPolicy:
    """Create the Biden 2021 American Rescue Plan CTC expansion."""
    avg_credit = 3300
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
        phase_out_threshold_single=75000.0,
        phase_out_threshold_married=150000.0,
        phase_out_rate=0.05,
        make_fully_refundable=True,
        participation_rate=0.92,
        annual_revenue_change_billions=-160.0,
        start_year=2025,
        duration_years=10,
    )


def create_ctc_permanent_extension() -> TaxCreditPolicy:
    """Extend current CTC provisions beyond the 2025 sunset."""
    return TaxCreditPolicy(
        name="CTC Permanent Extension",
        description="Extend current $2,000 CTC beyond 2025 sunset",
        policy_type=PolicyType.TAX_CREDIT,
        credit_type=CreditType.CHILD_TAX_CREDIT,
        is_partially_refundable=True,
        max_credit_per_unit=CTC_CURRENT_LAW["credit_per_child"],
        credit_change_per_unit=(
            CTC_CURRENT_LAW["credit_per_child"] - CTC_CURRENT_LAW["pre_tcja_credit"]
        ),
        units_affected_millions=CREDIT_RECIPIENT_COUNTS["ctc_children"],
        has_phase_out=True,
        phase_out_threshold_single=CTC_CURRENT_LAW["phase_out_start_single"],
        phase_out_threshold_married=CTC_CURRENT_LAW["phase_out_start_married"],
        phase_out_rate=CTC_CURRENT_LAW["phase_out_rate"],
        refundable_max=CTC_CURRENT_LAW["refundable_max"],
        refund_rate=CTC_CURRENT_LAW["refund_rate"],
        refund_threshold=CTC_CURRENT_LAW["refund_threshold"],
        participation_rate=0.90,
        annual_revenue_change_billions=-60.0,
        start_year=2026,
        duration_years=10,
    )


def create_eitc_expansion(
    childless_max_increase: float = 0.0,
    with_children_increase_pct: float = 0.0,
    expand_age_range: bool = False,
    start_year: int = 2025,
    duration_years: int = 10,
) -> TaxCreditPolicy:
    """Create an EITC expansion policy."""
    if childless_max_increase > 0:
        childless_cost = (
            childless_max_increase
            * CREDIT_RECIPIENT_COUNTS["eitc_childless"]
            * 0.85
            / 1000
        )
    else:
        childless_cost = 0.0

    if with_children_increase_pct > 0:
        current_with_children_cost = 22.0 * 3.0
        with_children_cost = current_with_children_cost * with_children_increase_pct
    else:
        with_children_cost = 0.0

    if expand_age_range:
        age_expansion_cost = 5.0 * 0.6 * 0.5 / 1
    else:
        age_expansion_cost = 0.0

    total_cost = childless_cost + with_children_cost + age_expansion_cost

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
        is_refundable=True,
        has_phase_in=True,
        has_phase_out=True,
        participation_rate=0.80,
        labor_supply_elasticity=0.25,
        annual_revenue_change_billions=-total_cost,
        start_year=start_year,
        duration_years=duration_years,
    )


def create_biden_eitc_childless() -> TaxCreditPolicy:
    """Create Biden proposal to expand EITC for childless workers."""
    return TaxCreditPolicy(
        name="Biden EITC Childless Expansion",
        description="Triple max credit to ~$1,500, expand age range 19-65+",
        policy_type=PolicyType.TAX_CREDIT,
        credit_type=CreditType.EARNED_INCOME_CREDIT,
        is_refundable=True,
        max_credit_per_unit=1500.0,
        credit_change_per_unit=900.0,
        units_affected_millions=15.0,
        has_phase_in=True,
        phase_in_rate=0.153,
        phase_in_threshold=0.0,
        phase_in_end=9820.0,
        has_phase_out=True,
        phase_out_threshold_single=11610.0,
        phase_out_threshold_married=17550.0,
        phase_out_rate=0.153,
        participation_rate=0.75,
        labor_supply_elasticity=0.30,
        annual_revenue_change_billions=-17.8,
        start_year=2025,
        duration_years=10,
    )
