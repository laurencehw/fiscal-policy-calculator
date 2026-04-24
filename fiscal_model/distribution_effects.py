"""
Policy-specific effect calculators for distributional analysis.
"""

from .distribution_core import DistributionalResult, IncomeGroup
from .policies import Policy, TaxPolicy


def _get_credit_policy():
    from .credits import CreditType, TaxCreditPolicy

    return TaxCreditPolicy, CreditType


def _get_tcja_policy():
    from .tcja import TCJAExtensionPolicy

    return TCJAExtensionPolicy


def _get_corporate_policy():
    from .corporate import CorporateTaxPolicy

    return CorporateTaxPolicy


def _get_payroll_policy():
    from .payroll import PayrollTaxPolicy

    return PayrollTaxPolicy


def _get_tax_expenditure_policy():
    from .tax_expenditures import TaxExpenditurePolicy

    return TaxExpenditurePolicy


def build_distribution_result(
    *,
    group: IncomeGroup,
    tax_change_total: float,
    tax_change_avg: float,
    tax_change_pct_income: float,
    pct_with_increase: float,
    pct_with_decrease: float,
) -> DistributionalResult:
    """Build a standard distribution result payload."""
    baseline_etr = group.effective_tax_rate
    new_tax = group.baseline_tax + tax_change_total
    new_etr = new_tax / group.total_agi if group.total_agi > 0 else 0.0

    return DistributionalResult(
        income_group=group,
        tax_change_total=tax_change_total,
        tax_change_avg=tax_change_avg,
        tax_change_pct_income=tax_change_pct_income,
        share_of_total_change=0.0,
        pct_with_increase=pct_with_increase,
        pct_with_decrease=pct_with_decrease,
        pct_unchanged=100 - pct_with_increase - pct_with_decrease,
        baseline_etr=baseline_etr,
        new_etr=new_etr,
        etr_change=new_etr - baseline_etr,
    )


def calculate_group_effect(policy: TaxPolicy, group: IncomeGroup) -> DistributionalResult:
    """Calculate the effect of a basic rate-change tax policy on one group."""
    rate_change = getattr(policy, "rate_change", 0.0)
    threshold = getattr(policy, "affected_income_threshold", 0)
    group_ceiling = group.ceiling if group.ceiling else float("inf")

    if threshold >= group_ceiling:
        affected_fraction = 0.0
    elif threshold <= group.floor:
        affected_fraction = 1.0
    elif group.ceiling is None:
        if group.avg_agi > threshold:
            affected_fraction = min(1.0, (group.avg_agi - threshold) / group.avg_agi + 0.5)
        else:
            affected_fraction = max(0.0, 0.5 - (threshold - group.avg_agi) / group.avg_agi)
        affected_fraction = max(0.0, min(1.0, affected_fraction))
    else:
        group_width = group_ceiling - group.floor
        affected_width = group_ceiling - threshold
        affected_fraction = affected_width / group_width if group_width > 0 else 0.0

    affected_taxable = group.total_taxable_income * affected_fraction
    tax_change_total = rate_change * affected_taxable
    affected_returns = int(group.num_returns * affected_fraction)
    tax_change_avg = (tax_change_total * 1e9) / affected_returns if affected_returns > 0 else 0.0
    after_tax_income = group.total_agi - group.baseline_tax
    tax_change_pct_income = (tax_change_total / after_tax_income) * 100 if after_tax_income > 0 else 0.0

    if rate_change > 0:
        pct_with_increase = affected_fraction * 100
        pct_with_decrease = 0.0
    elif rate_change < 0:
        pct_with_increase = 0.0
        pct_with_decrease = affected_fraction * 100
    else:
        pct_with_increase = 0.0
        pct_with_decrease = 0.0

    return build_distribution_result(
        group=group,
        tax_change_total=tax_change_total,
        tax_change_avg=tax_change_avg,
        tax_change_pct_income=tax_change_pct_income,
        pct_with_increase=pct_with_increase,
        pct_with_decrease=pct_with_decrease,
    )


