"""
Lane R5 (B): the corporate app default is ``derived``, and the caption that says
so is computed rather than written down.

Owner decision ⑤ was "hold ``reported`` until H3b lands, then re-measure once".
``planning/lanes/R5_h3b_corporate.md`` §3.2 fixed the rule **before** the
measurement: the flip ships only if ``derived`` beats ``reported`` on the mean
absolute error over the three published corporate targets **and** lands inside
H3a's four-house estimator span at the +7pp step where ``reported`` lands
outside. These tests assert both, so the default cannot be moved back or further
without the measurement moving with it.
"""

from __future__ import annotations

import pytest

from fiscal_model.corporate import (
    BASELINE_TAXABLE_PROFITS_BILLIONS,
    CORPORATE_APP_MODE,
    CORPORATE_MODE_DERIVED,
    CORPORATE_MODE_REPORTED,
    CORPORATE_VALIDATION_MODE,
    create_biden_corporate_rate_only,
    create_republican_corporate_cut,
)
from fiscal_model.scoring import FiscalPolicyScorer
from fiscal_model.ui.estimator_ranges import corporate_estimator_range
from fiscal_model.ui.tabs.results_summary import (
    corporate_mode_flip_caption,
    reported_mode_total_billions,
)
from fiscal_model.validation.specialized_business import validate_corporate_policy

PUBLISHED_TARGETS = (
    "biden_corporate_28",
    "biden_corporate_28_fy2022",
    "trump_corporate_15",
)


def _mean_abs_error(mode: str) -> float:
    errors = [
        abs(validate_corporate_policy(sid, verbose=False, mode=mode).percent_difference)
        for sid in PUBLISHED_TARGETS
    ]
    return sum(errors) / len(errors)


# ---------------------------------------------------------------------------
# The flip, and the rule that decided it
# ---------------------------------------------------------------------------


def test_the_app_default_is_derived():
    assert CORPORATE_APP_MODE == CORPORATE_MODE_DERIVED


def test_the_validation_mode_is_still_derived():
    """The uncalibrated path must not read a base fitted to a benchmark.

    It was already ``derived`` before the flip and stays ``derived`` after it,
    so ``cbo_opt64_corporate_rate_1pp`` is unmoved by this lane.
    """
    assert CORPORATE_VALIDATION_MODE == CORPORATE_MODE_DERIVED


def test_metric_one_derived_is_nearer_on_the_published_targets():
    """§3.2 metric 1, strictly — no tie-break and no re-weighting."""
    reported = _mean_abs_error(CORPORATE_MODE_REPORTED)
    derived = _mean_abs_error(CORPORATE_MODE_DERIVED)
    assert derived < reported
    assert reported == pytest.approx(62.75, abs=0.05)
    assert derived == pytest.approx(61.43, abs=0.05)


def test_metric_one_wins_on_the_mean_while_losing_two_rows():
    """The result is narrow and the tests say so, so nobody quotes it as broad.

    ``derived`` is nearer on the mean because it wins the FY2022 rate-only row
    by 12.2 points; it loses the other two by 0.3 and 7.9.
    """
    per_row = {}
    for sid in PUBLISHED_TARGETS:
        per_row[sid] = {
            mode: abs(
                validate_corporate_policy(sid, verbose=False, mode=mode).percent_difference
            )
            for mode in (CORPORATE_MODE_REPORTED, CORPORATE_MODE_DERIVED)
        }
    won = [
        sid
        for sid, errs in per_row.items()
        if errs[CORPORATE_MODE_DERIVED] < errs[CORPORATE_MODE_REPORTED]
    ]
    assert won == ["biden_corporate_28_fy2022"]


def test_metric_two_derived_is_inside_the_span_and_reported_is_not():
    """§3.2 metric 2, at the +7pp step every shipped corporate preset uses."""
    positions = {}
    for mode in (CORPORATE_MODE_REPORTED, CORPORATE_MODE_DERIVED):
        policy = create_biden_corporate_rate_only(mode=mode)
        result = FiscalPolicyScorer(start_year=2025, use_real_data=False).score_policy(
            policy, dynamic=False
        )
        spread = corporate_estimator_range(
            rate_change_pp=7.0, model_billions=result.total_10_year_cost
        )
        positions[mode] = spread.model_position
    assert positions[CORPORATE_MODE_DERIVED] == "inside"
    assert positions[CORPORATE_MODE_REPORTED] != "inside"


