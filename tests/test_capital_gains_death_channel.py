"""
Tests for the gains-at-death carve-outs and the behavioural response at death.

Wave 4 (``planning/lanes/W4_gains_at_death.md``) gave the death channel the
reliefs every published realization-at-death proposal states, and a response to
the rate it charges. What is worth testing is not a level - no benchmark is
reproduced here - but the four claims the lane rests on:

* two of the six stated reliefs remove **nothing**, because the base already
  excludes them, and the module must not deduct them again;
* the reliefs that do bite move in the direction and the order the statute
  says, and the per-donor exclusion applies *after* them;
* the response at death carries the persistent coefficient and **not** the
  transitory one, because death cannot be retimed;
* the one design switch is keyed to the publishing document, not to a row.
"""

from __future__ import annotations

import math

import pytest

from fiscal_model.data.capital_gains import CapitalGainsBaseline
from fiscal_model.policies import CapitalGainsPolicy, PolicyType
from fiscal_model.validation.cbo_scores import KNOWN_SCORES, validation_shape
from fiscal_model.validation.core import uses_green_book_death_design

YEAR = 2025


def _policy(**kwargs) -> CapitalGainsPolicy:
    defaults = dict(
        name="death channel",
        description="constructive realization at death",
        policy_type=PolicyType.CAPITAL_GAINS_TAX,
        rate_change=0.0,
        affected_income_threshold=0.0,
        start_year=YEAR,
        duration_years=10,
        eliminate_step_up=True,
        step_up_exemption=0.0,
        data_year=2024,
    )
    defaults.update(kwargs)
    return CapitalGainsPolicy(**defaults)


@pytest.fixture(scope="module")
def baseline() -> CapitalGainsBaseline:
    return CapitalGainsBaseline()


@pytest.fixture(scope="module")
def classes(baseline) -> list:
    return baseline.decedent_classes(YEAR)


def _death_channel(policy, slices: int | None = None) -> float:
    """The ten-year death channel, optionally at a different slice count."""
    if slices is not None:
        from fiscal_model.data.capital_gains import CapitalGainsBaseline as _Base

        _Base.DECEDENT_SLICES_PER_REGION = slices
    try:
        return sum(
            policy.estimate_step_up_elimination_revenue(year)
            for year in range(policy.duration_years)
        )
    finally:
        if slices is not None:
            from fiscal_model.data.capital_gains import CapitalGainsBaseline as _Base

            _Base.DECEDENT_SLICES_PER_REGION = 200


# ---------------------------------------------------------------------------
# The data file
# ---------------------------------------------------------------------------


def test_every_ladder_class_has_carveout_shares(baseline, classes):
    """The carve-out file covers the ladder, class for class."""
    assert {row["group"] for _, row in baseline._ladder.iterrows()} == {
        c.group for c in classes
    }
    for decedent_class in classes:
        for share in (
            decedent_class.residence_gain_share,
            decedent_class.active_business_gain_share,
            decedent_class.charitable_bequest_share,
        ):
            assert 0.0 <= share <= 1.0


def test_residence_falls_and_business_rises_with_estate_size(classes):
    """Poterba & Weisbenner Table 8's shape, which is the point of the ladder.

    Below $250,000 of net worth essentially all unrealized gain is in the
    house; above $10 million essentially all of it is in an active business.
    """
    by_group = {c.group: c for c in classes}
    assert by_group["Bottom50"].residence_gain_share > 0.9
    assert by_group["TopPt1"].residence_gain_share < 0.05
    assert by_group["Bottom50"].active_business_gain_share < 0.05
    assert by_group["TopPt1"].active_business_gain_share > 0.7


