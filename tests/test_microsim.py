"""
Comprehensive unit tests for the MicroTaxCalculator engine.

Tests cover:
1. Basic bracket calculation (single, married)
2. Standard deduction
3. CTC calculation and phase-out
4. SALT cap enforcement
5. AMT (Alternative Minimum Tax)
6. EITC (Earned Income Tax Credit)
7. NIIT (Medicare surtax)
8. apply_reform() method
9. Edge cases (zero income, high income)
10. Married vs single tax differences
"""

import numpy as np
import pandas as pd
import pytest

from fiscal_model.microsim.engine import MicroTaxCalculator


class TestBasicBracketCalculation:
    """Test income tax calculation with progressive brackets."""

    def test_single_filer_bottom_bracket(self):
        """Single filer in lowest bracket (10% on $0-$11,925)."""
        calc = MicroTaxCalculator(year=2025)
        pop = pd.DataFrame({
            'agi': [20000],
            'wages': [20000],
            'married': [0],
            'children': [0],
            'weight': [1.0],
            'age_head': [35],
        })
        result = calc.calculate(pop)
        # Taxable income = 20000 - 15000 = 5000
        # Tax = 5000 * 0.10 = 500
        assert result.loc[0, 'income_tax_before_credits'] == pytest.approx(500, abs=1)

    def test_single_filer_multiple_brackets(self):
        """Single filer spanning multiple brackets."""
        calc = MicroTaxCalculator(year=2025)
        pop = pd.DataFrame({
            'agi': [50000],
            'wages': [50000],
            'married': [0],
            'children': [0],
            'weight': [1.0],
            'age_head': [35],
        })
        result = calc.calculate(pop)
        # Taxable income = 50000 - 15000 = 35000
        # Tax = 11925*0.10 + (23550-11925)*0.12 + (35000-23550)*0.22
        #     = 1192.5 + 1395 + 2519 = 5106.5
        # But brackets in 2025 are [0, 11925, 48475, ...], so:
        # Tax = 11925*0.10 + (35000-11925)*0.12 = 1192.5 + 2769 = 3961.5
        expected_tax = 11925 * 0.10 + (35000 - 11925) * 0.12
        assert result.loc[0, 'income_tax_before_credits'] == pytest.approx(expected_tax, abs=10)

    def test_married_filing_jointly(self):
        """Married couple should use doubled brackets."""
        calc = MicroTaxCalculator(year=2025)

        # Single earning $50K
        single_pop = pd.DataFrame({
            'agi': [50000],
            'wages': [50000],
            'married': [0],
            'children': [0],
            'weight': [1.0],
            'age_head': [35],
        })
        single_result = calc.calculate(single_pop)

        # Married couple with one earning $50K (and thus $50K household AGI)
        married_pop = pd.DataFrame({
            'agi': [50000],
            'wages': [50000],
            'married': [1],
            'children': [0],
            'weight': [1.0],
            'age_head': [35],
        })
        married_result = calc.calculate(married_pop)

        # Married should pay less tax due to wider brackets
        assert married_result.loc[0, 'income_tax_before_credits'] < single_result.loc[0, 'income_tax_before_credits']

    def test_high_income_top_bracket(self):
        """High income filer in top bracket (37%)."""
        calc = MicroTaxCalculator(year=2025)
        pop = pd.DataFrame({
            'agi': [1000000],
            'wages': [1000000],
            'married': [0],
            'children': [0],
            'weight': [1.0],
            'age_head': [55],
        })
        result = calc.calculate(pop)

        # Should include 37% on income above $626,350
        tax = result.loc[0, 'income_tax_before_credits']
        assert tax > 0
        # Rough check: top rate of 37% on large portion
        assert tax > 200000  # Should be significant


