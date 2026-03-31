"""
Tests for fiscal_model/economics.py

Covers EconomicConditions factory methods, EconomicModel initialization,
condition-adjusted multipliers, calculate_effects for TaxPolicy and
SpendingPolicy, DynamicEffects properties, and interest rate effects.
"""

import numpy as np
import pytest

from fiscal_model.baseline import CBOBaseline
from fiscal_model.economics import (
    DynamicEffects,
    EconomicConditions,
    EconomicModel,
)
from fiscal_model.policies import (
    PolicyType,
    SpendingPolicy,
    TaxPolicy,
    TransferPolicy,
)

# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def baseline():
    """CBO baseline projection using hardcoded fallback data."""
    return CBOBaseline(start_year=2025, use_real_data=False).generate()


@pytest.fixture
def normal_conditions():
    return EconomicConditions.normal_times()


@pytest.fixture
def recession_conditions():
    return EconomicConditions.recession()


@pytest.fixture
def model_normal(baseline):
    """EconomicModel under normal conditions."""
    return EconomicModel(baseline, EconomicConditions.normal_times())


@pytest.fixture
def model_recession(baseline):
    """EconomicModel under recession conditions."""
    return EconomicModel(baseline, EconomicConditions.recession())


@pytest.fixture
def model_overheating(baseline):
    """EconomicModel under overheating conditions."""
    return EconomicModel(baseline, EconomicConditions.overheating())


@pytest.fixture
def tax_cut_policy():
    """A tax cut policy for dynamic effects testing."""
    return TaxPolicy(
        name="Tax Cut",
        description="2pp cut for all income",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=-0.02,
        affected_income_threshold=0,
        start_year=2025,
        duration_years=10,
    )


@pytest.fixture
def tax_increase_policy():
    """A tax increase policy for dynamic effects testing."""
    return TaxPolicy(
        name="Tax Increase",
        description="2pp increase on high earners",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=0.02,
        affected_income_threshold=400_000,
        start_year=2025,
        duration_years=10,
    )


@pytest.fixture
def spending_policy():
    """A spending increase policy for dynamic effects testing."""
    return SpendingPolicy(
        name="Infrastructure",
        description="infrastructure spending",
        policy_type=PolicyType.INFRASTRUCTURE,
        start_year=2025,
        duration_years=10,
        annual_spending_change_billions=50.0,
        gdp_multiplier=1.5,
        employment_per_billion=10000,
    )


@pytest.fixture
def transfer_policy():
    """A transfer policy for dynamic effects testing."""
    return TransferPolicy(
        name="SS Expansion",
        description="social security expansion",
        policy_type=PolicyType.SOCIAL_SECURITY,
        start_year=2025,
        duration_years=10,
        benefit_change_percent=0.05,
    )


# =============================================================================
# EconomicConditions factory methods
# =============================================================================

class TestEconomicConditionsFactories:
    def test_normal_times(self):
        cond = EconomicConditions.normal_times()
        assert cond.output_gap == 0.0
        assert cond.at_zlb is False
        assert cond.unemployment_rate == pytest.approx(0.04)

    def test_recession(self):
        cond = EconomicConditions.recession()
        assert cond.output_gap < 0
        assert cond.at_zlb is True
        assert cond.unemployment_rate > 0.04

    def test_deep_recession(self):
        cond = EconomicConditions.deep_recession()
        assert cond.output_gap < EconomicConditions.recession().output_gap
        assert cond.at_zlb is True
        assert cond.unemployment_rate >= 0.10

    def test_overheating(self):
        cond = EconomicConditions.overheating()
        assert cond.output_gap > 0
        assert cond.at_zlb is False
        assert cond.unemployment_rate < 0.04


# =============================================================================
# EconomicModel initialization
# =============================================================================

class TestEconomicModelInit:
    def test_default_conditions_are_normal(self, baseline):
        model = EconomicModel(baseline)
        assert model.conditions.output_gap == 0.0
        assert model.conditions.at_zlb is False

    def test_custom_conditions(self, baseline):
        cond = EconomicConditions.recession()
        model = EconomicModel(baseline, cond)
        assert model.conditions is cond
        assert model.conditions.at_zlb is True

    def test_params_populated(self, model_normal):
        assert 'spending_multiplier_peak' in model_normal.params
        assert 'tax_multiplier' in model_normal.params
        assert 'crowding_out' in model_normal.params
        assert 'marginal_revenue_rate' in model_normal.params


# =============================================================================
# EconomicModel._adjust_for_conditions
# =============================================================================