def test_the_spousal_share_is_carried_and_never_read(baseline):
    """The double count the lane refused to make is in the file, not the model.

    Poterba & Weisbenner's flow already excludes inter-spousal transfers, so a
    spousal deduction would be taken twice. The row stays in the CSV as the
    record of what that would have cost - SOI puts it near a third of the gross
    estate - and the loader must not hand it to anything. Wave 7 moved the file
    to one row per (source, size class, quantity); the ``applied`` column is
    what carries the distinction now.
    """
    frame = baseline._read(CapitalGainsBaseline.CARVEOUT_FILE)
    marital = frame[frame["quantity"] == "marital_bequest_share"]
    assert not marital.empty
    assert marital["share"].max() > 0.2
    assert marital["applied"].astype(str).str.lower().eq("false").all()

    tangible = frame[frame["quantity"] == "tangible_personal_property_gain_share"]
    assert not tangible.empty
    assert tangible["share"].eq(0.0).all()
    assert tangible["applied"].astype(str).str.lower().eq("false").all()

    # Neither reaches the loader, and neither reaches a decedent class.
    assert "marital_bequest_share" not in baseline._carveout_ladders
    assert "tangible_personal_property_gain_share" not in baseline._carveout_ladders
    assert set(baseline.carveout_shares_at(50.0)) == {
        "residence_gain_share",
        "active_business_gain_share",
        "charitable_bequest_share",
    }


# ---------------------------------------------------------------------------
# The size distribution (Wave 7)
# ---------------------------------------------------------------------------


def test_the_fit_reproduces_every_dfa_group_aggregate(baseline):
    """One unknown, one equation, and the equation is the published aggregate.

    The piecewise-Pareto is fitted segment by segment so that each
    Distributional Financial Accounts percentile group's own net worth comes
    back out. If that ever stops holding, the distribution has acquired a free
    parameter and is no longer the DFA's.
    """
    households = baseline._parameters["households_millions"] * 1e6
    slices = baseline.decedent_size_slices()
    published = {
        str(row["group"]): float(row["net_worth_millions_usd"])
        for _, row in baseline._ladder.iterrows()
    }
    for group, aggregate in published.items():
        fitted = sum(
            share * households * mean for share, mean, name in slices if name == group
        )
        assert fitted == pytest.approx(aggregate, rel=1e-9), group
    assert sum(share for share, _, _ in slices) == pytest.approx(1.0, rel=1e-12)


def test_the_fit_is_refused_below_the_ninetieth_percentile(baseline):
    """The two reasons, both in the shipped file, and the model obeying them."""
    frame = baseline._size_distribution
    dispersed = frame[frame["dispersed"].astype(bool)]
    refused = frame[~frame["dispersed"].astype(bool)]
    assert set(dispersed["group"]) == {"TopPt1", "RemainingTop1", "Next9"}
    assert set(refused["group"]) == {"Next40", "Bottom50"}

    # Reason one: no finite-mean Pareto exists there.
    assert (dispersed["pareto_alpha"] > 1.0).all()
    assert (refused["pareto_alpha"] < 1.0).all()

    # Reason two: the median it would imply is twice the SCF's published one.
    median_row = refused[refused["percentile_share_upper"] == 0.5].iloc[0]
    scf = baseline._parameters["scf_2022_median_family_net_worth_thousands"]
    assert float(median_row["threshold_millions_usd"]) * 1e3 > 1.5 * scf
    assert "SCF" in str(median_row["note"])

    # And the model gives each refused group exactly one slice, at its mean.
    slices = baseline.decedent_size_slices()
    ladder = baseline._ladder.set_index("group")
    for group in ("Next40", "Bottom50"):
        rows = [row for row in slices if row[2] == group]
        assert len(rows) == 1
        assert rows[0][1] == pytest.approx(
            float(ladder.loc[group, "mean_net_worth_millions_usd"])
        )


def test_the_level_is_not_this_schedules_to_change(baseline):
    """Gains at death is Poterba & Weisbenner's flow at any slice count."""
    for count in (1, 25, 200, 400):
        classes = baseline.decedent_classes(YEAR, slices_per_region=count)
        total = sum(
            c.decedents_per_year * c.gains_per_decedent_dollars for c in classes
        )
        assert total / 1e9 == pytest.approx(
            baseline.gains_at_death_billions(YEAR), rel=1e-9
        )
        assert sum(c.decedents_per_year for c in classes) == pytest.approx(
            baseline._parameters["households_millions"]
            * 1e6
            * baseline._parameters["estate_flow_rate"],
            rel=1e-9,
        )


