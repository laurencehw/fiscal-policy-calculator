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
from typing import TYPE_CHECKING, Any

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
    annual_effects: np.ndarray  # Year-by-year deficit effect

    # Uncertainty
    low_estimate: float = 0.0
    high_estimate: float = 0.0

    # Dynamic effects (optional)
    gdp_effect_pct: float = 0.0
    employment_effect_thousands: float = 0.0

    # Model-specific extras
    extras: dict[str, Any] = field(default_factory=dict)

    # Compatibility fields for UI adapters
    policy_name: str = ""
    distributional: "pd.DataFrame | None" = None
    dynamic_effects: Any = None

    @property
    def average_annual(self) -> float:
        return self.ten_year_cost / max(len(self.annual_effects), 1)

    @property
    def uncertainty_range(self) -> tuple[float, float]:
        return (float(self.low_estimate), float(self.high_estimate))

    @property
    def uncertainty_range_str(self) -> str:
        return f"${self.low_estimate:,.0f}B to ${self.high_estimate:,.0f}B"


class BaseScoringModel(ABC):
    """
    Abstract interface for all scoring models.
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
    def score(self, policy: "Policy", **kwargs: Any) -> ModelResult:
        """Score a policy and return standardized results."""

    @abstractmethod
    def get_assumptions(self) -> dict[str, Any]:
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
        costs = [r.ten_year_cost for r in self.results]
        return max(costs) - min(costs) if costs else 0.0

    @property
    def consensus_estimate(self) -> float:
        if not self.results:
            return 0.0
        return sum(r.ten_year_cost for r in self.results) / len(self.results)

    def to_dataframe(self) -> "pd.DataFrame":
        import pandas as pd_lib

        return pd_lib.DataFrame(
            [
                {
                    "Model": r.model_name,
                    "Methodology": r.methodology,
                    "10-Year Cost ($B)": r.ten_year_cost,
                    "Annual Avg ($B)": r.average_annual,
                    "Low ($B)": r.low_estimate,
                    "High ($B)": r.high_estimate,
                    "GDP Effect (%)": r.gdp_effect_pct,
                }
                for r in self.results
            ]
        )

    def explain_divergence(self) -> str:
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

        dynamic = [r for r in self.results if r.gdp_effect_pct != 0]
        static = [r for r in self.results if r.gdp_effect_pct == 0]
        if dynamic and static:
            lines.append(
                f"Dynamic models ({', '.join(r.model_name for r in dynamic)}) "
                "include GDP feedback effects, reducing estimated costs."
            )

        return "\n".join(lines)


class CBOStyleModel(BaseScoringModel):
    """
    Thin compatibility wrapper around FiscalPolicyScorer for the UI comparison tab.
    """

    name = "CBO-Style"
    methodology = "Static + ETI behavioral response + optional FRB/US dynamic feedback"

    def __init__(self, fiscal_policy_scorer_cls: Any, use_real_data: bool = True):
        self.scorer = fiscal_policy_scorer_cls(use_real_data=use_real_data)
        self.use_real_data = use_real_data

    def score(self, policy: "Policy", dynamic: bool = False, **kwargs: Any) -> ModelResult:
        del kwargs
        result = self.scorer.score_policy(policy, dynamic=dynamic)

        if hasattr(result, "final_deficit_effect") and result.final_deficit_effect is not None:
            annual = np.asarray(result.final_deficit_effect, dtype=float)
        elif hasattr(result, "static_revenue_effect") and result.static_revenue_effect is not None:
            annual = np.asarray(result.static_revenue_effect, dtype=float)
        else:
            horizon = max(
                1,
                int(
                    getattr(
                        policy,
                        "duration_years",
                        len(getattr(getattr(result, "baseline", None), "years", []) or []),
                    )
                    or 1
                ),
            )
            annual = np.zeros(horizon, dtype=float)

        low_estimate = getattr(result, "low_estimate", None)
        high_estimate = getattr(result, "high_estimate", None)
        low_total = 0.0
        high_total = 0.0
        if low_estimate is not None and high_estimate is not None:
            low_total = float(np.asarray(low_estimate, dtype=float).sum())
            high_total = float(np.asarray(high_estimate, dtype=float).sum())

        gdp_effect_pct = 0.0
        employment_effect_thousands = 0.0
        if getattr(result, "dynamic_effects", None) is not None:
            gdp_effect_pct = float(np.mean(result.dynamic_effects.gdp_percent_change))
            employment_effect_thousands = float(np.mean(result.dynamic_effects.employment_change))

        return ModelResult(
            model_name=self.name,
            methodology=self.methodology,
            policy_name=getattr(policy, "name", "Unnamed Policy"),
            ten_year_cost=float(annual.sum()),
            annual_effects=annual,
            low_estimate=low_total,
            high_estimate=high_total,
            gdp_effect_pct=gdp_effect_pct,
            employment_effect_thousands=employment_effect_thousands,
            extras={"dynamic_enabled": dynamic},
            dynamic_effects=getattr(result, "dynamic_effects", None),
        )

    def get_assumptions(self) -> dict[str, Any]:
        return {
            "scoring_type": "cbo_style",
            "dynamic": True,
            "uses_real_data": self.use_real_data,
        }
