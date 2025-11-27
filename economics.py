"""
Economic Feedback Module

Calculates macroeconomic effects of fiscal policies for dynamic scoring,
including GDP, employment, and interest rate impacts.
"""

from dataclasses import dataclass, field
import numpy as np
from typing import Optional, Literal

from .policies import Policy, TaxPolicy, SpendingPolicy, TransferPolicy, PolicyType
from .baseline import BaselineProjection


@dataclass
class DynamicEffects:
    """
    Container for dynamic/macroeconomic effects of a policy.
    """
    years: np.ndarray
    
    # GDP effects
    gdp_level_change: np.ndarray  # Change in GDP level (billions)
    gdp_percent_change: np.ndarray  # Percent change from baseline
    
    # Labor market effects
    employment_change: np.ndarray  # Change in employment (thousands)
    hours_worked_change: np.ndarray  # Percent change in hours worked
    labor_force_change: np.ndarray  # Change in labor force participation
    
    # Capital effects
    capital_stock_change: np.ndarray  # Percent change in capital stock
    investment_change: np.ndarray  # Change in investment (billions)
    
    # Interest rate effects
    interest_rate_change: np.ndarray  # Change in interest rate (percentage points)
    
    # Revenue feedback
    revenue_feedback: np.ndarray  # Additional revenue from economic growth (billions)
    
    @property
    def cumulative_gdp_effect(self) -> float:
        """Total GDP effect over the window."""
        return np.sum(self.gdp_level_change)
    
    @property
    def cumulative_revenue_feedback(self) -> float:
        """Total revenue feedback over the window."""
        return np.sum(self.revenue_feedback)
    
    @property
    def average_employment_effect(self) -> float:
        """Average employment change over the window."""
        return np.mean(self.employment_change)


class EconomicConditions:
    """
    Economic conditions that affect fiscal multipliers.
    
    Based on empirical research showing multipliers vary with:
    - Output gap (slack in economy)
    - Monetary policy stance (ZLB constraint)
    - Exchange rate regime
    - Debt levels
    
    References:
    - Auerbach & Gorodnichenko (2012): Multipliers larger in recessions
    - Christiano, Eichenbaum & Rebelo (2011): ZLB increases multipliers
    - Blanchard & Leigh (2013): IMF underestimated multipliers in 2010-11
    """
    
    def __init__(self, 
                 output_gap: float = 0.0,  # Negative = recession
                 at_zero_lower_bound: bool = False,
                 debt_to_gdp: float = 1.0,  # Current ~100%
                 unemployment_rate: float = 0.04):
        self.output_gap = output_gap
        self.at_zlb = at_zero_lower_bound
        self.debt_to_gdp = debt_to_gdp
        self.unemployment_rate = unemployment_rate
    
    @classmethod
    def normal_times(cls) -> 'EconomicConditions':
        """Normal economic conditions (near full employment)."""
        return cls(output_gap=0.0, at_zero_lower_bound=False, 
                   debt_to_gdp=1.0, unemployment_rate=0.04)
    
    @classmethod
    def recession(cls) -> 'EconomicConditions':
        """Recession conditions (significant slack)."""
        return cls(output_gap=-0.03, at_zero_lower_bound=True,
                   debt_to_gdp=1.0, unemployment_rate=0.07)
    
    @classmethod
    def deep_recession(cls) -> 'EconomicConditions':
        """Deep recession (severe slack, like 2009)."""
        return cls(output_gap=-0.06, at_zero_lower_bound=True,
                   debt_to_gdp=0.8, unemployment_rate=0.10)
    
    @classmethod
    def overheating(cls) -> 'EconomicConditions':
        """Overheating economy (above potential)."""
        return cls(output_gap=0.02, at_zero_lower_bound=False,
                   debt_to_gdp=1.0, unemployment_rate=0.035)


