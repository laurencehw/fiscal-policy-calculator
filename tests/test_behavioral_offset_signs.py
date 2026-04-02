"""
Integration tests for behavioral offset sign conventions.

These tests verify that the scoring engine correctly handles behavioral
responses for both tax increases AND tax cuts. Specifically:

- Tax increases: behavioral offset should INCREASE deficit relative to static
  (people shelter income → less revenue than static predicts)
- Tax cuts: behavioral offset should DECREASE deficit relative to static
  (people earn more → less revenue loss than static predicts)

These invariants should hold regardless of policy parameters.
"""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from fiscal_model.corporate import CorporateTaxPolicy
from fiscal_model.policies import PolicyType, TaxPolicy
from fiscal_model.scoring import FiscalPolicyScorer


@pytest.fixture
def scorer():
    return FiscalPolicyScorer(use_real_data=False)


# =============================================================================
# TAX POLICY BEHAVIORAL OFFSET SIGN INVARIANTS
# =============================================================================

class TestTaxCutBehavioralOffset:
    """Tax cuts should cost LESS after behavioral response (partial Laffer effect)."""

    def test_broad_tax_cut_behavioral_reduces_cost(self, scorer):
        """A broad income tax cut should cost less after behavioral offset."""
        policy = TaxPolicy(
            name="Broad Tax Cut",
            description="1pp across-the-board cut",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=-0.01,
            affected_income_threshold=0,
        )
        result = scorer.score_policy(policy)

        static_cost = np.sum(result.static_deficit_effect)
        final_cost = np.sum(result.final_deficit_effect)

        assert static_cost > 0, "Tax cut should increase static deficit"
        assert final_cost < static_cost, (
            f"Behavioral offset should reduce tax cut cost: "
            f"static={static_cost:.1f}B, final={final_cost:.1f}B"
        )

    def test_high_earner_tax_cut_behavioral_reduces_cost(self, scorer):
        """A high-earner tax cut should cost less after behavioral response."""
        policy = TaxPolicy(
            name="High Earner Cut",
            description="2pp cut above $400K",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=-0.02,
            affected_income_threshold=400_000,
            affected_taxpayers_millions=1.8,
            avg_taxable_income_in_bracket=1_200_000,
        )
        result = scorer.score_policy(policy)

        static_cost = np.sum(result.static_deficit_effect)
        final_cost = np.sum(result.final_deficit_effect)

        assert static_cost > 0, "Tax cut should increase static deficit"
        assert final_cost < static_cost, (
            f"Behavioral offset should reduce tax cut cost: "
            f"static={static_cost:.1f}B, final={final_cost:.1f}B"
        )

    def test_behavioral_offset_is_negative_for_tax_cut(self, scorer):
        """The behavioral offset array should be negative for a tax cut."""
        policy = TaxPolicy(
            name="Tax Cut",
            description="Cut for testing",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=-0.01,
            affected_income_threshold=0,
        )
        result = scorer.score_policy(policy)

        # Static revenue is negative (revenue loss) for a tax cut
        assert np.all(result.static_revenue_effect <= 0), (
            "Static revenue should be negative for a tax cut"
        )
        # Behavioral offset should be negative (recovers revenue)
        assert np.all(result.behavioral_offset <= 0), (
            f"Behavioral offset should be negative for a tax cut, "
            f"got: {result.behavioral_offset}"
        )


