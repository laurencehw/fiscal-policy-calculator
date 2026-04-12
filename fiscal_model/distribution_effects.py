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
    """Calculate distributional effect for TCJA extension."""
    ten_year_cost = getattr(policy, "ten_year_cost_billions", 4600)
    extend_salt_cap = getattr(policy, "extend_salt_cap", True)
    annual_cost = ten_year_cost / 10.0

    if extend_salt_cap:
        distribution_shares = {
            (0, 35_000): 0.02,
            (35_000, 65_000): 0.05,
            (65_000, 105_000): 0.10,
            (105_000, 170_000): 0.18,
            (170_000, None): 0.65,
        }
    else:
        distribution_shares = {
            (0, 35_000): 0.02,
            (35_000, 65_000): 0.04,
            (65_000, 105_000): 0.08,
            (105_000, 170_000): 0.16,
            (170_000, None): 0.70,
        }

    group_share = 0.0
    for (floor, _ceiling), share in distribution_shares.items():
        if group.floor == floor:
            group_share = share
            break

    if group_share == 0.0:
        if group.ceiling and group.ceiling <= 35_000:
            group_share = 0.02 * (group.num_returns / total_returns) * 5
        elif group.floor >= 170_000:
            group_share = 0.65 * (group.num_returns / total_returns) * 5
        else:
            group_share = 0.15 * (group.num_returns / total_returns) * 5

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


def calculate_corporate_effect(policy: Policy, group: IncomeGroup, total_returns: int) -> DistributionalResult:
    """Calculate distributional effect for corporate tax changes."""
    rate_change = getattr(policy, "rate_change", 0)
    baseline_revenue = getattr(policy, "baseline_revenue_billions", 475)
    static_revenue_change = baseline_revenue * (rate_change / 0.21)
    elasticity = getattr(policy, "corporate_elasticity", 0.25)
    behavioral_offset = static_revenue_change * elasticity * 0.5
    revenue_change = static_revenue_change - behavioral_offset
    capital_share = 0.75
    labor_share = 0.25

    capital_income_shares = {
        (0, 35_000): 0.01,
        (35_000, 65_000): 0.02,
        (65_000, 105_000): 0.05,
        (105_000, 170_000): 0.12,
        (170_000, None): 0.80,
    }
    labor_income_shares = {
        (0, 35_000): 0.08,
        (35_000, 65_000): 0.12,
        (65_000, 105_000): 0.18,
        (105_000, 170_000): 0.25,
        (170_000, None): 0.37,
    }

    capital_share_group = 0.0
    labor_share_group = 0.0
    for (floor, ceiling), share in capital_income_shares.items():
        if group.floor == floor:
            capital_share_group = share
            labor_share_group = labor_income_shares[(floor, ceiling)]
            break

    if capital_share_group == 0.0:
        if group.floor >= 170_000:
            capital_share_group = 0.80 * (group.num_returns / total_returns) * 5
            labor_share_group = 0.37 * (group.num_returns / total_returns) * 5
        else:
            capital_share_group = 0.05 * (group.num_returns / total_returns) * 5
            labor_share_group = 0.15 * (group.num_returns / total_returns) * 5

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

    if isinstance(policy, TaxCreditPolicy):
        return calculate_credit_effect(policy, group, total_returns)
    if isinstance(policy, TCJAExtensionPolicy):
        return calculate_tcja_effect(policy, group, total_returns)
    if isinstance(policy, CorporateTaxPolicy):
        return calculate_corporate_effect(policy, group, total_returns)
    if isinstance(policy, PayrollTaxPolicy):
        return calculate_payroll_effect(policy, group)
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