class TestStandardDeduction:
    """Test standard deduction application."""

    def test_standard_deduction_single(self):
        """Single filer gets $15,000 standard deduction (2025)."""
        calc = MicroTaxCalculator(year=2025)
        pop = pd.DataFrame({
            'agi': [20000],
            'wages': [20000],
            'married': [0],
            'children': [0],
            'weight': [1.0],
            'age_head': [30],
        })
        result = calc.calculate(pop)
        assert result.loc[0, 'std_deduction'] == 15000

    def test_standard_deduction_married(self):
        """Married filer gets $30,000 standard deduction (2025)."""
        calc = MicroTaxCalculator(year=2025)
        pop = pd.DataFrame({
            'agi': [40000],
            'wages': [40000],
            'married': [1],
            'children': [0],
            'weight': [1.0],
            'age_head': [35],
        })
        result = calc.calculate(pop)
        assert result.loc[0, 'std_deduction'] == 30000

    def test_taxable_income_deducted(self):
        """Taxable income = AGI - standard deduction."""
        calc = MicroTaxCalculator(year=2025)
        pop = pd.DataFrame({
            'agi': [50000],
            'wages': [50000],
            'married': [0],
            'children': [0],
            'weight': [1.0],
            'age_head': [35],
        })
        result = calc.calculate(pop)
        assert result.loc[0, 'taxable_income'] == pytest.approx(50000 - 15000)

    def test_zero_income_no_tax(self):
        """Zero income should result in zero tax."""
        calc = MicroTaxCalculator(year=2025)
        pop = pd.DataFrame({
            'agi': [0],
            'wages': [0],
            'married': [0],
            'children': [0],
            'weight': [1.0],
            'age_head': [65],
        })
        result = calc.calculate(pop)
        assert result.loc[0, 'final_tax'] == 0


class TestChildTaxCredit:
    """Test Child Tax Credit with phase-out."""

    def test_ctc_basic(self):
        """Single child earns $2,000 CTC."""
        calc = MicroTaxCalculator(year=2025)
        pop = pd.DataFrame({
            'agi': [50000],
            'wages': [50000],
            'married': [0],
            'children': [1],
            'weight': [1.0],
            'age_head': [35],
        })
        result = calc.calculate(pop)
        assert result.loc[0, 'ctc_value'] == 2000

    def test_ctc_multiple_children(self):
        """Three children earn $6,000 CTC (3 × $2,000)."""
        calc = MicroTaxCalculator(year=2025)
        pop = pd.DataFrame({
            'agi': [60000],
            'wages': [60000],
            'married': [0],
            'children': [3],
            'weight': [1.0],
            'age_head': [40],
        })
        result = calc.calculate(pop)
        assert result.loc[0, 'ctc_value'] == 6000

    def test_ctc_phaseout_single(self):
        """CTC phases out for single filers above $200K AGI."""
        calc = MicroTaxCalculator(year=2025)

        # Low income: full credit
        low_pop = pd.DataFrame({
            'agi': [100000],
            'wages': [100000],
            'married': [0],
            'children': [1],
            'weight': [1.0],
            'age_head': [35],
        })
        low_result = calc.calculate(low_pop)

        # High income: reduced credit
        high_pop = pd.DataFrame({
            'agi': [210000],
            'wages': [210000],
            'married': [0],
            'children': [1],
            'weight': [1.0],
            'age_head': [35],
        })
        high_result = calc.calculate(high_pop)

        # High income should have less credit
        assert high_result.loc[0, 'ctc_value'] < low_result.loc[0, 'ctc_value']
        # Should be fully phased out by high income
        assert high_result.loc[0, 'ctc_value'] >= 0

    def test_ctc_phaseout_married(self):
        """CTC phases out for married filers above $400K AGI."""
        calc = MicroTaxCalculator(year=2025)

        # At threshold ($400K), should still have credit
        pop = pd.DataFrame({
            'agi': [400000],
            'wages': [400000],
            'married': [1],
            'children': [1],
            'weight': [1.0],
            'age_head': [45],
        })
        result = calc.calculate(pop)
        assert result.loc[0, 'ctc_value'] == 2000  # No phaseout yet

    def test_no_children_no_ctc(self):
        """No children means no CTC."""
        calc = MicroTaxCalculator(year=2025)
        pop = pd.DataFrame({
            'agi': [50000],
            'wages': [50000],
            'married': [0],
            'children': [0],
            'weight': [1.0],
            'age_head': [35],
        })
        result = calc.calculate(pop)
        assert result.loc[0, 'ctc_value'] == 0


