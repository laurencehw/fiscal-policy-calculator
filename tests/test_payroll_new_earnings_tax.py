"""
The new-flat-payroll-tax branch: base, incidence, shifting and timing.

These are lane W5-A's pre-registered falsification tests
(``planning/lanes/W5_payroll_margin.md`` §4). Each one is written to fail the
lane rather than to be adjusted afterwards.
"""

from __future__ import annotations

import pytest

from fiscal_model.baseline import BaselineVintage
from fiscal_model.payroll import (
    COVERED_EARNINGS_TO_WAGES,
    HI_COST_RATE_CY2023,
    HI_TOTAL_EXPENDITURES_CY2023_BILLIONS,
    LABOR_INCOME_MARGINAL_TAX_RATE,
    NIPA_WAGES_CY2023_BILLIONS,
    PayrollTaxPolicy,
    PayrollTaxType,
    covered_earnings,
    create_expand_niit,
    create_new_payroll_tax,
    create_ss_cap_90_percent,
    create_ss_donut_hole,
    create_ss_eliminate_cap,
    first_fiscal_year_share,
)
from fiscal_model.policies import PolicyType
from fiscal_model.validation.cbo_scores import KNOWN_SCORES
from fiscal_model.validation.core import build_scorer_for_vintage, create_policy_from_score


def _score(policy):
    scorer = build_scorer_for_vintage(BaselineVintage.CBO_FEB_2024)
    return scorer.score_policy(policy, dynamic=False)


# ---------------------------------------------------------------------------
# The base
# ---------------------------------------------------------------------------


def test_covered_earnings_ratio_inverts_a_published_definition():
    """k is expenditures / cost rate / wages, all three published for CY2023."""
    hi_taxable_payroll = (
        HI_TOTAL_EXPENDITURES_CY2023_BILLIONS / HI_COST_RATE_CY2023
    )
    assert hi_taxable_payroll == pytest.approx(12_178.2, abs=0.1)
    assert COVERED_EARNINGS_TO_WAGES == pytest.approx(
        hi_taxable_payroll / NIPA_WAGES_CY2023_BILLIONS
    )
    # Covered earnings add self-employment income and drop non-covered
    # employment, so the ratio sits just above one. A value outside this band
    # would mean the two documents are being read against each other wrongly.
    assert 1.00 < COVERED_EARNINGS_TO_WAGES < 1.08


def test_covered_earnings_follows_cbos_own_wage_path():
    """The base grows at the baseline's wage growth, not a module constant."""
    assert covered_earnings(2025) == pytest.approx(13_210.3, abs=0.1)
    assert covered_earnings(2034) == pytest.approx(18_789.0, abs=0.1)
    growth = (covered_earnings(2034) / covered_earnings(2025)) ** (1 / 9) - 1
    assert 0.035 < growth < 0.042  # CBO's Feb 2024 path, ~3.9%/yr

    # Monotone across the whole tabulated window.
    values = [covered_earnings(y) for y in range(2025, 2035)]
    assert values == sorted(values)


def test_covered_earnings_extrapolates_outside_the_window():
    """Years the baseline does not project continue the nearest growth rate."""
    last_growth = covered_earnings(2034) / covered_earnings(2033)
    assert covered_earnings(2035) == pytest.approx(
        covered_earnings(2034) * last_growth
    )
    first_growth = covered_earnings(2026) / covered_earnings(2025)
    assert covered_earnings(2024) == pytest.approx(
        covered_earnings(2025) / first_growth
    )


def test_no_constant_in_the_branch_is_a_target_over_ten():
    """Anti-leakage: -1281.5/10 and -2540.0/10 appear nowhere in the mechanism."""
    forbidden = (128.15, 254.0)
    for value in (
        COVERED_EARNINGS_TO_WAGES,
        LABOR_INCOME_MARGINAL_TAX_RATE,
        HI_TOTAL_EXPENDITURES_CY2023_BILLIONS,
        HI_COST_RATE_CY2023,
        NIPA_WAGES_CY2023_BILLIONS,
    ):
        for target_annual in forbidden:
            assert value != pytest.approx(target_annual, rel=1e-6)


# ---------------------------------------------------------------------------
# Timing
# ---------------------------------------------------------------------------


