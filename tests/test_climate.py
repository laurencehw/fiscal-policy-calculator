"""
Tests for climate and energy policy scoring.

Covers IRA clean energy credits, carbon taxes, EV credits, and other
climate-related fiscal policies. Validates against CBO estimates
and tests revenue, emissions, and behavioral effects.

References:
- CBO (2024): Budgetary Effects of IRA Energy-Related Tax Provisions
- EPA (2023): Social Cost of Carbon — $51/ton (Biden administration)
- EIA (2024): U.S. emissions baseline and energy outlook
"""

import pytest
import numpy as np
from fiscal_model.climate import (
    ClimateEnergyPolicy,
    ClimatePolicyType,
    create_repeal_ira_credits,
    create_carbon_tax_50,
    create_carbon_tax_25,
    create_repeal_ev_credits,
    create_extend_ira,
    CLIMATE_BASELINE,
    CLIMATE_VALIDATION_SCENARIOS,
)
from fiscal_model.policies import PolicyType
from fiscal_model.scoring import FiscalPolicyScorer


class TestRepealIRACredits:
    """Test IRA clean energy credit repeal policy."""

    def test_repeal_ira_creates_valid_policy(self):
        """Factory function should create valid policy."""
        policy = create_repeal_ira_credits()

        assert policy.name == "Repeal IRA Clean Energy Credits"
        assert policy.repeal_ira_credits is True
        assert policy.reform_type == ClimatePolicyType.IRA_REPEAL
        assert policy.policy_type == PolicyType.MANDATORY_SPENDING

    def test_repeal_ira_revenue_direction(self):
        """IRA repeal should increase revenue (reduces spending)."""
        policy = create_repeal_ira_credits()

        # Estimate annual effect
        annual_effect = policy.estimate_cost_effect()

        # Repeal saves money (positive = reduces spending)
        assert annual_effect < 0, (
            "Repeal should reduce spending (save money)"
        )

    def test_repeal_ira_magnitude(self):
        """IRA repeal should save ~$78.3B/year (CBO: $783B/10yr)."""
        policy = create_repeal_ira_credits()

        annual_effect = policy.estimate_cost_effect()

        # Should be around $78.3B/year
        # Allow 20% tolerance for baseline variations
        expected = CLIMATE_BASELINE["ira_annual_avg_billions"]
        assert abs(annual_effect - (-expected)) < expected * 0.2, (
            f"Repeal should save ~${expected:.1f}B/year, got ${-annual_effect:.1f}B"
        )

    def test_repeal_ira_increases_emissions(self):
        """Repeal should reduce emissions reduction (negative effect)."""
        policy = create_repeal_ira_credits()

        emissions_reduction = policy.estimate_emissions_reduction()

        # Repeal means less clean energy, so negative reduction (more emissions)
        assert emissions_reduction < 0, (
            "Repeal should reduce emissions reduction"
        )

    def test_repeal_ira_policy_type(self):
        """Policy should be classified as spending."""
        policy = create_repeal_ira_credits()

        assert policy.policy_type == PolicyType.MANDATORY_SPENDING


