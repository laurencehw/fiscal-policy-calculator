"""The result views behind a score, as plain data: who pays, and economic effects.

The Streamlit app draws these in its Distribution and Economic Effects tabs.
The new site reads the same numbers from the nightly static export, so the
two surfaces call the same engines: ``DistributionalEngine.analyze_policy``
and :func:`fiscal_model.dynamic_view.run_dynamic_view`.

Nothing here imports Streamlit or Plotly; the engine bundle can import it.
"""

from __future__ import annotations

from typing import Any

from fiscal_model.distribution import DistributionalEngine, IncomeGroupType
from fiscal_model.distribution_reporting import (
    distribution_not_representable,
    generate_winners_losers_summary,
)
from fiscal_model.dynamic_view import run_dynamic_view

GROUPINGS: dict[str, IncomeGroupType] = {
    "quintile": IncomeGroupType.QUINTILE,
    "decile": IncomeGroupType.DECILE,
    "jct_dollar": IncomeGroupType.JCT_DOLLAR,
}


def _num(value: Any) -> float:
    return float(value or 0.0)


def distribution_view(policy: Any, engine: DistributionalEngine | None = None) -> dict[str, Any]:
    """Who pays, by income group, in the policy's first year.

    ``available`` is False when the engine cannot represent the policy at the
    household level; an all-zero table would read as "flat" and be wrong, so
    no table is given then (the app's rule, ``distribution_not_representable``).
    """
    if not hasattr(policy, "rate_change"):
        return {"available": False, "reason": "not_a_tax_policy", "groupings": {}}
    engine = engine or DistributionalEngine(data_year=2022)
    groupings: dict[str, Any] = {}
    for key, group_type in GROUPINGS.items():
        analysis = engine.analyze_policy(policy, group_type=group_type, prefer_microsim=True)
        if distribution_not_representable(policy, analysis):
            return {"available": False, "reason": "not_representable", "groupings": {}}
        summary = generate_winners_losers_summary(analysis)
        groupings[key] = {
            "engine": "microsim" if str(analysis.engine).lower().startswith("micro") else "synthetic",
            "unit": analysis.unit,
            "year": int(analysis.year),
            "total_tax_change_billions": _num(analysis.total_tax_change),
            "pct_with_increase": _num(summary["pct_with_increase"]),
            "pct_with_decrease": _num(summary["pct_with_decrease"]),
            "groups": [
                {
                    "name": r.income_group.name,
                    "floor": _num(r.income_group.floor),
                    "ceiling": None if r.income_group.ceiling is None else _num(r.income_group.ceiling),
                    "returns_millions": _num(r.income_group.num_returns) / 1e6,
                    "avg_tax_change": _num(r.tax_change_avg),
                    "pct_of_income": _num(r.tax_change_pct_income),
                    "share_of_total": _num(r.share_of_total_change),
                    "pct_with_increase": _num(r.pct_with_increase),
                    "pct_with_decrease": _num(r.pct_with_decrease),
                    "baseline_etr": _num(r.baseline_etr),
                    "new_etr": _num(r.new_etr),
                }
                for r in analysis.results
            ],
        }
    return {"available": True, "reason": None, "groupings": groupings}


def economic_view(policy: Any, result: Any) -> dict[str, Any]:
    """The macro paths behind the dynamic score (FRB/US-Lite, the app's default).

    ``result`` needs only its conventional path. Returns ``available: False``
    when the macro adapter fails, as the app does.
    """
    view, macro = run_dynamic_view(policy, result)
    if view is None or macro is None:
        return {"available": False}

    def series(values: Any) -> list[float]:
        return [float(v) for v in values]

    return {
        "available": True,
        "model": view.model_name,
        "conventional_billions": view.conventional,
        "revenue_feedback_billions": view.feedback,
        "debt_service_billions": view.debt_service,
        "dynamic_total_billions": view.dynamic_total,
        "gdp_percent_years": float(macro.cumulative_gdp_effect),
        "years": [int(y) for y in macro.years],
        "gdp_level_pct": series(macro.gdp_level_pct),
        "employment_millions": series(macro.employment_change_millions),
        "unemployment_rate_ppts": series(macro.unemployment_rate_ppts),
        "long_rate_ppts": series(macro.long_rate_ppts),
        "revenue_feedback_by_year": series(macro.revenue_feedback_billions),
        "debt_service_by_year": series(macro.interest_cost_billions),
    }


