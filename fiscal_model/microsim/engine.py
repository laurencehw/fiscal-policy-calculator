
import pandas as pd
import numpy as np

class MicroTaxCalculator:
    """
    Vectorized tax calculator that processes individual tax units.
    This allows for capturing complex interactions (cliffs, phase-outs)
    that aggregate models miss.
    """
    
    def __init__(self, year: int = 2024):
        self.year = year
        
        # 2024 Simplified Brackets (Single)
        self.brackets_single = [0, 11600, 47150, 100525, 191950, 243725, 609350]
        self.rates_single =    [0.10, 0.12,  0.22,   0.24,   0.32,   0.35,   0.37]
        
        # Standard Deduction
        self.std_deduction_single = 14600
        self.std_deduction_married = 29200
        
        # CTC Parameters
        self.ctc_amount = 2000
        self.ctc_phaseout_start_single = 200000
        self.ctc_phaseout_start_married = 400000
        self.ctc_phaseout_rate = 0.05

    def calculate(self, pop: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate tax liability for the population.
        """
        df = pop.copy()

        # 1. Determine Standard Deduction
        df.loc[:, 'std_deduction'] = np.where(df['married'] == 1,
                                              self.std_deduction_married,
                                              self.std_deduction_single)

        # 2. Taxable Income
        # Max(0, AGI - Deduction)
        df.loc[:, 'taxable_income'] = np.maximum(0, df['agi'] - df['std_deduction'])
        
        # 3. Income Tax (Simplified Progressive Calculation)
        # We'll just do a simple tiered calculation for the prototype
        # In production, use interval arithmetic
        
        # Vectorized bracket calculation
        tax = np.zeros(len(df))
        
        # Apply brackets (Assuming all are single for simplicity in prototype, 
        # or doubling brackets for married)
        brackets = self.brackets_single
        rates = self.rates_single
        
        previous_bracket = 0
        
        for i, threshold in enumerate(brackets[1:]):
            rate = rates[i]
            # Income in this chunk
            # If married, double the bracket width (simplified marriage penalty relief)
            threshold_adj = np.where(df['married']==1, threshold * 2, threshold)
            prev_adj = np.where(df['married']==1, previous_bracket * 2, previous_bracket)
            
            income_in_bracket = np.clip(df['taxable_income'] - prev_adj, 0, threshold_adj - prev_adj)
            tax += income_in_bracket * rate
            
            previous_bracket = threshold
            
        # Top bracket
        last_threshold = brackets[-1]
        last_threshold_adj = np.where(df['married']==1, last_threshold * 2, last_threshold)
        tax += np.maximum(0, df['taxable_income'] - last_threshold_adj) * rates[-1]
        
        df.loc[:, 'income_tax_before_credits'] = tax

        # 4. Child Tax Credit (with Phase-out)
        # This is where microsim shines: capturing the exact interaction of income & kids
        
        # Base credit
        max_credit = df['children'] * self.ctc_amount
        
        # Phase-out
        phaseout_start = np.where(df['married'] == 1, 
                                self.ctc_phaseout_start_married, 
                                self.ctc_phaseout_start_single)
        
        excess_income = np.maximum(0, df['agi'] - phaseout_start)
        reduction = np.ceil(excess_income / 1000) * 50 # $50 per $1000
        
        df.loc[:, 'ctc_value'] = np.maximum(0, max_credit - reduction)

        # 5. Final Tax
        df.loc[:, 'final_tax'] = np.maximum(0, df['income_tax_before_credits'] - df['ctc_value'])

        # Metrics
        df.loc[:, 'effective_tax_rate'] = np.where(df['agi'] > 0, df['final_tax'] / df['agi'], 0)
        
        return df

    def run_reform(self, pop: pd.DataFrame, reform_func) -> pd.DataFrame:
        """
        Run the calculator with a modified parameter set (reform).
        """
        # Save original state
        original_ctc = self.ctc_amount
        
        # Apply reform (function that modifies self)
        reform_func(self)
        
        # Calculate
        res = self.calculate(pop)
        
        # Restore state
        self.ctc_amount = original_ctc
        
        return res

