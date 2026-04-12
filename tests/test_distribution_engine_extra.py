"""
Focused tests for lower-coverage distribution engine branches.
"""

from __future__ import annotations

import pandas as pd
import pytest

import fiscal_model.microsim.engine as microsim_engine
from fiscal_model.distribution import DistributionalEngine, IncomeGroup, IncomeGroupType
from fiscal_model.policies import PolicyType, TaxPolicy


def test_brackets_fall_back_to_synthetic_when_irs_year_missing(monkeypatch):
    engine = DistributionalEngine(data_year=2099)

    monkeypatch.setattr(
        engine.irs_data,
        "get_bracket_distribution",
        lambda year: (_ for _ in ()).throw(FileNotFoundError(f"missing {year}")),
    )

    groups = engine.create_income_groups(IncomeGroupType.QUINTILE)

    assert len(groups) == 5
    assert engine.total_returns > 0
    assert engine.brackets


def test_analyze_policy_microsim_handles_empty_groups_and_weighted_changes(monkeypatch):
    engine = DistributionalEngine(data_year=2022)
    policy = TaxPolicy(
        name="Microsim Test",
        description="Microsim branch coverage",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=0.01,
        affected_income_threshold=0,
    )
    microdata = pd.DataFrame(
        {
            "agi": [2_000_000.0, 4_000_000.0],
            "weight": [1.0, 2.0],
        }
    )
    groups = [
        IncomeGroup(name="Empty Group", floor=0, ceiling=100_000, num_returns=0),
        IncomeGroup(name="All Filers", floor=0, ceiling=None, num_returns=2),
    ]

    class _DummyMicroTaxCalculator:
        def __init__(self, year: int):
            self.year = year

        def calculate(self, pop: pd.DataFrame) -> pd.DataFrame:
            result = pop.copy()
            result["final_tax"] = [200_000.0, 500_000.0]
            return result

        def apply_reform(self, pop: pd.DataFrame, reforms: dict) -> pd.DataFrame:
            del reforms
            result = pop.copy()
            result["final_tax"] = [700_000.0, 1_200_000.0]
            return result

    monkeypatch.setattr(microsim_engine, "MicroTaxCalculator", _DummyMicroTaxCalculator)
    monkeypatch.setattr(
        "fiscal_model.distribution_engine.policy_to_microsim_reforms",
        lambda policy, year: {"year": year, "policy": policy.name},
    )
    monkeypatch.setattr(
        "fiscal_model.distribution_engine.create_groups_from_microdata",
        lambda merged, group_type: groups,
    )

    result = engine.analyze_policy_microsim(
        policy=policy,
        microdata=microdata,
        group_type=IncomeGroupType.QUINTILE,
        year=2026,
    )

    assert result.year == 2026
    assert result.total_tax_change == pytest.approx(0.0019)
    assert result.total_affected_returns == 2
    assert result.results[0].pct_unchanged == 100.0
    assert result.results[1].pct_with_increase == 100.0
    assert result.results[1].share_of_total_change == pytest.approx(1.0)
