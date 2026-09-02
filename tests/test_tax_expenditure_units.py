"""
Units, distributions and modes for tax-expenditure scoring (lane L6).

These tests pin the three things that were wrong before
`planning/lanes/L6_tax_expenditures.md`:

1. a cap parameter's **unit** -- a premium cap compared with a tax benefit;
2. the **level in force** an `eliminate` rule prices, when a statutory
   limitation has lapsed over the policy's window;
3. that the fitted constants still short-circuit everything in `reported`
   mode, so nothing a user sees moves.

They also re-add the transcribed SOI columns against the totals the published
table prints, so a bad transcription cannot pass silently.
"""

from __future__ import annotations

import pytest

from fiscal_model.microsim.engine import MicroTaxCalculator
from fiscal_model.policies import PolicyType
from fiscal_model.tax_expenditure_distributions import (
    SOI_BASE_YEAR,
    STATUTORY_MFJ_BRACKETS_2025,
    implied_sigma,
    load_deduction_distribution,
    load_premium_distribution,
    statutory_marginal_rate,
)
from fiscal_model.tax_expenditures import (
    EXPENDITURE_APP_MODE,
    EXPENDITURE_MODE_DERIVED,
    EXPENDITURE_MODE_REPORTED,
    JCT_TAX_EXPENDITURES,
    CapUnit,
    ExpenditureDistributionMissing,
    TaxExpenditurePolicy,
    TaxExpenditureType,
    create_cap_charitable_deduction,
    create_cap_employer_health_exclusion,
    create_cap_retirement_contributions,
    create_eliminate_mortgage_deduction,
    create_eliminate_salt_deduction,
    create_repeal_salt_cap,
)

# ---------------------------------------------------------------------------
# The transcription
# ---------------------------------------------------------------------------

#: "All returns, total" row of IRS SOI Table 2.1, TY2023, in thousands of
#: dollars (returns as a count). Transcribed from the same published file as
#: the data table itself.
SOI_2023_PUBLISHED_TOTALS = {
    "returns": 15_106_257,
    "salt": 331_823_221,
    "salt_limited": 121_050_787,
    "mortgage_interest": 171_364_787,
    "charitable": 211_975_123,
}


@pytest.mark.parametrize(
    "column",
    ["salt", "salt_limited", "mortgage_interest", "charitable"],
)
def test_transcribed_agi_classes_add_to_the_published_total(column):
    """SOI prints a total; the class rows must re-add to it."""
    distribution = load_deduction_distribution(column)
    published_billions = SOI_2023_PUBLISHED_TOTALS[column] / 1e6
    # SOI's own note: "detail may not add to totals because of rounding".
    assert distribution.total_amount_billions == pytest.approx(
        published_billions, rel=1e-4
    )


def test_statutory_schedule_matches_the_one_the_microsim_already_carries():
    """
    The rate schedule is the statute, not a lane-local parameter.

    `MicroTaxCalculator` transcribes the same 2025 married-joint brackets from
    Rev. Proc. 2024-40. If the two ever diverge, one of them is wrong.
    """
    calculator = MicroTaxCalculator(year=2025)
    expected = tuple(
        zip(
            (float(b) for b in calculator.brackets_mfj),
            calculator.rates_mfj,
            strict=True,
        )
    )
    assert STATUTORY_MFJ_BRACKETS_2025 == expected


@pytest.mark.parametrize(
    ("taxable_income", "rate"),
    [(0, 0.10), (23_850, 0.12), (96_949, 0.12), (96_950, 0.22), (2_000_000, 0.37)],
)
def test_statutory_marginal_rate_steps_at_the_bracket_floors(taxable_income, rate):
    assert statutory_marginal_rate(taxable_income) == rate


def test_soi_times_the_statutory_schedule_reproduces_the_capped_salt_expenditure():
    """
    The independent check that the marginal-rate rule is not made up.

    Pricing SOI's *limited* SALT deduction at the statutory schedule gives
    $25.0B/yr against the base table's own `annual_cost = 25.0` -- two
    numbers with no common ancestor agreeing to a tenth of a percent.

    The same computation on the *unlimited* deduction gives about $89.6B,
    against the record's `annual_cost_no_cap = 120.0`. That 25% gap is a
    finding, not a failure: it is recorded in the lane file and handed to the
    provenance lane, and it is pinned here so a data refresh cannot close it
    silently.
    """
    capped = load_deduction_distribution("salt_limited").implied_benefit_billions
    uncapped = load_deduction_distribution("salt").implied_benefit_billions

    assert capped == pytest.approx(JCT_TAX_EXPENDITURES["salt"]["annual_cost"], rel=0.01)
    assert uncapped == pytest.approx(89.6, rel=0.01)
    assert uncapped < JCT_TAX_EXPENDITURES["salt"]["annual_cost_no_cap"]


