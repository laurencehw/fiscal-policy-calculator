"""
Reporting helpers for distributional analysis.
"""

import pandas as pd

from .distribution_core import DistributionalAnalysis


def format_distribution_table(
    analysis: DistributionalAnalysis,
    style: str = "tpc",
) -> pd.DataFrame:
    """Format distributional analysis as a styled table."""
    df = analysis.to_dataframe()

    if style == "tpc":
        cols = [
            "Income Group",
            "Returns (M)",
            "Avg Tax Change ($)",
            "% of Income",
            "Share of Total",
            "% Tax Increase",
            "% Tax Decrease",
            "ETR Change (ppts)",
        ]
    else:
        cols = [
            "Income Group",
            "AGI Range",
            "Returns (M)",
            "Tax Change ($B)",
            "Avg Tax Change ($)",
            "% Tax Increase",
            "% Tax Decrease",
            "Baseline ETR",
            "New ETR",
        ]

    available_cols = [column for column in cols if column in df.columns]
    return df[available_cols]


def generate_winners_losers_summary(analysis: DistributionalAnalysis) -> dict:
    """Generate summary of winners and losers from policy change."""
    total_returns = sum(result.income_group.num_returns for result in analysis.results)
    total_with_increase = 0
    total_with_decrease = 0
    increase_amount = 0.0
    decrease_amount = 0.0

    for result in analysis.results:
        num_returns = result.income_group.num_returns
        total_with_increase += num_returns * result.pct_with_increase / 100
        total_with_decrease += num_returns * result.pct_with_decrease / 100

        if result.tax_change_avg > 0:
            increase_amount += result.tax_change_total
        else:
            decrease_amount += result.tax_change_total

    sorted_by_avg = sorted(analysis.results, key=lambda result: result.tax_change_avg)
    biggest_winners = sorted_by_avg[:3]
    biggest_losers = sorted_by_avg[-3:][::-1]

    return {
        "total_returns": total_returns,
        "pct_with_increase": (total_with_increase / total_returns * 100) if total_returns > 0 else 0,
        "pct_with_decrease": (total_with_decrease / total_returns * 100) if total_returns > 0 else 0,
        "total_increase_billions": increase_amount,
        "total_decrease_billions": decrease_amount,
        "biggest_winners": [
            {"group": result.income_group.name, "avg_change": result.tax_change_avg}
            for result in biggest_winners
            if result.tax_change_avg < 0
        ],
        "biggest_losers": [
            {"group": result.income_group.name, "avg_change": result.tax_change_avg}
            for result in biggest_losers
            if result.tax_change_avg > 0
        ],
    }
