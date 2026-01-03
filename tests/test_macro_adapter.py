"""
Tests for macro model adapter module.

Tests cover:
- SimpleMultiplierAdapter
- MacroScenario creation
- MacroResult properties
- Policy to scenario conversion
"""

import pytest
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fiscal_model.models import (
    MacroScenario,
    MacroResult,
    SimpleMultiplierAdapter,
    FRBUSAdapter,
    FRBUSAdapterLite,
    FiscalClosureType,
    MonetaryPolicyRule,
    policy_to_scenario,
)
from fiscal_model.policies import TaxPolicy, PolicyType


class TestMacroScenario:
    """Test MacroScenario data class."""

    def test_default_scenario(self):
        """Test scenario with defaults."""
        scenario = MacroScenario(
            name="Test",
            description="Test scenario",
        )

        assert scenario.start_year == 2025
        assert scenario.horizon_years == 10
        assert len(scenario.receipts_change) == 10
        assert len(scenario.outlays_change) == 10
        assert np.all(scenario.receipts_change == 0)
        assert np.all(scenario.outlays_change == 0)

    def test_custom_scenario(self):
        """Test scenario with custom values."""
        receipts = np.array([-100.0] * 10)
        outlays = np.array([50.0] * 10)

        scenario = MacroScenario(
            name="Custom",
            description="Custom scenario",
            start_year=2026,
            horizon_years=10,
            receipts_change=receipts,
            outlays_change=outlays,
            fiscal_closure=FiscalClosureType.SPENDING_CUTS,
            monetary_rule=MonetaryPolicyRule.ZERO_LOWER_BOUND,
        )

        assert scenario.start_year == 2026
        assert np.all(scenario.receipts_change == -100.0)
        assert np.all(scenario.outlays_change == 50.0)
        assert scenario.fiscal_closure == FiscalClosureType.SPENDING_CUTS
        assert scenario.monetary_rule == MonetaryPolicyRule.ZERO_LOWER_BOUND

    def test_fiscal_closure_types(self):
        """Test all fiscal closure types."""
        for closure in FiscalClosureType:
            scenario = MacroScenario(
                name=f"Test {closure}",
                description="Test",
                fiscal_closure=closure,
            )
            assert scenario.fiscal_closure == closure

    def test_monetary_policy_rules(self):
        """Test all monetary policy rules."""
        for rule in MonetaryPolicyRule:
            scenario = MacroScenario(
                name=f"Test {rule}",
                description="Test",
                monetary_rule=rule,
            )
            assert scenario.monetary_rule == rule


