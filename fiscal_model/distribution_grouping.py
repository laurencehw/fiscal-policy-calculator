"""
Grouping helpers for distributional analysis.
"""

import pandas as pd

from .data.irs_soi import TaxBracketData
from .distribution_core import IncomeGroup, IncomeGroupType

TOP_INCOME_BREAKOUT_THRESHOLDS = [
    ("Bottom 80%", 0, 170_000),
    ("80th-90th Percentile", 170_000, 215_000),
    ("90th-95th Percentile", 215_000, 335_000),
    ("95th-99th Percentile", 335_000, 800_000),
    ("Top 1% (excl. 0.1%)", 800_000, 3_500_000),
    ("Top 0.1%", 3_500_000, None),
]


def get_group_thresholds(
    group_type: IncomeGroupType,
    custom_brackets: list[tuple[float, float | None]] | None = None,
) -> list[tuple[str, float, float | None]]:
    """Return threshold definitions for a supported group type."""
    if group_type == IncomeGroupType.QUINTILE:
        return [
            ("Lowest Quintile", 0, 35_000),
            ("Second Quintile", 35_000, 65_000),
            ("Middle Quintile", 65_000, 105_000),
            ("Fourth Quintile", 105_000, 170_000),
            ("Top Quintile", 170_000, None),
        ]
    if group_type == IncomeGroupType.DECILE:
        return [
            ("1st Decile", 0, 15_000),
            ("2nd Decile", 15_000, 28_000),
            ("3rd Decile", 28_000, 42_000),
            ("4th Decile", 42_000, 55_000),
            ("5th Decile", 55_000, 72_000),
            ("6th Decile", 72_000, 92_000),
            ("7th Decile", 92_000, 118_000),
            ("8th Decile", 118_000, 155_000),
            ("9th Decile", 155_000, 220_000),
            ("10th Decile", 220_000, None),
        ]
    if group_type == IncomeGroupType.JCT_DOLLAR:
        return [
            ("Less than $10K", 0, 10_000),
            ("$10K-$20K", 10_000, 20_000),
            ("$20K-$30K", 20_000, 30_000),
            ("$30K-$40K", 30_000, 40_000),
            ("$40K-$50K", 40_000, 50_000),
            ("$50K-$75K", 50_000, 75_000),
            ("$75K-$100K", 75_000, 100_000),
            ("$100K-$200K", 100_000, 200_000),
            ("$200K-$500K", 200_000, 500_000),
            ("$500K-$1M", 500_000, 1_000_000),
            ("$1M and over", 1_000_000, None),
        ]
    if group_type == IncomeGroupType.CUSTOM:
        if custom_brackets is None:
            raise ValueError("custom_brackets required for CUSTOM group type")
        return [
            (
                f"${floor/1e3:.0f}K-${ceiling/1e3:.0f}K" if ceiling else f"${floor/1e3:.0f}K+",
                floor,
                ceiling,
            )
            for floor, ceiling in custom_brackets
        ]
    raise ValueError(f"Unknown group type: {group_type}")


def generate_synthetic_brackets(data_year: int) -> list[TaxBracketData]:
    """Generate synthetic bracket data based on typical IRS distributions."""
    synthetic_data = [
        (1, 5_000, 8.5, 25, 5, 0.3),
        (5_000, 10_000, 10.2, 76, 20, 0.8),
        (10_000, 15_000, 10.8, 135, 45, 2.1),
        (15_000, 20_000, 9.5, 166, 68, 3.8),
        (20_000, 25_000, 8.2, 184, 82, 5.2),
        (25_000, 30_000, 7.3, 201, 96, 7.1),
        (30_000, 40_000, 12.5, 437, 230, 18.5),
        (40_000, 50_000, 10.1, 455, 265, 24.2),
        (50_000, 75_000, 18.2, 1140, 720, 75.0),
        (75_000, 100_000, 12.8, 1100, 750, 90.5),
        (100_000, 200_000, 21.5, 3050, 2200, 310.0),
        (200_000, 500_000, 8.5, 2550, 2000, 380.0),
        (500_000, 1_000_000, 1.8, 1200, 1000, 250.0),
        (1_000_000, 1_500_000, 0.42, 510, 430, 120.0),
        (1_500_000, 2_000_000, 0.18, 310, 270, 78.0),
        (2_000_000, 5_000_000, 0.25, 750, 660, 195.0),
        (5_000_000, 10_000_000, 0.065, 450, 400, 125.0),
        (10_000_000, None, 0.045, 850, 780, 260.0),
    ]

    brackets = []
    for floor, ceiling, returns_m, agi_b, taxable_b, tax_b in synthetic_data:
        brackets.append(
            TaxBracketData(
                year=data_year,
                agi_floor=floor,
                agi_ceiling=ceiling,
                num_returns=int(returns_m * 1e6),
                total_agi=agi_b,
                taxable_income=taxable_b,
                total_tax=tax_b,
            )
        )

    return brackets