def calculate_credit_effect(policy: Policy, group: IncomeGroup, total_returns: int) -> DistributionalResult:
    """Calculate distributional effect for tax credit policies."""
    credit_change = getattr(policy, "credit_change_per_unit", 0) or getattr(policy, "max_credit_change", 0)
    units_millions = getattr(policy, "units_affected_millions", 0)
    is_refundable = getattr(policy, "is_refundable", True)
    phase_out_start = getattr(
        policy,
        "phase_out_threshold_single",
        getattr(policy, "phase_out_threshold", 200_000),
    )
    phase_out_rate = getattr(policy, "phase_out_rate", 0.05)
    phase_in_end = getattr(policy, "phase_in_end", 0)
    group_ceiling = group.ceiling if group.ceiling else float("inf")

    if group.floor >= phase_out_start:
        if phase_out_rate > 0:
            excess_income = group.avg_agi - phase_out_start
            credit_reduction = min(1.0, excess_income * phase_out_rate / max(credit_change, 1))
            affected_fraction = max(0.0, 1.0 - credit_reduction)
        else:
            affected_fraction = 0.0
    elif phase_in_end > 0 and group_ceiling <= phase_in_end:
        affected_fraction = group.avg_agi / phase_in_end if phase_in_end > 0 else 1.0
    else:
        affected_fraction = 1.0

    if not is_refundable and group.avg_tax < abs(credit_change):
        effective_credit = min(abs(credit_change), group.avg_tax)
        credit_fraction = effective_credit / abs(credit_change) if credit_change != 0 else 0
        affected_fraction *= credit_fraction

    if group.floor < 50_000:
        recipient_share = 0.3
    elif group.floor < 100_000:
        recipient_share = 0.35
    elif group.floor < 200_000:
        recipient_share = 0.25
    else:
        recipient_share = 0.10

    recipient_share *= (group.num_returns / total_returns) * 5
    units_in_group = units_millions * 1e6 * recipient_share
    tax_change_total = -credit_change * units_in_group * affected_fraction / 1e9
    affected_returns = int(min(units_in_group, group.num_returns) * affected_fraction)
    tax_change_avg = (tax_change_total * 1e9) / affected_returns if affected_returns > 0 else 0.0
    after_tax_income = group.total_agi - group.baseline_tax
    tax_change_pct_income = (tax_change_total / after_tax_income) * 100 if after_tax_income > 0 else 0.0

    if credit_change > 0:
        pct_with_increase = 0.0
        pct_with_decrease = recipient_share * affected_fraction * 100
    elif credit_change < 0:
        pct_with_increase = recipient_share * affected_fraction * 100
        pct_with_decrease = 0.0
    else:
        pct_with_increase = 0.0
        pct_with_decrease = 0.0

    return build_distribution_result(
        group=group,
        tax_change_total=tax_change_total,
        tax_change_avg=tax_change_avg,
        tax_change_pct_income=tax_change_pct_income,
        pct_with_increase=pct_with_increase,
        pct_with_decrease=pct_with_decrease,
    )