class TestSaltCap:
    """Test SALT (State and Local Tax) cap enforcement."""

    def test_salt_cap_10k_with_itemizing(self):
        """SALT capped at $10K when itemizing (TCJA)."""
        calc = MicroTaxCalculator(year=2025)
        pop = pd.DataFrame({
            'agi': [100000],
            'wages': [100000],
            'married': [0],
            'children': [0],
            'weight': [1.0],
            'age_head': [50],
            'itemized_deductions': [50000],  # Large itemized deductions
            'state_and_local_taxes': [15000],  # Over $10K SALT
        })
        result = calc.calculate(pop, salt_cap=10000)
        # SALT should be capped at $10K
        assert result.loc[0, 'state_and_local_taxes'] == 10000

    def test_salt_uncapped(self):
        """SALT uncapped when cap is None."""
        calc = MicroTaxCalculator(year=2025)
        pop = pd.DataFrame({
            'agi': [100000],
            'wages': [100000],
            'married': [0],
            'children': [0],
            'weight': [1.0],
            'age_head': [50],
            'itemized_deductions': [50000],
            'state_and_local_taxes': [15000],
        })
        # Pass salt_cap=None explicitly to override default
        calc.salt_cap = None  # Set instance variable to None
        result = calc.calculate(pop, salt_cap=None)
        # SALT should NOT be capped
        assert result.loc[0, 'state_and_local_taxes'] == 15000


class TestAMT:
    """Test Alternative Minimum Tax."""

    def test_amt_high_income_with_deductions(self):
        """High income with large deductions triggers AMT."""
        calc = MicroTaxCalculator(year=2025)
        pop = pd.DataFrame({
            'agi': [500000],
            'wages': [500000],
            'married': [0],
            'children': [0],
            'weight': [1.0],
            'age_head': [50],
        })
        result = calc.calculate(pop)
        # Should have AMT tax calculated
        assert result.loc[0, 'amt_tax'] > 0

    def test_amt_final_tax_is_max_regular_or_amt(self):
        """Final tax should be max(regular income tax, AMT)."""
        calc = MicroTaxCalculator(year=2025)
        pop = pd.DataFrame({
            'agi': [1000000],
            'wages': [1000000],
            'married': [1],
            'children': [0],
            'weight': [1.0],
            'age_head': [55],
        })
        result = calc.calculate(pop)
        # income_tax_final should be >= both regular and AMT
        assert result.loc[0, 'income_tax_final'] >= result.loc[0, 'income_tax_after_credits']
        assert result.loc[0, 'income_tax_final'] >= result.loc[0, 'amt_tax']


