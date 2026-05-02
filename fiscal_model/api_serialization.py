"""
Helpers for turning scoring results into API response payloads.
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


def _extract_dynamic_series(result: Any) -> dict[str, np.ndarray | None]:
    effects = getattr(result, "dynamic_effects", None)
    if effects is not None:
        return {
            "revenue_feedback": _as_float_array(getattr(effects, "revenue_feedback", None)),
            "gdp_percent_change": _as_float_array(getattr(effects, "gdp_percent_change", None)),
            "employment_change": _as_float_array(getattr(effects, "employment_change", None)),
        }

    # Legacy shape retained for compatibility with existing tests and older callers.
    return {
        "revenue_feedback": _as_float_array(getattr(result, "revenue_feedback", None)),
        "gdp_percent_change": _as_float_array(getattr(result, "gdp_effect", None)),
        "employment_change": _as_float_array(getattr(result, "employment_effect", None)),
    }


def serialize_scoring_result(
    result: Any,
    *,
    policy_name: str,
    policy_description: str,
    dynamic_scoring_enabled: bool,
) -> dict[str, Any]:
    """Serialize a scoring result into the API response contract."""
    years = np.asarray(getattr(result, "years", []), dtype=int)
    static_revenue = _as_float_array(getattr(result, "static_revenue_effect", None))
    behavioral = _as_float_array(getattr(result, "behavioral_offset", None))
    final_deficit = _as_float_array(getattr(result, "final_deficit_effect", None))
    dynamic = _extract_dynamic_series(result)

    year_by_year = [
        {
            "year": int(year),
            "revenue_effect": _value_at(static_revenue, index),
            "behavioral_offset": _value_at(behavioral, index),
            "dynamic_feedback": _value_at(dynamic["revenue_feedback"], index),
            "final_effect": _value_at(final_deficit, index),
        }
        for index, year in enumerate(years)
    ]

    baseline = getattr(result, "baseline", None)
    baseline_vintage = (
        getattr(baseline, "baseline_vintage_date", None)
        or getattr(baseline, "baseline_vintage", None)
        or "unknown"
    )

    gdp_effect = None
    employment_effect = None
    if dynamic_scoring_enabled:
        if dynamic["gdp_percent_change"] is not None:
            gdp_effect = float(np.sum(dynamic["gdp_percent_change"]))
        if dynamic["employment_change"] is not None:
            employment_effect = float(np.mean(dynamic["employment_change"]))

    ten_year_impact = _sum_float(final_deficit)
    static_total = _sum_float(static_revenue)
    behavioral_total = _sum_float(behavioral)
    # Use the actual feedback baked into the result for any derived math —
    # final_deficit already has feedback subtracted whenever the engine ran
    # dynamic scoring, regardless of how the caller wants it displayed.
    actual_feedback_total = _sum_float(dynamic["revenue_feedback"])
    revenue_feedback_total = actual_feedback_total if dynamic_scoring_enabled else 0.0
    # Derive from the engine's final_deficit so the math holds for every
    # policy class regardless of whether its behavioral offset is signed
    # (TaxExpenditurePolicy) or magnitude (TaxPolicy). Equivalent to
    # -(static_deficit + behavioral) since revenue_feedback only enters
    # final_deficit when dynamic scoring is on.
    final_static_effect = -ten_year_impact - actual_feedback_total
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
        "revenue_feedback": revenue_feedback_total,
        "dynamic_adjusted_impact": ten_year_impact if dynamic_scoring_enabled else None,
        "year_by_year": year_by_year,
        "dynamic_scoring_enabled": dynamic_scoring_enabled,
        "credibility": credibility_to_dict(credibility),
    }
