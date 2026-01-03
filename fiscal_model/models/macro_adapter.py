"""
Macro Model Adapter Interface

Abstract interface for connecting fiscal policy scoring to macroeconomic models
like FRB/US (Federal Reserve) and USMM (S&P Global).

This enables Yale Budget Lab-style dynamic scoring by running fiscal scenarios
through large-scale macro models and extracting GDP, employment, and interest
rate effects.

Architecture:
    FiscalPolicy -> MacroScenario -> MacroModelAdapter -> MacroResult
                                           |
                                    FRB/US | USMM | Simple

References:
- Yale Budget Lab: https://budgetlab.yale.edu/research/dynamic-scoring-using-frbus-macroeconomic-model
- FRB/US Documentation: https://www.federalreserve.gov/econres/us-models-about.htm
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
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
    SPENDING_CUTS = "spending_cuts"        # Cut spending proportionally
    DEBT_ACCUMULATION = "debt_accumulate"  # Let debt grow (no closure)
    SURPLUS_RATIO = "surplus_ratio"        # Target deficit/surplus ratio


class MonetaryPolicyRule(Enum):
    """Monetary policy reaction function."""
    TAYLOR_RULE = "taylor"            # Standard Taylor rule
    ZERO_LOWER_BOUND = "zlb"          # At effective lower bound
    INTEREST_RATE_PEG = "peg"         # Fixed interest rate path
    OPTIMAL_CONTROL = "optimal"       # Fed optimal policy


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
    receipts_change: Optional[np.ndarray] = None   # Federal revenue change
    outlays_change: Optional[np.ndarray] = None    # Federal spending change

    # Closure assumptions
    fiscal_closure: FiscalClosureType = FiscalClosureType.LUMP_SUM_TAXES
    closure_start_year: int = 2035  # When closure kicks in

    # Monetary policy
    monetary_rule: MonetaryPolicyRule = MonetaryPolicyRule.TAYLOR_RULE
    fed_accommodates: bool = False  # If True, Fed doesn't offset fiscal

    # Debt dynamics
    initial_debt_gdp: float = 1.0   # Starting debt-to-GDP ratio
    target_debt_gdp: Optional[float] = None  # Long-run target

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
    gdp_level_pct: np.ndarray         # Cumulative GDP level change
    gdp_growth_ppts: np.ndarray       # Change in growth rate (ppts)

    # Employment effects
    employment_change_millions: np.ndarray
    unemployment_rate_ppts: np.ndarray

    # Interest rates (percentage points from baseline)
    short_rate_ppts: np.ndarray       # Federal funds rate
    long_rate_ppts: np.ndarray        # 10-year Treasury

    # Fiscal feedback
    revenue_feedback_billions: np.ndarray  # Additional revenue from GDP
    interest_cost_billions: np.ndarray     # Change in interest expense

    # Investment and capital
    investment_pct: Optional[np.ndarray] = None
    capital_stock_pct: Optional[np.ndarray] = None

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
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Brief description of the model methodology."""
        pass

    @abstractmethod
    def run(self, scenario: MacroScenario) -> MacroResult:
        """
        Run a macroeconomic simulation.

        Args:
            scenario: MacroScenario with fiscal paths and assumptions

        Returns:
            MacroResult with output paths
        """
        pass

    @abstractmethod
    def get_baseline(self) -> pd.DataFrame:
        """
        Get the baseline economic projection.

        Returns:
            DataFrame with baseline GDP, employment, rates, etc.
        """
        pass


# =============================================================================
# SIMPLE MULTIPLIER MODEL (FOR TESTING)
# =============================================================================

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


# =============================================================================
# FRB/US ADAPTER (PLACEHOLDER - REQUIRES pyfrbus)
# =============================================================================

