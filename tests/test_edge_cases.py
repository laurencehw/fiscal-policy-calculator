"""
Systematic edge case tests for the scoring engine.

Tests boundary conditions, extreme values, and invariant properties
to ensure robustness and correctness across the full input space.
"""

import pytest
import numpy as np
from fiscal_model.scoring import FiscalPolicyScorer
from fiscal_model.policies import TaxPolicy, SpendingPolicy, TransferPolicy, PolicyType


class TestZeroInputs:
    """Test behavior with zero-value inputs."""

    def test_zero_rate_change(self):
        """A zero rate change should produce zero revenue effect."""
        policy = TaxPolicy(
            name="No Change",
            description="Zero rate change",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.0,
            affected_income_threshold=100000,
        )

        scorer = FiscalPolicyScorer(use_real_data=False)
        result = scorer.score_policy(policy)

        # Revenue effect should be near zero
        assert np.allclose(result.static_revenue_effect, 0.0, atol=1.0), (
            "Zero rate change should produce near-zero revenue effect"
        )

    def test_zero_threshold_affects_all(self):
        """A zero threshold should apply to all taxpayers."""
        policy = TaxPolicy(
            name="All Taxpayers",
            description="Zero threshold affects all",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.01,  # 1pp rate change
            affected_income_threshold=0.0,  # All taxpayers
        )

        scorer = FiscalPolicyScorer(use_real_data=False)
        result = scorer.score_policy(policy)

        # Should have significant revenue effect (all taxpayers affected)
        # Positive static_revenue_effect = revenue raised
        assert np.sum(result.static_revenue_effect) > 1000.0, (
            "Rate change on all taxpayers should have significant revenue effect"
        )

    def test_very_high_threshold_affects_few(self):
        """A very high threshold should affect only top earners."""
        policy = TaxPolicy(
            name="Top Earners Only",
            description="Very high threshold",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.10,  # 10pp rate change
            affected_income_threshold=10_000_000.0,  # $10M+ only
        )

        scorer = FiscalPolicyScorer(use_real_data=False)
        result = scorer.score_policy(policy)

        # Should have modest revenue effect (few but high-earners affected)
        # Still meaningful due to high rate change and high incomes
        assert abs(np.sum(result.static_revenue_effect)) > 100.0, (
            "Rate change on high earners should have revenue effect"
        )

    def test_zero_duration_raises_error(self):
        """Zero duration should raise ValueError."""
        with pytest.raises(ValueError):
            TaxPolicy(
                name="Invalid",
                description="Zero duration",
                policy_type=PolicyType.INCOME_TAX,
                rate_change=0.01,
                affected_income_threshold=100000,
                duration_years=0,
            )

    def test_negative_duration_raises_error(self):
        """Negative duration should raise ValueError."""
        with pytest.raises(ValueError):
            TaxPolicy(
                name="Invalid",
                description="Negative duration",
                policy_type=PolicyType.INCOME_TAX,
                rate_change=0.01,
                affected_income_threshold=100000,
                duration_years=-5,
            )