def calculate_tcja_effect(policy: Policy, group: IncomeGroup, total_returns: int) -> DistributionalResult:
    """
    Calculate distributional effect for TCJA extension.

    Uses published CBO/JCT TCJA distributional benchmarks (CBO 60007,
    JCX-68-17) as the calibration target. Tiers span the full AGI
    distribution and lookup uses the group midpoint so quintiles,
    deciles, and JCT dollar brackets all resolve cleanly.

    Validated against CBO_TCJA_2018 (decile) and CBO_TCJA_EXTENSION_2026
    (decile). With SALT cap kept: top decile gets ~37% of the cut,
    bottom decile ~0.5% — matching CBO within 2pp on most deciles.
    """
    ten_year_cost = getattr(policy, "ten_year_cost_billions", 4600)
    extend_salt_cap = getattr(policy, "extend_salt_cap", True)
    annual_cost = ten_year_cost / 10.0

    # Ranged tiers covering the full AGI distribution. Tier boundaries
    # align with IRS SOI 2022 decile floors so CBO decile benchmarks
    # can match exactly; shares sum to 1.0 and are calibrated against
    # CBO's published TCJA distributional tables (CBO 54796, CBO 60007).
    #
    # See docs/VALIDATION_NOTES.md §3b for the derivation.
    if extend_salt_cap:
        tcja_tiers = (
            (0, 15_000, 0.005),
            (15_000, 28_000, 0.018),
            (28_000, 42_000, 0.032),
            (42_000, 55_000, 0.048),
            (55_000, 72_000, 0.058),
            (72_000, 92_000, 0.073),
            (92_000, 118_000, 0.092),
            (118_000, 155_000, 0.126),
            (155_000, 220_000, 0.180),
            (220_000, 500_000, 0.135),
            (500_000, 1_000_000, 0.070),
            (1_000_000, float("inf"), 0.163),
        )
    else:
        # Without SALT cap, more of the cut accrues to high-tax-state
        # filers who bunch at $220K+. Shift ~5pp from middle to top.
        tcja_tiers = (
            (0, 15_000, 0.004),
            (15_000, 28_000, 0.015),
            (28_000, 42_000, 0.027),
            (42_000, 55_000, 0.040),
            (55_000, 72_000, 0.048),
            (72_000, 92_000, 0.061),
            (92_000, 118_000, 0.076),
            (118_000, 155_000, 0.104),
            (155_000, 220_000, 0.155),
            (220_000, 500_000, 0.155),
            (500_000, 1_000_000, 0.085),
            (1_000_000, float("inf"), 0.230),
        )

    group_floor = float(group.floor)
    group_ceiling = float(
        group.ceiling if group.ceiling is not None else float("inf")
    )

    # Sum contributions from every tier the group overlaps. For a tier
    # [lo, hi) with share s, the group gets an overlap fraction of
    # (min(group_ceiling, hi) - max(group_floor, lo)) / (hi - lo), so a
    # quintile that spans multiple tiers captures all of them and a
    # decile that sub-divides a tier takes only its piece.
    group_share = 0.0
    for lo, hi, share in tcja_tiers:
        overlap_lo = max(group_floor, lo)
        overlap_hi = min(group_ceiling, hi)
        if overlap_hi <= overlap_lo:
            continue
        if hi == float("inf"):
            # Infinite tier: treat the group's portion above lo as
            # capturing the full tier share (the tier is a point-mass
            # on "top of distribution" that should not be pro-rated).
            group_share += share
        else:
            group_share += share * (overlap_hi - overlap_lo) / (hi - lo)

    tax_change_total = -annual_cost * group_share
    tax_change_avg = (tax_change_total * 1e9) / group.num_returns if group.num_returns > 0 else 0.0
    after_tax_income = group.total_agi - group.baseline_tax
    tax_change_pct_income = (tax_change_total / after_tax_income) * 100 if after_tax_income > 0 else 0.0
    pct_with_increase = 0.0
    pct_with_decrease = min(95.0, group_share * 500)

    return build_distribution_result(
        group=group,
        tax_change_total=tax_change_total,
        tax_change_avg=tax_change_avg,
        tax_change_pct_income=tax_change_pct_income,
        pct_with_increase=pct_with_increase,
        pct_with_decrease=pct_with_decrease,
    )


def _sum_tier_overlap(
    tiers: tuple[tuple[float, float, float], ...],
    group: IncomeGroup,
) -> float:
    """
    Sum the distribution-share contributions from every tier the group
    overlaps. Shared helper for the tier-table calculators (TCJA,
    corporate, tax expenditures); factored out here so a bracket that
    spans multiple tiers always captures all of them and a bracket that
    sub-divides a tier takes only its proper width.
    """
    group_floor = float(group.floor)
    group_ceiling = float(
        group.ceiling if group.ceiling is not None else float("inf")
    )
    total = 0.0
    for lo, hi, share in tiers:
        overlap_lo = max(group_floor, lo)
        overlap_hi = min(group_ceiling, hi)
        if overlap_hi <= overlap_lo:
            continue
        if hi == float("inf"):
            total += share
        else:
            total += share * (overlap_hi - overlap_lo) / (hi - lo)
    return total


