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
    spousal deduction would be taken twice. The column stays in the CSV as the
    record of what that would have cost - SOI puts it near a third of the gross
    estate - and the loader must not hand it to anything.
    """
    frame = baseline._read(CapitalGainsBaseline.CARVEOUT_FILE)
    assert frame["marital_bequest_share"].max() > 0.2
    for shares in baseline._carveouts.values():
        assert "marital_bequest_share" not in shares
    assert frame["tangible_personal_property_gain_share"].eq(0.0).all()


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