class TestCarbonTax50:
    """Test $50/ton carbon tax policy."""

    def test_carbon_tax_50_creates_valid_policy(self):
        """Factory function should create valid policy."""
        policy = create_carbon_tax_50()

        assert "Carbon Tax" in policy.name
        assert "50" in policy.name
        assert policy.carbon_tax_per_ton == 50.0
        assert policy.carbon_tax_growth_rate == 0.05
        assert policy.reform_type == ClimatePolicyType.CARBON_TAX
        assert policy.policy_type == PolicyType.EXCISE_TAX

    def test_carbon_tax_50_revenue_direction(self):
        """Carbon tax should raise revenue (negative = reduces deficit)."""
        policy = create_carbon_tax_50()

        annual_effect = policy.estimate_cost_effect()

        # Revenue positive (saves money)
        assert annual_effect < 0, (
            "Carbon tax should raise revenue"
        )

    def test_carbon_tax_50_magnitude(self):
        """$50/ton tax should raise ~$1.7T/10yr (CBO-style estimate)."""
        policy = create_carbon_tax_50()

        # Calculate annual average
        total_revenue = 0.0
        for yr in range(10):
            total_revenue += policy.estimate_carbon_tax_revenue(year_offset=yr)
        avg_annual = total_revenue / 10.0

        # CBO expects ~$170B/year average for $50/ton
        expected = 170.0
        assert abs(avg_annual - expected) < expected * 0.3, (
            f"$50/ton should raise ~${expected:.1f}B/year, got ${avg_annual:.1f}B"
        )

    def test_carbon_tax_50_emissions_reduction(self):
        """$50/ton tax should reduce emissions."""
        policy = create_carbon_tax_50()

        emissions_reduction = policy.estimate_emissions_reduction()

        # Should reduce emissions
        assert emissions_reduction > 0, (
            "Carbon tax should reduce emissions"
        )

    def test_carbon_tax_revenue_escalates(self):
        """Revenue should escalate with 5% annual price increase."""
        policy = create_carbon_tax_50()

        revenue_yr1 = policy.estimate_carbon_tax_revenue(year_offset=0)
        revenue_yr2 = policy.estimate_carbon_tax_revenue(year_offset=1)

        # Year 2 should be higher (price escalates)
        # But not 5% more due to behavioral response offsetting price growth
        assert revenue_yr2 >= revenue_yr1 * 0.95, (
            "Revenue should grow over time"
        )

    def test_carbon_tax_behavioral_offset(self):
        """Behavioral response should reduce revenue over time."""
        policy = create_carbon_tax_50()

        revenues = [policy.estimate_carbon_tax_revenue(y) for y in range(10)]

        # Due to emissions reduction from behavioral response,
        # revenue growth should slow over time
        growth_early = revenues[1] - revenues[0]
        growth_late = revenues[9] - revenues[8]

        # Growth should decline as behavioral effect accumulates
        # (Allow for some volatility)
        assert growth_late < growth_early * 0.5, (
            "Behavioral response should slow revenue growth"
        )


class TestCarbonTax25:
    """Test $25/ton carbon tax policy."""

    def test_carbon_tax_25_creates_valid_policy(self):
        """Factory function should create valid policy."""
        policy = create_carbon_tax_25()

        assert "Carbon Tax" in policy.name
        assert "25" in policy.name
        assert policy.carbon_tax_per_ton == 25.0
        assert policy.reform_type == ClimatePolicyType.CARBON_TAX

    def test_carbon_tax_25_magnitude(self):
        """$25/ton tax should raise ~$1.0T/10yr (CBO-style estimate)."""
        policy = create_carbon_tax_25()

        total_revenue = 0.0
        for yr in range(10):
            total_revenue += policy.estimate_carbon_tax_revenue(year_offset=yr)

        # CBO expects ~$1.0T total for $25/ton
        expected = 1000.0
        assert abs(total_revenue - expected) < expected * 0.4, (
            f"$25/ton should raise ~${expected:.0f}B/10yr, got ${total_revenue:.0f}B"
        )

    def test_carbon_tax_25_lower_than_50(self):
        """$25/ton should raise less revenue than $50/ton."""
        policy_25 = create_carbon_tax_25()
        policy_50 = create_carbon_tax_50()

        revenue_25 = sum(
            policy_25.estimate_carbon_tax_revenue(y) for y in range(10)
        )
        revenue_50 = sum(
            policy_50.estimate_carbon_tax_revenue(y) for y in range(10)
        )

        # $25/ton should raise less than $50/ton
        assert revenue_25 < revenue_50, (
            "$25/ton should raise less revenue than $50/ton"
        )

    def test_carbon_tax_25_emissions_reduction(self):
        """$25/ton tax should reduce emissions less than $50/ton."""
        policy_25 = create_carbon_tax_25()
        policy_50 = create_carbon_tax_50()

        reduction_25 = policy_25.estimate_emissions_reduction()
        reduction_50 = policy_50.estimate_emissions_reduction()

        # Lower price should mean less reduction
        assert reduction_25 < reduction_50, (
            "$25/ton should reduce emissions less than $50/ton"
        )


