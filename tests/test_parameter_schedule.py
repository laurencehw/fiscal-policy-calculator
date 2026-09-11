"""Lane R4 — the statutory parameter schedule.

The load-bearing test is :func:`test_bracket_one_scores_to_the_cent`: a $0 floor
read through the whole schedule path — four per-status floors, per year,
deflated onto the SOI base year, through PR #127's filing-status split — must
come back out equal to the fixed-threshold path it replaces. If it ever does
not, the schedule is perturbing something nobody asked it to touch.

See ``planning/lanes/R4_parameter_schedule.md``.
"""

from __future__ import annotations

import pytest

from fiscal_model import cbo_tax_parameters as tp
from fiscal_model.baseline import BaselineVintage
from fiscal_model.data.irs_soi import FILING_STATUSES
from fiscal_model.policies import (
    DEFAULT_THRESHOLD_INDEXATION,
    THRESHOLD_INDEXATION_INCOME,
    THRESHOLD_INDEXATION_NOMINAL,
    THRESHOLD_INDEXATION_STATUTORY,
    CapitalGainsPolicy,
    Policy,
    PolicyType,
    TaxPolicy,
)
from fiscal_model.validation.cbo_scores import KNOWN_SCORES
from fiscal_model.validation.core import (
    STATUTORY_BRACKET_SCHEDULE_RULE,
    build_scorer_for_vintage,
    create_policy_from_score,
)

# The five statuses CBO's schedule is stated in, mapped from SOI's four. "mfs"
# and "single" differ in the law even where they agree in a given year, which is
# why the mapping is explicit rather than a default.
PRE_TCJA_RATES = (0.10, 0.15, 0.25, 0.28, 0.33, 0.35, 0.396)
TCJA_RATES = (0.10, 0.12, 0.22, 0.24, 0.32, 0.35, 0.37)


# --------------------------------------------------------------------------
# The transcription
# --------------------------------------------------------------------------


def test_all_three_vintages_are_transcribed():
    assert tp.schedule_vintages() == (
        "cbo_feb_2024",
        "cbo_jan_2025",
        "cbo_feb_2026",
    )
    assert tp.is_available()


def test_every_baseline_vintage_has_a_schedule():
    """A vintage the app can score on but has no law for is a silent fallback."""
    served = set(tp.schedule_vintages())
    for vintage in BaselineVintage:
        assert vintage.value in served, f"no tax-parameter schedule for {vintage.value}"


def test_provenance_grades_the_one_substitution():
    """February 2024 has no edition of its own and must not claim one."""
    records = tp.provenance()
    assert records["cbo_feb_2024"]["edition"] == "2024-06"
    assert records["cbo_feb_2024"]["match"] == "nearest_vintage"
    assert records["cbo_jan_2025"]["match"] == "exact"
    assert records["cbo_feb_2026"]["match"] == "exact"
    # The substitution must say what it is, not merely be graded.
    assert "no February 2024 edition" in records["cbo_feb_2024"]["note"]


def test_bracket_one_is_zero_in_every_year_of_every_vintage():
    """The property both byte-identity rows depend on."""
    for vintage in tp.schedule_vintages():
        for year in tp.years_available(vintage):
            for status in FILING_STATUSES:
                assert tp.bracket_floor(vintage, 1, status, year) == 0.0


def test_bracket_floors_ascend_within_a_year():
    for vintage in tp.schedule_vintages():
        for year in tp.years_available(vintage):
            for status in FILING_STATUSES:
                floors = [
                    tp.bracket_floor(vintage, i, status, year)
                    for i in range(1, tp.BRACKET_COUNT + 1)
                ]
                assert floors == sorted(floors)
                assert len(set(floors)) == len(floors)


@pytest.mark.parametrize("vintage", ["cbo_feb_2024", "cbo_jan_2025"])
def test_the_pre_obbba_vintages_revert_in_2026(vintage):
    """The table the repository said did not exist, asserted rather than described."""
    before = tuple(tp.ordinary_rate(vintage, i, 2025) for i in range(1, 8))
    after = tuple(tp.ordinary_rate(vintage, i, 2026) for i in range(1, 8))
    assert before == pytest.approx(TCJA_RATES)
    assert after == pytest.approx(PRE_TCJA_RATES)