def test_the_slice_count_is_quadrature_and_not_a_parameter():
    """Doubling the resolution must not move the answer.

    The slices are a numerical integration of a continuous distribution. If the
    ten-year death channel depended on how many of them there are, the count
    would be a modelling parameter this lane never declared.
    """
    policy = _policy(step_up_exemption=1_000_000.0)
    coarse = _death_channel(policy, slices=100)
    fine = _death_channel(policy, slices=200)
    finer = _death_channel(policy, slices=400)
    assert abs(fine - coarse) / coarse < 0.005
    assert abs(finer - fine) / fine < 0.005


def test_the_exclusion_is_no_longer_a_cliff():
    """The defect item 15 names: an exclusion on point masses is a step function.

    On the five-class ladder, raising the per-donor exclusion knocked out whole
    classes, so the revenue schedule had flats and drops. On a distribution it
    falls smoothly, and the test for "smoothly" is that no single $250,000 step
    of the exclusion removes more than a fifth of what is left.
    """
    previous = None
    for exclusion in range(0, 6_000_000, 250_000):
        revenue = _death_channel(_policy(step_up_exemption=float(exclusion)))
        if previous is not None:
            assert revenue <= previous + 1e-9
            assert previous - revenue < 0.20 * previous
        previous = revenue


def test_the_dead_published_rows_are_alive_where_the_fit_reaches(baseline):
    """Seven of eighteen published rows were never read. Six of them now are.

    The five class means read Poterba & Weisbenner's six published rows at four
    points, Avery, Grodzicki & Moore's eight at four and SOI's four at three.
    Every band above the 90th percentile now contains a slice. The one that is
    still dark is PW's $250,000-$500,000 class, which lies inside the region the
    fit refuses (``test_the_fit_is_refused_below_the_ninetieth_percentile``) and
    where the two remaining group means fall either side of it - so the lane
    says which row is still unread rather than claiming all eighteen.
    """
    estates = [mean for _, mean, _ in baseline.decedent_size_slices()]

    def covered(lower: float, upper: float) -> bool:
        return any(lower <= estate < upper for estate in estates)

    frame = baseline._read(CapitalGainsBaseline.CARVEOUT_FILE)
    frame = frame[frame["applied"].astype(str).str.lower() == "true"]
    bands = {
        (
            float(row["size_class_lower_millions_usd"]),
            float(row["size_class_upper_millions_usd"]),
        )
        for _, row in frame.iterrows()
    }
    agm_lowers = [bound for bound, _ in baseline._agm_ladder]
    bands |= set(zip(agm_lowers, agm_lowers[1:] + [float("inf")]))

    dark = sorted(band for band in bands if not covered(*band))
    assert dark == [(0.25, 0.5)], dark
    # And every band the fit reaches is read.
    threshold = float(
        baseline._size_distribution.set_index("group").loc[
            "Next9", "threshold_millions_usd"
        ]
    )
    for lower, upper in sorted(bands):
        if lower >= threshold:
            assert covered(lower, upper), f"${lower}M-${upper}M"


def test_the_open_top_slice_is_one_household(baseline):
    """The top of an open-ended Pareto is cut somewhere; here it is cut at one.

    A bound with a meaning, and one with an external check: the conditional mean
    above it is the fitted net worth of the single richest household, which on
    the shipped Distributional Financial Accounts vintage comes out in the
    hundreds of billions - the order of magnitude the published wealth lists put
    it at, without any of this being fitted to them.
    """
    households = baseline._parameters["households_millions"] * 1e6
    top = baseline.decedent_size_slices()[0]
    assert top[2] == "TopPt1"
    assert top[0] * households == pytest.approx(1.0)
    assert 100_000.0 < top[1] < 1_000_000.0  # $100B-$1T, in millions


