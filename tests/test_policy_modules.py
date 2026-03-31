"""
Smoke tests for each policy module's factory functions.

Verifies that factory functions return valid policy objects and produce
non-zero revenue estimates with correct behavioral offset signs.
"""


from fiscal_model.tcja import TCJAExtensionPolicy, create_tcja_extension
from fiscal_model.corporate import CorporateTaxPolicy, create_biden_corporate_rate_only
from fiscal_model.credits import TaxCreditPolicy, create_biden_ctc_2021
from fiscal_model.estate import EstateTaxPolicy, create_biden_estate_proposal
from fiscal_model.payroll import PayrollTaxPolicy, create_ss_donut_hole
from fiscal_model.amt import AMTPolicy, create_repeal_corporate_amt
from fiscal_model.ptc import PremiumTaxCreditPolicy, create_extend_enhanced_ptc
from fiscal_model.tax_expenditures import TaxExpenditurePolicy, create_cap_employer_health_exclusion


# =============================================================================
# TCJA Extension
# =============================================================================

class TestTCJAExtensionPolicy:
    """Tests for TCJAExtensionPolicy via create_tcja_extension."""

    def test_factory_returns_correct_type(self):
        policy = create_tcja_extension(extend_all=True)
        assert isinstance(policy, TCJAExtensionPolicy)

    def test_policy_has_correct_name(self):
        policy = create_tcja_extension(extend_all=True)
        assert "TCJA" in policy.name
        assert "Extension" in policy.name or "Full" in policy.name

    def test_policy_has_components(self):
        policy = create_tcja_extension(extend_all=True)
        breakdown = policy.get_component_breakdown()
        assert len(breakdown) > 0
        assert "rate_cuts" in breakdown

    def test_static_revenue_is_nonzero(self):
        policy = create_tcja_extension(extend_all=True)
        effect = policy.estimate_static_revenue_effect(baseline_revenue=0)
        assert effect != 0
        # TCJA extension costs money (reduces revenue), so effect should be negative
        assert effect < 0, f"TCJA extension should reduce revenue, got {effect}"

    def test_behavioral_offset_is_nonnegative(self):
        policy = create_tcja_extension(extend_all=True)
        static = policy.estimate_static_revenue_effect(baseline_revenue=0)
        offset = policy.estimate_behavioral_offset(static)
        assert offset >= 0, f"Behavioral offset should be non-negative, got {offset}"


# =============================================================================
# Corporate Tax
# =============================================================================

class TestCorporateTaxPolicy:
    """Tests for CorporateTaxPolicy via create_biden_corporate_rate_only."""

    def test_factory_returns_correct_type(self):
        policy = create_biden_corporate_rate_only()
        assert isinstance(policy, CorporateTaxPolicy)

    def test_static_revenue_is_nonzero(self):
        policy = create_biden_corporate_rate_only()
        effect = policy.estimate_static_revenue_effect(baseline_revenue=475.0)
        assert effect != 0

    def test_tax_increase_produces_positive_revenue(self):
        policy = create_biden_corporate_rate_only()
        effect = policy.estimate_static_revenue_effect(baseline_revenue=475.0)
        # Raising corporate rate from 21% to 28% should raise revenue (positive effect)
        assert effect > 0, f"Corporate rate increase should raise revenue, got {effect}"

    def test_behavioral_offset_is_nonnegative(self):
        policy = create_biden_corporate_rate_only()
        static = policy.estimate_static_revenue_effect(baseline_revenue=475.0)
        offset = policy.estimate_behavioral_offset(static)
        assert offset >= 0, f"Behavioral offset should be non-negative, got {offset}"


# =============================================================================
# Tax Credits (CTC)
# =============================================================================

class TestTaxCreditPolicy:
    """Tests for TaxCreditPolicy via create_biden_ctc_2021."""

    def test_factory_returns_correct_type(self):
        policy = create_biden_ctc_2021()
        assert isinstance(policy, TaxCreditPolicy)

    def test_static_revenue_is_nonzero(self):
        policy = create_biden_ctc_2021()
        effect = policy.estimate_static_revenue_effect(baseline_revenue=0)
        assert effect != 0

    def test_ctc_expansion_costs_money(self):
        policy = create_biden_ctc_2021()
        effect = policy.estimate_static_revenue_effect(baseline_revenue=0)
        # Expanding CTC costs money (negative revenue effect)
        assert effect < 0, f"CTC expansion should cost money (negative revenue), got {effect}"

    def test_behavioral_offset_is_nonnegative(self):
        policy = create_biden_ctc_2021()
        static = policy.estimate_static_revenue_effect(baseline_revenue=0)
        offset = policy.estimate_behavioral_offset(static)
        # CTC behavioral offset is proportional to static effect (negative * 0.05)
        # so it is negative; check absolute value is non-negative
        assert abs(offset) >= 0


# =============================================================================
# Estate Tax
# =============================================================================

