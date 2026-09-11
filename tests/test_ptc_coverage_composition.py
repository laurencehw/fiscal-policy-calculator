"""Lane HSD/H11 — the PTC coverage response, priced channel by channel.

Pre-registration: ``planning/lanes/HSD_h11_ptc_coverage.md``. Every figure
asserted here was computed from the transcribed tables *before*
``fiscal_model/ptc.py`` was edited, and the lane's §4 falsification tests are
the ones marked as such below.

The claim under test is not "19.28% was the wrong size". It is that **a ratio is
the wrong object**: the effects it aggregates are responses to people moving
between sources of coverage, so they scale with person-years, and a repeal
removes a very different number of people per dollar of credit than an extension
attracts.
"""

import csv

import pytest

from fiscal_model.ptc import (
    CBO_OFFSETTING_SHARE,
    PTC_CHANNELS_PATH,
    PTC_ENROLLMENT_PATH,
    CoverageChange,
    CoverageChannelRates,
    DestinationSplit,
    baseline_credit_cost,
    cbo_channel,
    create_extend_enhanced_ptc,
    create_repeal_ptc,
    offsetting_effects,
    published_extension_coverage,
    published_extension_insured,
    repeal_offsetting_share,
    subsidized_enrollment,
    subsidized_enrollment_by_year,
)
from fiscal_model.scoring import FiscalPolicyScorer

# ---------------------------------------------------------------------------
# The transcription reproduces CBO's own printed arithmetic (falsification 4)
# ---------------------------------------------------------------------------


def test_the_letters_direct_spending_line_sums_to_what_cbo_prints():
    """60437 report p. 4: $275B of direct spending, itemised on the same page."""
    total = (
        cbo_channel("budget", "credit_outlays")
        + cbo_channel("budget", "medicaid_chip")
        + cbo_channel("budget", "basic_health_program_and_1332")
        + cbo_channel("budget", "other_outlay_effects")
    )
    assert total == pytest.approx(275.0)


def test_the_letters_revenue_line_sums_to_what_cbo_prints():
    """60437 report p. 4: "revenues would decrease by $60 billion ... because of
    three partially offsetting effects"."""
    total = (
        -cbo_channel("budget", "credit_revenue_reductions")
        + cbo_channel("budget", "employment_based_to_taxable_wages")
        + cbo_channel("budget", "employer_mandate_penalties")
    )
    assert total == pytest.approx(-60.0)


def test_the_two_legs_give_cbos_deficit_and_its_gross():
    """275 + 60 = 335, the figure Table 2 prints as 335,045 millions."""
    outlays = 275.0
    revenues = -60.0
    assert outlays - revenues == pytest.approx(
        cbo_channel("budget", "net_deficit_printed")
    )
    # The two credit legs sum to 414 against CBO's printed 415: its own rounding
    # to the billion, recorded in the data file's header.
    summed = cbo_channel("budget", "credit_outlays") + cbo_channel(
        "budget", "credit_revenue_reductions"
    )
    assert summed == pytest.approx(414.0)
    assert cbo_channel("budget", "credit_gross_printed") == pytest.approx(415.0)


def test_the_five_coverage_lines_give_cbos_own_insured_change():
    """60437 report p. 5: 6.9 + 0.5 - 0.5 - 3.5 = 3.4, exactly as printed."""
    total = (
        cbo_channel("coverage", "marketplace_net")
        + cbo_channel("coverage", "medicaid_chip")
        + cbo_channel("coverage", "nongroup_outside_marketplaces")
        + cbo_channel("coverage", "employment_based")
    )
    assert total == pytest.approx(cbo_channel("coverage", "insured"))


def test_the_fpl_bands_sum_to_the_marginal_enrollment_and_meet_the_esi_decline():
    """60437 Table 3, p. 10 — and the identity §1.7(a) rests on.

    The four bands above 400% FPL total 3.5M, which is the decline in
    employment-based coverage to the decimal, and report p. 6 says that decline
    "would affect people with higher incomes". That is the strongest available
    statement about where the ESI channel lives, and the lane declines to turn
    it into a zero for the repeal.
    """
    below = cbo_channel("fpl", "below_400_enrollees")
    above = cbo_channel("fpl", "above_400_enrollees")
    assert below + above == pytest.approx(
        cbo_channel("coverage", "marketplace_net"), abs=0.05
    )
    assert above == pytest.approx(abs(cbo_channel("coverage", "employment_based")))


def test_every_transcribed_row_carries_a_document_and_a_page():
    """A figure without a reference is the thing this lane exists to remove."""
    with PTC_CHANNELS_PATH.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(line for line in handle if not line.startswith("#")))
    assert rows
    for row in rows:
        assert row["document"].strip(), row
        assert row["page"].strip(), row