def test_each_slice_reads_the_ladders_at_its_own_estate_size(baseline):
    """No slice straddles a published boundary, and none reads a group mean."""
    classes = baseline.decedent_classes(YEAR)
    for decedent_class in classes:
        estate = decedent_class.net_worth_millions_usd
        expected = baseline.carveout_shares_at(estate)
        assert decedent_class.residence_gain_share == pytest.approx(
            min(1.0, expected["residence_gain_share"])
        )
        assert decedent_class.active_business_gain_share == pytest.approx(
            min(1.0, expected["active_business_gain_share"])
        )
        assert decedent_class.charitable_bequest_share == pytest.approx(
            expected["charitable_bequest_share"]
        )
        assert decedent_class.unrealized_gain_share == pytest.approx(
            baseline.unrealized_gain_share_at(estate)
        )
    # A distribution, not five points: the top decile spans three orders of
    # magnitude of estate size and the shares vary across it.
    top = [c for c in classes if c.group in {"TopPt1", "RemainingTop1", "Next9"}]
    assert len({c.charitable_bequest_share for c in top}) >= 3
    assert len({c.unrealized_gain_share for c in top}) >= 4


def test_the_charitable_floor_is_a_rule_about_soi_coverage(baseline):
    """SOI's table is estate-tax filers; a small estate gets no share at all."""
    floor = baseline._parameters["soi_estate_charitable_floor_millions_usd"]
    assert baseline.carveout_shares_at(floor * 0.99)["charitable_bequest_share"] == 0.0
    assert baseline.carveout_shares_at(floor * 1.01)["charitable_bequest_share"] > 0.0


def test_the_soi_decedent_count_is_a_check_and_not_an_input(baseline):
    """SOI's own return count against the fitted distribution's implied one.

    SOI Estate Tax Table 1 reports the estates that actually filed above the
    threshold; the fitted distribution says how many decedents it puts there.
    The two are the same order of magnitude and neither feeds the other - the
    figure is in the parameters file marked CHECK ONLY, and nothing multiplies
    by it.
    """
    threshold = baseline._parameters["soi_fy2024_estate_filing_threshold_millions_usd"]
    published = baseline._parameters["soi_fy2024_estate_returns_above_filing_threshold"]
    implied = sum(
        c.decedents_per_year
        for c in baseline.decedent_classes(YEAR)
        if c.net_worth_millions_usd >= threshold
    )
    assert 0.4 < implied / published < 2.5
    # The check is not wired into anything: the whole channel is unchanged when
    # the published count is not read, because it never is.
    frame = baseline._read(CapitalGainsBaseline.PARAMETER_FILE)
    row = frame[frame["key"] == "soi_fy2024_estate_returns_above_filing_threshold"]
    assert "CHECK ONLY" in str(row["source"].iloc[0])


# ---------------------------------------------------------------------------
# The carve-outs
# ---------------------------------------------------------------------------


def test_carveouts_reduce_the_reachable_gain(classes):
    """Charity and section 121 both bite, and turning them off restores the base."""
    with_carveouts = _policy()
    without = _policy(apply_death_carveouts=False)
    for decedent_class in classes:
        reachable = with_carveouts.reachable_gains_per_decedent(decedent_class, 0.238)
        bare = without.reachable_gains_per_decedent(decedent_class, 0.238)
        assert bare == pytest.approx(decedent_class.gains_per_decedent_dollars)
        assert reachable <= bare + 1e-9


def test_section_121_erases_a_small_decedent_and_barely_touches_a_large_one(classes):
    """The statutory cap is what makes the exclusion regressive in relative terms."""
    policy = _policy()
    by_group = {c.group: c for c in classes}
    small = by_group["Bottom50"]
    large = by_group["TopPt1"]
    assert small.gains_per_decedent_dollars < policy.section_121_exclusion
    assert policy.reachable_gains_per_decedent(small, 0.0) == pytest.approx(0.0)
    reached = policy.reachable_gains_per_decedent(large, 0.238)
    assert reached > 0.5 * large.gains_per_decedent_dollars


