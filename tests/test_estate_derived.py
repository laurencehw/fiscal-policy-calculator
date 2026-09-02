"""
SOI-fitted estate tax-base distribution: shape, level, lag, and the two modes.

The defect this replaces was an algebraic invariance, not an approximation:
``estimate_taxable_estates`` used to return ``19,000 * (6.4M / E)`` estates
against an average of ``4M * (E / 6.4M)``, whose product does not depend on
``E`` at all, so lowering the exemption derived exactly zero revenue. Several
tests below exist only to make sure that cannot come back.
"""

from __future__ import annotations

import itertools
import math

import pytest

from fiscal_model.estate import (
    BASELINE_ESTATE_DATA,
    ESTATE_APP_MODE,
    ESTATE_BASE_GROWTH_RATE,
    ESTATE_MODE_DERIVED,
    ESTATE_MODE_REPORTED,
    ESTATE_RECEIPTS_LAG_YEARS,
    ESTATE_SCORECARD_MODE,
    ESTATE_TAX_EXEMPTIONS,
    KOPCZUK_SLEMROD_PLANNING_ELASTICITY,
    SOI_ESTATE_TABLE1_PATH,
    EstateTaxPolicy,
    annual_estate_tax,
    create_biden_estate_proposal,
    create_estate_exemption_change,
    create_estate_rate_change,
    create_tcja_estate_extension,
    load_soi_estate_table1,
    soi_estate_anchor,
    soi_tax_base_pareto_alpha,
    taxable_base_above_exemption,
)
from fiscal_model.policies import PolicyType
from fiscal_model.scoring import FiscalPolicyScorer


def _probe(**kwargs) -> EstateTaxPolicy:
    kwargs.setdefault("name", "probe")
    kwargs.setdefault("description", "probe")
    kwargs.setdefault("policy_type", PolicyType.ESTATE_TAX)
    return EstateTaxPolicy(**kwargs)


# ---------------------------------------------------------------------------
# The data file
# ---------------------------------------------------------------------------


def test_soi_table_carries_its_provenance():
    """A transcribed table without a source header is an unsourced constant."""
    header = SOI_ESTATE_TABLE1_PATH.read_text(encoding="utf-8").split("filing_year,")[0]
    assert "Statistics of Income" in header
    assert "irs.gov/pub/irs-soi/24es01fy.xlsx" in header
    assert "Read: 2026-09-02" in header
    assert "Form 706" in header  # the filing-lag footnote the module cites


def test_soi_table_has_all_three_filing_years_in_all_three_panels():
    rows = load_soi_estate_table1()
    years = {int(row["filing_year"]) for row in rows}
    assert years == {2010, 2013, 2024}
    for year in years:
        panels = {row["tax_status"] for row in rows if int(row["filing_year"]) == year}
        assert panels == {"all", "taxable", "nontaxable"}


# ---------------------------------------------------------------------------
# Shape
# ---------------------------------------------------------------------------


def test_pareto_alpha_is_read_from_the_file_and_lands_where_soi_puts_it():
    alpha = soi_tax_base_pareto_alpha()
    assert 1.65 < alpha < 1.85
    # A Pareto with alpha <= 1 has no finite mean, so the mean-excess term
    # would be undefined; alpha >= 3 would make the tail thinner than any
    # wealth distribution ever measured.
    assert 1.0 < alpha < 3.0


def test_alpha_is_stable_across_filing_years():
    """Three regimes, thresholds a factor of 3.7 apart, one shape."""
    from fiscal_model.estate import _survival_above_boundaries

    per_year = {}
    for filing_year in (2010, 2013, 2024):
        points = _survival_above_boundaries(filing_year)
        assert len(points) >= 2, filing_year
        local = []
        for (_g1, n1, b1), (_g2, n2, b2) in itertools.pairwise(points):
            local.append(math.log(n1 / n2) / math.log((b2 / n2) / (b1 / n1)))
        per_year[filing_year] = local
    flat = [a for values in per_year.values() for a in values]
    assert len(flat) == 7
    assert min(flat) > 1.6
    assert max(flat) < 1.9


def test_boundaries_below_the_filing_threshold_are_not_read():
    """SOI's sub-threshold classes are a mixture and do not lie on the curve."""
    from fiscal_model.estate import _survival_above_boundaries

    for filing_year, threshold in ((2010, 3_500_000), (2013, 5_120_000), (2024, 12_920_000)):
        for boundary, _n, _b in _survival_above_boundaries(filing_year):
            assert boundary >= 0.95 * threshold


# ---------------------------------------------------------------------------
# Level
# ---------------------------------------------------------------------------