def test_neither_mode_was_retuned_to_win():
    """§5: the fitted constant is untouched, in either direction."""
    assert BASELINE_TAXABLE_PROFITS_BILLIONS == 1900.0


# ---------------------------------------------------------------------------
# The Decision 6 caption
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "factory",
    [create_biden_corporate_rate_only, create_republican_corporate_cut],
    ids=["biden_28", "trump_15"],
)
def test_the_caption_reconstruction_is_the_engines_own_reported_figure(factory):
    """The caption computes the old number instead of re-scoring it.

    ``reported_mode_total_billions`` replays the four lines
    ``ScoringEngine._score_growth_tax_policy`` uses, because constructing a
    second scorer costs ~300ms on a render path. This is what stops that
    shortcut from drifting: score the same policy through the real engine in
    ``reported`` mode and require the reconstruction to match to the cent.
    """
    scorer = FiscalPolicyScorer(start_year=2026, use_real_data=True)
    reported_policy = factory(mode=CORPORATE_MODE_REPORTED)
    reported_policy.start_year = 2026
    engine_result = scorer.score_policy(reported_policy, dynamic=False)
    engine_total = float(sum(engine_result.static_deficit_effect)) + float(
        sum(engine_result.behavioral_offset)
    )

    derived_policy = factory(mode=CORPORATE_MODE_DERIVED)
    derived_policy.start_year = 2026
    window = len(engine_result.static_deficit_effect)
    assert reported_mode_total_billions(derived_policy, window) == pytest.approx(
        engine_total, abs=0.01
    )


def test_the_caption_fires_on_a_corporate_rate_run_and_names_both_figures():
    scorer = FiscalPolicyScorer(start_year=2026, use_real_data=True)
    policy = create_biden_corporate_rate_only(mode=CORPORATE_MODE_DERIVED)
    policy.start_year = 2026
    result = scorer.score_policy(policy, dynamic=False)

    caption = corporate_mode_flip_caption(policy, result)
    assert caption
    assert "derived" in caption and "reported" in caption
    # Both the new figure and the one it replaced must appear, so a reader can
    # see the size of the move rather than being told there was one.
    current = float(sum(result.static_deficit_effect)) + float(
        sum(result.behavioral_offset)
    )
    previous = reported_mode_total_billions(policy, len(result.static_deficit_effect))
    assert f"{current:+,.1f}" in caption
    assert f"{previous:+,.1f}" in caption


def test_the_caption_is_silent_where_nothing_moved():
    """A corporate policy with no statutory rate step scores the same in both modes."""
    from fiscal_model.corporate import CorporateTaxPolicy
    from fiscal_model.policies import PolicyType

    scorer = FiscalPolicyScorer(start_year=2026, use_real_data=True)
    policy = CorporateTaxPolicy(
        name="Repeal CAMT",
        description="book minimum only",
        policy_type=PolicyType.CORPORATE_TAX,
        rate_change=0.0,
        adjust_book_minimum=True,
        book_minimum_rate_change=-0.15,
        mode=CORPORATE_MODE_DERIVED,
        start_year=2026,
    )
    result = scorer.score_policy(policy, dynamic=False)
    assert corporate_mode_flip_caption(policy, result) == ""


def test_the_caption_is_silent_for_a_reported_run():
    """Someone comparing modes deliberately is not being told the default moved."""
    scorer = FiscalPolicyScorer(start_year=2026, use_real_data=True)
    policy = create_biden_corporate_rate_only(mode=CORPORATE_MODE_REPORTED)
    policy.start_year = 2026
    result = scorer.score_policy(policy, dynamic=False)
    assert corporate_mode_flip_caption(policy, result) == ""
