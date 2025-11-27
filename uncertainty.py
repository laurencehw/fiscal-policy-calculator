"""
Uncertainty Analysis Module

Quantifies uncertainty in budget estimates following CBO methodology.
Provides range estimates and sensitivity analysis.
"""

from dataclasses import dataclass, field
import numpy as np
from typing import Optional, Literal
from scipy import stats

from .policies import Policy, TaxPolicy, SpendingPolicy, TransferPolicy
from .baseline import BaselineProjection


@dataclass
class UncertaintyFactors:
    """
    Sources of uncertainty in budget projections.
    """
    # Economic forecast uncertainty
    gdp_growth_std: float = 0.015  # Std dev of GDP growth error
    inflation_std: float = 0.008  # Std dev of inflation error
    interest_rate_std: float = 0.005  # Std dev of interest rate error
    unemployment_std: float = 0.01  # Std dev of unemployment error
    
    # Revenue projection uncertainty
    individual_tax_cv: float = 0.08  # Coefficient of variation
    corporate_tax_cv: float = 0.20  # Higher for corporate (volatile)
    payroll_tax_cv: float = 0.04  # Lower (more stable)
    
    # Spending projection uncertainty
    mandatory_cv: float = 0.05
    discretionary_cv: float = 0.03  # Lower (set by appropriations)
    interest_cv: float = 0.10  # Depends on rates and debt
    
    # Policy-specific uncertainty
    behavioral_response_cv: float = 0.50  # High uncertainty
    participation_cv: float = 0.30  # Take-up rates


@dataclass
class SensitivityResult:
    """
    Results from sensitivity analysis.
    """
    parameter_name: str
    parameter_values: np.ndarray
    deficit_effects: np.ndarray
    elasticity: float  # Percent change in deficit per 1% change in parameter
    
    @property
    def range(self) -> tuple[float, float]:
        return (np.min(self.deficit_effects), np.max(self.deficit_effects))


