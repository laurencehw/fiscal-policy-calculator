"""
Data loaders for fiscal model inputs.
"""

from .irs_soi import IRSSOIData, TaxBracketData
from .fred_data import FREDData
from .capital_gains import CapitalGainsBaseline

__all__ = [
    "IRSSOIData",
    "TaxBracketData",
    "FREDData",
    "CapitalGainsBaseline",
]