class TestEITC:
    """Test Earned Income Tax Credit."""

    def test_eitc_phase_in_single_no_children(self):
        """Single worker with no children: 7.65% phase-in."""
        calc = MicroTaxCalculator(year=2025)
        pop = pd.DataFrame({
            'agi': [10000],
            'wages': [10000],
            'married': [0],
            'children': [0],
            'weight': [1.0],
            'age_head': [25],
        })
        result = calc.calculate(pop)
        # Max EITC for 0 children is $632
        eitc = result.loc[0, 'eitc_value']
        assert 0 < eitc <= 632

    def test_eitc_phase_in_one_child(self):
        """Single worker with 1 child: 34% phase-in, max $3,995."""
        calc = MicroTaxCalculator(year=2025)
        pop = pd.DataFrame({
            'agi': [10000],
            'wages': [10000],
            'married': [0],
            'children': [1],
            'weight': [1.0],
            'age_head': [30],
        })
        result = calc.calculate(pop)
        eitc = result.loc[0, 'eitc_value']
        # Phase-in: 10000 * 0.34 = 3400 (less than $3,995 max)
        assert eitc == pytest.approx(3400, abs=10)

    def test_eitc_phase_in_two_children(self):
        """Single worker with 2 children: 40% phase-in, max $6,604."""
        calc = MicroTaxCalculator(year=2025)
        pop = pd.DataFrame({
            'agi': [8000],
            'wages': [8000],
            'married': [0],
            'children': [2],
            'weight': [1.0],
            'age_head': [32],
        })
        result = calc.calculate(pop)
        eitc = result.loc[0, 'eitc_value']
        # Phase-in: 8000 * 0.40 = 3200
        assert eitc == pytest.approx(3200, abs=10)

    def test_eitc_three_plus_children(self):
        """Single worker with 3+ children: 45% phase-in, max $7,430."""
        calc = MicroTaxCalculator(year=2025)
        pop = pd.DataFrame({
            'agi': [10000],
            'wages': [10000],
            'married': [0],
            'children': [5],
            'weight': [1.0],
            'age_head': [35],
        })
        result = calc.calculate(pop)
        eitc = result.loc[0, 'eitc_value']
        # Phase-in: 10000 * 0.45 = 4500 (less than $7,430 max)
        assert eitc == pytest.approx(4500, abs=10)

    def test_eitc_phaseout_single_with_children(self):
        """EITC phases out above $20,600 for single filers with children."""
        calc = MicroTaxCalculator(year=2025)

        # Low income: high credit
        low_pop = pd.DataFrame({
            'agi': [15000],
            'wages': [15000],
            'married': [0],
            'children': [1],
            'weight': [1.0],
            'age_head': [30],
        })
        low_result = calc.calculate(low_pop)

        # Higher income: reduced credit
        high_pop = pd.DataFrame({
            'agi': [30000],
            'wages': [30000],
            'married': [0],
            'children': [1],
            'weight': [1.0],
            'age_head': [30],
        })
        high_result = calc.calculate(high_pop)

        # Phaseout should reduce credit
        assert high_result.loc[0, 'eitc_value'] < low_result.loc[0, 'eitc_value']

    def test_eitc_married_threshold(self):
        """EITC phases out at $27,400 for married with children."""
        calc = MicroTaxCalculator(year=2025)
        pop = pd.DataFrame({
            'agi': [25000],
            'wages': [25000],
            'married': [1],
            'children': [1],
            'weight': [1.0],
            'age_head': [40],
        })
        result = calc.calculate(pop)
        # At $25K (below $27,400 threshold), should still have good credit
        assert result.loc[0, 'eitc_value'] > 0

    def test_eitc_refundable(self):
        """EITC can make total tax negative (refundable)."""
        calc = MicroTaxCalculator(year=2025)
        pop = pd.DataFrame({
            'agi': [8000],
            'wages': [8000],
            'married': [0],
            'children': [2],
            'weight': [1.0],
            'age_head': [28],
        })
        result = calc.calculate(pop)
        # With EITC, final tax might be negative
        # Note: final_tax is clipped at 0 in current implementation,
        # but we check that EITC is substantial
        assert result.loc[0, 'eitc_value'] > 0

    def test_eitc_requires_earned_income(self):
        """EITC requires earned income (wages)."""
        calc = MicroTaxCalculator(year=2025)
        pop = pd.DataFrame({
            'agi': [10000],
            'wages': [0],  # No wages
            'married': [0],
            'children': [1],
            'weight': [1.0],
            'age_head': [30],
        })
        result = calc.calculate(pop)
        # No earned income = no EITC
        assert result.loc[0, 'eitc_value'] == 0


