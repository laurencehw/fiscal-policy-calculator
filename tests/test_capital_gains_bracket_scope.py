"""
Tests for scoping thresholded capital-gains rate changes to statutory brackets
at or above ``affected_income_threshold``.

Lane ``planning/lanes/REVIEW_cg_top_bracket_scope.md`` fixed a structural defect
where ``CapitalGainsPolicy`` shifted every SOI Table 3.5 preferential bracket
(0%, 15%, 20%) returned above an AGI threshold, causing top-rate cuts to push
the 0% bracket below zero and high-threshold rate changes to misprice lower
statutory brackets under 26 U.S.C. 1(h).
"""

from __future__ import annotations

import pytest

from fiscal_model.data.capital_gains import LTCG_RATE_BRACKETS, CapitalGainsBaseline
from fiscal_model.policies import CapitalGainsPolicy, PolicyType
from fiscal_model.scoring import FiscalPolicyScorer
from fiscal_model.validation.core import validate_policy
from fiscal_model.validation.sealed import RETIRED, SEALED_CASES, sealed_cases


def _policy(**kwargs) -> CapitalGainsPolicy:
    defaults = dict(
        name="cg bracket scope",
        description="thresholded capital-gains rate change",
        policy_type=PolicyType.CAPITAL_GAINS_TAX,
        rate_change=-0.05,
        affected_income_threshold=613_700.0,
        start_year=2027,
        duration_years=10,
        baseline_capital_gains_rate=0.0,
        baseline_realizations_billions=0.0,
    )
    defaults.update(kwargs)
    return CapitalGainsPolicy(**defaults)


@pytest.mark.parametrize(
    ("threshold", "expected_floor"),
    [
        (0.0, 0.00),
        (40_000.0, 0.00),
        (LTCG_RATE_BRACKETS[1][0], 0.15),
        (200_000.0, 0.15),
        (400_000.0, 0.15),
        (LTCG_RATE_BRACKETS[2][0], 0.20),
        (613_700.0, 0.20),
        (1_000_000.0, 0.20),
    ],
)
def test_threshold_maps_to_statutory_preferential_bracket(threshold, expected_floor):
    policy = _policy(affected_income_threshold=threshold)
    assert policy._threshold_statutory_rate() == pytest.approx(expected_floor)


def test_top_threshold_scopes_to_twenty_percent_bracket_only():
    """Above the top statutory threshold, only the 20% bracket faces the change."""
    source = CapitalGainsBaseline()
    year = max(source.available_years())
    raw = source.get_brackets_above_threshold(year, 613_700.0)
    raw_rates = {b.statutory_rate for b in raw}
    assert raw_rates == {0.00, 0.15, 0.20}

    policy = _policy(affected_income_threshold=613_700.0, rate_change=-0.05)
    scoped = policy.get_brackets(use_real_data=True)
    assert {b.statutory_rate for b in scoped} == {0.20}

    expected_top = sum(b.realizations_billions for b in raw if b.statutory_rate == 0.20)
    assert policy.baseline_realizations_billions == pytest.approx(expected_top)
    assert policy.baseline_capital_gains_rate == pytest.approx(0.238)


def test_static_effect_matches_top_bracket_share_identity():
    """Pricing only the 20% bracket is algebraically identical to moving each
    SOI AGI class's effective rate by rate_change * (top_bracket_share)."""
    source = CapitalGainsBaseline()
    year = max(source.available_years())
    raw = source.get_brackets_above_threshold(year, 613_700.0)
    total_above = sum(b.realizations_billions for b in raw)
    top_share = (
        sum(b.realizations_billions for b in raw if b.statutory_rate == 0.20)
        / total_above
    )

    policy = _policy(affected_income_threshold=613_700.0, rate_change=-0.05)
    static_data_year = policy.estimate_static_revenue_effect(0.0, use_real_data=True)
    assert static_data_year == pytest.approx((-0.05 * top_share) * total_above)


def test_top_rate_cut_scores_cleanly_with_positive_deficit():
    """A -5pp cut to the top capital-gains rate above $613,700 no longer crashes."""
    policy = _policy(affected_income_threshold=613_700.0, rate_change=-0.05)
    scorer = FiscalPolicyScorer(baseline=None, use_real_data=True)
    result = scorer.score_policy(policy, dynamic=False, include_uncertainty=False)

    static_deficit = float(sum(result.static_deficit_effect))
    net_deficit = float(sum(result.final_deficit_effect))
    assert static_deficit > 0
    assert net_deficit > 0
    assert net_deficit < static_deficit


def test_intermediate_threshold_excludes_zero_percent_bracket():
    """A $400K threshold reaches the 15% and 20% brackets and skips 0%."""
    policy = _policy(affected_income_threshold=400_000.0, rate_change=-0.05)
    scoped = policy.get_brackets(use_real_data=True)
    assert {b.statutory_rate for b in scoped} == {0.15, 0.20}
    assert policy.estimate_static_revenue_effect(0.0, use_real_data=True) < 0


def test_zero_threshold_retains_all_three_statutory_brackets():
    """Across-the-board reforms (CBO Option 47 shape) are untouched."""
    policy = _policy(affected_income_threshold=0.0, rate_change=0.02)
    scoped = policy.get_brackets(use_real_data=True)
    assert {b.statutory_rate for b in scoped} == {0.00, 0.15, 0.20}


def test_cut_taking_a_reached_bracket_below_zero_still_raises():
    """The [0, 1) guard remains active for every bracket the threshold reaches."""
    across_the_board_cut = _policy(affected_income_threshold=0.0, rate_change=-0.05)
    with pytest.raises(ValueError, match="Capital gains rates must be in"):
        across_the_board_cut.estimate_static_revenue_effect(0.0, use_real_data=True)

    extreme_top_cut = _policy(affected_income_threshold=613_700.0, rate_change=-0.25)
    with pytest.raises(ValueError, match="Capital gains rates must be in"):
        extreme_top_cut.estimate_static_revenue_effect(0.0, use_real_data=True)


def test_caller_supplied_realizations_bypass_soi_bracket_filtering():
    """Explicit single-bracket bases (e.g. LOO/specialized scenarios) are untouched."""
    policy = _policy(
        affected_income_threshold=1_000_000.0,
        rate_change=0.05,
        baseline_realizations_billions=500.0,
        baseline_capital_gains_rate=0.15,
    )
    brackets = policy.get_brackets(use_real_data=True)
    assert len(brackets) == 1
    assert brackets[0].statutory_rate == pytest.approx(0.15)
    assert policy.estimate_static_revenue_effect(0.0, use_real_data=True) == pytest.approx(
        25.0
    )


def test_retired_sealed_cg_cut_names_lane_and_scores_cleanly():
    """Rule 3 retirement: tf3_opt7_cg_top_rate_15 left the live battery and now scores."""
    case_id = "tf3_opt7_cg_top_rate_15"
    assert case_id in RETIRED
    assert "REVIEW_cg_top_bracket_scope.md" in RETIRED[case_id]
    assert all(c.case_id != case_id for c in sealed_cases())

    case = next(c for c in SEALED_CASES if c.case_id == case_id)
    result = validate_policy(case.score)
    assert result is not None
    assert result.direction_match is True
    assert result.model_10yr > 0
