"""
Tests for trade and tariff policy module.

Covers:
- TariffPolicy creation and validation
- Revenue calculation for tariff presets
- Consumer cost estimation
- Retaliation cost estimation
- Household impact calculation
- Behavioral offset (avoidance)
- Edge cases and non-linear volume effects
- Trade summary and factory functions
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fiscal_model.policies import PolicyType
from fiscal_model.trade import (
    TRADE_BASELINE,
    TariffPolicy,
    create_auto_tariff_25,
    create_reciprocal_tariffs,
    create_steel_tariff_25,
    create_trump_china_60,
    create_trump_universal_10,
)


class TestTariffPolicyCreation:
    """Test TariffPolicy creation and validation."""

    def test_tariff_policy_basic_creation(self):
        """Test basic TariffPolicy instantiation."""
        policy = TariffPolicy(
            name="Test Tariff",
            description="Test description",
            tariff_rate_change=0.10,
            import_base_billions=1000.0,
        )
        assert policy.name == "Test Tariff"
        assert policy.tariff_rate_change == 0.10
        assert policy.import_base_billions == 1000.0
        assert policy.policy_type == PolicyType.EXCISE_TAX

    def test_tariff_policy_default_base(self):
        """Test that zero import_base defaults to total imports."""
        policy = TariffPolicy(
            name="Test Tariff",
            description="Test description",
            tariff_rate_change=0.10,
            import_base_billions=0.0,
        )
        assert policy.import_base_billions == TRADE_BASELINE["total_imports_billions"]

    def test_tariff_policy_pass_through_rate(self):
        """Test pass-through rate defaults and overrides."""
        policy = TariffPolicy(
            name="Test Tariff",
            description="Test description",
            tariff_rate_change=0.10,
            import_base_billions=1000.0,
        )
        assert policy.pass_through_rate == TRADE_BASELINE["consumer_pass_through_rate"]

        policy2 = TariffPolicy(
            name="Test Tariff 2",
            description="Test description 2",
            tariff_rate_change=0.10,
            import_base_billions=1000.0,
            pass_through_rate=0.80,
        )
        assert policy2.pass_through_rate == 0.80

    def test_tariff_policy_with_country_target(self):
        """Test tariff policy with target country specified."""
        policy = TariffPolicy(
            name="China Tariff",
            description="China tariff test",
            tariff_rate_change=0.60,
            target_country="china",
            import_base_billions=430.0,
        )
        assert policy.target_country == "china"

    def test_tariff_policy_with_sector_target(self):
        """Test tariff policy with target sector specified."""
        policy = TariffPolicy(
            name="Auto Tariff",
            description="Auto tariff test",
            tariff_rate_change=0.25,
            target_sector="autos",
            import_base_billions=133.0,
        )
        assert policy.target_sector == "autos"


class TestRevenueCalculation:
    """Test tariff revenue calculations for different presets."""

    def test_trump_universal_10_revenue(self):
        """Test universal 10% tariff revenue calculation."""
        policy = create_trump_universal_10()
        static_revenue = policy.estimate_static_revenue_effect(0)
        assert static_revenue > 200 and static_revenue < 250

    def test_trump_china_60_revenue(self):
        """Test China 60% tariff revenue calculation."""
        policy = create_trump_china_60()
        static_revenue = policy.estimate_static_revenue_effect(0)
        assert static_revenue > 40 and static_revenue < 90

    def test_auto_tariff_25_revenue(self):
        """Test 25% auto tariff revenue calculation."""
        policy = create_auto_tariff_25()
        static_revenue = policy.estimate_static_revenue_effect(0)
        assert static_revenue > 20 and static_revenue < 35

    def test_steel_tariff_25_revenue(self):
        """Test 25% steel/aluminum tariff revenue calculation."""
        policy = create_steel_tariff_25()
        static_revenue = policy.estimate_static_revenue_effect(0)
        assert static_revenue > 8 and static_revenue < 15

    def test_reciprocal_tariff_revenue(self):
        """Test reciprocal tariff revenue calculation."""
        policy = create_reciprocal_tariffs()
        static_revenue = policy.estimate_static_revenue_effect(0)
        assert static_revenue > 250 and static_revenue < 330


class TestConsumerImpact:
    """Test consumer cost estimation methods."""

    def test_estimate_consumer_cost_basic(self):
        """Test basic consumer cost calculation."""
        policy = TariffPolicy(
            name="Test",
            description="Test",
            tariff_rate_change=0.10,
            import_base_billions=1000.0,
            pass_through_rate=0.60,
        )
        consumer_cost = policy.estimate_consumer_cost()
        assert consumer_cost == 60.0

    def test_estimate_consumer_cost_zero_tariff(self):
        """Test that zero tariff yields zero consumer cost."""
        policy = TariffPolicy(
            name="Test",
            description="Test",
            tariff_rate_change=0.0,
            import_base_billions=1000.0,
        )
        consumer_cost = policy.estimate_consumer_cost()
        assert consumer_cost == 0.0

    def test_estimate_consumer_cost_high_pass_through(self):
        """Test consumer cost with high pass-through rate."""
        policy = TariffPolicy(
            name="Test",
            description="Test",
            tariff_rate_change=0.10,
            import_base_billions=1000.0,
            pass_through_rate=1.0,
        )
        consumer_cost = policy.estimate_consumer_cost()
        assert consumer_cost == 100.0

    def test_estimate_consumer_cost_low_pass_through(self):
        """Test consumer cost with low pass-through rate."""
        policy = TariffPolicy(
            name="Test",
            description="Test",
            tariff_rate_change=0.10,
            import_base_billions=1000.0,
            pass_through_rate=0.30,
        )
        consumer_cost = policy.estimate_consumer_cost()
        assert consumer_cost == 30.0

    def test_universal_10_consumer_cost(self):
        """Test universal 10% tariff consumer cost."""
        policy = create_trump_universal_10()
        consumer_cost = policy.estimate_consumer_cost()
        assert 130 < consumer_cost < 140


class TestRetaliationCost:
    """Test retaliation cost estimation."""

    def test_estimate_retaliation_cost_basic(self):
        """Test basic retaliation cost calculation."""
        policy = TariffPolicy(
            name="Test",
            description="Test",
            tariff_rate_change=0.10,
            import_base_billions=1000.0,
            retaliation_rate=0.30,
        )
        retaliation_cost = policy.estimate_retaliation_cost()
        assert retaliation_cost == 63.0

    def test_estimate_retaliation_cost_zero_tariff(self):
        """Test that zero tariff yields zero retaliation cost."""
        policy = TariffPolicy(
            name="Test",
            description="Test",
            tariff_rate_change=0.0,
            import_base_billions=1000.0,
        )
        retaliation_cost = policy.estimate_retaliation_cost()
        assert retaliation_cost == 0.0

    def test_estimate_retaliation_cost_custom_rate(self):
        """Test retaliation cost with custom retaliation rate."""
        policy = TariffPolicy(
            name="Test",
            description="Test",
            tariff_rate_change=0.10,
            import_base_billions=1000.0,
            retaliation_rate=0.50,
        )
        retaliation_cost = policy.estimate_retaliation_cost()
        assert retaliation_cost == 105.0

    def test_universal_10_retaliation_cost(self):
        """Test universal 10% tariff retaliation cost."""
        policy = create_trump_universal_10()
        retaliation_cost = policy.estimate_retaliation_cost()
        assert 60 < retaliation_cost < 70


class TestHouseholdImpact:
    """Test per-household impact calculations."""

    def test_household_impact_basic(self):
        """Test basic household impact calculation."""
        policy = TariffPolicy(
            name="Test",
            description="Test",
            tariff_rate_change=0.10,
            import_base_billions=1000.0,
            pass_through_rate=0.60,
        )
        household_cost = policy.get_household_impact()
        expected = 60.0 * 1e9 / TRADE_BASELINE["us_households"]
        assert abs(household_cost - expected) < 1.0

    def test_household_impact_zero_tariff(self):
        """Test that zero tariff yields zero household cost."""
        policy = TariffPolicy(
            name="Test",
            description="Test",
            tariff_rate_change=0.0,
            import_base_billions=1000.0,
        )
        household_cost = policy.get_household_impact()
        assert household_cost == 0.0

    def test_universal_10_household_impact(self):
        """Test universal 10% tariff household impact."""
        policy = create_trump_universal_10()
        household_cost = policy.get_household_impact()
        assert 1000 < household_cost < 1100

    def test_china_60_household_impact(self):
        """Test China 60% tariff household impact."""
        policy = create_trump_china_60()
        household_cost = policy.get_household_impact()
        assert household_cost < 500


class TestBehavioralOffset:
    """Test tariff avoidance behavioral offset."""

    def test_behavioral_offset_basic(self):
        """Test basic behavioral offset calculation."""
        policy = TariffPolicy(
            name="Test",
            description="Test",
            tariff_rate_change=0.10,
            import_base_billions=1000.0,
        )
        static = policy.estimate_static_revenue_effect(0)
        offset = policy.estimate_behavioral_offset(static)
        expected = TRADE_BASELINE["tariff_avoidance_rate"] * static
        assert abs(offset - expected) < 0.01

    def test_behavioral_offset_zero_static(self):
        """Test that zero static revenue yields zero offset."""
        policy = TariffPolicy(
            name="Test",
            description="Test",
            tariff_rate_change=0.0,
            import_base_billions=1000.0,
        )
        static = policy.estimate_static_revenue_effect(0)
        offset = policy.estimate_behavioral_offset(static)
        assert offset == 0.0

    def test_behavioral_offset_high_tariff(self):
        """Test behavioral offset scales with tariff rate."""
        policy_low = TariffPolicy(
            name="Low",
            description="Test",
            tariff_rate_change=0.05,
            import_base_billions=1000.0,
        )
        policy_high = TariffPolicy(
            name="High",
            description="Test",
            tariff_rate_change=0.20,
            import_base_billions=1000.0,
        )
        static_low = policy_low.estimate_static_revenue_effect(0)
        static_high = policy_high.estimate_static_revenue_effect(0)
        offset_low = policy_low.estimate_behavioral_offset(static_low)
        offset_high = policy_high.estimate_behavioral_offset(static_high)
        assert offset_high > offset_low


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_tariff_rate(self):
        """Test that zero tariff rate produces zero effects."""
        policy = TariffPolicy(
            name="Zero Tariff",
            description="Test",
            tariff_rate_change=0.0,
            import_base_billions=1000.0,
        )
        assert policy.estimate_static_revenue_effect(0) == 0.0
        assert policy.estimate_consumer_cost() == 0.0
        assert policy.estimate_retaliation_cost() == 0.0
        assert policy.get_household_impact() == 0.0

    def test_very_high_tariff_100_percent(self):
        """Test very high tariff rate (100%) with volume floor."""
        policy = TariffPolicy(
            name="Extreme Tariff",
            description="Test",
            tariff_rate_change=1.0,
            import_base_billions=1000.0,
        )
        static_revenue = policy.estimate_static_revenue_effect(0)
        assert static_revenue >= 200.0

    def test_negative_tariff_rate(self):
        """Test that negative tariff (tariff cut) produces negative revenue."""
        policy = TariffPolicy(
            name="Tariff Cut",
            description="Test",
            tariff_rate_change=-0.05,
            import_base_billions=1000.0,
        )
        static_revenue = policy.estimate_static_revenue_effect(0)
        assert static_revenue < 0.0

    def test_zero_import_base_defaults(self):
        """Test that zero base defaults to total imports."""
        policy = TariffPolicy(
            name="Zero Base",
            description="Test",
            tariff_rate_change=0.10,
            import_base_billions=0.0,
        )
        assert policy.import_base_billions == TRADE_BASELINE["total_imports_billions"]

    def test_very_large_import_base(self):
        """Test with very large import base."""
        policy = TariffPolicy(
            name="Large Base",
            description="Test",
            tariff_rate_change=0.10,
            import_base_billions=10000.0,
        )
        static_revenue = policy.estimate_static_revenue_effect(0)
        assert static_revenue > 500.0


class TestNonLinearVolumeEffects:
    """Test non-linear volume effects at high tariff rates."""

    def test_low_tariff_volume_effect(self):
        """Test linear volume effect at low tariff rates."""
        policy = TariffPolicy(
            name="Low Tariff",
            description="Test",
            tariff_rate_change=0.10,
            import_base_billions=1000.0,
        )
        static_revenue = policy.estimate_static_revenue_effect(0)
        assert static_revenue > 0

    def test_high_tariff_volume_effect(self):
        """Test non-linear volume effect at high tariff rates."""
        policy_low = TariffPolicy(
            name="25% Tariff",
            description="Test",
            tariff_rate_change=0.25,
            import_base_billions=1000.0,
        )
        policy_high = TariffPolicy(
            name="40% Tariff",
            description="Test",
            tariff_rate_change=0.40,
            import_base_billions=1000.0,
        )
        static_low = policy_low.estimate_static_revenue_effect(0)
        static_high = policy_high.estimate_static_revenue_effect(0)
        ratio = static_high / static_low if static_low > 0 else 0
        assert ratio < 1.6

    def test_volume_floor_prevents_collapse(self):
        """Test that volume floor prevents import collapse."""
        policy = TariffPolicy(
            name="Extreme",
            description="Test",
            tariff_rate_change=2.0,
            import_base_billions=1000.0,
        )
        static_revenue = policy.estimate_static_revenue_effect(0)
        assert static_revenue >= 400.0


class TestGetTradeSummary:
    """Test get_trade_summary() method."""

    def test_trade_summary_keys(self):
        """Test that trade summary contains all required keys."""
        policy = create_trump_universal_10()
        summary = policy.get_trade_summary()
        required_keys = {
            "tariff_revenue",
            "behavioral_offset",
            "net_revenue",
            "consumer_cost",
            "retaliation_cost",
            "household_cost",
        }
        assert set(summary.keys()) == required_keys

    def test_trade_summary_relationships(self):
        """Test that summary values have correct relationships."""
        policy = create_trump_universal_10()
        summary = policy.get_trade_summary()
        assert abs(
            summary["net_revenue"] - (summary["tariff_revenue"] - summary["behavioral_offset"])
        ) < 0.01
        assert abs(summary["consumer_cost"] - policy.estimate_consumer_cost()) < 0.01
        assert abs(summary["retaliation_cost"] - policy.estimate_retaliation_cost()) < 0.01

    def test_trade_summary_all_zeros_for_zero_tariff(self):
        """Test that summary is all zeros for zero tariff."""
        policy = TariffPolicy(
            name="Zero Tariff",
            description="Test",
            tariff_rate_change=0.0,
            import_base_billions=1000.0,
        )
        summary = policy.get_trade_summary()
        for key, value in summary.items():
            assert value == 0.0, f"{key} should be 0 for zero tariff"


class TestFactoryFunctions:
    """Test factory functions return correct types."""

    def test_create_trump_universal_10(self):
        """Test trump_universal_10 factory function."""
        policy = create_trump_universal_10()
        assert isinstance(policy, TariffPolicy)
        assert policy.tariff_rate_change == 0.10
        assert "Universal 10%" in policy.name

    def test_create_trump_china_60(self):
        """Test trump_china_60 factory function."""
        policy = create_trump_china_60()
        assert isinstance(policy, TariffPolicy)
        assert policy.target_country == "china"
        assert policy.tariff_rate_change > 0

    def test_create_auto_tariff_25(self):
        """Test auto_tariff_25 factory function."""
        policy = create_auto_tariff_25()
        assert isinstance(policy, TariffPolicy)
        assert policy.target_sector == "autos"

    def test_create_steel_tariff_25(self):
        """Test steel_tariff_25 factory function."""
        policy = create_steel_tariff_25()
        assert isinstance(policy, TariffPolicy)
        assert policy.target_sector == "steel"
        assert "Steel" in policy.name

    def test_create_reciprocal_tariffs(self):
        """Test reciprocal_tariffs factory function."""
        policy = create_reciprocal_tariffs()
        assert isinstance(policy, TariffPolicy)
        assert policy.tariff_rate_change == 0.20
        assert "Reciprocal" in policy.name


class TestTariffValidationAgainstCBO:
    """Test tariff policy scores against known CBO estimates."""

    def test_universal_10_within_range(self):
        """Test that universal 10% tariff revenue is within plausible range."""
        policy = create_trump_universal_10()
        summary = policy.get_trade_summary()
        annual_net = summary["net_revenue"]
        assert 150 < annual_net < 250, f"Annual revenue {annual_net}B outside expected range"

    def test_china_60_within_range(self):
        """Test that China 60% tariff revenue is within plausible range."""
        policy = create_trump_china_60()
        summary = policy.get_trade_summary()
        annual_net = summary["net_revenue"]
        assert 30 < annual_net < 70, f"Annual revenue {annual_net}B outside expected range"

    def test_auto_25_within_range(self):
        """Test that auto 25% tariff revenue is within plausible range."""
        policy = create_auto_tariff_25()
        summary = policy.get_trade_summary()
        annual_net = summary["net_revenue"]
        assert 15 < annual_net < 35, f"Annual revenue {annual_net}B outside expected range"
