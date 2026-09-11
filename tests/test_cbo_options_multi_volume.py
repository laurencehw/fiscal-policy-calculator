"""Lane R3: the 2018, 2020 and 2022 *Options for Reducing the Deficit* volumes.

What these tests are for
------------------------
The battery doubled, so the question a reader asks is not "is it bigger" but
"was it *selected*?". Each test below answers one half of that:

* every revenue option in all three volumes carries a verdict, so the battery
  cannot be a curated set of flattering shapes;
* every registered row's target is CBO's own printed ten-year figure from the
  transcription, so no target was rounded, rescaled or chosen after a run;
* every per-status threshold is CBO's own published statutory parameter for the
  option's own first calendar year, so none of them is a hand-typed number; and
* the shape inputs each row declares are the ones its own source states.

``tests/test_preregistration.py`` covers the manifest side (two-commit rule,
target immutability, the window rule); this file covers the data side.
"""

from __future__ import annotations

import csv
import io
from pathlib import Path

import pytest

from fiscal_model.validation.cbo_options import (
    MULTI_VOLUME_SOURCES,
    describe_multi_volume_coverage,
    load_multi_volume_alternatives,
    load_multi_volume_options,
)
from fiscal_model.validation.cbo_scores import KNOWN_SCORES, get_validation_targets
from fiscal_model.validation.preregistered import (
    PREREGISTERED_CASES,
    R3_MULTI_VOLUME_ENTERED_COMMIT,
    R3_SELECTION_RULE,
)

TAX_PARAMETERS_CSV = (
    Path(__file__).resolve().parent.parent
    / "fiscal_model"
    / "data_files"
    / "cbo_tax_parameters"
    / "cbo_tax_parameters.csv"
)

#: ``FILING_STATUSES`` key -> the suffix CBO's own schedule uses.
_STATUS_SUFFIX = {
    "single": "single",
    "joint": "mfj",
    "separate": "mfs",
    "head_of_household": "hoh",
}


def _r3_policy_ids() -> set[str]:
    return {
        case.policy_id
        for case in PREREGISTERED_CASES
        if case.entered_commit == R3_MULTI_VOLUME_ENTERED_COMMIT and case.is_live
    }


def _tax_parameters() -> dict[tuple[str, int, str], float]:
    with TAX_PARAMETERS_CSV.open(encoding="utf-8") as handle:
        body = (line for line in handle if not line.startswith("#"))
        rows = list(csv.DictReader(io.StringIO("".join(body))))
    return {
        (row["vintage"], int(row["calendar_year"]), row["variable"]): float(row["value"])
        for row in rows
    }


# ---------------------------------------------------------------------------
# Composition
# ---------------------------------------------------------------------------


def test_every_revenue_option_in_all_three_volumes_carries_a_verdict():
    """A silently dropped option is how a battery becomes a curated set."""
    options = load_multi_volume_options()
    assert len(options) == 100
    seen: dict[tuple[str, str], set[int]] = {}
    for option in options:
        assert option.volume in MULTI_VOLUME_SOURCES
        assert option.title.strip()
        # Runnable options carry no reason; every other one carries exactly one
        # line saying which shape does not exist.
        assert option.runnable is (option.reason == "")
        key = (option.volume, option.chapter)
        numbers = seen.setdefault(key, set())
        assert option.option_number not in numbers, (
            f"{option.volume} {option.chapter} option {option.option_number} twice"
        )
        numbers.add(option.option_number)

    # The exact option numbers, per volume and chapter, so a missing option is a
    # test failure rather than a smaller total. The 2018 and 2020 volumes number
    # their revenue chapters from 1; the 2022 edition splits into two volumes and
    # numbers Volume I's options across categories, so its revenue options are
    # 6 (the employment-based health exclusion) and 13-17, with Volume II's
    # revenue chapter continuing at 37.
    assert seen == {
        ("2018", "Revenues"): set(range(1, 41)),
        ("2020", "Revenues"): set(range(1, 32)),
        ("2022", "Volume I"): {6, 13, 14, 15, 16, 17},
        ("2022", "Volume II, Revenues"): set(range(37, 60)),
    }