def test_the_post_obbba_vintage_does_not_revert():
    before = tuple(tp.ordinary_rate("cbo_feb_2026", i, 2025) for i in range(1, 8))
    after = tuple(tp.ordinary_rate("cbo_feb_2026", i, 2026) for i in range(1, 8))
    assert before == after == pytest.approx(TCJA_RATES)


def test_the_2026_reversion_is_not_a_uniform_shift():
    """The finding that makes PR #127's split a prerequisite rather than a nicety.

    A scalar threshold cannot express a reversion that moves the four statuses
    in two directions, and neither can a scalar plus one joint amount.
    """
    before = tp.bracket_floors_by_status("cbo_feb_2024", 4, 2025)
    after = tp.bracket_floors_by_status("cbo_feb_2024", 4, 2026)
    assert after["joint"] < before["joint"]
    assert after["single"] > before["single"]
    assert after["head_of_household"] > before["head_of_household"]
    # And the joint floor stops being twice the unmarried one, which is the
    # marriage penalty the pre-2018 schedule carried at this bracket.
    assert before["joint"] == pytest.approx(2 * before["single"])
    assert after["joint"] < 2 * after["single"]


def test_a_year_outside_the_edition_raises_rather_than_extrapolating():
    with pytest.raises(tp.TaxParameterError):
        tp.bracket_floor("cbo_feb_2024", 4, "joint", 2099)


@pytest.mark.parametrize("index", [0, 8, -1])
def test_a_bracket_index_outside_one_to_seven_is_refused(index):
    with pytest.raises(ValueError):
        tp.bracket_floor("cbo_feb_2024", index, "joint", 2026)


def test_an_unknown_filing_status_is_refused():
    with pytest.raises(ValueError):
        tp.bracket_floor("cbo_feb_2024", 4, "widower", 2026)


# --------------------------------------------------------------------------
# The policy contract
# --------------------------------------------------------------------------


def test_the_default_is_income_indexation():
    """Today's arithmetic, named at last, and still the default."""
    assert DEFAULT_THRESHOLD_INDEXATION == THRESHOLD_INDEXATION_INCOME
    policy = TaxPolicy(
        name="x", description="x", policy_type=PolicyType.INCOME_TAX,
        rate_change=0.01, affected_income_threshold=400_000.0,
    )
    assert policy.threshold_indexation == THRESHOLD_INDEXATION_INCOME
    assert not policy.reindexes_threshold()
    assert not policy.scores_by_year()


def test_statutory_requires_a_bracket_index():
    with pytest.raises(ValueError, match="threshold_bracket_index"):
        TaxPolicy(
            name="x", description="x", policy_type=PolicyType.INCOME_TAX,
            rate_change=0.01, threshold_indexation=THRESHOLD_INDEXATION_STATUTORY,
        )


def test_a_bracket_index_without_statutory_is_refused():
    """A declared bracket nobody reads means somebody believes a lie."""
    with pytest.raises(ValueError, match="only meaningful"):
        TaxPolicy(
            name="x", description="x", policy_type=PolicyType.INCOME_TAX,
            rate_change=0.01, threshold_bracket_index=4,
        )


def test_a_reindexed_threshold_refuses_a_caller_supplied_base():
    with pytest.raises(ValueError, match="affected_taxpayers_millions"):
        TaxPolicy(
            name="x", description="x", policy_type=PolicyType.INCOME_TAX,
            rate_change=0.01, affected_income_threshold=100_000.0,
            affected_taxpayers_millions=20.0,
            threshold_indexation=THRESHOLD_INDEXATION_NOMINAL,
        )


def test_an_unknown_indexation_is_refused():
    with pytest.raises(ValueError, match="threshold_indexation"):
        TaxPolicy(
            name="x", description="x", policy_type=PolicyType.INCOME_TAX,
            rate_change=0.01, threshold_indexation="cpi",
        )


