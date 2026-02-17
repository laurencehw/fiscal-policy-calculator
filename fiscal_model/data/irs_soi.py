"""
IRS SOI data loader utilities.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import re

import pandas as pd


@dataclass
class TaxBracketData:
    """IRS SOI bracket-level aggregates (amounts in billions)."""

    year: int
    agi_floor: float
    agi_ceiling: Optional[float]
    num_returns: int
    total_agi: float
    taxable_income: float
    total_tax: float


class IRSSOIData:
    """Load IRS SOI Table 1.1 CSV files shipped in `data_files/irs_soi`."""

    _NO_AGI_LABEL = "No adjusted gross income"

    def __init__(self, data_dir: Optional[Path] = None):
        default_dir = Path(__file__).resolve().parent.parent / "data_files" / "irs_soi"
        self.data_dir = Path(data_dir) if data_dir else default_dir
        self._bracket_cache: dict[int, list[TaxBracketData]] = {}
        self._table_cache: dict[int, pd.DataFrame] = {}

    def get_data_years_available(self) -> list[int]:
        years: list[int] = []
        for path in self.data_dir.glob("table_1_1_*.csv"):
            match = re.search(r"table_1_1_(\d{4})\.csv$", path.name)
            if match:
                years.append(int(match.group(1)))
        return sorted(set(years))

    def get_total_revenue(self, year: int) -> float:
        """Return total income tax (billions) for `year` from Table 1.1."""
        df = self._read_table_1_1(year)
        all_returns_idx = self._first_all_returns_idx(df)
        total_tax_thousands = self._to_float(df.iloc[all_returns_idx, 16])
        return total_tax_thousands / 1_000_000.0

    def get_bracket_distribution(self, year: int) -> list[TaxBracketData]:
        if year in self._bracket_cache:
            return self._bracket_cache[year]

        df = self._read_table_1_1(year)
        start_idx = self._first_all_returns_idx(df)
        end_idx = self._first_accumulated_idx(df, start_idx)

        brackets: list[TaxBracketData] = []
        for idx in range(start_idx + 1, end_idx):
            label = str(df.iloc[idx, 0]).strip()
            parsed = self._parse_bracket_label(label)
            if parsed is None:
                continue

            agi_floor, agi_ceiling = parsed
            num_returns = int(round(self._to_float(df.iloc[idx, 1])))
            if num_returns <= 0:
                continue

            total_agi = self._to_float(df.iloc[idx, 3]) / 1_000_000.0
            taxable_income = self._to_float(df.iloc[idx, 11]) / 1_000_000.0
            total_tax = self._to_float(df.iloc[idx, 16]) / 1_000_000.0

            brackets.append(
                TaxBracketData(
                    year=year,
                    agi_floor=agi_floor,
                    agi_ceiling=agi_ceiling,
                    num_returns=num_returns,
                    total_agi=total_agi,
                    taxable_income=taxable_income,
                    total_tax=total_tax,
                )
            )

        brackets.sort(key=lambda b: b.agi_floor)
        self._bracket_cache[year] = brackets
        return brackets

    def get_filers_by_bracket(self, year: int, threshold: float) -> dict:
        """
        Aggregate filers and incomes above `threshold`.

        Returns keys used by policy auto-population logic.
        """
        threshold = max(0.0, float(threshold))
        brackets = self.get_bracket_distribution(year)

        total_filers = 0.0
        total_agi_dollars = 0.0
        total_taxable_dollars = 0.0
        total_tax_dollars = 0.0

        for bracket in brackets:
            share = self._share_above_threshold(bracket, threshold)
            if share <= 0.0:
                continue

            filers = bracket.num_returns * share
            total_filers += filers
            total_agi_dollars += bracket.total_agi * 1_000_000_000.0 * share
            total_taxable_dollars += bracket.taxable_income * 1_000_000_000.0 * share
            total_tax_dollars += bracket.total_tax * 1_000_000_000.0 * share

        avg_agi = total_agi_dollars / total_filers if total_filers > 0 else 0.0
        avg_taxable_income = (
            total_taxable_dollars / total_filers if total_filers > 0 else 0.0
        )
        effective_tax_rate = total_tax_dollars / total_agi_dollars if total_agi_dollars > 0 else 0.0

        return {
            "num_filers": int(round(total_filers)),
            "num_filers_millions": total_filers / 1_000_000.0,
            "avg_agi": avg_agi,
            "avg_taxable_income": avg_taxable_income,
            "total_agi_billions": total_agi_dollars / 1_000_000_000.0,
            "total_taxable_income_billions": total_taxable_dollars / 1_000_000_000.0,
            "total_tax_billions": total_tax_dollars / 1_000_000_000.0,
            "effective_tax_rate": effective_tax_rate,
        }

    def _read_table_1_1(self, year: int) -> pd.DataFrame:
        if year in self._table_cache:
            return self._table_cache[year]

        path = self.data_dir / f"table_1_1_{year}.csv"
        if not path.exists():
            raise FileNotFoundError(f"IRS SOI table not found: {path}")

        df = pd.read_csv(path, header=None, dtype=str, na_filter=False)
        self._table_cache[year] = df
        return df

    @staticmethod
    def _to_float(value) -> float:
        text = str(value).strip()
        if not text or text.lower() == "nan":
            return 0.0
        if text.startswith("[") and text.endswith("]"):
            return 0.0
        text = text.replace(",", "")
        try:
            return float(text)
        except ValueError:
            return 0.0

    @staticmethod
    def _first_all_returns_idx(df: pd.DataFrame) -> int:
        col0 = df[0].astype(str).str.strip()
        matches = col0[col0 == "All returns"]
        if matches.empty:
            raise ValueError("Could not locate 'All returns' row in IRS SOI file")
        return int(matches.index[0])

    @staticmethod
    def _first_accumulated_idx(df: pd.DataFrame, start_idx: int) -> int:
        col0 = df[0].astype(str).str.strip()
        candidates = col0[col0.str.startswith("Accumulated from", na=False)].index
        after_start = [int(i) for i in candidates if int(i) > start_idx]
        return min(after_start) if after_start else len(df)

    def _parse_bracket_label(self, label: str) -> Optional[tuple[float, Optional[float]]]:
        if not label or label == "Size of adjusted gross income":
            return None
        if label == self._NO_AGI_LABEL:
            return (0.0, 1.0)

        match_under = re.match(r"^\$([\d,]+)\s+under\s+\$([\d,]+)$", label)
        if match_under:
            floor = float(match_under.group(1).replace(",", ""))
            ceiling = float(match_under.group(2).replace(",", ""))
            return (floor, ceiling)

        match_top = re.match(r"^\$([\d,]+)\s+or more$", label)
        if match_top:
            floor = float(match_top.group(1).replace(",", ""))
            return (floor, None)

        return None

    @staticmethod
    def _share_above_threshold(bracket: TaxBracketData, threshold: float) -> float:
        if threshold <= bracket.agi_floor:
            return 1.0

        if bracket.agi_ceiling is not None:
            if threshold >= bracket.agi_ceiling:
                return 0.0
            width = max(bracket.agi_ceiling - bracket.agi_floor, 1.0)
            return max(0.0, min(1.0, (bracket.agi_ceiling - threshold) / width))

        # Top open-ended bracket: use average AGI to avoid assuming full inclusion.
        avg_agi = (
            (bracket.total_agi * 1_000_000_000.0) / bracket.num_returns
            if bracket.num_returns > 0
            else bracket.agi_floor
        )
        if avg_agi <= threshold:
            return 0.0
        denom = max(avg_agi - bracket.agi_floor, 1.0)
        return max(0.0, min(1.0, (avg_agi - threshold) / denom))
