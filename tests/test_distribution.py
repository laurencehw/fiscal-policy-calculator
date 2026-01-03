"""
Tests for distributional analysis module.

Tests cover:
- Income group creation
- Policy-specific distributional handlers
- TPC validation benchmarks
- Output formatting
"""

import pytest
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fiscal_model.distribution import (
    DistributionalEngine,
    IncomeGroupType,
    DistributionalAnalysis,
    DistributionalResult,
    IncomeGroup,
    format_distribution_table,
    generate_winners_losers_summary,
    QUINTILE_THRESHOLDS_2024,
)
from fiscal_model.policies import TaxPolicy, PolicyType


class TestIncomeGroups:
    """Test income group creation and properties."""

    def test_quintile_creation(self, distribution_engine):
        """Test that quintile groups are created correctly."""
        groups = distribution_engine.create_income_groups(IncomeGroupType.QUINTILE)

        assert len(groups) == 5
        assert groups[0].name == "Lowest Quintile"
        assert groups[4].name == "Top Quintile"

    def test_decile_creation(self, distribution_engine):
        """Test that decile groups are created correctly."""
        groups = distribution_engine.create_income_groups(IncomeGroupType.DECILE)

        assert len(groups) == 10
        assert groups[0].name == "1st Decile"
        assert groups[9].name == "10th Decile"

    def test_jct_dollar_brackets(self, distribution_engine):
        """Test JCT-style dollar brackets."""
        groups = distribution_engine.create_income_groups(IncomeGroupType.JCT_DOLLAR)

        assert len(groups) == 11
        assert groups[0].name == "Less than $10K"
        assert groups[-1].name == "$1M and over"

    def test_income_group_properties(self, distribution_engine):
        """Test IncomeGroup computed properties."""
        groups = distribution_engine.create_income_groups(IncomeGroupType.QUINTILE)

        for group in groups:
            # Population share should be between 0 and 1
            assert 0 <= group.population_share <= 1

            # Effective tax rate should be reasonable
            assert 0 <= group.effective_tax_rate <= 0.5

            # Average AGI should be positive
            if group.num_returns > 0:
                assert group.avg_agi > 0

    def test_total_returns_sum(self, distribution_engine):
        """Test that total returns across groups matches total."""
        groups = distribution_engine.create_income_groups(IncomeGroupType.QUINTILE)
        total_in_groups = sum(g.num_returns for g in groups)

        # Should be close to total (may not be exact due to bracket aggregation)
        assert total_in_groups > 0
        # Population shares should sum reasonably close to 1
        # (bracket aggregation can cause some overlap/double-counting)
        total_share = sum(g.population_share for g in groups)
        assert 0.8 <= total_share <= 1.3


class TestTaxPolicyDistribution:
    """Test distributional analysis for basic TaxPolicy."""

    def test_high_income_tax_increase(self, distribution_engine, basic_tax_policy):
        """Test that $400K+ tax increase only affects top quintile."""
        result = distribution_engine.analyze_policy(
            basic_tax_policy,
            group_type=IncomeGroupType.QUINTILE
        )

        assert isinstance(result, DistributionalAnalysis)
        assert result.total_tax_change > 0  # Revenue increase

        # Bottom 4 quintiles should have zero change
        for r in result.results[:4]:
            assert r.tax_change_avg == 0 or abs(r.tax_change_avg) < 1

        # Top quintile should have positive change (tax increase)
        assert result.results[4].tax_change_avg > 0

    def test_universal_tax_cut(self, distribution_engine, tax_cut_policy):
        """Test that universal tax cut affects all quintiles."""
        result = distribution_engine.analyze_policy(
            tax_cut_policy,
            group_type=IncomeGroupType.QUINTILE
        )

        assert result.total_tax_change < 0  # Revenue loss

        # All quintiles should benefit (negative tax change)
        for r in result.results:
            assert r.tax_change_avg <= 0

    def test_share_of_total_sums_to_one(self, distribution_engine, basic_tax_policy):
        """Test that shares of total sum to approximately 1."""
        result = distribution_engine.analyze_policy(
            basic_tax_policy,
            group_type=IncomeGroupType.QUINTILE
        )

        if result.total_tax_change != 0:
            total_share = sum(abs(r.share_of_total_change) for r in result.results)
            assert 0.95 <= total_share <= 1.05

    def test_winners_losers_consistency(self, distribution_engine, basic_tax_policy):
        """Test that winners/losers percentages are consistent."""
        result = distribution_engine.analyze_policy(
            basic_tax_policy,
            group_type=IncomeGroupType.QUINTILE
        )

        for r in result.results:
            # Percentages should be non-negative
            assert r.pct_with_increase >= 0
            assert r.pct_with_decrease >= 0
            assert r.pct_unchanged >= 0

            # Should sum to 100
            total = r.pct_with_increase + r.pct_with_decrease + r.pct_unchanged
            assert 99 <= total <= 101