# ---------------------------------------------------------------------------
# Tax-expenditure distribution tables
# ---------------------------------------------------------------------------
#
# Published benchmarks that these were calibrated against:
# - SALT cap repeal: JCT JCX-4-24 (2024) — 94% of the cut goes to filers
#   above \$200K, 66% above \$500K, 38% above \$1M.
# - Mortgage interest: TPC methodology note (heavily skewed to top 40%
#   of filers, 60%+ to top decile).
# - Charitable deduction: TPC — 80%+ to top decile.
# - Employer health exclusion: CBO — roughly evenly distributed because
#   employer-provided insurance is broadly held.
# - Step-up basis / like-kind / capital-gains treatment: concentrated at
#   the top; ~90% of the benefit goes to the top decile per JCT.
#
# Shape of each tier table: [(lower, upper, share)] where shares sum to
# 1.0 across the table and upper=float("inf") for the open-ended top.
_TAX_EXPENDITURE_TIER_TABLES: dict[str, tuple[tuple[float, float, float], ...]] = {
    "SALT": (
        (0, 50_000, 0.00),
        (50_000, 100_000, 0.003),
        (100_000, 200_000, 0.055),
        (200_000, 500_000, 0.281),
        (500_000, 1_000_000, 0.279),
        (1_000_000, float("inf"), 0.382),
    ),
    "MORTGAGE_INTEREST": (
        (0, 50_000, 0.01),
        (50_000, 100_000, 0.06),
        (100_000, 200_000, 0.23),
        (200_000, 500_000, 0.35),
        (500_000, 1_000_000, 0.15),
        (1_000_000, float("inf"), 0.20),
    ),
    "CHARITABLE": (
        (0, 50_000, 0.01),
        (50_000, 100_000, 0.03),
        (100_000, 200_000, 0.09),
        (200_000, 500_000, 0.22),
        (500_000, 1_000_000, 0.16),
        (1_000_000, float("inf"), 0.49),
    ),
    "EMPLOYER_HEALTH": (
        (0, 50_000, 0.10),
        (50_000, 100_000, 0.22),
        (100_000, 200_000, 0.32),
        (200_000, 500_000, 0.24),
        (500_000, 1_000_000, 0.07),
        (1_000_000, float("inf"), 0.05),
    ),
    "STEP_UP_BASIS": (
        (0, 100_000, 0.01),
        (100_000, 200_000, 0.03),
        (200_000, 500_000, 0.08),
        (500_000, 1_000_000, 0.12),
        (1_000_000, float("inf"), 0.76),
    ),
}
# Default (reasonably top-heavy) for expenditure types without an explicit
# benchmark — prevents a silent fall-through to even distribution.
_TAX_EXPENDITURE_DEFAULT_TIERS = (
    (0, 50_000, 0.02),
    (50_000, 100_000, 0.08),
    (100_000, 200_000, 0.20),
    (200_000, 500_000, 0.30),
    (500_000, 1_000_000, 0.15),
    (1_000_000, float("inf"), 0.25),
)


def calculate_tax_expenditure_effect(
    policy: Policy,
    group: IncomeGroup,
    total_returns: int,
) -> DistributionalResult:
    """
    Calculate distributional effect for a tax-expenditure policy.

    Uses a per-expenditure-type tier table calibrated against published
    JCT / TPC distributional analyses of the underlying expenditure
    (see ``_TAX_EXPENDITURE_TIER_TABLES`` for sources). Tier shares
    are summed over every tier the income group overlaps, so quintiles,
    deciles, and JCT dollar brackets all resolve cleanly.

    Validated against JCT JCX-4-24 (SALT cap repeal): the engine's
    \\$1M+ share (38.2%) matches JCT's 38.2% exactly because the tier
    table was calibrated against this benchmark.
    """
    del total_returns  # tier fractions already normalise by group width

    annual_revenue_change = getattr(policy, "annual_revenue_change_billions", 0) or 0
    # Positive annual_revenue_change = policy raises revenue (cuts deductions);
    # treat that as a tax *increase* on filers. Negative = policy expands
    # the deduction (SALT cap repeal), which is a tax *cut*.
    expenditure_type = getattr(policy, "expenditure_type", None)
    type_key = expenditure_type.name if expenditure_type is not None else ""
    tiers = _TAX_EXPENDITURE_TIER_TABLES.get(type_key, _TAX_EXPENDITURE_DEFAULT_TIERS)

    group_share = _sum_tier_overlap(tiers, group)
    # Flip sign so positive annual_revenue_change → positive
    # tax_change_total (burden increase on filers).
    tax_change_total = annual_revenue_change * group_share

    tax_change_avg = (
        (tax_change_total * 1e9) / group.num_returns if group.num_returns > 0 else 0.0
    )
    after_tax_income = group.total_agi - group.baseline_tax
    tax_change_pct_income = (
        (tax_change_total / after_tax_income) * 100 if after_tax_income > 0 else 0.0
    )

    if tax_change_total > 0:
        pct_with_increase = min(95.0, group_share * 500)
        pct_with_decrease = 0.0
    elif tax_change_total < 0:
        pct_with_increase = 0.0
        pct_with_decrease = min(95.0, group_share * 500)
    else:
        pct_with_increase = 0.0
        pct_with_decrease = 0.0

    return build_distribution_result(
        group=group,
        tax_change_total=tax_change_total,
        tax_change_avg=tax_change_avg,
        tax_change_pct_income=tax_change_pct_income,
        pct_with_increase=pct_with_increase,
        pct_with_decrease=pct_with_decrease,
    )


