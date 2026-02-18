"""
Calculation workflow helpers.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .controller_utils import run_with_spinner_feedback


def render_sidebar_inputs(st_module: Any, deps: Any) -> dict[str, Any]:
    """
    Render policy input controls in the sidebar and return interaction context.
    """
    policy_category = st_module.radio(
        "Select policy type",
        ["💰 Tax Policy", "📊 Spending Policy"],
        horizontal=True,
        help="Choose whether to analyze tax changes or spending programs",
    )
    is_spending = policy_category == "📊 Spending Policy"

    preset_policies = deps.PRESET_POLICIES
    tax_inputs: dict[str, Any] = {}
    spending_inputs: dict[str, Any] = {}
    
    if not is_spending:
        tax_inputs = deps.render_tax_policy_inputs(st_module, preset_policies)
    else:
        spending_inputs = deps.render_spending_policy_inputs(st_module)

    st_module.markdown("---")
    
    # Calculate button is primary action
    calculate = st_module.button("🚀 Calculate Impact", type="primary", use_container_width=True)
    
    # Reset button
    if st_module.button("🔄 Reset", use_container_width=True):
        st_module.rerun()

    return {
        "is_spending": is_spending,
        "preset_policies": preset_policies,
        "tax_inputs": tax_inputs,
        "spending_inputs": spending_inputs,
        "calculate": calculate,
    }


def ensure_results_state(st_module: Any) -> None:
    """
    Initialize results slot in session state when missing.
    """
    if "results" not in st_module.session_state:
        st_module.session_state.results = None


def execute_calculation_if_requested(
    st_module: Any,
    deps: Any,
    app_root: Path,
    model_available: bool,
    calc_context: dict[str, Any],
    settings: dict[str, Any],
) -> None:
    """
    Execute selected calculation branch and write to session state.
    """
    if not (calc_context["calculate"] and model_available):
        return

    is_spending = calc_context["is_spending"]
    preset_policies = calc_context["preset_policies"]
    tax_inputs = calc_context["tax_inputs"]
    spending_inputs = calc_context["spending_inputs"]

    dynamic_scoring = settings["dynamic_scoring"]
    use_real_data = settings["use_real_data"]
    use_microsim = settings["use_microsim"]
    data_year = settings["data_year"]

    if use_microsim:
        def _run_microsim() -> None:
                st_module.session_state.results = deps.run_microsim_calculation(
                    preset_choice=tax_inputs.get("preset_choice", "Custom Policy"),
                    base_dir=app_root,
                    micro_tax_calculator_cls=deps.MicroTaxCalculator,
                    synthetic_population_cls=deps.SyntheticPopulation,
                    pd_module=deps.pd,
                )

        run_with_spinner_feedback(
            st_module=st_module,
            spinner_message="Running microsimulation on individual tax units...",
            success_message="✅ Microsimulation complete!",
            error_prefix="❌ Microsimulation failed",
            action_fn=_run_microsim,
        )
        return

    if is_spending:
        def _run_spending() -> None:
                st_module.session_state.results = deps.calculate_spending_policy_result(
                    spending_inputs=spending_inputs,
                    spending_policy_cls=deps.SpendingPolicy,
                    policy_type_discretionary_nondefense=deps.PolicyType.DISCRETIONARY_NONDEFENSE,
                    fiscal_policy_scorer_cls=deps.FiscalPolicyScorer,
                    use_real_data=use_real_data,
                    dynamic_scoring=dynamic_scoring,
                )

        run_with_spinner_feedback(
            st_module=st_module,
            spinner_message="Calculating spending program impact...",
            success_message="✅ Calculation complete!",
            error_prefix="❌ Error calculating spending impact",
            action_fn=_run_spending,
        )
        return

    def _run_tax() -> None:
            st_module.session_state.results = deps.calculate_tax_policy_result(
                preset_policies=preset_policies,
                preset_choice=tax_inputs["preset_choice"],
                create_policy_from_preset_fn=deps.create_policy_from_preset,
                dynamic_scoring=dynamic_scoring,
                use_real_data=use_real_data,
                fiscal_policy_scorer_cls=deps.FiscalPolicyScorer,
                tax_policy_cls=deps.TaxPolicy,
                capital_gains_policy_cls=deps.CapitalGainsPolicy,
                policy_type_cls=deps.PolicyType,
                policy_type=tax_inputs["policy_type"],
                policy_name=tax_inputs["policy_name"],
                rate_change_pct=tax_inputs["rate_change_pct"],
                rate_change=tax_inputs["rate_change"],
                threshold=tax_inputs["threshold"],
                data_year=data_year,
                duration=tax_inputs["duration"],
                phase_in=tax_inputs["phase_in"],
                eti=tax_inputs["eti"],
                manual_taxpayers=tax_inputs["manual_taxpayers"],
                manual_avg_income=tax_inputs["manual_avg_income"],
                cg_base_year=tax_inputs["cg_base_year"],
                baseline_cg_rate=float(tax_inputs["baseline_cg_rate"]),
                baseline_realizations=float(tax_inputs["baseline_realizations"]),
                realization_elasticity=float(tax_inputs["realization_elasticity"]),
                short_run_elasticity=float(tax_inputs["short_run_elasticity"]),
                long_run_elasticity=float(tax_inputs["long_run_elasticity"]),
                transition_years=int(tax_inputs["transition_years"]),
                use_time_varying=bool(tax_inputs["use_time_varying"]),
                eliminate_step_up=bool(tax_inputs["eliminate_step_up"]),
                step_up_exemption=float(tax_inputs["step_up_exemption"]),
                gains_at_death=float(tax_inputs["gains_at_death"]),
                step_up_lock_in_multiplier=float(tax_inputs["step_up_lock_in_multiplier"]),
            )

    run_with_spinner_feedback(
        st_module=st_module,
        spinner_message="Calculating policy impact using real IRS data...",
        success_message="✅ Calculation complete!",
        error_prefix="❌ Error calculating policy impact",
        action_fn=_run_tax,
    )