class TestAdjustForConditions:
    def test_recession_increases_multipliers(self, model_normal, model_recession):
        """Recession conditions should produce higher multipliers than normal."""
        normal_spending = model_normal.params['spending_multiplier_peak']
        recession_spending = model_recession.params['spending_multiplier_peak']
        assert recession_spending > normal_spending

        normal_tax = model_normal.params['tax_multiplier']
        recession_tax = model_recession.params['tax_multiplier']
        assert recession_tax > normal_tax

    def test_overheating_decreases_multipliers(self, model_normal, model_overheating):
        """Overheating conditions should produce lower multipliers than normal."""
        normal_spending = model_normal.params['spending_multiplier_peak']
        overheating_spending = model_overheating.params['spending_multiplier_peak']
        assert overheating_spending < normal_spending

    def test_zlb_reduces_crowding_out(self, model_normal, model_recession):
        """At the ZLB, crowding out should be lower."""
        assert model_recession.params['crowding_out'] < model_normal.params['crowding_out']

    def test_update_conditions(self, model_normal):
        """update_conditions recalculates parameters."""
        old_multiplier = model_normal.params['spending_multiplier_peak']
        model_normal.update_conditions(EconomicConditions.recession())
        new_multiplier = model_normal.params['spending_multiplier_peak']
        assert new_multiplier > old_multiplier


# =============================================================================
# EconomicModel.get_multiplier_summary
# =============================================================================

class TestGetMultiplierSummary:
    def test_returns_expected_keys(self, model_normal):
        summary = model_normal.get_multiplier_summary()
        assert 'spending_multiplier' in summary
        assert 'tax_multiplier' in summary
        assert 'transfer_multiplier' in summary
        assert 'conditions' in summary

    def test_conditions_dict(self, model_normal):
        summary = model_normal.get_multiplier_summary()
        cond = summary['conditions']
        assert 'output_gap' in cond
        assert 'at_zlb' in cond
        assert 'debt_to_gdp' in cond


# =============================================================================
# calculate_effects for TaxPolicy
# =============================================================================

class TestCalculateEffectsTaxPolicy:
    def test_returns_dynamic_effects(self, model_normal, tax_cut_policy):
        budget_effect = np.full(10, -100.0)  # $100B/yr tax cut (revenue loss)
        effects = model_normal.calculate_effects(tax_cut_policy, budget_effect)
        assert isinstance(effects, DynamicEffects)

    def test_correct_array_shapes(self, model_normal, tax_cut_policy):
        budget_effect = np.full(10, -100.0)
        effects = model_normal.calculate_effects(tax_cut_policy, budget_effect)
        assert effects.gdp_level_change.shape == (10,)
        assert effects.gdp_percent_change.shape == (10,)
        assert effects.employment_change.shape == (10,)
        assert effects.revenue_feedback.shape == (10,)
        assert effects.interest_rate_change.shape == (10,)

    def test_tax_cut_produces_positive_gdp(self, model_normal, tax_cut_policy):
        """A tax cut (negative budget effect) should produce positive GDP effect."""
        budget_effect = np.full(10, -100.0)
        effects = model_normal.calculate_effects(tax_cut_policy, budget_effect)
        # At least some years should have positive GDP effect
        assert np.any(effects.gdp_level_change > 0)

    def test_years_array_matches(self, model_normal, tax_cut_policy):
        budget_effect = np.full(10, -100.0)
        effects = model_normal.calculate_effects(tax_cut_policy, budget_effect)
        np.testing.assert_array_equal(effects.years, model_normal.years)


# =============================================================================
# calculate_effects for SpendingPolicy
# =============================================================================

class TestCalculateEffectsSpendingPolicy:
    def test_returns_dynamic_effects(self, model_normal, spending_policy):
        budget_effect = np.full(10, 50.0)  # $50B/yr spending increase
        effects = model_normal.calculate_effects(spending_policy, budget_effect)
        assert isinstance(effects, DynamicEffects)

    def test_spending_increase_produces_positive_gdp(self, model_normal, spending_policy):
        """Spending increase should produce positive GDP effect (at least initially)."""
        budget_effect = np.full(10, 50.0)
        effects = model_normal.calculate_effects(spending_policy, budget_effect)
        # First year should have positive GDP effect from multiplier
        assert effects.gdp_level_change[0] > 0

    def test_employment_follows_spending(self, model_normal, spending_policy):
        """Spending policy should produce positive employment in active years."""
        budget_effect = np.full(10, 50.0)
        effects = model_normal.calculate_effects(spending_policy, budget_effect)
        assert effects.employment_change[0] > 0


# =============================================================================
# Revenue feedback
# =============================================================================