def test_premium_distribution_shape_comes_from_cbo_option_56():
    """
    Sigma is CBO's own p75/p50 ratio, not a fitted spread.

    Option 56 of *Options for Reducing the Deficit: 2025 to 2034* prints
    $10,000/$12,700 for individual coverage and $24,400/$31,300 for family.
    Inverting each pair must reproduce the stored shape, and the two tiers
    must agree -- otherwise the lognormal is describing one tier, not the
    premium distribution.
    """
    tiers = {tier.tier: tier for tier in load_premium_distribution().tiers}
    assert tiers["single"].sigma == pytest.approx(implied_sigma(10_000, 12_700), rel=1e-5)
    assert tiers["family"].sigma == pytest.approx(implied_sigma(24_400, 31_300), rel=1e-5)
    ratio = tiers["family"].sigma / tiers["single"].sigma
    assert 0.95 < ratio < 1.05


# ---------------------------------------------------------------------------
# The unit bug this lane exists to remove
# ---------------------------------------------------------------------------


def test_a_dollar_cap_on_premiums_is_compared_with_premiums():
    """
    A $50,000 cap is above the whole premium distribution, and must score so.

    The old rule compared $50,000 with `avg_benefit = 1_600` -- an average
    *tax benefit* -- and concluded 0.32% of the base was affected, giving
    $0.8B/yr. The corrected rule gives about $2.1B/yr, which is still small,
    because CBO's own 75th percentile of family premiums is $31,300.

    Both are far below the -$450B benchmark, and that is the point: no
    published option caps this exclusion at $50,000, so the benchmark cannot
    be reached by any correct model of a $50,000 cap.
    """
    policy = create_cap_employer_health_exclusion(mode=EXPENDITURE_MODE_DERIVED)
    policy.annual_revenue_change_billions = None
    assert policy.estimate_static_revenue_effect(0.0) == pytest.approx(2.12, rel=0.02)


def test_a_cap_inside_the_premium_distribution_scores_far_larger():
    """
    The corrected rule is monotone and responds at the right scale.

    A cap near the median family premium bites; one at $50,000 does not. If
    these were the same order of magnitude, the distribution would not be
    doing any work.
    """
    small_cap = create_cap_employer_health_exclusion(
        cap_amount=25_000, mode=EXPENDITURE_MODE_DERIVED
    )
    large_cap = create_cap_employer_health_exclusion(
        cap_amount=50_000, mode=EXPENDITURE_MODE_DERIVED
    )
    for policy in (small_cap, large_cap):
        policy.annual_revenue_change_billions = None

    tight = small_cap.estimate_static_revenue_effect(0.0)
    loose = large_cap.estimate_static_revenue_effect(0.0)
    assert tight > 10 * loose


def test_per_tier_caps_are_expressible():
    """
    Every published design of this option caps per coverage tier.

    CBO's Option 56 sets its first alternative at the 50th percentile of 2026
    premiums: $10,000 individual, $24,400 family in 2028. Being able to write
    that at all is what a base-dollar cap unit buys.
    """
    policy = create_cap_employer_health_exclusion(
        cap_amount=50_000,
        caps_by_coverage_tier={"single": 10_000, "family": 24_400},
        mode=EXPENDITURE_MODE_DERIVED,
    )
    policy.annual_revenue_change_billions = None
    percentile_cap = policy.estimate_static_revenue_effect(0.0)
    assert percentile_cap > 30.0


def test_benefit_dollar_unit_must_be_asked_for_by_name():
    """The old comparison survives only when a caller declares that unit."""
    policy = create_cap_employer_health_exclusion(mode=EXPENDITURE_MODE_DERIVED)
    policy.annual_revenue_change_billions = None
    policy.cap_unit = CapUnit.BENEFIT_DOLLARS
    # 250.0 * 0.1 * (1600 / 50000)
    assert policy.estimate_static_revenue_effect(0.0) == pytest.approx(0.8)


def test_cap_without_a_base_distribution_raises_instead_of_guessing():
    """
    No distribution, no number.

    Retirement contributions have no transcribed distribution, so a $20,000
    contribution cap has nothing to be applied to. Returning an approximation
    here is precisely the defect this lane removed.
    """
    policy = create_cap_retirement_contributions(mode=EXPENDITURE_MODE_DERIVED)
    policy.annual_revenue_change_billions = None
    with pytest.raises(ExpenditureDistributionMissing):
        policy.estimate_static_revenue_effect(0.0)


# ---------------------------------------------------------------------------
# Limitations
# ---------------------------------------------------------------------------


