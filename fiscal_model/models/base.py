"""
Base scoring model interface for multi-model comparison.

All scoring models implement BaseScoringModel, producing standardized
ModelResult objects that can be compared side-by-side. This enables
running the same policy through CBO-style, TPC-style, and dynamic
models and showing divergences.

See docs/ARCHITECTURE.md for the full multi-model vision.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    import pandas as pd

    from fiscal_model.policies import Policy


@dataclass
class ModelResult:
    """
    Standardized output from any scoring model.

    All models produce this format so results are directly comparable.
    """

    model_name: str
    methodology: str

    # Core budget estimates
    ten_year_cost: float  # Billions, positive = deficit increase
    annual_effects: np.ndarray  # Year-by-year deficit effect (10 values)

    # Uncertainty
    low_estimate: float = 0.0
    high_estimate: float = 0.0

    # Dynamic effects (optional)
    gdp_effect_pct: float = 0.0  # 10-year average GDP effect
    employment_effect_thousands: float = 0.0

    # Model-specific extras (distributional tables, generational accounts, etc.)
    extras: dict = field(default_factory=dict)

    @property
    def average_annual(self) -> float:
        return self.ten_year_cost / max(len(self.annual_effects), 1)

    @property
    def uncertainty_range_str(self) -> str:
        return f"${self.low_estimate:,.0f}B to ${self.high_estimate:,.0f}B"


class BaseScoringModel(ABC):
    """
    Abstract interface for all scoring models.

    Implementations:
    - CBOStyleModel: Static + behavioral (ETI) scoring (wraps FiscalPolicyScorer)
    - DynamicModel: Adds macro feedback (wraps FiscalPolicyScorer + MacroModelAdapter)

    Future:
    - TPCMicrosimModel: Microsimulation-based scoring
    - YaleBudgetLabModel: Macro + microsim + behavioral
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable model name (e.g., 'CBO Conventional')."""

    @property
    @abstractmethod
    def methodology(self) -> str:
        """Brief methodology description (1-2 sentences)."""

    @abstractmethod
    def score(self, policy: Policy) -> ModelResult:
        """
        Score a policy and return standardized results.

        Args:
            policy: Any Policy subclass (TaxPolicy, SpendingPolicy, etc.)

        Returns:
            ModelResult with ten_year_cost, annual_effects, uncertainty, extras
        """

    @abstractmethod
    def get_assumptions(self) -> dict:
        """Return all model parameters/assumptions as a flat dict."""


@dataclass
class ModelComparison:
    """
    Side-by-side comparison of the same policy scored by multiple models.
    """

    policy_name: str
    results: list[ModelResult] = field(default_factory=list)

    @property
    def model_names(self) -> list[str]:
        return [r.model_name for r in self.results]

    @property
    def spread(self) -> float:
        """Range between highest and lowest 10-year estimates."""
        costs = [r.ten_year_cost for r in self.results]
        return max(costs) - min(costs) if costs else 0.0

    @property
    def consensus_estimate(self) -> float:
        """Simple average of all model estimates."""
        if not self.results:
            return 0.0
        return sum(r.ten_year_cost for r in self.results) / len(self.results)

    def to_dataframe(self) -> pd.DataFrame:
        """Convert comparison to a DataFrame with numeric columns."""
        import pandas as pd_lib

        rows = []
        for r in self.results:
            rows.append({
                "Model": r.model_name,
                "Methodology": r.methodology,
                "10-Year Cost ($B)": r.ten_year_cost,
                "Annual Avg ($B)": r.average_annual,
                "Low ($B)": r.low_estimate,
                "High ($B)": r.high_estimate,
                "GDP Effect (%)": r.gdp_effect_pct,
            })
        return pd_lib.DataFrame(rows)

    def explain_divergence(self) -> str:
        """Generate a brief explanation of why models diverge."""
        if len(self.results) < 2:
            return "Only one model — no comparison available."

        sorted_results = sorted(self.results, key=lambda r: r.ten_year_cost)
        lowest = sorted_results[0]
        highest = sorted_results[-1]

        lines = [
            f"Models diverge by ${self.spread:,.0f}B over 10 years.",
            f"Lowest: {lowest.model_name} (${lowest.ten_year_cost:,.0f}B) — {lowest.methodology}",
            f"Highest: {highest.model_name} (${highest.ten_year_cost:,.0f}B) — {highest.methodology}",
        ]

        # Identify key drivers
        if any(r.gdp_effect_pct != 0 for r in self.results):
            dynamic = [r for r in self.results if r.gdp_effect_pct != 0]
            static = [r for r in self.results if r.gdp_effect_pct == 0]
            if dynamic and static:
                lines.append(
                    f"Dynamic models ({', '.join(r.model_name for r in dynamic)}) "
                    f"include GDP feedback effects, reducing estimated costs."
                )

        return "\n".join(lines)