class FRBUSAdapter(MacroModelAdapter):
    """
    Adapter for the Federal Reserve's FRB/US model.

    Requires pyfrbus package and model data files from:
    https://www.federalreserve.gov/econres/us-models-package.htm

    This adapter translates fiscal scenarios into FRB/US inputs
    and extracts relevant outputs for dynamic scoring.

    Key FRB/US fiscal variables:
    - gfexpn: Federal expenditures (nominal, millions)
    - gfrecn: Federal receipts (nominal, millions)
    - gtn: Federal receipts - individual income tax portion
    - gfintn: Federal interest payments
    - gfdbtn: Federal debt (nominal)
    - gfsrpn: Federal surplus/deficit
    - dfpdbt: Debt targeting flag (1=target debt ratio)
    - dfpsrp: Surplus ratio targeting flag (1=target surplus ratio)

    Output variables:
    - xgdp: Real GDP
    - xgdpn: Nominal GDP
    - lur: Unemployment rate
    - rff: Federal funds rate
    - rg10: 10-year Treasury rate
    """

    @property
    def name(self) -> str:
        return "FRB/US"

    @property
    def description(self) -> str:
        return "Federal Reserve Board's US macroeconomic model"

    # Default paths relative to Economy_Forecasts project
    DEFAULT_MODEL_PATH = r"C:\Users\lwils\Projects\apps\Economy_Forecasts\models\frbus\models\model.xml"
    DEFAULT_DATA_PATH = r"C:\Users\lwils\Projects\apps\Economy_Forecasts\models\frbus\data\LONGBASE.TXT"

    def __init__(
        self,
        model_path: Optional[str] = None,
        data_path: Optional[str] = None,
        use_mce: bool = False,
        fiscal_closure: FiscalClosureType = FiscalClosureType.SURPLUS_RATIO,
    ):
        """
        Initialize FRB/US adapter.

        Args:
            model_path: Path to model.xml file (defaults to Economy_Forecasts location)
            data_path: Path to LONGBASE.TXT data file
            use_mce: Use model-consistent expectations (rational expectations)
            fiscal_closure: How to handle long-run fiscal sustainability
        """
        self.model_path = model_path or self.DEFAULT_MODEL_PATH
        self.data_path = data_path or self.DEFAULT_DATA_PATH
        self.use_mce = use_mce
        self.fiscal_closure = fiscal_closure
        self._model = None
        self._data = None
        self._baseline_gdp = None

    def _load_model(self):
        """Lazy load FRB/US model."""
        if self._model is not None:
            return

        try:
            # Add pyfrbus to path
            import sys
            frbus_path = r"C:\Users\lwils\Projects\apps\Economy_Forecasts\models\frbus"
            if frbus_path not in sys.path:
                sys.path.insert(0, frbus_path)

            from pyfrbus.frbus import Frbus
            from pyfrbus.load_data import load_data

            mce_option = "mcap+wp" if self.use_mce else None
            self._model = Frbus(self.model_path, mce=mce_option)
            self._data = load_data(self.data_path)

            # Store baseline GDP for scaling
            recent_gdp = self._data['xgdpn'].iloc[-1]
            self._baseline_gdp = recent_gdp / 1_000_000  # Convert to trillions

        except ImportError as e:
            raise ImportError(
                f"pyfrbus not installed or not found. Error: {e}\n"
                "Install from: https://www.federalreserve.gov/econres/us-models-package.htm"
            )
        except FileNotFoundError as e:
            raise FileNotFoundError(
                f"FRB/US model files not found: {e}\n"
                f"Model path: {self.model_path}\n"
                f"Data path: {self.data_path}"
            )

    def run(self, scenario: MacroScenario) -> MacroResult:
        """
        Run FRB/US simulation with fiscal scenario.

        Maps scenario to FRB/US shock variables and runs solve.
        Returns difference between policy simulation and baseline.
        """
        import pandas as pd

        self._load_model()

        # Determine simulation dates (quarterly)
        n_years = scenario.horizon_years
        n_quarters = n_years * 4

        # Use a future simulation period to avoid historical data issues
        start = pd.Period(f"{scenario.start_year}Q1")
        end = start + n_quarters - 1

        # Make a copy of baseline data
        data = self._data.copy()

        # Set fiscal closure flags
        if self.fiscal_closure == FiscalClosureType.SURPLUS_RATIO:
            data.loc[start:end, "dfpdbt"] = 0
            data.loc[start:end, "dfpsrp"] = 1
        elif self.fiscal_closure == FiscalClosureType.DEBT_ACCUMULATION:
            data.loc[start:end, "dfpdbt"] = 0
            data.loc[start:end, "dfpsrp"] = 0
        else:
            # Default to surplus ratio targeting
            data.loc[start:end, "dfpdbt"] = 0
            data.loc[start:end, "dfpsrp"] = 1

        # Initialize tracking residuals for baseline
        baseline_data = self._model.init_trac(start, end, data)

        # Solve baseline
        baseline = self._model.solve(start, end, baseline_data)

        # Create reform scenario with fiscal shocks
        reform_data = baseline_data.copy()

        # Convert annual scenario to quarterly shocks
        # Scenario values are in billions, FRB/US uses millions
        receipts_quarterly = self._annual_to_quarterly(scenario.receipts_change) * 1000
        outlays_quarterly = self._annual_to_quarterly(scenario.outlays_change) * 1000

        # Apply shocks via add-factors (_aerr variables)
        # Receipt changes affect gfrecn (total federal receipts)
        # Outlay changes affect gfexpn (federal expenditures)
        for i, (q_start, q_end) in enumerate(self._quarter_ranges(start, n_quarters)):
            if i < len(receipts_quarterly):
                # Shock to federal receipts
                reform_data.loc[q_start:q_end, "gfrecn_aerr"] = receipts_quarterly[i]
                # Also shock gtn (income tax portion) proportionally
                # gtn is ~70% of gfrecn based on the data
                reform_data.loc[q_start:q_end, "gtn_aerr"] = receipts_quarterly[i] * 0.7

            if i < len(outlays_quarterly):
                # Shock to federal expenditures
                reform_data.loc[q_start:q_end, "gfexpn_aerr"] = outlays_quarterly[i]

        # Solve reform scenario
        reform = self._model.solve(start, end, reform_data)

        # Extract results (differences from baseline)
        years = np.arange(scenario.start_year, scenario.start_year + n_years)

        # GDP effects (percent change from baseline)
        baseline_gdp = self._quarterly_to_annual(baseline.loc[start:end, "xgdp"].values)
        reform_gdp = self._quarterly_to_annual(reform.loc[start:end, "xgdp"].values)
        gdp_level_pct = (reform_gdp - baseline_gdp) / baseline_gdp * 100

        # GDP growth effect (change in growth rate)
        gdp_growth_ppts = np.zeros(n_years)
        gdp_growth_ppts[0] = gdp_level_pct[0]
        gdp_growth_ppts[1:] = np.diff(gdp_level_pct)

        # Employment (use Okun's law approximation: 1% GDP ≈ 0.5% employment)
        # Could enhance to use FRB/US employment variables directly
        employment_pct = gdp_level_pct * 0.5
        employment_change = employment_pct / 100 * 160  # ~160M employed

        # Unemployment rate change
        baseline_lur = self._quarterly_to_annual(baseline.loc[start:end, "lur"].values)
        reform_lur = self._quarterly_to_annual(reform.loc[start:end, "lur"].values)
        unemployment_ppts = reform_lur - baseline_lur

        # Interest rates
        baseline_rff = self._quarterly_to_annual(baseline.loc[start:end, "rff"].values)
        reform_rff = self._quarterly_to_annual(reform.loc[start:end, "rff"].values)
        short_rate_ppts = reform_rff - baseline_rff

        baseline_rg10 = self._quarterly_to_annual(baseline.loc[start:end, "rg10"].values)
        reform_rg10 = self._quarterly_to_annual(reform.loc[start:end, "rg10"].values)
        long_rate_ppts = reform_rg10 - baseline_rg10

        # Revenue feedback (GDP increase generates additional tax revenue)
        # Use marginal tax rate of ~25%
        marginal_rate = 0.25
        gdp_change_billions = (reform_gdp - baseline_gdp) / 1000  # xgdp is in billions
        revenue_feedback = gdp_change_billions * marginal_rate

        # Interest cost on additional debt
        baseline_debt = self._quarterly_to_annual(baseline.loc[start:end, "gfdbtn"].values)
        reform_debt = self._quarterly_to_annual(reform.loc[start:end, "gfdbtn"].values)
        debt_increase = (reform_debt - baseline_debt) / 1000  # Convert to billions
        avg_rate = 0.04  # ~4% average interest rate
        interest_cost = debt_increase * avg_rate

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

    def _annual_to_quarterly(self, annual: np.ndarray) -> np.ndarray:
        """Convert annual values to quarterly (divide by 4)."""
        quarterly = []
        for val in annual:
            quarterly.extend([val / 4] * 4)
        return np.array(quarterly)

    def _quarterly_to_annual(self, quarterly: np.ndarray) -> np.ndarray:
        """Convert quarterly values to annual (average of 4 quarters)."""
        n_years = len(quarterly) // 4
        annual = []
        for i in range(n_years):
            annual.append(np.mean(quarterly[i*4:(i+1)*4]))
        return np.array(annual)

    def _quarter_ranges(self, start, n_quarters):
        """Generate quarter period ranges."""
        import pandas as pd
        for i in range(n_quarters):
            q = start + i
            yield q, q

    def get_baseline(self) -> pd.DataFrame:
        """Get FRB/US baseline projection."""
        self._load_model()

        # Extract 10 years of baseline data
        import pandas as pd
        start = pd.Period("2025Q1")
        end = start + 39  # 10 years

        # Get key variables
        vars_of_interest = ['xgdp', 'xgdpn', 'lur', 'rff', 'rg10', 'picxfe',
                           'gfexpn', 'gfrecn', 'gfdbtn', 'gfintn']

        baseline = self._data.loc[start:end, vars_of_interest].copy()

        # Convert to annual averages
        years = range(2025, 2035)
        annual_data = []
        for year in years:
            year_start = pd.Period(f"{year}Q1")
            year_end = pd.Period(f"{year}Q4")
            year_data = baseline.loc[year_start:year_end].mean()
            annual_data.append(year_data)

        result = pd.DataFrame(annual_data)
        result['Year'] = list(years)

        # Rename and convert units
        result = result.rename(columns={
            'xgdp': 'Real GDP',
            'xgdpn': 'Nominal GDP',
            'lur': 'Unemployment (%)',
            'rff': 'Fed Funds (%)',
            'rg10': '10Y Rate (%)',
            'picxfe': 'Core PCE (%)',
        })

        # Convert GDP to trillions
        result['GDP ($T)'] = result['Nominal GDP'] / 1_000_000
        result['Real GDP ($T)'] = result['Real GDP'] / 1_000

        return result[['Year', 'GDP ($T)', 'Real GDP ($T)', 'Unemployment (%)',
                       'Fed Funds (%)', '10Y Rate (%)', 'Core PCE (%)']]


