"""
The dynamic view: the one macroeconomic-feedback decomposition every surface
reports.

Phase 4 of the redesign (``planning/redesign/NOTES.md`` §4.4) settled what a
dynamic score means in this repository with one rule:

* **The headline is always the conventional score**: ``static_deficit +
  behavioral``, positive = increases the deficit. It never moves when dynamic
  scoring is switched on, so a calibrated preset keeps matching its official
  benchmark either way.
* **Dynamic scoring adds a labelled view, never a different headline**:
  revenue feedback, debt service and a dynamic total, all from one run of the
  macro adapter the model setting names (FRB/US-Lite by default, or the simple
  multiplier).
* **Debt service is included in both places or neither.** CBO's dynamic
  analyses net the interest cost of the added deficit against growth feedback,
  and a dynamic total that ignores it overstates the offset.

This module is that rule with no UI attached, so the Streamlit app, the REST
API (``POST /score`` and ``/score/preset``) and the Ask assistant compute the
dynamic view with the same code. Until 2026-09-29 only the app did. The API
and Ask reported the scoring engine's internal ``EconomicModel`` feedback
(``ScoringResult.dynamic_effects``) instead. That model's supply channel
applies a rate change to all of nominal GDP, and it scored +2.6pp above
$400,000 at -$86.1B dynamically where the app scored -$338.9B.
``EconomicModel`` is unchanged and still runs under
``score_policy(dynamic=True)``. R9 weighted its supply channel by the share of
AGI a rate change reaches (``planning/lanes/R9_economic_model_supply_weighting.md``),
taking that policy to -$206.4B; it is still a different model from this view.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

#: Value of the "Macro model" setting that selects the simple Keynesian path.
SIMPLE_MULTIPLIER_SETTING = "Simple Multiplier"
#: The setting's default option. Surfaces with no setting (the API, Ask) run it.
DEFAULT_MACRO_MODEL_SETTING = "FRB/US-Lite (recommended)"
#: Display names for the two adapters (used in captions, exports and metadata).
FRBUS_LITE_MODEL_LABEL = "FRB/US-Lite (Federal Reserve calibrated)"
SIMPLE_MULTIPLIER_MODEL_LABEL = "Simple Keynesian Multiplier"


@dataclass(frozen=True)
class DynamicView:
    """The dynamic decomposition of one scored policy.

    Every field is in the deficit convention (**positive increases the
    deficit**) except ``feedback``, which is revenue: extra revenue shrinks the
    deficit, so it is subtracted. ``debt_service`` is added, so::

        dynamic_total = conventional - feedback + debt_service
    """

    model_name: str
    conventional: float
    feedback: float
    debt_service: float
    dynamic_total: float

    def as_dict(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "conventional": self.conventional,
            "feedback": self.feedback,
            "debt_service": self.debt_service,
            "dynamic_total": self.dynamic_total,
        }


def conventional_path(result: Any) -> np.ndarray:
    """Return the year-by-year conventional deficit effect, static + behavioral.

    For a run scored with ``dynamic=False`` this equals
    ``result.final_deficit_effect``. With ``dynamic=True`` it does not: the
    engine subtracts ``EconomicModel`` feedback there.
    """
    return np.asarray(result.static_deficit_effect, dtype=float) + np.asarray(
        result.behavioral_offset, dtype=float
    )


def conventional_total(result: Any) -> float:
    """Return the conventional (static + behavioral) 10-year deficit effect.

    This is the headline number on every surface, in every mode. It is
    deliberately *not* ``result.final_deficit_effect``: with dynamic scoring on,
    the engine subtracts its internal feedback there, which pushed calibrated
    presets off their benchmark purely because a toggle was flipped.
    """
    return float(conventional_path(result).sum())


def policy_is_spending(policy: Any) -> bool:
    """Whether the macro scenario carries this policy as outlays, not receipts.

    This is the app's rule. The spending form builds a
    :class:`~fiscal_model.policies_core.SpendingPolicy` and flags the run as
    spending. Every other path (Tailor, every preset, every tax module) is a
    receipts impulse. No preset builds a ``SpendingPolicy`` today, so this and
    the preset path's hard-coded ``is_spending: False`` agree on every preset.
    ``tests/test_dynamic_view_routing.py`` fails if that ever stops being true.
    """
    from fiscal_model.policies_core import SpendingPolicy

    return isinstance(policy, SpendingPolicy)


def build_macro_scenario(
    policy: Any,
    result: Any,
    is_spending_policy: bool,
    macro_scenario_cls: Any = None,
) -> Any:
    """Build a MacroScenario from a scored policy result.

    Spending policy impacts map to outlays, while tax policies map to receipts.
    """
    if macro_scenario_cls is None:
        from fiscal_model.models.macro_adapter import MacroScenario

        macro_scenario_cls = MacroScenario

    # behavioral_offset is deficit convention (positive = adds to deficit),
    # so the conventional deficit path is static_deficit + behavioral — the
    # same sum the scorer uses for deficit_after_behavioral. Deriving receipts
    # from static_revenue + behavioral mixed conventions (double-counting the
    # offset), and spending policies produced an all-zero scenario because
    # their impulse lives in static_spending_effect, not static_revenue_effect.
    net_deficit = result.static_deficit_effect + result.behavioral_offset
    horizon = len(net_deficit)

    if is_spending_policy:
        receipts_change = np.zeros(horizon)
        outlays_change = np.array(net_deficit)
    else:
        receipts_change = np.array(-net_deficit)
        outlays_change = np.zeros(horizon)

    return macro_scenario_cls(
        name=policy.name,
        description=f"Dynamic scoring for {policy.name}",
        start_year=int(result.baseline.years[0]),
        horizon_years=horizon,
        receipts_change=receipts_change,
        outlays_change=outlays_change,
    )


def resolve_macro_adapter(
    macro_model_name: str | None = None,
    frbus_adapter_lite_cls: Any = None,
    simple_multiplier_adapter_cls: Any = None,
) -> tuple[Any, str]:
    """Instantiate the macro adapter named by the model setting.

    Shared by the calculation pipeline, the Economic Effects tab, the API and
    Ask, so every surface runs the *same* model. That is the precondition for
    them printing the same feedback number. Any value other than
    :data:`SIMPLE_MULTIPLIER_SETTING`, ``None`` included, selects FRB/US-Lite.
    The adapter classes are injectable for the app's dependency container and
    tests, and default to the shipped adapters.
    """
    if macro_model_name == SIMPLE_MULTIPLIER_SETTING:
        if simple_multiplier_adapter_cls is None:
            from fiscal_model.models.macro_adapter import SimpleMultiplierAdapter

            simple_multiplier_adapter_cls = SimpleMultiplierAdapter
        return simple_multiplier_adapter_cls(), SIMPLE_MULTIPLIER_MODEL_LABEL
    if frbus_adapter_lite_cls is None:
        from fiscal_model.models.macro_adapter import FRBUSAdapterLite

        frbus_adapter_lite_cls = FRBUSAdapterLite
    return frbus_adapter_lite_cls(), FRBUS_LITE_MODEL_LABEL


def macro_setting_for_label(model_name: str | None) -> str:
    """The model setting that produces the adapter a display label names.

    ``DynamicView.model_name`` (and ``ScoredResult.macro_model``) carry the
    display label; re-running the same adapter needs the setting value.
    """
    if model_name == SIMPLE_MULTIPLIER_MODEL_LABEL:
        return SIMPLE_MULTIPLIER_SETTING
    return DEFAULT_MACRO_MODEL_SETTING


def compute_dynamic_view(result: Any, macro_result: Any, model_name: str) -> DynamicView:
    """Build the one dynamic decomposition every surface renders."""
    conventional = conventional_total(result)
    feedback = float(macro_result.cumulative_revenue_feedback)
    debt_service = float(np.sum(macro_result.interest_cost_billions))
    return DynamicView(
        model_name=model_name,
        conventional=conventional,
        feedback=feedback,
        debt_service=debt_service,
        dynamic_total=conventional - feedback + debt_service,
    )


def run_dynamic_view(
    policy: Any,
    result: Any,
    *,
    is_spending: bool | None = None,
    macro_model_name: str | None = None,
    macro_scenario_cls: Any = None,
    frbus_adapter_lite_cls: Any = None,
    simple_multiplier_adapter_cls: Any = None,
    build_macro_scenario_fn: Any = None,
) -> tuple[DynamicView | None, Any]:
    """Run the macro adapter once and return ``(DynamicView, MacroResult)``.

    ``result`` needs only its conventional path, so a run scored with
    ``dynamic=False`` gives the same view as one scored with ``dynamic=True``.
    ``is_spending`` defaults to :func:`policy_is_spending`, and
    ``macro_model_name`` to FRB/US-Lite.

    Returns ``(None, None)`` if the adapter fails. A broken macro model must
    degrade the dynamic view, never the conventional score.
    """
    if is_spending is None:
        is_spending = policy_is_spending(policy)
    build = build_macro_scenario_fn or build_macro_scenario
    try:
        scenario = build(
            policy=policy,
            result=result,
            is_spending_policy=is_spending,
            macro_scenario_cls=macro_scenario_cls,
        )
        adapter, model_name = resolve_macro_adapter(
            macro_model_name, frbus_adapter_lite_cls, simple_multiplier_adapter_cls
        )
        macro_result = adapter.run(scenario)
        return compute_dynamic_view(result, macro_result, model_name), macro_result
    except Exception:
        logger.exception("Dynamic view computation failed for %r", getattr(policy, "name", "?"))
        return None, None


__all__ = [
    "DEFAULT_MACRO_MODEL_SETTING",
    "FRBUS_LITE_MODEL_LABEL",
    "SIMPLE_MULTIPLIER_MODEL_LABEL",
    "SIMPLE_MULTIPLIER_SETTING",
    "DynamicView",
    "build_macro_scenario",
    "compute_dynamic_view",
    "conventional_path",
    "conventional_total",
    "macro_setting_for_label",
    "policy_is_spending",
    "resolve_macro_adapter",
    "run_dynamic_view",
]
