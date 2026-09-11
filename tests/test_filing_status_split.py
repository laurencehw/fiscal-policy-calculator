"""The filing-status dimension of the generic income-tax path (lane W7).

The design these tests protect is one sentence: **Table 1.1 supplies the level,
Table 1.2 supplies the within-class composition.** Everything else follows from
it, and the two properties that make the split an honest experiment rather than
a re-basing are:

1. A split evaluated at one **uniform** threshold reproduces the pooled score,
   so any movement is attributable to the per-status floors alone.
2. A policy with **no** per-status threshold is untouched, byte for byte.

See ``planning/lanes/W7_filing_status_split.md``.
"""

from __future__ import annotations

import numpy as np
import pytest

from fiscal_model.data.irs_soi import FILING_STATUSES, IRSSOIData
from fiscal_model.policies import PolicyType, TaxPolicy
from fiscal_model.scoring import FiscalPolicyScorer
from fiscal_model.validation.cbo_scores import KNOWN_SCORES
from fiscal_model.validation.core import (
    FILING_STATUS_THRESHOLD_RULE,
    create_policy_from_score,
)

DATA_YEAR = 2023

#: Thresholds the split is exercised at: zero, both Option 46 floors, the 2025
#: 24%-bracket floor, the Green Book's unmarried floor, and a top-tail value.
CONTROL_THRESHOLDS = (0.0, 20_000.0, 100_000.0, 103_350.0, 400_000.0, 1_000_000.0)


@pytest.fixture(scope="module")
def irs() -> IRSSOIData:
    return IRSSOIData()


# ---------------------------------------------------------------------------
# The data
# ---------------------------------------------------------------------------


def test_table_1_2_is_available(irs):
    assert DATA_YEAR in irs.get_filing_status_years_available()


def test_split_reassembles_to_table_1_1(irs):
    """The four statuses sum back to Table 1.1's class totals, exactly."""
    pooled = irs.get_bracket_distribution(DATA_YEAR)
    split = irs.get_bracket_distribution_by_status(DATA_YEAR)

    assert set(split) == set(FILING_STATUSES)
    for status in FILING_STATUSES:
        assert len(split[status]) == len(pooled)

    for index, bracket in enumerate(pooled):
        for field in ("num_returns", "total_agi", "taxable_income", "total_tax"):
            summed = sum(getattr(split[status][index], field) for status in FILING_STATUSES)
            assert summed == pytest.approx(getattr(bracket, field), rel=1e-9, abs=1e-9), (
                f"{field} does not reassemble in class "
                f"{bracket.agi_floor}-{bracket.agi_ceiling}"
            )
        for status in FILING_STATUSES:
            assert split[status][index].agi_floor == bracket.agi_floor
            assert split[status][index].agi_ceiling == bracket.agi_ceiling


def test_table_1_2_agrees_with_table_1_1_on_returns_and_agi(irs):
    """The two tables are the same universe, and say so on the two fields where
    they are directly comparable.

    Table 1.2's *taxable income* is the exception and it is asserted here too,
    because the disagreement is the whole reason the loader apportions rather
    than reading Table 1.2 wholesale: Table 1.1 column 11 is taxable income on
    *taxable* returns, Table 1.2's is taxable income on *all* returns.
    """
    pooled = irs.get_bracket_distribution(DATA_YEAR)
    raw = irs._read_table_1_2_classes(DATA_YEAR)
    assert len(raw) == len(pooled)

    returns_1_2 = 0.0
    agi_1_2 = 0.0
    taxable_1_2 = 0.0
    for bracket, row in zip(pooled, raw):
        assert (row["agi_floor"], row["agi_ceiling"]) == (bracket.agi_floor, bracket.agi_ceiling)
        returns = sum(row["by_status"][s]["num_returns"] for s in FILING_STATUSES)
        agi = sum(row["by_status"][s]["total_agi"] for s in FILING_STATUSES) / 1e6
        taxable = sum(row["by_status"][s]["taxable_income"] for s in FILING_STATUSES) / 1e6
        # SOI rounds and suppresses each block separately, so the four statuses
        # can differ from the all-returns column by a return or two.
        assert abs(returns - bracket.num_returns) <= 2.0
        assert agi == pytest.approx(bracket.total_agi, abs=0.001)
        returns_1_2 += returns
        agi_1_2 += agi
        taxable_1_2 += taxable

    pooled_taxable = sum(b.taxable_income for b in pooled)
    assert returns_1_2 == pytest.approx(sum(b.num_returns for b in pooled), abs=2.0)
    assert agi_1_2 == pytest.approx(sum(b.total_agi for b in pooled), rel=1e-6)
    # Different universes: all returns vs taxable returns, about $319B apart.
    assert taxable_1_2 - pooled_taxable == pytest.approx(319.0, abs=5.0)