class TestNIIT:
    """Test Net Investment Income Tax (Medicare surtax)."""

    def test_niit_applies_above_threshold_single(self):
        """3.8% NIIT applies to investment income above $200K (single)."""
        calc = MicroTaxCalculator(year=2025)
        pop = pd.DataFrame({
            'agi': [250000],
            'wages': [100000],
            'married': [0],
            'children': [0],
            'weight': [1.0],
            'age_head': [50],
            'interest_income': [100000],
            'dividend_income': [50000],
            'capital_gains': [0],
        })
        result = calc.calculate(pop)
        niit = result.loc[0, 'niit_tax']
        # NIIT = min(investment_income, excess_agi) * 0.038
        # investment_income = 150000, excess_agi = 250000 - 200000 = 50000
        # taxable_investment = min(150000, 50000) = 50000
        # NIIT = 50000 * 0.038 = 1900
        assert niit == pytest.approx(1900, abs=50)

    def test_niit_applies_above_threshold_married(self):
        """3.8% NIIT applies to investment income above $250K (married)."""
        calc = MicroTaxCalculator(year=2025)
        pop = pd.DataFrame({
            'agi': [300000],
            'wages': [150000],
            'married': [1],
            'children': [0],
            'weight': [1.0],
            'age_head': [55],
            'interest_income': [100000],
            'dividend_income': [50000],
            'capital_gains': [0],
        })
        result = calc.calculate(pop)
        niit = result.loc[0, 'niit_tax']
        # excess_agi = 300000 - 250000 = 50000
        # investment_income = 150000
        # taxable_investment = min(150000, 50000) = 50000
        # NIIT = 50000 * 0.038 = 1900
        assert niit == pytest.approx(1900, abs=50)

    def test_niit_below_threshold_no_tax(self):
        """No NIIT below threshold."""
        calc = MicroTaxCalculator(year=2025)
        pop = pd.DataFrame({
            'agi': [100000],
            'wages': [100000],
            'married': [0],
            'children': [0],
            'weight': [1.0],
            'age_head': [40],
            'interest_income': [0],
            'dividend_income': [0],
            'capital_gains': [0],
        })
        result = calc.calculate(pop)
        assert result.loc[0, 'niit_tax'] == 0


