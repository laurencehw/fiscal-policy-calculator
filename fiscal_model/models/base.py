"""
Base classes for the pluggable multi-model scoring platform.

See docs/ARCHITECTURE.md for the full vision.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd

from ..baseline import APP_DEFAULT_START_YEAR


@dataclass
class ModelResult:
    """Standardized output from any scoring model."""

    model_name: str
    policy_name: str
    ten_year_cost: float
    annual_effects: np.ndarray | list[float]
    uncertainty_range: tuple[float, float] | None = None
    distributional: pd.DataFrame | None = None
    dynamic_effects: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseScoringModel(ABC):
    """Abstract base for all fiscal scoring models (CBO, TPC, PWBM, Yale, etc.)."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable model name (e.g. 'CBO', 'FRB/US-Lite', 'TPC Microsim')."""

    @property
    @abstractmethod
    def methodology(self) -> str:
        """Short description of the model's approach."""

    @abstractmethod
    def score(self, policy: Any, **kwargs: Any) -> ModelResult:
        """Score a policy and return standardized results."""

    def get_assumptions(self) -> dict[str, Any]:
        """Return key assumptions for transparency."""
        return {"name": self.name, "methodology": self.methodology}


#: Window the multi-model platform opens on when the policy names no year.
#: The app's window, not the library's — every consumer of this module (the
#: composer, the comparison tabs, the multi-model pilot) is a user-facing
#: surface.
DEFAULT_SCORER_START_YEAR = APP_DEFAULT_START_YEAR


def build_scorer_for_start_year(
    scorer_cls: Any,
    *,
    start_year: int,
    use_real_data: bool,
    cache: dict[int, Any],
) -> Any:
    """Build (and cache) a scorer whose budget window starts at ``start_year``.

    A policy that starts after the scorer's window (e.g. TCJA extension at
    2026 against a 2025–2034 window) would silently lose its final year and
    report a nine-year total as a "10-year" cost. Aligning the window to the
    policy start year keeps this total consistent with the Results tab.
    Scorer classes that don't accept ``start_year`` fall back to their default
    window.
    """
    if start_year not in cache:
        try:
            cache[start_year] = scorer_cls(start_year=start_year, use_real_data=use_real_data)
        except TypeError:
            cache[start_year] = cache.get(DEFAULT_SCORER_START_YEAR) or scorer_cls(
                use_real_data=use_real_data
            )
    return cache[start_year]


def policy_start_year(policy: Any) -> int:
    try:
        return int(getattr(policy, "start_year", DEFAULT_SCORER_START_YEAR) or DEFAULT_SCORER_START_YEAR)
    except (TypeError, ValueError):
        return DEFAULT_SCORER_START_YEAR


class CBOStyleModel(BaseScoringModel):
    """Wrapper around the existing FiscalPolicyScorer (CBO-style)."""

    name = "CBO-Style"
    methodology = "Static + ETI behavioral response + optional FRB/US dynamic feedback"

    def __init__(self, fiscal_policy_scorer_cls: Any, use_real_data: bool = True):
        self._scorer_cls = fiscal_policy_scorer_cls
        self.use_real_data = use_real_data
        self._scorers: dict[int, Any] = {}

    @property
    def scorer(self) -> Any:
        """Default-window scorer, kept for backward compatibility."""
        return build_scorer_for_start_year(
            self._scorer_cls,
            start_year=DEFAULT_SCORER_START_YEAR,
            use_real_data=self.use_real_data,
            cache=self._scorers,
        )

    def score(self, policy: Any, dynamic: bool = False, **kwargs: Any) -> ModelResult:
        del kwargs
        scorer = build_scorer_for_start_year(
            self._scorer_cls,
            start_year=policy_start_year(policy),
            use_real_data=self.use_real_data,
            cache=self._scorers,
        )
        result = scorer.score_policy(policy, dynamic=dynamic)

        # Use final_deficit_effect if available, otherwise static_revenue_effect
        if hasattr(result, "final_deficit_effect") and result.final_deficit_effect is not None:
            annual = (
                result.final_deficit_effect.tolist()
                if hasattr(result.final_deficit_effect, "tolist")
                else list(result.final_deficit_effect)
            )
            total = sum(annual)
        elif hasattr(result, "static_revenue_effect"):
            annual = (
                result.static_revenue_effect.tolist()
                if hasattr(result.static_revenue_effect, "tolist")
                else list(result.static_revenue_effect)
            )
            total = sum(annual)
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
            annual = [0.0] * horizon
            total = 0.0

        low_estimate = getattr(result, "low_estimate", None)
        high_estimate = getattr(result, "high_estimate", None)
        uncertainty_range = None
        if low_estimate is not None and high_estimate is not None:
            low_annual = low_estimate.tolist() if hasattr(low_estimate, "tolist") else list(low_estimate)
            high_annual = high_estimate.tolist() if hasattr(high_estimate, "tolist") else list(high_estimate)
            uncertainty_range = (float(sum(low_annual)), float(sum(high_annual)))

        return ModelResult(
            model_name=self.name,
            policy_name=getattr(policy, "name", "Unnamed Policy"),
            ten_year_cost=total,
            annual_effects=annual,
            uncertainty_range=uncertainty_range,
            dynamic_effects=getattr(result, "dynamic_effects", None),
            metadata={
                "dynamic_enabled": dynamic,
                "methodology": self.methodology,
                "use_real_data": self.use_real_data,
            },
        )
