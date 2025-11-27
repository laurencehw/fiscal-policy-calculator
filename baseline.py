"""
Baseline Budget Projections

Provides baseline projections for federal revenues, spending, and deficits
following CBO methodology and current law assumptions.
"""

from dataclasses import dataclass, field
import numpy as np
from typing import Optional


@dataclass
class EconomicAssumptions:
    """
    Economic assumptions underlying the baseline projection.
    Based on typical CBO assumptions.
    """
    # GDP growth (real)
    real_gdp_growth: np.ndarray = field(default_factory=lambda: np.array([
        0.024, 0.021, 0.019, 0.018, 0.018, 0.018, 0.018, 0.018, 0.018, 0.018
    ]))
    
    # Inflation (GDP deflator)
    inflation: np.ndarray = field(default_factory=lambda: np.array([
        0.023, 0.022, 0.021, 0.020, 0.020, 0.020, 0.020, 0.020, 0.020, 0.020
    ]))
    
    # Unemployment rate
    unemployment: np.ndarray = field(default_factory=lambda: np.array([
        0.042, 0.044, 0.045, 0.045, 0.045, 0.045, 0.045, 0.045, 0.045, 0.045
    ]))
    
    # Interest rates (10-year Treasury)
    interest_rate_10yr: np.ndarray = field(default_factory=lambda: np.array([
        0.044, 0.043, 0.042, 0.041, 0.040, 0.040, 0.040, 0.040, 0.040, 0.040
    ]))
    
    # Labor force participation rate
    labor_force_participation: np.ndarray = field(default_factory=lambda: np.array([
        0.622, 0.620, 0.618, 0.616, 0.614, 0.612, 0.610, 0.608, 0.606, 0.604
    ]))


@dataclass
class BaselineProjection:
    """
    10-year baseline budget projection.
    
    All values in billions of dollars unless otherwise noted.
    """
    start_year: int = 2025
    years: np.ndarray = field(default_factory=lambda: np.arange(2025, 2035))
    
    # Economic variables
    nominal_gdp: np.ndarray = field(default_factory=lambda: np.zeros(10))
    real_gdp: np.ndarray = field(default_factory=lambda: np.zeros(10))
    
    # Revenue categories
    individual_income_tax: np.ndarray = field(default_factory=lambda: np.zeros(10))
    corporate_income_tax: np.ndarray = field(default_factory=lambda: np.zeros(10))
    payroll_taxes: np.ndarray = field(default_factory=lambda: np.zeros(10))
    other_revenues: np.ndarray = field(default_factory=lambda: np.zeros(10))
    
    # Spending categories
    social_security: np.ndarray = field(default_factory=lambda: np.zeros(10))
    medicare: np.ndarray = field(default_factory=lambda: np.zeros(10))
    medicaid: np.ndarray = field(default_factory=lambda: np.zeros(10))
    other_mandatory: np.ndarray = field(default_factory=lambda: np.zeros(10))
    defense_discretionary: np.ndarray = field(default_factory=lambda: np.zeros(10))
    nondefense_discretionary: np.ndarray = field(default_factory=lambda: np.zeros(10))
    net_interest: np.ndarray = field(default_factory=lambda: np.zeros(10))
    
    # Debt
    debt_held_by_public: np.ndarray = field(default_factory=lambda: np.zeros(10))
    
    @property
    def total_revenues(self) -> np.ndarray:
        """Total federal revenues."""
        return (self.individual_income_tax + self.corporate_income_tax + 
                self.payroll_taxes + self.other_revenues)
    
    @property
    def total_outlays(self) -> np.ndarray:
        """Total federal outlays."""
        return (self.social_security + self.medicare + self.medicaid +
                self.other_mandatory + self.defense_discretionary +
                self.nondefense_discretionary + self.net_interest)
    
    @property
    def deficit(self) -> np.ndarray:
        """Budget deficit (positive = deficit, negative = surplus)."""
        return self.total_outlays - self.total_revenues
    
    @property
    def primary_deficit(self) -> np.ndarray:
        """Primary deficit (excluding interest payments)."""
        return self.deficit - self.net_interest
    
    @property
    def deficit_to_gdp(self) -> np.ndarray:
        """Deficit as percentage of GDP."""
        return self.deficit / self.nominal_gdp * 100
    
    @property
    def debt_to_gdp(self) -> np.ndarray:
        """Debt as percentage of GDP."""
        return self.debt_held_by_public / self.nominal_gdp * 100
    
    def get_year_index(self, year: int) -> int:
        """Get array index for a given year."""
        return year - self.start_year
    
    def get_value(self, category: str, year: int) -> float:
        """Get a specific value for a category and year."""
        idx = self.get_year_index(year)
        return getattr(self, category)[idx]
    
    def get_cumulative_deficit(self, start_year: Optional[int] = None, 
                               end_year: Optional[int] = None) -> float:
        """Get cumulative deficit over a period."""
        start = start_year or self.start_year
        end = end_year or (self.start_year + len(self.years) - 1)
        
        start_idx = self.get_year_index(start)
        end_idx = self.get_year_index(end) + 1
        
        return np.sum(self.deficit[start_idx:end_idx])