# ---------------------------------------------------------------------------
# The rates, and the identity they must satisfy (falsification 4)
# ---------------------------------------------------------------------------


def test_the_channel_rates_are_cbos_own_dollars_over_cbos_own_people():
    rates = CoverageChannelRates.from_published()
    # ($101B + $3B) / (3.5M x 10 years)
    assert rates.employment_based == pytest.approx(2971.43, abs=0.01)
    # $21B / (0.5M x 10 years)
    assert rates.medicaid_chip == pytest.approx(4200.0, abs=0.01)
    # ($17B - $13B) / (6.9M x 10 years)
    assert rates.marketplace_adjacent == pytest.approx(57.97, abs=0.01)


def test_the_rates_reproduce_the_letters_own_offsetting_total():
    """The identity check. Nothing here is free: handed 60437's own coverage
    vector, the rates return the letter's own itemised $79B.

    CBO prints $80B and its own lines itemise to $79B — the rounding the data
    file's header records. The $0.06B residual on top of that is the same
    rounding once more: the rate's denominator is CBO's printed net marketplace
    change of 6.9M, and its two components print as 7.4 and -0.6.
    """
    effects = offsetting_effects(published_extension_coverage())

    assert effects.employment_based == pytest.approx(-104.0, abs=0.01)
    assert effects.medicaid_chip == pytest.approx(21.0, abs=0.01)
    assert effects.marketplace_adjacent == pytest.approx(4.0, abs=0.07)
    assert effects.uninsured == 0.0
    assert effects.total == pytest.approx(-79.0, abs=0.1)

    share = -effects.total / cbo_channel("budget", "credit_gross_printed")
    assert share == pytest.approx(0.19036, abs=0.001)
    # Against the headline ratio PR #131 transferred.
    assert CBO_OFFSETTING_SHARE == pytest.approx(0.192771, abs=1e-6)


def test_the_uninsured_channel_is_priced_at_exactly_nothing():
    """A person who leaves the marketplace for nothing costs these lines nothing.

    That is the composition's whole content in one assertion: a share cannot
    express it, because a share prices every destination the same.
    """
    only_uninsured = CoverageChange(
        marketplace_subsidized=-10.0, uninsured=10.0, years=10.0
    )
    effects = offsetting_effects(only_uninsured)
    assert effects.employment_based == 0.0
    assert effects.medicaid_chip == 0.0
    assert effects.uninsured == 0.0
    # Only the marketplace-adjacent line fires, on the marketplace movement.
    assert effects.total == pytest.approx(-5.797, abs=0.01)


def test_the_channels_reverse_with_the_coverage_movement():
    """What a single share cannot do, and the sign defect it hid.

    Under the extension employment-based coverage shrinks and the exclusion's
    revenue arrives; under a repeal it grows and the exclusion is reinstated.
    Medicaid runs the other way for the same published reason — CBO's Medicaid
    increase is driven by employers dropping offers, so restoring them lowers
    it. A single scaled ratio books the Medicaid line in the *eroding*
    direction under a repeal, which is backwards.
    """
    extension = published_extension_coverage()
    forward = offsetting_effects(extension)
    reverse = offsetting_effects(
        CoverageChange(
            marketplace_subsidized=-extension.marketplace_subsidized,
            marketplace_unsubsidized=-extension.marketplace_unsubsidized,
            employment_based=-extension.employment_based,
            medicaid_chip=-extension.medicaid_chip,
            nongroup_outside=-extension.nongroup_outside,
            uninsured=-extension.uninsured,
            years=extension.years,
        )
    )
    assert forward.employment_based < 0 < reverse.employment_based
    assert reverse.medicaid_chip < 0 < forward.medicaid_chip
    assert reverse.total == pytest.approx(-forward.total)


# ---------------------------------------------------------------------------
# Publication 51298 Table 1 — the "19 million", replaced
# ---------------------------------------------------------------------------


def test_the_enrollment_table_carries_the_same_two_vintages_as_the_cost_table():
    """A score and the coverage figure printed beside it come from one document."""
    with PTC_ENROLLMENT_PATH.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(line for line in handle if not line.startswith("#")))
    assert {row["vintage"] for row in rows} == {"cbo_jun_2024", "cbo_feb_2026"}


def test_subsidized_enrollment_is_cbos_own_cells_across_the_lapse():
    """51298 Feb 2026 Table 1, p. 2 of 5 — the ARPA/IRA enhancement lapsing."""
    table = subsidized_enrollment_by_year("cbo_feb_2026")
    assert table[2025] == pytest.approx(20.9)
    assert table[2026] == pytest.approx(13.4)
    assert table[2027] == pytest.approx(10.3)
    # June 2024, the vintage the carried target came from, still has the
    # enhancement in force in its first year.
    assert subsidized_enrollment_by_year("cbo_jun_2024")[2025] == pytest.approx(21.3)