def test_the_charitable_share_rises_with_the_rate_it_avoids(classes):
    """The avoidance channel: a higher rate makes a charitable bequest cheaper."""
    policy = _policy()
    top = next(c for c in classes if c.group == "TopPt1")
    low = policy._charitable_share_at_death(top, 0.238)
    high = policy._charitable_share_at_death(top, 0.434)
    assert top.charitable_bequest_share < low < high <= 1.0
    # A class with no charitable bequests in SOI gets no induced ones either.
    bottom = next(c for c in classes if c.group == "Bottom50")
    assert policy._charitable_share_at_death(bottom, 0.434) == 0.0


def test_a_bigger_price_elasticity_gives_a_bigger_response(classes):
    """The frozen 1.617 is the smallest in its own table; (d) would cut more."""
    top = next(c for c in classes if c.group == "TopPt1")
    small = _policy(charitable_bequest_price_elasticity=1.617)
    large = _policy(charitable_bequest_price_elasticity=2.142)
    assert large._charitable_share_at_death(top, 0.434) > small._charitable_share_at_death(
        top, 0.434
    )
    assert large.estimate_step_up_elimination_revenue(
        0
    ) < small.estimate_step_up_elimination_revenue(0)


def test_the_family_business_deferral_only_defers(classes):
    """Within the window, deferred gains come back at the module's own hazard."""
    deferred = _policy(defer_family_business_gains=True)
    immediate = _policy(defer_family_business_gains=False)
    top = next(c for c in classes if c.group == "TopPt1")
    year_one = deferred.reachable_gains_per_decedent(top, 0.238, 0.0, 0)
    year_ten = deferred.reachable_gains_per_decedent(top, 0.238, 0.0, 9)
    assert year_one < year_ten  # recapture accumulates
    assert year_ten < immediate.reachable_gains_per_decedent(top, 0.238, 0.0, 9)
    assert deferred.estimate_step_up_elimination_revenue(
        0
    ) < immediate.estimate_step_up_elimination_revenue(0)


def test_the_per_donor_exclusion_applies_after_the_carveouts():
    """Both Green Books grant it against *other* unrealized capital gains.

    Applying it first would leave a much larger base, so the ordering is worth
    a test rather than a comment.
    """
    after = _policy(step_up_exemption=1_000_000.0)
    revenue_after = after.estimate_step_up_elimination_revenue(0)
    bare = _policy(step_up_exemption=1_000_000.0, apply_death_carveouts=False)
    assert revenue_after < bare.estimate_step_up_elimination_revenue(0)
    # And a larger exclusion always collects less.
    larger = _policy(step_up_exemption=5_000_000.0)
    assert larger.estimate_step_up_elimination_revenue(0) < revenue_after


# ---------------------------------------------------------------------------
# The behavioural response
# ---------------------------------------------------------------------------


def test_the_death_response_is_persistent_only():
    """Death cannot be retimed, so the transitory coefficient has no place."""
    policy = _policy(rate_change=0.196, affected_income_threshold=1_000_000.0)
    expected = policy.persistent_elasticity / policy.elasticity_reference_rate
    expected /= policy.lock_in_wedge()
    assert policy.death_response_coefficient() == pytest.approx(expected)
    # The realizations coefficient in the enactment year carries the transitory
    # term on top of exactly this; the death coefficient must not.
    realizations = policy.semi_log_coefficient(years_since_start=0, long_term_share=1.0)
    assert realizations > policy.death_response_coefficient()
    assert policy.semi_log_coefficient(
        years_since_start=1
    ) == pytest.approx(policy.death_response_coefficient())


def test_a_rate_change_shrinks_gains_at_death_semi_logarithmically(classes):
    """`exp(-b dtau)` on the decedents the rate change reaches, and only those."""
    policy = _policy(rate_change=0.196, affected_income_threshold=1_000_000.0)
    top = next(c for c in classes if c.group == "TopPt1")
    unresponsive = policy.reachable_gains_per_decedent(top, 0.434, 0.0)
    responsive = policy.reachable_gains_per_decedent(top, 0.434, 0.196)
    assert responsive == pytest.approx(
        unresponsive * math.exp(-policy.death_response_coefficient() * 0.196)
    )