def test_the_selection_rule_is_recorded_rather_than_a_list():
    """A list of ids is a choice; a rule is a rule. The manifest holds the rule
    and every one of the lane's own rows quotes it."""
    assert "REVENUE option" in R3_SELECTION_RULE
    assert "never for its answer" in R3_SELECTION_RULE
    rows = [
        case
        for case in PREREGISTERED_CASES
        if case.entered_commit == R3_MULTI_VOLUME_ENTERED_COMMIT
    ]
    assert len(rows) == 22
    for case in rows:
        assert R3_SELECTION_RULE in case.note, case.case_id


def test_registered_alternatives_are_exactly_the_lane_s_rows():
    coverage = describe_multi_volume_coverage()
    assert coverage["registered_alternatives"] == 22
    assert len(_r3_policy_ids()) == 22


def test_no_unregistered_alternative_has_a_scored_record():
    """The seven transcribed-but-not-registered alternatives exist so the
    exclusions are visible at the alternative level. None of them may be
    quietly scored."""
    unregistered = [alt for alt in load_multi_volume_alternatives() if not alt.registered]
    assert len(unregistered) == 7
    for alt in unregistered:
        assert alt.not_registered_reason.strip(), alt.alternative_id
        for score in KNOWN_SCORES.values():
            if score.source_url and str(alt.option_number) in score.policy_id:
                continue
        # The strongest form: no KNOWN_SCORES target equals this alternative's
        # published figure on this volume's window.
        clashes = [
            score.policy_id
            for score in KNOWN_SCORES.values()
            if score.policy_id in _r3_policy_ids()
            and abs(score.ten_year_cost - alt.deficit_effect_10yr_billions) < 1e-9
            and score.scoring_window_first_year == alt.window_first_year
        ]
        assert not clashes, f"{alt.alternative_id} is scored as {clashes}"


# ---------------------------------------------------------------------------
# Targets
# ---------------------------------------------------------------------------


def test_every_registered_target_is_cbo_s_own_printed_figure():
    """The target a row scores against must be the transcription's, to the
    cent. This is the assertion that makes 'no target was chosen after seeing
    the answer' checkable rather than asserted."""
    registered = {
        (alt.volume, alt.alternative_id): alt
        for alt in load_multi_volume_alternatives()
        if alt.registered
    }
    assert len(registered) == 22
    by_target = {}
    for alt in registered.values():
        by_target.setdefault(
            round(alt.deficit_effect_10yr_billions, 6), []
        ).append(alt)

    for policy_id in sorted(_r3_policy_ids()):
        score = KNOWN_SCORES[policy_id]
        key = round(score.ten_year_cost, 6)
        assert key in by_target, f"{policy_id}: no transcribed alternative at {key}"
        matches = [
            alt for alt in by_target[key]
            if alt.window_first_year == score.scoring_window_first_year
        ]
        assert matches, f"{policy_id}: no alternative on window {score.scoring_window_first_year}"


def test_sign_conventions_are_normalised_on_every_transcribed_row():
    for alt in load_multi_volume_alternatives():
        assert alt.deficit_effect_10yr_billions == pytest.approx(
            -alt.savings_10yr_billions
        ), alt.alternative_id


def test_annual_paths_sum_to_their_published_ten_year_total():
    """CBO prints the annual path and the total separately, so the sum is an
    independent check on the transcription rather than a restatement of it."""
    for alt in load_multi_volume_alternatives():
        if len(alt.annual_savings_billions) != 10:
            continue
        assert sum(alt.annual_savings_billions) == pytest.approx(
            alt.savings_10yr_billions, abs=0.6
        ), alt.alternative_id


# ---------------------------------------------------------------------------
# Shape inputs
# ---------------------------------------------------------------------------


