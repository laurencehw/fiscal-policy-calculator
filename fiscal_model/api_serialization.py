"""
Helpers for turning scoring results into API response payloads.

The dynamic fields are the app's dynamic view (:mod:`fiscal_model.dynamic_view`),
which the caller runs and passes in. They are never read off the scoring
engine's ``ScoringResult.dynamic_effects``.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from fiscal_model.validation.credibility import (
    credibility_to_dict,
    get_credibility_for_result,
)


def _as_float_array(value: Any) -> np.ndarray | None:
    if value is None:
        return None

    try:
        array = np.asarray(value, dtype=float)
    except (TypeError, ValueError):
        return None

    if array.ndim == 0:
        return array.reshape(1)
    return array


def _sum_float(value: Any) -> float:
    array = _as_float_array(value)
    if array is None:
        return 0.0
    return float(np.sum(array))


def _value_at(series: np.ndarray | None, index: int) -> float:
    if series is None or series.size == 0:
        return 0.0
    if index < series.size:
        return float(series[index])
    return float(series[-1])


#: ``error_message`` when dynamic scoring was asked for and the macro model
#: produced no view. The conventional fields are unaffected, and the dynamic
#: ones are null rather than zero, so a failure cannot read as "no feedback".
DYNAMIC_VIEW_UNAVAILABLE_MESSAGE = (
    "Dynamic view unavailable: the macro model did not run on this policy. "
    "The conventional score is unaffected; the dynamic fields are null."
)


def _conventional_series(result: Any) -> np.ndarray | None:
    """Year-by-year conventional deficit effect: static + behavioral.

    This is the engine's own ``deficit_after_behavioral`` for every policy
    class, whichever sign convention its behavioral offset uses, and it does
    not move when the engine is run with ``dynamic=True``. A hand-built result
    without the decomposition is read at ``final_deficit_effect``, which is the
    same path for any run scored with ``dynamic=False`` (the only kind the API
    scores).
    """
    static_deficit = _as_float_array(getattr(result, "static_deficit_effect", None))
    behavioral = _as_float_array(getattr(result, "behavioral_offset", None))
    if (
        static_deficit is not None
        and behavioral is not None
        and static_deficit.shape == behavioral.shape
    ):
        return static_deficit + behavioral
    return _as_float_array(getattr(result, "final_deficit_effect", None))


def serialize_scoring_result(
    result: Any,
    *,
    policy_name: str,
    policy_description: str,
    dynamic_scoring_enabled: bool,
    dynamic_view: Any = None,
    macro_result: Any = None,
) -> dict[str, Any]:
    """Serialize a scoring result into the API response contract.

    The headline, ``ten_year_deficit_impact``, is the **conventional** score
    (static + behavioral, positive = increases the deficit) whether or not
    dynamic scoring was asked for. That is the app's rule: dynamic scoring adds
    a labelled view and never moves the headline.

    With ``dynamic_scoring_enabled`` the dynamic fields come from
    ``dynamic_view`` and ``macro_result``, the pair
    :func:`fiscal_model.dynamic_view.run_dynamic_view` returns. That is the
    macro adapter the app's dynamic view runs, FRB/US-Lite by default. The
    engine's ``EconomicModel`` output on ``result.dynamic_effects`` is never
    read. Until 2026-09-29 it was, and for +2.6pp above $400,000 the API
    returned a dynamic score of -$86.1B where the app showed -$338.9B.
    """
    years = np.asarray(getattr(result, "years", []), dtype=int)
    static_revenue = _as_float_array(getattr(result, "static_revenue_effect", None))
    behavioral = _as_float_array(getattr(result, "behavioral_offset", None))
    conventional = _conventional_series(result)

    view = dynamic_view if dynamic_scoring_enabled else None
    macro = macro_result if view is not None else None
    feedback_path = _as_float_array(getattr(macro, "revenue_feedback_billions", None))
    debt_service_path = _as_float_array(getattr(macro, "interest_cost_billions", None))

    year_by_year = []
    for index, year in enumerate(years):
        final_effect = _value_at(conventional, index)
        feedback = _value_at(feedback_path, index)
        entry: dict[str, Any] = {
            "year": int(year),
            "revenue_effect": _value_at(static_revenue, index),
            "behavioral_offset": _value_at(behavioral, index),
            "dynamic_feedback": feedback,
            "final_effect": final_effect,
            "debt_service": None,
            "dynamic_effect": None,
        }
        if macro is not None:
            debt_service_year = _value_at(debt_service_path, index)
            entry["debt_service"] = debt_service_year
            entry["dynamic_effect"] = final_effect - feedback + debt_service_year
        year_by_year.append(entry)

    baseline = getattr(result, "baseline", None)
    baseline_vintage = (
        getattr(baseline, "baseline_vintage_date", None)
        or getattr(baseline, "baseline_vintage", None)
        or "unknown"
    )

    ten_year_impact = _sum_float(conventional)
    static_total = _sum_float(static_revenue)
    behavioral_total = _sum_float(behavioral)
    # Revenue convention: the revenue effect net of behavioral response and
    # before any macro feedback, which is the negated conventional path for
    # every policy class.
    final_static_effect = -ten_year_impact

    revenue_feedback: float | None = None
    gdp_effect: float | None = None
    employment_effect: float | None = None
    debt_service: float | None = None
    dynamic_adjusted_impact: float | None = None
    dynamic_model: str | None = None
    error_message: str | None = None
    if not dynamic_scoring_enabled:
        revenue_feedback = 0.0
    elif view is None:
        error_message = DYNAMIC_VIEW_UNAVAILABLE_MESSAGE
    else:
        revenue_feedback = float(view.feedback)
        debt_service = float(view.debt_service)
        dynamic_adjusted_impact = float(view.dynamic_total)
        dynamic_model = str(view.model_name)
        if macro is not None:
            # Percent-years: the sum of the annual GDP level effect, the
            # "Cumulative GDP Effect" the app's Economic Effects tab prints.
            gdp_effect = float(macro.cumulative_gdp_effect)
            employment = _as_float_array(getattr(macro, "employment_change_millions", None))
            if employment is not None and employment.size:
                # The adapters report millions; this field has always been
                # thousands of jobs.
                employment_effect = float(np.mean(employment)) * 1000.0

    credibility = get_credibility_for_result(
        point_estimate=ten_year_impact,
        policy_name=policy_name,
        policy=getattr(result, "policy", None),
    )

    return {
        "policy_name": policy_name,
        "policy_description": policy_description,
        "baseline_vintage": str(baseline_vintage),
        "budget_window": (
            f"FY{int(years[0])}-{int(years[-1])}" if years.size else ""
        ),
        "ten_year_deficit_impact": ten_year_impact,
        "static_revenue_effect": static_total,
        "behavioral_offset": behavioral_total,
        "final_static_effect": final_static_effect,
        "gdp_effect": gdp_effect,
        "employment_effect": employment_effect,
        "revenue_feedback": revenue_feedback,
        "debt_service": debt_service,
        "dynamic_adjusted_impact": dynamic_adjusted_impact,
        "dynamic_model": dynamic_model,
        "year_by_year": year_by_year,
        "dynamic_scoring_enabled": dynamic_scoring_enabled,
        "credibility": credibility_to_dict(credibility),
        "error_message": error_message,
    }
