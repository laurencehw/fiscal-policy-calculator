"""
Policy execution helpers for the single-policy calculation paths.

This module owns the *one* point where a run completes. Everything a result
surface needs is assembled here — including the macro "dynamic view" — so that
the headline, Key Metrics, the Economic Effects tab, Copy Summary and the CSV
export cannot disagree (``planning/redesign/NOTES.md`` §4.4).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fiscal_model.baseline import APP_DEFAULT_START_YEAR

logger = logging.getLogger(__name__)


def run_dynamic_view(
    *,
    policy: Any,
    result: Any,
    is_spending: bool,
    macro_model_name: str | None,
    macro_scenario_cls: Any,
    frbus_adapter_lite_cls: Any,
    simple_multiplier_adapter_cls: Any,
    build_macro_scenario_fn: Any,
) -> tuple[Any, Any]:
    """Run the macro adapter once and return ``(DynamicView, MacroResult)``.

    Called from :func:`~fiscal_model.ui.calculation_controller.
    execute_calculation_if_requested` when dynamic scoring is on. The result is
    stashed on the run so the Economic Effects tab, the Results headline panel
    and the exports all read identical numbers from one adapter run rather than
    each estimating feedback their own way.

    Returns ``(None, None)`` if the adapter fails — a broken macro model must
    degrade the dynamic view, never the conventional score.
    """
    from .tabs.dynamic_scoring import compute_dynamic_view, resolve_macro_adapter

    try:
        scenario = build_macro_scenario_fn(
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
    except Exception:  # pragma: no cover — defensive; adapters are unit-tested
        logger.exception("Dynamic view computation failed for %r", getattr(policy, "name", "?"))
        return None, None


def run_microsim_calculation(
    preset_choice: str,
    base_dir: Path,
    micro_tax_calculator_cls: Any,
    synthetic_population_cls: Any,
    pd_module: Any,
) -> dict[str, Any]:
    """
    Run microsimulation flow and return normalized session-state results.
    """
    data_path = base_dir / "fiscal_model" / "microsim" / "tax_microdata_2024.csv"
    if data_path.exists():
        population = pd_module.read_csv(data_path)
        source_msg = "Using **Real CPS ASEC 2024** Microdata"
    else:
        pop_gen = synthetic_population_cls(size=100_000)
        population = pop_gen.generate()
        source_msg = "Using **Synthetic** Microdata (Real data not found)"

    calc = micro_tax_calculator_cls()

    def reform_func(c):
        # Prototype reform path: currently CTC expansion demo.
        if "CTC" in preset_choice:
            c.ctc_amount = 4000
        else:
            c.ctc_amount = 4000

    baseline = calc.calculate(population)
    reform = calc.run_reform(population, reform_func)

    baseline_rev = (baseline["final_tax"] * baseline["weight"]).sum() / 1e9
    reform_rev = (reform["final_tax"] * reform["weight"]).sum() / 1e9
    rev_change = reform_rev - baseline_rev

    merged = baseline.copy(deep=True)
    merged.loc[:, "reform_tax"] = reform["final_tax"].to_numpy()
    merged.loc[:, "tax_change"] = merged["reform_tax"] - merged["final_tax"]

    weighted = merged.assign(weighted_tax_change=merged["tax_change"] * merged["weight"])
    dist_kids = weighted.groupby("children", as_index=False).agg(
        total_weighted_tax_change=("weighted_tax_change", "sum"),
        total_weight=("weight", "sum"),
    )
    dist_kids.loc[:, "avg_tax_change"] = dist_kids["total_weighted_tax_change"] / dist_kids["total_weight"]
    dist_kids = dist_kids[["children", "avg_tax_change"]]

    return {
        "is_microsim": True,
        "revenue_change_billions": rev_change,
        "baseline_revenue": baseline_rev,
        "reform_revenue": reform_rev,
        "distribution_kids": dist_kids,
        "source_msg": source_msg,
        "policy_name": preset_choice if preset_choice != "Custom Policy" else "Microsim Reform",
    }


def calculate_tax_policy_result(
    *,
    preset_policies: dict[str, dict[str, Any]],
    preset_choice: str,
    create_policy_from_preset_fn: Any,
    dynamic_scoring: bool,
    use_real_data: bool,
    fiscal_policy_scorer_cls: Any,
    tax_policy_cls: Any,
    capital_gains_policy_cls: Any,
    policy_type_cls: Any,
    policy_type: str,
    policy_name: str,
    rate_change_pct: float,
    rate_change: float,
    threshold: int,
    data_year: int,
    duration: int,
    phase_in: int,
    eti: float,
    ordinary_income_base: bool,
    manual_taxpayers: float,
    manual_avg_income: float,
    cg_base_year: int,
    baseline_cg_rate: float,
    baseline_realizations: float,
    realization_elasticity: float,
    persistent_elasticity: float,
    transitory_elasticity: float,
    use_time_varying: bool,
    eliminate_step_up: bool,
    step_up_exemption: float,
) -> dict[str, Any]:
    """
    Build and score a tax policy from UI inputs and preset metadata.
    """
    preset_data = preset_policies[preset_choice]
    policy = create_policy_from_preset_fn(preset_data)

    if policy:
        # ``create_policy_from_preset`` has already moved the policy onto the
        # app window, so this is APP_DEFAULT_START_YEAR for every preset that
        # states no later year of its own. The ``max`` is the belt: a scorer
        # window that opened before the policy would cost the run a year.
        start_year = max(
            int(getattr(policy, "start_year", APP_DEFAULT_START_YEAR)),
            APP_DEFAULT_START_YEAR,
        )
        scorer = fiscal_policy_scorer_cls(start_year=start_year, use_real_data=False)
        result = scorer.score_policy(policy, dynamic=dynamic_scoring)

        return {
            "policy": policy,
            "result": result,
            "scorer": scorer,
            "is_spending": False,
            "policy_name": preset_choice,
            **preset_data,
        }

    policy_type_map = {
        "Income Tax Rate": policy_type_cls.INCOME_TAX,
        "Capital Gains": policy_type_cls.CAPITAL_GAINS_TAX,
        "Corporate Tax": policy_type_cls.CORPORATE_TAX,
        "Payroll Tax": policy_type_cls.PAYROLL_TAX,
    }
    mapped_type = policy_type_map.get(policy_type, policy_type_cls.INCOME_TAX)

    if policy_type == "Capital Gains":
        description = f"{rate_change_pct:+.1f}pp capital gains rate change for AGI >= ${threshold:,}"
        if eliminate_step_up:
            description += " + eliminate step-up basis"

        policy = capital_gains_policy_cls(
            name=policy_name,
            description=description,
            policy_type=mapped_type,
            rate_change=rate_change,
            affected_income_threshold=threshold,
            data_year=int(cg_base_year),
            start_year=APP_DEFAULT_START_YEAR,
            duration_years=duration,
            phase_in_years=max(1, int(phase_in)),
            baseline_capital_gains_rate=float(baseline_cg_rate),
            baseline_realizations_billions=float(baseline_realizations),
            realization_elasticity=float(realization_elasticity),
            persistent_elasticity=float(persistent_elasticity),
            transitory_elasticity=float(transitory_elasticity),
            use_time_varying_elasticity=use_time_varying,
            step_up_at_death=True,
            eliminate_step_up=eliminate_step_up,
            step_up_exemption=float(step_up_exemption),
        )

        if baseline_realizations <= 0:
            policy.baseline_realizations_billions = 0.0
            policy.baseline_capital_gains_rate = 0.0
    elif policy_type == "Corporate Tax":
        # A bare TaxPolicy with policy_type=CORPORATE_TAX runs the individual
        # income-tax base and scores 21%->28% at -$1,855B (37% off Treasury's
        # -$1,347B). CorporateTaxPolicy is driven by the rate alone and lands
        # at -$1,397B (3.7%), so the Tailor "Corporate" option routes here.
        # There is no income threshold on the corporate base, so the
        # "who is affected" control does not apply.
        from fiscal_model.corporate import CorporateTaxPolicy

        policy = CorporateTaxPolicy(
            name=policy_name,
            description=f"{rate_change_pct:+.1f}pp corporate rate change",
            policy_type=policy_type_cls.CORPORATE_TAX,
            rate_change=rate_change,
            start_year=APP_DEFAULT_START_YEAR,
            duration_years=duration,
            phase_in_years=max(1, int(phase_in)),
            corporate_elasticity=eti if eti > 0 else 0.25,
        )
    else:
        policy = tax_policy_cls(
            name=policy_name,
            description=f"{rate_change_pct:+.1f}pp tax rate change for AGI >= ${threshold:,}",
            policy_type=mapped_type,
            rate_change=rate_change,
            affected_income_threshold=threshold,
            data_year=data_year,
            start_year=APP_DEFAULT_START_YEAR,
            duration_years=duration,
            phase_in_years=max(1, int(phase_in)),
            taxable_income_elasticity=eti,
            ordinary_income_base=ordinary_income_base,
        )

    # Only the individual-base paths take a taxpayer count / average income;
    # capital gains scores off realizations and corporate off profits.
    if policy_type in ("Income Tax Rate", "Payroll Tax"):
        if manual_taxpayers > 0:
            policy.affected_taxpayers_millions = manual_taxpayers
        if manual_avg_income > 0:
            policy.avg_taxable_income_in_bracket = manual_avg_income

    scorer = fiscal_policy_scorer_cls(
        baseline=None, start_year=APP_DEFAULT_START_YEAR, use_real_data=use_real_data
    )
    result = scorer.score_policy(policy, dynamic=dynamic_scoring)

    return {
        "policy": policy,
        "result": result,
        "scorer": scorer,
        "is_spending": False,
        "is_tcja": False,
        "policy_name": preset_choice,
    }