class TestSimpleMultiplierAdapter:
    """Test SimpleMultiplierAdapter."""

    @pytest.fixture
    def adapter(self):
        """Create adapter with default parameters."""
        return SimpleMultiplierAdapter()

    @pytest.fixture
    def custom_adapter(self):
        """Create adapter with custom parameters."""
        return SimpleMultiplierAdapter(
            spending_multiplier=1.5,
            tax_multiplier=-0.7,
            marginal_tax_rate=0.30,
            multiplier_decay=0.8,
        )

    def test_adapter_properties(self, adapter):
        """Test adapter name and description."""
        assert adapter.name == "Simple Multiplier"
        assert "Keynesian" in adapter.description or "multiplier" in adapter.description.lower()

    def test_tax_cut_scenario(self, adapter, sample_macro_scenario):
        """Test tax cut produces GDP increase."""
        result = adapter.run(sample_macro_scenario)

        assert isinstance(result, MacroResult)
        assert result.scenario_name == sample_macro_scenario.name
        assert result.model_name == adapter.name

        # Tax cut should increase GDP
        assert np.all(result.gdp_level_pct > 0)

        # Employment should increase
        assert np.all(result.employment_change_millions > 0)

        # Revenue feedback should be positive
        assert result.cumulative_revenue_feedback > 0

    def test_spending_scenario(self, adapter, spending_scenario):
        """Test spending increase produces GDP increase."""
        result = adapter.run(spending_scenario)

        # Spending increase should increase GDP
        assert np.all(result.gdp_level_pct > 0)

    def test_gdp_effect_accumulates(self, adapter, sample_macro_scenario):
        """Test that GDP effect accumulates over time."""
        result = adapter.run(sample_macro_scenario)

        # GDP level should generally increase (with decay)
        # First year effect
        assert result.gdp_level_pct[0] > 0

        # Later years should show accumulated effect
        assert result.gdp_level_pct[-1] > result.gdp_level_pct[0]

    def test_multiplier_decay(self, adapter, sample_macro_scenario):
        """Test that multiplier effect decays over time."""
        result = adapter.run(sample_macro_scenario)

        # Growth rate should decrease as decay kicks in
        growth_rates = result.gdp_growth_ppts

        # Later growth rates should be smaller (effect decaying)
        assert growth_rates[-1] < growth_rates[0]

    def test_custom_multipliers(self, custom_adapter, sample_macro_scenario):
        """Test that custom multipliers affect results."""
        default_adapter = SimpleMultiplierAdapter()

        default_result = default_adapter.run(sample_macro_scenario)
        custom_result = custom_adapter.run(sample_macro_scenario)

        # Custom has higher tax multiplier, should have larger effect
        assert custom_result.gdp_level_pct[0] != default_result.gdp_level_pct[0]

    def test_interest_rate_effect(self, adapter, sample_macro_scenario):
        """Test interest rate response to deficit."""
        result = adapter.run(sample_macro_scenario)

        # Tax cut increases deficit, should raise rates
        # (But effect depends on crowding out assumptions)
        assert result.long_rate_ppts is not None
        assert len(result.long_rate_ppts) == 10

    def test_result_dataframe(self, adapter, sample_macro_scenario):
        """Test MacroResult to_dataframe method."""
        result = adapter.run(sample_macro_scenario)

        df = result.to_dataframe()

        assert len(df) == 10
        assert "Year" in df.columns
        assert "GDP Level (%)" in df.columns
        assert "Employment (M)" in df.columns
        assert "Revenue Feedback ($B)" in df.columns

    def test_cumulative_properties(self, adapter, sample_macro_scenario):
        """Test cumulative effect properties."""
        result = adapter.run(sample_macro_scenario)

        # Cumulative GDP effect
        manual_sum = float(np.sum(result.gdp_level_pct))
        assert abs(result.cumulative_gdp_effect - manual_sum) < 0.001

        # Cumulative revenue feedback
        feedback_sum = float(np.sum(result.revenue_feedback_billions))
        assert abs(result.cumulative_revenue_feedback - feedback_sum) < 0.001

    def test_baseline_projection(self, adapter):
        """Test baseline economic projection."""
        baseline = adapter.get_baseline()

        assert len(baseline) == 10
        assert "Year" in baseline.columns
        assert "GDP ($T)" in baseline.columns
        assert baseline["GDP ($T)"].iloc[0] > 0

    def test_zero_scenario(self, adapter):
        """Test scenario with no fiscal change."""
        scenario = MacroScenario(
            name="No Change",
            description="Zero fiscal impulse",
        )

        result = adapter.run(scenario)

        # No fiscal change = no GDP effect
        assert np.allclose(result.gdp_level_pct, 0, atol=0.001)
        assert np.allclose(result.employment_change_millions, 0, atol=0.001)


class TestFRBUSAdapter:
    """Test FRBUSAdapter."""

    def test_adapter_properties(self):
        """Test FRBUS adapter properties."""
        adapter = FRBUSAdapter()

        assert adapter.name == "FRB/US"
        assert "Federal Reserve" in adapter.description

    def test_run_with_nonexistent_files(self):
        """Test that run raises error with nonexistent model files."""
        adapter = FRBUSAdapter(
            model_path="nonexistent.xml",
            data_path="nonexistent.txt",
        )

        scenario = MacroScenario(name="Test", description="Test")

        with pytest.raises((ImportError, FileNotFoundError)):
            adapter.run(scenario)

    def test_default_paths(self):
        """Test that default paths are set correctly."""
        adapter = FRBUSAdapter()

        assert "Economy_Forecasts" in adapter.model_path
        assert "model.xml" in adapter.model_path
        assert "LONGBASE.TXT" in adapter.data_path