class CBOBaseline:
    """
    Generator for CBO-style baseline projections.
    
    Based on CBO's February 2024 baseline with adjustments.
    """
    
    def __init__(self, start_year: int = 2025, use_real_data: bool = True):
        import logging
        logger = logging.getLogger(__name__)

        self.start_year = start_year
        self.years = np.arange(start_year, start_year + 10)
        self.assumptions = EconomicAssumptions()

        # Try to load real data, fall back to hardcoded if unavailable
        if use_real_data:
            try:
                self._load_from_data_sources()
                logger.info("Successfully loaded baseline data from IRS SOI and FRED")
            except Exception as e:
                logger.warning(f"Could not load real data: {e}")
                logger.warning("Falling back to hardcoded baseline values")
                self._use_hardcoded_fallback()
        else:
            self._use_hardcoded_fallback()

    def _load_from_data_sources(self):
        """Load baseline values from IRS SOI and FRED data."""
        from fiscal_model.data import IRSSOIData, FREDData

        # Initialize data loaders
        irs_data = IRSSOIData()
        fred_data = FREDData(api_key="a2efb8590f142e4ff8a528e194b531ef")  # User's API key

        # Get most recent available IRS data year
        available_years = irs_data.get_data_years_available()
        if not available_years:
            raise FileNotFoundError("No IRS SOI data files found. See fiscal_model/data_files/irs_soi/README.md")

        data_year = max(available_years)
        print(f"Loading baseline from {data_year} IRS SOI data")

        # Load individual income tax revenue from IRS data
        self.base_individual_income_tax = irs_data.get_total_revenue(data_year)

        # Load GDP from FRED
        if fred_data.is_available():
            gdp_series = fred_data.get_gdp(nominal=True)
            # Get most recent quarterly value (in billions)
            self.base_gdp = float(gdp_series.iloc[-1])
            print(f"Loaded GDP from FRED: ${self.base_gdp:,.0f}B")
        else:
            # Use ratio from IRS data
            print("FRED not available, estimating GDP from IRS data")
            self.base_gdp = self.base_individual_income_tax / 0.088  # ~8.8% ratio

        # Corporate tax: Historical ratio to individual income tax (~18%)
        self.base_corporate_tax = self.base_individual_income_tax * 0.18

        # Payroll tax: ~6% of GDP (historical average)
        self.base_payroll_tax = self.base_gdp * 0.06

        # Other revenue: Estate, excise, customs (~1.4% of GDP)
        self.base_other_revenue = self.base_gdp * 0.014

        # Spending categories: Use GDP ratios
        self.base_social_security = self.base_gdp * 0.053  # ~5.3% of GDP
        self.base_medicare = self.base_gdp * 0.032  # ~3.2% of GDP
        self.base_medicaid = self.base_gdp * 0.021  # ~2.1% of GDP
        self.base_other_mandatory = self.base_gdp * 0.032  # ~3.2% of GDP
        self.base_defense = self.base_gdp * 0.032  # ~3.2% of GDP
        self.base_nondefense = self.base_gdp * 0.026  # ~2.6% of GDP

        # Debt: ~98% of GDP (current debt-to-GDP ratio)
        self.base_debt = self.base_gdp * 0.98

    def _use_hardcoded_fallback(self):
        """Use hardcoded baseline values (fallback when data unavailable)."""
        # Base year (2024) values in billions
        self.base_gdp = 28500  # Nominal GDP
        self.base_individual_income_tax = 2500
        self.base_corporate_tax = 450
        self.base_payroll_tax = 1700
        self.base_other_revenue = 400
        self.base_social_security = 1500
        self.base_medicare = 900
        self.base_medicaid = 600
        self.base_other_mandatory = 900
        self.base_defense = 900
        self.base_nondefense = 750
        self.base_debt = 28000
        
    def generate(self) -> BaselineProjection:
        """Generate a 10-year baseline projection."""
        proj = BaselineProjection(
            start_year=self.start_year,
            years=self.years.copy()
        )
        
        # Generate GDP path
        proj.nominal_gdp = self._project_gdp()
        proj.real_gdp = self._project_real_gdp()
        
        # Generate revenues
        proj.individual_income_tax = self._project_individual_tax()
        proj.corporate_income_tax = self._project_corporate_tax()
        proj.payroll_taxes = self._project_payroll_tax()
        proj.other_revenues = self._project_other_revenue()
        
        # Generate spending
        proj.social_security = self._project_social_security()
        proj.medicare = self._project_medicare()
        proj.medicaid = self._project_medicaid()
        proj.other_mandatory = self._project_other_mandatory()
        proj.defense_discretionary = self._project_defense()
        proj.nondefense_discretionary = self._project_nondefense()
        
        # Calculate interest and debt
        proj.debt_held_by_public = self._project_debt(proj)
        proj.net_interest = self._project_interest(proj)
        
        return proj
    
    def _project_gdp(self) -> np.ndarray:
        """Project nominal GDP."""
        gdp = np.zeros(10)
        gdp[0] = self.base_gdp * (1 + self.assumptions.real_gdp_growth[0] + 
                                   self.assumptions.inflation[0])
        for i in range(1, 10):
            growth = self.assumptions.real_gdp_growth[i] + self.assumptions.inflation[i]
            gdp[i] = gdp[i-1] * (1 + growth)
        return gdp
    
    def _project_real_gdp(self) -> np.ndarray:
        """Project real GDP (2024 dollars)."""
        real_gdp = np.zeros(10)
        real_gdp[0] = self.base_gdp * (1 + self.assumptions.real_gdp_growth[0])
        for i in range(1, 10):
            real_gdp[i] = real_gdp[i-1] * (1 + self.assumptions.real_gdp_growth[i])
        return real_gdp
    
    def _project_individual_tax(self) -> np.ndarray:
        """Project individual income tax revenues."""
        # Income tax grows faster than GDP due to bracket creep
        revenue = np.zeros(10)
        growth_premium = 0.003  # Extra growth from real bracket creep
        
        revenue[0] = self.base_individual_income_tax * (1 + 
                     self.assumptions.real_gdp_growth[0] + 
                     self.assumptions.inflation[0] + growth_premium)
        
        for i in range(1, 10):
            base_growth = (self.assumptions.real_gdp_growth[i] + 
                          self.assumptions.inflation[i] + growth_premium)
            revenue[i] = revenue[i-1] * (1 + base_growth)
        
        return revenue
    
    def _project_corporate_tax(self) -> np.ndarray:
        """Project corporate income tax revenues."""
        # More volatile, tied to profits
        revenue = np.zeros(10)
        revenue[0] = self.base_corporate_tax * 1.04
        
        for i in range(1, 10):
            # Corporate profits grow slightly faster than GDP
            growth = self.assumptions.real_gdp_growth[i] + self.assumptions.inflation[i] + 0.01
            revenue[i] = revenue[i-1] * (1 + growth)
        
        return revenue
    
    def _project_payroll_tax(self) -> np.ndarray:
        """Project payroll tax revenues."""
        # Tied to wage growth
        revenue = np.zeros(10)
        revenue[0] = self.base_payroll_tax * 1.04
        
        for i in range(1, 10):
            # Wage growth typically matches GDP growth
            growth = self.assumptions.real_gdp_growth[i] + self.assumptions.inflation[i]
            revenue[i] = revenue[i-1] * (1 + growth)
        
        return revenue
    
    def _project_other_revenue(self) -> np.ndarray:
        """Project other revenues (excise, customs, misc)."""
        revenue = np.zeros(10)
        revenue[0] = self.base_other_revenue * 1.03
        
        for i in range(1, 10):
            revenue[i] = revenue[i-1] * 1.02  # Slower growth
        
        return revenue
    
    def _project_social_security(self) -> np.ndarray:
        """Project Social Security spending."""
        # Fast growing due to demographics
        spending = np.zeros(10)
        spending[0] = self.base_social_security * 1.06
        
        for i in range(1, 10):
            # ~5% annual growth
            spending[i] = spending[i-1] * 1.05
        
        return spending
    
    def _project_medicare(self) -> np.ndarray:
        """Project Medicare spending."""
        # Fast growing due to demographics and healthcare costs
        spending = np.zeros(10)
        spending[0] = self.base_medicare * 1.07
        
        for i in range(1, 10):
            spending[i] = spending[i-1] * 1.06
        
        return spending
    
    def _project_medicaid(self) -> np.ndarray:
        """Project Medicaid spending."""
        spending = np.zeros(10)
        spending[0] = self.base_medicaid * 1.05
        
        for i in range(1, 10):
            spending[i] = spending[i-1] * 1.05
        
        return spending
    
    def _project_other_mandatory(self) -> np.ndarray:
        """Project other mandatory spending."""
        spending = np.zeros(10)
        spending[0] = self.base_other_mandatory * 1.03
        
        for i in range(1, 10):
            spending[i] = spending[i-1] * 1.03
        
        return spending
    
    def _project_defense(self) -> np.ndarray:
        """Project defense discretionary spending."""
        # Assume caps or slow growth
        spending = np.zeros(10)
        spending[0] = self.base_defense * 1.02
        
        for i in range(1, 10):
            spending[i] = spending[i-1] * 1.02
        
        return spending
    
    def _project_nondefense(self) -> np.ndarray:
        """Project nondefense discretionary spending."""
        spending = np.zeros(10)
        spending[0] = self.base_nondefense * 1.01
        
        for i in range(1, 10):
            spending[i] = spending[i-1] * 1.01
        
        return spending
    
    def _project_debt(self, proj: BaselineProjection) -> np.ndarray:
        """Project debt held by public (iterative with interest)."""
        debt = np.zeros(10)
        debt[0] = self.base_debt + proj.deficit[0]
        
        for i in range(1, 10):
            debt[i] = debt[i-1] + proj.deficit[i]
        
        return debt
    
    def _project_interest(self, proj: BaselineProjection) -> np.ndarray:
        """Project net interest payments."""
        interest = np.zeros(10)
        
        for i in range(10):
            avg_debt = self.base_debt if i == 0 else (proj.debt_held_by_public[i-1] + 
                                                       proj.debt_held_by_public[i]) / 2
            # Effective interest rate is lower than 10-year due to mix of maturities
            effective_rate = self.assumptions.interest_rate_10yr[i] * 0.75
            interest[i] = avg_debt * effective_rate
        
        return interest
    
    def adjust_for_policy(self, baseline: BaselineProjection, 
                         category: str, 
                         changes: np.ndarray) -> BaselineProjection:
        """
        Create a new projection with policy changes applied.
        
        Args:
            baseline: Original baseline projection
            category: Which category to modify
            changes: Array of changes for each year (in billions)
            
        Returns:
            New projection with changes applied
        """
        # Create a copy
        new_proj = BaselineProjection(
            start_year=baseline.start_year,
            years=baseline.years.copy(),
            nominal_gdp=baseline.nominal_gdp.copy(),
            real_gdp=baseline.real_gdp.copy(),
            individual_income_tax=baseline.individual_income_tax.copy(),
            corporate_income_tax=baseline.corporate_income_tax.copy(),
            payroll_taxes=baseline.payroll_taxes.copy(),
            other_revenues=baseline.other_revenues.copy(),
            social_security=baseline.social_security.copy(),
            medicare=baseline.medicare.copy(),
            medicaid=baseline.medicaid.copy(),
            other_mandatory=baseline.other_mandatory.copy(),
            defense_discretionary=baseline.defense_discretionary.copy(),
            nondefense_discretionary=baseline.nondefense_discretionary.copy(),
            net_interest=baseline.net_interest.copy(),
            debt_held_by_public=baseline.debt_held_by_public.copy(),
        )
        
        # Apply changes
        current = getattr(new_proj, category)
        setattr(new_proj, category, current + changes)
        
        return new_proj

