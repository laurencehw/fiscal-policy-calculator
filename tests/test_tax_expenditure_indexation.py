"""
A year-indexed excess share for capped tax expenditures (Wave 4 lane 3a).

`planning/lanes/W4_option56_excess_share.md` is the lane; the mechanism it
builds is that a cap's bite moves across a window, because the limit and the
quantity it limits grow at different rates. Before it, the module asked the
distribution "what share sits above the cap" **once**, at `start_year`, and the
scoring engine grew that one answer at the expenditure's own rate.

These tests pin four things:

1. the price index is an index -- 1.0 in its own year, monotone, invertible,
   and near-identical across the three baseline vintages the repository
   carries, so the answer does not depend on which one a caller scores on;
2. the stated annual is **unchanged**, which is what keeps every existing
   caller (and every leave-one-out row, which reads exactly that annual) at
   the value it had;
3. the limit really is indexed -- an indexed limit yields a smaller share than
   a limit fixed in nominal dollars, in every year after the first;
4. deduction caps are *not* year-indexed, because the SOI class aggregates
   they are compared against have no year dimension to index against.
"""

from __future__ import annotations

import pytest

from fiscal_model.baseline import BaselineVintage
from fiscal_model.policies import PolicyType
from fiscal_model.tax_expenditure_distributions import (
    BASELINE_ASSUMPTION_FIRST_YEAR,
    CAP_INDEXATION_VINTAGE,
    load_premium_distribution,
    price_index_factor,
)
from fiscal_model.tax_expenditures import (
    EXPENDITURE_MODE_DERIVED,
    JCT_TAX_EXPENDITURES,
    TaxExpenditurePolicy,
    TaxExpenditureType,
    create_cap_charitable_deduction,
    create_cap_employer_health_exclusion,
)

#: CBO's own annual revenue rows for Option 56's third alternative, FY2028-2034
#: (pub. 60557, report p. 66; PDF p. 72, "Change in revenues"). Carried here to
#: shape-test the model's path, never to fit it.
CBO_OPTION_56_REVENUE_BY_YEAR = {
    2028: 59.0,
    2029: 86.0,
    2030: 94.0,
    2031: 103.0,
    2032: 112.0,
    2033: 123.0,
    2034: 132.0,
}

#: The limits CBO states for that alternative, in 2028 dollars.
CBO_OPTION_56_CAPS_2028 = {"single": 10_000.0, "family": 24_400.0}


# ---------------------------------------------------------------------------
# The price index
# ---------------------------------------------------------------------------


def test_a_limit_in_its_own_year_is_worth_itself():
    """
    The property that makes this change invisible where it should be.

    A cap is stated in the policy's start-year dollars, so the factor there is
    exactly one. Every caller that asks for the stated annual -- the app's
    factories, `validation/loo.py`'s `derive_expenditure_annual` -- gets the
    number it got before indexation existed.
    """
    for year in (2025, 2028, 2034, 2040):
        assert price_index_factor(year, year) == 1.0


def test_the_index_compounds_forward_and_inverts_backward():
    forward = price_index_factor(2028, 2034)
    assert forward > 1.0
    assert price_index_factor(2034, 2028) == pytest.approx(1.0 / forward)
    # Six years of ~2% price growth, not twelve and not none.
    assert 1.10 < forward < 1.16


def test_the_index_is_monotone_in_the_horizon():
    factors = [price_index_factor(2028, year) for year in range(2028, 2040)]
    assert factors == sorted(factors)


def test_years_past_the_projection_hold_the_terminal_rate():
    """
    Not extrapolated, held -- which is what the baseline does with its own
    terminal assumption. One year past the end must cost exactly one more
    application of the last projected rate.
    """
    last_year = BASELINE_ASSUMPTION_FIRST_YEAR + 9
    step = price_index_factor(last_year, last_year + 1)
    assert price_index_factor(last_year, last_year + 3) == pytest.approx(step**3)


def test_the_vintages_agree_so_the_answer_is_not_a_vintage_choice():
    """
    The lane picks CBO's February 2024 baseline because that is the one the
    options volume was built on. If the three vintages disagreed materially,
    that pick would be a knob; they do not.
    """
    factors = [
        price_index_factor(2028, 2034, vintage) for vintage in BaselineVintage
    ]
    assert max(factors) / min(factors) < 1.005
    assert CAP_INDEXATION_VINTAGE is BaselineVintage.CBO_FEB_2024


# ---------------------------------------------------------------------------
# What the module does with it
# ---------------------------------------------------------------------------


def test_the_employer_health_record_declares_its_indexation_with_the_source():
    """
    A design element is a declared object with its source, like SALT's
    `limitation` -- not a constant somebody has to trust.
    """
    block = JCT_TAX_EXPENDITURES["employer_health"]["cap_indexation"]
    assert "chained consumer price index" in block["design"]
    assert "60557" in block["design"]
    # The substitution is stated where the series is named, not buried.
    assert "chained CPI-U" in block["series"]


def test_the_stated_annual_does_not_move():
    """
    Asking for no year must be the same as asking for the start year.

    This is what leaves all five derivable expenditure LOO rows untouched:
    `derive_expenditure_annual` reads exactly this number.
    """
    policy = create_cap_employer_health_exclusion(
        caps_by_coverage_tier=dict(CBO_OPTION_56_CAPS_2028),
        mode=EXPENDITURE_MODE_DERIVED,
    )
    policy.annual_revenue_change_billions = None
    stated = policy.estimate_static_revenue_effect(0.0)
    assert stated == pytest.approx(
        policy.estimate_static_revenue_effect(0.0, year=policy.start_year)
    )


