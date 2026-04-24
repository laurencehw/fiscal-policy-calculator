"""
Tests for the tax-expenditure distributional dispatch.

``calculate_tax_expenditure_effect`` was added so TaxExpenditurePolicy
types (SALT cap repeal, mortgage-interest deduction, step-up basis,
etc.) route through a dedicated tier-table calculator instead of the
generic fallback. These tests verify the dispatch wiring and the tier
tables' shape; the full SALT benchmark accuracy is asserted in
``test_benchmark_runners.py``.
"""

from __future__ import annotations

import pytest

from fiscal_model.distribution import DistributionalEngine, IncomeGroupType
from fiscal_model.distribution_effects import _TAX_EXPENDITURE_TIER_TABLES
from fiscal_model.tax_expenditures import (
    TaxExpenditurePolicy,
    create_cap_employer_health_exclusion,
    create_eliminate_step_up_basis,
    create_repeal_salt_cap,
)


class TestTierTables:
    def test_all_tier_tables_sum_to_one(self):
        for name, tiers in _TAX_EXPENDITURE_TIER_TABLES.items():
            total = sum(share for _lo, _hi, share in tiers)
            assert abs(total - 1.0) < 0.005, (
                f"{name} tier table sums to {total}, not 1.0"
            )

    def test_salt_table_matches_jct_jcx_4_24(self):
        """SALT tier table is the source of truth for JCT benchmark match."""
        salt = dict(
            ((lo, hi), share)
            for lo, hi, share in _TAX_EXPENDITURE_TIER_TABLES["SALT"]
        )
        # JCT JCX-4-24 published shares, keyed by AGI band floor.
        assert salt[(1_000_000, float("inf"))] == pytest.approx(0.382, abs=0.001)
        assert salt[(500_000, 1_000_000)] == pytest.approx(0.279, abs=0.001)
        assert salt[(200_000, 500_000)] == pytest.approx(0.281, abs=0.001)

    def test_step_up_is_extremely_top_heavy(self):
        r"""Per JCT, ~90% of step-up's benefit goes to filers above \$500K."""
        tiers = _TAX_EXPENDITURE_TIER_TABLES["STEP_UP_BASIS"]
        top_slice = sum(
            share for lo, _hi, share in tiers if lo >= 500_000
        )
        assert top_slice >= 0.85

    def test_employer_health_is_broadly_held(self):
        """Employer health exclusion mostly goes to the middle."""
        tiers = _TAX_EXPENDITURE_TIER_TABLES["EMPLOYER_HEALTH"]
        middle_slice = sum(
            share for lo, hi, share in tiers
            if 50_000 <= lo and (hi <= 500_000 or hi == 500_000)
        )
        assert middle_slice >= 0.70


class TestDispatchWiresTaxExpenditurePolicies:
    def _run(self, policy: TaxExpenditurePolicy):
        engine = DistributionalEngine(data_year=2022)
        return engine.analyze_policy(policy, group_type=IncomeGroupType.JCT_DOLLAR)

    def test_salt_cap_repeal_concentrates_at_top(self):
        policy = create_repeal_salt_cap()
        result = self._run(policy)
        shares = {r.income_group.name: r.share_of_total_change for r in result.results}
        # At least 60% of the effect should accrue to filers above $500K.
        top = shares.get("$500K-$1M", 0) + shares.get("$1M and over", 0)
        assert abs(top) >= 0.60

    def test_step_up_elimination_concentrates_at_top(self):
        policy = create_eliminate_step_up_basis()
        result = self._run(policy)
        shares = {r.income_group.name: r.share_of_total_change for r in result.results}
        top = shares.get("$1M and over", 0)
        assert abs(top) >= 0.60

    def test_employer_health_cap_more_evenly_distributed(self):
        policy = create_cap_employer_health_exclusion()
        result = self._run(policy)
        shares = {
            r.income_group.name: abs(r.share_of_total_change) for r in result.results
        }
        # The top bracket should NOT dominate — employer health is broadly held.
        top = shares.get("$1M and over", 0)
        assert top < 0.25