def test_anchor_reproduces_soi_own_printed_totals():
    anchor = soi_estate_anchor()
    assert anchor.decedent_year == 2023
    assert anchor.taxable_returns == 2663
    assert annual_estate_tax(
        anchor.exemption, anchor.statutory_top_rate, anchor.decedent_year
    ) == pytest.approx(anchor.net_estate_tax_billions, rel=1e-9)
    estates, average = _probe().estimate_taxable_estates(
        anchor.exemption, anchor.decedent_year
    )
    assert estates == anchor.taxable_returns
    assert estates * average / 1e9 == pytest.approx(
        anchor.base_above_exemption_billions, rel=1e-6
    )


def test_2026_baseline_level_agrees_with_the_cbo_projection():
    """
    The level is anchored on SOI, so CBO's projection is a free check on it.

    The old two-point blend implied ~$196B/yr here -- four times CBO's figure,
    which is why ``eliminate_estate_tax`` was recorded as not cross-validatable
    for a reason that no longer applies.
    """
    modelled = annual_estate_tax(ESTATE_TAX_EXEMPTIONS[2026], 0.40, 2026)
    cbo = BASELINE_ESTATE_DATA["revenue_baseline_2026"]
    assert modelled == pytest.approx(cbo, rel=0.15)
    assert 40.0 < modelled < 55.0


def test_growth_is_the_baseline_gdp_rate_not_the_rate_soi_history_implies():
    """
    Pins the lane's most consequential judgement call.

    Fitting the level and the growth jointly to SOI's three filing years
    returns ~6.8%/yr, because household wealth outgrew GDP over 2009-2023. The
    module projects forward at nominal GDP growth instead, so it *over*-states
    what was actually collected in 2009 and 2012. That is a known and
    deliberate bias, recorded here so a data refresh cannot quietly turn it
    into an accident.
    """
    assert ESTATE_BASE_GROWTH_RATE == pytest.approx(0.0382, abs=1e-4)
    for filing_year, actual in ((2010, 13.216723), (2013, 12.666774)):
        anchor = soi_estate_anchor(filing_year)
        modelled = annual_estate_tax(
            anchor.exemption, anchor.statutory_top_rate, anchor.decedent_year
        )
        assert modelled == pytest.approx(actual, rel=0.05) or modelled > actual
    # ...and reproduces the anchor year itself exactly.
    assert annual_estate_tax(12_920_000, 0.40, 2023) == pytest.approx(23.31322, rel=1e-6)


# ---------------------------------------------------------------------------
# The invariance is gone
# ---------------------------------------------------------------------------


def test_lowering_the_exemption_now_derives_revenue():
    high = annual_estate_tax(6_400_000, 0.40, 2026)
    low = annual_estate_tax(3_500_000, 0.40, 2026)
    assert low > high * 1.3


def test_count_times_average_is_not_invariant_in_the_exemption():
    """The exact defect: the old blend's product did not depend on E."""
    policy = _probe()
    products = []
    for exemption in (2_000_000, 3_500_000, 5_000_000, 6_400_000, 10_000_000):
        estates, average = policy.estimate_taxable_estates(exemption, 2026)
        products.append(estates * average)
    assert products == sorted(products, reverse=True)
    assert products[0] > products[-1] * 2


def test_revenue_falls_monotonically_in_the_exemption():
    previous = float("inf")
    for exemption in range(2_000_000, 20_000_001, 500_000):
        current = annual_estate_tax(exemption, 0.40, 2026)
        assert current < previous
        previous = current


def test_repeal_and_zero_rate_collapse_to_zero():
    assert annual_estate_tax(float("inf"), 0.40, 2026) == 0.0
    assert annual_estate_tax(6_400_000, 0.0, 2026) == 0.0
    assert taxable_base_above_exemption(0.0, 2026) == 0.0


# ---------------------------------------------------------------------------
# The receipts lag
# ---------------------------------------------------------------------------


def test_extension_is_a_no_op_until_the_sunset_reaches_receipts():
    """
    FY2025 and FY2026 receipts come from 2024 and 2025 deaths, and TCJA's
    exemption is current law for both, so extending it changes nothing there.
    """
    assert ESTATE_RECEIPTS_LAG_YEARS == 1
    path = dict(create_tcja_estate_extension(mode=ESTATE_MODE_DERIVED).derived_revenue_path())
    assert path[2025] == 0.0
    assert path[2026] == 0.0
    assert path[2027] < 0.0
    assert sum(1 for effect in path.values() if effect != 0.0) == 8