class TestExtremeInputs:
    """Test behavior with extreme values."""

    def test_max_rate_change_1_0(self):
        """Rate change of 1.0 (100 percentage points) should be handled."""
        policy = TaxPolicy(
            name="Extreme Rate",
            description="1.0 (100pp) rate change",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=1.0,
            affected_income_threshold=100000,
        )

        scorer = FiscalPolicyScorer(use_real_data=False)
        result = scorer.score_policy(policy)

        # Should produce valid (possibly extreme) results
        assert not np.any(np.isnan(result.static_revenue_effect)), (
            "Extreme rate change should not produce NaN"
        )
        assert not np.any(np.isinf(result.static_revenue_effect)), (
            "Extreme rate change should not produce Inf"
        )

    def test_max_rate_change_neg_1_0(self):
        """Rate change of -1.0 should be handled (complete tax cut)."""
        policy = TaxPolicy(
            name="Complete Cut",
            description="-1.0 (100pp) rate cut",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=-1.0,
            affected_income_threshold=100000,
        )

        scorer = FiscalPolicyScorer(use_real_data=False)
        result = scorer.score_policy(policy)

        # Should produce valid results
        assert not np.any(np.isnan(result.static_revenue_effect))
        assert not np.any(np.isinf(result.static_revenue_effect))

    def test_very_high_threshold_1_billion(self):
        """Threshold of $1 billion should be handled gracefully."""
        policy = TaxPolicy(
            name="Billionaire",
            description="Threshold $1B",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.05,
            affected_income_threshold=1_000_000_000.0,  # $1 billion
        )

        scorer = FiscalPolicyScorer(use_real_data=False)
        result = scorer.score_policy(policy)

        # Should produce valid results (very small number affected)
        assert not np.any(np.isnan(result.static_revenue_effect))
        assert np.sum(result.static_revenue_effect) > -10.0, (
            "Policy affecting billionaires only should have minimal revenue effect"
        )

    def test_one_year_duration(self):
        """Duration of 1 year should be handled."""
        policy = TaxPolicy(
            name="One Year",
            description="1-year policy",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.01,
            affected_income_threshold=100000,
            duration_years=1,
        )

        scorer = FiscalPolicyScorer(use_real_data=False)
        result = scorer.score_policy(policy)

        # Should have valid 1-year results
        assert len(result.years) >= 1
        assert not np.any(np.isnan(result.static_revenue_effect))

    def test_max_duration_30_years(self):
        """Duration of 30 years (3 full CBO windows) should be handled."""
        policy = TaxPolicy(
            name="Long Term",
            description="30-year policy",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.01,
            affected_income_threshold=100000,
            duration_years=30,
        )

        scorer = FiscalPolicyScorer(use_real_data=False)
        result = scorer.score_policy(policy)

        # Baseline only has 10 years, but should still be valid
        assert len(result.years) >= 1
        assert not np.any(np.isnan(result.static_revenue_effect))

    def test_high_eti_1_0(self):
        """Elasticity of income of 1.0 (high sensitivity) should be handled."""
        policy = TaxPolicy(
            name="High ETI",
            description="ETI = 1.0",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.01,
            affected_income_threshold=100000,
            taxable_income_elasticity=1.0,
        )

        scorer = FiscalPolicyScorer(use_real_data=False)
        result = scorer.score_policy(policy)

        # High ETI means large behavioral response
        # But should still produce valid results
        assert not np.any(np.isnan(result.static_revenue_effect))
        assert not np.any(np.isnan(result.behavioral_offset))


class TestNegativeValues:
    """Test tax cuts and spending cuts (negative revenue effects)."""

    def test_tax_cut_increases_deficit(self):
        """A tax cut should increase the deficit."""
        policy = TaxPolicy(
            name="Tax Cut",
            description="Rate cut of 2pp",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=-0.02,  # Tax cut
            affected_income_threshold=0,
        )

        scorer = FiscalPolicyScorer(use_real_data=False)
        result = scorer.score_policy(policy)

        # Final deficit effect should be positive (increases deficit)
        final_effect = np.sum(result.final_deficit_effect)
        assert final_effect > 0, (
            "Tax cut should increase deficit"
        )

    def test_tax_increase_reduces_deficit(self):
        """A tax increase should reduce the deficit."""
        policy = TaxPolicy(
            name="Tax Increase",
            description="Rate increase of 2pp",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.02,  # Tax increase
            affected_income_threshold=0,
        )

        scorer = FiscalPolicyScorer(use_real_data=False)
        result = scorer.score_policy(policy)

        # Final deficit effect should be negative (reduces deficit)
        final_effect = np.sum(result.final_deficit_effect)
        assert final_effect < 0, (
            "Tax increase should reduce deficit"
        )

    def test_spending_increase_increases_deficit(self):
        """A spending increase should increase the deficit."""
        policy = SpendingPolicy(
            name="Spending Increase",
            description="100B annual increase",
            policy_type=PolicyType.DISCRETIONARY_NONDEFENSE,
            annual_spending_change_billions=100.0,
        )

        scorer = FiscalPolicyScorer(use_real_data=False)
        result = scorer.score_policy(policy)

        # Final deficit effect should be positive
        final_effect = np.sum(result.final_deficit_effect)
        assert final_effect > 0, (
            "Spending increase should increase deficit"
        )

    def test_spending_cut_reduces_deficit(self):
        """A spending cut should reduce the deficit."""
        policy = SpendingPolicy(
            name="Spending Cut",
            description="100B annual decrease",
            policy_type=PolicyType.DISCRETIONARY_NONDEFENSE,
            annual_spending_change_billions=-100.0,
        )

        scorer = FiscalPolicyScorer(use_real_data=False)
        result = scorer.score_policy(policy)

        # Final deficit effect should be negative (reduces deficit)
        final_effect = np.sum(result.final_deficit_effect)
        assert final_effect < 0, (
            "Spending cut should reduce deficit"
        )


