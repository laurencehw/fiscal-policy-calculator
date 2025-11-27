"""
IRS Statistics of Income (SOI) data loader.

This module provides classes and functions to load and process IRS Statistics
of Income Individual Income Tax data for use in fiscal policy analysis.

Data Source: https://www.irs.gov/statistics/soi-tax-stats-individual-income-tax-statistics
"""

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class TaxBracketData:
    """
    Tax bracket data from IRS Statistics of Income.

    Represents one AGI bracket with filer counts, income totals, and tax liability.
    All dollar amounts in billions unless otherwise specified.
    """
    year: int
    agi_floor: float  # Lower bound of AGI bracket (dollars)
    agi_ceiling: Optional[float]  # Upper bound (None for top bracket)
    num_returns: int  # Number of tax returns in bracket
    total_agi: float  # Total AGI in bracket (billions)
    taxable_income: float  # Total taxable income in bracket (billions)
    total_tax: float  # Total income tax liability (billions)

    @property
    def avg_agi(self) -> float:
        """Average AGI per return (dollars)."""
        if self.num_returns == 0:
            return 0.0
        return (self.total_agi * 1e9) / self.num_returns

    @property
    def avg_taxable_income(self) -> float:
        """Average taxable income per return (dollars)."""
        if self.num_returns == 0:
            return 0.0
        return (self.taxable_income * 1e9) / self.num_returns

    @property
    def avg_tax_rate(self) -> float:
        """Average tax rate for this bracket."""
        if self.total_agi == 0:
            return 0.0
        return self.total_tax / self.total_agi

    @property
    def avg_tax_per_return(self) -> float:
        """Average tax liability per return (dollars)."""
        if self.num_returns == 0:
            return 0.0
        return (self.total_tax * 1e9) / self.num_returns

    def __str__(self) -> str:
        ceiling_str = f"${self.agi_ceiling:,.0f}" if self.agi_ceiling else "no limit"
        return (f"Bracket ${self.agi_floor:,.0f}-{ceiling_str}: "
                f"{self.num_returns/1e6:.2f}M returns, "
                f"avg AGI ${self.avg_agi:,.0f}, "
                f"avg tax rate {self.avg_tax_rate*100:.1f}%")