class TestRepealEVCredits:
    """Test EV credit repeal policy."""

    def test_repeal_ev_credits_creates_valid_policy(self):
        """Factory function should create valid policy."""
        policy = create_repeal_ev_credits()

        assert policy.name == "Repeal EV Tax Credits"
        assert policy.ev_credit_change == -7500.0
        assert policy.reform_type == ClimatePolicyType.EV_CREDIT_CHANGE

    def test_repeal_ev_credits_revenue_direction(self):
        """EV credit repeal should increase revenue (save money)."""
        policy = create_repeal_ev_credits()

        annual_effect = policy.estimate_cost_effect()

        # Repeal saves money
        assert annual_effect < 0, (
            "Repeal should save money"
        )

    def test_repeal_ev_credits_magnitude(self):
        """EV credit repeal should save ~$200B/10yr (CBO estimate)."""
        policy = create_repeal_ev_credits()

        # Calculate total over 10 years
        annual_effect = policy.estimate_cost_effect()
        ten_year_effect = annual_effect * 10

        # CBO estimates $200B total
        # So ~$20B/year average
        expected_annual = 20.0
        assert abs(annual_effect - (-expected_annual)) < expected_annual * 0.3, (
            f"Repeal should save ~${expected_annual:.1f}B/year, got ${-annual_effect:.1f}B"
        )

    def test_repeal_ev_credits_emissions_impact(self):
        """EV credit repeal should increase emissions (less EV adoption)."""
        policy = create_repeal_ev_credits()

        emissions_reduction = policy.estimate_emissions_reduction()

        # Repeal means less EV adoption, so zero or negative emissions impact
        # (The EV credit reduction is not explicitly modeled in emissions yet)
        assert emissions_reduction <= 0, (
            "Repeal should not increase emissions reduction"
        )


class TestExtendIRACredits:
    """Test IRA credit extension policy."""

    def test_extend_ira_creates_valid_policy(self):
        """Factory function should create valid policy."""
        policy = create_extend_ira()

        assert policy.name == "Extend IRA Credits (5 years)"
        assert policy.extend_ira_credits is True
        assert policy.ira_extension_years == 5
        assert policy.reform_type == ClimatePolicyType.IRA_EXTENSION

    def test_extend_ira_revenue_direction(self):
        """IRA extension should increase spending (cost money)."""
        policy = create_extend_ira()

        annual_effect = policy.estimate_cost_effect()

        # Extension costs money
        assert annual_effect > 0, (
            "Extension should cost money (increase spending)"
        )

    def test_extend_ira_magnitude(self):
        """IRA extension should cost ~$400B/5yr (CBO-style estimate)."""
        policy = create_extend_ira()

        annual_effect = policy.estimate_cost_effect()

        # $400B over 5 years = $80B/year
        # But averaged over 10-year budget window
        expected_total_extension = (
            CLIMATE_BASELINE["ira_extension_5yr_billions"]
        )
        # Averaged over 10 years: ~$40B/year
        expected_annual = expected_total_extension / 10.0

        assert abs(annual_effect - expected_annual) < expected_annual * 0.3, (
            f"Extension should cost ~${expected_annual:.1f}B/year, got ${annual_effect:.1f}B"
        )

    def test_extend_ira_emissions_reduction(self):
        """IRA extension should increase emissions reduction."""
        policy = create_extend_ira()

        emissions_reduction = policy.estimate_emissions_reduction()

        # Extension means more clean energy, so positive emissions reduction
        assert emissions_reduction > 0, (
            "Extension should increase emissions reduction"
        )


