
import numpy as np
import pandas as pd


class MicroTaxCalculator:
    """
    Vectorized tax calculator that processes individual tax units.
    This allows for capturing complex interactions (cliffs, phase-outs, AMT, SALT cap, EITC, NIIT)
    that aggregate models miss.
    """

    def __init__(self, year: int = 2025):
        self.year = year

        # 2025 Tax Brackets (Single and Married Filing Jointly) - inflation-adjusted
        self.brackets_single = [0, 11925, 48475, 103350, 197300, 250525, 626350]
        self.rates_single =    [0.10, 0.12,  0.22,   0.24,   0.32,   0.35,   0.37]

        self.brackets_mfj = [0, 23850, 96950, 206700, 394600, 501050, 751600]
        self.rates_mfj =    [0.10, 0.12,  0.22,   0.24,   0.32,   0.35,   0.37]

        # Standard Deduction (2025)
        self.std_deduction_single = 15000
        self.std_deduction_married = 30000

        # CTC Parameters (2025)
        self.ctc_amount = 2000
        self.ctc_phaseout_start_single = 200000
        self.ctc_phaseout_start_married = 400000
        self.ctc_phaseout_rate = 0.05  # $50 per $1000 over threshold

        # SALT Cap (TCJA, 2017+)
        self.salt_cap = 10000  # None = no cap

        # AMT Parameters (2025)
        self.amt_exemption_single = 88100
        self.amt_exemption_married = 137000
        self.amt_rate_1 = 0.26  # 26% on first $232,600 (MFJ)
        self.amt_rate_2 = 0.28  # 28% above
        self.amt_threshold = 232600

        # EITC Parameters (2025) - single/head of household for simplicity
        # Phase-in rates by number of children
        self.eitc_phasein_0_children = 0.0765   # 7.65% (no children)
        self.eitc_phasein_1_child = 0.34
        self.eitc_phasein_2_children = 0.40
        self.eitc_phasein_3plus_children = 0.45

        # Maximum credit by children
        self.eitc_max_0_children = 632
        self.eitc_max_1_child = 3995
        self.eitc_max_2_children = 6604
        self.eitc_max_3plus_children = 7430

        # Phase-out rates (same for all)
        self.eitc_phaseout_rate = 0.2106

        # Phase-out start thresholds (single/HOH)
        self.eitc_phaseout_start_single_0_children = 9100
        self.eitc_phaseout_start_single_with_children = 20600

        # Phase-out start thresholds (married)
        self.eitc_phaseout_start_married_0_children = 14500
        self.eitc_phaseout_start_married_with_children = 27400

        # Medicare Surtax (NIIT) Parameters (3.8% on investment income)
        self.niit_rate = 0.038
        self.niit_threshold_single = 200000
        self.niit_threshold_married = 250000

    def calculate(self, pop: pd.DataFrame, salt_cap: int | None = None) -> pd.DataFrame:
        """
        Calculate tax liability for the population.

        Args:
            pop: DataFrame with columns: agi, wages, married, children, weight, age_head
                 Optional: itemized_deductions, investment_income
            salt_cap: Override SALT cap. None = no cap, 10000 = $10K cap (TCJA), etc.
        """
        df = pop.copy()

        if salt_cap is not None:
            active_salt_cap = salt_cap
        else:
            active_salt_cap = self.salt_cap

        # 1. Determine Standard Deduction
        df.loc[:, 'std_deduction'] = np.where(df['married'] == 1,
                                              self.std_deduction_married,
                                              self.std_deduction_single)

        # 2. Handle Itemized vs Standard Deduction
        # If itemized_deductions column exists, compare; otherwise use standard
        if 'itemized_deductions' in df.columns:
            # Apply SALT cap if itemizing
            if 'state_and_local_taxes' not in df.columns:
                df.loc[:, 'state_and_local_taxes'] = 0
            if active_salt_cap is not None:
                df.loc[:, 'state_and_local_taxes'] = df['state_and_local_taxes'].clip(upper=active_salt_cap)

            # Adjusted itemized deduction
            df.loc[:, 'itemized_after_salt_cap'] = df['itemized_deductions'].copy()

            # Take max of standard vs itemized
            df.loc[:, 'deduction'] = np.maximum(df['std_deduction'], df['itemized_after_salt_cap'])
        else:
            df.loc[:, 'deduction'] = df['std_deduction']

        # 3. Taxable Income
        df.loc[:, 'taxable_income'] = np.maximum(0, df['agi'] - df['deduction'])

        # 4. Income Tax (Vectorized Progressive Calculation)
        tax = self._calculate_income_tax_vectorized(df)
        df.loc[:, 'income_tax_before_credits'] = tax

        # 5. Child Tax Credit (with Phase-out)
        df.loc[:, 'ctc_value'] = self._calculate_ctc(df)

        # 6. EITC (Earned Income Tax Credit) - Refundable
        df.loc[:, 'eitc_value'] = self._calculate_eitc(df)

        # 7. Income tax after credits (can be negative due to refundable EITC)
        df.loc[:, 'income_tax_after_credits'] = df['income_tax_before_credits'] - df['ctc_value'] - df['eitc_value']

        # 8. AMT (Alternative Minimum Tax)
        df.loc[:, 'amt_tax'] = self._calculate_amt(df)

        # 9. Regular tax vs AMT (take the higher)
        df.loc[:, 'income_tax_final'] = np.maximum(
            df['income_tax_after_credits'],
            df['amt_tax']
        )

        # 10. Medicare Surtax (NIIT) - on investment income
        df.loc[:, 'niit_tax'] = self._calculate_niit(df)

        # 11. Total Tax (Income + NIIT)
        df.loc[:, 'final_tax'] = np.maximum(0, df['income_tax_final'] + df['niit_tax'])

        # 12. Metrics
        df.loc[:, 'effective_tax_rate'] = np.where(df['agi'] > 0, df['final_tax'] / df['agi'], 0)

        return df

    def _calculate_income_tax_vectorized(self, df: pd.DataFrame) -> np.ndarray:
        """Calculate income tax using vectorized bracket logic."""
        tax = np.zeros(len(df))

        # Get arrays
        is_married = df['married'].values == 1
        taxable_income = df['taxable_income'].values

        # Apply each bracket
        for i in range(len(self.brackets_single) - 1):
            lower_single = self.brackets_single[i]
            upper_single = self.brackets_single[i + 1]
            lower_mfj = self.brackets_mfj[i]
            upper_mfj = self.brackets_mfj[i + 1]
            rate = self.rates_single[i]

            # Choose bracket bounds based on filing status
            lower = np.where(is_married, lower_mfj, lower_single)
            upper = np.where(is_married, upper_mfj, upper_single)

            # Income in this bracket
            income_in_bracket = np.clip(taxable_income - lower, 0, upper - lower)
            tax += income_in_bracket * rate

        # Top bracket
        last_lower_single = self.brackets_single[-1]
        last_lower_mfj = self.brackets_mfj[-1]
        last_rate = self.rates_single[-1]
        last_lower = np.where(is_married, last_lower_mfj, last_lower_single)
        tax += np.maximum(0, taxable_income - last_lower) * last_rate

        return tax

    def _calculate_ctc(self, df: pd.DataFrame) -> np.ndarray:
        """Calculate Child Tax Credit with phase-out."""
        children = df['children'].values
        agi = df['agi'].values
        married = df['married'].values

        # Base credit
        max_credit = children * self.ctc_amount

        # Phase-out start
        phaseout_start = np.where(
            married == 1,
            self.ctc_phaseout_start_married,
            self.ctc_phaseout_start_single
        )

        # Excess income
        excess_income = np.maximum(0, agi - phaseout_start)

        # Reduction: $50 per $1000 (or part thereof)
        reduction = np.ceil(excess_income / 1000) * 50

        ctc = np.maximum(0, max_credit - reduction)
        return ctc

    def _calculate_eitc(self, df: pd.DataFrame) -> np.ndarray:
        """Calculate Earned Income Tax Credit (refundable)."""
        children = df['children'].values
        agi = df['agi'].values
        married = df['married'].values
        wages = df.get('wages', pd.Series(0, index=df.index)).values

        # Only available to workers with earned income
        has_earned_income = wages > 0

        # Determine phase-in rate and max credit by children
        phase_in = np.zeros(len(df))
        max_credit = np.zeros(len(df))

        # 0 children
        mask_0 = (children == 0) & has_earned_income
        phase_in[mask_0] = self.eitc_phasein_0_children
        max_credit[mask_0] = self.eitc_max_0_children

        # 1 child
        mask_1 = (children == 1) & has_earned_income
        phase_in[mask_1] = self.eitc_phasein_1_child
        max_credit[mask_1] = self.eitc_max_1_child

        # 2 children
        mask_2 = (children == 2) & has_earned_income
        phase_in[mask_2] = self.eitc_phasein_2_children
        max_credit[mask_2] = self.eitc_max_2_children

        # 3+ children
        mask_3plus = (children >= 3) & has_earned_income
        phase_in[mask_3plus] = self.eitc_phasein_3plus_children
        max_credit[mask_3plus] = self.eitc_max_3plus_children

        # Phase-in credit = min(earned income * phase_in_rate, max_credit)
        phasein_credit = np.minimum(wages * phase_in, max_credit)

        # Phase-out start threshold
        phaseout_start = np.where(
            married == 1,
            np.where(
                children > 0,
                self.eitc_phaseout_start_married_with_children,
                self.eitc_phaseout_start_married_0_children
            ),
            np.where(
                children > 0,
                self.eitc_phaseout_start_single_with_children,
                self.eitc_phaseout_start_single_0_children
            )
        )

        # Excess income for phase-out
        excess = np.maximum(0, agi - phaseout_start)

        # Phase-out credit = max_credit - (excess * phase_out_rate)
        # Use the max_credit from phase-in (where they plateau)
        phaseout_credit = np.maximum(0, phasein_credit - excess * self.eitc_phaseout_rate)

        eitc = phaseout_credit

        return eitc

    def _calculate_amt(self, df: pd.DataFrame) -> np.ndarray:
        """Calculate Alternative Minimum Tax (simplified)."""
        agi = df['agi'].values
        married = df['married'].values

        # AMT exemption
        amt_exemption = np.where(
            married == 1,
            self.amt_exemption_married,
            self.amt_exemption_single
        )

        # Simplified AMT base = AGI - exemption
        # (In real world, includes preferences/adjustments, but AGI is proxy)
        amt_base = np.maximum(0, agi - amt_exemption)

        # Two-rate system: 26% on first $232.6K, 28% above
        amt_tax = np.zeros(len(df))
        threshold = self.amt_threshold if married.any() else self.amt_threshold / 2

        # For simplicity, apply 26% up to threshold, 28% above
        amt_tax = np.minimum(amt_base, threshold) * self.amt_rate_1 + \
                  np.maximum(0, amt_base - threshold) * self.amt_rate_2

        return amt_tax

    def _calculate_niit(self, df: pd.DataFrame) -> np.ndarray:
        """Calculate Net Investment Income Tax (3.8% surtax)."""
        married = df['married'].values

        # Check if investment_income column exists
        if 'investment_income' in df.columns:
            investment_income = df['investment_income'].values
        else:
            # Estimate from interest, dividends, capital gains, etc.
            investment_income = (
                df.get('interest_income', pd.Series(0, index=df.index)).values +
                df.get('dividend_income', pd.Series(0, index=df.index)).values +
                df.get('capital_gains', pd.Series(0, index=df.index)).values
            )

        agi = df['agi'].values

        # NIIT threshold
        niit_threshold = np.where(
            married == 1,
            self.niit_threshold_married,
            self.niit_threshold_single
        )

        # NIIT applies to lesser of (1) investment income or (2) excess of AGI over threshold
        investable_income = np.maximum(0, agi - niit_threshold)
        taxable_investment = np.minimum(investment_income, investable_income)

        niit = taxable_investment * self.niit_rate

        return niit

    def apply_reform(self, pop: pd.DataFrame, reforms: dict) -> pd.DataFrame:
        """
        Apply policy reforms and calculate.

        Args:
            pop: Population DataFrame
            reforms: Dict of parameter overrides:
                - 'rate_changes': dict of bracket_index: new_rate (single brackets)
                - 'rate_changes_mfj': dict of bracket_index: new_rate (MFJ brackets)
                - 'ctc_amount': new CTC amount
                - 'salt_cap': new SALT cap (None = uncapped)
                - 'std_deduction_bonus': additional std deduction
                - 'new_top_rate': override top marginal rate
                - 'income_rate_change': rate change above income_rate_change_threshold
                - 'income_rate_change_threshold': taxable-income threshold for rate change
                - 'eitc_expansion': multiplier for EITC amounts (e.g., 1.5)
                - 'amt_exemption_adjustment': adjustment to AMT exemption

        Returns:
            Calculated DataFrame with reform applied
        """
        # Save original state
        original_brackets_single = self.brackets_single.copy()
        original_rates_single = self.rates_single.copy()
        original_brackets_mfj = self.brackets_mfj.copy()
        original_rates_mfj = self.rates_mfj.copy()
        original_ctc = self.ctc_amount
        original_salt_cap = self.salt_cap
        original_std_ded_single = self.std_deduction_single
        original_std_ded_married = self.std_deduction_married
        original_eitc_max_0 = self.eitc_max_0_children
        original_eitc_max_1 = self.eitc_max_1_child
        original_eitc_max_2 = self.eitc_max_2_children
        original_eitc_max_3plus = self.eitc_max_3plus_children
        original_amt_exemption_single = self.amt_exemption_single
        original_amt_exemption_married = self.amt_exemption_married

        try:
            # Apply rate changes (single)
            if 'rate_changes' in reforms:
                for idx, new_rate in reforms['rate_changes'].items():
                    if 0 <= idx < len(self.rates_single):
                        self.rates_single[idx] = new_rate

            # Apply rate changes (MFJ)
            if 'rate_changes_mfj' in reforms:
                for idx, new_rate in reforms['rate_changes_mfj'].items():
                    if 0 <= idx < len(self.rates_mfj):
                        self.rates_mfj[idx] = new_rate

            # Apply new top rate (overrides both single and MFJ)
            if 'new_top_rate' in reforms:
                self.rates_single[-1] = reforms['new_top_rate']
                self.rates_mfj[-1] = reforms['new_top_rate']

            # Apply CTC change
            if 'ctc_amount' in reforms:
                self.ctc_amount = reforms['ctc_amount']

            # Apply SALT cap
            if 'salt_cap' in reforms:
                self.salt_cap = reforms['salt_cap']

            # Apply standard deduction bonus
            if 'std_deduction_bonus' in reforms:
                bonus = reforms['std_deduction_bonus']
                self.std_deduction_single += bonus
                self.std_deduction_married += bonus

            # Apply EITC expansion
            if 'eitc_expansion' in reforms:
                multiplier = reforms['eitc_expansion']
                self.eitc_max_0_children = int(self.eitc_max_0_children * multiplier)
                self.eitc_max_1_child = int(self.eitc_max_1_child * multiplier)
                self.eitc_max_2_children = int(self.eitc_max_2_children * multiplier)
                self.eitc_max_3plus_children = int(self.eitc_max_3plus_children * multiplier)

            # Apply AMT exemption adjustment
            if 'amt_exemption_adjustment' in reforms:
                adj = reforms['amt_exemption_adjustment']
                self.amt_exemption_single += adj
                self.amt_exemption_married += adj

            # Calculate with reforms
            result = self.calculate(pop, salt_cap=self.salt_cap)
            if 'income_rate_change' in reforms:
                threshold = float(reforms.get('income_rate_change_threshold', 0.0) or 0.0)
                rate_change = float(reforms['income_rate_change'])
                taxable_income = result['taxable_income'].values
                adjustment = np.maximum(0, taxable_income - threshold) * rate_change
                result.loc[:, 'income_rate_change_adjustment'] = adjustment
                result.loc[:, 'income_tax_final'] = np.maximum(
                    0,
                    result['income_tax_final'].values + adjustment,
                )
                result.loc[:, 'final_tax'] = np.maximum(
                    0,
                    result['income_tax_final'].values + result['niit_tax'].values,
                )
                effective_tax_rate = np.zeros(len(result))
                np.divide(
                    result['final_tax'].values,
                    result['agi'].values,
                    out=effective_tax_rate,
                    where=result['agi'].values > 0,
                )
                result.loc[:, 'effective_tax_rate'] = effective_tax_rate

            return result

        finally:
            # Restore original state
            self.brackets_single = original_brackets_single
            self.rates_single = original_rates_single
            self.brackets_mfj = original_brackets_mfj
            self.rates_mfj = original_rates_mfj
            self.ctc_amount = original_ctc
            self.salt_cap = original_salt_cap
            self.std_deduction_single = original_std_ded_single
            self.std_deduction_married = original_std_ded_married
            self.eitc_max_0_children = original_eitc_max_0
            self.eitc_max_1_child = original_eitc_max_1
            self.eitc_max_2_children = original_eitc_max_2
            self.eitc_max_3plus_children = original_eitc_max_3plus
            self.amt_exemption_single = original_amt_exemption_single
            self.amt_exemption_married = original_amt_exemption_married

    def run_reform(self, pop: pd.DataFrame, reform_func) -> pd.DataFrame:
        """
        Run the calculator with a modified parameter set (reform).
        Legacy interface - converts function to dict-based apply_reform.
        """
        # Save original state
        original_state = {
            'ctc_amount': self.ctc_amount,
            'salt_cap': self.salt_cap,
        }

        # Apply reform (function that modifies self)
        reform_func(self)

        # Calculate
        res = self.calculate(pop, salt_cap=self.salt_cap)

        # Restore state
        for key, val in original_state.items():
            setattr(self, key, val)

        return res