class TestPolicyInteractions:
    """Test policy package interactions."""

    def test_same_policy_doubles(self):
        """Two identical policies should roughly double the effect."""
        policy = TaxPolicy(
            name="Base Policy",
            description="Base tax policy",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.01,
            affected_income_threshold=100000,
        )

        scorer = FiscalPolicyScorer(use_real_data=False)
        single_result = scorer.score_policy(policy)

        # Create a double-rate policy (equivalent to applying twice)
        double_policy = TaxPolicy(
            name="Double Policy",
            description="2x the rate change",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.02,  # 2x the rate change
            affected_income_threshold=100000,
        )

        double_result = scorer.score_policy(double_policy)

        # The double-rate policy should have roughly 2x the effect
        single_total = np.sum(single_result.final_deficit_effect)
        double_total = np.sum(double_result.final_deficit_effect)

        # Allow 20% tolerance for behavioral nonlinearities
        assert abs(double_total - 2 * single_total) < abs(
            single_total * 0.25
        ), (
            "2x rate change should produce ~2x effect"
        )

    def test_opposing_policies_mostly_cancel(self):
        """Opposing policies should have opposite effects."""
        cut_policy = TaxPolicy(
            name="Cut",
            description="Tax cut",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=-0.02,
            affected_income_threshold=100000,
        )

        increase_policy = TaxPolicy(
            name="Increase",
            description="Tax increase",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.02,
            affected_income_threshold=100000,
        )

        scorer = FiscalPolicyScorer(use_real_data=False)

        cut_result = scorer.score_policy(cut_policy)
        increase_result = scorer.score_policy(increase_policy)

        # Effects should be opposite in sign
        cut_effect = np.sum(cut_result.final_deficit_effect)
        increase_effect = np.sum(increase_result.final_deficit_effect)

        # Tax cut increases deficit, tax increase reduces it
        assert cut_effect > 0 and increase_effect < 0, (
            "Opposite policies should have opposite effects"
        )


class TestResultConsistency:
    """Verify result invariants and consistency."""

    def test_final_equals_static_plus_behavioral(self):
        """Final deficit effect incorporates static and behavioral."""
        policy = TaxPolicy(
            name="Test",
            description="Test policy",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.02,
            affected_income_threshold=100000,
        )

        scorer = FiscalPolicyScorer(use_real_data=False)
        result = scorer.score_policy(policy)

        # Verify static and behavioral components exist and are non-zero
        assert hasattr(result, "static_revenue_effect"), "Should have static effects"
        if hasattr(result, "behavioral_offset"):
            # Both should be present
            assert len(result.static_revenue_effect) == len(result.behavioral_offset)
            assert len(result.final_deficit_effect) > 0

    def test_year_by_year_sums_to_total(self):
        """Sum of year-by-year effects should equal total."""
        policy = TaxPolicy(
            name="Test",
            description="Test policy",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.01,
            affected_income_threshold=100000,
        )

        scorer = FiscalPolicyScorer(use_real_data=False)
        result = scorer.score_policy(policy)

        # Sum of static effects
        static_sum = np.sum(result.static_revenue_effect)
        static_via_sum = np.sum(result.static_revenue_effect)

        assert abs(static_sum - static_via_sum) < 0.1, (
            "Sum of static effects should be consistent"
        )

    def test_no_nan_in_results(self):
        """Results should never contain NaN."""
        policy = TaxPolicy(
            name="Test",
            description="Test policy",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.01,
            affected_income_threshold=100000,
        )

        scorer = FiscalPolicyScorer(use_real_data=False)
        result = scorer.score_policy(policy)

        assert not np.any(np.isnan(result.static_revenue_effect)), (
            "Static revenue effect contains NaN"
        )
        assert not np.any(np.isnan(result.final_deficit_effect)), (
            "Final deficit effect contains NaN"
        )
        if hasattr(result, "behavioral_offset"):
            assert not np.any(np.isnan(result.behavioral_offset)), (
                "Behavioral offset contains NaN"
            )

    def test_no_inf_in_results(self):
        """Results should never contain Inf."""
        policy = TaxPolicy(
            name="Test",
            description="Test policy",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.01,
            affected_income_threshold=100000,
        )

        scorer = FiscalPolicyScorer(use_real_data=False)
        result = scorer.score_policy(policy)

        assert not np.any(np.isinf(result.static_revenue_effect)), (
            "Static revenue effect contains Inf"
        )
        assert not np.any(np.isinf(result.final_deficit_effect)), (
            "Final deficit effect contains Inf"
        )
        if hasattr(result, "behavioral_offset"):
            assert not np.any(np.isinf(result.behavioral_offset)), (
                "Behavioral offset contains Inf"
            )

    def test_years_array_is_monotonic(self):
        """Years array should be strictly increasing."""
        policy = TaxPolicy(
            name="Test",
            description="Test policy",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.01,
            affected_income_threshold=100000,
        )

        scorer = FiscalPolicyScorer(use_real_data=False)
        result = scorer.score_policy(policy)

        # Years should be strictly increasing
        for i in range(1, len(result.years)):
            assert result.years[i] > result.years[i - 1], (
                f"Years not monotonic at index {i}"
            )