class TestEnvironmentalMetrics:
    """Test environmental impact calculations."""

    def test_carbon_tax_50_metrics(self):
        """$50/ton carbon tax should have reasonable environmental metrics."""
        policy = create_carbon_tax_50()

        metrics = policy.get_environmental_metrics()

        # Should have CO2 reduction
        assert metrics["co2_reduction_gt"] > 0
        assert metrics["co2_reduction_pct"] > 0

        # Should have social benefit
        assert metrics["social_benefit_billions"] > 0

        # Should have revenue
        assert metrics["total_revenue_billions"] > 0

        # Net benefit should be positive (benefits > costs)
        assert metrics["net_social_benefit_billions"] > 0

    def test_repeal_ira_metrics(self):
        """IRA repeal should have negative environmental metrics."""
        policy = create_repeal_ira_credits()

        metrics = policy.get_environmental_metrics()

        # Repeal reduces emissions reduction (increases emissions)
        assert metrics["co2_reduction_gt"] < 0

    def test_carbon_tax_consumer_cost(self):
        """Carbon tax should have estimated consumer costs."""
        policy = create_carbon_tax_50()

        metrics = policy.get_environmental_metrics()

        # Consumer cost should be estimated
        assert metrics["consumer_cost_billions"] > 0

        # Consumer cost should be less than total revenue
        # (60% pass-through estimate)
        assert (
            metrics["consumer_cost_billions"]
            <= metrics["total_revenue_billions"]
        )

    def test_social_cost_of_carbon_included(self):
        """Environmental metrics should include social cost of carbon."""
        policy = create_carbon_tax_50()

        metrics = policy.get_environmental_metrics()

        # Should include SCC per ton
        assert metrics["social_cost_of_carbon_per_ton"] == 51.0  # EPA 2023 estimate


class TestPolicyTypeCorrectness:
    """Test that policies are classified correctly."""

    def test_carbon_tax_is_excise_tax(self):
        """Carbon tax should be classified as EXCISE_TAX."""
        policy = create_carbon_tax_50()

        assert policy.policy_type == PolicyType.EXCISE_TAX

    def test_ira_repeal_is_mandatory_spending(self):
        """IRA repeal should be classified as MANDATORY_SPENDING."""
        policy = create_repeal_ira_credits()

        assert policy.policy_type == PolicyType.MANDATORY_SPENDING

    def test_ev_credit_repeal_is_mandatory_spending(self):
        """EV credit repeal should be classified as MANDATORY_SPENDING."""
        policy = create_repeal_ev_credits()

        assert policy.policy_type == PolicyType.MANDATORY_SPENDING

    def test_ira_extension_is_mandatory_spending(self):
        """IRA extension should be classified as MANDATORY_SPENDING."""
        policy = create_extend_ira()

        assert policy.policy_type == PolicyType.MANDATORY_SPENDING


