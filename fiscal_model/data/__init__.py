"""
Data integration layer for fiscal_model.

This package provides data loaders and validators for:
- IRS Statistics of Income (SOI) tax data
- FRED (Federal Reserve Economic Data) economic indicators

Example usage:
    >>> from fiscal_model.data import IRSSOIData, FREDData
    >>> irs = IRSSOIData()
    >>> fred = FREDData(api_key="your_key")
    >>> revenue = irs.get_total_revenue(2021)
    >>> gdp = fred.get_gdp()
"""

from fiscal_model.data.irs_soi import IRSSOIData, TaxBracketData
from fiscal_model.data.capital_gains import CapitalGainsBaseline
from fiscal_model.data.fred_data import FREDData
from fiscal_model.data.validation import DataValidator, ValidationResult

__all__ = [
    'IRSSOIData',
    'TaxBracketData',
    'CapitalGainsBaseline',
    'FREDData',
    'DataValidator',
    'ValidationResult',
]
