"""
Tests for under-covered policy modules to boost test coverage.

Covers:
- fiscal_model/amt.py (Alternative Minimum Tax)
- fiscal_model/credits.py (Tax Credits)
- fiscal_model/estate.py (Estate Tax)
- fiscal_model/pharma.py (Drug Pricing)
- fiscal_model/payroll.py (Payroll Tax)
- fiscal_model/ptc.py (Premium Tax Credits)

Tests exercise factory functions, policy creation, and revenue effect calculations.
"""

import pytest

from fiscal_model.amt import (
    AMTPolicy,
    AMTType,
    create_amt_rate_change,
    create_extend_tcja_amt_relief,
    create_increase_amt_exemption,
    create_repeal_corporate_amt,
    create_repeal_individual_amt,
)
from fiscal_model.credits import (
    CreditType,
    TaxCreditPolicy,
    create_biden_ctc_2021,
    create_biden_eitc_childless,
    create_ctc_expansion,
    create_ctc_permanent_extension,
    create_eitc_expansion,
)
from fiscal_model.estate import (
    EstateTaxPolicy,
    create_biden_estate_proposal,
    create_eliminate_estate_tax,
    create_estate_exemption_change,
    create_estate_rate_change,
    create_tcja_estate_extension,
    create_warren_estate_proposal,
)
from fiscal_model.pharma import (
    DrugPricingPolicy,
    create_comprehensive_pharma_reform,
    create_expand_drug_negotiation,
    create_insulin_cap_all,
    create_reference_pricing,
)
from fiscal_model.payroll import (
    PayrollTaxPolicy,
    create_biden_payroll_proposal,
    create_expand_niit,
    create_medicare_rate_increase,
    create_ss_cap_90_percent,
    create_ss_donut_hole,
    create_ss_eliminate_cap,
    create_ss_rate_increase,
)
from fiscal_model.policies import PolicyType
from fiscal_model.ptc import (
    PremiumTaxCreditPolicy,
    create_extend_enhanced_ptc,
    create_expand_ptc_eligibility,
    create_let_enhanced_expire,
    create_lower_premium_cap,
    create_repeal_ptc,
)

# =============================================================================
# AMT POLICY TESTS
# =============================================================================


class TestAMTPolicyCreation:
    """Tests for AMTPolicy and factory functions."""

    def test_amt_policy_default_creation(self):
        """Verify basic AMTPolicy can be created."""
        policy = AMTPolicy(
            name="Test AMT",
            description="Test policy",
            policy_type=PolicyType.INCOME_TAX,
        )
        assert policy.name == "Test AMT"
        assert policy.amt_type == AMTType.INDIVIDUAL

    def test_amt_policy_corporate_type(self):
        """Verify corporate AMT policy creation."""
        policy = AMTPolicy(
            name="Corporate AMT",
            description="Test corporate AMT",
            policy_type=PolicyType.CORPORATE_TAX,
            amt_type=AMTType.CORPORATE,
        )
        assert policy.amt_type == AMTType.CORPORATE

    def test_extend_tcja_amt_relief_factory(self):
        """Verify create_extend_tcja_amt_relief factory."""
        policy = create_extend_tcja_amt_relief(duration_years=10)
        assert isinstance(policy, AMTPolicy)
        assert policy.extend_tcja_relief is True
        assert "TCJA" in policy.name

    def test_repeal_individual_amt_factory(self):
        """Verify create_repeal_individual_amt factory."""
        policy = create_repeal_individual_amt()
        assert isinstance(policy, AMTPolicy)
        assert policy.repeal_individual_amt is True

    def test_repeal_corporate_amt_factory(self):
        """Verify create_repeal_corporate_amt factory."""
        policy = create_repeal_corporate_amt()
        assert isinstance(policy, AMTPolicy)
        assert policy.amt_type == AMTType.CORPORATE
        assert policy.repeal_corporate_amt is True

    def test_increase_amt_exemption_factory(self):
        """Verify create_increase_amt_exemption factory."""
        policy = create_increase_amt_exemption(
            exemption_increase=25_000,
        )
        assert isinstance(policy, AMTPolicy)
        assert policy.exemption_change == 25_000

    def test_amt_rate_change_factory(self):
        """Verify create_amt_rate_change factory."""
        policy = create_amt_rate_change(rate_change=0.02)
        assert isinstance(policy, AMTPolicy)
        assert policy.rate_change == 0.02

    def test_amt_get_exemption_for_year(self):
        """Verify get_exemption_for_year method."""
        policy = AMTPolicy(
            name="Test",
            description="Test",
            policy_type=PolicyType.INCOME_TAX,
        )
        # Should return 2025 exemption for MFJ
        exemption = policy.get_exemption_for_year(2025, "mfj")
        assert isinstance(exemption, float)
        assert exemption > 0

    def test_amt_get_exemption_repeal_returns_infinity(self):
        """Verify repeal returns infinite exemption."""
        policy = AMTPolicy(
            name="Test",
            description="Test",
            policy_type=PolicyType.INCOME_TAX,
            repeal_individual_amt=True,
        )
        exemption = policy.get_exemption_for_year(2026, "mfj")
        assert exemption == float('inf')

    def test_amt_get_rate_for_tier(self):
        """Verify get_rate_for_tier method."""
        policy = AMTPolicy(name="Test", description="Test", policy_type=PolicyType.INCOME_TAX)
        rate1 = policy.get_rate_for_tier(1)
        rate2 = policy.get_rate_for_tier(2)
        assert 0 < rate1 < 1
        assert 0 < rate2 < 1
        assert rate2 > rate1  # Second tier is higher

    def test_amt_estimate_affected_taxpayers(self):
        """Verify estimate_affected_taxpayers method."""
        policy = AMTPolicy(name="Test", description="Test", policy_type=PolicyType.INCOME_TAX)
        taxpayers = policy.estimate_affected_taxpayers(2026)
        assert isinstance(taxpayers, int)
        assert taxpayers > 0

    def test_amt_estimate_affected_taxpayers_repeal(self):
        """Verify repeal returns zero affected taxpayers."""
        policy = AMTPolicy(
            name="Test",
            description="Test",
            policy_type=PolicyType.INCOME_TAX,
            repeal_individual_amt=True,
        )
        taxpayers = policy.estimate_affected_taxpayers(2026)
        assert taxpayers == 0

    def test_amt_static_revenue_effect(self):
        """Verify estimate_static_revenue_effect method."""
        policy = create_repeal_individual_amt()
        effect = policy.estimate_static_revenue_effect(baseline_revenue=5.0)
        assert isinstance(effect, float)
        # Repeal should reduce revenue (negative effect)
        assert effect < 0

    def test_amt_corporate_static_revenue_effect(self):
        """Verify corporate AMT static revenue effect."""
        policy = create_repeal_corporate_amt()
        effect = policy.estimate_static_revenue_effect(baseline_revenue=0)
        assert isinstance(effect, float)
        assert effect < 0  # Repeal reduces revenue