def aggregate_brackets_into_groups(
    brackets: list[TaxBracketData],
    thresholds: list[tuple[str, float, float | None]],
    total_returns: int,
) -> list[IncomeGroup]:
    """Aggregate IRS brackets into income groups."""
    groups = []

    for name, floor, ceiling in thresholds:
        group_returns = 0
        group_agi = 0.0
        group_taxable = 0.0
        group_tax = 0.0

        for bracket in brackets:
            bracket_floor = bracket.agi_floor
            bracket_ceiling = bracket.agi_ceiling if bracket.agi_ceiling else float("inf")
            group_ceiling = ceiling if ceiling else float("inf")
            overlap_start = max(bracket_floor, floor)
            overlap_end = min(bracket_ceiling, group_ceiling)

            if overlap_start < overlap_end:
                bracket_width = bracket_ceiling - bracket_floor
                overlap_width = overlap_end - overlap_start
                overlap_fraction = overlap_width / bracket_width if bracket_width > 0 else 1.0

                if overlap_fraction > 0.5 or bracket_floor >= floor:
                    group_returns += bracket.num_returns
                    group_agi += bracket.total_agi
                    group_taxable += bracket.taxable_income
                    group_tax += bracket.total_tax

        groups.append(
            IncomeGroup(
                name=name,
                floor=floor,
                ceiling=ceiling,
                num_returns=group_returns,
                total_agi=group_agi,
                total_taxable_income=group_taxable,
                baseline_tax=group_tax,
                population_share=group_returns / total_returns if total_returns > 0 else 0,
            )
        )

    return groups


def aggregate_top_income_groups(
    brackets: list[TaxBracketData],
    total_returns: int,
) -> list[IncomeGroup]:
    """Create the top-income breakout groups used by the UI and tests."""
    groups = []

    for name, floor, ceiling in TOP_INCOME_BREAKOUT_THRESHOLDS:
        group_returns = 0
        group_agi = 0.0
        group_taxable = 0.0
        group_tax = 0.0

        for bracket in brackets:
            bracket_floor = bracket.agi_floor
            bracket_ceiling = bracket.agi_ceiling if bracket.agi_ceiling else float("inf")
            group_ceiling = ceiling if ceiling else float("inf")

            if bracket_floor >= floor and bracket_floor < group_ceiling:
                if ceiling is None or bracket_ceiling <= group_ceiling:
                    group_returns += bracket.num_returns
                    group_agi += bracket.total_agi
                    group_taxable += bracket.taxable_income
                    group_tax += bracket.total_tax

        groups.append(
            IncomeGroup(
                name=name,
                floor=floor,
                ceiling=ceiling,
                num_returns=group_returns,
                total_agi=group_agi,
                total_taxable_income=group_taxable,
                baseline_tax=group_tax,
                population_share=group_returns / total_returns if total_returns > 0 else 0,
            )
        )

    return groups


def create_groups_from_microdata(
    microdata: pd.DataFrame,
    group_type: IncomeGroupType,
) -> list[IncomeGroup]:
    """Create income groups from microdata by aggregating by AGI."""
    thresholds = get_group_thresholds(group_type)
    groups = []
    weights = microdata.get("weight", pd.Series(1.0, index=microdata.index)).values
    total_weight = weights.sum()

    for name, floor, ceiling in thresholds:
        in_group = (microdata["agi"] >= floor) & (
            (microdata["agi"] < ceiling) if ceiling else (microdata["agi"] >= floor)
        )
        group_data = microdata[in_group]

        if len(group_data) > 0:
            group_weights = group_data.get("weight", pd.Series(1.0, index=group_data.index)).values
            num_returns = int(group_weights.sum())
        else:
            num_returns = 0

        groups.append(
            IncomeGroup(
                name=name,
                floor=floor,
                ceiling=ceiling,
                num_returns=num_returns,
                total_agi=group_data["agi"].sum() / 1e9 if len(group_data) > 0 else 0.0,
                total_taxable_income=group_data["taxable_income"].sum() / 1e9 if len(group_data) > 0 else 0.0,
                baseline_tax=group_data["final_tax"].sum() / 1e9 if len(group_data) > 0 else 0.0,
                population_share=num_returns / total_weight if total_weight > 0 else 0,
            )
        )

    return groups
