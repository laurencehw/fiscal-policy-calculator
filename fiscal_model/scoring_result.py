"""
Scoring result model and presentation helpers.
"""

from dataclasses import dataclass, field

import numpy as np

from .baseline import BaselineProjection
from .economics import DynamicEffects
from .policies import Policy


@dataclass
class ScoringResult:
    """
    Complete scoring results for a fiscal policy.
    """

    policy: Policy
    baseline: BaselineProjection
    years: np.ndarray
    static_revenue_effect: np.ndarray
    static_spending_effect: np.ndarray
    static_deficit_effect: np.ndarray
    behavioral_offset: np.ndarray
    dynamic_effects: DynamicEffects | None = None
    final_deficit_effect: np.ndarray = field(default_factory=lambda: np.zeros(10))
    low_estimate: np.ndarray = field(default_factory=lambda: np.zeros(10))
    high_estimate: np.ndarray = field(default_factory=lambda: np.zeros(10))

    @property
    def is_dynamic(self) -> bool:
        """Whether dynamic scoring was applied."""
        return self.dynamic_effects is not None

    @property
    def total_10_year_cost(self) -> float:
        """Total 10-year cost (positive = increases deficit)."""
        return np.sum(self.final_deficit_effect)

    @property
    def total_static_cost(self) -> float:
        """Total 10-year static cost."""
        return np.sum(self.static_deficit_effect)

    @property
    def revenue_feedback_10yr(self) -> float:
        """Total revenue feedback from economic effects."""
        if self.dynamic_effects:
            return np.sum(self.dynamic_effects.revenue_feedback)
        return 0.0

    @property
    def average_annual_cost(self) -> float:
        """Average annual cost."""
        return self.total_10_year_cost / len(self.years)

    def get_year_effect(self, year: int) -> dict:
        """Get detailed effects for a specific year."""
        idx = year - self.years[0]
        result = {
            "year": year,
            "static_revenue": self.static_revenue_effect[idx],
            "static_spending": self.static_spending_effect[idx],
            "static_deficit": self.static_deficit_effect[idx],
            "behavioral_offset": self.behavioral_offset[idx],
            "final_deficit": self.final_deficit_effect[idx],
            "low_estimate": self.low_estimate[idx],
            "high_estimate": self.high_estimate[idx],
        }

        if self.dynamic_effects:
            result.update(
                {
                    "gdp_effect": self.dynamic_effects.gdp_level_change[idx],
                    "gdp_pct": self.dynamic_effects.gdp_percent_change[idx],
                    "employment": self.dynamic_effects.employment_change[idx],
                    "revenue_feedback": self.dynamic_effects.revenue_feedback[idx],
                }
            )

        return result

    def to_dataframe(self):
        """Convert results to pandas DataFrame."""
        import pandas as pd

        data = {
            "Year": self.years,
            "Static Revenue Effect ($B)": self.static_revenue_effect,
            "Static Spending Effect ($B)": self.static_spending_effect,
            "Static Deficit Effect ($B)": self.static_deficit_effect,
            "Behavioral Offset ($B)": self.behavioral_offset,
            "Final Deficit Effect ($B)": self.final_deficit_effect,
            "Low Estimate ($B)": self.low_estimate,
            "High Estimate ($B)": self.high_estimate,
        }

        if self.dynamic_effects:
            data.update(
                {
                    "GDP Effect ($B)": self.dynamic_effects.gdp_level_change,
                    "GDP Effect (%)": self.dynamic_effects.gdp_percent_change,
                    "Employment (thousands)": self.dynamic_effects.employment_change,
                    "Revenue Feedback ($B)": self.dynamic_effects.revenue_feedback,
                }
            )

        return pd.DataFrame(data)

    def display_summary(self):
        """Print a formatted summary of results."""
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table

        console = Console()
        console.print(
            Panel(
                f"[bold blue]{self.policy.name}[/bold blue]\n{self.policy.description}",
                title="Fiscal Policy Score",
            )
        )

        console.print("\n[bold]10-Year Budget Impact:[/bold]")
        console.print(f"  Static Cost: ${self.total_static_cost:,.1f} billion")
        if self.is_dynamic:
            console.print(f"  Revenue Feedback: ${self.revenue_feedback_10yr:,.1f} billion")
        console.print(f"  [bold]Final Cost: ${self.total_10_year_cost:,.1f} billion[/bold]")
        console.print(
            f"  Range: ${np.sum(self.low_estimate):,.1f}B to ${np.sum(self.high_estimate):,.1f}B"
        )

        table = Table(title="\nYear-by-Year Effects ($ billions)")
        table.add_column("Year", style="cyan")
        table.add_column("Static", justify="right")
        table.add_column("Behavioral", justify="right")
        if self.is_dynamic:
            table.add_column("Feedback", justify="right")
        table.add_column("Final", justify="right", style="bold")
        table.add_column("Range", justify="right")

        for idx, year in enumerate(self.years):
            row = [
                str(year),
                f"{self.static_deficit_effect[idx]:,.1f}",
                f"{self.behavioral_offset[idx]:,.1f}",
            ]
            if self.is_dynamic:
                row.append(f"{self.dynamic_effects.revenue_feedback[idx]:,.1f}")
            row.extend(
                [
                    f"{self.final_deficit_effect[idx]:,.1f}",
                    f"{self.low_estimate[idx]:,.1f} to {self.high_estimate[idx]:,.1f}",
                ]
            )
            table.add_row(*row)

        total_row = [
            "[bold]Total[/bold]",
            f"[bold]{self.total_static_cost:,.1f}[/bold]",
            f"[bold]{np.sum(self.behavioral_offset):,.1f}[/bold]",
        ]
        if self.is_dynamic:
            total_row.append(f"[bold]{self.revenue_feedback_10yr:,.1f}[/bold]")
        total_row.extend(
            [
                f"[bold]{self.total_10_year_cost:,.1f}[/bold]",
                f"[bold]{np.sum(self.low_estimate):,.1f} to {np.sum(self.high_estimate):,.1f}[/bold]",
            ]
        )
        table.add_row(*total_row)
        console.print(table)

        if self.is_dynamic:
            console.print("\n[bold]Economic Effects (10-year average):[/bold]")
            console.print(f"  GDP: {np.mean(self.dynamic_effects.gdp_percent_change):.2f}%")
            console.print(
                "  Employment: "
                f"{np.mean(self.dynamic_effects.employment_change):,.0f} thousand jobs"
            )