def test_status_shares_sum_to_one(irs):
    split = irs.get_bracket_distribution_by_status(DATA_YEAR)
    pooled = irs.get_bracket_distribution(DATA_YEAR)
    for index, bracket in enumerate(pooled):
        if bracket.num_returns <= 0:
            continue
        shares = [
            split[status][index].num_returns / bracket.num_returns for status in FILING_STATUSES
        ]
        assert sum(shares) == pytest.approx(1.0, rel=1e-9)
        assert all(share >= 0.0 for share in shares)


# ---------------------------------------------------------------------------
# The control: a uniform split is a no-op
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("threshold", CONTROL_THRESHOLDS)
def test_uniform_split_reproduces_the_pooled_aggregate(irs, threshold):
    pooled = irs.get_filers_by_bracket(DATA_YEAR, threshold)
    split = irs.get_filers_by_status_thresholds(
        DATA_YEAR, {status: threshold for status in FILING_STATUSES}
    )
    for key in (
        "num_filers_millions",
        "avg_agi",
        "avg_taxable_income",
        "total_agi_billions",
        "total_taxable_income_billions",
        "total_tax_billions",
        "effective_tax_rate",
    ):
        assert split[key] == pytest.approx(pooled[key], rel=1e-9), key
    # ``num_filers`` passes through int(round(...)) on both sides.
    assert abs(split["num_filers"] - pooled["num_filers"]) <= 1


@pytest.mark.parametrize("threshold", CONTROL_THRESHOLDS)
def test_uniform_split_reproduces_the_pooled_marginal_income(irs, threshold):
    pooled = irs.get_filers_by_bracket(DATA_YEAR, threshold)
    average = pooled["avg_taxable_income"]
    per_return = average if threshold == 0 else max(0.0, average - threshold)
    expected = per_return * pooled["num_filers"]

    split = irs.get_filers_by_status_thresholds(
        DATA_YEAR, {status: threshold for status in FILING_STATUSES}
    )
    # The pooled helper's ``num_filers`` passes through ``int(round(...))``
    # before it is multiplied out; the split sums floats. The gap is bounded by
    # half a return's marginal income - about $96k on a $1.8 trillion base at
    # the $400,000 floor - and is the only difference between the two paths.
    assert split["marginal_income_dollars"] == pytest.approx(expected, rel=1e-6)


def test_missing_status_is_an_error(irs):
    with pytest.raises(ValueError, match="threshold missing"):
        irs.get_filers_by_status_thresholds(DATA_YEAR, {"joint": 40_000.0})


# ---------------------------------------------------------------------------
# The policy field
# ---------------------------------------------------------------------------


def _policy(**kwargs) -> TaxPolicy:
    params = dict(
        name="test",
        description="test",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=0.02,
        affected_income_threshold=103_350,
        data_year=DATA_YEAR,
        start_year=2025,
        duration_years=10,
    )
    params.update(kwargs)
    return TaxPolicy(**params)


def test_partial_mapping_falls_back_to_the_single_threshold():
    policy = _policy(threshold_by_filing_status={"joint": 206_700})
    assert policy.resolved_filing_status_thresholds() == {
        "joint": 206_700.0,
        "separate": 103_350.0,
        "head_of_household": 103_350.0,
        "single": 103_350.0,
    }


def test_empty_mapping_declares_nothing():
    assert _policy(threshold_by_filing_status={}).threshold_by_filing_status is None


def test_unknown_status_is_rejected():
    with pytest.raises(ValueError, match="unknown filing status"):
        _policy(threshold_by_filing_status={"married": 206_700})


def test_negative_status_threshold_is_rejected():
    with pytest.raises(ValueError, match=">= 0"):
        _policy(threshold_by_filing_status={"joint": -1})


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def scorer() -> FiscalPolicyScorer:
    return FiscalPolicyScorer(use_real_data=True)


def test_uniform_split_scores_like_the_pooled_policy(scorer):
    pooled = scorer.score_policy(_policy(), dynamic=False)
    uniform = scorer.score_policy(
        _policy(threshold_by_filing_status={status: 103_350 for status in FILING_STATUSES}),
        dynamic=False,
    )
    assert uniform.total_10_year_cost == pytest.approx(pooled.total_10_year_cost, rel=1e-8)