def calculate_corporate_effect(policy: Policy, group: IncomeGroup, total_returns: int) -> DistributionalResult:
    """
    Calculate distributional effect for corporate tax changes.

    Uses the CBO/JCT 75/25 capital/labor split. Capital-income shares by
    AGI tier are drawn from IRS SOI Table 1.4 (dividends + net capital
    gains + S-corp/partnership distributions); labor-income shares are
    drawn from Table 1.1 wage columns. Values are smoothed across the
    published tiers so the function returns a coherent allocation for
    any bracket boundary the engine passes in (quintiles, deciles,
    JCT dollar brackets all work).

    Validated against JCT JCX-32-21 (Biden 21% → 28%): with these
    tables the engine assigns ~34% of corporate burden to filers above
    \\$1M, matching JCT's 35.9% within 2pp.
    """
    rate_change = getattr(policy, "rate_change", 0)
    baseline_revenue = getattr(policy, "baseline_revenue_billions", 475)
    static_revenue_change = baseline_revenue * (rate_change / 0.21)
    elasticity = getattr(policy, "corporate_elasticity", 0.25)
    behavioral_offset = static_revenue_change * elasticity * 0.5
    revenue_change = static_revenue_change - behavioral_offset
    capital_share = 0.75
    labor_share = 0.25

    # Share of *national* capital income flowing to each AGI tier, and
    # share of national labor income. Tiers are [floor, ceiling) and
    # cover the full AGI range; a group is assigned to a tier by its
    # midpoint so finer-grained groupings (deciles, JCT dollar brackets)
    # match without exact-floor equality checks.
    capital_tiers = (
        (0, 100_000, 0.10),
        (100_000, 200_000, 0.12),
        (200_000, 500_000, 0.18),
        (500_000, 1_000_000, 0.15),
        (1_000_000, float("inf"), 0.45),
    )
    labor_tiers = (
        (0, 100_000, 0.65),
        (100_000, 200_000, 0.20),
        (200_000, 500_000, 0.10),
        (500_000, 1_000_000, 0.03),
        (1_000_000, float("inf"), 0.02),
    )

    group_floor = float(group.floor)
    group_ceiling = float(
        group.ceiling if group.ceiling is not None else float("inf")
    )

    def _tier_share(tiers):
        # Sum contributions from every tier the group overlaps. See
        # calculate_tcja_effect for the derivation — same pattern.
        total = 0.0
        for lo, hi, share in tiers:
            overlap_lo = max(group_floor, lo)
            overlap_hi = min(group_ceiling, hi)
            if overlap_hi <= overlap_lo:
                continue
            if hi == float("inf"):
                total += share
            else:
                total += share * (overlap_hi - overlap_lo) / (hi - lo)
        return total

    capital_share_group = _tier_share(capital_tiers)
    labor_share_group = _tier_share(labor_tiers)

    group_burden_share = capital_share * capital_share_group + labor_share * labor_share_group
    tax_change_total = revenue_change * group_burden_share
    tax_change_avg = (tax_change_total * 1e9) / group.num_returns if group.num_returns > 0 else 0.0
    after_tax_income = group.total_agi - group.baseline_tax
    tax_change_pct_income = (tax_change_total / after_tax_income) * 100 if after_tax_income > 0 else 0.0

    if rate_change > 0:
        pct_with_increase = group_burden_share * 100
        pct_with_decrease = 0.0
    elif rate_change < 0:
        pct_with_increase = 0.0
        pct_with_decrease = group_burden_share * 100
    else:
        pct_with_increase = 0.0
        pct_with_decrease = 0.0

    return build_distribution_result(
        group=group,
        tax_change_total=tax_change_total,
        tax_change_avg=tax_change_avg,
        tax_change_pct_income=tax_change_pct_income,
        pct_with_increase=pct_with_increase,
        pct_with_decrease=pct_with_decrease,
    )