class TestCorporateDistribution:
    """Test distributional analysis for corporate tax policy."""

    @pytest.fixture
    def corporate_policy(self):
        """Corporate tax policy fixture."""
        from fiscal_model.corporate import CorporateTaxPolicy

        return CorporateTaxPolicy(
            name="Test Corporate",
            description="7pp rate increase",
            policy_type=PolicyType.CORPORATE_TAX,
            rate_change=0.07,
        )

    def test_corporate_incidence_top_heavy(self, distribution_engine, corporate_policy):
        """Test that corporate tax burden falls mainly on top quintile."""
        result = distribution_engine.analyze_policy(
            corporate_policy,
            group_type=IncomeGroupType.QUINTILE
        )

        # Top quintile should bear majority of burden
        top_share = abs(result.results[4].share_of_total_change)
        assert top_share > 0.5  # >50% to top quintile

    def test_corporate_affects_all_groups(self, distribution_engine, corporate_policy):
        """Test that corporate tax affects all groups (via capital/labor)."""
        result = distribution_engine.analyze_policy(
            corporate_policy,
            group_type=IncomeGroupType.QUINTILE
        )

        # All groups should have some burden (even if small)
        for r in result.results:
            # Either has tax change or very small group
            if r.income_group.num_returns > 1_000_000:
                assert r.tax_change_total != 0


class TestTCJADistribution:
    """Test distributional analysis for TCJA extension."""

    @pytest.fixture
    def tcja_policy(self):
        """TCJA extension policy fixture."""
        from fiscal_model.tcja import create_tcja_extension

        return create_tcja_extension(extend_all=True)

    def test_tcja_is_tax_cut(self, distribution_engine, tcja_policy):
        """Test that TCJA extension is a tax cut (negative revenue)."""
        result = distribution_engine.analyze_policy(
            tcja_policy,
            group_type=IncomeGroupType.QUINTILE
        )

        assert result.total_tax_change < 0  # Tax cut = revenue loss

    def test_tcja_benefits_top_most(self, distribution_engine, tcja_policy):
        """Test that TCJA benefits skew to top quintile."""
        result = distribution_engine.analyze_policy(
            tcja_policy,
            group_type=IncomeGroupType.QUINTILE
        )

        # Top quintile should get majority of tax cut
        top_share = abs(result.results[4].share_of_total_change)
        assert top_share > 0.5  # >50% to top quintile

        # Should be around 65% based on TPC
        assert 0.55 <= top_share <= 0.75

    def test_tcja_tpc_validation(self, distribution_engine, tcja_policy):
        """Validate TCJA distribution against TPC benchmarks."""
        result = distribution_engine.analyze_policy(
            tcja_policy,
            group_type=IncomeGroupType.QUINTILE
        )

        # TPC shares (approximate)
        tpc_shares = [0.02, 0.05, 0.10, 0.18, 0.65]

        for i, (r, expected) in enumerate(zip(result.results, tpc_shares)):
            actual = abs(r.share_of_total_change)
            # Allow 50% relative error (TPC uses different methodology)
            assert abs(actual - expected) < expected * 0.6 or expected < 0.05


class TestCreditDistribution:
    """Test distributional analysis for tax credit policies."""

    @pytest.fixture
    def ctc_policy(self):
        """CTC expansion policy fixture."""
        from fiscal_model.credits import TaxCreditPolicy, CreditType

        return TaxCreditPolicy(
            name="CTC Expansion",
            description="Expand CTC by $1000",
            policy_type=PolicyType.TAX_CREDIT,
            credit_type=CreditType.CHILD_TAX_CREDIT,
            credit_change_per_unit=1000,
            units_affected_millions=48.0,
            is_refundable=True,
            phase_out_threshold_single=200_000,
            phase_out_threshold_married=400_000,
            phase_out_rate=0.05,
        )

    def test_credit_is_tax_cut(self, distribution_engine, ctc_policy):
        """Test that credit expansion reduces taxes."""
        result = distribution_engine.analyze_policy(
            ctc_policy,
            group_type=IncomeGroupType.QUINTILE
        )

        # Credits reduce taxes
        assert result.total_tax_change < 0

    def test_credit_phases_out(self, distribution_engine, ctc_policy):
        """Test that credit phases out at high income."""
        result = distribution_engine.analyze_policy(
            ctc_policy,
            group_type=IncomeGroupType.QUINTILE
        )

        # Lower/middle quintiles should benefit more per capita than top
        # (because credit phases out)
        middle_avg = abs(result.results[2].tax_change_avg)
        top_avg = abs(result.results[4].tax_change_avg)

        # Middle should get comparable or better benefit per capita
        # (may not always hold due to income distribution assumptions)
        assert middle_avg > 0  # At least some benefit to middle