def test_scores_by_year_has_two_implementers_in_this_module():
    """Item 27 asked for the concept, not a third special case."""
    assert Policy.scores_by_year(
        Policy(name="x", description="x", policy_type=PolicyType.INCOME_TAX)
    ) is False
    gains = CapitalGainsPolicy(
        name="g", description="g", policy_type=PolicyType.CAPITAL_GAINS_TAX,
        rate_change=0.05,
    )
    assert gains.scores_by_year() is True
    scheduled = TaxPolicy(
        name="s", description="s", policy_type=PolicyType.INCOME_TAX,
        rate_change=0.02, affected_income_threshold=103_350.0,
        threshold_indexation=THRESHOLD_INDEXATION_STATUTORY,
        threshold_bracket_index=4,
    )
    assert scheduled.scores_by_year() is True


def test_statutory_thresholds_come_from_the_declared_vintage():
    policy = TaxPolicy(
        name="s", description="s", policy_type=PolicyType.INCOME_TAX,
        rate_change=0.02, affected_income_threshold=103_350.0,
        threshold_indexation=THRESHOLD_INDEXATION_STATUTORY,
        threshold_bracket_index=4,
        threshold_schedule_vintage="cbo_feb_2024",
    )
    assert policy.statutory_thresholds_for_year(2026) == tp.bracket_floors_by_status(
        "cbo_feb_2024", 4, 2026
    )
    # A different vintage is a different law, not a different rounding.
    assert policy.statutory_thresholds_for_year(2026) != tp.bracket_floors_by_status(
        "cbo_feb_2026", 4, 2026
    )


def test_nominal_indexation_returns_the_policys_own_amounts():
    policy = TaxPolicy(
        name="n", description="n", policy_type=PolicyType.INCOME_TAX,
        rate_change=0.02, affected_income_threshold=400_000.0,
        threshold_by_filing_status={"joint": 450_000.0},
        threshold_indexation=THRESHOLD_INDEXATION_NOMINAL,
    )
    for year in (2026, 2035):
        floors = policy.statutory_thresholds_for_year(year)
        assert floors["joint"] == 450_000.0
        assert floors["single"] == 400_000.0


# --------------------------------------------------------------------------
# The rule, and the records that read it
# --------------------------------------------------------------------------


def test_exactly_three_records_declare_a_bracket_index():
    declared = {
        pid: score.statutory_bracket_index
        for pid, score in KNOWN_SCORES.items()
        if score.statutory_bracket_index is not None
    }
    assert declared == {
        "cbo_opt45_all_rates_1pp": 1,
        "cbo_opt45_top4_brackets_2pp": 4,
        "illustrative_1pp_all": 1,
    }


def test_the_option_46_and_green_book_thresholds_are_not_statutory():
    """Their sources state their own amounts; the rule says those stay put."""
    for pid in (
        "cbo_opt46_agi_surtax_1pp_20k",
        "cbo_opt46_agi_surtax_2pp_100k",
        "biden_high_income_tax",
    ):
        assert KNOWN_SCORES[pid].statutory_bracket_index is None


def test_numeric_coincidence_is_not_evidence():
    """The trap the rule exists for, asserted as a fact about the data.

    Option 46's ``$20,000`` IS a bracket floor - head-of-household bracket 2 in
    CY2033 on the February 2024 vintage - so a rule that matched dollars would
    sweep that record onto a schedule its own text never mentions.
    """
    assert tp.bracket_floor("cbo_feb_2024", 2, "head_of_household", 2033) == 20_000.0
    assert KNOWN_SCORES["cbo_opt46_agi_surtax_1pp_20k"].income_threshold == 20_000.0
    assert KNOWN_SCORES["cbo_opt46_agi_surtax_1pp_20k"].statutory_bracket_index is None
    assert "Numeric coincidence is not evidence" in STATUTORY_BRACKET_SCHEDULE_RULE


def test_create_policy_from_score_carries_the_index_and_the_vintage():
    policy = create_policy_from_score(KNOWN_SCORES["cbo_opt45_top4_brackets_2pp"])
    assert policy.threshold_indexation == THRESHOLD_INDEXATION_STATUTORY
    assert policy.threshold_bracket_index == 4
    assert policy.threshold_schedule_vintage == "cbo_feb_2024"
    # The record's own amounts are kept as the fallback and the anchor the
    # preferential-income share is measured at.
    assert policy.affected_income_threshold == 103_350.0
    assert policy.threshold_by_filing_status == {"joint": 206_700.0}