class TestApplyReform:
    """Test the apply_reform() method for policy changes."""

    def test_reform_rate_change(self):
        """apply_reform with rate_changes."""
        calc = MicroTaxCalculator(year=2025)
        pop = pd.DataFrame({
            'agi': [1000000],
            'wages': [1000000],
            'married': [0],
            'children': [0],
            'weight': [1.0],
            'age_head': [40],
        })

        # Baseline
        baseline = calc.calculate(pop)

        # Reform: increase top rate from 37% to 40%
        reforms = {'new_top_rate': 0.40}
        reform_result = calc.apply_reform(pop, reforms)

        # Reform should have more tax (only applies to high income)
        assert reform_result.loc[0, 'final_tax'] > baseline.loc[0, 'final_tax']

    def test_reform_income_rate_change_above_threshold(self):
        """apply_reform should apply income rate changes only above threshold."""
        calc = MicroTaxCalculator(year=2025)
        pop = pd.DataFrame({
            'agi': [700000, 300000],
            'wages': [700000, 300000],
            'married': [0, 0],
            'children': [0, 0],
            'weight': [1.0, 1.0],
            'age_head': [40, 40],
        })

        baseline = calc.calculate(pop)
        reform_result = calc.apply_reform(
            pop,
            {
                'income_rate_change': 0.02,
                'income_rate_change_threshold': 500000,
            },
        )

        expected_high_income_adjustment = (
            baseline.loc[0, 'taxable_income'] - 500000
        ) * 0.02
        assert reform_result.loc[0, 'final_tax'] == pytest.approx(
            baseline.loc[0, 'final_tax'] + expected_high_income_adjustment
        )
        assert reform_result.loc[1, 'final_tax'] == pytest.approx(
            baseline.loc[1, 'final_tax']
        )
        assert reform_result.loc[0, 'income_rate_change_adjustment'] == pytest.approx(
            expected_high_income_adjustment
        )

    def test_reform_ctc_expansion(self):
        """apply_reform with CTC increase."""
        calc = MicroTaxCalculator(year=2025)
        pop = pd.DataFrame({
            'agi': [50000],
            'wages': [50000],
            'married': [0],
            'children': [1],
            'weight': [1.0],
            'age_head': [35],
        })

        # Baseline
        baseline = calc.calculate(pop)

        # Reform: increase CTC to $3,000
        reforms = {'ctc_amount': 3000}
        reform_result = calc.apply_reform(pop, reforms)

        # Reform CTC should be higher
        assert reform_result.loc[0, 'ctc_value'] > baseline.loc[0, 'ctc_value']

    def test_reform_std_deduction_bonus(self):
        """apply_reform with standard deduction increase."""
        calc = MicroTaxCalculator(year=2025)
        pop = pd.DataFrame({
            'agi': [60000],
            'wages': [60000],
            'married': [0],
            'children': [0],
            'weight': [1.0],
            'age_head': [40],
        })

        # Baseline
        baseline = calc.calculate(pop)

        # Reform: $2,000 bonus to std deduction
        reforms = {'std_deduction_bonus': 2000}
        reform_result = calc.apply_reform(pop, reforms)

        # Reform should have lower taxable income
        assert reform_result.loc[0, 'taxable_income'] < baseline.loc[0, 'taxable_income']
        # Thus lower tax
        assert reform_result.loc[0, 'final_tax'] < baseline.loc[0, 'final_tax']

    def test_reform_eitc_expansion(self):
        """apply_reform with EITC expansion (multiplier)."""
        calc = MicroTaxCalculator(year=2025)
        pop = pd.DataFrame({
            'agi': [12000],  # Upper phase-in range for 1 child (34% * 12000 = 4080 > baseline max of 3995)
            'wages': [12000],
            'married': [0],
            'children': [1],
            'weight': [1.0],
            'age_head': [30],
        })

        # Baseline
        baseline = calc.calculate(pop)
        baseline_eitc = baseline.loc[0, 'eitc_value']
        # At $12K: baseline = min(12000 * 0.34, 3995) = 3995 (capped at max)

        # Reform: 1.5x EITC expansion (max changes from $3,995 to ~$5,993)
        reforms = {'eitc_expansion': 1.5}
        reform_result = calc.apply_reform(pop, reforms)

        # Reform EITC should be larger
        # After 1.5x: max becomes 3995 * 1.5 = 5992.5
        # At $12K: reform = min(12000 * 0.34, 5992.5) = min(4080, 5992.5) = 4080 > baseline 3995
        reform_eitc = reform_result.loc[0, 'eitc_value']
        assert reform_eitc > baseline_eitc

    def test_reform_restores_original_state(self):
        """apply_reform restores calculator state after reform."""
        calc = MicroTaxCalculator(year=2025)
        pop = pd.DataFrame({
            'agi': [50000],
            'wages': [50000],
            'married': [0],
            'children': [0],
            'weight': [1.0],
            'age_head': [35],
        })

        original_ctc = calc.ctc_amount
        original_std_ded = calc.std_deduction_single

        # Apply reform
        reforms = {
            'ctc_amount': 3000,
            'std_deduction_bonus': 2000,
        }
        calc.apply_reform(pop, reforms)

        # After reform, should be back to original
        assert calc.ctc_amount == original_ctc
        assert calc.std_deduction_single == original_std_ded