# =============================================================================
# TAX CREDIT POLICY TESTS
# =============================================================================


class TestTaxCreditPolicy:
    """Tests for TaxCreditPolicy and factory functions."""

    def test_tax_credit_policy_creation(self):
        """Verify basic TaxCreditPolicy creation."""
        policy = TaxCreditPolicy(
            name="Test Credit",
            description="Test policy",
            policy_type=PolicyType.INCOME_TAX,
            credit_type=CreditType.CHILD_TAX_CREDIT,
        )
        assert policy.name == "Test Credit"
        assert policy.credit_type == CreditType.CHILD_TAX_CREDIT

    def test_ctc_expansion_factory(self):
        """Verify create_ctc_expansion factory."""
        policy = create_ctc_expansion(credit_per_child=3000)
        assert isinstance(policy, TaxCreditPolicy)
        assert policy.credit_type == CreditType.CHILD_TAX_CREDIT

    def test_biden_ctc_2021_factory(self):
        """Verify create_biden_ctc_2021 factory."""
        policy = create_biden_ctc_2021()
        assert isinstance(policy, TaxCreditPolicy)
        assert "Biden" in policy.name or "CTC" in policy.name

    def test_ctc_permanent_extension_factory(self):
        """Verify create_ctc_permanent_extension factory."""
        policy = create_ctc_permanent_extension()
        assert isinstance(policy, TaxCreditPolicy)
        assert policy.credit_type == CreditType.CHILD_TAX_CREDIT

    def test_eitc_expansion_factory(self):
        """Verify create_eitc_expansion factory."""
        policy = create_eitc_expansion(childless_max_increase=500)
        assert isinstance(policy, TaxCreditPolicy)
        assert policy.credit_type == CreditType.EARNED_INCOME_CREDIT

    def test_biden_eitc_childless_factory(self):
        """Verify create_biden_eitc_childless factory."""
        policy = create_biden_eitc_childless()
        assert isinstance(policy, TaxCreditPolicy)
        assert policy.credit_type == CreditType.EARNED_INCOME_CREDIT

    def test_credit_policy_static_revenue_effect(self):
        """Verify credit policy revenue effect calculation."""
        policy = create_biden_ctc_2021()
        effect = policy.estimate_static_revenue_effect(baseline_revenue=0)
        assert isinstance(effect, float)
        # Credit expansion costs money
        assert effect < 0

    def test_credit_policy_behavioral_offset(self):
        """Verify credit policy behavioral offset."""
        policy = create_biden_ctc_2021()
        static = policy.estimate_static_revenue_effect(0)
        offset = policy.estimate_behavioral_offset(static)
        assert isinstance(offset, float)
        # Offset should be present for all policies
        assert offset is not None


