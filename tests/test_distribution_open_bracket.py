"""Distribution tables above SOI's open-ended $10M+ bracket.

The bracket path used to skip the open bracket whenever the threshold sat
above its floor, so +2pp above $10,000,001 printed an all-zero table while the
revenue score for the same policy was about -$52B. It now reads the same Pareto
tail the revenue score does (``IRSSOIData._shares_above_threshold``).
"""

from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest

from fiscal_model.distribution import DistributionalEngine, IncomeGroupType
from fiscal_model.policies import PolicyType, TaxPolicy
from fiscal_model.ui.tabs.distribution_analysis import _distribution_not_representable


def _policy(threshold: float) -> TaxPolicy:
    return TaxPolicy(
        name="t", description="t", policy_type=PolicyType.INCOME_TAX,
        rate_change=0.02, affected_income_threshold=threshold,
    )


@pytest.fixture(scope="module")
def bracket_totals() -> dict[float, float]:
    logging.disable(logging.CRITICAL)
    try:
        engine = DistributionalEngine()
        return {
            t: engine.analyze_policy(
                _policy(t), group_type=IncomeGroupType.JCT_DOLLAR, prefer_microsim=False
            ).total_tax_change
            for t in (9_990_000.0, 10_000_001.0, 20_000_000.0, 50_000_000.0)
        }
    finally:
        logging.disable(logging.NOTSET)


def test_thresholds_inside_the_open_bracket_are_not_zero(bracket_totals):
    assert bracket_totals[20_000_000.0] > 0
    assert bracket_totals[50_000_000.0] > 0
    assert bracket_totals[50_000_000.0] < bracket_totals[20_000_000.0]


def test_no_cliff_at_the_open_bracket_floor(bracket_totals):
    below, above = bracket_totals[9_990_000.0], bracket_totals[10_000_001.0]
    assert above == pytest.approx(below, rel=0.01)


def test_all_zero_table_for_a_rate_change_reads_as_not_available():
    """An all-zero table for a non-zero rate change is a coverage gap (nobody in
    the population above the threshold), not a flat result."""
    zero = SimpleNamespace(
        results=[SimpleNamespace(tax_change_avg=0.0)] * 5, total_tax_change=0.0
    )
    assert _distribution_not_representable(_policy(50_000_000.0), zero) is True