def test_an_untranscribed_vintage_raises_rather_than_borrowing_another_one():
    """Reporting a February 2026 figure as June 2024's would be a false
    provenance claim, so the caller decides. Same rule as the cost table's."""
    with pytest.raises(KeyError):
        subsidized_enrollment_by_year("cbo_jan_2025")


def test_enrollment_holds_its_end_levels_rather_than_compounding_a_step():
    table = subsidized_enrollment_by_year("cbo_feb_2026")
    years = sorted(table)
    assert subsidized_enrollment(years[0] - 5) == pytest.approx(table[years[0]])
    assert subsidized_enrollment(years[-1] + 5) == pytest.approx(table[years[-1]])


def test_the_repeal_no_longer_says_nineteen_million():
    """``MARKETPLACE_DATA``'s uncited figure, replaced by CBO's own table.

    19.0M is nearer calendar 2025's 20.9M — the last year of the enhancement —
    than anything inside the window the app scores.
    """
    effect = create_repeal_ptc().estimate_coverage_effect()
    assert effect["coverage_change_millions"] == pytest.approx(-11.06, abs=0.01)
    assert effect["coverage_change_millions"] != pytest.approx(-19.0)
    # And it now says where they went.
    assert effect["employment_based_change_millions"] == pytest.approx(5.231, abs=0.01)
    assert effect["uninsured_change_millions"] == pytest.approx(5.082, abs=0.01)
    assert effect["medicaid_chip_change_millions"] == pytest.approx(-0.747, abs=0.01)


def test_the_extension_reports_the_composition_in_reverse_and_moves_no_dollar():
    """§1.5: the extension sees the same lines and keeps its fitted annual."""
    effect = create_extend_enhanced_ptc().estimate_coverage_effect()
    assert effect["coverage_change_millions"] == pytest.approx(7.4)
    assert effect["employment_based_change_millions"] == pytest.approx(-3.5)
    assert effect["medicaid_chip_change_millions"] == pytest.approx(0.5)
    assert effect["uninsured_change_millions"] == pytest.approx(-3.4)
    # CBO/JCT pub. 61734 Table 2, on the app's own FY2026-2035 window.
    assert effect["insured_change_millions"] == pytest.approx(3.48, abs=0.005)


def test_the_later_vintage_corroborates_the_coverage_side_of_the_letter():
    """61734 (Sept 2025) averages 3.48M against 60437's 3.4M on the earlier
    window — evidence the coverage side has not been revised out from under the
    composition priced off it."""
    assert published_extension_insured() == pytest.approx(3.48, abs=0.005)
    assert abs(published_extension_insured() - 3.4) / 3.4 < 0.03


# ---------------------------------------------------------------------------
# The share, and the score (falsification 1 and 2)
# ---------------------------------------------------------------------------


def test_the_repeals_share_is_computed_from_its_own_population():
    """12.32% on February 2026, not the transferred 19.28%.

    The mechanism in one line: the offsets scale with people and the gross with
    dollars, and a repeal's average enrollee holds an $8,671 credit where the
    extension's marginal enrollee holds the $5,370 CBO prints in Table 3.
    """
    share = repeal_offsetting_share(2026, 10, "cbo_feb_2026")
    assert share == pytest.approx(0.123211, abs=1e-6)
    assert share < CBO_OFFSETTING_SHARE

    window = range(2026, 2036)
    gross = sum(baseline_credit_cost(year, "cbo_feb_2026") for year in window)
    person_years = sum(subsidized_enrollment(year, "cbo_feb_2026") for year in window)
    assert gross == pytest.approx(959.0)
    assert person_years == pytest.approx(110.6, abs=0.01)
    assert gross * 1e3 / person_years == pytest.approx(8671.0, abs=1.0)
    assert cbo_channel("rate", "marginal_enrollee_average_credit") == 5370.0


def test_the_share_differs_by_vintage_because_the_population_does():
    """A transferred ratio cannot do this: it is the same number on both."""
    feb = repeal_offsetting_share(2026, 10, "cbo_feb_2026")
    jun = repeal_offsetting_share(2025, 10, "cbo_jun_2024")
    assert feb == pytest.approx(0.123211, abs=1e-6)
    assert jun == pytest.approx(0.136932, abs=1e-6)
    assert jun > feb


def test_the_share_follows_a_window_moved_after_the_factory_returned():
    """``preset_handler._open_no_earlier_than`` mutates ``start_year``, so the
    share is resolved per call rather than frozen at construction."""
    policy = create_repeal_ptc(start_year=2025)
    before = policy.resolved_offset_share()
    policy.start_year = 2026
    assert policy.resolved_offset_share() != pytest.approx(before)
    assert policy.resolved_offset_share() == pytest.approx(0.123211, abs=1e-6)