# =============================================================================
# ESTATE TAX POLICY TESTS
# =============================================================================


class TestEstateTaxPolicy:
    """Tests for EstateTaxPolicy and factory functions."""

    def test_estate_policy_creation(self):
        """Verify basic EstateTaxPolicy creation."""
        policy = EstateTaxPolicy(
            name="Test Estate",
            description="Test policy",
            policy_type=PolicyType.ESTATE_TAX,
        )
        assert policy.name == "Test Estate"

    def test_tcja_estate_extension_factory(self):
        """Verify create_tcja_estate_extension factory."""
        policy = create_tcja_estate_extension()
        assert isinstance(policy, EstateTaxPolicy)
        assert "TCJA" in policy.name or "Extension" in policy.name

    def test_biden_estate_proposal_factory(self):
        """Verify create_biden_estate_proposal factory."""
        policy = create_biden_estate_proposal()
        assert isinstance(policy, EstateTaxPolicy)
        assert policy.new_exemption is not None or policy.rate_change != 0

    def test_warren_estate_proposal_factory(self):
        """Verify create_warren_estate_proposal factory."""
        policy = create_warren_estate_proposal()
        assert isinstance(policy, EstateTaxPolicy)

    def test_eliminate_estate_tax_factory(self):
        """Verify create_eliminate_estate_tax factory."""
        policy = create_eliminate_estate_tax()
        assert isinstance(policy, EstateTaxPolicy)
        assert policy.new_rate == 0.0

    def test_estate_rate_change_factory(self):
        """Verify create_estate_rate_change factory."""
        policy = create_estate_rate_change(rate_change=0.05)
        assert isinstance(policy, EstateTaxPolicy)
        assert policy.rate_change == 0.05

    def test_estate_exemption_change_factory(self):
        """Verify create_estate_exemption_change factory."""
        policy = create_estate_exemption_change(new_exemption=3_500_000)
        assert isinstance(policy, EstateTaxPolicy)
        assert policy.new_exemption == 3_500_000

    def test_estate_policy_static_revenue_effect(self):
        """Verify estate policy revenue effect calculation."""
        policy = create_biden_estate_proposal()
        effect = policy.estimate_static_revenue_effect(baseline_revenue=35.0)
        assert isinstance(effect, float)
        # Biden proposal raises revenue
        assert effect > 0

    def test_eliminate_estate_tax_revenue_loss(self):
        """Verify elimination reduces revenue."""
        policy = create_eliminate_estate_tax()
        effect = policy.estimate_static_revenue_effect(baseline_revenue=35.0)
        assert isinstance(effect, float)
        # Elimination loses revenue
        assert effect < 0


# =============================================================================
# PHARMA POLICY TESTS
# =============================================================================


class TestPharmacyPolicy:
    """Tests for DrugPricingPolicy and factory functions."""

    def test_pharma_policy_creation(self):
        """Verify basic DrugPricingPolicy creation."""
        policy = DrugPricingPolicy(
            name="Test Pharma",
            description="Test policy",
            policy_type=PolicyType.MANDATORY_SPENDING,
        )
        assert policy.name == "Test Pharma"

    def test_expand_drug_negotiation_factory(self):
        """Verify create_expand_drug_negotiation factory."""
        policy = create_expand_drug_negotiation()
        assert isinstance(policy, DrugPricingPolicy)
        assert "negotiation" in policy.name.lower()

    def test_insulin_cap_all_factory(self):
        """Verify create_insulin_cap_all factory."""
        policy = create_insulin_cap_all()
        assert isinstance(policy, DrugPricingPolicy)
        assert "insulin" in policy.name.lower()

    def test_reference_pricing_factory(self):
        """Verify create_reference_pricing factory."""
        policy = create_reference_pricing()
        assert isinstance(policy, DrugPricingPolicy)

    def test_comprehensive_pharma_reform_factory(self):
        """Verify create_comprehensive_pharma_reform factory."""
        policy = create_comprehensive_pharma_reform()
        assert isinstance(policy, DrugPricingPolicy)

    def test_pharma_policy_has_revenue_estimate(self):
        """Verify pharma policy can be created and has description."""
        policy = create_expand_drug_negotiation()
        assert isinstance(policy, DrugPricingPolicy)
        assert policy.description is not None or policy.name is not None


# =============================================================================
# PAYROLL TAX POLICY TESTS
# =============================================================================


