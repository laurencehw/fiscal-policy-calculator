"""R7b: an all-bracket rate change reaches every bracket of the distribution table.

``planning/lanes/R7_weighted_group_totals.md`` §7. A plain income-tax
``TaxPolicy`` with no threshold used to map to ``new_top_rate = 0.37 + Δ``, so
its distribution table changed only the 37% bracket while its revenue score
priced every bracket.
"""

from __future__ import annotations

import logging

import pytest

from fiscal_model.distribution import DistributionalEngine, IncomeGroupType
from fiscal_model.distribution_effects import policy_to_microsim_reforms
from fiscal_model.policies import PolicyType, TaxPolicy


def _policy(rate: float, threshold: float = 0.0) -> TaxPolicy:
    return TaxPolicy(
        name=f"{rate:+.3f} above {threshold:,.0f}",
        description="R7b",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=rate,
        affected_income_threshold=threshold,
        start_year=2026,
    )


@pytest.fixture(scope="module")
def engine() -> DistributionalEngine:
    return DistributionalEngine()


@pytest.mark.parametrize("rate", [0.01, -0.01])
def test_all_bracket_change_reaches_every_quintile(engine, rate):
    analysis = engine.analyze_policy(_policy(rate), group_type=IncomeGroupType.QUINTILE)
    assert analysis.engine == "microsim"
    for result in analysis.results:
        # Every group's tax moves in the policy's direction...
        assert result.tax_change_total * rate > 0, result.income_group.name
        # ...and a real share of each group is affected, not 0.34% of the top.
        affected = result.pct_with_increase if rate > 0 else result.pct_with_decrease
        assert affected > 0, result.income_group.name
    top = analysis.results[-1]
    assert abs(top.share_of_total_change) < 0.75  # it was 100%


def test_all_bracket_total_agrees_with_the_revenue_score_in_sign_and_order(engine):
    from fiscal_model.composer.composer import _scorer_for

    policy = _policy(0.01)
    logging.disable(logging.CRITICAL)
    try:
        score = _scorer_for(policy, True).score_policy(policy, dynamic=False)
    finally:
        logging.disable(logging.NOTSET)
    revenue_year_one = float(score.static_revenue_effect[0])  # $B, + = revenue
    table_total = engine.analyze_policy(policy, group_type=IncomeGroupType.QUINTILE).total_tax_change
    assert revenue_year_one > 0 and table_total > 0
    # Same order of magnitude: about 0.75 on the shipped CPS file (the microsim
    # base is CPS ordinary taxable income, the score's is SOI); it was 0.015.
    assert 0.5 < table_total / revenue_year_one < 1.5


def test_mapping_is_one_rule_at_every_threshold():
    for threshold in (0.0, 50_000.0, 400_000.0, 609_350.0, 2_000_000.0):
        assert policy_to_microsim_reforms(_policy(0.02, threshold)) == {
            "income_rate_change": 0.02,
            "income_rate_change_threshold": threshold,
        }


def test_threshold_policies_are_byte_identical_to_before(engine):
    """A policy above a threshold is untouched: same reform dict as the old
    branch, same table to the last bit as recorded before R7b."""
    top_45 = _policy(0.08, 609_350.0)
    assert policy_to_microsim_reforms(top_45) == {
        "income_rate_change": 0.08,
        "income_rate_change_threshold": 609_350.0,
    }
    analysis = engine.analyze_policy(top_45, group_type=IncomeGroupType.QUINTILE)
    assert [r.tax_change_total for r in analysis.results] == [
        0.0, 0.0, 0.0, 0.0, 21.06182331932978,
    ]