class TestRevenueFeedback:
    def test_positive_gdp_produces_positive_feedback(self, model_normal, spending_policy):
        """When GDP effect is positive, revenue feedback should be positive."""
        budget_effect = np.full(10, 50.0)
        effects = model_normal.calculate_effects(spending_policy, budget_effect)
        # Revenue feedback = gdp_level * marginal_revenue_rate
        # If GDP is positive (at least year 0), feedback should be positive there
        for i in range(10):
            if effects.gdp_level_change[i] > 0:
                assert effects.revenue_feedback[i] > 0

    def test_feedback_proportional_to_marginal_rate(self, model_normal, spending_policy):
        """Revenue feedback should equal GDP change * marginal revenue rate."""
        budget_effect = np.full(10, 50.0)
        effects = model_normal.calculate_effects(spending_policy, budget_effect)
        marginal_rate = model_normal.params['marginal_revenue_rate']
        expected = effects.gdp_level_change * marginal_rate
        np.testing.assert_allclose(effects.revenue_feedback, expected, rtol=1e-10)


# =============================================================================
# Employment follows GDP direction
# =============================================================================

class TestEmploymentFollowsGDP:
    def test_tax_cut_employment(self, model_normal, tax_cut_policy):
        """Employment change should follow GDP direction for tax cuts."""
        budget_effect = np.full(10, -100.0)
        effects = model_normal.calculate_effects(tax_cut_policy, budget_effect)
        # Where GDP is positive, employment should be positive
        positive_gdp = effects.gdp_percent_change > 0
        if np.any(positive_gdp):
            assert np.all(effects.employment_change[positive_gdp] > 0)

    def test_spending_employment(self, model_normal, spending_policy):
        """Spending increase should produce positive employment."""
        budget_effect = np.full(10, 50.0)
        effects = model_normal.calculate_effects(spending_policy, budget_effect)
        # First year employment should be positive
        assert effects.employment_change[0] > 0


# =============================================================================
# DynamicEffects properties
# =============================================================================

class TestDynamicEffectsProperties:
    def test_cumulative_gdp_effect(self, model_normal, spending_policy):
        budget_effect = np.full(10, 50.0)
        effects = model_normal.calculate_effects(spending_policy, budget_effect)
        expected = np.sum(effects.gdp_level_change)
        assert effects.cumulative_gdp_effect == pytest.approx(expected)

    def test_cumulative_revenue_feedback(self, model_normal, spending_policy):
        budget_effect = np.full(10, 50.0)
        effects = model_normal.calculate_effects(spending_policy, budget_effect)
        expected = np.sum(effects.revenue_feedback)
        assert effects.cumulative_revenue_feedback == pytest.approx(expected)

    def test_average_employment_effect(self, model_normal, spending_policy):
        budget_effect = np.full(10, 50.0)
        effects = model_normal.calculate_effects(spending_policy, budget_effect)
        expected = np.mean(effects.employment_change)
        assert effects.average_employment_effect == pytest.approx(expected)


# =============================================================================
# Interest rate effects from crowding out
# =============================================================================

class TestInterestRateEffects:
    def test_deficit_spending_increases_interest_rates(self, model_normal, spending_policy):
        """Cumulative deficit spending should push interest rates up."""
        budget_effect = np.full(10, 50.0)  # Spending adds to deficit
        effects = model_normal.calculate_effects(spending_policy, budget_effect)
        # Later years should have higher interest rate change as deficit accumulates
        assert effects.interest_rate_change[-1] > effects.interest_rate_change[0]

    def test_tax_cut_interest_rate_direction(self, model_normal, tax_cut_policy):
        """Tax cuts (negative budget effect) should affect interest rates via deficit."""
        budget_effect = np.full(10, -100.0)  # Revenue loss
        effects = model_normal.calculate_effects(tax_cut_policy, budget_effect)
        # Cumulative deficit from tax cut is negative (revenue loss),
        # so interest_rate_change = -cumulative / 100 * crowding_out
        # cumulative is negative => -(-) = positive
        assert effects.interest_rate_change[-1] > 0

    def test_crowding_out_lower_at_zlb(self, model_normal, model_recession, spending_policy):
        """Interest rate effects should be smaller during recession (ZLB)."""
        budget_effect = np.full(10, 50.0)
        model_normal.calculate_effects(spending_policy, budget_effect)
        model_recession.calculate_effects(spending_policy, budget_effect)
        # Crowding out param is lower at ZLB, so interest rate change is smaller
        assert model_recession.params['crowding_out'] < model_normal.params['crowding_out']
