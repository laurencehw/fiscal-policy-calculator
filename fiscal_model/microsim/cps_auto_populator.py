"""
CPS Microdata Auto-Populator for Tax Policy Parameters.

Uses Current Population Survey (CPS ASEC) microdata to produce precise
filer counts and income statistics by threshold, replacing the heuristic
AGI-to-taxable-income adjustment in the IRS SOI pipeline.

The CPS microdata includes individual-level AGI, deductions, and weights,
enabling exact computation of:
- Number of filers with taxable income above a threshold
- Average taxable income for affected filers
- Effective tax rates by income group

This module provides a drop-in replacement for IRSSOIData.get_filers_by_bracket()
with higher fidelity for rate-change policies.
"""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Default path to CPS-derived microdata
_DEFAULT_DATA_PATH = Path(__file__).parent / "tax_microdata_2024.csv"

# Standard deduction amounts (2025 law)
_STD_DEDUCTION = {"single": 15_000, "married": 30_000}


class CPSAutoPopulator:
    """
    Compute policy-relevant statistics from CPS microdata.

    Loads the CPS ASEC-derived tax unit file and provides weighted
    aggregates matching the IRSSOIData.get_filers_by_bracket() interface.
    """

    def __init__(self, data_path: Path | str | None = None):
        path = Path(data_path) if data_path else _DEFAULT_DATA_PATH
        if not path.exists():
            raise FileNotFoundError(
                f"CPS microdata not found at {path}. "
                "Run fiscal_model/microsim/data_builder.py to generate it."
            )
        self._df = pd.read_csv(path)
        self._prepare_data()
        logger.info(
            "CPSAutoPopulator loaded %d tax units (%.1fM weighted)",
            len(self._df),
            self._df["weight"].sum() / 1e6,
        )

    def _prepare_data(self) -> None:
        """Compute taxable income and effective tax rate per record."""
        df = self._df

        # Standard deduction based on filing status
        df["deduction"] = np.where(
            df["married"] == 1,
            _STD_DEDUCTION["married"],
            _STD_DEDUCTION["single"],
        )

        # Taxable income = max(0, AGI - deduction)
        df["taxable_income"] = np.maximum(0, df["agi"] - df["deduction"])

    @staticmethod
    def is_available(data_path: Path | str | None = None) -> bool:
        """Check if CPS microdata is available."""
        path = Path(data_path) if data_path else _DEFAULT_DATA_PATH
        return path.exists()

    def get_filers_by_threshold(
        self,
        threshold: float,
        income_basis: str = "taxable_income",
    ) -> dict:
        """
        Aggregate filers above a threshold, using population weights.

        Args:
            threshold: Income threshold in dollars
            income_basis: Column to filter on ("taxable_income" or "agi")

        Returns:
            Dict matching IRSSOIData.get_filers_by_bracket() interface:
            - num_filers, num_filers_millions
            - avg_agi, avg_taxable_income
            - total_agi_billions, total_taxable_income_billions
            - total_tax_billions (estimated), effective_tax_rate
        """
        if income_basis not in ("taxable_income", "agi"):
            raise ValueError(f"income_basis must be 'taxable_income' or 'agi', got '{income_basis}'")

        df = self._df
        mask = df[income_basis] >= threshold
        affected = df[mask]

        if affected.empty:
            return {
                "num_filers": 0,
                "num_filers_millions": 0.0,
                "avg_agi": 0.0,
                "avg_taxable_income": 0.0,
                "total_agi_billions": 0.0,
                "total_taxable_income_billions": 0.0,
                "total_tax_billions": 0.0,
                "effective_tax_rate": 0.0,
            }

        w = affected["weight"].values
        total_weight = w.sum()

        agi = affected["agi"].values
        taxable = affected["taxable_income"].values

        weighted_agi = (agi * w).sum()
        weighted_taxable = (taxable * w).sum()

        # Estimate tax using a simplified progressive calculation
        # (marginal rates for 2025 MFJ brackets as rough proxy)
        avg_rate = self._estimate_avg_rate(taxable, w)
        estimated_tax = weighted_taxable * avg_rate

        return {
            "num_filers": int(round(total_weight)),
            "num_filers_millions": total_weight / 1e6,
            "avg_agi": weighted_agi / total_weight,
            "avg_taxable_income": weighted_taxable / total_weight,
            "total_agi_billions": weighted_agi / 1e9,
            "total_taxable_income_billions": weighted_taxable / 1e9,
            "total_tax_billions": estimated_tax / 1e9,
            "effective_tax_rate": estimated_tax / weighted_agi if weighted_agi > 0 else 0.0,
        }

    @staticmethod
    def _estimate_avg_rate(taxable_income: np.ndarray, weights: np.ndarray) -> float:
        """Estimate weighted-average effective rate from taxable income."""
        # Simplified rate schedule (MFJ 2025)
        brackets = np.array([0, 23850, 96950, 206700, 394600, 501050, 751600])
        rates = np.array([0.10, 0.12, 0.22, 0.24, 0.32, 0.35, 0.37])

        total_tax = np.zeros(len(taxable_income))
        for i in range(len(rates)):
            lower = brackets[i]
            upper = brackets[i + 1] if i + 1 < len(brackets) else np.inf
            income_in_bracket = np.clip(taxable_income - lower, 0, upper - lower)
            total_tax += income_in_bracket * rates[i]

        return (total_tax * weights).sum() / (taxable_income * weights).sum()