class TestFRBUSAdapterLite:
    """Test FRBUSAdapterLite (FRB/US-calibrated reduced-form model)."""

    @pytest.fixture
    def adapter(self):
        """Create adapter with default parameters."""
        return FRBUSAdapterLite()

    @pytest.fixture
    def custom_adapter(self):
        """Create adapter with custom parameters."""
        return FRBUSAdapterLite(
            spending_multiplier=1.6,
            tax_multiplier=-0.8,
            multiplier_decay=0.70,
            crowding_out=0.20,
        )

    def test_adapter_properties(self, adapter):
        """Test adapter name and description."""
        assert adapter.name == "FRB/US-Lite"
        assert "FRB/US" in adapter.description
        assert "pyfrbus" in adapter.description.lower()

    def test_tax_cut_scenario(self, adapter, sample_macro_scenario):
        """Test tax cut produces GDP increase with FRB/US-calibrated multipliers."""
        result = adapter.run(sample_macro_scenario)

        assert isinstance(result, MacroResult)
        assert result.scenario_name == sample_macro_scenario.name
        assert result.model_name == adapter.name

        # Tax cut should increase GDP
        assert np.all(result.gdp_level_pct > 0)

        # Employment should increase
        assert np.all(result.employment_change_millions > 0)

        # Revenue feedback should be positive
        assert result.cumulative_revenue_feedback > 0

    def test_spending_scenario(self, adapter, spending_scenario):
        """Test spending increase with higher FRB/US multiplier."""
        result = adapter.run(spending_scenario)

        # Spending increase should increase GDP
        assert np.all(result.gdp_level_pct > 0)

        # With FRB/US-calibrated multipliers, effect should be meaningful
        assert result.cumulative_gdp_effect > 0.1

    def test_crowding_out_effect(self, adapter, sample_macro_scenario):
        """Test that crowding out reduces GDP effect over time."""
        result = adapter.run(sample_macro_scenario)

        # With crowding out, later-year effects should be smaller
        # relative to cumulative fiscal impulse than early years
        early_effect = result.gdp_level_pct[0]
        late_effect = result.gdp_level_pct[-1]

        # Later effects exist but don't grow indefinitely
        assert late_effect > early_effect  # Cumulative effect
        assert late_effect < early_effect * 20  # But crowding limits growth

    def test_custom_multipliers(self, custom_adapter, sample_macro_scenario):
        """Test that custom multipliers affect results."""
        default_adapter = FRBUSAdapterLite()

        default_result = default_adapter.run(sample_macro_scenario)
        custom_result = custom_adapter.run(sample_macro_scenario)

        # Custom has higher tax multiplier, should have different effect
        assert custom_result.gdp_level_pct[0] != default_result.gdp_level_pct[0]

    def test_frbus_vs_simple_comparison(self, adapter, sample_macro_scenario):
        """Compare FRB/US-Lite to SimpleMultiplier results."""
        simple = SimpleMultiplierAdapter()

        frbus_result = adapter.run(sample_macro_scenario)
        simple_result = simple.run(sample_macro_scenario)

        # Both should show positive GDP effect for tax cut
        assert frbus_result.cumulative_gdp_effect > 0
        assert simple_result.cumulative_gdp_effect > 0

        # FRB/US-Lite has higher tax multiplier, so larger effect expected
        assert frbus_result.cumulative_gdp_effect > simple_result.cumulative_gdp_effect

    def test_baseline_projection(self, adapter):
        """Test baseline economic projection."""
        baseline = adapter.get_baseline()

        assert len(baseline) == 10
        assert "Year" in baseline.columns
        assert "GDP ($T)" in baseline.columns
        assert "Unemployment (%)" in baseline.columns
        assert baseline["GDP ($T)"].iloc[0] > 0


class TestPolicyToScenario:
    """Test policy to scenario conversion."""

    def test_tax_policy_conversion(self):
        """Test converting tax policy to scenario."""
        policy = TaxPolicy(
            name="Test Tax",
            description="Test",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.02,
        )

        # Mock scoring result
        class MockResult:
            final_deficit_effect = np.array([50.0] * 10)

        scenario = policy_to_scenario(policy, MockResult())

        assert scenario.name == policy.name
        assert len(scenario.receipts_change) == 10
        # Tax policy affects receipts
        assert not np.all(scenario.receipts_change == 0)

    def test_custom_scenario_name(self):
        """Test custom scenario name."""
        policy = TaxPolicy(
            name="Original Name",
            description="Test",
            policy_type=PolicyType.INCOME_TAX,
        )

        class MockResult:
            final_deficit_effect = np.array([0.0] * 10)

        scenario = policy_to_scenario(policy, MockResult(), scenario_name="Custom Name")

        assert scenario.name == "Custom Name"

    def test_scenario_horizon_matches_result(self):
        """Test that scenario horizon matches scoring result."""
        policy = TaxPolicy(
            name="Test",
            description="Test",
            policy_type=PolicyType.INCOME_TAX,
        )

        class MockResult:
            final_deficit_effect = np.array([10.0] * 5)  # 5 years

        scenario = policy_to_scenario(policy, MockResult())

        assert scenario.horizon_years == 5
        assert len(scenario.receipts_change) == 5


