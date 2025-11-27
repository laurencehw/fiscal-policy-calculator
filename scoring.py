"""
Fiscal Policy Scoring Engine

Main scoring logic combining static and dynamic analysis.
"""

from dataclasses import dataclass, field
import numpy as np
from typing import Optional, Union, Literal

from .policies import (
    Policy, TaxPolicy, SpendingPolicy, TransferPolicy, 
    PolicyPackage, PolicyType
)
from .baseline import BaselineProjection, CBOBaseline
from .economics import EconomicModel, DynamicEffects


@dataclass
class ScoringResult:
    """
    Complete scoring results for a fiscal policy.
    """
    policy: Policy
    baseline: BaselineProjection
    
    # Budget window
    years: np.ndarray
    
    # Static effects (before behavioral/economic feedback)
    static_revenue_effect: np.ndarray  # Billions, negative = revenue loss
    static_spending_effect: np.ndarray  # Billions, positive = spending increase
    static_deficit_effect: np.ndarray  # Net effect on deficit
    
    # Behavioral effects (microeconomic responses)
    behavioral_offset: np.ndarray  # Revenue offset from behavioral response
    
    # Dynamic effects (macroeconomic feedback)
    dynamic_effects: Optional[DynamicEffects] = None
    
    # Final estimates
    final_deficit_effect: np.ndarray = field(default_factory=lambda: np.zeros(10))
    
    # Uncertainty
    low_estimate: np.ndarray = field(default_factory=lambda: np.zeros(10))
    high_estimate: np.ndarray = field(default_factory=lambda: np.zeros(10))
    
    @property
    def is_dynamic(self) -> bool:
        """Whether dynamic scoring was applied."""
        return self.dynamic_effects is not None
    
    @property
    def total_10_year_cost(self) -> float:
        """Total 10-year cost (positive = increases deficit)."""
        return np.sum(self.final_deficit_effect)
    
    @property
    def total_static_cost(self) -> float:
        """Total 10-year static cost."""
        return np.sum(self.static_deficit_effect)
    
    @property
    def revenue_feedback_10yr(self) -> float:
        """Total revenue feedback from economic effects."""
        if self.dynamic_effects:
            return np.sum(self.dynamic_effects.revenue_feedback)
        return 0.0
    
    @property
    def average_annual_cost(self) -> float:
        """Average annual cost."""
        return self.total_10_year_cost / len(self.years)
    
    def get_year_effect(self, year: int) -> dict:
        """Get detailed effects for a specific year."""
        idx = year - self.years[0]
        result = {
            'year': year,
            'static_revenue': self.static_revenue_effect[idx],
            'static_spending': self.static_spending_effect[idx],
            'static_deficit': self.static_deficit_effect[idx],
            'behavioral_offset': self.behavioral_offset[idx],
            'final_deficit': self.final_deficit_effect[idx],
            'low_estimate': self.low_estimate[idx],
            'high_estimate': self.high_estimate[idx],
        }
        
        if self.dynamic_effects:
            result.update({
                'gdp_effect': self.dynamic_effects.gdp_level_change[idx],
                'gdp_pct': self.dynamic_effects.gdp_percent_change[idx],
                'employment': self.dynamic_effects.employment_change[idx],
                'revenue_feedback': self.dynamic_effects.revenue_feedback[idx],
            })
        
        return result
    
    def to_dataframe(self):
        """Convert results to pandas DataFrame."""
        import pandas as pd
        
        data = {
            'Year': self.years,
            'Static Revenue Effect ($B)': self.static_revenue_effect,
            'Static Spending Effect ($B)': self.static_spending_effect,
            'Static Deficit Effect ($B)': self.static_deficit_effect,
            'Behavioral Offset ($B)': self.behavioral_offset,
            'Final Deficit Effect ($B)': self.final_deficit_effect,
            'Low Estimate ($B)': self.low_estimate,
            'High Estimate ($B)': self.high_estimate,
        }
        
        if self.dynamic_effects:
            data.update({
                'GDP Effect ($B)': self.dynamic_effects.gdp_level_change,
                'GDP Effect (%)': self.dynamic_effects.gdp_percent_change,
                'Employment (thousands)': self.dynamic_effects.employment_change,
                'Revenue Feedback ($B)': self.dynamic_effects.revenue_feedback,
            })
        
        return pd.DataFrame(data)
    
    def display_summary(self):
        """Print a formatted summary of results."""
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel
        
        console = Console()
        
        # Header
        console.print(Panel(
            f"[bold blue]{self.policy.name}[/bold blue]\n{self.policy.description}",
            title="Fiscal Policy Score"
        ))
        
        # Summary stats
        console.print(f"\n[bold]10-Year Budget Impact:[/bold]")
        console.print(f"  Static Cost: ${self.total_static_cost:,.1f} billion")
        if self.is_dynamic:
            console.print(f"  Revenue Feedback: ${self.revenue_feedback_10yr:,.1f} billion")
        console.print(f"  [bold]Final Cost: ${self.total_10_year_cost:,.1f} billion[/bold]")
        console.print(f"  Range: ${np.sum(self.low_estimate):,.1f}B to ${np.sum(self.high_estimate):,.1f}B")
        
        # Year-by-year table
        table = Table(title="\nYear-by-Year Effects ($ billions)")
        
        table.add_column("Year", style="cyan")
        table.add_column("Static", justify="right")
        table.add_column("Behavioral", justify="right")
        if self.is_dynamic:
            table.add_column("Feedback", justify="right")
        table.add_column("Final", justify="right", style="bold")
        table.add_column("Range", justify="right")
        
        for i, year in enumerate(self.years):
            row = [
                str(year),
                f"{self.static_deficit_effect[i]:,.1f}",
                f"{self.behavioral_offset[i]:,.1f}",
            ]
            if self.is_dynamic:
                row.append(f"{self.dynamic_effects.revenue_feedback[i]:,.1f}")
            row.extend([
                f"{self.final_deficit_effect[i]:,.1f}",
                f"{self.low_estimate[i]:,.1f} to {self.high_estimate[i]:,.1f}"
            ])
            table.add_row(*row)
        
        # Totals row
        total_row = [
            "[bold]Total[/bold]",
            f"[bold]{self.total_static_cost:,.1f}[/bold]",
            f"[bold]{np.sum(self.behavioral_offset):,.1f}[/bold]",
        ]
        if self.is_dynamic:
            total_row.append(f"[bold]{self.revenue_feedback_10yr:,.1f}[/bold]")
        total_row.extend([
            f"[bold]{self.total_10_year_cost:,.1f}[/bold]",
            f"[bold]{np.sum(self.low_estimate):,.1f} to {np.sum(self.high_estimate):,.1f}[/bold]"
        ])
        table.add_row(*total_row)
        
        console.print(table)
        
        # Economic effects if dynamic
        if self.is_dynamic:
            console.print(f"\n[bold]Economic Effects (10-year average):[/bold]")
            console.print(f"  GDP: {np.mean(self.dynamic_effects.gdp_percent_change):.2f}%")
            console.print(f"  Employment: {np.mean(self.dynamic_effects.employment_change):,.0f} thousand jobs")


