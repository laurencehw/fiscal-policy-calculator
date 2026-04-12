"""
Core types and constants for distributional analysis.
"""

from dataclasses import dataclass, field
from enum import Enum

import pandas as pd

from .policies import Policy


class IncomeGroupType(Enum):
    """Type of income grouping for distributional analysis."""

    QUINTILE = "quintile"
    DECILE = "decile"
    JCT_DOLLAR = "jct_dollar"
    CUSTOM = "custom"


QUINTILE_THRESHOLDS_2024 = {
    "lowest": (0, 35_000),
    "second": (35_000, 65_000),
    "middle": (65_000, 105_000),
    "fourth": (105_000, 170_000),
    "top": (170_000, None),
}


TOP_INCOME_THRESHOLDS_2024 = {
    "top_10": 215_000,
    "top_5": 335_000,
    "top_1": 800_000,
    "top_0_1": 3_500_000,
}


JCT_DOLLAR_BRACKETS = [
    (0, 10_000),
    (10_000, 20_000),
    (20_000, 30_000),
    (30_000, 40_000),
    (40_000, 50_000),
    (50_000, 75_000),
    (75_000, 100_000),
    (100_000, 200_000),
    (200_000, 500_000),
    (500_000, 1_000_000),
    (1_000_000, None),
]


DECILE_THRESHOLDS_2024 = {
    "1st": (0, 15_000),
    "2nd": (15_000, 28_000),
    "3rd": (28_000, 42_000),
    "4th": (42_000, 55_000),
    "5th": (55_000, 72_000),
    "6th": (72_000, 92_000),
    "7th": (92_000, 118_000),
    "8th": (118_000, 155_000),
    "9th": (155_000, 220_000),
    "10th": (220_000, None),
}


@dataclass
class IncomeGroup:
    """Represents one income group in distributional analysis."""

    name: str
    floor: float
    ceiling: float | None
    num_returns: int = 0
    total_agi: float = 0.0
    total_taxable_income: float = 0.0
    baseline_tax: float = 0.0
    population_share: float = 0.0

    @property
    def avg_agi(self) -> float:
        """Average AGI per return in dollars."""
        if self.num_returns == 0:
            return 0.0
        return (self.total_agi * 1e9) / self.num_returns

    @property
    def avg_tax(self) -> float:
        """Average tax per return in dollars."""
        if self.num_returns == 0:
            return 0.0
        return (self.baseline_tax * 1e9) / self.num_returns

    @property
    def effective_tax_rate(self) -> float:
        """Baseline effective tax rate (tax/AGI)."""
        if self.total_agi == 0:
            return 0.0
        return self.baseline_tax / self.total_agi

    def __str__(self) -> str:
        ceiling_str = f"${self.ceiling:,.0f}" if self.ceiling else "+"
        return f"{self.name} (${self.floor:,.0f}-{ceiling_str})"


@dataclass
class DistributionalResult:
    """Result of distributional analysis for one income group."""

    income_group: IncomeGroup
    tax_change_total: float = 0.0
    tax_change_avg: float = 0.0
    tax_change_pct_income: float = 0.0
    share_of_total_change: float = 0.0
    pct_with_increase: float = 0.0
    pct_with_decrease: float = 0.0
    pct_unchanged: float = 100.0
    baseline_etr: float = 0.0
    new_etr: float = 0.0
    etr_change: float = 0.0


@dataclass
class DistributionalAnalysis:
    """Complete distributional analysis of a tax policy."""

    policy: Policy
    year: int
    group_type: IncomeGroupType
    results: list[DistributionalResult] = field(default_factory=list)
    total_tax_change: float = 0.0
    total_affected_returns: int = 0

    def get_winners(self) -> list[DistributionalResult]:
        """Get income groups that receive a net tax cut."""
        return [result for result in self.results if result.tax_change_avg < 0]

    def get_losers(self) -> list[DistributionalResult]:
        """Get income groups that face a net tax increase."""
        return [result for result in self.results if result.tax_change_avg > 0]

    def to_dataframe(self) -> pd.DataFrame:
        """Convert results to a pandas DataFrame for display."""
        rows = []
        for result in self.results:
            rows.append(
                {
                    "Income Group": result.income_group.name,
                    "AGI Range": f"${result.income_group.floor:,.0f}"
                    + (
                        f"-${result.income_group.ceiling:,.0f}"
                        if result.income_group.ceiling
                        else "+"
                    ),
                    "Returns (M)": result.income_group.num_returns / 1e6,
                    "Avg AGI": result.income_group.avg_agi,
                    "Tax Change ($B)": result.tax_change_total,
                    "Avg Tax Change ($)": result.tax_change_avg,
                    "% of Income": result.tax_change_pct_income,
                    "Share of Total": result.share_of_total_change * 100,
                    "% Tax Increase": result.pct_with_increase,
                    "% Tax Decrease": result.pct_with_decrease,
                    "Baseline ETR": result.baseline_etr * 100,
                    "New ETR": result.new_etr * 100,
                    "ETR Change (ppts)": result.etr_change * 100,
                }
            )
        return pd.DataFrame(rows)

    def summary(self) -> str:
        """Generate text summary of distributional effects."""
        lines = [
            f"Distributional Analysis: {self.policy.name}",
            f"Year: {self.year}",
            f"Grouping: {self.group_type.value}",
            f"Total Tax Change: ${self.total_tax_change:.1f}B",
            "",
            "By Income Group:",
            "-" * 80,
        ]

        for result in self.results:
            sign = "+" if result.tax_change_avg > 0 else ""
            lines.append(
                f"  {result.income_group.name:20s}: "
                f"Avg change {sign}${result.tax_change_avg:,.0f} "
                f"({result.share_of_total_change*100:.1f}% of total)"
            )

        return "\n".join(lines)