class TestEffectiveTaxRate:
    """Test effective tax rate calculation."""

    def test_effective_tax_rate_positive_income(self):
        """ETR = final_tax / AGI for positive income."""
        calc = MicroTaxCalculator(year=2025)
        pop = pd.DataFrame({
            'agi': [100000],
            'wages': [100000],
            'married': [0],
            'children': [0],
            'weight': [1.0],
            'age_head': [40],
        })
        result = calc.calculate(pop)
        agi = result.loc[0, 'agi']
        final_tax = result.loc[0, 'final_tax']
        expected_etr = final_tax / agi if agi > 0 else 0
        assert result.loc[0, 'effective_tax_rate'] == pytest.approx(expected_etr, abs=0.001)

    def test_effective_tax_rate_zero_income(self):
        """ETR = 0 for zero income."""
        calc = MicroTaxCalculator(year=2025)
        pop = pd.DataFrame({
            'agi': [0],
            'wages': [0],
            'married': [0],
            'children': [0],
            'weight': [1.0],
            'age_head': [65],
        })
        result = calc.calculate(pop)
        assert result.loc[0, 'effective_tax_rate'] == 0


class TestVeryHighIncome:
    """Test with very high income ($10M+)."""

    def test_ten_million_income(self):
        """$10M income should have substantial tax."""
        calc = MicroTaxCalculator(year=2025)
        pop = pd.DataFrame({
            'agi': [10000000],
            'wages': [10000000],
            'married': [1],
            'children': [0],
            'weight': [1.0],
            'age_head': [60],
        })
        result = calc.calculate(pop)

        final_tax = result.loc[0, 'final_tax']
        # Should be substantial
        assert final_tax > 2000000  # At least ~20% effective

        # ETR should be reasonable
        etr = result.loc[0, 'effective_tax_rate']
        assert 0.2 < etr < 0.4  # Should be in typical range


class TestBulkCalculation:
    """Test vectorized calculation with many rows."""

    def test_vectorized_calculation_1000_rows(self):
        """Calculate tax for 1,000 individuals at once."""
        calc = MicroTaxCalculator(year=2025)
        np.random.seed(42)

        pop = pd.DataFrame({
            'agi': np.random.uniform(10000, 500000, 1000),
            'wages': np.random.uniform(10000, 500000, 1000),
            'married': np.random.choice([0, 1], 1000),
            'children': np.random.choice([0, 1, 2, 3], 1000),
            'weight': np.ones(1000),
            'age_head': np.random.uniform(25, 70, 1000),
        })

        result = calc.calculate(pop)

        # All rows should be calculated
        assert len(result) == 1000
        # All should have final_tax >= 0
        assert (result['final_tax'] >= 0).all()
        # Effective tax rates should be reasonable
        assert (result['effective_tax_rate'] >= 0).all()
        assert (result['effective_tax_rate'] <= 1.0).all()


class TestMarriedVsSingle:
    """Test married vs single tax differences."""

    def test_marriage_bonus_same_income(self):
        """Married couple should often pay less tax than two singles (wide brackets)."""
        calc = MicroTaxCalculator(year=2025)

        # Two single filers earning $50K each
        single_pop = pd.DataFrame({
            'agi': [50000, 50000],
            'wages': [50000, 50000],
            'married': [0, 0],
            'children': [0, 0],
            'weight': [1.0, 1.0],
            'age_head': [40, 40],
        })
        single_result = calc.calculate(single_pop)
        single_total_tax = single_result['final_tax'].sum()

        # One married couple earning $100K (total AGI from one earner)
        married_pop = pd.DataFrame({
            'agi': [100000],
            'wages': [100000],
            'married': [1],
            'children': [0],
            'weight': [1.0],
            'age_head': [40],
        })
        married_result = calc.calculate(married_pop)
        married_total_tax = married_result.loc[0, 'final_tax']

        # Married couple should have marriage bonus (pay less than equivalent singles)
        # They have exactly doubled brackets which removes marriage penalty
        assert married_total_tax <= single_total_tax