class FiscalPolicyScorer:
    """
    Main scoring engine for fiscal policy analysis.
    
    Implements CBO-style scoring methodology with both static
    and dynamic options.
    """
    
    def __init__(self, baseline: Optional[BaselineProjection] = None,
                 start_year: int = 2025,
                 use_real_data: bool = True):
        """
        Initialize the scorer.

        Args:
            baseline: Pre-computed baseline projection (optional)
            start_year: Start year for analysis
            use_real_data: If True, load baseline from IRS/FRED data.
                          If False, use hardcoded fallback values.
        """
        self.start_year = start_year

        if baseline is None:
            generator = CBOBaseline(start_year=start_year, use_real_data=use_real_data)
            self.baseline = generator.generate()
        else:
            self.baseline = baseline

        self.economic_model = EconomicModel(self.baseline)
    
    def score_policy(self, policy: Policy, 
                    dynamic: bool = False,
                    include_uncertainty: bool = True) -> ScoringResult:
        """
        Score a fiscal policy proposal.
        
        Args:
            policy: Policy to score
            dynamic: Whether to include dynamic/macroeconomic effects
            include_uncertainty: Whether to calculate uncertainty ranges
            
        Returns:
            ScoringResult with complete analysis
        """
        years = self.baseline.years
        n_years = len(years)
        
        # Initialize effect arrays
        static_revenue = np.zeros(n_years)
        static_spending = np.zeros(n_years)
        behavioral = np.zeros(n_years)
        
        # Calculate static effects based on policy type
        if isinstance(policy, TaxPolicy):
            static_revenue, behavioral = self._score_tax_policy(policy)
            static_spending = np.zeros(n_years)
            
        elif isinstance(policy, SpendingPolicy):
            static_revenue = np.zeros(n_years)
            static_spending = self._score_spending_policy(policy)
            behavioral = np.zeros(n_years)
            
        elif isinstance(policy, TransferPolicy):
            static_revenue = np.zeros(n_years)
            static_spending = self._score_transfer_policy(policy)
            behavioral = np.zeros(n_years)
        
        # Static deficit effect (positive = increases deficit)
        static_deficit = static_spending - static_revenue
        
        # Apply behavioral offset
        deficit_after_behavioral = static_deficit + behavioral
        
        # Dynamic scoring if requested
        dynamic_effects = None
        if dynamic:
            dynamic_effects = self.economic_model.calculate_effects(
                policy, deficit_after_behavioral
            )
            # Revenue feedback reduces deficit impact
            final_deficit = deficit_after_behavioral - dynamic_effects.revenue_feedback
        else:
            final_deficit = deficit_after_behavioral
        
        # Uncertainty ranges
        if include_uncertainty:
            low, high = self._calculate_uncertainty(
                policy, final_deficit, dynamic_effects
            )
        else:
            low = final_deficit.copy()
            high = final_deficit.copy()
        
        return ScoringResult(
            policy=policy,
            baseline=self.baseline,
            years=years,
            static_revenue_effect=static_revenue,
            static_spending_effect=static_spending,
            static_deficit_effect=static_deficit,
            behavioral_offset=behavioral,
            dynamic_effects=dynamic_effects,
            final_deficit_effect=final_deficit,
            low_estimate=low,
            high_estimate=high,
        )
    
    def score_package(self, package: PolicyPackage,
                     dynamic: bool = False) -> ScoringResult:
        """
        Score a package of policies together.
        
        Accounts for interactions between policies.
        """
        # Score each policy
        results = [self.score_policy(p, dynamic=dynamic) for p in package.policies]
        
        # Aggregate effects
        n_years = len(self.baseline.years)
        
        total_static_revenue = np.zeros(n_years)
        total_static_spending = np.zeros(n_years)
        total_behavioral = np.zeros(n_years)
        
        for r in results:
            total_static_revenue += r.static_revenue_effect
            total_static_spending += r.static_spending_effect
            total_behavioral += r.behavioral_offset
        
        # Apply interaction factor
        total_static_revenue *= package.interaction_factor
        total_static_spending *= package.interaction_factor
        
        static_deficit = total_static_spending - total_static_revenue
        deficit_after_behavioral = static_deficit + total_behavioral
        
        # Aggregate dynamic effects
        if dynamic:
            # Combine dynamic effects (simplified aggregation)
            combined_dynamic = self._aggregate_dynamic_effects(results)
            final_deficit = deficit_after_behavioral - combined_dynamic.revenue_feedback
        else:
            combined_dynamic = None
            final_deficit = deficit_after_behavioral
        
        low, high = self._calculate_uncertainty(
            package.policies[0], final_deficit, combined_dynamic
        )
        
        # Create synthetic policy for package
        synthetic = Policy(
            name=package.name,
            description=package.description,
            policy_type=PolicyType.MANDATORY_SPENDING,
            start_year=min(p.start_year for p in package.policies),
        )
        
        return ScoringResult(
            policy=synthetic,
            baseline=self.baseline,
            years=self.baseline.years,
            static_revenue_effect=total_static_revenue,
            static_spending_effect=total_static_spending,
            static_deficit_effect=static_deficit,
            behavioral_offset=total_behavioral,
            dynamic_effects=combined_dynamic,
            final_deficit_effect=final_deficit,
            low_estimate=low,
            high_estimate=high,
        )
    
    def _score_tax_policy(self, policy: TaxPolicy) -> tuple[np.ndarray, np.ndarray]:
        """Calculate static revenue effect and behavioral offset for tax policy."""
        n_years = len(self.baseline.years)
        revenue = np.zeros(n_years)
        behavioral = np.zeros(n_years)
        
        for i, year in enumerate(self.baseline.years):
            if not policy.is_active(year):
                continue
            
            phase = policy.get_phase_in_factor(year)
            
            # Get relevant baseline revenue
            if policy.policy_type == PolicyType.INCOME_TAX:
                base_rev = self.baseline.individual_income_tax[i]
            elif policy.policy_type == PolicyType.CORPORATE_TAX:
                base_rev = self.baseline.corporate_income_tax[i]
            elif policy.policy_type == PolicyType.PAYROLL_TAX:
                base_rev = self.baseline.payroll_taxes[i]
            else:
                base_rev = self.baseline.individual_income_tax[i]  # Default
            
            # Static effect
            static_annual = policy.estimate_static_revenue_effect(base_rev)
            revenue[i] = static_annual * phase
            
            # Behavioral offset (reduces revenue gain from tax increases,
            # reduces revenue loss from tax cuts)
            behavioral[i] = policy.estimate_behavioral_offset(revenue[i])
        
        return revenue, behavioral
    
    def _score_spending_policy(self, policy: SpendingPolicy) -> np.ndarray:
        """Calculate static spending effect for spending policy."""
        n_years = len(self.baseline.years)
        spending = np.zeros(n_years)
        
        for i, year in enumerate(self.baseline.years):
            spending[i] = policy.get_spending_in_year(year)
        
        return spending
    
    def _score_transfer_policy(self, policy: TransferPolicy) -> np.ndarray:
        """Calculate static cost effect for transfer policy."""
        n_years = len(self.baseline.years)
        cost = np.zeros(n_years)
        
        for i, year in enumerate(self.baseline.years):
            if not policy.is_active(year):
                continue
            
            phase = policy.get_phase_in_factor(year)
            
            # Get relevant baseline cost
            if policy.policy_type == PolicyType.SOCIAL_SECURITY:
                base_cost = self.baseline.social_security[i]
            elif policy.policy_type == PolicyType.MEDICARE:
                base_cost = self.baseline.medicare[i]
            elif policy.policy_type == PolicyType.MEDICAID:
                base_cost = self.baseline.medicaid[i]
            else:
                base_cost = self.baseline.other_mandatory[i]
            
            cost[i] = policy.estimate_cost_effect(base_cost) * phase
        
        return cost
    
    def _aggregate_dynamic_effects(self, 
                                   results: list[ScoringResult]) -> DynamicEffects:
        """Aggregate dynamic effects from multiple policies."""
        n_years = len(self.baseline.years)
        
        # Sum up effects (simplified - ignores interactions)
        gdp_level = np.zeros(n_years)
        gdp_pct = np.zeros(n_years)
        employment = np.zeros(n_years)
        revenue_fb = np.zeros(n_years)
        
        for r in results:
            if r.dynamic_effects:
                gdp_level += r.dynamic_effects.gdp_level_change
                gdp_pct += r.dynamic_effects.gdp_percent_change
                employment += r.dynamic_effects.employment_change
                revenue_fb += r.dynamic_effects.revenue_feedback
        
        return DynamicEffects(
            years=self.baseline.years.copy(),
            gdp_level_change=gdp_level,
            gdp_percent_change=gdp_pct,
            employment_change=employment,
            hours_worked_change=np.zeros(n_years),
            labor_force_change=np.zeros(n_years),
            capital_stock_change=np.zeros(n_years),
            investment_change=np.zeros(n_years),
            interest_rate_change=np.zeros(n_years),
            revenue_feedback=revenue_fb,
        )
    
    def _calculate_uncertainty(self, 
                              policy: Policy,
                              central: np.ndarray,
                              dynamic: Optional[DynamicEffects]) -> tuple[np.ndarray, np.ndarray]:
        """
        Calculate uncertainty ranges.
        
        Uses multiplicative factors that increase with forecast horizon,
        consistent with CBO uncertainty analysis.
        """
        n_years = len(central)
        
        # Base uncertainty (increases with time)
        base_uncertainty = np.array([0.10 + 0.02 * i for i in range(n_years)])
        
        # Adjust for policy type (some are more uncertain)
        if isinstance(policy, TaxPolicy):
            # Tax revenue is harder to predict
            policy_factor = 1.2
        elif isinstance(policy, SpendingPolicy):
            # Direct spending is more predictable
            policy_factor = 0.8
        else:
            policy_factor = 1.0
        
        # Increase uncertainty for dynamic estimates
        if dynamic is not None:
            dynamic_factor = 1.5
        else:
            dynamic_factor = 1.0
        
        total_uncertainty = base_uncertainty * policy_factor * dynamic_factor
        
        # Calculate ranges (asymmetric - costs tend to be higher than estimated)
        low = central * (1 - total_uncertainty * 0.9)
        high = central * (1 + total_uncertainty * 1.1)
        
        return low, high


def quick_score(policy: Policy, dynamic: bool = False) -> ScoringResult:
    """
    Convenience function for quick policy scoring.
    
    Example:
        result = quick_score(TaxPolicy(...))
        print(f"10-year cost: ${result.total_10_year_cost:.1f}B")
    """
    scorer = FiscalPolicyScorer()
    return scorer.score_policy(policy, dynamic=dynamic)