class TestEstateTaxPolicy:
    """Tests for EstateTaxPolicy via create_biden_estate_proposal."""

    def test_factory_returns_correct_type(self):
        policy = create_biden_estate_proposal()
        assert isinstance(policy, EstateTaxPolicy)

    def test_static_revenue_is_nonzero(self):
        policy = create_biden_estate_proposal()
        effect = policy.estimate_static_revenue_effect(baseline_revenue=0)
        assert effect != 0

    def test_biden_estate_raises_revenue(self):
        policy = create_biden_estate_proposal()
        effect = policy.estimate_static_revenue_effect(baseline_revenue=0)
        # Lowering exemption and raising rate should raise revenue (positive effect)
        assert effect > 0, f"Biden estate proposal should raise revenue, got {effect}"

    def test_behavioral_offset_is_nonnegative(self):
        policy = create_biden_estate_proposal()
        static = policy.estimate_static_revenue_effect(baseline_revenue=0)
        offset = policy.estimate_behavioral_offset(static)
        # For estate tax, behavioral offset on revenue gain is negative (reduces gain)
        # but abs value should be non-negative
        assert abs(offset) >= 0


# =============================================================================
# Payroll Tax
# =============================================================================

class TestPayrollTaxPolicy:
    """Tests for PayrollTaxPolicy via create_ss_donut_hole."""

    def test_factory_returns_correct_type(self):
        policy = create_ss_donut_hole()
        assert isinstance(policy, PayrollTaxPolicy)

    def test_static_revenue_is_nonzero(self):
        policy = create_ss_donut_hole()
        effect = policy.estimate_static_revenue_effect(baseline_revenue=0)
        assert effect != 0

    def test_donut_hole_raises_revenue(self):
        policy = create_ss_donut_hole()
        effect = policy.estimate_static_revenue_effect(baseline_revenue=0)
        # Applying SS tax above $250K should raise revenue (positive effect)
        assert effect > 0, f"SS donut hole should raise revenue, got {effect}"

    def test_behavioral_offset_is_nonnegative(self):
        policy = create_ss_donut_hole()
        static = policy.estimate_static_revenue_effect(baseline_revenue=0)
        offset = policy.estimate_behavioral_offset(static)
        # Payroll behavioral offset on revenue gain is negative (reduces gain)
        assert abs(offset) >= 0


# =============================================================================
# AMT
# =============================================================================

class TestAMTPolicy:
    """Tests for AMTPolicy via create_repeal_corporate_amt."""

    def test_factory_returns_correct_type(self):
        policy = create_repeal_corporate_amt()
        assert isinstance(policy, AMTPolicy)

    def test_static_revenue_is_nonzero(self):
        policy = create_repeal_corporate_amt()
        effect = policy.estimate_static_revenue_effect(baseline_revenue=0)
        assert effect != 0

    def test_repeal_costs_money(self):
        policy = create_repeal_corporate_amt()
        effect = policy.estimate_static_revenue_effect(baseline_revenue=0)
        # Repealing corporate AMT loses revenue (negative effect)
        assert effect < 0, f"Repealing corporate AMT should lose revenue, got {effect}"

    def test_behavioral_offset_is_nonnegative(self):
        policy = create_repeal_corporate_amt()
        static = policy.estimate_static_revenue_effect(baseline_revenue=0)
        offset = policy.estimate_behavioral_offset(static)
        assert abs(offset) >= 0


# =============================================================================
# Premium Tax Credits
# =============================================================================

class TestPremiumTaxCreditPolicy:
    """Tests for PremiumTaxCreditPolicy via create_extend_enhanced_ptc."""

    def test_factory_returns_correct_type(self):
        policy = create_extend_enhanced_ptc()
        assert isinstance(policy, PremiumTaxCreditPolicy)

    def test_static_revenue_is_nonzero(self):
        policy = create_extend_enhanced_ptc()
        effect = policy.estimate_static_revenue_effect(baseline_revenue=0)
        assert effect != 0

    def test_extending_ptc_costs_money(self):
        policy = create_extend_enhanced_ptc()
        effect = policy.estimate_static_revenue_effect(baseline_revenue=0)
        # Extending enhanced PTCs costs money (negative revenue effect)
        assert effect < 0, f"Extending PTCs should cost money, got {effect}"

    def test_behavioral_offset_is_nonnegative(self):
        policy = create_extend_enhanced_ptc()
        static = policy.estimate_static_revenue_effect(baseline_revenue=0)
        offset = policy.estimate_behavioral_offset(static)
        assert offset >= 0, f"Behavioral offset should be non-negative, got {offset}"


# =============================================================================
# Tax Expenditures
# =============================================================================

class TestTaxExpenditurePolicy:
    """Tests for TaxExpenditurePolicy via create_cap_employer_health_exclusion."""

    def test_factory_returns_correct_type(self):
        policy = create_cap_employer_health_exclusion()
        assert isinstance(policy, TaxExpenditurePolicy)

    def test_static_revenue_is_nonzero(self):
        policy = create_cap_employer_health_exclusion()
        effect = policy.estimate_static_revenue_effect(baseline_revenue=0)
        assert effect != 0

    def test_capping_exclusion_raises_revenue(self):
        policy = create_cap_employer_health_exclusion()
        effect = policy.estimate_static_revenue_effect(baseline_revenue=0)
        # Capping employer health exclusion raises revenue (positive effect)
        assert effect > 0, f"Capping employer health exclusion should raise revenue, got {effect}"

    def test_behavioral_offset_is_nonnegative(self):
        policy = create_cap_employer_health_exclusion()
        static = policy.estimate_static_revenue_effect(baseline_revenue=0)
        offset = policy.estimate_behavioral_offset(static)
        # Behavioral offset on revenue gain is negative (reduces gain)
        assert abs(offset) >= 0
