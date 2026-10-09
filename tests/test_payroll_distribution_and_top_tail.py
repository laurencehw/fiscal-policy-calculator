"""Payroll presets reach the distribution table; the $10M+ bracket has a tail.

Both were open findings from the 2026-08-31 review:

* ``calculate_payroll_effect`` read ``current_ss_cap`` / ``new_ss_cap``, which
  ``PayrollTaxPolicy`` does not define, so every cap preset produced an
  all-zero table and the tab said "not available".
* ``IRSSOIData`` prorated the open-ended top bracket linearly to its mean, so a
  threshold above about $30M scored exactly nothing.
"""

from __future__ import annotations

import pytest

from fiscal_model import payroll
from fiscal_model.data.irs_soi import IRSSOIData, TaxBracketData
from fiscal_model.distribution import DistributionalEngine, IncomeGroupType


@pytest.fixture(scope="module")
def engine():
    return DistributionalEngine(data_year=2022)


def _table(engine, policy):
    return engine.analyze_policy(
        policy, group_type=IncomeGroupType.QUINTILE, prefer_microsim=False
    )


@pytest.mark.parametrize(
    "factory",
    [
        payroll.create_ss_donut_hole,
        payroll.create_ss_eliminate_cap,
        payroll.create_ss_cap_90_percent,
        payroll.create_biden_payroll_proposal,
        payroll.create_expand_niit,
    ],
)
def test_cap_and_high_income_payroll_presets_land_on_the_top_quintile(engine, factory):
    table = _table(engine, factory())
    assert table.total_tax_change > 0
    top = table.results[-1]
    assert top.tax_change_total == pytest.approx(table.total_tax_change)
    assert all(r.tax_change_total == 0 for r in table.results[:-1])


def test_payroll_cap_designs_order_as_their_scores_do(engine):
    eliminate = _table(engine, payroll.create_ss_eliminate_cap()).total_tax_change
    donut = _table(engine, payroll.create_ss_donut_hole()).total_tax_change
    cover_90 = _table(engine, payroll.create_ss_cap_90_percent()).total_tax_change
    # Eliminating the cap taxes a superset of what a $250K donut or a
    # 90%-coverage cap reaches.
    assert eliminate > donut > cover_90 > 0


def test_payroll_rate_increase_reaches_every_quintile(engine):
    table = _table(engine, payroll.create_ss_rate_increase(0.01))
    assert all(r.tax_change_total > 0 for r in table.results)


def _top_bracket(floor=10_000_000.0, returns=30_000.0, mean=30_000_000.0):
    return TaxBracketData(
        year=2023,
        agi_floor=floor,
        agi_ceiling=None,
        num_returns=returns,
        total_agi=returns * mean / 1e9,
        taxable_income=returns * mean / 1e9,
        total_tax=0.0,
    )


def test_top_bracket_tail_is_continuous_at_its_floor():
    assert IRSSOIData._shares_above_threshold(_top_bracket(), 10_000_000.0) == (1.0, 1.0)


def test_top_bracket_tail_never_runs_out_above_the_mean():
    bracket = _top_bracket()
    previous = (1.0, 1.0)
    for threshold in (2e7, 3e7, 5e7, 1e8, 1e9):
        returns_share, income_share = IRSSOIData._shares_above_threshold(bracket, threshold)
        assert 0 < returns_share < previous[0]
        assert 0 < income_share < previous[1]
        # The filers kept above a higher threshold are richer on average.
        assert income_share > returns_share
        previous = (returns_share, income_share)


def test_average_agi_rises_with_threshold_above_ten_million():
    irs = IRSSOIData()
    low = irs.get_filers_by_bracket(2023, 20_000_000)
    high = irs.get_filers_by_bracket(2023, 100_000_000)
    assert high["num_filers"] > 0
    assert high["avg_agi"] > low["avg_agi"] > 20_000_000
    assert high["avg_agi"] > 100_000_000


def test_thresholds_below_the_top_floor_are_unchanged():
    """The tail rule only touches thresholds inside the open-ended bracket."""
    irs = IRSSOIData()
    for bracket in irs.get_bracket_distribution(2023):
        if bracket.agi_ceiling is None:
            continue
        mid = (bracket.agi_floor + bracket.agi_ceiling) / 2
        returns_share, income_share = IRSSOIData._shares_above_threshold(bracket, mid)
        assert returns_share == income_share == pytest.approx(0.5)
