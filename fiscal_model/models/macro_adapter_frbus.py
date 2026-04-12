"""
FRB/US-backed macro adapters.
"""

import os

import numpy as np
import pandas as pd

from .macro_adapter_core import (
    FiscalClosureType,
    MacroModelAdapter,
    MacroResult,
    MacroScenario,
)


class FRBUSAdapter(MacroModelAdapter):
    """
    Adapter for the Federal Reserve's FRB/US model.

    NOTE: Requires pyfrbus package and FRB/US model files.
    Set FRBUS_MODEL_PATH and FRBUS_DATA_PATH environment variables
    to point to your local FRB/US installation.

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

    def __init__(
        self,
        model_path: str | None = None,
        data_path: str | None = None,
        use_mce: bool = False,
        fiscal_closure: FiscalClosureType = FiscalClosureType.SURPLUS_RATIO,
    ):
        """
        Initialize FRB/US adapter.

        Args:
            model_path: Path to model.xml file (defaults to FRBUS_MODEL_PATH env var)
            data_path: Path to LONGBASE.TXT data file (defaults to FRBUS_DATA_PATH env var)
            use_mce: Use model-consistent expectations (rational expectations)
            fiscal_closure: How to handle long-run fiscal sustainability
        """
        self.model_path = model_path or os.environ.get("FRBUS_MODEL_PATH")
        self.data_path = data_path or os.environ.get("FRBUS_DATA_PATH")
        if self.model_path is None or self.data_path is None:
            raise FileNotFoundError(
                "FRB/US model files not configured. Set FRBUS_MODEL_PATH and "
                "FRBUS_DATA_PATH environment variables."
            )
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
            from pyfrbus.frbus import Frbus
            from pyfrbus.load_data import load_data

            mce_option = "mcap+wp" if self.use_mce else None
            self._model = Frbus(self.model_path, mce=mce_option)
            self._data = load_data(self.data_path)

            # Store baseline GDP for scaling
            recent_gdp = self._data["xgdpn"].iloc[-1]
            self._baseline_gdp = recent_gdp / 1_000_000  # Convert to trillions

        except ImportError as err:
            raise ImportError(
                f"pyfrbus not installed or not found. Error: {err}\n"
                "Install from: https://www.federalreserve.gov/econres/us-models-package.htm"
            ) from err
        except FileNotFoundError as err:
            raise FileNotFoundError(
                f"FRB/US model files not found: {err}\n"
                f"Model path: {self.model_path}\n"
                f"Data path: {self.data_path}"
            ) from err

    def run(self, scenario: MacroScenario) -> MacroResult:
        """
        Run FRB/US simulation with fiscal scenario.

        Maps scenario to FRB/US shock variables and runs solve.
        Returns difference between policy simulation and baseline.
        """
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
            annual.append(np.mean(quarterly[i * 4:(i + 1) * 4]))
        return np.array(annual)

    def _quarter_ranges(self, start, n_quarters):
        """Generate quarter period ranges."""
        for i in range(n_quarters):
            q = start + i
            yield q, q

    def get_baseline(self) -> pd.DataFrame:
        """Get FRB/US baseline projection."""
        self._load_model()

        # Extract 10 years of baseline data
        start = pd.Period("2025Q1")
        end = start + 39  # 10 years

        # Get key variables
        vars_of_interest = [
            "xgdp",
            "xgdpn",
            "lur",
            "rff",
            "rg10",
            "picxfe",
            "gfexpn",
            "gfrecn",
            "gfdbtn",
            "gfintn",
        ]

        baseline = self._data.loc[start:end, vars_of_interest].copy()

        # Convert to annual averages
        years = range(2025, 2035)
        annual_data = []
        for year in years:
            year_start = pd.Period(f"{year}Q1")
            year_end = pd.Period(f"{year}Q4")
            year_data = baseline.loc[year_start:year_end].mean()
            annual_data.append(year_data)

        result = pd.DataFrame(annual_data).copy()
        result["Year"] = list(years)

        # Rename and convert units
        result = result.rename(columns={
            "xgdp": "Real GDP",
            "xgdpn": "Nominal GDP",
            "lur": "Unemployment (%)",
            "rff": "Fed Funds (%)",
            "rg10": "10Y Rate (%)",
            "picxfe": "Core PCE (%)",
        })

        # Convert GDP to trillions
        result.loc[:, "GDP ($T)"] = result["Nominal GDP"] / 1_000_000
        result.loc[:, "Real GDP ($T)"] = result["Real GDP"] / 1_000

        return result[
            [
                "Year",
                "GDP ($T)",
                "Real GDP ($T)",
                "Unemployment (%)",
                "Fed Funds (%)",
                "10Y Rate (%)",
                "Core PCE (%)",
            ]
        ]


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
            outlays_chg * self.spending_multiplier
            + receipts_chg * self.tax_multiplier
        )

        # GDP effect with decay and crowding out
        gdp_change = np.zeros(n_years)
        for t in range(n_years):
            # Cumulative effect with decay
            for s in range(t + 1):
                decay = self.multiplier_decay ** (t - s)
                gdp_change[t] += fiscal_impulse[s] * decay

            # Crowding out from higher interest rates
            cumulative_deficit = np.sum(outlays_chg[:t + 1] - receipts_chg[:t + 1])
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


__all__ = ["FRBUSAdapter", "FRBUSAdapterLite"]
