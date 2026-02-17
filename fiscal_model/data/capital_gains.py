"""
Capital gains baseline helper.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd


class CapitalGainsBaseline:
    """
    Build threshold-specific capital gains baselines from bundled aggregate data.
    """

    # Approximate share of total realized gains above AGI threshold.
    # Used as a transparent fallback when detailed IRS-by-AGI capital gains
    # microdistribution is not available in the repository snapshot.
    SHARE_ABOVE_THRESHOLD = [
        (0, 1.00),
        (50_000, 0.92),
        (100_000, 0.85),
        (200_000, 0.72),
        (400_000, 0.58),
        (500_000, 0.52),
        (1_000_000, 0.38),
        (2_000_000, 0.28),
        (5_000_000, 0.17),
        (10_000_000, 0.10),
    ]

    def __init__(self, data_dir: Optional[Path] = None):
        default_dir = Path(__file__).resolve().parent.parent / "data_files" / "capital_gains"
        self.data_dir = Path(data_dir) if data_dir else default_dir
        self._aggregate_df = self._load_aggregate_series()

    def get_baseline_above_threshold_with_rate_method(
        self,
        year: int,
        threshold: float,
        rate_method: str = "statutory_by_agi",
    ) -> dict:
        year_row = self._lookup_year(year)
        threshold = max(0.0, float(threshold))
        share = self._share_above_threshold(threshold)

        total_realized = float(year_row["total_realized_capital_gains_billions"])
        realized_above = total_realized * share

        if rate_method == "taxfoundation_aggregate":
            rate = float(year_row["average_effective_tax_rate"])
            rate_source = "taxfoundation_aggregate"
        else:
            rate = self._statutory_proxy_rate(threshold)
            rate_source = "statutory_by_agi"

        return {
            "tax_year": int(year_row["tax_year"]),
            "threshold": threshold,
            "net_capital_gain_billions": realized_above,
            "average_effective_tax_rate": rate,
            "taxes_paid_on_capital_gains_billions": realized_above * rate,
            "share_of_total_realizations": share,
            "rate_source": rate_source,
        }

    def _load_aggregate_series(self) -> pd.DataFrame:
        path = self.data_dir / "taxfoundation_capital_gains_2022_2024.csv"
        if not path.exists():
            raise FileNotFoundError(f"Capital gains baseline file not found: {path}")
        df = pd.read_csv(path)
        return df.sort_values("tax_year").reset_index(drop=True)

    def _lookup_year(self, year: int) -> pd.Series:
        exact = self._aggregate_df[self._aggregate_df["tax_year"] == year]
        if not exact.empty:
            return exact.iloc[0]

        # Use nearest available year to keep scoring functional.
        idx = (self._aggregate_df["tax_year"] - year).abs().idxmin()
        return self._aggregate_df.loc[idx]

    def _share_above_threshold(self, threshold: float) -> float:
        share = 1.0
        for cutoff, cutoff_share in self.SHARE_ABOVE_THRESHOLD:
            if threshold >= cutoff:
                share = cutoff_share
            else:
                break
        return float(max(0.0, min(1.0, share)))

    @staticmethod
    def _statutory_proxy_rate(threshold: float) -> float:
        """
        Rough bracket-aware LTCG+NIIT effective proxy.
        """
        if threshold >= 1_000_000:
            return 0.238  # 20% LTCG + 3.8% NIIT
        if threshold >= 500_000:
            return 0.232
        if threshold >= 250_000:
            return 0.225
        if threshold >= 200_000:
            return 0.205
        if threshold >= 100_000:
            return 0.185
        return 0.155
