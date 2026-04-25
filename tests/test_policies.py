"""
Tests for fiscal_model/policies.py

Covers Policy base class, TaxPolicy, CapitalGainsPolicy, SpendingPolicy,
TransferPolicy, PolicyPackage, and convenience factory functions.
"""

import pytest

from fiscal_model.policies import (
    CapitalGainsPolicy,
    Policy,
    PolicyPackage,
    PolicyType,
    SpendingPolicy,
    TaxPolicy,
    TransferPolicy,
    create_income_tax_cut,
    create_new_tax_credit,
    create_spending_increase,
)

# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def base_policy():
    """A minimal Policy for testing base-class behaviour."""
    return Policy(
        name="Base",
        description="base policy",
        policy_type=PolicyType.INCOME_TAX,
        start_year=2025,
        duration_years=10,
        phase_in_years=1,
        sunset=False,
    )


@pytest.fixture
def sunset_policy():
    """Policy that sunsets after 5 years."""
    return Policy(
        name="Sunset",
        description="sunsets after 5 years",
        policy_type=PolicyType.INCOME_TAX,
        start_year=2025,
        duration_years=5,
        phase_in_years=1,
        sunset=True,
    )


@pytest.fixture
def phase_in_policy():
    """Policy with a 4-year phase-in starting 2025."""
    return Policy(
        name="PhaseIn",
        description="4-year phase-in",
        policy_type=PolicyType.INCOME_TAX,
        start_year=2025,
        duration_years=10,
        phase_in_years=4,
        sunset=True,
    )


@pytest.fixture
def bracket_tax_policy():
    """TaxPolicy with bracket-level data for static scoring."""
    return TaxPolicy(
        name="Bracket Tax",
        description="rate increase on high earners",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=0.026,
        affected_income_threshold=400_000,
        affected_taxpayers_millions=1.8,
        avg_taxable_income_in_bracket=1_200_000,
    )


@pytest.fixture
def cap_gains_policy():
    """CapitalGainsPolicy with sensible defaults for testing."""
    return CapitalGainsPolicy(
        name="CG Increase",
        description="raise cap gains rate",
        policy_type=PolicyType.CAPITAL_GAINS_TAX,
        rate_change=0.05,
        baseline_capital_gains_rate=0.20,
        baseline_realizations_billions=1000.0,
        step_up_at_death=False,  # disable multiplier for cleaner tests
        eliminate_step_up=False,
    )


@pytest.fixture
def spending_policy():
    """Basic SpendingPolicy."""
    return SpendingPolicy(
        name="Infra",
        description="infrastructure spending",
        policy_type=PolicyType.INFRASTRUCTURE,
        start_year=2025,
        duration_years=10,
        annual_spending_change_billions=50.0,
        annual_growth_rate=0.02,
    )


@pytest.fixture
def transfer_policy():
    """Basic TransferPolicy."""
    return TransferPolicy(
        name="SS Increase",
        description="social security benefit increase",
        policy_type=PolicyType.SOCIAL_SECURITY,
        benefit_change_percent=0.05,
        new_beneficiaries_millions=2.0,
        start_year=2025,
        duration_years=10,
    )


# =============================================================================
# Policy.get_phase_in_factor
# =============================================================================

class TestPolicyPhaseInFactor:
    def test_before_start_returns_zero(self, base_policy):
        assert base_policy.get_phase_in_factor(2024) == 0.0

    def test_after_full_phase_in_returns_one(self, base_policy):
        # phase_in_years=1 means immediate full effect
        assert base_policy.get_phase_in_factor(2025) == 1.0
        assert base_policy.get_phase_in_factor(2030) == 1.0

    def test_during_phase_in_fractional(self, phase_in_policy):
        # phase_in_years=4, start_year=2025
        # year 2025: years_since_start=0, factor = (0+1)/4 = 0.25
        assert phase_in_policy.get_phase_in_factor(2025) == pytest.approx(0.25)
        # year 2026: (1+1)/4 = 0.50
        assert phase_in_policy.get_phase_in_factor(2026) == pytest.approx(0.50)
        # year 2027: (2+1)/4 = 0.75
        assert phase_in_policy.get_phase_in_factor(2027) == pytest.approx(0.75)
        # year 2028: (3+1)/4 = 1.0
        assert phase_in_policy.get_phase_in_factor(2028) == pytest.approx(1.0)

    def test_after_sunset_returns_zero(self, sunset_policy):
        # duration_years=5, start=2025 => sunset at year 2030
        assert sunset_policy.get_phase_in_factor(2030) == 0.0
        assert sunset_policy.get_phase_in_factor(2035) == 0.0

    def test_just_before_sunset_returns_one(self, sunset_policy):
        assert sunset_policy.get_phase_in_factor(2029) == 1.0

    def test_no_sunset_stays_active(self, base_policy):
        assert base_policy.get_phase_in_factor(2040) == 1.0