class FRBUSAdapterLite(MacroModelAdapter):
    """
    Lightweight FRB/US-calibrated adapter that doesn't require pyfrbus.

    Uses FRB/US-derived multipliers and response functions to approximate
    the full model's behavior. Useful for quick estimates when full model
    isn't available.

    Calibration based on Fed analysis of FRB/US fiscal multipliers:
    - Spending multiplier: ~1.4 in year 1, decaying
    - Tax multiplier: ~-0.7 in year 1
    - Crowding out effects from interest rate response
    """

    @property
    def name(self) -> str:
        return "FRB/US-Lite"

    @property
    def description(self) -> str:
        return "FRB/US-calibrated reduced-form model (no pyfrbus required)"

    def __init__(
        self,
        spending_multiplier: float = 1.4,
        tax_multiplier: float = -0.7,
        multiplier_decay: float = 0.75,
        crowding_out: float = 0.15,
        marginal_tax_rate: float = 0.25,
    ):
        """
        Initialize with FRB/US-calibrated parameters.

        Args:
            spending_multiplier: First-year spending multiplier (FRB/US ~1.4)
            tax_multiplier: First-year tax multiplier (FRB/US ~-0.7)
            multiplier_decay: Annual decay of multiplier effects
            crowding_out: Interest rate crowding out coefficient
            marginal_tax_rate: For revenue feedback calculation
        """
        self.spending_multiplier = spending_multiplier
        self.tax_multiplier = tax_multiplier
        self.multiplier_decay = multiplier_decay
        self.crowding_out = crowding_out
        self.marginal_tax_rate = marginal_tax_rate
        self.baseline_gdp = 28_000.0  # $28T baseline GDP

    def run(self, scenario: MacroScenario) -> MacroResult:
        """Run FRB/US-lite simulation."""
        n_years = scenario.horizon_years
        years = np.arange(scenario.start_year, scenario.start_year + n_years)

        # Calculate fiscal impulse with FRB/US-calibrated multipliers
        receipts_chg = scenario.receipts_change
        outlays_chg = scenario.outlays_change

        # Net fiscal impulse (billions)
        fiscal_impulse = (
            outlays_chg * self.spending_multiplier +
            receipts_chg * self.tax_multiplier
        )

        # GDP effect with decay and crowding out
        gdp_change = np.zeros(n_years)
        for t in range(n_years):
            # Cumulative effect with decay
            for s in range(t + 1):
                decay = self.multiplier_decay ** (t - s)
                gdp_change[t] += fiscal_impulse[s] * decay

            # Crowding out from higher interest rates
            cumulative_deficit = np.sum(outlays_chg[:t+1] - receipts_chg[:t+1])
            crowding_effect = cumulative_deficit * self.crowding_out / 1000
            gdp_change[t] *= (1 - crowding_effect)

        # Convert to percent
        gdp_level_pct = gdp_change / self.baseline_gdp * 100

        # Growth rate effect
        gdp_growth_ppts = np.zeros(n_years)
        gdp_growth_ppts[0] = gdp_level_pct[0]
        gdp_growth_ppts[1:] = np.diff(gdp_level_pct)

        # Employment (FRB/US shows ~0.4% employment per 1% GDP)
        employment_pct = gdp_level_pct * 0.4
        employment_change = employment_pct / 100 * 160

        # Unemployment (Okun coefficient ~-0.5)
        unemployment_ppts = -gdp_level_pct * 0.5

        # Interest rates (FRB/US shows ~3bp per 1% GDP deficit)
        deficit_change = outlays_chg - receipts_chg
        cumulative_deficit = np.cumsum(deficit_change)
        debt_gdp = cumulative_deficit / self.baseline_gdp

        long_rate_ppts = debt_gdp * 0.03  # 3bp per 1% GDP debt
        short_rate_ppts = long_rate_ppts * 0.7  # Fed responds less than long rates

        # Revenue feedback
        revenue_feedback = gdp_change * self.marginal_tax_rate

        # Interest cost
        interest_cost = cumulative_deficit * 0.04

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
        """Get baseline projection (CBO-based)."""
        years = np.arange(2025, 2035)
        return pd.DataFrame({
            "Year": years,
            "GDP ($T)": np.linspace(28.0, 35.0, 10),
            "Real GDP ($T)": np.linspace(22.0, 26.0, 10),
            "Unemployment (%)": np.linspace(4.0, 4.5, 10),
            "Fed Funds (%)": np.linspace(4.5, 3.0, 10),
            "10Y Rate (%)": np.linspace(4.4, 4.0, 10),
            "Core PCE (%)": np.linspace(2.5, 2.0, 10),
        })


