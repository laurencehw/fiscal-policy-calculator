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


def olg_view(capital_tax_rate: float, payroll_tax_rate: float, replacement_rate: float) -> dict[str, Any]:
    """The app's Generational tab: a long-run OLG reform against the model's own baseline.

    The three rates are the tab's sliders, as fractions. The OLG model is
    separate from the scorer; its results are labelled wide-uncertainty.
    """
    from fiscal_model.models.olg import OLGModel, OLGParameters

    params = OLGParameters()
    baseline_rates = {
        "tau_k": params.capital_tax_rate,
        "tau_ss": params.ss_payroll_rate,
        "ss_replacement_rate": params.ss_replacement_rate,
    }
    asked = {"tau_k": capital_tax_rate, "tau_ss": payroll_tax_rate, "ss_replacement_rate": replacement_rate}
    overrides = {k: v for k, v in asked.items() if abs(v - baseline_rates[k]) > 0.001}
    common = {
        "baseline_rates": {
            "capital_tax_rate": params.capital_tax_rate,
            "payroll_tax_rate": params.ss_payroll_rate,
            "replacement_rate": params.ss_replacement_rate,
        },
        "rates": {
            "capital_tax_rate": capital_tax_rate,
            "payroll_tax_rate": payroll_tax_rate,
            "replacement_rate": replacement_rate,
        },
    }
    if not overrides:
        return {**common, "changed": False}
    r = OLGModel(params).analyze_policy(
        reform_overrides=overrides,
        policy_name="OLG reform",
        compute_gen_accounts=True,
        compute_transition=True,
        start_year=2026,
    )
    import math

    def finite(values: Any) -> list[float | None]:
        # JSON has no NaN; an unsolved year is a gap in the chart, not a zero.
        return [float(v) if math.isfinite(float(v)) else None for v in values]

    t, base = r.transition, r.baseline
    gdp_path = r.gdp_transition_pct_change()
    # The transition should settle at the reform's steady state. When it does
    # not, the path is the solver's and not the model's answer, so say so.
    path_end = float(gdp_path[-1]) if len(gdp_path) else float("nan")
    settles = math.isfinite(path_end) and abs(path_end - float(r.long_run_gdp_pct_change)) <= 1.0
    ga = r.gen_accounts
    accounts = None
    if ga is not None:
        frame = ga.to_dataframe()
        accounts = {
            "newborn_burden_change": float(ga.newborn_burden_change),
            "weighted_burden_change": float(ga.weighted_burden_change()),
            "generational_imbalance": float(ga.generational_imbalance),
            "by_age": [
                {
                    "age": int(row["age"]),
                    "baseline": float(row["baseline_burden"]),
                    "reform": float(row["reform_burden"]),
                    "change": float(row["burden_change"]),
                }
                for _, row in frame.iterrows()
            ],
        }
    return {
        **common,
        "changed": True,
        "converged": r.reform.status.value == "converged",
        "solver_status": r.reform.status.value,
        "confidence_label": r.confidence_label,
        "long_run": {
            "gdp_pct": float(r.long_run_gdp_pct_change),
            "capital_pct": float(r.long_run_capital_pct_change),
            "wage_pct": float(r.long_run_wage_pct_change),
            "interest_rate_ppts": float(r.long_run_interest_rate_change),
            "capital_output_baseline": float(r.baseline.capital_output_ratio),
            "capital_output_reform": float(r.reform.capital_output_ratio),
        },
        "year_30_gdp_pct": float(r.year_30_gdp_effect()),
        "years": [int(y) for y in t.years],
        "gdp_path_pct": finite(gdp_path),
        "path_settles": settles,
        "path_end_gdp_pct": path_end if math.isfinite(path_end) else None,
        "capital_path_pct": finite((t.K_path - base.K) / max(base.K, 1e-10) * 100.0),
        "interest_path_ppts": finite((t.r_path - base.r) * 100.0),
        "accounts": accounts,
    }


__all__ = ["GROUPINGS", "distribution_view", "economic_view", "models_view", "olg_view", "states_view"]