# =============================================================================
# Policy.is_active
# =============================================================================

class TestPolicyIsActive:
    def test_before_start(self, base_policy):
        assert base_policy.is_active(2024) is False

    def test_during_active_period(self, base_policy):
        assert base_policy.is_active(2025) is True
        assert base_policy.is_active(2030) is True

    def test_after_sunset(self, sunset_policy):
        assert sunset_policy.is_active(2030) is False

    def test_no_sunset_always_active_after_start(self, base_policy):
        assert base_policy.is_active(2050) is True


# =============================================================================
# TaxPolicy.estimate_static_revenue_effect
# =============================================================================

class TestTaxPolicyStaticRevenue:
    def test_bracket_level_calculation(self, bracket_tax_policy):
        """With bracket data, revenue = rate_change * marginal_income * taxpayers."""
        result = bracket_tax_policy.estimate_static_revenue_effect(
            baseline_revenue=2000, use_real_data=False
        )
        # marginal_income = 1_200_000 - 400_000 = 800_000
        # revenue = 0.026 * 800_000 * 1.8e6 / 1e9 = 37.44 B
        expected = 0.026 * 800_000 * 1.8e6 / 1e9
        assert result == pytest.approx(expected, rel=1e-6)

    def test_fallback_proportional(self):
        """Without bracket data, uses proportional heuristic."""
        policy = TaxPolicy(
            name="Proportional",
            description="rate change only",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.02,
            affected_income_threshold=200_000,
        )
        result = policy.estimate_static_revenue_effect(
            baseline_revenue=2000, use_real_data=False
        )
        # affected_share for 200K threshold = 0.40
        # avg_effective_rate = 0.18
        # result = 2000 * 0.40 * (0.02 / 0.18)
        expected = 2000 * 0.40 * (0.02 / 0.18)
        assert result == pytest.approx(expected, rel=1e-6)

    def test_annual_revenue_change_override(self):
        """annual_revenue_change_billions takes precedence over everything."""
        policy = TaxPolicy(
            name="Override",
            description="override",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=0.05,
            annual_revenue_change_billions=-50.0,
        )
        result = policy.estimate_static_revenue_effect(
            baseline_revenue=2000, use_real_data=False
        )
        assert result == -50.0

    def test_credit_amount(self):
        """credit_amount produces negative revenue (cost)."""
        policy = TaxPolicy(
            name="Credit",
            description="credit",
            policy_type=PolicyType.TAX_CREDIT,
            credit_amount=1000,
            affected_taxpayers_millions=30.0,
        )
        result = policy.estimate_static_revenue_effect(
            baseline_revenue=2000, use_real_data=False
        )
        # -1000 * 30 / 1e3 = -30 B
        assert result == pytest.approx(-30.0)

    def test_zero_threshold_uses_full_income(self):
        """When threshold is 0, marginal_income = full avg_taxable_income."""
        policy = TaxPolicy(
            name="AllIncome",
            description="affects all",
            policy_type=PolicyType.INCOME_TAX,
            rate_change=-0.01,
            affected_income_threshold=0,
            affected_taxpayers_millions=150.0,
            avg_taxable_income_in_bracket=60_000,
        )
        result = policy.estimate_static_revenue_effect(
            baseline_revenue=2000, use_real_data=False
        )
        expected = -0.01 * 60_000 * 150e6 / 1e9
        assert result == pytest.approx(expected, rel=1e-6)


# =============================================================================
# TaxPolicy.estimate_behavioral_offset
# =============================================================================