class TestMacroResultProperties:
    """Test MacroResult computed properties."""

    @pytest.fixture
    def sample_result(self):
        """Create a sample MacroResult."""
        return MacroResult(
            scenario_name="Test",
            model_name="Test Model",
            years=np.arange(2025, 2035),
            gdp_level_pct=np.array([0.1, 0.2, 0.3, 0.35, 0.38, 0.40, 0.41, 0.42, 0.43, 0.44]),
            gdp_growth_ppts=np.array([0.1, 0.1, 0.1, 0.05, 0.03, 0.02, 0.01, 0.01, 0.01, 0.01]),
            employment_change_millions=np.array([0.1, 0.2, 0.3, 0.35, 0.4, 0.42, 0.43, 0.44, 0.45, 0.46]),
            unemployment_rate_ppts=np.array([-0.05] * 10),
            short_rate_ppts=np.array([0.01] * 10),
            long_rate_ppts=np.array([0.02] * 10),
            revenue_feedback_billions=np.array([10.0] * 10),
            interest_cost_billions=np.array([5.0] * 10),
        )

    def test_cumulative_gdp_effect(self, sample_result):
        """Test cumulative GDP effect calculation."""
        expected = float(np.sum(sample_result.gdp_level_pct))
        assert abs(sample_result.cumulative_gdp_effect - expected) < 0.001

    def test_cumulative_revenue_feedback(self, sample_result):
        """Test cumulative revenue feedback calculation."""
        expected = float(np.sum(sample_result.revenue_feedback_billions))
        assert abs(sample_result.cumulative_revenue_feedback - expected) < 0.001

    def test_net_budget_effect(self, sample_result):
        """Test net budget effect calculation."""
        expected = (
            sample_result.cumulative_revenue_feedback -
            float(np.sum(sample_result.interest_cost_billions))
        )
        assert abs(sample_result.net_budget_effect - expected) < 0.001


class TestIntegration:
    """Integration tests combining multiple components."""

    def test_full_pipeline(self):
        """Test full pipeline from policy to macro result."""
        # Create policy
        policy = TaxPolicy(
            name="Integration Test",
            description="Test full pipeline",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=-0.02,
        )

        # Mock scoring result (tax cut = deficit increase)
        class MockScoringResult:
            final_deficit_effect = np.array([100.0] * 10)  # $100B/yr deficit increase

        # Convert to scenario
        scenario = policy_to_scenario(policy, MockScoringResult())

        # Run through adapter
        adapter = SimpleMultiplierAdapter()
        result = adapter.run(scenario)

        # Verify results make sense
        assert result.cumulative_gdp_effect > 0  # Tax cut stimulates
        assert result.cumulative_revenue_feedback > 0  # GDP growth generates revenue
        assert result.net_budget_effect != 0  # Some net effect

    def test_comparison_tax_vs_spending(self):
        """Compare tax cut vs spending increase effects."""
        adapter = SimpleMultiplierAdapter(
            spending_multiplier=1.0,
            tax_multiplier=-0.5,
        )

        # Tax cut scenario
        tax_scenario = MacroScenario(
            name="Tax Cut",
            description="$100B tax cut",
            receipts_change=np.array([-100.0] * 10),
        )

        # Equivalent spending increase
        spend_scenario = MacroScenario(
            name="Spending",
            description="$100B spending increase",
            outlays_change=np.array([100.0] * 10),
        )

        tax_result = adapter.run(tax_scenario)
        spend_result = adapter.run(spend_scenario)

        # With these multipliers, spending should have larger GDP effect
        # (spending multiplier 1.0 > tax multiplier magnitude 0.5)
        assert spend_result.cumulative_gdp_effect > tax_result.cumulative_gdp_effect