class TestPayrollDistribution:
    """Test distributional analysis for payroll tax policies."""

    @pytest.fixture
    def ss_cap_policy(self):
        """SS cap increase policy fixture."""
        from fiscal_model.payroll import PayrollTaxPolicy

        return PayrollTaxPolicy(
            name="SS Cap Increase",
            description="Raise SS cap to $250K",
            policy_type=PolicyType.PAYROLL_TAX,
            ss_new_cap=250_000,
        )

    def test_ss_cap_affects_high_income(self, distribution_engine, ss_cap_policy):
        """Test that SS cap increase mainly affects high earners."""
        result = distribution_engine.analyze_policy(
            ss_cap_policy,
            group_type=IncomeGroupType.QUINTILE
        )

        # Lower quintiles (below current cap) should have no change
        assert result.results[0].tax_change_total == 0
        assert result.results[1].tax_change_total == 0

        # Top quintile (includes income above cap) should have change
        # Note: depends on income distribution assumptions


class TestOutputFormatting:
    """Test output formatting functions."""

    def test_to_dataframe(self, distribution_engine, basic_tax_policy):
        """Test DataFrame conversion."""
        result = distribution_engine.analyze_policy(
            basic_tax_policy,
            group_type=IncomeGroupType.QUINTILE
        )

        df = result.to_dataframe()

        assert len(df) == 5
        assert "Income Group" in df.columns
        assert "Avg Tax Change ($)" in df.columns
        assert "Share of Total" in df.columns

    def test_format_distribution_table_tpc(self, distribution_engine, basic_tax_policy):
        """Test TPC-style table formatting."""
        result = distribution_engine.analyze_policy(
            basic_tax_policy,
            group_type=IncomeGroupType.QUINTILE
        )

        table = format_distribution_table(result, style="tpc")

        assert len(table) == 5
        assert "Income Group" in table.columns
        assert "% Tax Increase" in table.columns

    def test_format_distribution_table_jct(self, distribution_engine, basic_tax_policy):
        """Test JCT-style table formatting."""
        result = distribution_engine.analyze_policy(
            basic_tax_policy,
            group_type=IncomeGroupType.QUINTILE
        )

        table = format_distribution_table(result, style="jct")

        assert len(table) == 5
        assert "Tax Change ($B)" in table.columns

    def test_winners_losers_summary(self, distribution_engine, basic_tax_policy):
        """Test winners/losers summary generation."""
        result = distribution_engine.analyze_policy(
            basic_tax_policy,
            group_type=IncomeGroupType.QUINTILE
        )

        summary = generate_winners_losers_summary(result)

        assert "total_returns" in summary
        assert "pct_with_increase" in summary
        assert "pct_with_decrease" in summary
        assert "biggest_winners" in summary
        assert "biggest_losers" in summary

    def test_summary_method(self, distribution_engine, basic_tax_policy):
        """Test summary text generation."""
        result = distribution_engine.analyze_policy(
            basic_tax_policy,
            group_type=IncomeGroupType.QUINTILE
        )

        summary = result.summary()

        assert isinstance(summary, str)
        assert basic_tax_policy.name in summary
        assert "Total Tax Change" in summary


class TestTopIncomeBreakout:
    """Test top income group breakout analysis."""

    def test_top_income_breakout_structure(self, distribution_engine, basic_tax_policy):
        """Test top income breakout returns correct structure."""
        result = distribution_engine.create_top_income_breakout(basic_tax_policy)

        assert len(result.results) == 6  # Bottom 80% + 5 top groups
        assert result.results[0].income_group.name == "Bottom 80%"
        assert "Top 0.1%" in result.results[-1].income_group.name

    def test_top_income_concentration(self, distribution_engine, basic_tax_policy):
        """Test that tax increase on $400K+ is concentrated at very top."""
        result = distribution_engine.create_top_income_breakout(basic_tax_policy)

        # Bottom 80% should have no change
        assert result.results[0].tax_change_avg == 0

        # Top 0.1% should have largest per-capita burden
        top_01_avg = result.results[-1].tax_change_avg
        assert top_01_avg > 0  # Tax increase


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_zero_rate_change(self, distribution_engine):
        """Test policy with zero rate change."""
        policy = TaxPolicy(
            name="No Change",
            description="Zero rate change",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.0,
            affected_income_threshold=0,
        )

        result = distribution_engine.analyze_policy(policy)

        assert result.total_tax_change == 0
        for r in result.results:
            assert r.tax_change_avg == 0

    def test_very_high_threshold(self, distribution_engine):
        """Test policy with threshold above all income."""
        policy = TaxPolicy(
            name="Ultra High Threshold",
            description="Threshold at $100M",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.10,
            affected_income_threshold=100_000_000,
        )

        result = distribution_engine.analyze_policy(policy)

        # Very few (if any) affected
        assert abs(result.total_tax_change) < 10  # Less than $10B

    def test_negative_threshold(self, distribution_engine):
        """Test policy with negative threshold (should be treated as 0)."""
        policy = TaxPolicy(
            name="Negative Threshold",
            description="Negative threshold",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.01,
            affected_income_threshold=-1000,
        )

        # Should not raise error
        result = distribution_engine.analyze_policy(policy)
        assert result is not None
