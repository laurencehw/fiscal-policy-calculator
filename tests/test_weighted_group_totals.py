"""R7: every tax-unit microsim group statistic is weighted.

``planning/lanes/R7_weighted_group_totals.md``. Before R7,
``create_groups_from_microdata`` weighted the return count and summed AGI,
taxable income and tax unweighted, and the tax-unit branch of
``analyze_policy_microsim`` counted rows for ``pct_with_*`` and the ETRs. The
synthetic frames here use weights 1 and 1,000 so an unweighted sum cannot pass.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

import fiscal_model.microsim.engine as microsim_engine
from fiscal_model.distribution import DistributionalEngine, IncomeGroupType
from fiscal_model.distribution_grouping import create_groups_from_microdata
from fiscal_model.policies import PolicyType, TaxPolicy


def _two_row_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "agi": [200_000.0, 250_000.0],
            "taxable_income": [170_000.0, 220_000.0],
            "final_tax": [30_000.0, 45_000.0],
            "weight": [1.0, 1000.0],
        }
    )


class TestGroupTotals:
    def test_money_totals_are_weighted(self):
        groups = create_groups_from_microdata(_two_row_frame(), IncomeGroupType.QUINTILE)
        top = next(g for g in groups if g.name == "Top Quintile")

        assert top.num_returns == 1001
        assert top.total_agi == pytest.approx((200_000 + 250_000 * 1000) / 1e9)
        assert top.total_taxable_income == pytest.approx((170_000 + 220_000 * 1000) / 1e9)
        assert top.baseline_tax == pytest.approx((30_000 + 45_000 * 1000) / 1e9)
        # The shipped (unweighted) code gave $449.55; the weighted average is
        # inside the group's own AGI range.
        assert top.avg_agi == pytest.approx(250_200_000 / 1001)
        assert 200_000 <= top.avg_agi <= 250_000
        assert top.effective_tax_rate == pytest.approx(45_030_000 / 250_200_000)

    def test_frame_without_weight_is_weight_one(self):
        frame = _two_row_frame().drop(columns="weight")
        top = next(
            g
            for g in create_groups_from_microdata(frame, IncomeGroupType.QUINTILE)
            if g.name == "Top Quintile"
        )
        assert top.num_returns == 2
        assert top.total_agi == pytest.approx(450_000 / 1e9)
        assert top.baseline_tax == pytest.approx(75_000 / 1e9)

    @pytest.mark.parametrize(
        "group_type",
        [IncomeGroupType.QUINTILE, IncomeGroupType.DECILE, IncomeGroupType.JCT_DOLLAR],
    )
    def test_group_totals_sum_to_the_weighted_population(self, group_type):
        """Invariant: the groups partition AGI >= 0, so their totals add up."""
        rng = np.random.default_rng(7)
        n = 2_000
        agi = rng.lognormal(mean=11.0, sigma=1.2, size=n)
        frame = pd.DataFrame(
            {
                "agi": agi,
                "taxable_income": agi * 0.8,
                "final_tax": agi * rng.uniform(-0.05, 0.3, size=n),
                "weight": rng.uniform(100.0, 20_000.0, size=n),
            }
        )
        groups = create_groups_from_microdata(frame, group_type)
        w = frame["weight"]
        assert sum(g.total_agi for g in groups) == pytest.approx((frame["agi"] * w).sum() / 1e9)
        assert sum(g.total_taxable_income for g in groups) == pytest.approx(
            (frame["taxable_income"] * w).sum() / 1e9
        )
        assert sum(g.baseline_tax for g in groups) == pytest.approx(
            (frame["final_tax"] * w).sum() / 1e9
        )
        assert sum(g.population_share for g in groups) == pytest.approx(1.0, abs=1e-6)

    def test_invariant_on_the_shipped_microdata(self):
        """Same invariant on the shipped CPS file's AGI and weights."""
        from fiscal_model.data.cps_asec import load_tax_microdata

        df, _ = load_tax_microdata()
        frame = df[["agi", "weight"]].copy()
        frame["taxable_income"] = frame["agi"]
        frame["final_tax"] = frame["agi"] * 0.1
        groups = create_groups_from_microdata(frame, IncomeGroupType.QUINTILE)
        in_scope = frame["agi"] >= 0
        expected_agi = (frame.loc[in_scope, "agi"] * frame.loc[in_scope, "weight"]).sum() / 1e9
        assert sum(g.total_agi for g in groups) == pytest.approx(expected_agi, rel=1e-12)
        # The defect put the top quintile's average AGI near $130; a weighted
        # average sits inside the group's own range.
        top = groups[-1]
        assert top.avg_agi >= top.floor


class _DummyCalculator:
    """Baseline tax per row; the reform raises tax on the first row only."""

    def __init__(self, year: int):
        self.year = year

    def calculate(self, pop: pd.DataFrame) -> pd.DataFrame:
        out = pop.copy()
        out["taxable_income"] = out["agi"] * 0.8
        out["final_tax"] = [30_000.0, 45_000.0]
        return out

    def apply_reform(self, pop: pd.DataFrame, reforms: dict) -> pd.DataFrame:
        del reforms
        out = pop.copy()
        out["final_tax"] = [40_000.0, 45_000.0]
        return out


@pytest.fixture
def two_row_analysis(monkeypatch):
    monkeypatch.setattr(microsim_engine, "MicroTaxCalculator", _DummyCalculator)
    monkeypatch.setattr(
        "fiscal_model.distribution_engine.policy_to_microsim_reforms",
        lambda policy, year: {"stub": True},
    )
    policy = TaxPolicy(
        name="R7 weights",
        description="two-row weighting check",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=0.01,
        affected_income_threshold=0,
    )
    frame = _two_row_frame()[["agi", "weight"]].assign(state_fips=6)
    return DistributionalEngine().analyze_policy_microsim(
        policy, microdata=frame, group_type=IncomeGroupType.QUINTILE, year=2026
    )


class TestTaxUnitBranch:
    def test_share_with_increase_is_weighted(self, two_row_analysis):
        top = next(r for r in two_row_analysis.results if r.income_group.name == "Top Quintile")
        # Row-counting gave 50%; one return in 1,001 had its tax raised.
        assert top.pct_with_increase == pytest.approx(100 / 1001)
        assert top.pct_unchanged == pytest.approx(100 * 1000 / 1001)
        assert top.pct_with_decrease == 0.0

    def test_etrs_and_percent_of_income_are_weighted(self, two_row_analysis):
        top = next(r for r in two_row_analysis.results if r.income_group.name == "Top Quintile")
        agi_w = 200_000 + 250_000 * 1000
        assert top.baseline_etr == pytest.approx((30_000 + 45_000 * 1000) / agi_w)
        assert top.new_etr == pytest.approx((40_000 + 45_000 * 1000) / agi_w)
        avg_change = 10_000 / 1001
        after_tax_avg = (170_000 + 205_000 * 1000) / 1001
        assert top.tax_change_avg == pytest.approx(avg_change)
        assert top.tax_change_pct_income == pytest.approx(avg_change / after_tax_avg * 100)
        # The dollar change was already weighted and must not move.
        assert top.tax_change_total == pytest.approx(10_000 / 1e9)

    def test_summary_share_equals_the_weighted_count(self, two_row_analysis):
        from fiscal_model.distribution_reporting import generate_winners_losers_summary

        summary = generate_winners_losers_summary(two_row_analysis)
        assert summary["pct_with_increase"] == pytest.approx(100 / 1001, rel=1e-3)