class TestTaxPolicyBehavioralOffset:
    def test_sign_matches_static_for_tax_increase(self, bracket_tax_policy):
        """Offset has the same sign as static effect (positive on a tax increase)."""
        offset = bracket_tax_policy.estimate_behavioral_offset(static_effect=37.0)
        assert offset > 0

    def test_sign_matches_static_for_tax_cut(self, bracket_tax_policy):
        """Offset is negative when static revenue is negative (tax cut), so the
        engine's ``static_deficit + behavioral`` recovers some revenue rather
        than amplifying the cost."""
        offset = bracket_tax_policy.estimate_behavioral_offset(static_effect=-37.0)
        assert offset < 0

    def test_proportional_to_eti(self):
        """Offset scales with ETI."""
        policy_low = TaxPolicy(
            name="LowETI", description="", policy_type=PolicyType.INCOME_TAX,
            taxable_income_elasticity=0.1,
        )
        policy_high = TaxPolicy(
            name="HighETI", description="", policy_type=PolicyType.INCOME_TAX,
            taxable_income_elasticity=0.5,
        )
        offset_low = policy_low.estimate_behavioral_offset(100.0)
        offset_high = policy_high.estimate_behavioral_offset(100.0)
        assert offset_high / offset_low == pytest.approx(5.0)

    def test_formula_value(self):
        """offset = static * ETI * 0.5 (signed)."""
        policy = TaxPolicy(
            name="T", description="", policy_type=PolicyType.INCOME_TAX,
            taxable_income_elasticity=0.25,
        )
        assert policy.estimate_behavioral_offset(-50.0) == pytest.approx(-50.0 * 0.25 * 0.5)
        assert policy.estimate_behavioral_offset(50.0) == pytest.approx(50.0 * 0.25 * 0.5)


# =============================================================================
# CapitalGainsPolicy.get_elasticity_for_year
# =============================================================================

class TestCapitalGainsElasticity:
    def test_year_zero_short_run(self, cap_gains_policy):
        """Year 0 returns short-run elasticity."""
        e = cap_gains_policy.get_elasticity_for_year(0)
        assert e == pytest.approx(0.8)

    def test_year_at_or_beyond_transition_long_run(self, cap_gains_policy):
        """Year >= transition_years returns long-run elasticity."""
        e3 = cap_gains_policy.get_elasticity_for_year(3)
        e5 = cap_gains_policy.get_elasticity_for_year(5)
        assert e3 == pytest.approx(0.4)
        assert e5 == pytest.approx(0.4)

    def test_interpolation_midpoint(self, cap_gains_policy):
        """Year 1 with transition_years=3: weight=1/3, e = 0.8*2/3 + 0.4*1/3."""
        e = cap_gains_policy.get_elasticity_for_year(1)
        expected = 0.8 * (2 / 3) + 0.4 * (1 / 3)
        assert e == pytest.approx(expected, rel=1e-6)

    def test_step_up_multiplier_applied(self):
        """When step_up_at_death=True, elasticity is multiplied by lock-in multiplier."""
        policy = CapitalGainsPolicy(
            name="StepUp", description="", policy_type=PolicyType.CAPITAL_GAINS_TAX,
            rate_change=0.05,
            baseline_capital_gains_rate=0.20,
            baseline_realizations_billions=1000.0,
            step_up_at_death=True,
            eliminate_step_up=False,
            step_up_lock_in_multiplier=2.0,
        )
        e = policy.get_elasticity_for_year(0)
        assert e == pytest.approx(0.8 * 2.0)


# =============================================================================
# CapitalGainsPolicy.estimate_static_revenue_effect
# =============================================================================

class TestCapitalGainsStaticRevenue:
    def test_basic_calculation(self, cap_gains_policy):
        """static = (tau1 - tau0) * R0"""
        result = cap_gains_policy.estimate_static_revenue_effect(
            baseline_revenue=0, use_real_data=False
        )
        expected = (0.25 - 0.20) * 1000.0  # 50 B
        assert result == pytest.approx(expected)

    def test_rate_decrease(self):
        """Negative rate_change produces negative static effect."""
        policy = CapitalGainsPolicy(
            name="Cut", description="", policy_type=PolicyType.CAPITAL_GAINS_TAX,
            rate_change=-0.05,
            baseline_capital_gains_rate=0.20,
            baseline_realizations_billions=800.0,
            step_up_at_death=False,
        )
        result = policy.estimate_static_revenue_effect(0, use_real_data=False)
        assert result == pytest.approx(-0.05 * 800.0)


