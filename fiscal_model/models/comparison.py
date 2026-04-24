"""
Pilot multi-model comparison services for feasibility work.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from fiscal_model.distribution import DistributionalEngine, IncomeGroupType
from fiscal_model.distribution_effects import policy_to_microsim_reforms
from fiscal_model.feasibility import DEFAULT_MICRODATA_RELATIVE_PATH
from fiscal_model.microsim.engine import MicroTaxCalculator
from fiscal_model.models.olg import PWBMModel

from .base import BaseScoringModel, CBOStyleModel, ModelResult
from .macro_adapter import policy_to_scenario


class UnsupportedModelPolicyError(ValueError):
    """Raised when a policy cannot yet be represented by a pilot comparison model."""


@dataclass
class ComparisonBundle:
    """Serializable multi-model comparison output."""

    policy_name: str
    results: list[ModelResult] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)

    @property
    def max_gap(self) -> float | None:
        if len(self.results) < 2:
            return None
        estimates = [float(result.ten_year_cost) for result in self.results]
        return max(estimates) - min(estimates)

    def to_dataframe(self) -> pd.DataFrame:
        rows = []
        for result in self.results:
            lower = None
            upper = None
            if result.uncertainty_range is not None:
                lower, upper = result.uncertainty_range

            rows.append(
                {
                    "Model": result.model_name,
                    "Policy": result.policy_name,
                    "10-Year Cost": float(result.ten_year_cost),
                    "Methodology": (result.metadata or {}).get("methodology", ""),
                    "Has Distributional Output": result.distributional is not None,
                    "Uncertainty Low": lower,
                    "Uncertainty High": upper,
                }
            )

        return pd.DataFrame(rows)

    def to_dict(self) -> dict[str, Any]:
        return {
            "policy_name": self.policy_name,
            "results": [
                {
                    "model_name": result.model_name,
                    "policy_name": result.policy_name,
                    "ten_year_cost": float(result.ten_year_cost),
                    "annual_effects": [float(value) for value in result.annual_effects],
                    "uncertainty_range": (
                        [float(result.uncertainty_range[0]), float(result.uncertainty_range[1])]
                        if result.uncertainty_range is not None
                        else None
                    ),
                    "has_distributional_output": result.distributional is not None,
                    "metadata": result.metadata or {},
                }
                for result in self.results
            ],
            "errors": dict(self.errors),
            "max_gap": self.max_gap,
        }


def _default_microdata_path() -> Path:
    return Path(__file__).resolve().parents[2] / DEFAULT_MICRODATA_RELATIVE_PATH


def _pad_or_trim(values: Any, length: int) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if len(array) == length:
        return array
    if len(array) == 0:
        return np.zeros(length, dtype=float)
    if len(array) > length:
        return array[:length]
    return np.concatenate([array, np.full(length - len(array), array[-1])])


class TPCMicrosimModel(BaseScoringModel):
    """Pilot microsimulation adapter behind the shared model interface."""

    name = "TPC-Microsim Pilot"
    methodology = (
        "Single-year CPS-style microsimulation with flat-horizon annualization and "
        "quintile distribution output."
    )

    def __init__(
        self,
        *,
        population: pd.DataFrame | None = None,
        microdata_path: str | Path | None = None,
        distribution_engine_cls: Any = DistributionalEngine,
    ):
        self._population = population.copy(deep=True) if population is not None else None
        self._microdata_path = Path(microdata_path).resolve() if microdata_path else _default_microdata_path()
        self._distribution_engine_cls = distribution_engine_cls

    def _load_population(self) -> tuple[pd.DataFrame, str]:
        if self._population is not None:
            return self._population.copy(deep=True), "in_memory"
        if not self._microdata_path.exists():
            raise FileNotFoundError(
                f"Microsim pilot requires built microdata at {self._microdata_path}."
            )
        return pd.read_csv(self._microdata_path), str(self._microdata_path)

    def score(self, policy: Any, **kwargs: Any) -> ModelResult:
        del kwargs
        reforms = policy_to_microsim_reforms(policy, year=getattr(policy, "start_year", 2025))
        if not reforms:
            supported = (
                "rate-change (any TaxPolicy), Child Tax Credit (TaxCreditPolicy), "
                "EITC expansion, standard-deduction bonus, and SALT cap "
                "(TaxExpenditurePolicy)."
            )
            raise UnsupportedModelPolicyError(
                f"{getattr(policy, 'name', 'Policy')} of type "
                f"{type(policy).__name__} does not map onto the current "
                f"microsim pilot reforms. Supported today: {supported} "
                "See fiscal_model.distribution_effects.policy_to_microsim_reforms "
                "for the mapping; extend it if you need a new policy type."
            )

        population, population_source = self._load_population()
        year = int(getattr(policy, "start_year", 2025) or 2025)
        calc = MicroTaxCalculator(year=year)
        baseline = calc.calculate(population)
        reform = calc.apply_reform(population, reforms)

        weighted_change = (reform["final_tax"] - baseline["final_tax"]) * baseline["weight"]
        annual_revenue_change = float(weighted_change.sum() / 1e9)
        annual_deficit_effect = -annual_revenue_change
        horizon = max(1, int(getattr(policy, "duration_years", 10) or 10))
        annual_effects = [annual_deficit_effect] * horizon

        notes: list[str] = []
        if getattr(policy, "rate_change", 0.0) != 0:
            notes.append("Generic rate-change policies are approximated as top-rate reforms in the pilot microsim.")
        if getattr(policy, "affected_income_threshold", 0.0) not in (0, None):
            notes.append("Income thresholds are not yet explicitly represented in the pilot microsim mapping.")

        distributional = None
        try:
            analysis = self._distribution_engine_cls(
                data_year=int(getattr(policy, "data_year", 2022) or 2022)
            ).analyze_policy_microsim(
                policy,
                microdata=population,
                group_type=IncomeGroupType.QUINTILE,
                year=year,
            )
            distributional = analysis.to_dataframe()
        except Exception as exc:  # pragma: no cover - fallback path exercised in integration use
            notes.append(f"Distributional output unavailable: {exc}")

        return ModelResult(
            model_name=self.name,
            policy_name=getattr(policy, "name", "Unnamed Policy"),
            ten_year_cost=float(sum(annual_effects)),
            annual_effects=annual_effects,
            distributional=distributional,
            metadata={
                "methodology": self.methodology,
                "population_source": population_source,
                "reforms": reforms,
                "annualization_assumption": "flat_by_year",
                "notes": notes,
            },
        )


class PWBMScoringModel(BaseScoringModel):
    """Pilot adapter that combines the existing scorer with the OLG backend."""

    name = "PWBM-OLG Pilot"
    methodology = (
        "Static fiscal path from the core scorer plus OLG revenue-feedback and interest-cost "
        "adjustments from the PWBM-style adapter."
    )

    def __init__(
        self,
        fiscal_policy_scorer_cls: Any,
        *,
        macro_model: Any | None = None,
        use_real_data: bool = False,
    ):
        self.scorer = fiscal_policy_scorer_cls(use_real_data=use_real_data)
        self.use_real_data = use_real_data
        self.macro_model = macro_model or PWBMModel()

    def score(self, policy: Any, **kwargs: Any) -> ModelResult:
        del kwargs
        scored_policy = self.scorer.score_policy(policy, dynamic=False)
        base_deficit = np.asarray(getattr(scored_policy, "final_deficit_effect", []), dtype=float)
        scenario = policy_to_scenario(policy, scored_policy, scenario_name=f"{policy.name} — PWBM Pilot")
        macro_result = self.macro_model.run(scenario)
        revenue_feedback = _pad_or_trim(macro_result.revenue_feedback_billions, len(base_deficit))
        interest_cost = _pad_or_trim(macro_result.interest_cost_billions, len(base_deficit))
        final_deficit = base_deficit - revenue_feedback + interest_cost

        metadata = {
            "methodology": self.methodology,
            "use_real_data": self.use_real_data,
            "macro_model": getattr(self.macro_model, "name", type(self.macro_model).__name__),
        }
        confidence_label = getattr(macro_result, "confidence_label", None)
        if confidence_label:
            metadata["confidence_label"] = confidence_label

        return ModelResult(
            model_name=self.name,
            policy_name=getattr(policy, "name", "Unnamed Policy"),
            ten_year_cost=float(final_deficit.sum()),
            annual_effects=final_deficit.tolist(),
            dynamic_effects=macro_result,
            metadata=metadata,
        )


def build_default_comparison_models(
    fiscal_policy_scorer_cls: Any,
    *,
    use_real_data: bool = False,
    microdata_path: str | Path | None = None,
) -> list[BaseScoringModel]:
    """Build the current pilot model set for feasibility comparisons."""

    return [
        CBOStyleModel(fiscal_policy_scorer_cls, use_real_data=use_real_data),
        TPCMicrosimModel(microdata_path=microdata_path),
        PWBMScoringModel(fiscal_policy_scorer_cls, use_real_data=use_real_data),
    ]


def compare_policy_models(
    policy: Any,
    models: Iterable[BaseScoringModel],
    *,
    continue_on_error: bool = False,
) -> ComparisonBundle:
    """Run one policy through multiple model backends."""

    bundle = ComparisonBundle(policy_name=getattr(policy, "name", "Unnamed Policy"))
    for model in models:
        try:
            bundle.results.append(model.score(policy))
        except Exception as exc:
            if not continue_on_error:
                raise
            bundle.errors[getattr(model, "name", type(model).__name__)] = str(exc)
    return bundle