def models_view(policy: Any, models: Any) -> dict[str, Any]:
    """The same policy through every default pilot backend (the app's Scoring Models tab).

    ``models`` is ``build_default_comparison_models(...)``. Backends that cannot
    represent the policy are listed with their reason rather than dropped.
    """
    from fiscal_model.feasibility import assess_model_pilot_comparison
    from fiscal_model.models.comparison import compare_policy_models

    bundle = compare_policy_models(policy, models, continue_on_error=True)
    assessment = assess_model_pilot_comparison(bundle) if bundle.results else None
    results = []
    for r in bundle.results:
        meta = r.metadata or {}
        notes = meta.get("notes") or []
        results.append(
            {
                "model": r.model_name,
                "ten_year_billions": float(r.ten_year_cost),
                "annual_billions": [float(v) for v in r.annual_effects],
                "methodology": str(meta.get("methodology", "")),
                "confidence": meta.get("confidence_label"),
                "notes": [str(n) for n in notes] if isinstance(notes, list) else [str(notes)],
            }
        )
    return {
        "results": results,
        "skipped": [
            {"model": name, "kind": bundle.error_kinds.get(name, "error"), "reason": reason}
            for name, reason in bundle.errors.items()
        ],
        "blockers": list(assessment.blockers) if assessment else [],
        "warnings": list(assessment.warnings) if assessment else [],
    }


def states_view(year: int = 2025) -> dict[str, Any]:
    """The app's State tab for the ten modelled states: parameters, rate curves, SALT cap lift."""
    from fiscal_model.models.state import (
        FederalStateCalculator,
        StateTaxDatabase,
        compute_salt_interaction,
    )
    from fiscal_model.models.state.database import STATE_NAMES, SUPPORTED_STATES

    db = StateTaxDatabase(year)
    states = []
    for code in SUPPORTED_STATES:
        p = db.get_state(code)
        curve = FederalStateCalculator(code, year).effective_rate_curve()
        lift = compute_salt_interaction(state=code, baseline_cap=10_000, reform_cap=None, db=db)
        states.append(
            {
                "code": code,
                "name": STATE_NAMES.get(code, code),
                "has_income_tax": bool(p.has_income_tax),
                "flat_rate": None if p.flat_rate is None else float(p.flat_rate),
                "top_rate": float(p.top_rate),
                "std_ded_single": float(p.std_ded_single or 0.0),
                "effective_salt_rate": float(p.effective_salt_rate),
                "pct_itemizers": float(p.pct_itemizers),
                "avg_salt_deduction_itemizers": float(p.avg_salt_deduction_itemizers),
                "median_household_income": float(p.median_household_income),
                "notes": str(p.notes or ""),
                "rate_curve": [
                    {
                        "agi": float(row["agi"]),
                        "federal_rate": float(row["federal_rate"]),
                        "state_rate": float(row["state_rate"]),
                        "combined_rate": float(row["combined_rate"]),
                    }
                    for _, row in curve.iterrows()
                ],
                "salt_cap_lift": {
                    "affected_filers_millions": float(lift.affected_filers),
                    "avg_deduction_change": float(lift.avg_deduction_change),
                    "federal_revenue_change_billions": float(lift.federal_revenue_change_billions),
                    "effective_rate_change_ppts": float(lift.effective_rate_change) * 100,
                },
            }
        )
    return {"year": year, "salt_cap_baseline": 10_000, "states": states}


__all__ = ["GROUPINGS", "distribution_view", "economic_view", "models_view", "states_view"]