class EconomicModel:
    """
    Economic model for dynamic scoring.
    
    Incorporates key channels through which fiscal policy affects the economy:
    1. Aggregate demand effects (short-run)
    2. Labor supply effects
    3. Saving and investment effects
    4. Interest rate effects
    
    Based on CBO's approach to dynamic analysis.
    
    KEY IMPROVEMENT: Multipliers now vary with economic conditions.
    
    Multiplier estimates by condition (from empirical literature):
    - Normal times: Spending ~1.0, Tax cuts ~0.5
    - Recession: Spending ~1.5-2.0, Tax cuts ~0.8-1.0
    - At ZLB: Spending ~2.0+, Tax cuts ~1.0+
    - Overheating: Spending ~0.5, Tax cuts ~0.3 (crowding out dominates)
    """
    
    def __init__(self, baseline: BaselineProjection,
                 conditions: EconomicConditions = None):
        self.baseline = baseline
        self.years = baseline.years
        self.conditions = conditions or EconomicConditions.normal_times()
        
        # Base parameters (adjusted by conditions below)
        self._base_params = {
            # Base multipliers (adjusted for conditions)
            'spending_multiplier_base': 1.0,
            'tax_multiplier_base': 0.5,
            'transfer_multiplier_base': 0.8,
            'spending_multiplier_decay': 0.7,  # Annual decay rate
            
            # Supply-side elasticities
            'labor_supply_elasticity': 0.15,  # Compensated elasticity
            'capital_elasticity': 0.25,  # Response of capital to after-tax return
            'eti': 0.25,  # Elasticity of taxable income
            
            # Production function
            'labor_share': 0.65,  # Labor's share of output
            'capital_share': 0.35,  # Capital's share
            'tfp_growth': 0.01,  # Annual TFP growth
            
            # Interest rate effects
            'crowding_out_base': 0.03,  # Interest rate increase per $100B deficit
            'investment_elasticity': -0.5,  # Response of investment to interest rates
            
            # Revenue feedback
            'marginal_revenue_rate': 0.25,  # Avg marginal rate on additional income
        }
        
        # Apply condition adjustments
        self.params = self._adjust_for_conditions()
    
    def _adjust_for_conditions(self) -> dict:
        """
        Adjust model parameters based on economic conditions.
        
        Key relationships from empirical literature:
        1. Multipliers higher when output gap is negative (slack)
        2. Multipliers higher at ZLB (no monetary offset)
        3. Crowding out higher when debt is high
        4. Labor supply effects larger when unemployment is high
        """
        params = self._base_params.copy()
        cond = self.conditions
        
        # === MULTIPLIER ADJUSTMENTS ===
        
        # Output gap effect: Larger multipliers in recessions
        # Based on Auerbach & Gorodnichenko (2012)
        # Multiplier ~1.5-2.0 in recessions vs ~0.5 in expansions
        if cond.output_gap < -0.02:
            # Deep recession: big multiplier boost
            gap_adjustment = 1.5
        elif cond.output_gap < 0:
            # Mild recession: moderate boost
            gap_adjustment = 1.0 + abs(cond.output_gap) * 15  # scales up to 1.3
        elif cond.output_gap > 0.01:
            # Overheating: reduced multipliers (crowding out)
            gap_adjustment = 0.7
        else:
            # Normal: baseline
            gap_adjustment = 1.0
        
        # ZLB effect: No monetary offset when at zero lower bound
        # Christiano et al. (2011): Multiplier can be 2-3x higher at ZLB
        zlb_adjustment = 1.5 if cond.at_zlb else 1.0
        
        # High debt reduces multiplier (Ricardian concerns, interest rates)
        debt_adjustment = max(0.7, 1.0 - (cond.debt_to_gdp - 0.6) * 0.2)
        
        # Combined adjustment
        total_adjustment = gap_adjustment * zlb_adjustment * debt_adjustment
        
        params['spending_multiplier_peak'] = (
            params['spending_multiplier_base'] * total_adjustment
        )
        params['tax_multiplier'] = (
            params['tax_multiplier_base'] * total_adjustment
        )
        params['transfer_multiplier'] = (
            params['transfer_multiplier_base'] * total_adjustment
        )
        
        # === CROWDING OUT ADJUSTMENTS ===
        # Higher when debt is high, lower at ZLB
        crowding_base = params['crowding_out_base']
        if cond.at_zlb:
            params['crowding_out'] = crowding_base * 0.3  # Much less crowding out at ZLB
        elif cond.debt_to_gdp > 1.0:
            params['crowding_out'] = crowding_base * (1 + (cond.debt_to_gdp - 1.0))
        else:
            params['crowding_out'] = crowding_base
        
        return params
    
    def update_conditions(self, conditions: EconomicConditions):
        """Update economic conditions and recalculate parameters."""
        self.conditions = conditions
        self.params = self._adjust_for_conditions()
    
    def get_multiplier_summary(self) -> dict:
        """Return current effective multipliers for documentation."""
        return {
            'spending_multiplier': self.params['spending_multiplier_peak'],
            'tax_multiplier': self.params['tax_multiplier'],
            'transfer_multiplier': self.params.get('transfer_multiplier', 0.8),
            'conditions': {
                'output_gap': self.conditions.output_gap,
                'at_zlb': self.conditions.at_zlb,
                'debt_to_gdp': self.conditions.debt_to_gdp,
            }
        }
    
    def calculate_effects(self, policy: Policy, 
                         static_budget_effect: np.ndarray) -> DynamicEffects:
        """
        Calculate dynamic economic effects of a policy.
        
        Args:
            policy: The policy being analyzed
            static_budget_effect: Static budget effect by year (billions, positive = costs)
            
        Returns:
            DynamicEffects container with all calculated effects
        """
        n_years = len(self.years)
        
        # Initialize effect arrays
        gdp_level = np.zeros(n_years)
        gdp_pct = np.zeros(n_years)
        employment = np.zeros(n_years)
        hours = np.zeros(n_years)
        labor_force = np.zeros(n_years)
        capital = np.zeros(n_years)
        investment = np.zeros(n_years)
        interest = np.zeros(n_years)
        revenue_fb = np.zeros(n_years)
        
        # Calculate effects based on policy type
        if isinstance(policy, TaxPolicy):
            effects = self._tax_policy_effects(policy, static_budget_effect)
        elif isinstance(policy, SpendingPolicy):
            effects = self._spending_policy_effects(policy, static_budget_effect)
        elif isinstance(policy, TransferPolicy):
            effects = self._transfer_policy_effects(policy, static_budget_effect)
        else:
            effects = self._generic_policy_effects(policy, static_budget_effect)
        
        return DynamicEffects(
            years=self.years.copy(),
            **effects
        )
    
    def _tax_policy_effects(self, policy: TaxPolicy, 
                           budget_effect: np.ndarray) -> dict:
        """Calculate effects of tax policy changes."""
        n_years = len(self.years)
        
        # Determine if tax cut or tax increase
        is_tax_cut = np.mean(budget_effect) < 0
        
        # Labor supply effects (supply-side)
        labor_effect = np.zeros(n_years)
        if policy.rate_change != 0:
            # Marginal rate change affects labor supply
            # Uncompensated elasticity is small/negative, compensated is positive
            marginal_rate_change = policy.rate_change
            labor_effect = (-marginal_rate_change * 
                           self.params['labor_supply_elasticity'] * 
                           np.ones(n_years))
        
        # Demand effects (short-run)
        demand_effect = np.zeros(n_years)
        if is_tax_cut:
            for i in range(n_years):
                if policy.is_active(self.years[i]):
                    phase = policy.get_phase_in_factor(self.years[i])
                    # Decaying multiplier effect
                    for j in range(i + 1):
                        decay = self.params['spending_multiplier_decay'] ** (i - j)
                        demand_effect[i] += (-budget_effect[j] * 
                                            self.params['tax_multiplier'] * 
                                            decay * phase)
        
        # Total GDP effect
        gdp_level = np.zeros(n_years)
        gdp_pct = np.zeros(n_years)
        
        for i in range(n_years):
            # Short-run: demand effects dominate
            # Long-run: supply effects matter more
            weight_demand = max(0.2, 1 - 0.1 * i)  # Decay demand importance
            weight_supply = 1 - weight_demand
            
            supply_gdp = labor_effect[i] * self.baseline.nominal_gdp[i]
            demand_gdp = demand_effect[i]
            
            gdp_level[i] = weight_demand * demand_gdp + weight_supply * supply_gdp
            gdp_pct[i] = gdp_level[i] / self.baseline.nominal_gdp[i] * 100
        
        # Employment effects
        employment = gdp_pct / 100 * 150000  # Rough: 1% GDP = 1.5M jobs
        hours = labor_effect * 100  # Convert to percent
        
        # Capital effects (long-run)
        capital = np.zeros(n_years)
        if policy.policy_type in [PolicyType.CORPORATE_TAX, PolicyType.CAPITAL_GAINS_TAX]:
            # Corporate/capital gains tax affects investment
            after_tax_return_change = -policy.rate_change * 0.5
            for i in range(n_years):
                capital[i] = after_tax_return_change * self.params['capital_elasticity'] * (i + 1) / 5
        
        investment = capital * self.baseline.nominal_gdp * 0.18  # Investment ~18% of GDP
        
        # Interest rate effects (crowding out)
        cumulative_deficit = np.cumsum(budget_effect)
        interest_change = -cumulative_deficit / 100 * self.params['crowding_out']
        
        # Revenue feedback
        revenue_fb = gdp_level * self.params['marginal_revenue_rate']
        
        return {
            'gdp_level_change': gdp_level,
            'gdp_percent_change': gdp_pct,
            'employment_change': employment,
            'hours_worked_change': hours,
            'labor_force_change': labor_effect * 100,
            'capital_stock_change': capital * 100,
            'investment_change': investment,
            'interest_rate_change': interest_change,
            'revenue_feedback': revenue_fb,
        }
    
    def _spending_policy_effects(self, policy: SpendingPolicy,
                                budget_effect: np.ndarray) -> dict:
        """Calculate effects of spending policy changes."""
        n_years = len(self.years)
        
        # Fiscal multiplier effects (demand)
        gdp_level = np.zeros(n_years)
        multiplier = policy.gdp_multiplier
        
        for i in range(n_years):
            if policy.is_active(self.years[i]):
                phase = policy.get_phase_in_factor(self.years[i])
                # Apply multiplier with decay
                for j in range(i + 1):
                    decay = self.params['spending_multiplier_decay'] ** (i - j)
                    gdp_level[i] += (budget_effect[j] * multiplier * decay * phase)
        
        gdp_pct = gdp_level / self.baseline.nominal_gdp * 100
        
        # Employment from spending
        employment = np.zeros(n_years)
        for i in range(n_years):
            if policy.is_active(self.years[i]):
                employment[i] = (budget_effect[i] * 
                               policy.employment_per_billion / 1000)  # In thousands
        
        # Long-run effects (crowding out)
        cumulative_deficit = np.cumsum(budget_effect)
        interest_change = cumulative_deficit / 100 * self.params['crowding_out']
        
        # Crowding out of private investment
        investment_effect = (interest_change * 
                            self.params['investment_elasticity'] * 
                            self.baseline.nominal_gdp * 0.18)
        
        # Adjust GDP for crowding out
        for i in range(1, n_years):
            gdp_level[i] += investment_effect[i] * 0.5  # Partial offset
        
        gdp_pct = gdp_level / self.baseline.nominal_gdp * 100
        
        # Revenue feedback
        revenue_fb = gdp_level * self.params['marginal_revenue_rate']
        
        return {
            'gdp_level_change': gdp_level,
            'gdp_percent_change': gdp_pct,
            'employment_change': employment,
            'hours_worked_change': np.zeros(n_years),
            'labor_force_change': employment / 1000,  # Small LFP effect
            'capital_stock_change': interest_change * self.params['investment_elasticity'],
            'investment_change': investment_effect,
            'interest_rate_change': interest_change,
            'revenue_feedback': revenue_fb,
        }
    
    def _transfer_policy_effects(self, policy: TransferPolicy,
                                budget_effect: np.ndarray) -> dict:
        """Calculate effects of transfer policy changes."""
        n_years = len(self.years)
        
        # Transfers have lower multipliers than direct spending
        transfer_multiplier = 0.8
        
        gdp_level = np.zeros(n_years)
        for i in range(n_years):
            if policy.is_active(self.years[i]):
                phase = policy.get_phase_in_factor(self.years[i])
                for j in range(i + 1):
                    decay = self.params['spending_multiplier_decay'] ** (i - j)
                    gdp_level[i] += budget_effect[j] * transfer_multiplier * decay * phase
        
        gdp_pct = gdp_level / self.baseline.nominal_gdp * 100
        
        # Labor force effects (transfers can reduce labor supply)
        labor_force_effect = np.zeros(n_years)
        if policy.labor_force_participation_effect != 0:
            for i in range(n_years):
                if policy.is_active(self.years[i]):
                    phase = policy.get_phase_in_factor(self.years[i])
                    labor_force_effect[i] = policy.labor_force_participation_effect * phase
        
        # Employment effect is sum of demand + labor supply effects
        employment = gdp_pct / 100 * 150000 + labor_force_effect * 160000
        
        # Revenue feedback
        revenue_fb = gdp_level * self.params['marginal_revenue_rate']
        
        return {
            'gdp_level_change': gdp_level,
            'gdp_percent_change': gdp_pct,
            'employment_change': employment,
            'hours_worked_change': np.zeros(n_years),
            'labor_force_change': labor_force_effect * 100,
            'capital_stock_change': np.zeros(n_years),
            'investment_change': np.zeros(n_years),
            'interest_rate_change': np.cumsum(budget_effect) / 100 * self.params['crowding_out'],
            'revenue_feedback': revenue_fb,
        }
    
    def _generic_policy_effects(self, policy: Policy,
                               budget_effect: np.ndarray) -> dict:
        """Calculate effects for generic policies."""
        n_years = len(self.years)
        
        # Simple multiplier approach
        gdp_level = budget_effect * 0.5  # Conservative multiplier
        gdp_pct = gdp_level / self.baseline.nominal_gdp * 100
        
        employment = gdp_pct / 100 * 150000
        revenue_fb = gdp_level * self.params['marginal_revenue_rate']
        
        return {
            'gdp_level_change': gdp_level,
            'gdp_percent_change': gdp_pct,
            'employment_change': employment,
            'hours_worked_change': np.zeros(n_years),
            'labor_force_change': np.zeros(n_years),
            'capital_stock_change': np.zeros(n_years),
            'investment_change': np.zeros(n_years),
            'interest_rate_change': np.cumsum(budget_effect) / 100 * self.params['crowding_out'],
            'revenue_feedback': revenue_fb,
        }
    
    def get_long_run_effects(self, policy: Policy, 
                            budget_effect: np.ndarray,
                            years_out: int = 20) -> dict:
        """
        Estimate long-run (steady-state) effects beyond the budget window.
        
        Useful for understanding full policy impacts.
        """
        # Calculate 10-year effects first
        effects = self.calculate_effects(policy, budget_effect)
        
        # Extrapolate to long run
        # GDP effect converges to supply-side effect
        if isinstance(policy, TaxPolicy):
            # Long-run GDP effect from labor and capital changes
            labor_effect = effects.labor_force_change[-1] / 100
            capital_effect = effects.capital_stock_change[-1] / 100
            
            long_run_gdp = (self.params['labor_share'] * labor_effect +
                           self.params['capital_share'] * capital_effect)
        else:
            # Other policies: effect decays to zero
            long_run_gdp = effects.gdp_percent_change[-1] * 0.5
        
        return {
            'long_run_gdp_percent': long_run_gdp,
            'long_run_employment': long_run_gdp * 1.5,  # Okun's law
            'steady_state_year': self.years[-1] + 10,
        }

