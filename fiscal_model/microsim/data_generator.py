
import numpy as np
import pandas as pd
from dataclasses import dataclass

@dataclass
class SyntheticPopulation:
    """
    Generates synthetic tax units (taxpayers) for microsimulation.
    In a production system, this would load CPS ASEC or IRS PUF data.
    """
    size: int = 10_000
    year: int = 2024

    def generate(self) -> pd.DataFrame:
        """
        Generate a synthetic population of taxpayers with realistic(ish) 
        distributions of income types.
        """
        np.random.seed(42)
        n = self.size
        
        # 1. Wages (Log-normal distribution to capture inequality)
        # Shifted to ensure some zero-wage filers
        wages = np.random.lognormal(mean=10.5, sigma=1.0, size=n)
        wages = np.where(np.random.random(n) < 0.15, 0, wages) # 15% have no wages
        
        # 2. Capital Gains (Highly concentrated)
        # Most have 0, top end has huge amounts
        cap_gains = np.random.lognormal(mean=10, sigma=2.5, size=n)
        has_gains = np.random.random(n)
        # Only top 20% have material gains, top 1% have massive gains
        prob_gains = np.zeros(n)
        wage_percentiles = pd.Series(wages).rank(pct=True)
        
        # Higher probability of gains if higher wages (correlation)
        gains_mask = np.random.random(n) > (0.95 - 0.5 * wage_percentiles)
        cap_gains = np.where(gains_mask, cap_gains, 0)
        
        # 3. Demographics
        # Marital status (correlated with age/income)
        married = np.random.choice([0, 1], size=n, p=[0.5, 0.5])
        
        # Children (0 to 4)
        children = np.random.choice([0, 1, 2, 3, 4], size=n, p=[0.6, 0.15, 0.15, 0.08, 0.02])
        
        # 4. Weights
        # Each record represents X actual households.
        # Simple version: equal weights summing to US population (~150M filers)
        total_filers = 150_000_000
        weight = total_filers / n

        df = pd.DataFrame({
            'id': range(n),
            'weight': weight,
            'wages': wages,
            'capital_gains': cap_gains,
            'interest_income': wages * np.random.uniform(0, 0.05, n),
            'married': married, # 1=Married, 0=Single
            'children': children,
            'age': np.random.randint(18, 90, n)
        })
        
        # Calculate Total Income (AGI proxy)
        df['agi'] = df['wages'] + df['capital_gains'] + df['interest_income']
        
        return df

if __name__ == "__main__":
    pop = SyntheticPopulation()
    df = pop.generate()
    print(df.describe())