def test_a_proposal_that_changes_no_rate_gets_no_rate_response(classes):
    """CBO Option 51 charges the statutory rate, so this channel is inert for it."""
    policy = _policy(rate_change=0.0)
    for decedent_class in classes:
        assert policy.reachable_gains_per_decedent(
            decedent_class, 0.238, 0.0
        ) == pytest.approx(policy.reachable_gains_per_decedent(decedent_class, 0.238))


# ---------------------------------------------------------------------------
# The one design switch
# ---------------------------------------------------------------------------


def test_the_green_book_design_rule_keys_on_the_document():
    """GREEN_BOOK_DEATH_DESIGN_RULE, and the alternative key that agrees with it.

    The rule selects the Green Book rows by publisher. Keying instead on "the
    record does not state a zero per-donor exclusion" must pick the same rows;
    if the two ever diverge, the rule has become a per-row switch and this test
    says so. (The FY2022 record leaves the exclusion unset and inherits the
    module default, so the key is "not stated as zero" rather than "positive" -
    a correction the lane recorded in its own outturn.)
    """
    death_rows = [
        score
        for score in KNOWN_SCORES.values()
        if validation_shape(score) == "capital_gains"
        and score.eliminate_step_up
        # A record with a specialized runner is built by ``scenarios.py``, not
        # by ``create_policy_from_score``, so the rule never sees it.
        and not score.specialized_runner
    ]
    assert death_rows, "no realization-at-death records to check"
    by_publisher = {s.policy_id for s in death_rows if uses_green_book_death_design(s)}
    by_exclusion = {s.policy_id for s in death_rows if s.step_up_exemption != 0}
    assert by_publisher == by_exclusion
    assert "cbo_opt51_gains_at_death" not in by_publisher


def test_option_51_scores_the_bare_construction_its_own_text_describes():
    """No exclusion, no deferral, no rate change - and the carve-outs still apply."""
    from fiscal_model.validation.core import create_policy_from_score

    policy = create_policy_from_score(KNOWN_SCORES["cbo_opt51_gains_at_death"])
    assert policy.eliminate_step_up is True
    assert policy.defer_family_business_gains is False
    assert policy.step_up_exemption == 0.0
    assert policy.apply_death_carveouts is True


def test_the_two_green_book_rows_carry_their_own_documents_exclusions():
    from fiscal_model.validation.core import create_policy_from_score

    fy2025 = create_policy_from_score(KNOWN_SCORES["biden_capital_gains_39"])
    fy2022 = create_policy_from_score(
        KNOWN_SCORES["treasury_capgains_39_plus_stepup_elim"]
    )
    assert fy2025.step_up_exemption == 5_000_000.0  # FY2025 GB, report p. 81
    assert fy2022.step_up_exemption == 1_000_000.0  # FY2022 GB, report p. 63
    for policy in (fy2025, fy2022):
        assert policy.defer_family_business_gains is True
        assert policy.rate_change == pytest.approx(0.196)
    # Same rate channel, so the exclusion is the only thing that separates them.
    assert fy2025.estimate_step_up_elimination_revenue(
        0
    ) < fy2022.estimate_step_up_elimination_revenue(0)


def test_validation_parameters_are_not_per_case():
    """No behavioural or carve-out parameter varies by row."""
    from fiscal_model.validation.core import create_policy_from_score

    policies = [
        create_policy_from_score(KNOWN_SCORES[pid])
        for pid in (
            "cbo_opt51_gains_at_death",
            "biden_capital_gains_39",
            "treasury_capgains_39_plus_stepup_elim",
        )
    ]
    for field in (
        "persistent_elasticity",
        "transitory_elasticity",
        "elasticity_reference_rate",
        "section_121_exclusion",
        "charitable_bequest_price_elasticity",
    ):
        values = {getattr(policy, field) for policy in policies}
        assert len(values) == 1, f"{field} varies across rows: {values}"


# ---------------------------------------------------------------------------
# The user-facing note (Decision 6)
# ---------------------------------------------------------------------------