def test_split_policy_carries_year_ones_answer_across_the_window(scorer):
    """Years 2-10 must be year 1, projected and nothing else.

    The pooled path re-derives its base on later years from
    ``avg_taxable_income_in_bracket`` minus one threshold, which is meaningless
    once the statuses face different floors. If the cache regresses, this test
    catches a policy that silently reverts to the pooled formula after year one.

    Until 2026-09-09 the observable was that the path was **flat**. The base is
    now projected onto each scored year
    (``planning/lanes/HSB_h2_base_growth.md``), so the invariant is stated the
    way it was always meant: divide each year's own factor back out and ten
    identical annuals must remain. A silent revert to the pooled formula would
    still break it, because the pooled formula returns a different level.
    """
    policy = _policy(threshold_by_filing_status={"joint": 206_700})
    result = scorer.score_policy(policy, dynamic=False)
    annual = np.asarray(result.final_deficit_effect, dtype=float)
    assert annual[0] != 0.0

    anchor = scorer.baseline.nominal_income_index(int(policy.soi_base_tax_year))
    factors = np.array(
        [scorer.baseline.nominal_income_index(int(year)) / anchor for year in result.years]
    )
    unprojected = annual / factors
    assert unprojected.max() == pytest.approx(unprojected.min(), abs=1e-9)


def test_raising_the_joint_floor_shrinks_the_base(scorer):
    baseline = scorer.score_policy(_policy(), dynamic=False).total_10_year_cost
    raised = scorer.score_policy(
        _policy(threshold_by_filing_status={"joint": 206_700}), dynamic=False
    ).total_10_year_cost
    # A rate increase scores negative (reduces the deficit); a smaller base is
    # a smaller magnitude.
    assert abs(raised) < abs(baseline)


def test_lowering_a_floor_grows_the_base(scorer):
    """The direction ``biden_high_income_tax`` exercises: one of its four floors
    is *below* the single-filer threshold, so its base grows."""
    baseline = scorer.score_policy(_policy(), dynamic=False).total_10_year_cost
    lowered = scorer.score_policy(
        _policy(threshold_by_filing_status={"separate": 51_675}), dynamic=False
    ).total_10_year_cost
    assert abs(lowered) > abs(baseline)


# ---------------------------------------------------------------------------
# The validation shapes
# ---------------------------------------------------------------------------


EXPECTED_SHAPE_THRESHOLDS = {
    # CBO Options 60557, report pp. 55-56; IRS Rev. Proc. 2024-40 s.2.01.
    "cbo_opt45_top4_brackets_2pp": {
        "joint": 206_700.0,
        "separate": 103_350.0,
        "head_of_household": 103_350.0,
        "single": 103_350.0,
    },
    "cbo_opt46_agi_surtax_1pp_20k": {
        "joint": 40_000.0,
        "separate": 20_000.0,
        "head_of_household": 20_000.0,
        "single": 20_000.0,
    },
    "cbo_opt46_agi_surtax_2pp_100k": {
        "joint": 200_000.0,
        "separate": 100_000.0,
        "head_of_household": 100_000.0,
        "single": 100_000.0,
    },
    # FY2025 Green Book, report p. 78 - all four printed in the proposal.
    "biden_high_income_tax": {
        "joint": 450_000.0,
        "separate": 225_000.0,
        "head_of_household": 425_000.0,
        "single": 400_000.0,
    },
}


@pytest.mark.parametrize("policy_id,expected", sorted(EXPECTED_SHAPE_THRESHOLDS.items()))
def test_validation_shape_carries_its_sources_thresholds(policy_id, expected):
    policy = create_policy_from_score(KNOWN_SCORES[policy_id])
    assert policy is not None
    assert policy.resolved_filing_status_thresholds() == expected


def test_only_the_four_sourced_rows_declare_a_split():
    """A boundary is recorded because a document prints it, never because a row
    would score better with one. ``medicare_surcharge_2pp`` in particular states
    one $400,000 amount for every return in its own proposal."""
    declared = {
        policy_id
        for policy_id, score in KNOWN_SCORES.items()
        if score.income_threshold_by_filing_status
    }
    assert declared == set(EXPECTED_SHAPE_THRESHOLDS)
    assert KNOWN_SCORES["medicare_surcharge_2pp"].income_threshold_by_filing_status is None


def test_declared_amounts_never_repeat_the_single_amount():
    """A per-status entry that equals ``income_threshold`` says nothing and would
    make the mapping look richer than the source is."""
    for policy_id in EXPECTED_SHAPE_THRESHOLDS:
        score = KNOWN_SCORES[policy_id]
        for status, value in (score.income_threshold_by_filing_status or {}).items():
            assert value != score.income_threshold, (
                f"{policy_id}: {status} repeats income_threshold; drop it and let "
                "FILING_STATUS_THRESHOLD_RULE supply the fallback"
            )


def test_no_declared_threshold_is_a_target_over_ten():
    """The anti-fitting invariant, restated for this lane's inputs."""
    for policy_id, score in KNOWN_SCORES.items():
        for value in (score.income_threshold_by_filing_status or {}).values():
            assert value != pytest.approx(abs(score.ten_year_cost) / 10.0), policy_id


def test_the_rule_for_unnamed_statuses_is_written_down():
    assert "1411(b)" in FILING_STATUS_THRESHOLD_RULE
    assert "income_threshold" in FILING_STATUS_THRESHOLD_RULE