# =============================================================================
# POLICY TO SCENARIO CONVERTER
# =============================================================================

def policy_to_scenario(
    policy,
    scoring_result,
    scenario_name: Optional[str] = None,
) -> MacroScenario:
    """
    Convert a scored fiscal policy to a MacroScenario.

    Args:
        policy: Policy object (TaxPolicy, SpendingPolicy, etc.)
        scoring_result: ScoringResult from FiscalPolicyScorer
        scenario_name: Optional name for the scenario

    Returns:
        MacroScenario ready for macro model simulation
    """
    if scenario_name is None:
        scenario_name = policy.name

    # Extract fiscal paths from scoring result
    # Revenue changes (negative = tax cut = less revenue)
    if hasattr(scoring_result, 'final_deficit_effect'):
        # Deficit effect includes behavioral adjustments
        deficit_effect = scoring_result.final_deficit_effect
    else:
        deficit_effect = np.zeros(10)

    # Split into receipts and outlays based on policy type
    policy_type = getattr(policy, 'policy_type', None)

    if policy_type and "SPENDING" in str(policy_type.name):
        # Spending policy - affects outlays
        outlays_change = deficit_effect  # Higher deficit = more spending
        receipts_change = np.zeros_like(deficit_effect)
    else:
        # Tax policy - affects receipts
        receipts_change = -deficit_effect  # Deficit increase = revenue loss
        outlays_change = np.zeros_like(deficit_effect)

    return MacroScenario(
        name=scenario_name,
        description=f"Dynamic scoring scenario for {policy.name}",
        start_year=getattr(policy, 'start_year', 2025),
        horizon_years=len(deficit_effect),
        receipts_change=receipts_change,
        outlays_change=outlays_change,
    )


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Enums
    "FiscalClosureType",
    "MonetaryPolicyRule",
    # Data classes
    "MacroScenario",
    "MacroResult",
    # Adapters
    "MacroModelAdapter",
    "SimpleMultiplierAdapter",
    "FRBUSAdapter",
    "FRBUSAdapterLite",
    # Helpers
    "policy_to_scenario",
]