def test_the_shipped_repeal_score():
    """The lane's pre-registered figure, computed before ``ptc.py`` was opened."""
    scorer = FiscalPolicyScorer(start_year=2026, use_real_data=False)
    result = scorer.score_policy(create_repeal_ptc(), dynamic=False)
    assert float(result.total_10_year_cost) == pytest.approx(-840.84, abs=0.05)


def test_the_extension_benchmark_does_not_move(  # falsification 2
):
    """Any movement is a leakage failure, not a finding: the only published
    quantity that would drive a derived extension path is CBO's own score of
    that same policy, which is its target."""
    policy = create_extend_enhanced_ptc()
    assert policy.resolved_offset_share() is None
    scorer = FiscalPolicyScorer(start_year=2026, use_real_data=False)
    result = scorer.score_policy(policy, dynamic=False)
    assert float(result.total_10_year_cost) == pytest.approx(366.1863, abs=0.001)


def test_the_june_2024_demonstration_is_unmoved_by_this_lane():  # falsification 1
    """The lane is falsified if the module reproduces -$1,100B.

    It does not, and the reason the target is refused is unchanged: run on the
    vintage and window it came from with **no** coverage response, the
    mechanism returns $1,143B against CBO's own $1,142B — 0.09%, which is what
    a model reading a baseline table reproducing a baseline projection looks
    like. This lane touches only the coverage response, so this figure must not
    have moved.
    """
    scorer = FiscalPolicyScorer(start_year=2025, use_real_data=False)
    policy = create_repeal_ptc(start_year=2025, baseline_vintage="cbo_jun_2024")
    policy.coverage_offset_share = 0.0
    result = scorer.score_policy(policy, dynamic=False)

    gross = float(result.total_10_year_cost)
    assert gross == pytest.approx(-1143.0, abs=0.01)
    assert abs(abs(gross) - 1142.0) / 1142.0 < 0.001

    # And the shipped score is nowhere near the carried target.
    shipped = FiscalPolicyScorer(start_year=2026, use_real_data=False).score_policy(
        create_repeal_ptc(), dynamic=False
    )
    error = abs(abs(float(shipped.total_10_year_cost)) - 1100.0) / 1100.0
    assert error == pytest.approx(0.2356, abs=0.001)
    assert error > 0.20  # still rated Poor; no threshold was crossed


# ---------------------------------------------------------------------------
# §1.7 — the two asymmetries, measured and deliberately not shipped
# ---------------------------------------------------------------------------


def test_the_esi_concentration_is_measured_and_not_taken():
    """§1.7(a). Zeroing the ESI channel gives 9.43% against the carried target,
    and that is exactly why it is not done: "most" and "would affect people
    with higher incomes" do not license a zero, and §36B(c)(2)(C) bars only an
    *affordable* offer, so a repeal does reach people with an employer.

    The assertion that matters is the second one — the shipped path is **not**
    the flattering one.
    """
    window = range(2026, 2036)
    gross = sum(baseline_credit_cost(year, "cbo_feb_2026") for year in window)
    person_years = sum(subsidized_enrollment(year, "cbo_feb_2026") for year in window)
    average = person_years / len(list(window))
    split = DestinationSplit.from_published()
    no_esi = CoverageChange(
        marketplace_subsidized=-average,
        marketplace_unsubsidized=average * split.marketplace_unsubsidized,
        employment_based=0.0,
        medicaid_chip=-average * split.medicaid_chip,
        uninsured=average * split.uninsured,
        years=float(len(list(window))),
    )
    score = -(gross - offsetting_effects(no_esi).total)
    assert score == pytest.approx(-996.28, abs=0.5)

    would_be = abs(abs(score) - 1100.0) / 1100.0
    shipped = 0.2356
    assert would_be == pytest.approx(0.0943, abs=0.001)
    assert would_be < shipped, (
        "the unshipped variant is nearer the refused target, which is the "
        "reason it is unshipped"
    )


def test_the_destination_split_is_a_named_transfer_not_a_hidden_one():
    """The split is the one input a repeal has no document for, so it is an
    object with a docstring rather than a number folded into a ratio."""
    split = DestinationSplit.from_published()
    assert split.employment_based == pytest.approx(3.5 / 7.4)
    assert split.medicaid_chip == pytest.approx(0.5 / 7.4)
    assert split.uninsured == pytest.approx(3.4 / 7.4)
    doc = DestinationSplit.__doc__ or ""
    assert "400% FPL" in doc
    assert "36B(c)(2)(C)" in doc
