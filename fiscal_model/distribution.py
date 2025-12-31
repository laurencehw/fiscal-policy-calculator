"""
Distributional Analysis Module

Analyzes how tax policy changes affect different income groups using
Tax Policy Center (TPC) and Joint Committee on Taxation (JCT) methodology.

Key features:
- Income quintile/decile analysis
- Dollar-based income brackets (JCT style)
- Average tax change by income group
- Percent with tax increase/decrease (winners/losers)
- Share of total tax change by group
- Effective tax rate changes
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from .data.irs_soi import IRSSOIData, TaxBracketData
from .policies import TaxPolicy, Policy


class IncomeGroupType(Enum):
    """Type of income grouping for distributional analysis."""
    QUINTILE = "quintile"           # 5 equal-population groups
    DECILE = "decile"               # 10 equal-population groups
    JCT_DOLLAR = "jct_dollar"       # JCT-style dollar brackets
    CUSTOM = "custom"               # User-defined brackets


# =============================================================================
# INCOME GROUP DEFINITIONS
# =============================================================================

# 2024/2025 Income Quintile Thresholds (based on TPC/Census data)
# These are approximate AGI thresholds for population quintiles
QUINTILE_THRESHOLDS_2024 = {
    "lowest": (0, 35_000),           # Bottom 20%
    "second": (35_000, 65_000),      # 20-40%
    "middle": (65_000, 105_000),     # 40-60%
    "fourth": (105_000, 170_000),    # 60-80%
    "top": (170_000, None),          # Top 20%
}

# Top income group breakouts
TOP_INCOME_THRESHOLDS_2024 = {
    "top_10": 215_000,     # Top 10%
    "top_5": 335_000,      # Top 5%
    "top_1": 800_000,      # Top 1%
    "top_0_1": 3_500_000,  # Top 0.1%
}

# JCT-style dollar brackets
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
    (1_000_000, None),  # $1M+
]

# Decile thresholds (2024 estimates)
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
    """
    Represents one income group in distributional analysis.

    Attributes:
        name: Human-readable name (e.g., "Middle Quintile", "$50K-$75K")
        floor: Lower bound of income (dollars)
        ceiling: Upper bound of income (None for top bracket)
        num_returns: Number of tax returns in this group
        total_agi: Total AGI in group (billions)
        total_taxable_income: Total taxable income (billions)
        baseline_tax: Baseline tax liability (billions)
        population_share: Share of total tax filers (0-1)
    """
    name: str
    floor: float
    ceiling: Optional[float]
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
    """
    Result of distributional analysis for one income group.

    Attributes:
        income_group: The income group analyzed
        tax_change_total: Total tax change for this group (billions)
        tax_change_avg: Average tax change per return (dollars)
        tax_change_pct_income: Tax change as % of after-tax income
        share_of_total_change: This group's share of total tax change (0-1)
        pct_with_increase: Percent of filers with tax increase (0-100)
        pct_with_decrease: Percent of filers with tax decrease (0-100)
        pct_unchanged: Percent of filers with no change (0-100)
        baseline_etr: Baseline effective tax rate (0-1)
        new_etr: New effective tax rate after policy (0-1)
        etr_change: Change in effective tax rate (ppts)
    """
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
    """
    Complete distributional analysis of a tax policy.

    Attributes:
        policy: The policy being analyzed
        year: Analysis year
        group_type: Type of income grouping used
        results: List of DistributionalResult for each income group
        total_tax_change: Total tax change across all groups (billions)
        total_affected_returns: Number of returns affected
    """
    policy: Policy
    year: int
    group_type: IncomeGroupType
    results: List[DistributionalResult] = field(default_factory=list)
    total_tax_change: float = 0.0
    total_affected_returns: int = 0

    def get_winners(self) -> List[DistributionalResult]:
        """Get income groups that receive a net tax cut."""
        return [r for r in self.results if r.tax_change_avg < 0]

    def get_losers(self) -> List[DistributionalResult]:
        """Get income groups that face a net tax increase."""
        return [r for r in self.results if r.tax_change_avg > 0]

    def to_dataframe(self) -> pd.DataFrame:
        """Convert results to a pandas DataFrame for display."""
        rows = []
        for r in self.results:
            rows.append({
                "Income Group": r.income_group.name,
                "AGI Range": f"${r.income_group.floor:,.0f}" +
                            (f"-${r.income_group.ceiling:,.0f}" if r.income_group.ceiling else "+"),
                "Returns (M)": r.income_group.num_returns / 1e6,
                "Avg AGI": r.income_group.avg_agi,
                "Tax Change ($B)": r.tax_change_total,
                "Avg Tax Change ($)": r.tax_change_avg,
                "% of Income": r.tax_change_pct_income,
                "Share of Total": r.share_of_total_change * 100,
                "% Tax Increase": r.pct_with_increase,
                "% Tax Decrease": r.pct_with_decrease,
                "Baseline ETR": r.baseline_etr * 100,
                "New ETR": r.new_etr * 100,
                "ETR Change (ppts)": r.etr_change * 100,
            })
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

        for r in self.results:
            sign = "+" if r.tax_change_avg > 0 else ""
            lines.append(
                f"  {r.income_group.name:20s}: "
                f"Avg change {sign}${r.tax_change_avg:,.0f} "
                f"({r.share_of_total_change*100:.1f}% of total)"
            )

        return "\n".join(lines)


# =============================================================================
# DISTRIBUTIONAL ENGINE
# =============================================================================

class DistributionalEngine:
    """
    Engine for computing distributional effects of tax policies.

    Uses IRS Statistics of Income data to calculate how tax changes
    affect different income groups.
    """

    def __init__(self, data_year: int = 2022):
        """
        Initialize the distributional engine.

        Args:
            data_year: Year of IRS SOI data to use
        """
        self.data_year = data_year
        self._irs_data = None
        self._brackets = None
        self._total_returns = None

    @property
    def irs_data(self) -> IRSSOIData:
        """Lazy load IRS data."""
        if self._irs_data is None:
            self._irs_data = IRSSOIData()
        return self._irs_data

    @property
    def brackets(self) -> List[TaxBracketData]:
        """Lazy load bracket data."""
        if self._brackets is None:
            try:
                self._brackets = self.irs_data.get_bracket_distribution(self.data_year)
            except FileNotFoundError:
                # Use synthetic data if IRS files not available
                self._brackets = self._generate_synthetic_brackets()
        return self._brackets

    @property
    def total_returns(self) -> int:
        """Total number of tax returns."""
        if self._total_returns is None:
            self._total_returns = sum(b.num_returns for b in self.brackets)
        return self._total_returns

    def _generate_synthetic_brackets(self) -> List[TaxBracketData]:
        """
        Generate synthetic bracket data based on typical distributions.

        Used when actual IRS SOI data files are not available.
        Based on 2022 IRS statistics.
        """
        # Typical bracket distribution based on IRS 2022 data
        synthetic_data = [
            # (floor, ceiling, returns_M, agi_B, taxable_B, tax_B)
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
            brackets.append(TaxBracketData(
                year=self.data_year,
                agi_floor=floor,
                agi_ceiling=ceiling,
                num_returns=int(returns_m * 1e6),
                total_agi=agi_b,
                taxable_income=taxable_b,
                total_tax=tax_b,
            ))

        return brackets

    def create_income_groups(
        self,
        group_type: IncomeGroupType = IncomeGroupType.QUINTILE,
        custom_brackets: Optional[List[Tuple[float, Optional[float]]]] = None,
    ) -> List[IncomeGroup]:
        """
        Create income groups by aggregating IRS brackets.

        Args:
            group_type: Type of income grouping
            custom_brackets: Custom bracket definitions if group_type is CUSTOM

        Returns:
            List of IncomeGroup objects with aggregated statistics
        """
        # Define bracket boundaries based on group type
        if group_type == IncomeGroupType.QUINTILE:
            thresholds = [
                ("Lowest Quintile", 0, 35_000),
                ("Second Quintile", 35_000, 65_000),
                ("Middle Quintile", 65_000, 105_000),
                ("Fourth Quintile", 105_000, 170_000),
                ("Top Quintile", 170_000, None),
            ]
        elif group_type == IncomeGroupType.DECILE:
            thresholds = [
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
        elif group_type == IncomeGroupType.JCT_DOLLAR:
            thresholds = [
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
        elif group_type == IncomeGroupType.CUSTOM:
            if custom_brackets is None:
                raise ValueError("custom_brackets required for CUSTOM group type")
            thresholds = [
                (f"${floor/1e3:.0f}K-${ceiling/1e3:.0f}K" if ceiling else f"${floor/1e3:.0f}K+",
                 floor, ceiling)
                for floor, ceiling in custom_brackets
            ]
        else:
            raise ValueError(f"Unknown group type: {group_type}")

        # Aggregate IRS brackets into income groups
        groups = []
        total_returns = self.total_returns

        for name, floor, ceiling in thresholds:
            # Find all IRS brackets that overlap with this income group
            group_returns = 0
            group_agi = 0.0
            group_taxable = 0.0
            group_tax = 0.0

            for bracket in self.brackets:
                # Check if bracket overlaps with this group
                bracket_floor = bracket.agi_floor
                bracket_ceiling = bracket.agi_ceiling if bracket.agi_ceiling else float('inf')
                group_ceiling = ceiling if ceiling else float('inf')

                # Calculate overlap fraction
                overlap_start = max(bracket_floor, floor)
                overlap_end = min(bracket_ceiling, group_ceiling)

                if overlap_start < overlap_end:
                    # There is overlap
                    bracket_width = bracket_ceiling - bracket_floor
                    overlap_width = overlap_end - overlap_start

                    if bracket_width > 0:
                        overlap_fraction = overlap_width / bracket_width
                    else:
                        overlap_fraction = 1.0

                    # For simplicity, use full bracket if >50% overlap
                    # This avoids complex income distribution assumptions
                    if overlap_fraction > 0.5 or bracket_floor >= floor:
                        group_returns += bracket.num_returns
                        group_agi += bracket.total_agi
                        group_taxable += bracket.taxable_income
                        group_tax += bracket.total_tax

            groups.append(IncomeGroup(
                name=name,
                floor=floor,
                ceiling=ceiling,
                num_returns=group_returns,
                total_agi=group_agi,
                total_taxable_income=group_taxable,
                baseline_tax=group_tax,
                population_share=group_returns / total_returns if total_returns > 0 else 0,
            ))

        return groups

    def analyze_policy(
        self,
        policy: TaxPolicy,
        group_type: IncomeGroupType = IncomeGroupType.QUINTILE,
        year: Optional[int] = None,
    ) -> DistributionalAnalysis:
        """
        Analyze distributional effects of a tax policy.

        Args:
            policy: Tax policy to analyze
            group_type: Type of income grouping
            year: Analysis year (defaults to policy start year)

        Returns:
            DistributionalAnalysis with results for each income group
        """
        if year is None:
            year = getattr(policy, 'start_year', 2025)

        # Create income groups
        groups = self.create_income_groups(group_type)

        # Calculate tax change for each group
        results = []
        total_tax_change = 0.0
        total_affected = 0

        for group in groups:
            result = self._calculate_group_effect(policy, group)
            results.append(result)
            total_tax_change += result.tax_change_total
            if result.pct_with_increase > 0 or result.pct_with_decrease > 0:
                total_affected += group.num_returns

        # Calculate share of total change for each group
        if abs(total_tax_change) > 0.001:  # Avoid division by zero
            for result in results:
                result.share_of_total_change = result.tax_change_total / total_tax_change

        return DistributionalAnalysis(
            policy=policy,
            year=year,
            group_type=group_type,
            results=results,
            total_tax_change=total_tax_change,
            total_affected_returns=total_affected,
        )

    def _calculate_group_effect(
        self,
        policy: TaxPolicy,
        group: IncomeGroup,
    ) -> DistributionalResult:
        """
        Calculate tax change effect for one income group.

        This uses the policy's rate change and threshold to determine
        how much of the group is affected and the magnitude of change.
        """
        # Get policy parameters
        rate_change = getattr(policy, 'rate_change', 0.0)
        threshold = getattr(policy, 'affected_income_threshold', 0)

        # Determine what fraction of this group is affected
        # If policy threshold is below group floor, entire group affected
        # If threshold is above group ceiling, no one affected
        # If in between, partial effect

        group_ceiling = group.ceiling if group.ceiling else float('inf')

        if threshold >= group_ceiling:
            # No one in this group is affected
            affected_fraction = 0.0
        elif threshold <= group.floor:
            # Everyone in this group is affected
            affected_fraction = 1.0
        elif group.ceiling is None:
            # Top bracket (no ceiling) - need to estimate fraction above threshold
            # Use average AGI to estimate what fraction is above threshold
            if group.avg_agi > threshold:
                # Most of this group is above threshold
                affected_fraction = min(1.0, (group.avg_agi - threshold) / group.avg_agi + 0.5)
            else:
                # Threshold is above average - fewer affected
                affected_fraction = max(0.0, 0.5 - (threshold - group.avg_agi) / group.avg_agi)
            affected_fraction = max(0.0, min(1.0, affected_fraction))  # Clamp to [0, 1]
        else:
            # Partial effect - estimate fraction above threshold
            # Use simple linear approximation within the group
            group_width = group_ceiling - group.floor
            affected_width = group_ceiling - threshold
            affected_fraction = affected_width / group_width if group_width > 0 else 0

        # Calculate tax change
        affected_taxable = group.total_taxable_income * affected_fraction
        tax_change_total = rate_change * affected_taxable  # In billions

        # Calculate per-return metrics
        affected_returns = int(group.num_returns * affected_fraction)
        if affected_returns > 0:
            tax_change_avg = (tax_change_total * 1e9) / affected_returns
        else:
            tax_change_avg = 0.0

        # Calculate as percent of income (after-tax)
        after_tax_income = group.total_agi - group.baseline_tax
        if after_tax_income > 0:
            tax_change_pct_income = (tax_change_total / after_tax_income) * 100
        else:
            tax_change_pct_income = 0.0

        # Effective tax rates
        baseline_etr = group.effective_tax_rate
        new_tax = group.baseline_tax + tax_change_total
        new_etr = new_tax / group.total_agi if group.total_agi > 0 else 0

        # Winners/losers (simplified - assumes all affected move same direction)
        if rate_change > 0:  # Tax increase
            pct_with_increase = affected_fraction * 100
            pct_with_decrease = 0.0
        elif rate_change < 0:  # Tax cut
            pct_with_increase = 0.0
            pct_with_decrease = affected_fraction * 100
        else:
            pct_with_increase = 0.0
            pct_with_decrease = 0.0

        pct_unchanged = 100 - pct_with_increase - pct_with_decrease

        return DistributionalResult(
            income_group=group,
            tax_change_total=tax_change_total,
            tax_change_avg=tax_change_avg,
            tax_change_pct_income=tax_change_pct_income,
            share_of_total_change=0.0,  # Calculated later
            pct_with_increase=pct_with_increase,
            pct_with_decrease=pct_with_decrease,
            pct_unchanged=pct_unchanged,
            baseline_etr=baseline_etr,
            new_etr=new_etr,
            etr_change=new_etr - baseline_etr,
        )

    def create_top_income_breakout(
        self,
        policy: TaxPolicy,
        year: Optional[int] = None,
    ) -> DistributionalAnalysis:
        """
        Create detailed breakout for top income groups.

        Includes Top 20%, Top 10%, Top 5%, Top 1%, Top 0.1%.
        """
        custom_brackets = [
            (0, 170_000),           # Bottom 80%
            (170_000, 215_000),     # 80-90%
            (215_000, 335_000),     # 90-95%
            (335_000, 800_000),     # 95-99%
            (800_000, 3_500_000),   # 99-99.9%
            (3_500_000, None),      # Top 0.1%
        ]

        thresholds = [
            ("Bottom 80%", 0, 170_000),
            ("80th-90th Percentile", 170_000, 215_000),
            ("90th-95th Percentile", 215_000, 335_000),
            ("95th-99th Percentile", 335_000, 800_000),
            ("Top 1% (excl. 0.1%)", 800_000, 3_500_000),
            ("Top 0.1%", 3_500_000, None),
        ]

        # Create custom groups
        groups = []
        for name, floor, ceiling in thresholds:
            group_returns = 0
            group_agi = 0.0
            group_taxable = 0.0
            group_tax = 0.0

            for bracket in self.brackets:
                bracket_floor = bracket.agi_floor
                bracket_ceiling = bracket.agi_ceiling if bracket.agi_ceiling else float('inf')
                group_ceiling = ceiling if ceiling else float('inf')

                if bracket_floor >= floor and bracket_floor < group_ceiling:
                    if ceiling is None or bracket_ceiling <= group_ceiling:
                        group_returns += bracket.num_returns
                        group_agi += bracket.total_agi
                        group_taxable += bracket.taxable_income
                        group_tax += bracket.total_tax

            groups.append(IncomeGroup(
                name=name,
                floor=floor,
                ceiling=ceiling,
                num_returns=group_returns,
                total_agi=group_agi,
                total_taxable_income=group_taxable,
                baseline_tax=group_tax,
                population_share=group_returns / self.total_returns if self.total_returns > 0 else 0,
            ))

        # Analyze policy for these groups
        if year is None:
            year = getattr(policy, 'start_year', 2025)

        results = []
        total_tax_change = 0.0

        for group in groups:
            result = self._calculate_group_effect(policy, group)
            results.append(result)
            total_tax_change += result.tax_change_total

        # Calculate share of total change
        if abs(total_tax_change) > 0.001:
            for result in results:
                result.share_of_total_change = result.tax_change_total / total_tax_change

        return DistributionalAnalysis(
            policy=policy,
            year=year,
            group_type=IncomeGroupType.CUSTOM,
            results=results,
            total_tax_change=total_tax_change,
            total_affected_returns=sum(g.num_returns for g in groups),
        )


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def format_distribution_table(
    analysis: DistributionalAnalysis,
    style: str = "tpc",
) -> pd.DataFrame:
    """
    Format distributional analysis as a styled table.

    Args:
        analysis: DistributionalAnalysis to format
        style: "tpc" for Tax Policy Center style, "jct" for JCT style

    Returns:
        Formatted DataFrame
    """
    df = analysis.to_dataframe()

    if style == "tpc":
        # TPC style: focus on tax change as % of income
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
    else:  # JCT style
        # JCT style: focus on dollar amounts
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

    # Select available columns
    available_cols = [c for c in cols if c in df.columns]
    return df[available_cols]


def generate_winners_losers_summary(analysis: DistributionalAnalysis) -> Dict:
    """
    Generate summary of winners and losers from policy change.

    Returns:
        Dictionary with winner/loser statistics
    """
    total_returns = sum(r.income_group.num_returns for r in analysis.results)

    # Calculate weighted averages
    total_with_increase = 0
    total_with_decrease = 0
    increase_amount = 0.0
    decrease_amount = 0.0

    for r in analysis.results:
        n = r.income_group.num_returns
        total_with_increase += n * r.pct_with_increase / 100
        total_with_decrease += n * r.pct_with_decrease / 100

        if r.tax_change_avg > 0:
            increase_amount += r.tax_change_total
        else:
            decrease_amount += r.tax_change_total

    # Find which groups benefit/lose most
    sorted_by_avg = sorted(analysis.results, key=lambda r: r.tax_change_avg)
    biggest_winners = sorted_by_avg[:3]  # Largest tax cuts
    biggest_losers = sorted_by_avg[-3:][::-1]  # Largest tax increases

    return {
        "total_returns": total_returns,
        "pct_with_increase": (total_with_increase / total_returns * 100) if total_returns > 0 else 0,
        "pct_with_decrease": (total_with_decrease / total_returns * 100) if total_returns > 0 else 0,
        "total_increase_billions": increase_amount,
        "total_decrease_billions": decrease_amount,
        "biggest_winners": [
            {"group": r.income_group.name, "avg_change": r.tax_change_avg}
            for r in biggest_winners if r.tax_change_avg < 0
        ],
        "biggest_losers": [
            {"group": r.income_group.name, "avg_change": r.tax_change_avg}
            for r in biggest_losers if r.tax_change_avg > 0
        ],
    }


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    # Enums
    "IncomeGroupType",
    # Data classes
    "IncomeGroup",
    "DistributionalResult",
    "DistributionalAnalysis",
    # Engine
    "DistributionalEngine",
    # Constants
    "QUINTILE_THRESHOLDS_2024",
    "DECILE_THRESHOLDS_2024",
    "TOP_INCOME_THRESHOLDS_2024",
    "JCT_DOLLAR_BRACKETS",
    # Helper functions
    "format_distribution_table",
    "generate_winners_losers_summary",
]