def test_every_threshold_is_cbo_s_own_published_parameter():
    """Not one of the per-status amounts on these rows is a hand-typed number.

    Each is read from CBO's transcribed statutory schedule at the option's own
    first calendar year, on the vintage the row is scored on - CY2021 for the
    2020 volume (and, under the schedule clamp, for the 2018 volume too), CY2023
    for the 2022 volume. The two AGI-surtax rows are sums of published
    parameters, which is the one place this lane adds rather than reads, and the
    addition is asserted here rather than trusted.
    """
    params = _tax_parameters()
    expected: dict[str, tuple[int, str]] = {
        "cbo2019_opt1_top4_brackets_1pp": (2021, "bracket_4"),
        "cbo2019_opt1_top2_brackets_1pp": (2021, "bracket_6"),
        "cbo2021_opt1_top4_brackets_1pp": (2021, "bracket_4"),
        "cbo2021_opt1_top2_brackets_1pp": (2021, "bracket_6"),
        "cbo2023_opt13_top4_brackets_2pp": (2023, "bracket_4"),
        "cbo2023_opt13_agi_surtax_1pp_stdded": (2023, "std_deduction+exemption"),
        "cbo2023_opt13_agi_surtax_2pp_bracket4": (
            2023,
            "std_deduction+exemption+bracket_4",
        ),
    }
    from fiscal_model.validation.core import create_policy_from_score

    for policy_id, (year, formula) in expected.items():
        score = KNOWN_SCORES[policy_id]
        vintage = score.scoring_vintage
        assert vintage == "cbo_feb_2024"
        # The *resolved* map, so the fallback statuses are checked too: a
        # record declares only the amounts that differ from its single floor
        # (FILING_STATUS_THRESHOLD_RULE), and every status still has to land on
        # CBO's own published parameter.
        policy = create_policy_from_score(score)
        assert policy is not None
        thresholds = policy.resolved_filing_status_thresholds()
        assert set(thresholds) == set(_STATUS_SUFFIX), policy_id
        for status, amount in thresholds.items():
            suffix = _STATUS_SUFFIX[status]
            want = 0.0
            for term in formula.split("+"):
                if term == "exemption":
                    want += params[(vintage, year, "tp_personal_exemption")]
                elif term == "std_deduction":
                    want += params[(vintage, year, f"tp_std_deduction_{suffix}")]
                else:
                    want += params[(vintage, year, f"tp_{term}_{suffix}")]
            assert amount == pytest.approx(want), f"{policy_id}/{status}"


def test_a_window_carrying_row_is_scored_on_the_decade_its_source_published():
    for policy_id in sorted(_r3_policy_ids()):
        score = KNOWN_SCORES[policy_id]
        stated = int(str(score.budget_window).split("-")[0].removeprefix("FY"))
        assert score.scoring_window_first_year == stated, policy_id
        assert score.effective_start_year is not None


def test_the_whole_battery_reaches_the_generic_runner():
    """A pre-registration row that never scores is prose. All 22 dispatch."""
    dispatched = {score.policy_id for score in get_validation_targets()}
    assert _r3_policy_ids() <= dispatched
    assert len(dispatched) == 44


def test_the_2018_volume_is_admitted_by_its_window_not_by_a_lowered_floor():
    """``MIN_GENERIC_BASELINE_YEAR`` is unchanged at 2020; what admits the seven
    2018-volume rows is that each states its own decade. Both halves are
    asserted, because lowering the constant would have been the easy way and it
    is the wrong one."""
    from fiscal_model.validation.cbo_scores import MIN_GENERIC_BASELINE_YEAR

    assert MIN_GENERIC_BASELINE_YEAR == 2020
    older = [
        score
        for score in get_validation_targets()
        if score.baseline_year < MIN_GENERIC_BASELINE_YEAR
    ]
    assert {score.policy_id for score in older} == {
        "cbo2019_opt1_all_rates_1pp",
        "cbo2019_opt1_top4_brackets_1pp",
        "cbo2019_opt1_top2_brackets_1pp",
        "cbo2019_opt2_ltcg_qdiv_2pp",
        "cbo2019_opt18_hi_payroll_1pp",
        "cbo2019_opt18_hi_payroll_2pp",
        "cbo2019_opt24_corporate_rate_1pp",
    }
    for score in older:
        assert score.scoring_window_first_year is not None


# ---------------------------------------------------------------------------
# The finding the four editions make visible
# ---------------------------------------------------------------------------