def _tailor_policy(**kwargs) -> CapitalGainsPolicy:
    """A policy shaped the way Tailor's capital-gains form builds one."""
    defaults = dict(
        name="Tax Rate Change",
        description="capital gains",
        policy_type=PolicyType.CAPITAL_GAINS_TAX,
        rate_change=0.0,
        affected_income_threshold=0,
        data_year=2024,
        duration_years=10,
        phase_in_years=1,
        baseline_capital_gains_rate=0.238,
        baseline_realizations_billions=0.0,
        realization_elasticity=0.72,
        persistent_elasticity=0.72,
        transitory_elasticity=1.20,
        use_time_varying_elasticity=True,
        step_up_at_death=True,
        eliminate_step_up=False,
        step_up_exemption=0.0,
    )
    defaults.update(kwargs)
    policy = CapitalGainsPolicy(**defaults)
    # Tailor zeroes both so the SOI baseline auto-populates.
    policy.baseline_realizations_billions = 0.0
    policy.baseline_capital_gains_rate = 0.0
    return policy


def _score(policy):
    from fiscal_model import FiscalPolicyScorer

    return FiscalPolicyScorer(baseline=None, use_real_data=True).score_policy(
        policy, dynamic=False
    )


def test_the_note_ships_with_the_number_that_moved():
    """Decision 6: Tailor's step-up rows moved, so they carry an explanation.

    The note has to say the three things that make the figure smaller than
    "gains at death times the rate": the charitable exclusion, section 121, and
    that the per-donor exclusion applies to what is left. It must also say the
    two reliefs the model does *not* deduct, or a reader who knows the Green
    Books will think they were forgotten.
    """
    from fiscal_model.ui.tabs.results_summary import gains_at_death_caption

    policy = _tailor_policy(eliminate_step_up=True, step_up_exemption=1_000_000.0)
    caption = gains_at_death_caption(policy, _score(policy))
    assert "charity" in caption
    assert "section 121" in caption
    assert "$250,000" in caption.replace("\\", "")
    assert "$1,000,000 per-decedent exclusion" in caption.replace("\\", "")
    assert "to what is left, not to the whole gain" in caption
    assert "Inter-spousal transfers and tangible personal property" in caption
    # Wave 7: and that the exclusion meets a spread of estates, not an average.
    assert "fitted distribution of estate sizes" in caption


def test_the_note_reports_the_scorer_s_own_death_channel():
    """Computed by replaying the scorer's loop, so it cannot drift."""
    from fiscal_model.ui.tabs.results_summary import gains_at_death_caption

    with_death = _tailor_policy(eliminate_step_up=True, step_up_exemption=0.0)
    without = _tailor_policy(eliminate_step_up=False)
    headline = float(sum(_score(with_death).final_deficit_effect))
    rate_only = float(sum(_score(without).final_deficit_effect))
    caption = gains_at_death_caption(with_death, _score(with_death))
    reported = float(
        caption.split("Gains at death: ")[1]
        .split("B of")[0]
        .replace("\\$", "")
        .replace(",", "")
    )
    # No rate change, so the whole score is the death channel and there is no
    # behavioural offset between the static figure and the headline.
    assert rate_only == pytest.approx(0.0, abs=1e-9)
    # The caption rounds to one decimal; that is the only difference allowed.
    assert reported == pytest.approx(headline, abs=0.05)


def test_the_note_says_when_a_design_states_no_exclusion():
    from fiscal_model.ui.tabs.results_summary import gains_at_death_caption

    policy = _tailor_policy(eliminate_step_up=True, step_up_exemption=0.0)
    assert "states no per-decedent exclusion" in gains_at_death_caption(
        policy, _score(policy)
    )


def test_no_note_where_there_is_no_death_channel():
    """A rate change that keeps step-up gets no note, and neither does anything
    that is not a capital-gains policy."""
    from fiscal_model.ui.tabs.results_summary import gains_at_death_caption

    keeps_step_up = _tailor_policy(rate_change=0.05, affected_income_threshold=1_000_000)
    assert gains_at_death_caption(keeps_step_up, _score(keeps_step_up)) == ""
    not_scored = _tailor_policy(eliminate_step_up=True, score_gains_at_death=False)
    assert gains_at_death_caption(not_scored, _score(not_scored)) == ""
    assert gains_at_death_caption(object(), None) == ""
