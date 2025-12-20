"""
Capital gains baseline data helpers.

Goal:
- Provide a transparent way to auto-populate a capital gains realizations base (R0)
  by AGI threshold for recent years.

Data sources:
- IRS SOI Preliminary Table 1 (Selected Income and Tax Items) for Tax Year 2022:
  https://www.irs.gov/pub/irs-soi/22in01pl.xls
  This contains "Net capital gain" by AGI size, which we treat as a proxy for taxable realizations.
- Tax Foundation historical capital gains collections/realizations (aggregate, not by AGI):
  https://taxfoundation.org/data/all/federal/federal-capital-gains-tax-collections-historical-data/
  We use this series to scale 2022 AGI shares to approximate 2023/2024 totals when IRS-by-AGI
  tables are not yet published.

Notes:
- This is an approximation for 2023/2024: we assume the *distribution* of net capital gains by AGI
  is similar to 2022, and scale totals to match aggregate realized gains.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd


_ROOT = Path(__file__).parent.parent
_DATA_DIR = _ROOT / "data_files" / "capital_gains"


@dataclass(frozen=True)
class AGIBracketGains:
    year: int
    agi_floor: float
    agi_ceiling: Optional[float]
    net_capital_gain_billions: float


class CapitalGainsBaseline:
    """
    Loader/estimator for net capital gains by AGI bracket.
    """

    def __init__(self, data_dir: Optional[str | Path] = None):
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR

    def _irs_2022_table1_path(self) -> Path:
        return self.data_dir / "irs_22in01pl.xls"

    def _taxfoundation_path(self) -> Path:
        return self.data_dir / "taxfoundation_capital_gains_2022_2024.csv"

    @staticmethod
    def _parse_agi_range(label: str) -> tuple[float, Optional[float]]:
        """
        Parse AGI range labels from IRS preliminary table columns.

        Examples:
        - "Under $15,000 [1]" -> (0, 15000)
        - "$15,000 under $30,000" -> (15000, 30000)
        - "$250,000 or more" -> (250000, None)
        """
        import re

        text = " ".join(str(label).replace("\n", " ").split()).strip()
        text = text.replace("[1]", "").replace("[2]", "").replace("[3]", "").strip()
        lower = text.lower()

        nums = re.findall(r"\$([\d,]+)", text)
        vals = [int(x.replace(",", "")) for x in nums]

        if lower.startswith("under") and vals:
            return (0.0, float(vals[0]))
        if "under" in lower and len(vals) >= 2:
            return (float(vals[0]), float(vals[1]))
        if "or more" in lower and vals:
            return (float(vals[0]), None)

        raise ValueError(f"Could not parse AGI range label: {label!r}")

    def _load_irs_2022_net_capital_gain_by_bracket(self) -> list[AGIBracketGains]:
        """
        Extract the Tax Year 2022 net capital gain row by AGI bracket.

        Source: https://www.irs.gov/pub/irs-soi/22in01pl.xls
        """
        path = self._irs_2022_table1_path()
        if not path.exists():
            raise FileNotFoundError(
                f"Missing IRS preliminary 2022 Table 1 file at {path}. "
                f"See {self.data_dir / 'README.md'} for download instructions."
            )

        df = pd.read_excel(path, sheet_name=0, header=None)

        # Header row: AGI bracket labels are on row 4 (0-indexed) in this workbook.
        header_row_idx = 4
        # Data columns for 2022-by-AGI begin at column 4 (0-indexed) and run through 10.
        agi_cols = list(range(4, 11))

        labels = [df.iat[header_row_idx, c] for c in agi_cols]
        ranges = [self._parse_agi_range(l) for l in labels]

        # Net capital gain section: "Amount" row is at index 35 (0-indexed) in this workbook.
        # Values are in thousands of dollars.
        amount_row_idx = 35
        amounts_thousands = [df.iat[amount_row_idx, c] for c in agi_cols]

        def to_float(x) -> float:
            if pd.isna(x):
                return 0.0
            return float(x)

        amounts_billions = [to_float(x) / 1e6 for x in amounts_thousands]  # thousands -> billions

        out: list[AGIBracketGains] = []
        for (floor, ceil), amt_b in zip(ranges, amounts_billions, strict=True):
            out.append(
                AGIBracketGains(
                    year=2022,
                    agi_floor=floor,
                    agi_ceiling=ceil,
                    net_capital_gain_billions=amt_b,
                )
            )
        return out

    def _load_taxfoundation_totals(self) -> pd.DataFrame:
        """
        Load aggregate realized gains + taxes paid + average effective rate.

        Source: https://taxfoundation.org/data/all/federal/federal-capital-gains-tax-collections-historical-data/
        """
        path = self._taxfoundation_path()
        if not path.exists():
            raise FileNotFoundError(
                f"Missing Tax Foundation series at {path}. "
                f"See {self.data_dir / 'README.md'} for download instructions."
            )

        df = pd.read_csv(path)
        required = {
            "tax_year",
            "total_realized_capital_gains_billions",
            "taxes_paid_on_capital_gains_billions",
            "average_effective_tax_rate",
        }
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Tax Foundation CSV missing columns: {sorted(missing)}")
        return df

    def get_years_available(self) -> list[int]:
        years = []
        if self._irs_2022_table1_path().exists():
            years.append(2022)
        # We can estimate 2023/2024 from Tax Foundation totals if present.
        if self._taxfoundation_path().exists():
            tf = self._load_taxfoundation_totals()
            for y in sorted(tf["tax_year"].unique()):
                if int(y) in (2023, 2024):
                    years.append(int(y))
        return sorted(set(years))

    def get_net_capital_gain_by_bracket(self, year: int) -> list[AGIBracketGains]:
        """
        Return net capital gains by AGI bracket.

        - 2022: uses IRS preliminary AGI breakdown.
        - 2023/2024: scales 2022 bracket shares to match aggregate realized gains totals (approximation).
        """
        if year == 2022:
            return self._load_irs_2022_net_capital_gain_by_bracket()

        if year in (2023, 2024):
            base = self._load_irs_2022_net_capital_gain_by_bracket()
            tf = self._load_taxfoundation_totals().set_index("tax_year")
            if 2022 not in tf.index or year not in tf.index:
                raise ValueError("Tax Foundation totals must include both 2022 and target year for scaling.")

            # Scale by aggregate realized gains ratio (proxy for net gains growth).
            ratio = float(tf.loc[year, "total_realized_capital_gains_billions"]) / float(
                tf.loc[2022, "total_realized_capital_gains_billions"]
            )
            return [
                AGIBracketGains(
                    year=year,
                    agi_floor=b.agi_floor,
                    agi_ceiling=b.agi_ceiling,
                    net_capital_gain_billions=b.net_capital_gain_billions * ratio,
                )
                for b in base
            ]

        raise ValueError(f"Unsupported year for capital gains baseline: {year}")

    def get_baseline_above_threshold(self, year: int, threshold: float) -> dict:
        """
        Compute baseline net capital gains above an AGI threshold and an effective rate proxy.

        Returns:
        - net_capital_gain_billions: sum of bracket amounts with floor >= threshold
        - average_effective_tax_rate: effective tax rate proxy for the group (see rate_method)

        Note: If threshold falls inside a bracket, we include the whole bracket (conservative, documented).
        """
        return self.get_baseline_above_threshold_with_rate_method(
            year=year,
            threshold=threshold,
            rate_method="statutory_by_agi",
        )

    def get_baseline_above_threshold_with_rate_method(
        self,
        *,
        year: int,
        threshold: float,
        rate_method: str = "statutory_by_agi",
    ) -> dict:
        """
        Like get_baseline_above_threshold, but allows selecting how τ0 is estimated.

        rate_method:
        - "taxfoundation_avg": use Tax Foundation year-level avg effective rate (not by AGI)
        - "statutory_by_agi": compute a weighted effective rate using AGI brackets + a statutory/NIIT proxy
        """
        brackets = self.get_net_capital_gain_by_bracket(year)
        above = [b for b in brackets if b.agi_floor >= threshold]
        if not above:
            raise ValueError(f"No brackets found above threshold ${threshold:,.0f} for year {year}")

        net_gain = sum(b.net_capital_gain_billions for b in above)

        def statutory_rate_proxy(agi_floor: float, agi_ceiling: Optional[float]) -> float:
            """
            Simple statutory proxy for (LTCG rate + NIIT) using AGI bracket bounds.

            Caveat: ignores filing status and short-term gains; intended as a transparent proxy.
            """
            # Rough LTCG bands (single-ish) — enough for high-income thresholds.
            # 0% below ~50k, 15% mid, 20% high.
            # NIIT applies above ~$200k.
            ceiling = agi_ceiling if agi_ceiling is not None else float("inf")
            if ceiling <= 50_000:
                base = 0.00
            elif ceiling <= 500_000:
                base = 0.15
            else:
                base = 0.20

            niit = 0.038 if agi_floor >= 200_000 else 0.0
            return base + niit

        tf = None
        tau0: float
        if rate_method == "taxfoundation_avg":
            tf = self._load_taxfoundation_totals().set_index("tax_year")
            if year in tf.index:
                tau0 = float(tf.loc[year, "average_effective_tax_rate"])
            else:
                tau0 = 0.20
        elif rate_method == "statutory_by_agi":
            # Weight bracket-level proxy rates by bracket net gains.
            denom = sum(max(0.0, b.net_capital_gain_billions) for b in above)
            if denom <= 0:
                tau0 = 0.20
            else:
                tau0 = sum(
                    max(0.0, b.net_capital_gain_billions) * statutory_rate_proxy(b.agi_floor, b.agi_ceiling)
                    for b in above
                ) / denom
        else:
            raise ValueError(f"Unknown rate_method: {rate_method}")

        return {
            "year": year,
            "threshold": threshold,
            "net_capital_gain_billions": float(net_gain),
            "average_effective_tax_rate": float(tau0),
            "rate_method": rate_method,
        }