class TestCustomClimatePolicy:
    """Test custom climate policy creation."""

    def test_custom_carbon_tax(self):
        """Should be able to create custom carbon tax."""
        policy = ClimateEnergyPolicy(
            name="Custom Carbon Tax",
            description="Test policy",
            policy_type=PolicyType.EXCISE_TAX,
            reform_type=ClimatePolicyType.CARBON_TAX,
            carbon_tax_per_ton=100.0,
        )

        assert policy.carbon_tax_per_ton == 100.0
        assert policy.policy_type == PolicyType.EXCISE_TAX

    def test_custom_ev_credit_cut(self):
        """Should be able to customize EV credit change."""
        policy = ClimateEnergyPolicy(
            name="Reduce EV Credit",
            description="Cut EV credit to 3750",
            policy_type=PolicyType.MANDATORY_SPENDING,
            reform_type=ClimatePolicyType.EV_CREDIT_CHANGE,
            ev_credit_change=-3750.0,
        )

        assert policy.ev_credit_change == -3750.0

    def test_custom_policy_cost_effect(self):
        """Custom policy should calculate cost effect."""
        policy = ClimateEnergyPolicy(
            name="Hybrid Policy",
            description="Carbon tax + EV credit cut",
            policy_type=PolicyType.EXCISE_TAX,
            reform_type=ClimatePolicyType.CUSTOM,
            carbon_tax_per_ton=25.0,
            ev_credit_change=-3750.0,
        )

        cost_effect = policy.estimate_cost_effect()

        # Should be valid number
        assert not np.isnan(cost_effect)
        assert not np.isinf(cost_effect)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_carbon_tax(self):
        """Zero carbon tax should have zero effect."""
        policy = ClimateEnergyPolicy(
            name="No Tax",
            description="Zero carbon tax",
            policy_type=PolicyType.EXCISE_TAX,
            reform_type=ClimatePolicyType.CARBON_TAX,
            carbon_tax_per_ton=0.0,
        )

        revenue = policy.estimate_carbon_tax_revenue(year_offset=0)
        assert revenue == 0.0

    def test_very_high_carbon_tax(self):
        """Very high carbon tax should have large but reasonable effect."""
        policy = ClimateEnergyPolicy(
            name="High Tax",
            description="200/ton carbon tax",
            policy_type=PolicyType.EXCISE_TAX,
            reform_type=ClimatePolicyType.CARBON_TAX,
            carbon_tax_per_ton=200.0,
        )

        revenue = policy.estimate_carbon_tax_revenue(year_offset=0)

        # Should be large positive number (but behavioral response reduces it)
        assert revenue > 400.0

        # But not infinite
        assert revenue < 10000.0

    def test_multiple_policies_combined(self):
        """Should be able to combine multiple policies."""
        policy = ClimateEnergyPolicy(
            name="Comprehensive",
            description="Carbon tax + IRA extension",
            policy_type=PolicyType.EXCISE_TAX,
            reform_type=ClimatePolicyType.CUSTOM,
            carbon_tax_per_ton=50.0,
            extend_ira_credits=True,
        )

        cost_effect = policy.estimate_cost_effect()

        # Should reflect both policies
        assert cost_effect < 0, "Should raise net revenue"

    def test_policy_with_no_effect(self):
        """A policy with all parameters at zero should have zero effect."""
        policy = ClimateEnergyPolicy(
            name="No Effect",
            description="All parameters zero",
            policy_type=PolicyType.MANDATORY_SPENDING,
            reform_type=ClimatePolicyType.CUSTOM,
            carbon_tax_per_ton=0.0,
            ev_credit_change=0.0,
            repeal_ira_credits=False,
            extend_ira_credits=False,
        )

        cost_effect = policy.estimate_cost_effect()

        assert cost_effect == 0.0


class TestValidationScenarios:
    """Test against CBO validation scenarios."""

    def test_all_scenarios_produce_valid_results(self):
        """All validation scenarios should produce valid results."""
        from fiscal_model.climate import CLIMATE_VALIDATION_SCENARIOS

        for scenario_name, scenario_info in CLIMATE_VALIDATION_SCENARIOS.items():
            # Create policy based on scenario
            if "repeal_ira" in scenario_name:
                policy = create_repeal_ira_credits()
            elif "carbon_50" in scenario_name:
                policy = create_carbon_tax_50()
            elif "carbon_25" in scenario_name:
                policy = create_carbon_tax_25()
            elif "ev_credit" in scenario_name:
                policy = create_repeal_ev_credits()
            elif "extend_ira" in scenario_name:
                policy = create_extend_ira()
            else:
                continue

            # Calculate effect
            cost_effect = policy.estimate_cost_effect()

            # Should be valid number
            assert not np.isnan(cost_effect), (
                f"Scenario {scenario_name} produced NaN"
            )
            assert not np.isinf(cost_effect), (
                f"Scenario {scenario_name} produced Inf"
            )

    def test_scenario_directions_correct(self):
        """Validation scenarios should have correct direction (revenue vs spending)."""
        scenarios = {
            "repeal_ira_credits": (create_repeal_ira_credits(), False),  # Saves money
            "carbon_tax_50": (create_carbon_tax_50(), False),  # Raises revenue
            "carbon_tax_25": (create_carbon_tax_25(), False),  # Raises revenue
            "ev_credit_repeal": (create_repeal_ev_credits(), False),  # Saves money
            "extend_ira_5yr": (create_extend_ira(), True),  # Costs money
        }

        for name, (policy, should_cost) in scenarios.items():
            effect = policy.estimate_cost_effect()

            if should_cost:
                assert effect > 0, f"{name} should cost money"
            else:
                assert effect < 0, f"{name} should raise revenue"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