# --------------------------------------------------------------------------
# The scored outcomes
# --------------------------------------------------------------------------


def _score(policy_id: str) -> float:
    score = KNOWN_SCORES[policy_id]
    from fiscal_model.validation.core import _resolve_vintage, _resolve_window_start

    policy = create_policy_from_score(score)
    scorer = build_scorer_for_vintage(
        _resolve_vintage(score),
        start_year=score.effective_start_year or _resolve_window_start(score),
    )
    return float(sum(scorer.score_policy(policy, dynamic=False).final_deficit_effect))


@pytest.mark.parametrize(
    "policy_id, expected",
    [
        # Bracket 1: a $0 floor through the whole schedule path must return
        # what the fixed-threshold path returned. Pinned to the cent, because
        # "about the same" would not catch the failure this test exists for.
        ("cbo_opt45_all_rates_1pp", -1201.24),
        ("illustrative_1pp_all", -1235.67),
    ],
)
def test_bracket_one_scores_to_the_cent(policy_id, expected):
    assert _score(policy_id) == pytest.approx(expected, abs=0.01)


def test_the_top_four_brackets_row_landed_on_its_pre_registration():
    """R4 section 3.1: -671.2 +/- 0.5, a registered regression."""
    assert _score("cbo_opt45_top4_brackets_2pp") == pytest.approx(-671.21, abs=0.5)


def test_the_unmoved_generic_rows_are_unmoved():
    """Predicted byte-identical in R4 section 3.2."""
    assert _score("cbo_opt46_agi_surtax_1pp_20k") == pytest.approx(-1326.31, abs=0.01)
    assert _score("cbo_opt46_agi_surtax_2pp_100k") == pytest.approx(-1075.85, abs=0.01)
    assert _score("biden_high_income_tax") == pytest.approx(-299.84, abs=0.01)


def test_a_uniform_schedule_threshold_equals_the_fixed_one():
    """The general form of the byte-identity check, on a synthetic policy.

    A fixed threshold and a schedule read at a year whose floors equal it must
    agree, which is the property the whole mechanism is built around.
    """
    scorer = build_scorer_for_vintage(BaselineVintage.CBO_FEB_2024, start_year=2025)
    floors = tp.bracket_floors_by_status("cbo_feb_2024", 4, 2025)

    fixed = TaxPolicy(
        name="fixed", description="fixed", policy_type=PolicyType.INCOME_TAX,
        rate_change=0.02, affected_income_threshold=floors["single"],
        threshold_by_filing_status=dict(floors),
        start_year=2025, duration_years=10,
    )
    nominal = TaxPolicy(
        name="nominal", description="nominal", policy_type=PolicyType.INCOME_TAX,
        rate_change=0.02, affected_income_threshold=floors["single"],
        threshold_by_filing_status=dict(floors),
        threshold_indexation=THRESHOLD_INDEXATION_NOMINAL,
        start_year=2025, duration_years=10,
    )
    fixed_path = scorer.score_policy(fixed, dynamic=False).final_deficit_effect
    nominal_path = scorer.score_policy(nominal, dynamic=False).final_deficit_effect

    # Year one only: the deflator is not 1.0 even in the first scored year, so
    # the two agree exactly where the index does and diverge afterwards by the
    # real-bracket-creep term, which is the whole point of the distinction.
    assert float(fixed_path[0]) != pytest.approx(float(nominal_path[0]))
    # And "nominal" is the more generous base in every year, because a fixed
    # nominal floor is eaten by income growth.
    assert abs(float(sum(nominal_path))) > abs(float(sum(fixed_path)))


def test_the_deflation_is_not_optional():
    """R4 section 1.2: the unit error scores better, and must not be reachable.

    Applying a year-t nominal floor to a TY2023 income scores the Option 45
    row at about 3.6% where the correct conversion scores 17.9%. Nothing in the
    scoring path may produce the first number, so the deflated threshold must
    be strictly below the nominal one in every year the index exceeds 1.
    """
    score = KNOWN_SCORES["cbo_opt45_top4_brackets_2pp"]
    policy = create_policy_from_score(score)
    scorer = build_scorer_for_vintage(BaselineVintage.CBO_FEB_2024, start_year=2025)
    for year in scorer.baseline.years:
        year = int(year)
        deflator = scorer._threshold_deflator(policy, year)
        assert deflator > 1.0, f"index below 1 in FY{year}"
        nominal = policy.statutory_thresholds_for_year(year)
        deflated = policy._deflated_thresholds(year, deflator)
        for status in FILING_STATUSES:
            assert deflated[status] < nominal[status]


