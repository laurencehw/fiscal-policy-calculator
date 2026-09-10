"""
IRS SOI data loader utilities.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional
import re

import pandas as pd


#: The four filing statuses IRS SOI Table 1.2 reports separately. These are the
#: keys of every per-status threshold mapping in the model; "joint" is SOI's
#: *"Returns of married persons filing jointly and returns of surviving
#: spouses"*, the population that uses the IRC section 1(j)(2)(A) rate schedule.
FILING_STATUSES: tuple[str, ...] = ("joint", "separate", "head_of_household", "single")

#: The two income measures Table 1.1 and Table 1.2 both publish by AGI size
#: class, and which one a reform is priced on is a fact about its source, not
#: about its shape. CBO's Option 46 says *"a surtax ... would be imposed on
#: **AGI** above $20,000"*; the 2025 rate schedule's bracket floors are
#: statutory boundaries on **taxable** income. The same table carries both
#: columns, so the choice costs nothing to make correctly and 40% of the base
#: to make wrongly. See ``fiscal_model.policies_core.TaxPolicy.income_measure``
#: and ``planning/lanes/HSB_h2b_agi_column.md``.
INCOME_MEASURES: tuple[str, ...] = ("taxable_income", "agi")

#: Table 1.2's own column-block headings, which is how the loader finds its
#: columns - the sheet is 63 columns of five repeating 12-column blocks and
#: hard-coded offsets would break silently if the IRS re-laid it out.
_FILING_STATUS_HEADINGS: dict[str, str] = {
    "joint": "Returns of married persons filing jointly and returns of surviving spouses",
    "separate": "Returns of married persons filing separately",
    "head_of_household": "Returns of heads of households",
    "single": "Returns of single persons",
}

#: Offsets of the four quantities this model reads, from a status block's first
#: column. Each block is: returns, AGI, itemised (N, amount), standard
#: (N, amount), taxable income (N, amount), tax after credits (N, amount),
#: total income tax (N, amount).
_BLOCK_OFFSET_RETURNS = 0
_BLOCK_OFFSET_AGI = 1
_BLOCK_OFFSET_TAXABLE_INCOME = 7
_BLOCK_OFFSET_TOTAL_TAX = 11


@dataclass
class TaxBracketData:
    """IRS SOI bracket-level aggregates (amounts in billions)."""

    year: int
    agi_floor: float
    agi_ceiling: Optional[float]
    # Whole returns off Table 1.1; fractional once a class has been apportioned
    # across filing statuses by ``get_bracket_distribution_by_status``, where a
    # share of a sample-based estimate is not an integer and rounding it would
    # break the identity that the four statuses sum back to the pooled class.
    num_returns: float
    total_agi: float
    taxable_income: float
    total_tax: float


class IRSSOIData:
    """Load IRS SOI Table 1.1 CSV files shipped in `data_files/irs_soi`.

    Table 1.2 - the same AGI size classes split by filing status - is read too,
    but only for its *composition*: see
    :meth:`get_bracket_distribution_by_status`.
    """

    _NO_AGI_LABEL = "No adjusted gross income"
    _ALL_RETURNS_LABEL = "All returns"
    _TABLE_1_2_START_LABEL = "All returns, total"
    _TABLE_1_2_END_LABEL = "Taxable returns, total"

    def __init__(self, data_dir: Optional[Path] = None):
        default_dir = Path(__file__).resolve().parent.parent / "data_files" / "irs_soi"
        self.data_dir = Path(data_dir) if data_dir else default_dir
        self._bracket_cache: dict[int, list[TaxBracketData]] = {}
        self._table_cache: dict[int, pd.DataFrame] = {}
        self._status_bracket_cache: dict[int, dict[str, list[TaxBracketData]]] = {}
        self._status_table_cache: dict[int, pd.DataFrame] = {}

    def get_data_years_available(self) -> list[int]:
        years: list[int] = []
        for path in self.data_dir.glob("table_1_1_*.csv"):
            match = re.search(r"table_1_1_(\d{4})\.csv$", path.name)
            if match:
                years.append(int(match.group(1)))
        return sorted(set(years))

    def get_filing_status_years_available(self) -> list[int]:
        """Years for which the Table 1.2 (by-filing-status) transcription exists."""
        years: list[int] = []
        for path in self.data_dir.glob("table_1_2_*.csv"):
            match = re.search(r"table_1_2_(\d{4})\.csv$", path.name)
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

    # -- Filing-status split (SOI Table 1.2) --------------------------------
    #
    # The rule, stated once: **Table 1.1 supplies the level, Table 1.2 supplies
    # the within-class composition.** For every AGI size class and every field,
    # each status gets Table 1.1's class total times that status's share of the
    # class in Table 1.2.
    #
    # Reading Table 1.2 wholesale would be simpler and is wrong for this
    # purpose: its taxable-income column is measured on *all* returns
    # ($11,944.4B in 2023) where Table 1.1 column 11 is measured on *taxable*
    # returns ($11,625.3B), so switching tables would move every score that used
    # the split by 2.7% for a reason that has nothing to do with filing status.
    # Apportioning instead makes the split exactly neutral: the four statuses
    # sum back to the pooled class total, so evaluating a split at one uniform
    # threshold reproduces :meth:`get_filers_by_bracket` to the cent, and any
    # movement is attributable to the per-status floors alone.

    def get_bracket_distribution_by_status(self, year: int) -> dict[str, list[TaxBracketData]]:
        """Table 1.1's bracket distribution, apportioned across filing statuses.

        Returns one list per entry of :data:`FILING_STATUSES`, aligned index for
        index with :meth:`get_bracket_distribution` for the same year.
        """
        if year in self._status_bracket_cache:
            return self._status_bracket_cache[year]

        pooled = self.get_bracket_distribution(year)
        class_rows = self._read_table_1_2_classes(year)

        if len(class_rows) != len(pooled):
            raise ValueError(
                f"IRS SOI tables disagree for {year}: Table 1.1 has {len(pooled)} AGI "
                f"classes, Table 1.2 has {len(class_rows)}"
            )

        split: dict[str, list[TaxBracketData]] = {status: [] for status in FILING_STATUSES}
        for bracket, row in zip(pooled, class_rows):
            if (bracket.agi_floor, bracket.agi_ceiling) != (row["agi_floor"], row["agi_ceiling"]):
                raise ValueError(
                    f"IRS SOI tables disagree for {year} on AGI class "
                    f"{bracket.agi_floor}-{bracket.agi_ceiling}: Table 1.2 has "
                    f"{row['agi_floor']}-{row['agi_ceiling']}"
                )

            shares = {
                field: self._composition_shares(row["by_status"], field)
                for field in ("num_returns", "total_agi", "taxable_income", "total_tax")
            }
            for status in FILING_STATUSES:
                split[status].append(
                    TaxBracketData(
                        year=year,
                        agi_floor=bracket.agi_floor,
                        agi_ceiling=bracket.agi_ceiling,
                        num_returns=bracket.num_returns * shares["num_returns"][status],
                        total_agi=bracket.total_agi * shares["total_agi"][status],
                        taxable_income=bracket.taxable_income * shares["taxable_income"][status],
                        total_tax=bracket.total_tax * shares["total_tax"][status],
                    )
                )

        self._status_bracket_cache[year] = split
        return split

    def get_filers_by_status_thresholds(
        self,
        year: int,
        thresholds: dict[str, float],
        *,
        income_measure: str = "taxable_income",
    ) -> dict:
        """Aggregate filers and incomes above a *per-filing-status* threshold.

        ``thresholds`` maps each entry of :data:`FILING_STATUSES` to that
        status's own floor. Returns the same keys as
        :meth:`get_filers_by_bracket`, summed across statuses, plus a
        ``by_status`` breakdown and ``marginal_income_dollars`` - the quantity a
        rate change applies to, which is *not* recoverable from the aggregate
        average once the statuses face different floors.

        ``income_measure`` selects which of :data:`INCOME_MEASURES` the marginal
        quantity is measured on. Both columns are returned either way - only
        ``marginal_income_dollars`` and each status's ``marginal_income_dollars``
        change - because a caller that wants the other column's average for a
        caption or a diagnostic should not have to run the aggregation twice.
        The threshold itself is compared against the AGI size class in both
        cases, which is what SOI publishes; an AGI-stated reform is the one
        where the quantity subtracted from it is then measured the same way.
        """
        if income_measure not in INCOME_MEASURES:
            raise ValueError(
                f"unknown income_measure {income_measure!r}; "
                f"expected one of {', '.join(INCOME_MEASURES)}"
            )
        missing = [status for status in FILING_STATUSES if status not in thresholds]
        if missing:
            raise ValueError(f"threshold missing for filing status(es): {', '.join(missing)}")

        split = self.get_bracket_distribution_by_status(year)

        totals = {"filers": 0.0, "agi": 0.0, "taxable": 0.0, "tax": 0.0, "marginal": 0.0}
        by_status: dict[str, dict] = {}

        for status in FILING_STATUSES:
            threshold = max(0.0, float(thresholds[status]))
            filers = 0.0
            agi_dollars = 0.0
            taxable_dollars = 0.0
            tax_dollars = 0.0

            for bracket in split[status]:
                share = self._share_above_threshold(bracket, threshold)
                if share <= 0.0:
                    continue
                filers += bracket.num_returns * share
                agi_dollars += bracket.total_agi * 1_000_000_000.0 * share
                taxable_dollars += bracket.taxable_income * 1_000_000_000.0 * share
                tax_dollars += bracket.total_tax * 1_000_000_000.0 * share

            avg_taxable = taxable_dollars / filers if filers > 0 else 0.0
            avg_agi = agi_dollars / filers if filers > 0 else 0.0
            # Mirrors the pooled path exactly: marginal income is the average
            # above the floor times the count, and a threshold of zero means the
            # whole base rather than "income above zero".
            avg_measure = avg_agi if income_measure == "agi" else avg_taxable
            per_return = avg_measure if threshold == 0 else max(0.0, avg_measure - threshold)
            marginal = per_return * filers

            by_status[status] = {
                "threshold": threshold,
                "num_filers": filers,
                "num_filers_millions": filers / 1_000_000.0,
                "avg_agi": avg_agi,
                "avg_taxable_income": avg_taxable,
                "total_agi_billions": agi_dollars / 1_000_000_000.0,
                "total_taxable_income_billions": taxable_dollars / 1_000_000_000.0,
                "total_tax_billions": tax_dollars / 1_000_000_000.0,
                "marginal_income_dollars": marginal,
            }

            totals["filers"] += filers
            totals["agi"] += agi_dollars
            totals["taxable"] += taxable_dollars
            totals["tax"] += tax_dollars
            totals["marginal"] += marginal

        filers = totals["filers"]
        return {
            "num_filers": int(round(filers)),
            "num_filers_millions": filers / 1_000_000.0,
            "avg_agi": totals["agi"] / filers if filers > 0 else 0.0,
            "avg_taxable_income": totals["taxable"] / filers if filers > 0 else 0.0,
            "total_agi_billions": totals["agi"] / 1_000_000_000.0,
            "total_taxable_income_billions": totals["taxable"] / 1_000_000_000.0,
            "total_tax_billions": totals["tax"] / 1_000_000_000.0,
            "effective_tax_rate": totals["tax"] / totals["agi"] if totals["agi"] > 0 else 0.0,
            "marginal_income_dollars": totals["marginal"],
            # Which column ``marginal_income_dollars`` was measured on, so a
            # caller cannot read a marginal AGI aggregate as a taxable one.
            "income_measure": income_measure,
            "by_status": by_status,
        }

    @staticmethod
    def _composition_shares(by_status: dict[str, dict], field: str) -> dict[str, float]:
        """Each status's share of one field within one AGI class.

        Normalised on the four statuses rather than read off Table 1.2's own
        "all returns" block, because the two disagree by a few tenths of a
        percent in the sparse classes (SOI rounds and suppresses each block
        independently) and normalising is what makes the split sum back to
        Table 1.1 exactly.
        """
        values = {status: by_status[status][field] for status in FILING_STATUSES}
        total = sum(values.values())
        if total == 0:
            return {status: 0.0 for status in FILING_STATUSES}
        return {status: value / total for status, value in values.items()}

    def _read_table_1_2_classes(self, year: int) -> list[dict]:
        """Parse Table 1.2's AGI size classes into per-status raw aggregates."""
        df = self._read_table_1_2(year)
        columns = self._filing_status_block_columns(df)

        labels = df[0].astype(str).str.strip()
        start_matches = labels[labels == self._TABLE_1_2_START_LABEL]
        if start_matches.empty:
            raise ValueError(
                f"Could not locate '{self._TABLE_1_2_START_LABEL}' row in IRS SOI Table 1.2"
            )
        start_idx = int(start_matches.index[0])
        end_matches = [
            int(idx)
            for idx in labels[labels == self._TABLE_1_2_END_LABEL].index
            if int(idx) > start_idx
        ]
        end_idx = min(end_matches) if end_matches else len(df)

        rows: list[dict] = []
        for idx in range(start_idx + 1, end_idx):
            parsed = self._parse_bracket_label(str(df.iloc[idx, 0]).strip())
            if parsed is None:
                continue
            agi_floor, agi_ceiling = parsed
            by_status: dict[str, dict] = {}
            for status, first_col in columns.items():
                by_status[status] = {
                    "num_returns": self._to_float(df.iloc[idx, first_col + _BLOCK_OFFSET_RETURNS]),
                    "total_agi": self._to_float(df.iloc[idx, first_col + _BLOCK_OFFSET_AGI]),
                    "taxable_income": self._to_float(
                        df.iloc[idx, first_col + _BLOCK_OFFSET_TAXABLE_INCOME]
                    ),
                    "total_tax": self._to_float(
                        df.iloc[idx, first_col + _BLOCK_OFFSET_TOTAL_TAX]
                    ),
                }
            rows.append(
                {"agi_floor": agi_floor, "agi_ceiling": agi_ceiling, "by_status": by_status}
            )
        return rows

    @staticmethod
    def _filing_status_block_columns(df: pd.DataFrame) -> dict[str, int]:
        """Locate each status block's first column from the sheet's own headings."""
        columns: dict[str, int] = {}
        for row_idx in range(min(8, len(df))):
            for col_idx in range(df.shape[1]):
                cell = str(df.iloc[row_idx, col_idx]).strip()
                for status, heading in _FILING_STATUS_HEADINGS.items():
                    if cell == heading and status not in columns:
                        columns[status] = col_idx
        missing = [status for status in FILING_STATUSES if status not in columns]
        if missing:
            raise ValueError(
                "IRS SOI Table 1.2 header does not carry the expected filing-status "
                f"heading(s): {', '.join(missing)}"
            )
        return {status: columns[status] for status in FILING_STATUSES}

    def _read_table_1_2(self, year: int) -> pd.DataFrame:
        if year in self._status_table_cache:
            return self._status_table_cache[year]

        path = self.data_dir / f"table_1_2_{year}.csv"
        if not path.exists():
            raise FileNotFoundError(
                f"IRS SOI Table 1.2 not found: {path}. "
                "Run `python scripts/build_filing_status_data.py` to rebuild it."
            )

        df = pd.read_csv(path, header=None, dtype=str, na_filter=False)
        self._status_table_cache[year] = df
        return df

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
        # Table 1.1 writes "No adjusted gross income"; Table 1.2 writes the same
        # class as "No adjusted gross income (includes deficits)".
        if label.startswith(self._NO_AGI_LABEL):
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