def test_the_excess_share_widens_across_the_window():
    """
    Premiums grow at 4%/yr and the limit at about 2%, so the slice above the
    limit grows. A flat share is the defect this lane removes.
    """
    policy = create_cap_employer_health_exclusion(
        caps_by_coverage_tier=dict(CBO_OPTION_56_CAPS_2028),
        start_year=2028,
        mode=EXPENDITURE_MODE_DERIVED,
    )
    policy.annual_revenue_change_billions = None
    path = [
        policy.estimate_static_revenue_effect(0.0, year=year)
        for year in range(2028, 2035)
    ]
    assert path == sorted(path)
    # 22.4% of premium dollars above the limit in 2028, 28.5% by 2034: a
    # quarter more of the base inside seven years, from indexation alone.
    assert path[-1] / path[0] == pytest.approx(1.274, rel=0.02)


def test_an_indexed_limit_bites_less_than_a_frozen_one():
    """
    The direction that says the indexation is real: freezing the limit in
    nominal dollars would let it erode against premiums twice as fast, so it
    must produce a strictly larger share in every later year.
    """
    distribution = load_premium_distribution()
    growth = JCT_TAX_EXPENDITURES["employer_health"]["growth_rate"]
    for year in range(2029, 2035):
        indexed = distribution.base_share_above(
            0.0,
            year=year,
            growth_rate=growth,
            caps_by_tier=CBO_OPTION_56_CAPS_2028,
            cap_index_factor=price_index_factor(2028, year),
        )
        frozen = distribution.base_share_above(
            0.0,
            year=year,
            growth_rate=growth,
            caps_by_tier=CBO_OPTION_56_CAPS_2028,
        )
        assert 0.0 < indexed < frozen


def test_a_deduction_cap_is_not_year_indexed():
    """
    The boundary of the rule. `DeductionDistribution` carries SOI class
    aggregates with no year dimension, so indexing the limit against it would
    shrink one side of a comparison whose other side cannot move.
    """
    dollar_cap = TaxExpenditurePolicy(
        name="Cap the mortgage interest deduction at $10,000",
        description="A per-return dollar cap on a deduction",
        policy_type=PolicyType.TAX_DEDUCTION,
        expenditure_type=TaxExpenditureType.MORTGAGE_INTEREST,
        action="cap",
        cap_amount=10_000,
        mode=EXPENDITURE_MODE_DERIVED,
    )
    assert dollar_cap.estimate_static_revenue_effect(
        0.0, year=dollar_cap.start_year + 6
    ) == pytest.approx(dollar_cap.estimate_static_revenue_effect(0.0))

    # And the rate ceiling, which has no dollars in it at all.
    rate_cap = create_cap_charitable_deduction(mode=EXPENDITURE_MODE_DERIVED)
    rate_cap.annual_revenue_change_billions = None
    assert rate_cap.estimate_static_revenue_effect(
        0.0, year=rate_cap.start_year + 6
    ) == pytest.approx(rate_cap.estimate_static_revenue_effect(0.0))


# ---------------------------------------------------------------------------
# Against CBO's own path
# ---------------------------------------------------------------------------


def test_the_scored_path_tracks_cbos_growth_rather_than_the_expenditures():
    """
    The residual this lane exists to shrink is a *shape* residual.

    CBO's revenue for Option 56's third alternative grows about 14%/yr across
    FY2028-2034. A flat excess share grows at the expenditure's own 4%. The
    year-indexed share must land between the two and much nearer CBO -- it
    carries the indexation but still has no plan-switching channel and no
    payroll base.
    """
    from fiscal_model.baseline import BaselineVintage as Vintage
    from fiscal_model.validation.cbo_scores import KNOWN_SCORES
    from fiscal_model.validation.core import (
        build_scorer_for_vintage,
        create_policy_from_score,
    )

    score = KNOWN_SCORES["cbo_opt56_employer_health_income_only"]
    policy = create_policy_from_score(score)
    result = build_scorer_for_vintage(Vintage.CBO_FEB_2024).score_policy(
        policy, dynamic=False
    )
    revenue = {
        int(year): float(value)
        for year, value in zip(result.years, result.static_revenue_effect)
        if int(year) in CBO_OPTION_56_REVENUE_BY_YEAR
    }
    assert set(revenue) == set(CBO_OPTION_56_REVENUE_BY_YEAR)

    years = sorted(revenue)
    model_growth = (revenue[years[-1]] / revenue[years[0]]) ** (1 / (len(years) - 1)) - 1
    expenditure_growth = JCT_TAX_EXPENDITURES["employer_health"]["growth_rate"]
    assert model_growth > expenditure_growth + 0.03
    assert model_growth < 0.14

    # First year is the level check and it was already close; the total is the
    # shape check and it is what moved.
    assert revenue[2028] == pytest.approx(CBO_OPTION_56_REVENUE_BY_YEAR[2028], rel=0.06)
    assert sum(revenue.values()) == pytest.approx(506.0, rel=0.02)