def test_cbo_prices_one_corporate_reform_four_times_and_gets_four_numbers():
    """The reason the corporate class was worth quadrupling.

    CBO's own per-point yield for an identical 21%-to-22% increase rises 41%
    across the four editions. This asserts the *documents*, not the model - if
    a transcription ever flattens that spread, the class stops measuring what it
    was registered to measure.
    """
    targets = [
        KNOWN_SCORES["cbo2019_opt24_corporate_rate_1pp"].ten_year_cost,
        KNOWN_SCORES["cbo2021_opt19_corporate_rate_1pp"].ten_year_cost,
        KNOWN_SCORES["cbo2023_opt50_corporate_rate_1pp"].ten_year_cost,
        KNOWN_SCORES["cbo_opt64_corporate_rate_1pp"].ten_year_cost,
    ]
    assert targets == sorted(targets, reverse=True), "editions are not in order"
    spread = abs(targets[-1] / targets[0]) - 1.0
    assert spread == pytest.approx(0.4097, abs=0.001)


def test_the_two_earliest_corporate_rows_read_a_back_projected_receipts_path():
    """The second cause on the corporate rows, asserted rather than described.

    CBO's transcribed receipts path (publication 59710) starts in FY2025 and
    rises about 1.2%/yr, so extrapolating it *backwards* walks a nearly-flat
    line into years whose actual receipts were far lower. The 2018 row's base
    year is more than twice Treasury's own MTS actual for it, which is most of
    why that row reads 99.7% — and that is a statement about the base this lane
    reached for, not about the module's marginal share.

    The ordering is what is pinned: the ratio must fall monotonically toward
    1 as the window approaches the table's own first year. If it ever stops
    doing that, the projection has changed shape and the ``known_limitations``
    on those rows are describing something that no longer happens.
    """
    from fiscal_model.corporate import actual_corporate_receipts, cbo_corporate_receipts

    ratios = {}
    for year in (2019, 2021, 2023):
        projected = cbo_corporate_receipts(year)
        actual = actual_corporate_receipts(year)
        ratios[year] = projected / actual

    assert ratios[2019] == pytest.approx(2.218, abs=0.01)
    assert ratios[2021] == pytest.approx(1.358, abs=0.01)
    assert ratios[2023] == pytest.approx(1.191, abs=0.01)
    assert ratios[2019] > ratios[2021] > ratios[2023] > 1.0

    # And the table really does begin after all three, which is the reason the
    # extrapolation happens at all.
    from fiscal_model.corporate import cbo_receipts_by_fiscal_year

    assert cbo_receipts_by_fiscal_year("cbo_feb_2024")[0][0] == 2025


def test_the_2020_volume_prices_five_repeated_reforms_below_the_2018_volume():
    """The pandemic baseline, asserted from CBO's own figures.

    CBO's September 2020 baseline is below its April 2018 one in nominal terms
    for wages and ordinary income, so five of the six options this battery
    repeats across those two editions carry a *smaller* ten-year figure two
    years later. No model whose base grows monotonically with CBO's own nominal
    path can reproduce that, which is the documented cause on three of the
    lane's Poor rows.
    """
    pairs = {
        "all rates +1pp": ("cbo2019_opt1_all_rates_1pp", "cbo2021_opt1_all_rates_1pp"),
        "top four +1pp": (
            "cbo2019_opt1_top4_brackets_1pp",
            "cbo2021_opt1_top4_brackets_1pp",
        ),
        "top two +1pp": (
            "cbo2019_opt1_top2_brackets_1pp",
            "cbo2021_opt1_top2_brackets_1pp",
        ),
        "HI +1pp": ("cbo2019_opt18_hi_payroll_1pp", "cbo2021_opt15_hi_payroll_1pp"),
        "HI +2pp": ("cbo2019_opt18_hi_payroll_2pp", "cbo2021_opt15_hi_payroll_2pp"),
        "LTCG +2pp": ("cbo2019_opt2_ltcg_qdiv_2pp", "cbo2021_opt2_ltcg_qdiv_2pp"),
        "corporate +1pp": (
            "cbo2019_opt24_corporate_rate_1pp",
            "cbo2021_opt19_corporate_rate_1pp",
        ),
    }
    smaller = {
        name
        for name, (older, newer) in pairs.items()
        if abs(KNOWN_SCORES[newer].ten_year_cost)
        < abs(KNOWN_SCORES[older].ten_year_cost)
    }
    assert smaller == {
        "all rates +1pp",
        "top four +1pp",
        "top two +1pp",
        "HI +1pp",
        "HI +2pp",
    }