class TestTaxIncreaseBehavioralOffset:
    """Tax increases should raise LESS revenue after behavioral response."""

    def test_tax_increase_behavioral_reduces_revenue(self, scorer):
        """A tax increase should raise less revenue after behavioral offset."""
        policy = TaxPolicy(
            name="Tax Increase",
            description="2.6pp on high earners",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.026,
            affected_income_threshold=400_000,
            affected_taxpayers_millions=1.8,
            avg_taxable_income_in_bracket=1_200_000,
        )
        result = scorer.score_policy(policy)

        static_cost = np.sum(result.static_deficit_effect)
        final_cost = np.sum(result.final_deficit_effect)

        assert static_cost < 0, "Tax increase should reduce static deficit"
        assert final_cost > static_cost, (
            f"Behavioral offset should reduce revenue from tax increase: "
            f"static={static_cost:.1f}B, final={final_cost:.1f}B"
        )

    def test_behavioral_offset_is_positive_for_tax_increase(self, scorer):
        """The behavioral offset array should be positive for a tax increase."""
        policy = TaxPolicy(
            name="Tax Increase",
            description="Increase for testing",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.02,
            affected_income_threshold=200_000,
            affected_taxpayers_millions=5.0,
            avg_taxable_income_in_bracket=400_000,
        )
        result = scorer.score_policy(policy)

        assert np.all(result.static_revenue_effect >= 0), (
            "Static revenue should be positive for a tax increase"
        )
        assert np.all(result.behavioral_offset >= 0), (
            f"Behavioral offset should be positive for a tax increase, "
            f"got: {result.behavioral_offset}"
        )


class TestCorporateTaxBehavioralOffset:
    """Corporate tax behavioral offsets should have correct sign."""

    def test_corporate_rate_increase_offset_positive(self, scorer):
        """Corporate rate increase should have positive behavioral offset."""
        policy = CorporateTaxPolicy(
            name="Corp Rate Increase",
            description="21% → 28%",
            policy_type=PolicyType.CORPORATE_TAX,
            rate_change=0.07,
        )
        result = scorer.score_policy(policy)

        # Revenue increases → behavioral offset should be positive (revenue lost)
        assert np.all(result.behavioral_offset >= 0), (
            f"Corporate rate increase offset should be positive (revenue lost), "
            f"got: {result.behavioral_offset}"
        )

    def test_corporate_rate_cut_offset_negative(self, scorer):
        """Corporate rate cut should have negative behavioral offset."""
        policy = CorporateTaxPolicy(
            name="Corp Rate Cut",
            description="21% → 15%",
            policy_type=PolicyType.CORPORATE_TAX,
            rate_change=-0.06,
        )
        result = scorer.score_policy(policy)

        # Revenue decreases → behavioral offset should be negative (revenue recovered)
        assert np.all(result.behavioral_offset <= 0), (
            f"Corporate rate cut offset should be negative (revenue recovered), "
            f"got: {result.behavioral_offset}"
        )


class TestSymmetryInvariant:
    """Behavioral offset magnitude should be proportional to static effect."""

    def test_offset_bounded_by_static(self):
        """Behavioral offset should not exceed the static effect."""
        policy = TaxPolicy(
            name="Test",
            description="",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.05,
            taxable_income_elasticity=0.25,
        )
        static_effect = 100.0  # $100B revenue gain
        offset = policy.estimate_behavioral_offset(static_effect)

        # Offset should be less than 100% of static effect
        assert abs(offset) < abs(static_effect), (
            f"Behavioral offset ({offset}) should be smaller than "
            f"static effect ({static_effect})"
        )

    @pytest.mark.parametrize("rate_change", [-0.05, -0.02, -0.01, 0.01, 0.02, 0.05])
    def test_offset_sign_matches_static(self, rate_change):
        """Behavioral offset sign should match static_effect sign."""
        policy = TaxPolicy(
            name="Test",
            description="",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=rate_change,
            taxable_income_elasticity=0.25,
        )
        static_effect = rate_change * 1000  # Proportional to rate change
        offset = policy.estimate_behavioral_offset(static_effect)

        if static_effect > 0:
            assert offset > 0, "Offset should be positive for positive static effect"
        elif static_effect < 0:
            assert offset < 0, "Offset should be negative for negative static effect"


# =============================================================================
# PROPERTY-BASED INVARIANT TESTS
# =============================================================================