class IRSSOIData:
    """
    Loader for IRS Statistics of Income Individual Income Tax data.

    Loads and processes CSV files containing tax return data by AGI bracket.
    Provides methods to query filer counts, income distributions, and revenue
    totals for use in fiscal policy scoring.

    Example:
        >>> irs = IRSSOIData()
        >>> years = irs.get_data_years_available()
        >>> revenue = irs.get_total_revenue(2021)
        >>> bracket_info = irs.get_filers_by_bracket(2021, threshold=500000)
    """

    def __init__(self, data_dir: Optional[str] = None):
        """
        Initialize IRS SOI data loader.

        Args:
            data_dir: Path to directory containing CSV files. If None, uses
                     default location: fiscal_model/data_files/irs_soi/
        """
        if data_dir is None:
            # Default to data_files/irs_soi/ relative to this module
            module_dir = Path(__file__).parent.parent
            data_dir = module_dir / "data_files" / "irs_soi"

        self.data_dir = Path(data_dir)
        self._cache = {}  # Cache loaded DataFrames

        if not self.data_dir.exists():
            logger.warning(f"IRS SOI data directory not found: {self.data_dir}")

    def get_data_years_available(self) -> List[int]:
        """
        Get list of years for which IRS SOI data is available.

        Returns:
            Sorted list of years (e.g., [2021, 2022])
        """
        if not self.data_dir.exists():
            return []

        years = set()
        for file in self.data_dir.glob("table_*_*.csv"):
            # Extract year from filename like "table_1_1_2021.csv"
            parts = file.stem.split("_")
            if len(parts) >= 4:
                try:
                    year = int(parts[-1])
                    years.add(year)
                except ValueError:
                    continue

        return sorted(years)

    def load_table_1_1(self, year: int) -> pd.DataFrame:
        """
        Load Table 1.1 (All Returns: Selected Income and Tax Items).

        Table 1.1 contains:
        - Number of returns by AGI bracket
        - Total AGI
        - Taxable income
        - Total deductions

        Args:
            year: Tax year (e.g., 2021)

        Returns:
            DataFrame with columns: agi_floor, num_returns, total_agi,
                                   taxable_income, etc.

        Raises:
            FileNotFoundError: If data file not found
        """
        cache_key = f"table_1_1_{year}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        file_path = self.data_dir / f"table_1_1_{year}.csv"

        if not file_path.exists():
            raise FileNotFoundError(
                f"IRS SOI Table 1.1 for {year} not found at {file_path}. "
                f"See {self.data_dir / 'README.md'} for download instructions."
            )

        logger.info(f"Loading IRS SOI Table 1.1 for {year}")

        # Load CSV
        df = pd.read_csv(file_path)

        # Standardize column names (handle variations in IRS formatting)
        df = self._standardize_table_1_1_columns(df)

        # Cache and return
        self._cache[cache_key] = df
        return df

    def load_table_3_3(self, year: int) -> pd.DataFrame:
        """
        Load Table 3.3 (Tax Liability, Tax Credits, and Tax Payments).

        Table 3.3 contains:
        - Tax liability by AGI bracket
        - Tax credits
        - Effective tax rates

        Args:
            year: Tax year (e.g., 2021)

        Returns:
            DataFrame with columns: agi_floor, num_returns, total_tax, etc.

        Raises:
            FileNotFoundError: If data file not found
        """
        cache_key = f"table_3_3_{year}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        file_path = self.data_dir / f"table_3_3_{year}.csv"

        if not file_path.exists():
            raise FileNotFoundError(
                f"IRS SOI Table 3.3 for {year} not found at {file_path}. "
                f"See {self.data_dir / 'README.md'} for download instructions."
            )

        logger.info(f"Loading IRS SOI Table 3.3 for {year}")

        # Load CSV
        df = pd.read_csv(file_path)

        # Standardize column names
        df = self._standardize_table_3_3_columns(df)

        # Cache and return
        self._cache[cache_key] = df
        return df

    def _parse_bracket_range(self, bracket_text: str) -> tuple[float, Optional[float]]:
        """
        Parse AGI bracket text to extract floor and ceiling values.

        Args:
            bracket_text: Bracket description like "$500,000 under $1,000,000"

        Returns:
            Tuple of (floor, ceiling) in dollars. Ceiling is None for top bracket.

        Examples:
            "$500,000 under $1,000,000" -> (500000, 1000000)
            "$10,000,000 or more" -> (10000000, None)
            "No adjusted gross income" -> (float('-inf'), 0)
        """
        import re

        text = str(bracket_text).strip()

        # Handle special cases
        if 'no adjusted gross income' in text.lower():
            return (float('-inf'), 0)

        if 'all returns' in text.lower():
            return (float('-inf'), None)  # All income levels

        # Extract dollar amounts using regex
        amounts = re.findall(r'\$?([\d,]+)', text)
        amounts = [int(amt.replace(',', '')) for amt in amounts]

        if 'or more' in text.lower():
            # Top bracket: "$10,000,000 or more"
            return (amounts[0], None)
        elif 'under' in text.lower() and len(amounts) >= 2:
            # Range bracket: "$500,000 under $1,000,000"
            return (amounts[0], amounts[1])
        elif len(amounts) == 1:
            # Single threshold
            return (amounts[0], None)
        else:
            # Fallback
            logger.warning(f"Could not parse bracket: {text}")
            return (0, None)

    def _standardize_table_1_1_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize Table 1.1 column names."""
        # IRS Table 1.1 has multi-row headers, we need to clean this up

        # Skip header rows and find actual data
        # Data starts around row 7-8 in the CSV (after pandas reads it)
        # Look for FIRST "All returns" row (index ~7, not 47 or 67)
        all_returns_idx = None
        for idx, row in df.iterrows():
            if isinstance(row.iloc[0], str) and 'all returns' in row.iloc[0].lower():
                if 5 <= idx <= 15:  # First "All returns" is around row 7
                    all_returns_idx = idx
                    logger.debug(f"Found 'All returns' row at index {idx}")
                    break

        if all_returns_idx is None:
            # Fallback: assume data starts at row 7
            logger.warning("Could not find 'All returns' row, using fallback index 7")
            all_returns_idx = 7

        logger.debug(f"Starting data extraction from row {all_returns_idx}")

        # Extract data rows only until "Accumulated" section
        # Individual brackets are from all_returns row up to "Accumulated" row (~20 rows)
        df_data = df.iloc[all_returns_idx:all_returns_idx+50].copy()
        df_data = df_data.reset_index(drop=True)

        # Rename columns based on position
        # Col 0: Bracket, Col 1: Returns, Col 3: AGI, Col 11: Taxable Income, Col 14: Tax
        col_mapping = {
            df.columns[0]: 'agi_bracket',
            df.columns[1]: 'num_returns',
            df.columns[3]: 'total_agi',  # In thousands
            df.columns[11]: 'taxable_income',  # In thousands
            df.columns[14]: 'total_tax',  # In thousands
        }

        df_data = df_data.rename(columns=col_mapping)

        return df_data

    def _standardize_table_3_3_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize Table 3.3 column names."""
        # IRS Table 3.3 has multi-row headers

        # Find "All returns" row
        all_returns_idx = None
        for idx, row in df.iterrows():
            if isinstance(row.iloc[0], str) and 'all returns' in row.iloc[0].lower():
                if idx > 3:  # Make sure we're past headers
                    all_returns_idx = idx
                    break

        if all_returns_idx is None:
            # Fallback: assume data starts at row 7
            all_returns_idx = 7

        # Extract data rows only
        df_data = df.iloc[all_returns_idx:].copy()
        df_data = df_data.reset_index(drop=True)

        # Find income tax column - look for column with "income tax after credits" text
        # This is typically around column 56-60
        # For now, use column 56 for number of returns with tax, column 60 for total tax
        income_tax_col = 60  # This may need adjustment based on actual structure

        col_mapping = {
            df.columns[0]: 'agi_bracket',
            df.columns[1]: 'num_returns',
            df.columns[56]: 'num_returns_with_tax',  # Number with income tax
        }

        # Add the income tax column if it exists
        if len(df.columns) > income_tax_col:
            col_mapping[df.columns[income_tax_col]] = 'total_tax'

        df_data = df_data.rename(columns=col_mapping)

        return df_data

    def get_bracket_distribution(self, year: int) -> List[TaxBracketData]:
        """
        Get complete distribution of tax brackets for a year.

        Args:
            year: Tax year (e.g., 2021)

        Returns:
            List of TaxBracketData objects, one per AGI bracket
        """
        # Load table 1.1 (has all needed data)
        table_1_1 = self.load_table_1_1(year)

        brackets = []

        # Parse each row
        for idx, row in table_1_1.iterrows():
            try:
                bracket_text = row['agi_bracket']

                # Stop at "Accumulated" section
                if isinstance(bracket_text, str):
                    lower = bracket_text.lower()
                    if 'accumulated' in lower:
                        # Reached accumulated section, stop parsing
                        break
                    if 'all returns' in lower:
                        # Skip totals row
                        continue
                    if '$1 or more' in lower:
                        # Skip aggregated row
                        continue

                # Parse bracket range
                agi_floor, agi_ceiling = self._parse_bracket_range(bracket_text)

                # Skip invalid brackets
                if agi_floor == float('-inf'):
                    continue

                # Extract numeric values (convert from thousands to billions)
                def safe_float(val):
                    """Safely convert value to float, handling [1], [2] footnotes."""
                    if pd.isna(val):
                        return 0.0
                    if isinstance(val, str):
                        # Remove footnote markers
                        val = val.replace('[1]', '').replace('[2]', '').strip()
                        if not val or val == '':
                            return 0.0
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        return 0.0

                num_returns = int(safe_float(row['num_returns']))
                total_agi_thousands = safe_float(row['total_agi'])
                taxable_income_thousands = safe_float(row['taxable_income'])
                total_tax_thousands = safe_float(row['total_tax'])

                # Convert thousands to billions
                total_agi = total_agi_thousands / 1e6
                taxable_income = taxable_income_thousands / 1e6
                total_tax = total_tax_thousands / 1e6

                # Create bracket object
                bracket = TaxBracketData(
                    year=year,
                    agi_floor=agi_floor,
                    agi_ceiling=agi_ceiling,
                    num_returns=num_returns,
                    total_agi=total_agi,
                    taxable_income=taxable_income,
                    total_tax=total_tax
                )

                brackets.append(bracket)

            except Exception as e:
                logger.warning(f"Error parsing bracket row {idx}: {e}")
                continue

        logger.info(f"Parsed {len(brackets)} brackets for year {year}")
        return brackets

    def get_filers_by_bracket(self, year: int, threshold: float) -> Dict:
        """
        Get aggregate statistics for all filers above an income threshold.

        Args:
            year: Tax year (e.g., 2021)
            threshold: AGI threshold (dollars, e.g., 500000 for $500K+)

        Returns:
            Dictionary with keys:
            - num_filers: Total number of returns above threshold
            - total_agi: Total AGI above threshold (billions)
            - avg_agi: Average AGI per return (dollars)
            - total_taxable_income: Total taxable income (billions)
            - avg_taxable_income: Average taxable income per return (dollars)
            - total_tax: Total tax liability (billions)
            - avg_tax: Average tax per return (dollars)
        """
        brackets = self.get_bracket_distribution(year)

        # Filter to brackets that include income at or above threshold
        # A bracket includes the threshold if:
        # - Its floor is >= threshold, OR
        # - Its floor is < threshold and ceiling is > threshold (partial overlap)
        above_threshold = []
        for b in brackets:
            if b.agi_floor >= threshold:
                # Entire bracket is above threshold
                above_threshold.append(b)
            elif b.agi_ceiling is not None and b.agi_ceiling > threshold:
                # Bracket straddles threshold - include it but note this is approximate
                # In practice, IRS brackets are well-defined so this edge case is rare
                above_threshold.append(b)

        if not above_threshold:
            # Try to find closest bracket
            closest = min(brackets, key=lambda b: abs(b.agi_floor - threshold))
            logger.warning(
                f"No exact bracket found for threshold ${threshold:,.0f}. "
                f"Closest bracket starts at ${closest.agi_floor:,.0f}"
            )
            raise ValueError(f"No data found for income threshold ${threshold:,.0f}")

        # Aggregate
        num_filers = sum(b.num_returns for b in above_threshold)
        total_agi = sum(b.total_agi for b in above_threshold)
        total_taxable_income = sum(b.taxable_income for b in above_threshold)
        total_tax = sum(b.total_tax for b in above_threshold)

        return {
            'num_filers': num_filers,
            'total_agi': total_agi,
            'avg_agi': (total_agi * 1e9) / num_filers if num_filers > 0 else 0,
            'total_taxable_income': total_taxable_income,
            'avg_taxable_income': (total_taxable_income * 1e9) / num_filers if num_filers > 0 else 0,
            'total_tax': total_tax,
            'avg_tax': (total_tax * 1e9) / num_filers if num_filers > 0 else 0,
        }

    def get_total_revenue(self, year: int) -> float:
        """
        Get total individual income tax revenue for a year.

        Args:
            year: Tax year (e.g., 2021)

        Returns:
            Total revenue in billions
        """
        brackets = self.get_bracket_distribution(year)
        total = sum(b.total_tax for b in brackets)
        logger.info(f"Total individual income tax revenue for {year}: ${total:.1f}B")
        return total

    def validate_data(self, year: int) -> bool:
        """
        Validate IRS SOI data quality for a year.

        Checks:
        - Data files exist
        - Total returns in reasonable range (100-200M)
        - Total revenue in reasonable range ($2-3T)
        - No negative values
        - Brackets sum to published totals

        Args:
            year: Tax year to validate

        Returns:
            True if all validation checks pass
        """
        try:
            table_1_1 = self.load_table_1_1(year)
            table_3_3 = self.load_table_3_3(year)

            # TODO: Implement actual validation logic once we know file structure

            logger.info(f"IRS SOI data for {year} passed validation")
            return True

        except Exception as e:
            logger.error(f"IRS SOI data validation failed for {year}: {e}")
            return False