# =============================================================================
# CapitalGainsPolicy.estimate_behavioral_offset
# =============================================================================

class TestCapitalGainsBehavioralOffset:
    def test_rate_increase_positive_offset(self, cap_gains_policy):
        """Rate increase causes deferral -> positive offset (lost revenue)."""
        static = cap_gains_policy.estimate_static_revenue_effect(0, use_real_data=False)
        offset = cap_gains_policy.estimate_behavioral_offset(static, years_since_start=0)
        assert offset > 0

    def test_offset_larger_in_short_run(self, cap_gains_policy):
        """Short-run elasticity is higher, so offset should be larger."""
        static = cap_gains_policy.estimate_static_revenue_effect(0, use_real_data=False)
        offset_yr0 = cap_gains_policy.estimate_behavioral_offset(static, years_since_start=0)
        offset_yr5 = cap_gains_policy.estimate_behavioral_offset(static, years_since_start=5)
        assert offset_yr0 > offset_yr5


# =============================================================================
# CapitalGainsPolicy.estimate_step_up_elimination_revenue
# =============================================================================

class TestStepUpEliminationRevenue:
    def test_no_elimination_returns_zero(self, cap_gains_policy):
        assert cap_gains_policy.estimate_step_up_elimination_revenue() == 0.0

    def test_elimination_returns_positive(self):
        policy = CapitalGainsPolicy(
            name="Eliminate StepUp", description="",
            policy_type=PolicyType.CAPITAL_GAINS_TAX,
            rate_change=0.05,
            baseline_capital_gains_rate=0.20,
            baseline_realizations_billions=1000.0,
            eliminate_step_up=True,
            step_up_exemption=1_000_000,
            gains_at_death_billions=54.0,
            step_up_at_death=True,
        )
        rev = policy.estimate_step_up_elimination_revenue()
        # tau1 = 0.25, exemption_share = min(0.9, 0.4*1) = 0.4
        # taxable = 54 * (1 - 0.4) = 32.4, rev = 0.25 * 32.4 = 8.1
        assert rev == pytest.approx(0.25 * 54.0 * 0.6)
        assert rev > 0

    def test_zero_exemption_taxes_all_gains(self):
        policy = CapitalGainsPolicy(
            name="No Exempt", description="",
            policy_type=PolicyType.CAPITAL_GAINS_TAX,
            rate_change=0.0,
            new_rate=0.25,
            baseline_capital_gains_rate=0.20,
            baseline_realizations_billions=1000.0,
            eliminate_step_up=True,
            step_up_exemption=0,
            gains_at_death_billions=54.0,
        )
        rev = policy.estimate_step_up_elimination_revenue()
        assert rev == pytest.approx(0.25 * 54.0)


# =============================================================================
# SpendingPolicy.get_spending_in_year
# =============================================================================

class TestSpendingPolicyGetSpendingInYear:
    def test_active_year(self, spending_policy):
        """In start year, returns base amount * phase_in."""
        result = spending_policy.get_spending_in_year(2025)
        assert result == pytest.approx(50.0)

    def test_inactive_year(self, spending_policy):
        """Before start returns 0."""
        assert spending_policy.get_spending_in_year(2024) == 0.0

    def test_one_time_spending(self):
        policy = SpendingPolicy(
            name="OneTime", description="", policy_type=PolicyType.INFRASTRUCTURE,
            start_year=2025, duration_years=10,
            annual_spending_change_billions=100.0,
            is_one_time=True,
        )
        assert policy.get_spending_in_year(2025) == pytest.approx(100.0)
        assert policy.get_spending_in_year(2026) == 0.0

    def test_growth_rate(self, spending_policy):
        """Year 2 should include growth: 50 * (1.02)^1."""
        result = spending_policy.get_spending_in_year(2026)
        expected = 50.0 * 1.02
        assert result == pytest.approx(expected, rel=1e-6)

    def test_sunset_inactive(self):
        policy = SpendingPolicy(
            name="Sunset", description="", policy_type=PolicyType.INFRASTRUCTURE,
            start_year=2025, duration_years=3, sunset=True,
            annual_spending_change_billions=10.0,
        )
        assert policy.get_spending_in_year(2028) == 0.0