class TestPropertyInvariants:
    """Property-based tests: invariants that must hold for ALL policy parameters."""

    @pytest.mark.parametrize("eti", [0.1, 0.25, 0.4, 0.5])
    @pytest.mark.parametrize("static_effect", [-500, -100, -10, 10, 100, 500])
    def test_offset_sign_always_matches_static(self, eti, static_effect):
        """INVARIANT: offset sign must equal static_effect sign for any ETI."""
        policy = TaxPolicy(
            name="T", description="", policy_type=PolicyType.INCOME_TAX,
            taxable_income_elasticity=eti,
        )
        offset = policy.estimate_behavioral_offset(static_effect)
        if static_effect > 0:
            assert offset > 0
        elif static_effect < 0:
            assert offset < 0
        else:
            assert offset == 0

    @pytest.mark.parametrize("eti", [0.1, 0.25, 0.4, 0.5])
    @pytest.mark.parametrize("static_effect", [-500, -100, 100, 500])
    def test_offset_magnitude_less_than_static(self, eti, static_effect):
        """INVARIANT: |offset| < |static_effect| for ETI in [0, 1]."""
        policy = TaxPolicy(
            name="T", description="", policy_type=PolicyType.INCOME_TAX,
            taxable_income_elasticity=eti,
        )
        offset = policy.estimate_behavioral_offset(static_effect)
        assert abs(offset) < abs(static_effect), (
            f"ETI={eti}: offset {offset} exceeds static {static_effect}"
        )

    @pytest.mark.parametrize("eti", [0.1, 0.25, 0.4])
    def test_higher_eti_means_larger_offset(self, eti):
        """INVARIANT: higher ETI → larger offset magnitude."""
        low_eti_policy = TaxPolicy(
            name="T", description="", policy_type=PolicyType.INCOME_TAX,
            taxable_income_elasticity=eti,
        )
        high_eti_policy = TaxPolicy(
            name="T", description="", policy_type=PolicyType.INCOME_TAX,
            taxable_income_elasticity=eti + 0.1,
        )
        static = 100.0
        low_offset = low_eti_policy.estimate_behavioral_offset(static)
        high_offset = high_eti_policy.estimate_behavioral_offset(static)
        assert abs(high_offset) > abs(low_offset)

    @pytest.mark.parametrize("rate_change", [-0.05, -0.01, 0.01, 0.05])
    def test_full_pipeline_behavioral_reduces_static_magnitude(self, scorer, rate_change):
        """INVARIANT: behavioral response always moves final toward zero vs static.

        For tax increases: final deficit > static deficit (less negative, closer to 0)
        For tax cuts: final deficit < static deficit (less positive, closer to 0)
        """
        policy = TaxPolicy(
            name="Test", description="", policy_type=PolicyType.INCOME_TAX,
            rate_change=rate_change, affected_income_threshold=0,
        )
        result = scorer.score_policy(policy)
        static_total = abs(np.sum(result.static_deficit_effect))
        final_total = abs(np.sum(result.final_deficit_effect))
        assert final_total < static_total, (
            f"rate_change={rate_change}: final ({final_total:.1f}) should be "
            f"closer to zero than static ({static_total:.1f})"
        )


class TestScoringResultBoundsChecking:
    """Test that get_year_effect raises helpful errors for invalid years."""

    def test_year_before_window_raises(self, scorer):
        policy = TaxPolicy(
            name="Test", description="", policy_type=PolicyType.INCOME_TAX,
            rate_change=0.01, affected_income_threshold=0,
        )
        result = scorer.score_policy(policy)

        with pytest.raises(ValueError, match="outside the budget window"):
            result.get_year_effect(2000)

    def test_year_after_window_raises(self, scorer):
        policy = TaxPolicy(
            name="Test", description="", policy_type=PolicyType.INCOME_TAX,
            rate_change=0.01, affected_income_threshold=0,
        )
        result = scorer.score_policy(policy)

        with pytest.raises(ValueError, match="outside the budget window"):
            result.get_year_effect(2099)

    def test_valid_year_succeeds(self, scorer):
        policy = TaxPolicy(
            name="Test", description="", policy_type=PolicyType.INCOME_TAX,
            rate_change=0.01, affected_income_threshold=0,
        )
        result = scorer.score_policy(policy)

        # First year of window should work
        effect = result.get_year_effect(result.years[0])
        assert 'year' in effect