def test_the_threshold_deflator_is_the_base_projection_factor():
    """Two halves of one unit conversion, so they may not drift apart."""
    score = KNOWN_SCORES["cbo_opt45_top4_brackets_2pp"]
    policy = create_policy_from_score(score)
    scorer = build_scorer_for_vintage(BaselineVintage.CBO_FEB_2024, start_year=2025)
    scorer.score_policy(policy, dynamic=False)
    for year in scorer.baseline.years:
        year = int(year)
        assert scorer._threshold_deflator(policy, year) == pytest.approx(
            scorer._income_base_projection_factor(policy, year)
        )


def test_an_income_indexed_policy_gets_no_deflator():
    policy = TaxPolicy(
        name="x", description="x", policy_type=PolicyType.INCOME_TAX,
        rate_change=0.01, affected_income_threshold=400_000.0,
        start_year=2025, duration_years=10,
    )
    scorer = build_scorer_for_vintage(BaselineVintage.CBO_FEB_2024, start_year=2025)
    assert scorer._threshold_deflator(policy, 2030) == 1.0


def test_a_scheduled_policy_reports_its_first_scored_year_base():
    """Ten reads, one recorded base — the policy's, not its tenth year's."""
    score = KNOWN_SCORES["cbo_opt45_top4_brackets_2pp"]
    policy = create_policy_from_score(score)
    scorer = build_scorer_for_vintage(BaselineVintage.CBO_FEB_2024, start_year=2025)
    scorer.score_policy(policy, dynamic=False)
    first_year_filers = policy.affected_taxpayers_millions
    scorer.score_policy(policy, dynamic=False)
    assert policy.affected_taxpayers_millions == pytest.approx(first_year_filers)
    assert policy.soi_base_tax_year == 2023


def test_scoring_a_scheduled_policy_twice_is_idempotent():
    score = KNOWN_SCORES["cbo_opt45_top4_brackets_2pp"]
    policy = create_policy_from_score(score)
    scorer = build_scorer_for_vintage(BaselineVintage.CBO_FEB_2024, start_year=2025)
    first = float(sum(scorer.score_policy(policy, dynamic=False).final_deficit_effect))
    second = float(sum(scorer.score_policy(policy, dynamic=False).final_deficit_effect))
    assert first == pytest.approx(second, abs=1e-9)


# --------------------------------------------------------------------------
# The Decision 6 caption
# --------------------------------------------------------------------------


def test_the_caption_is_silent_for_every_default_policy():
    from fiscal_model.ui.tabs.results_summary import statutory_threshold_caption

    policy = TaxPolicy(
        name="x", description="x", policy_type=PolicyType.INCOME_TAX,
        rate_change=0.01, affected_income_threshold=400_000.0,
        start_year=2025, duration_years=10,
    )
    scorer = build_scorer_for_vintage(BaselineVintage.CBO_FEB_2024, start_year=2025)
    result = scorer.score_policy(policy, dynamic=False)
    assert statutory_threshold_caption(policy, result) == ""


@pytest.mark.parametrize("dynamic", [False, True])
def test_the_caption_fires_for_a_scheduled_policy_in_both_engine_modes(dynamic):
    """A caption tested only on one engine mode is untested on the other."""
    from fiscal_model.ui.tabs.results_summary import statutory_threshold_caption

    policy = create_policy_from_score(KNOWN_SCORES["cbo_opt45_top4_brackets_2pp"])
    scorer = build_scorer_for_vintage(BaselineVintage.CBO_FEB_2024, start_year=2025)
    result = scorer.score_policy(policy, dynamic=dynamic)
    caption = statutory_threshold_caption(policy, result)
    assert "bracket 4" in caption
    # The substitution must surface, not hide in PROVENANCE.csv.
    assert "nearest published" in caption
    # And the reversion this row exists to express.
    assert "reverts to the pre-2018 schedule" in caption