def calculate_payroll_effect(policy: Policy, group: IncomeGroup) -> DistributionalResult:
    """Calculate distributional effect for payroll tax changes."""
    current_cap = getattr(policy, "current_ss_cap", 168_600)
    new_cap = getattr(policy, "new_ss_cap", None)
    rate_change = getattr(policy, "rate_change", 0)
    group_ceiling = group.ceiling if group.ceiling else float("inf")

    if new_cap and new_cap > current_cap:
        if group.floor >= new_cap:
            affected_fraction = 1.0
            income_affected = min(new_cap - current_cap, group.avg_agi - current_cap)
        elif group.floor >= current_cap:
            affected_fraction = min(1.0, (group_ceiling - current_cap) / (new_cap - current_cap))
            income_affected = (new_cap - current_cap) * affected_fraction
        else:
            affected_fraction = 0.0
            income_affected = 0.0
        tax_change_total = income_affected * 0.124 * group.num_returns / 1e9
    elif rate_change != 0:
        if group.floor >= current_cap:
            affected_fraction = 0.0
        elif group_ceiling <= current_cap:
            affected_fraction = 1.0
        else:
            affected_fraction = (current_cap - group.floor) / (group_ceiling - group.floor)
        taxable_wages = group.total_agi * affected_fraction * 0.7
        tax_change_total = taxable_wages * rate_change
    else:
        tax_change_total = 0.0
        affected_fraction = 0.0

    affected_returns = int(group.num_returns * affected_fraction)
    tax_change_avg = (tax_change_total * 1e9) / affected_returns if affected_returns > 0 else 0.0
    after_tax_income = group.total_agi - group.baseline_tax
    tax_change_pct_income = (tax_change_total / after_tax_income) * 100 if after_tax_income > 0 else 0.0

    if tax_change_total > 0:
        pct_with_increase = affected_fraction * 100
        pct_with_decrease = 0.0
    elif tax_change_total < 0:
        pct_with_increase = 0.0
        pct_with_decrease = affected_fraction * 100
    else:
        pct_with_increase = 0.0
        pct_with_decrease = 0.0

    return build_distribution_result(
        group=group,
        tax_change_total=tax_change_total,
        tax_change_avg=tax_change_avg,
        tax_change_pct_income=tax_change_pct_income,
        pct_with_increase=pct_with_increase,
        pct_with_decrease=pct_with_decrease,
    )


def dispatch_distributional_effect(
    policy: Policy,
    group: IncomeGroup,
    total_returns: int,
) -> DistributionalResult:
    """Dispatch to the correct distributional effect calculator."""
    TaxCreditPolicy, _ = _get_credit_policy()
    TCJAExtensionPolicy = _get_tcja_policy()
    CorporateTaxPolicy = _get_corporate_policy()
    PayrollTaxPolicy = _get_payroll_policy()
    TaxExpenditurePolicy = _get_tax_expenditure_policy()

    if isinstance(policy, TaxCreditPolicy):
        return calculate_credit_effect(policy, group, total_returns)
    if isinstance(policy, TCJAExtensionPolicy):
        return calculate_tcja_effect(policy, group, total_returns)
    if isinstance(policy, CorporateTaxPolicy):
        return calculate_corporate_effect(policy, group, total_returns)
    if isinstance(policy, PayrollTaxPolicy):
        return calculate_payroll_effect(policy, group)
    if isinstance(policy, TaxExpenditurePolicy):
        return calculate_tax_expenditure_effect(policy, group, total_returns)
    return calculate_group_effect(policy, group)


def policy_to_microsim_reforms(policy: Policy, year: int = 2025) -> dict:
    """Convert a Policy object into microsim reform parameters."""
    reforms = {}

    if hasattr(policy, "rate_change"):
        rate_change = getattr(policy, "rate_change", 0.0)
        if rate_change != 0:
            reforms["new_top_rate"] = 0.37 + rate_change

    if hasattr(policy, "ctc_change"):
        ctc_change = getattr(policy, "ctc_change", 0)
        if ctc_change != 0:
            reforms["ctc_amount"] = 2000 + ctc_change

    if hasattr(policy, "eitc_expansion_factor"):
        eitc_expansion = getattr(policy, "eitc_expansion_factor", 1.0)
        if eitc_expansion != 1.0:
            reforms["eitc_expansion"] = eitc_expansion

    if hasattr(policy, "std_deduction_bonus"):
        std_ded_bonus = getattr(policy, "std_deduction_bonus", 0)
        if std_ded_bonus != 0:
            reforms["std_deduction_bonus"] = std_ded_bonus

    if hasattr(policy, "salt_cap"):
        salt_cap = getattr(policy, "salt_cap", 10000)
        if salt_cap != 10000:
            reforms["salt_cap"] = salt_cap

    return reforms
