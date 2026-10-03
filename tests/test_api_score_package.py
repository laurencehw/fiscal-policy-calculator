"""``FiscalPolicyScorer.score_package`` — interaction factor and empty packages.

Lives with the API tests because the API's scoring engine entry point is the
same ``scoring_engine`` module; reproduced on the real scorer.
"""

from __future__ import annotations

import pytest

from fiscal_model.baseline import APP_DEFAULT_START_YEAR
from fiscal_model.policies import PolicyType, TaxPolicy
from fiscal_model.policies_core import PolicyPackage
from fiscal_model.scoring import FiscalPolicyScorer


@pytest.fixture(scope="module")
def scorer():
    return FiscalPolicyScorer(start_year=APP_DEFAULT_START_YEAR, use_real_data=True)


@pytest.fixture(scope="module")
def policy():
    return TaxPolicy(
        name="t",
        description="d",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=0.01,
        affected_income_threshold=400000,
        start_year=APP_DEFAULT_START_YEAR,
    )


def _package(policy, factor):
    return PolicyPackage(
        name="p", description="d", policies=[policy], interaction_factor=factor
    )


def test_default_factor_is_the_single_policy_score(scorer, policy):
    single = scorer.score_policy(policy, dynamic=False)
    packaged = scorer.score_package(_package(policy, 1.0))
    assert packaged.final_deficit_effect.sum() == pytest.approx(
        single.final_deficit_effect.sum()
    )
    assert packaged.behavioral_offset.sum() == pytest.approx(
        single.behavioral_offset.sum()
    )


def test_interaction_factor_scales_the_behavioral_offset_with_its_static(scorer, policy):
    single = scorer.score_policy(policy, dynamic=False)
    half = scorer.score_package(_package(policy, 0.5))

    assert half.static_deficit_effect.sum() == pytest.approx(
        0.5 * single.static_deficit_effect.sum()
    )
    assert half.behavioral_offset.sum() == pytest.approx(
        0.5 * single.behavioral_offset.sum()
    )
    # The headline: half the conventional score, not half the static score plus
    # a full-size offset (-$49.8B against -$58.1B on this policy).
    assert half.final_deficit_effect.sum() == pytest.approx(
        0.5 * single.final_deficit_effect.sum()
    )
    # The band moves with the central estimate.
    assert half.low_estimate.sum() == pytest.approx(0.5 * single.low_estimate.sum())
    assert half.high_estimate.sum() == pytest.approx(0.5 * single.high_estimate.sum())


def test_an_empty_package_is_a_clean_value_error(scorer):
    with pytest.raises(ValueError, match="empty package"):
        scorer.score_package(PolicyPackage(name="e", description="d"))
