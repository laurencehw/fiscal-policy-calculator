"""
The CBO *Options for Reducing the Deficit: 2025-2034* battery.

These tests protect the two properties that make the battery a fair test rather
than a curated set of flattering shapes:

1. **Nothing is silently dropped.** All 76 options are classified, and every
   option that is not runnable states, in one line, why.
2. **Every runnable option is really runnable.** Its target matches the number
   CBO published for that specific alternative, and the uncalibrated path builds
   a concrete policy object for it.
"""

from __future__ import annotations

import pytest

from fiscal_model.validation.cbo_options import (
    ALTERNATIVES_CSV,
    N_OPTIONS,
    OPTIONS_CSV,
    OUT_OF_SCOPE_ALTERNATIVES,
    OUT_OF_SCOPE_REASONS,
    RUNNABLE_OPTIONS,
    classify_all,
    describe_option_coverage,
    first_effective_year,
    get_alternative,
    is_level_budget_authority_path,
    load_alternatives,
    load_options,
    runnable_score_ids,
)
from fiscal_model.validation.cbo_scores import KNOWN_SCORES, validation_shape
from fiscal_model.validation.core import create_policy_from_score

_EXPECTED_SHAPES = {
    "ordinary_rate",
    "capital_gains",
    "corporate_rate",
    "payroll_rate",
    "spending",
}


# ── The extracted data ─────────────────────────────────────────────────────


def test_all_76_options_are_present_and_contiguous():
    options = load_options()
    assert len(options) == N_OPTIONS
    assert [o.option_number for o in options] == list(range(1, N_OPTIONS + 1))


def test_every_option_has_a_title_category_page_and_baseline():
    for option in load_options():
        assert option.title
        assert option.category in {"mandatory", "discretionary", "revenue"}
        assert option.report_page and option.report_page > 0
        assert option.baseline_vintage


def test_table_1_1_savings_are_positive_reductions():
    """CBO's own sign convention: a savings figure reduces the deficit."""
    for option in load_options():
        assert option.savings_low_billions > 0
        assert option.savings_high_billions >= option.savings_low_billions
        low, high = option.deficit_effect_range
        assert low <= high <= 0


def test_alternatives_cover_every_runnable_option():
    numbers = {a.option_number for a in load_alternatives()}
    for entry in RUNNABLE_OPTIONS:
        assert entry.option_number in numbers


# ── Classification closes ──────────────────────────────────────────────────


def test_every_option_is_classified():
    coverage = describe_option_coverage()
    assert coverage["total"] == N_OPTIONS
    assert coverage["unclassified"] == []
    assert coverage["runnable_options"] + coverage["out_of_scope"] == N_OPTIONS


def test_every_out_of_scope_option_states_a_reason():
    for entry in classify_all():
        if entry.runnable:
            continue
        reason = OUT_OF_SCOPE_REASONS[entry.option_number]
        assert reason.strip(), f"option {entry.option_number} has an empty reason"
        assert reason.endswith("."), (
            f"option {entry.option_number}: reason should be one full sentence"
        )


def test_out_of_scope_reasons_do_not_shadow_runnable_options():
    runnable = {entry.option_number for entry in RUNNABLE_OPTIONS}
    assert not (runnable & set(OUT_OF_SCOPE_REASONS))


def test_out_of_scope_alternatives_belong_to_runnable_options():
    runnable = {entry.option_number for entry in RUNNABLE_OPTIONS}
    for alternative_id in OUT_OF_SCOPE_ALTERNATIVES:
        assert int(alternative_id.split(".")[0]) in runnable


def test_runnable_count_is_in_the_expected_band():
    """A sanity rail: a huge jump either way means the bar moved."""
    assert 10 <= len(RUNNABLE_OPTIONS) <= 25


# ── Every runnable option is really runnable ───────────────────────────────


@pytest.mark.parametrize("entry", RUNNABLE_OPTIONS, ids=lambda e: e.score_id)
def test_runnable_option_has_a_score_record(entry):
    assert entry.score_id in KNOWN_SCORES


@pytest.mark.parametrize("entry", RUNNABLE_OPTIONS, ids=lambda e: e.score_id)
def test_runnable_option_target_matches_the_published_alternative(entry):
    target = get_alternative(entry.target_row_id)
    assert target is not None, f"missing alternative {entry.target_row_id}"
    assert KNOWN_SCORES[entry.score_id].ten_year_cost == pytest.approx(
        target.deficit_effect_10yr_billions
    )


@pytest.mark.parametrize("entry", RUNNABLE_OPTIONS, ids=lambda e: e.score_id)
def test_spending_input_and_target_are_different_series(entry):
    """A spending case must predict outlays from budget authority, not from
    the outlay path it is being scored against."""
    if entry.shape != "spending":
        assert entry.target_alternative_id is None
        return

    source = get_alternative(entry.alternative_id)
    target = get_alternative(entry.target_row_id)
    assert source is not None and target is not None
    assert source.alternative_id != target.alternative_id
    assert source.measure in {"budget_authority", "spending_authority"}
    assert target.measure == "outlays"
    assert KNOWN_SCORES[entry.score_id].annual_amount_billions == pytest.approx(
        -source.annual_savings_billions[
            source.annual_savings_billions.index(
                next(v for v in source.annual_savings_billions if abs(v) > 1e-9)
            )
        ]
    )