def test_biden_reform_is_a_no_op_only_in_its_first_fiscal_year():
    path = dict(create_biden_estate_proposal(mode=ESTATE_MODE_DERIVED).derived_revenue_path())
    assert path[2025] == 0.0
    assert path[2026] > 0.0
    assert sum(1 for effect in path.values() if effect != 0.0) == 9
    # FY2026 receipts price 2025 deaths, whose baseline is still TCJA's
    # $13.99M exemption, so the first live year is larger than the second.
    assert path[2026] > path[2027]


# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------


def test_app_and_scorecard_stay_on_reported():
    """Decision 1's rule: derived does not beat fitted on the carried targets."""
    assert ESTATE_APP_MODE == ESTATE_MODE_REPORTED
    assert ESTATE_SCORECARD_MODE == ESTATE_MODE_REPORTED
    assert create_tcja_estate_extension().mode == ESTATE_MODE_REPORTED
    assert create_biden_estate_proposal().mode == ESTATE_MODE_REPORTED


def test_reported_mode_still_scores_the_fitted_annuals():
    scorer = FiscalPolicyScorer(use_real_data=False)
    assert scorer.score_policy(
        create_tcja_estate_extension()
    ).total_10_year_cost == pytest.approx(167.0, rel=1e-6)
    assert scorer.score_policy(
        create_biden_estate_proposal()
    ).total_10_year_cost == pytest.approx(-450.0, rel=1e-6)


@pytest.mark.parametrize("factory", [create_tcja_estate_extension, create_biden_estate_proposal])
def test_derived_path_reaches_the_engine_unchanged(factory):
    """
    The engine multiplies a flat annual by its own growth factor, so the
    derived year path can only arrive through ``get_phase_in_factor``.
    """
    policy = factory(mode=ESTATE_MODE_DERIVED)
    expected = sum(effect for _year, effect in policy.derived_revenue_path())
    scored = FiscalPolicyScorer(
        start_year=policy.start_year, use_real_data=False
    ).score_policy(policy, dynamic=False)
    assert -scored.total_10_year_cost == pytest.approx(expected, rel=1e-6)


def test_derived_path_survives_both_engine_growth_branches():
    """
    ``ScoringEngine`` grows an estate policy at 3%/yr, except that an explicit
    ``annual_revenue_change_billions`` is treated as a window average and grown
    at 0. The phase factor has to cancel whichever applies.
    """
    scorer = FiscalPolicyScorer(start_year=2025, use_real_data=False)
    with_annual = create_biden_estate_proposal(mode=ESTATE_MODE_DERIVED)
    without_annual = create_biden_estate_proposal(mode=ESTATE_MODE_DERIVED)
    without_annual.annual_revenue_change_billions = None
    a = scorer.score_policy(with_annual, dynamic=False).total_10_year_cost
    b = scorer.score_policy(without_annual, dynamic=False).total_10_year_cost
    assert a == pytest.approx(b, rel=1e-6)


def test_mode_must_be_one_of_the_two():
    with pytest.raises(ValueError, match="mode must be one of"):
        _probe(mode="fitted")


# ---------------------------------------------------------------------------
# The user-facing generic paths
# ---------------------------------------------------------------------------


def test_generic_exemption_change_no_longer_scores_zero():
    """
    Before the size distribution this returned exactly $0.0B for every
    exemption at or below the post-sunset level -- the invariance, visible to
    users rather than only to the validation battery.
    """
    cut = create_estate_exemption_change(3_500_000)
    assert cut.annual_revenue_change_billions > 10.0
    raised = create_estate_exemption_change(20_000_000)
    assert raised.annual_revenue_change_billions < 0.0


# ---------------------------------------------------------------------------
# Behaviour
# ---------------------------------------------------------------------------


def test_planning_response_is_an_elasticity_not_a_flat_haircut():
    assert KOPCZUK_SLEMROD_PLANNING_ELASTICITY == pytest.approx(0.16)
    exemption_only = _probe(new_exemption=3_500_000, gift_shifting_elasticity=0.0)
    # No rate change means no change in the net-of-tax share, so no planning
    # response. The old flat 15%-of-static rule charged one anyway.
    assert exemption_only.estimate_behavioral_offset(100.0) == 0.0

    rate_rise = _probe(new_rate=0.45, gift_shifting_elasticity=0.0)
    offset = rate_rise.estimate_behavioral_offset(100.0)
    assert offset < 0.0  # a revenue gain is eroded
    assert 0.0 < abs(offset) < 5.0  # ...but by ~1.4%, not by 15%


def test_rate_change_factory_uses_the_frozen_elasticity():
    policy = create_estate_rate_change(rate_change=0.05)
    assert policy.planning_elasticity == KOPCZUK_SLEMROD_PLANNING_ELASTICITY
