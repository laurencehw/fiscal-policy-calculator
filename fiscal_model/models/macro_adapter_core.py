"""
Core macro adapter types shared across macroeconomic model backends.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

import numpy as np
import pandas as pd


class FiscalClosureType(Enum):
    """
    Fiscal closure assumptions for long-run sustainability.

    These determine how debt is stabilized in the long run.
    """

    LUMP_SUM_TAXES = "lump_sum"           # Adjust lump-sum taxes
    INCOME_TAX_RATE = "income_tax"        # Adjust income tax rate
    SPENDING_CUTS = "spending_cuts"       # Cut spending proportionally
    DEBT_ACCUMULATION = "debt_accumulate"  # Let debt grow (no closure)
    SURPLUS_RATIO = "surplus_ratio"       # Target deficit/surplus ratio


class MonetaryPolicyRule(Enum):
    """Monetary policy reaction function."""

    TAYLOR_RULE = "taylor"       # Standard Taylor rule
    ZERO_LOWER_BOUND = "zlb"     # At effective lower bound
    INTEREST_RATE_PEG = "peg"    # Fixed interest rate path
    OPTIMAL_CONTROL = "optimal"  # Fed optimal policy


@dataclass
class MacroScenario:
    """
    Defines a macroeconomic scenario for fiscal policy analysis.

    Contains paths for receipts, outlays, and closure assumptions.
    """

    name: str
    description: str

    # Simulation period
    start_year: int = 2025
    horizon_years: int = 10

    # Fiscal paths (billions, by year relative to baseline)
    # Positive = higher than baseline
    receipts_change: np.ndarray | None = None  # Federal revenue change
    outlays_change: np.ndarray | None = None   # Federal spending change

    # Closure assumptions
    fiscal_closure: FiscalClosureType = FiscalClosureType.LUMP_SUM_TAXES
    closure_start_year: int = 2035  # When closure kicks in

    # Monetary policy
    monetary_rule: MonetaryPolicyRule = MonetaryPolicyRule.TAYLOR_RULE
    fed_accommodates: bool = False  # If True, Fed doesn't offset fiscal

    # Debt dynamics
    initial_debt_gdp: float = 1.0  # Starting debt-to-GDP ratio
    target_debt_gdp: float | None = None  # Long-run target

    def __post_init__(self):
        if self.receipts_change is None:
            self.receipts_change = np.zeros(self.horizon_years)
        if self.outlays_change is None:
            self.outlays_change = np.zeros(self.horizon_years)


@dataclass
class MacroResult:
    """
    Results from a macroeconomic model simulation.

    Contains output paths and key summary statistics.
    """

    scenario_name: str
    model_name: str

    # Years
    years: np.ndarray

    # GDP effects (percent change from baseline)
    gdp_level_pct: np.ndarray   # Cumulative GDP level change
    gdp_growth_ppts: np.ndarray  # Change in growth rate (ppts)

    # Employment effects
    employment_change_millions: np.ndarray
    unemployment_rate_ppts: np.ndarray

    # Interest rates (percentage points from baseline)
    short_rate_ppts: np.ndarray  # Federal funds rate
    long_rate_ppts: np.ndarray   # 10-year Treasury

    # Fiscal feedback
    revenue_feedback_billions: np.ndarray  # Additional revenue from GDP
    interest_cost_billions: np.ndarray     # Change in interest expense

    # Investment and capital
    investment_pct: np.ndarray | None = None
    capital_stock_pct: np.ndarray | None = None

    @property
    def cumulative_gdp_effect(self) -> float:
        """Total GDP effect over horizon (percent-years)."""
        return float(np.sum(self.gdp_level_pct))

    @property
    def cumulative_revenue_feedback(self) -> float:
        """Total revenue feedback over horizon (billions)."""
        return float(np.sum(self.revenue_feedback_billions))

    @property
    def net_budget_effect(self) -> float:
        """Net effect including revenue feedback and interest."""
        return self.cumulative_revenue_feedback - float(np.sum(self.interest_cost_billions))

    def to_dataframe(self) -> pd.DataFrame:
        """Convert results to DataFrame."""
        return pd.DataFrame({
            "Year": self.years,
            "GDP Level (%)": self.gdp_level_pct,
            "GDP Growth (ppts)": self.gdp_growth_ppts,
            "Employment (M)": self.employment_change_millions,
            "Unemployment (ppts)": self.unemployment_rate_ppts,
            "Short Rate (ppts)": self.short_rate_ppts,
            "Long Rate (ppts)": self.long_rate_ppts,
            "Revenue Feedback ($B)": self.revenue_feedback_billions,
            "Interest Cost ($B)": self.interest_cost_billions,
        })


class MacroModelAdapter(ABC):
    """
    Abstract interface for macroeconomic model adapters.

    Implementations connect to specific models (FRB/US, USMM, etc.)
    and translate fiscal scenarios into model inputs/outputs.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Model name (e.g., 'FRB/US', 'USMM')."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Brief description of the model methodology."""

    @abstractmethod
    def run(self, scenario: MacroScenario) -> MacroResult:
        """
        Run a macroeconomic simulation.

        Args:
            scenario: MacroScenario with fiscal paths and assumptions

        Returns:
            MacroResult with output paths
        """

    @abstractmethod
    def get_baseline(self) -> pd.DataFrame:
        """
        Get the baseline economic projection.

        Returns:
            DataFrame with baseline GDP, employment, rates, etc.
        """


__all__ = [
    "FiscalClosureType",
    "MacroModelAdapter",
    "MacroResult",
    "MacroScenario",
    "MonetaryPolicyRule",
]