@pytest.mark.parametrize("entry", RUNNABLE_OPTIONS, ids=lambda e: e.score_id)
def test_runnable_option_builds_a_concrete_policy(entry):
    score = KNOWN_SCORES[entry.score_id]
    shape = validation_shape(score)
    assert shape == entry.shape
    assert shape in _EXPECTED_SHAPES

    policy = create_policy_from_score(score)
    assert policy is not None, f"{entry.score_id} has no constructible policy"
    assert policy.start_year == (score.effective_start_year or 2025)


@pytest.mark.parametrize("entry", RUNNABLE_OPTIONS, ids=lambda e: e.score_id)
def test_runnable_option_is_scored_on_the_published_vintage(entry):
    """Both chapters were built on a 2024 baseline, so all 14 name it."""
    assert KNOWN_SCORES[entry.score_id].scoring_vintage == "cbo_feb_2024"


def test_runnable_score_ids_are_unique():
    assert len(runnable_score_ids()) == len(RUNNABLE_OPTIONS)


# ── The mechanical level-path test for spending shapes ─────────────────────


def test_level_path_test_accepts_the_five_spending_options():
    for entry in RUNNABLE_OPTIONS:
        if entry.shape != "spending":
            continue
        alternative = get_alternative(entry.alternative_id)
        assert alternative is not None
        assert is_level_budget_authority_path(alternative.annual_savings_billions), (
            f"{entry.score_id}: budget authority path is not a level change"
        )


@pytest.mark.parametrize(
    "alternative_id",
    ["28.1", "35.1", "36.1", "40.1", "41.1", "44.1"],
)
def test_level_path_test_rejects_ramps_and_wind_downs(alternative_id):
    alternative = get_alternative(alternative_id)
    assert alternative is not None
    assert not is_level_budget_authority_path(alternative.annual_savings_billions)


def test_level_path_test_rejects_an_all_zero_path():
    assert not is_level_budget_authority_path([0.0] * 10)


def test_spending_options_take_effect_the_year_cbo_says():
    for entry in RUNNABLE_OPTIONS:
        if entry.shape != "spending":
            continue
        alternative = get_alternative(entry.alternative_id)
        assert alternative is not None
        assert (
            KNOWN_SCORES[entry.score_id].effective_start_year
            == first_effective_year(alternative.annual_savings_billions)
        )


# ── Vintage matching ───────────────────────────────────────────────────────


def test_scorer_honours_a_requested_baseline_vintage():
    """The battery's targets were published on a 2024 baseline, so the runner
    must be able to score them on one."""
    from fiscal_model.baseline import BaselineVintage
    from fiscal_model.validation.core import build_scorer_for_vintage

    matched = build_scorer_for_vintage(BaselineVintage.CBO_FEB_2024)
    default = build_scorer_for_vintage(None)

    # The two baselines really are different projections, so a shape that reads
    # off baseline levels would move between them. (None of the 14 Phase B
    # shapes does: they are bottom-up from SOI filer counts, module revenue
    # identities and source-stated spending levels, so vintage matching is
    # wired end-to-end here without changing any of their scores. It matters for
    # shapes that scale off a baseline level - Phase D's concern.)
    assert float(matched.baseline.total_revenues.sum()) != pytest.approx(
        float(default.baseline.total_revenues.sum())
    )


def test_records_without_a_vintage_keep_the_default_scorer():
    """Vintage matching must not disturb the pre-Phase-B cases."""
    from fiscal_model.validation.core import _resolve_vintage

    assert _resolve_vintage(KNOWN_SCORES["illustrative_1pp_all"]) is None


def test_unknown_vintage_string_falls_back_to_the_default():
    import dataclasses

    from fiscal_model.validation.core import _resolve_vintage

    bogus = dataclasses.replace(
        KNOWN_SCORES["cbo_opt45_all_rates_1pp"], scoring_vintage="cbo_never_2099"
    )
    assert _resolve_vintage(bogus) is None


# ── The CSV provenance header must stay loader-compatible ──────────────────


@pytest.mark.parametrize(
    "path", [OPTIONS_CSV, ALTERNATIVES_CSV], ids=["options", "alternatives"]
)
def test_every_provenance_line_is_a_comment(path):
    """Consumers skip lines starting with ``#`` and treat the rest as CSV.

    The provenance block is written as a list of Python string literals, some
    of which are implicit concatenations spanning two source lines. If one of
    those ever loses its ``#`` prefix, the block silently becomes data rows.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    header_index = next(
        i for i, line in enumerate(lines) if line.startswith("option_number,")
    )
    assert header_index > 0, "expected a provenance block before the CSV header"
    for line in lines[:header_index]:
        assert line.startswith("#"), f"non-comment provenance line: {line!r}"


@pytest.mark.parametrize(
    "path", [OPTIONS_CSV, ALTERNATIVES_CSV], ids=["options", "alternatives"]
)
def test_comment_stripping_leaves_only_the_header_and_data(path):
    """The exact filter every loader in this repo applies."""
    import csv as _csv

    with path.open(encoding="utf-8") as handle:
        rows = list(_csv.DictReader(line for line in handle if not line.startswith("#")))
    assert rows
    assert all(row["option_number"].isdigit() for row in rows)
