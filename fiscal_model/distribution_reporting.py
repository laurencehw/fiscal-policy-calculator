"""
Reporting helpers for distributional analysis.
"""

from typing import Any

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


def distribution_not_representable(policy: Any, dist_analysis: Any) -> bool:
    """True when the engine produced no distributional signal for a policy it
    cannot represent (e.g. OASDI payroll caps, estate provisions).

    Those runs used to render an all-zero table narrated as "roughly flat" /
    "does not significantly affect top income groups" — confidently wrong
    statements. An all-zero output is trusted only for policy families the
    engine explicitly maps; otherwise we say "not available" instead.
    """
    results = list(getattr(dist_analysis, "results", []))
    if not results:
        return True
    if any(abs(float(getattr(r, "tax_change_avg", 0.0) or 0.0)) >= 0.5 for r in results):
        return False
    if abs(float(getattr(dist_analysis, "total_tax_change", 0.0) or 0.0)) >= 0.05:
        return False

    # A non-zero rate change cannot leave every group exactly unchanged unless
    # the population holds nobody above its threshold (e.g. +2pp above $50M on
    # a microdata file whose top record is below that). That is a coverage gap,
    # not a flat result.
    if abs(float(getattr(policy, "rate_change", 0.0) or 0.0)) > 0:
        return True

    # Zero output everywhere: only representable families may claim "flat".
    try:
        from fiscal_model.distribution_effects import policy_to_microsim_reforms

        year = int(getattr(policy, "start_year", 2025) or 2025)
        return not policy_to_microsim_reforms(policy, year=year)
    except Exception:
        return True
