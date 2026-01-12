
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Optional

@dataclass
class LongRunResult:
    """Results from a long-run growth simulation."""
    years: np.ndarray
    gdp: np.ndarray
    capital_stock: np.ndarray
    investment: np.ndarray
    wages: np.ndarray
    interest_rate: np.ndarray
    baseline_gdp: np.ndarray
    
    @property
    def gdp_pct_change(self) -> np.ndarray:
        return (self.gdp / self.baseline_gdp - 1) * 100

class SolowGrowthModel:
    """
    A Solow-Swan growth model adapted for fiscal policy analysis.
    Models how government deficits crowd out private investment and
    affect the long-run capital stock.
    
    Calibration (US Defaults):
    - Capital Share (alpha): 0.35
    - Depreciation (delta): 0.05
    - Savings Rate (s): 0.18
    - TFP Growth (g): 0.015
    - Population Growth (n): 0.005
    """
    
    def __init__(self, 
                 alpha: float = 0.35, 
                 delta: float = 0.05, 
                 savings_rate: float = 0.18,
                 tfp_growth: float = 0.015,
                 pop_growth: float = 0.005,
                 initial_k: float = 75000.0, # $75 Trillion initial capital stock
                 initial_l: float = 165.0,   # 165 Million workers
                 initial_a: float = 1.0):
        self.alpha = alpha
        self.delta = delta
        self.s = savings_rate
        self.g = tfp_growth
        self.n = pop_growth
        self.initial_k = initial_k
        self.initial_l = initial_l
        self.initial_a = initial_a

    def production_function(self, k: float, l: float, a: float) -> float:
        """Cobb-Douglas production: Y = A * K^alpha * L^(1-alpha)"""
        return a * (k ** self.alpha) * (l ** (1 - self.alpha))

    def run_simulation(self, 
                       deficits: np.ndarray, 
                       horizon: int = 30, 
                       start_year: int = 2025) -> LongRunResult:
        """
        Run simulation over the horizon.
        
        Args:
            deficits: Array of annual deficit increases (positive = more debt)
                      If shorter than horizon, assumes last value continues.
            horizon: Years to simulate
            start_year: Starting year
        """
        years = np.arange(start_year, start_year + horizon)
        
        # Extend deficits if needed
        if len(deficits) < horizon:
            last_val = deficits[-1] if len(deficits) > 0 else 0
            deficits = np.append(deficits, [last_val] * (horizon - len(deficits)))
            
        # Initialize arrays
        k = np.zeros(horizon)
        l = np.zeros(horizon)
        a = np.zeros(horizon)
        y = np.zeros(horizon)
        inv = np.zeros(horizon)
        base_y = np.zeros(horizon)
        
        # Baseline path (No deficit change)
        k_base = self.initial_k
        l_base = self.initial_l
        a_base = self.initial_a
        
        # Current state (with policy)
        k_curr = self.initial_k
        l_curr = self.initial_l
        a_curr = self.initial_a
        
        for t in range(horizon):
            # Track values
            l[t] = l_curr
            a[t] = a_curr
            
            # 1. Calculate Output
            y_curr = self.production_function(k_curr, l_curr, a_curr)
            y_base = self.production_function(k_base, l_base, a_base)
            
            y[t] = y_curr
            base_y[t] = y_base
            k[t] = k_curr
            
            # 2. Calculate Investment (Crowding Out)
            # Standard: I = S = s * Y
            # With Government: I = s * Y - Deficit
            # Deficits reduce the supply of loanable funds for private investment
            investment = (self.s * y_curr) - deficits[t]
            inv[t] = investment
            
            # Base Investment
            inv_base = (self.s * y_base)
            
            # 3. Capital Accumulation for next period
            # K(t+1) = (1-delta)K(t) + I(t)
            k_curr = (1 - self.delta) * k_curr + investment
            k_base = (1 - self.delta) * k_base + inv_base
            
            # 4. Exogenous Growth (TFP and Labor)
            l_curr *= (1 + self.n)
            a_curr *= (1 + self.g)
            l_base *= (1 + self.n)
            a_base *= (1 + self.g)
            
        # Simple wage calculation (Marginal Product of Labor)
        wages = (1 - self.alpha) * (y / l)
        
        # Simple interest rate calculation (Marginal Product of Capital)
        interest = self.alpha * (y / k)
        
        return LongRunResult(
            years=years,
            gdp=y,
            capital_stock=k,
            investment=inv,
            wages=wages,
            interest_rate=interest,
            baseline_gdp=base_y
        )

if __name__ == "__main__":
    model = SolowGrowthModel()
    # Scenario: Permanent $500B annual deficit increase
    res = model.run_simulation(deficits=np.array([500.0] * 10), horizon=30)
    
    print("--- SOLOW GROWTH SIMULATION: $500B PERM DEFICIT ---")
    print(f"Year 1 GDP Effect:  {res.gdp_pct_change[0]:.2f}%")
    print(f"Year 10 GDP Effect: {res.gdp_pct_change[9]:.2f}%")
    print(f"Year 30 GDP Effect: {res.gdp_pct_change[29]:.2f}%")