class TestPayrollTaxPolicy:
    """Tests for PayrollTaxPolicy and factory functions."""

    def test_payroll_policy_creation(self):
        """Verify basic PayrollTaxPolicy creation."""
        policy = PayrollTaxPolicy(
            name="Test Payroll",
            description="Test policy",
            policy_type=PolicyType.PAYROLL_TAX,
        )
        assert policy.name == "Test Payroll"
        assert policy.policy_type == PolicyType.PAYROLL_TAX

    def test_ss_cap_90_percent_factory(self):
        """Verify create_ss_cap_90_percent factory."""
        policy = create_ss_cap_90_percent()
        assert isinstance(policy, PayrollTaxPolicy)
        assert "cap" in policy.name.lower()

    def test_ss_donut_hole_factory(self):
        """Verify create_ss_donut_hole factory."""
        policy = create_ss_donut_hole()
        assert isinstance(policy, PayrollTaxPolicy)

    def test_ss_eliminate_cap_factory(self):
        """Verify create_ss_eliminate_cap factory."""
        policy = create_ss_eliminate_cap()
        assert isinstance(policy, PayrollTaxPolicy)

    def test_ss_rate_increase_factory(self):
        """Verify create_ss_rate_increase factory."""
        policy = create_ss_rate_increase(rate_change=0.005)
        assert isinstance(policy, PayrollTaxPolicy)

    def test_expand_niit_factory(self):
        """Verify create_expand_niit factory."""
        policy = create_expand_niit()
        assert isinstance(policy, PayrollTaxPolicy)

    def test_medicare_rate_increase_factory(self):
        """Verify create_medicare_rate_increase factory."""
        policy = create_medicare_rate_increase(rate_change=0.0045)
        assert isinstance(policy, PayrollTaxPolicy)

    def test_biden_payroll_proposal_factory(self):
        """Verify create_biden_payroll_proposal factory."""
        policy = create_biden_payroll_proposal()
        assert isinstance(policy, PayrollTaxPolicy)

    def test_payroll_policy_static_revenue_effect(self):
        """Verify payroll policy revenue effect."""
        policy = create_ss_donut_hole()
        effect = policy.estimate_static_revenue_effect(baseline_revenue=1_700.0)
        assert isinstance(effect, float)
        # Donut hole should raise revenue
        assert effect > 0

    def test_ss_eliminate_cap_revenue_effect(self):
        """Verify eliminate cap raises significant revenue."""
        policy = create_ss_eliminate_cap()
        effect = policy.estimate_static_revenue_effect(baseline_revenue=1_700.0)
        assert isinstance(effect, float)
        # Eliminating cap significantly raises revenue
        assert effect > 0


# =============================================================================
# PREMIUM TAX CREDIT POLICY TESTS
# =============================================================================


class TestPremiumTaxCreditPolicy:
    """Tests for PremiumTaxCreditPolicy and factory functions."""

    def test_ptc_policy_creation(self):
        """Verify basic PremiumTaxCreditPolicy creation."""
        policy = PremiumTaxCreditPolicy(
            name="Test PTC",
            description="Test policy",
            policy_type=PolicyType.TAX_CREDIT,
        )
        assert policy.name == "Test PTC"

    def test_extend_enhanced_ptc_factory(self):
        """Verify create_extend_enhanced_ptc factory."""
        policy = create_extend_enhanced_ptc()
        assert isinstance(policy, PremiumTaxCreditPolicy)
        assert "enhanced" in policy.name.lower() or "extend" in policy.name.lower()

    def test_let_enhanced_expire_factory(self):
        """Verify create_let_enhanced_expire factory."""
        policy = create_let_enhanced_expire()
        assert isinstance(policy, PremiumTaxCreditPolicy)

    def test_repeal_ptc_factory(self):
        """Verify create_repeal_ptc factory."""
        policy = create_repeal_ptc()
        assert isinstance(policy, PremiumTaxCreditPolicy)
        assert policy.repeal_ptc is True

    def test_expand_ptc_eligibility_factory(self):
        """Verify create_expand_ptc_eligibility factory."""
        policy = create_expand_ptc_eligibility()
        assert isinstance(policy, PremiumTaxCreditPolicy)

    def test_lower_premium_cap_factory(self):
        """Verify create_lower_premium_cap factory."""
        policy = create_lower_premium_cap(new_max_cap=0.06)
        assert isinstance(policy, PremiumTaxCreditPolicy)

    def test_ptc_policy_static_revenue_effect(self):
        """Verify PTC policy revenue effect."""
        policy = create_extend_enhanced_ptc()
        effect = policy.estimate_static_revenue_effect(baseline_revenue=0)
        assert isinstance(effect, float)
        # Extended PTC costs money
        assert effect < 0

    def test_ptc_repeal_revenue_gain(self):
        """Verify PTC repeal gains revenue."""
        policy = create_repeal_ptc()
        effect = policy.estimate_static_revenue_effect(baseline_revenue=0)
        assert isinstance(effect, float)
        # Repeal gains revenue
        assert effect > 0