class UncertaintyAnalysis:
    """
    Comprehensive uncertainty analysis for fiscal projections.
    """
    
    def __init__(self, factors: Optional[UncertaintyFactors] = None):
        self.factors = factors or UncertaintyFactors()
        
        # Correlation matrix for economic variables
        # (GDP, inflation, unemployment, interest rates)
        self.econ_correlation = np.array([
            [1.0, 0.3, -0.6, 0.2],
            [0.3, 1.0, -0.2, 0.5],
            [-0.6, -0.2, 1.0, -0.1],
            [0.2, 0.5, -0.1, 1.0]
        ])
    
    def calculate_baseline_uncertainty(self, 
                                       baseline: BaselineProjection,
                                       percentile: float = 0.9) -> dict:
        """
        Calculate uncertainty ranges for baseline projections.
        
        Args:
            baseline: Baseline projection
            percentile: Percentile for confidence interval (default 90%)
            
        Returns:
            Dictionary with low/high estimates for major categories
        """
        n_years = len(baseline.years)
        z_score = stats.norm.ppf((1 + percentile) / 2)
        
        # Time-increasing uncertainty
        time_factor = np.sqrt(np.arange(1, n_years + 1))
        
        results = {}
        
        # Revenue uncertainty
        for cat, cv in [
            ('individual_income_tax', self.factors.individual_tax_cv),
            ('corporate_income_tax', self.factors.corporate_tax_cv),
            ('payroll_taxes', self.factors.payroll_tax_cv),
        ]:
            values = getattr(baseline, cat)
            std = values * cv * time_factor / np.sqrt(n_years)
            results[cat] = {
                'central': values,
                'low': values - z_score * std,
                'high': values + z_score * std,
            }
        
        # Spending uncertainty
        results['total_mandatory'] = self._calc_mandatory_uncertainty(
            baseline, z_score, time_factor
        )
        
        results['net_interest'] = {
            'central': baseline.net_interest,
            'low': baseline.net_interest * (1 - self.factors.interest_cv * z_score),
            'high': baseline.net_interest * (1 + self.factors.interest_cv * z_score),
        }
        
        # Aggregate
        results['total_deficit'] = self._aggregate_uncertainty(
            baseline, results, z_score, time_factor
        )
        
        return results
    
    def calculate_policy_uncertainty(self,
                                    policy: Policy,
                                    central_estimate: np.ndarray,
                                    percentile: float = 0.9) -> dict:
        """
        Calculate uncertainty specific to a policy proposal.
        """
        n_years = len(central_estimate)
        z_score = stats.norm.ppf((1 + percentile) / 2)
        
        # Base CV depends on policy type
        if isinstance(policy, TaxPolicy):
            base_cv = 0.15
            behavioral_cv = self.factors.behavioral_response_cv
        elif isinstance(policy, SpendingPolicy):
            base_cv = 0.10
            behavioral_cv = 0.10
        elif isinstance(policy, TransferPolicy):
            base_cv = 0.12
            behavioral_cv = self.factors.participation_cv
        else:
            base_cv = 0.15
            behavioral_cv = 0.20
        
        # Time-increasing uncertainty
        time_factor = np.array([1.0 + 0.05 * i for i in range(n_years)])
        
        # Combine sources
        total_cv = np.sqrt(base_cv**2 + behavioral_cv**2) * time_factor
        
        std = np.abs(central_estimate) * total_cv
        
        return {
            'central': central_estimate,
            'low': central_estimate - z_score * std,
            'high': central_estimate + z_score * std,
            '10th': central_estimate - 1.28 * std,
            '25th': central_estimate - 0.67 * std,
            '75th': central_estimate + 0.67 * std,
            '90th': central_estimate + 1.28 * std,
        }
    
    def monte_carlo_simulation(self,
                              policy: Policy,
                              central_estimate: np.ndarray,
                              n_simulations: int = 1000) -> dict:
        """
        Run Monte Carlo simulation for more detailed uncertainty analysis.
        """
        n_years = len(central_estimate)
        simulations = np.zeros((n_simulations, n_years))
        
        # Generate correlated economic shocks
        econ_shocks = self._generate_correlated_shocks(n_simulations, n_years)
        
        for sim in range(n_simulations):
            # Economic uncertainty
            gdp_shock = econ_shocks[sim, :, 0]
            
            # Policy-specific uncertainty
            if isinstance(policy, TaxPolicy):
                policy_shock = np.random.normal(0, 0.15, n_years)
                behavioral_shock = np.random.normal(0, 0.3, n_years)
            else:
                policy_shock = np.random.normal(0, 0.10, n_years)
                behavioral_shock = np.random.normal(0, 0.15, n_years)
            
            # Combine shocks
            total_shock = 1 + gdp_shock * 0.5 + policy_shock + behavioral_shock
            
            # Time-cumulating effect for persistent shocks
            for t in range(1, n_years):
                total_shock[t] = total_shock[t-1] * 0.3 + total_shock[t] * 0.7
            
            simulations[sim] = central_estimate * total_shock
        
        # Calculate statistics
        return {
            'mean': np.mean(simulations, axis=0),
            'median': np.median(simulations, axis=0),
            'std': np.std(simulations, axis=0),
            'p10': np.percentile(simulations, 10, axis=0),
            'p25': np.percentile(simulations, 25, axis=0),
            'p75': np.percentile(simulations, 75, axis=0),
            'p90': np.percentile(simulations, 90, axis=0),
            'simulations': simulations,
        }
    
    def sensitivity_analysis(self,
                            policy: Policy,
                            central_estimate: np.ndarray,
                            parameter: str,
                            range_pct: float = 0.5) -> SensitivityResult:
        """
        Analyze sensitivity to a specific parameter.
        
        Args:
            policy: Policy being analyzed
            central_estimate: Central cost estimate
            parameter: Parameter name to vary
            range_pct: Percentage range to test (e.g., 0.5 = ±50%)
        """
        n_points = 11
        multipliers = np.linspace(1 - range_pct, 1 + range_pct, n_points)
        
        # Map parameter to effect type
        if parameter in ['gdp_growth', 'economic_growth']:
            # Higher growth -> lower costs for transfers, higher revenue
            effect_factor = -0.5
        elif parameter in ['interest_rate', 'inflation']:
            # Higher rates -> higher interest costs
            effect_factor = 0.3
        elif parameter == 'behavioral_elasticity':
            effect_factor = 0.4
        elif parameter == 'participation_rate':
            effect_factor = 0.8
        else:
            effect_factor = 0.2
        
        # Calculate effects at each point
        effects = np.zeros((n_points, len(central_estimate)))
        for i, mult in enumerate(multipliers):
            shock = (mult - 1) * effect_factor
            effects[i] = central_estimate * (1 + shock)
        
        # 10-year totals
        totals = np.sum(effects, axis=1)
        central_total = np.sum(central_estimate)
        
        # Elasticity
        elasticity = ((totals[-1] - totals[0]) / central_total) / (2 * range_pct)
        
        return SensitivityResult(
            parameter_name=parameter,
            parameter_values=multipliers,
            deficit_effects=totals,
            elasticity=elasticity,
        )
    
    def _calc_mandatory_uncertainty(self, baseline, z_score, time_factor):
        """Calculate uncertainty for mandatory spending."""
        mandatory = (baseline.social_security + baseline.medicare + 
                    baseline.medicaid + baseline.other_mandatory)
        
        # Different CVs for different programs
        ss_std = baseline.social_security * 0.03 * time_factor
        medicare_std = baseline.medicare * 0.08 * time_factor
        medicaid_std = baseline.medicaid * 0.10 * time_factor
        other_std = baseline.other_mandatory * 0.05 * time_factor
        
        # Combined (assuming some correlation)
        total_std = np.sqrt(ss_std**2 + medicare_std**2 * 0.5 + 
                           medicaid_std**2 * 0.5 + other_std**2)
        
        return {
            'central': mandatory,
            'low': mandatory - z_score * total_std,
            'high': mandatory + z_score * total_std,
        }
    
    def _aggregate_uncertainty(self, baseline, component_results, z_score, time_factor):
        """Aggregate uncertainty accounting for correlations."""
        n_years = len(baseline.years)
        
        central = baseline.deficit
        
        # Simplified aggregation (conservative)
        revenue_std = np.sqrt(
            (component_results['individual_income_tax']['high'] - 
             component_results['individual_income_tax']['central'])**2 +
            (component_results['corporate_income_tax']['high'] - 
             component_results['corporate_income_tax']['central'])**2 +
            (component_results['payroll_taxes']['high'] - 
             component_results['payroll_taxes']['central'])**2
        )
        
        spending_std = (component_results['total_mandatory']['high'] - 
                       component_results['total_mandatory']['central'])
        
        interest_std = (component_results['net_interest']['high'] - 
                       component_results['net_interest']['central'])
        
        # Total (assuming some correlation between revenue and spending)
        total_std = np.sqrt(revenue_std**2 + spending_std**2 * 0.5 + 
                           interest_std**2 + 2 * 0.3 * revenue_std * spending_std)
        
        return {
            'central': central,
            'low': central - total_std,
            'high': central + total_std,
        }
    
    def _generate_correlated_shocks(self, n_sims: int, n_years: int) -> np.ndarray:
        """Generate correlated economic shocks."""
        # 4 economic variables: GDP, inflation, unemployment, interest
        shocks = np.zeros((n_sims, n_years, 4))
        
        # Cholesky decomposition for correlation
        L = np.linalg.cholesky(self.econ_correlation)
        
        stds = [
            self.factors.gdp_growth_std,
            self.factors.inflation_std,
            self.factors.unemployment_std,
            self.factors.interest_rate_std,
        ]
        
        for t in range(n_years):
            uncorrelated = np.random.normal(0, 1, (n_sims, 4))
            correlated = uncorrelated @ L.T
            shocks[:, t, :] = correlated * np.array(stds)
        
        return shocks
    
    def format_uncertainty_summary(self, uncertainty_dict: dict) -> str:
        """Format uncertainty results as readable text."""
        lines = ["Uncertainty Analysis Summary", "=" * 40]
        
        if 'total_deficit' in uncertainty_dict:
            deficit = uncertainty_dict['total_deficit']
            lines.append("\n10-Year Deficit Range:")
            lines.append(f"  Low (10th percentile):  ${np.sum(deficit['low']):,.0f}B")
            lines.append(f"  Central estimate:       ${np.sum(deficit['central']):,.0f}B")
            lines.append(f"  High (90th percentile): ${np.sum(deficit['high']):,.0f}B")
        
        if 'simulations' in uncertainty_dict:
            sims = uncertainty_dict['simulations']
            totals = np.sum(sims, axis=1)
            lines.append("\nMonte Carlo Results (10-year total):")
            lines.append(f"  Mean:   ${np.mean(totals):,.0f}B")
            lines.append(f"  Median: ${np.median(totals):,.0f}B")
            lines.append(f"  Std:    ${np.std(totals):,.0f}B")
            lines.append(f"  10th:   ${np.percentile(totals, 10):,.0f}B")
            lines.append(f"  90th:   ${np.percentile(totals, 90):,.0f}B")
        
        return "\n".join(lines)