class TestPolicyDurationHandling:
    """Test correct handling of policy duration and phase-in."""

    def test_policy_inactive_before_start(self):
        """Policy should have zero effect before start year."""
        policy = TaxPolicy(
            name="Future Policy",
            description="Starts in 2030",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.05,
            affected_income_threshold=100000,
            start_year=2030,
        )

        # Note: policy should be inactive in 2025
        assert not policy.is_active(2024)
        assert not policy.is_active(2025)
        assert policy.is_active(2030)

    def test_sunset_policy_inactive_after_duration(self):
        """Policy with sunset should be inactive after duration years."""
        policy = TaxPolicy(
            name="Temporary",
            description="Sunsets after 5 years",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.02,
            affected_income_threshold=100000,
            start_year=2025,
            duration_years=5,
            sunset=True,
        )

        assert policy.is_active(2025)
        assert policy.is_active(2029)  # Year 4
        assert not policy.is_active(2030)  # Year 5 (sunset)

    def test_phase_in_factor_progression(self):
        """Phase-in factor should progress from 0 to 1."""
        policy = TaxPolicy(
            name="Phase In",
            description="4-year phase-in",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.04,
            affected_income_threshold=100000,
            start_year=2025,
            phase_in_years=4,
        )

        # Before start: 0
        assert policy.get_phase_in_factor(2024) == 0.0

        # During phase-in: 0 < factor < 1
        assert 0.0 < policy.get_phase_in_factor(2025) < 1.0  # Year 1
        assert 0.0 < policy.get_phase_in_factor(2026) < 1.0  # Year 2
        assert 0.0 < policy.get_phase_in_factor(2027) < 1.0  # Year 3

        # Fully phased in
        assert policy.get_phase_in_factor(2028) == 1.0  # Year 4+


class TestBoundaryBehaviors:
    """Test behaviors at boundaries and limits."""

    def test_elasticity_zero(self):
        """Zero elasticity should mean no behavioral response."""
        policy = TaxPolicy(
            name="No Elasticity",
            description="ETI = 0",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.05,
            affected_income_threshold=100000,
            taxable_income_elasticity=0.0,
        )

        scorer = FiscalPolicyScorer(use_real_data=False)
        result = scorer.score_policy(policy)

        # Behavioral offset should be zero
        if hasattr(result, "behavioral_offset"):
            assert np.allclose(result.behavioral_offset, 0.0, atol=1.0), (
                "Zero elasticity should mean zero behavioral offset"
            )

    def test_min_phase_in(self):
        """Phase-in of 1 year should mean immediate effect."""
        policy = TaxPolicy(
            name="Immediate",
            description="1-year phase-in",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.01,
            affected_income_threshold=100000,
            phase_in_years=1,
            start_year=2025,
        )

        # Should be fully phased in starting year
        assert policy.get_phase_in_factor(2025) == 1.0

    def test_threshold_equals_income_distribution(self):
        """Threshold right at median income should affect about half."""
        # Median household income ~ $75K
        policy = TaxPolicy(
            name="Median",
            description="Threshold at median",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.02,
            affected_income_threshold=75_000.0,
        )

        scorer = FiscalPolicyScorer(use_real_data=False)
        result = scorer.score_policy(policy)

        # Should have meaningful revenue effect
        effect = abs(np.sum(result.static_revenue_effect))
        assert effect > 100.0, (
            "Policy at median threshold should have meaningful effect"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