# =============================================================================
# TransferPolicy.estimate_cost_effect
# =============================================================================

class TestTransferPolicyCostEffect:
    def test_benefit_change_percent(self, transfer_policy):
        """Cost effect includes benefit_change_percent * baseline."""
        result = transfer_policy.estimate_cost_effect(baseline_cost=1000.0)
        # benefit_change_percent=0.05 => 50 B from percent change
        # new_beneficiaries=2.0, avg_benefit = 1000/60 => ~33.33 B
        pct_effect = 1000.0 * 0.05
        new_ben_effect = (1000.0 / 60) * 2.0
        assert result == pytest.approx(pct_effect + new_ben_effect, rel=1e-4)

    def test_override_cost(self):
        policy = TransferPolicy(
            name="Override", description="",
            policy_type=PolicyType.SOCIAL_SECURITY,
            annual_cost_change_billions=75.0,
        )
        assert policy.estimate_cost_effect(baseline_cost=1000.0) == 75.0


# =============================================================================
# PolicyPackage
# =============================================================================

class TestPolicyPackage:
    def test_get_all_years_empty(self):
        pkg = PolicyPackage(name="Empty", description="")
        assert pkg.get_all_years() == (2025, 2034)

    def test_get_all_years_with_policies(self, bracket_tax_policy, spending_policy):
        pkg = PolicyPackage(name="Pkg", description="")
        pkg.add_policy(bracket_tax_policy)
        pkg.add_policy(spending_policy)
        start, end = pkg.get_all_years()
        assert start == 2025
        assert end == 2035

    def test_get_active_policies(self):
        p1 = Policy(
            name="A", description="", policy_type=PolicyType.INCOME_TAX,
            start_year=2025, duration_years=3, sunset=True,
        )
        p2 = Policy(
            name="B", description="", policy_type=PolicyType.INCOME_TAX,
            start_year=2028, duration_years=5, sunset=True,
        )
        pkg = PolicyPackage(name="Mix", description="", policies=[p1, p2])
        assert len(pkg.get_active_policies(2026)) == 1
        assert pkg.get_active_policies(2026)[0].name == "A"
        assert len(pkg.get_active_policies(2029)) == 1
        assert pkg.get_active_policies(2029)[0].name == "B"
        # Both inactive
        assert len(pkg.get_active_policies(2040)) == 0


# =============================================================================
# Convenience factory functions
# =============================================================================

class TestConvenienceFunctions:
    def test_create_income_tax_cut(self):
        policy = create_income_tax_cut(
            name="TopCut", rate_reduction=0.03, income_threshold=500_000,
            start_year=2026, duration=5, affected_millions=1.0,
        )
        assert isinstance(policy, TaxPolicy)
        assert policy.rate_change == pytest.approx(-0.03)
        assert policy.affected_income_threshold == 500_000
        assert policy.start_year == 2026
        assert policy.duration_years == 5
        assert policy.affected_taxpayers_millions == 1.0

    def test_create_new_tax_credit(self):
        policy = create_new_tax_credit(
            name="Family", amount=2000, refundable=True,
            affected_millions=40.0, start_year=2025, duration=10,
        )
        assert isinstance(policy, TaxPolicy)
        assert policy.credit_amount == 2000
        assert policy.credit_refundable is True
        assert policy.affected_taxpayers_millions == 40.0
        assert policy.policy_type == PolicyType.TAX_CREDIT

    def test_create_spending_increase(self):
        policy = create_spending_increase(
            name="Infra", annual_billions=50, category="nondefense",
            start_year=2025, duration=10, multiplier=1.5,
        )
        assert isinstance(policy, SpendingPolicy)
        assert policy.annual_spending_change_billions == 50
        assert policy.gdp_multiplier == 1.5
        assert policy.policy_type == PolicyType.DISCRETIONARY_NONDEFENSE

    def test_create_spending_increase_defense(self):
        policy = create_spending_increase(
            name="Defense", annual_billions=30, category="defense",
        )
        assert policy.policy_type == PolicyType.DISCRETIONARY_DEFENSE

    def test_create_spending_increase_mandatory(self):
        policy = create_spending_increase(
            name="Mandatory", annual_billions=20, category="mandatory",
        )
        assert policy.policy_type == PolicyType.MANDATORY_SPENDING