def test_eliminate_prices_the_level_in_force_over_the_window():
    """
    The `eliminate_salt` half of the lane.

    The $10,000 cap expires after 2025 (IRC 164(b)(6)), so a window beginning
    in 2026 prices the unlimited deduction. A window beginning in 2021 -- ten
    years, all of them capped -- prices the limited one.
    """
    record = JCT_TAX_EXPENDITURES["salt"]

    uncapped_window = create_eliminate_salt_deduction(
        start_year=2026, mode=EXPENDITURE_MODE_DERIVED
    )
    uncapped_window.annual_revenue_change_billions = None
    assert uncapped_window.estimate_static_revenue_effect(0.0) == pytest.approx(
        record["annual_cost_no_cap"]
    )

    capped_window = create_eliminate_salt_deduction(
        start_year=2021, duration_years=5, mode=EXPENDITURE_MODE_DERIVED
    )
    capped_window.annual_revenue_change_billions = None
    assert capped_window.estimate_static_revenue_effect(0.0) == pytest.approx(
        record["annual_cost"]
    )


def test_a_window_straddling_the_expiry_is_averaged():
    """Four capped years then six uncapped, weighted by year count."""
    policy = create_eliminate_salt_deduction(
        start_year=2022, duration_years=10, mode=EXPENDITURE_MODE_DERIVED
    )
    policy.annual_revenue_change_billions = None
    record = JCT_TAX_EXPENDITURES["salt"]
    expected = 0.4 * record["annual_cost"] + 0.6 * record["annual_cost_no_cap"]
    assert policy.estimate_static_revenue_effect(0.0) == pytest.approx(expected)


def test_eliminate_without_a_limitation_is_unchanged():
    """
    Mortgage interest carries `annual_cost_no_limit` and no limitation block.

    That field names no statute and no expiry, so no rule reads it, and
    eliminating the deduction still prices `annual_cost`. Wiring it in would
    move this row by a factor of four on an unsourced constant.
    """
    policy = create_eliminate_mortgage_deduction(mode=EXPENDITURE_MODE_DERIVED)
    policy.annual_revenue_change_billions = None
    record = JCT_TAX_EXPENDITURES["mortgage_interest"]
    assert policy.estimate_static_revenue_effect(0.0) == pytest.approx(
        record["annual_cost"]
    )
    assert "limitation" not in record


def test_repealing_a_limitation_costs_the_limitations_own_value():
    """
    `expand` is driven by the limitation record, not by an expenditure-type
    special case as it was before.
    """
    policy = create_repeal_salt_cap(mode=EXPENDITURE_MODE_DERIVED)
    policy.annual_revenue_change_billions = None
    record = JCT_TAX_EXPENDITURES["salt"]
    assert policy.estimate_static_revenue_effect(0.0) == pytest.approx(
        -(record["annual_cost_no_cap"] - record["annual_cost"])
    )


def test_generic_expansion_is_unchanged_for_records_without_a_limitation():
    policy = TaxExpenditurePolicy(
        name="Generic Expansion",
        description="Expand charitable benefit",
        policy_type=PolicyType.TAX_DEDUCTION,
        expenditure_type=TaxExpenditureType.CHARITABLE,
        action="expand",
        mode=EXPENDITURE_MODE_DERIVED,
    )
    assert policy.estimate_static_revenue_effect(0.0) == pytest.approx(-14.0)


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------


def test_app_mode_is_reported_so_no_shipped_number_moves():
    assert EXPENDITURE_APP_MODE == EXPENDITURE_MODE_REPORTED


@pytest.mark.parametrize(
    ("factory", "fitted"),
    [
        (create_cap_employer_health_exclusion, 31.2),
        (create_eliminate_mortgage_deduction, 26.2),
        (create_repeal_salt_cap, -96.0),
        (create_eliminate_salt_deduction, 104.7),
        (create_cap_charitable_deduction, 12.5),
        (create_cap_retirement_contributions, 13.1),
    ],
)
def test_reported_mode_returns_the_fitted_constant(factory, fitted):
    assert factory().estimate_static_revenue_effect(0.0) == pytest.approx(fitted)


def test_derived_mode_ignores_the_fitted_constant():
    """Derived must not silently fall back to the answer it was given."""
    policy = create_cap_charitable_deduction(mode=EXPENDITURE_MODE_DERIVED)
    assert policy.annual_revenue_change_billions == 12.5
    assert policy.estimate_static_revenue_effect(0.0) == pytest.approx(10.831, rel=1e-4)


def test_unknown_mode_is_rejected():
    with pytest.raises(ValueError, match="mode must be one of"):
        create_cap_charitable_deduction(mode="fitted")


def test_soi_base_year_is_declared():
    """A silent vintage change would move every derived cap."""
    assert SOI_BASE_YEAR == 2023