def test_first_fiscal_year_share_is_a_calendar_identity():
    assert first_fiscal_year_share(1) == pytest.approx(0.75)  # January: Jan-Sep
    assert first_fiscal_year_share(4) == pytest.approx(0.5)   # April: Apr-Sep
    assert first_fiscal_year_share(9) == pytest.approx(1 / 12)
    # October onwards already falls in the next fiscal year, recorded with that
    # later start_year, so the whole year is covered.
    assert first_fiscal_year_share(10) == 1.0
    assert first_fiscal_year_share(12) == 1.0
    with pytest.raises(ValueError):
        first_fiscal_year_share(0)


def test_the_effective_month_only_scales_the_first_year():
    policy = create_new_payroll_tax(0.01)
    full_year = policy.estimate_static_revenue_effect(0.0, year=2026)
    first_year = policy.estimate_static_revenue_effect(0.0, year=2025)
    base_ratio = covered_earnings(2025) / covered_earnings(2026)
    assert first_year / full_year == pytest.approx(0.75 * base_ratio)


# ---------------------------------------------------------------------------
# The behavioural response
# ---------------------------------------------------------------------------


def test_offset_erodes_rather_than_magnifies():
    """|final| < |static|: the response costs revenue, it does not create it."""
    result = _score(create_new_payroll_tax(0.01))
    static = float(result.static_revenue_effect.sum())
    final = float(result.final_deficit_effect.sum())
    assert static > 0
    assert abs(final) < static


def test_the_response_scales_with_the_rate():
    """A flat share of the static effect would make these two equal."""
    one_pp = create_new_payroll_tax(0.01).new_earnings_tax_offset_share()
    two_pp = create_new_payroll_tax(0.02).new_earnings_tax_offset_share()
    assert two_pp > one_pp
    assert one_pp == pytest.approx(
        (0.01 + LABOR_INCOME_MARGINAL_TAX_RATE) * 0.25 / (1 - LABOR_INCOME_MARGINAL_TAX_RATE)
    )


def test_employer_share_is_zero_for_cbos_alternatives_and_live_otherwise():
    """The incidence rule is exercised, not dead code."""
    employee_side = create_new_payroll_tax(0.01, employer_share=0.0)
    split = create_new_payroll_tax(0.01, employer_share=0.5)
    assert split.new_earnings_tax_offset_share() > employee_side.new_earnings_tax_offset_share()
    assert split.new_earnings_tax_offset_share() - employee_side.new_earnings_tax_offset_share() == (
        pytest.approx(LABOR_INCOME_MARGINAL_TAX_RATE * 0.5)
    )
    # CBO's own conclusion: an employer-side or split tax raises less.
    assert abs(float(_score(split).final_deficit_effect.sum())) < abs(
        float(_score(employee_side).final_deficit_effect.sum())
    )
    # And the shape the validation path builds is the employee-side one.
    built = create_policy_from_score(KNOWN_SCORES["cbo_opt61_new_payroll_tax_1pct"])
    assert built.employer_share == 0.0
    assert built.payroll_tax_type is PayrollTaxType.NEW_EARNINGS_TAX
    assert built.effective_month == 1


# ---------------------------------------------------------------------------
# The engine wiring
# ---------------------------------------------------------------------------


def test_engine_does_not_grow_the_year_indexed_base_again():
    """The path carries CBO's growth; the module default 4%/yr is switched off."""
    policy = create_new_payroll_tax(0.01)
    result = _score(policy)
    scored = list(result.static_revenue_effect)
    expected = [
        policy.estimate_static_revenue_effect(0.0, year=year)
        for year in range(2025, 2035)
    ]
    assert scored == pytest.approx(expected)


def test_uses_covered_earnings_base_is_false_for_every_existing_policy():
    """The engine branch is a no-op for the calibrated payroll machinery."""
    for policy in (
        create_ss_cap_90_percent(),
        create_ss_donut_hole(),
        create_ss_eliminate_cap(),
        create_expand_niit(),
        PayrollTaxPolicy(
            name="Medicare",
            description="Medicare",
            policy_type=PolicyType.PAYROLL_TAX,
            medicare_rate_change=0.01,
        ),
    ):
        assert policy.uses_covered_earnings_base() is False


def test_fitted_payroll_benchmarks_are_untouched():
    """The four calibrated payroll rows still land on their targets exactly."""
    scorer = build_scorer_for_vintage(BaselineVintage.CBO_FEB_2024)
    for policy, expected in (
        (create_ss_cap_90_percent(), -800.0),
        (create_ss_donut_hole(), -2700.0),
        (create_ss_eliminate_cap(), -3200.0),
        (create_expand_niit(), -250.0),
    ):
        assert scorer.score_policy(policy).total_10_year_cost == pytest.approx(
            expected, rel=1e-6
        )
