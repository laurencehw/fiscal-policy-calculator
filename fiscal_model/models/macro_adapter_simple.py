"""
Reduced-form macro adapters used for testing and quick comparisons.
"""

import numpy as np
import pandas as pd

from .macro_adapter_core import MacroModelAdapter, MacroResult, MacroScenario


class SimpleMultiplierAdapter(MacroModelAdapter):
    """
    Simple fiscal multiplier model for testing and comparison.

    Uses textbook multiplier effects without full general equilibrium.
    This is a reduced-form model that captures first-order effects.
    """

    @property
    def name(self) -> str:
        return "Simple Multiplier"

    @property
    def description(self) -> str:
        return "Reduced-form fiscal multiplier model (Keynesian)"

    def __init__(
        self,
        spending_multiplier: float = 1.0,
        tax_multiplier: float = -0.5,
        marginal_tax_rate: float = 0.25,
        multiplier_decay: float = 0.7,
    ):
        """
        Initialize simple multiplier model.

        Args:
            spending_multiplier: First-year spending multiplier
            tax_multiplier: First-year tax multiplier (negative = cuts stimulate)
            marginal_tax_rate: For revenue feedback calculation
            multiplier_decay: Annual decay rate of multiplier effects
        """
        self.spending_multiplier = spending_multiplier
        self.tax_multiplier = tax_multiplier
        self.marginal_tax_rate = marginal_tax_rate
        self.multiplier_decay = multiplier_decay

        # Baseline GDP (2025)
        self.baseline_gdp = 28_000.0  # $28T

    def run(self, scenario: MacroScenario) -> MacroResult:
        """Run simple multiplier simulation."""
        n_years = scenario.horizon_years
        years = np.arange(scenario.start_year, scenario.start_year + n_years)

        # Calculate net fiscal impulse
        receipts_chg = scenario.receipts_change  # Revenue increase = contractionary
        outlays_chg = scenario.outlays_change    # Spending increase = expansionary

        # Net fiscal impulse (billions)
        fiscal_impulse = (
            outlays_chg * self.spending_multiplier +
            receipts_chg * self.tax_multiplier
        )

        # GDP effect with decay
        gdp_change = np.zeros(n_years)
        for t in range(n_years):
            for s in range(t + 1):
                decay = self.multiplier_decay ** (t - s)
                gdp_change[t] += fiscal_impulse[s] * decay

        # Convert to percent of GDP
        gdp_level_pct = gdp_change / self.baseline_gdp * 100

        # Growth rate effect (first difference of level)
        gdp_growth_ppts = np.zeros(n_years)
        gdp_growth_ppts[0] = gdp_level_pct[0]
        gdp_growth_ppts[1:] = np.diff(gdp_level_pct)

        # Employment (Okun's law: 1% GDP = 0.5% employment)
        employment_pct = gdp_level_pct * 0.5
        employment_change = employment_pct / 100 * 160  # 160M employed

        # Unemployment effect (inverse of employment)
        unemployment_ppts = -employment_pct * 0.4

        # Interest rates (crowding out from higher deficits)
        deficit_change = outlays_chg - receipts_chg  # Positive = larger deficit
        cumulative_deficit = np.cumsum(deficit_change)
        debt_gdp_increase = cumulative_deficit / self.baseline_gdp

        # Long rate rises with debt
        long_rate_ppts = debt_gdp_increase * 0.02  # 2bp per 1% GDP debt increase
        short_rate_ppts = long_rate_ppts * 0.5     # Short rate moves less

        # Revenue feedback (more GDP = more tax revenue)
        revenue_feedback = gdp_change * self.marginal_tax_rate

        # Interest cost on additional debt
        avg_rate = 0.04  # 4% average interest rate
        interest_cost = cumulative_deficit * avg_rate

        return MacroResult(
            scenario_name=scenario.name,
            model_name=self.name,
            years=years,
            gdp_level_pct=gdp_level_pct,
            gdp_growth_ppts=gdp_growth_ppts,
            employment_change_millions=employment_change,
            unemployment_rate_ppts=unemployment_ppts,
            short_rate_ppts=short_rate_ppts,
            long_rate_ppts=long_rate_ppts,
            revenue_feedback_billions=revenue_feedback,
            interest_cost_billions=interest_cost,
        )

    def get_baseline(self) -> pd.DataFrame:
        """Get baseline projection."""
        years = np.arange(2025, 2035)
        return pd.DataFrame({
            "Year": years,
            "GDP ($T)": np.linspace(28.0, 35.0, 10),
            "Growth (%)": np.linspace(2.4, 1.8, 10),
            "Unemployment (%)": np.linspace(4.0, 4.5, 10),
            "Fed Funds (%)": np.linspace(4.5, 3.0, 10),
            "10Y Rate (%)": np.linspace(4.4, 4.0, 10),
        })


__all__ = ["SimpleMultiplierAdapter"]
