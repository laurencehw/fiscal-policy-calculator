"""
Calculation workflow helpers.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from . import session_keys as SK
from .controller_utils import render_input_guardrails, run_with_spinner_feedback

SINGLE_POLICY_MODE = "📊 Single Policy"
COMPARE_POLICIES_MODE = "🔀 Compare Policies"
POLICY_PACKAGES_MODE = "📦 Policy Packages"


def render_sidebar_inputs(st_module: Any, deps: Any) -> dict[str, Any]:
    """
    Render policy input controls in the sidebar and return interaction context.
    Note: the Calculate button is rendered separately in _render_calculator so
    that Model settings can appear above it.
    """
    # ── Workflow mode: single policy / compare / package ──────────────────
    workflow_mode = st_module.radio(
        "Workflow:",
        [SINGLE_POLICY_MODE, COMPARE_POLICIES_MODE, POLICY_PACKAGES_MODE],
        horizontal=False,
        help=(
            "**Single Policy** — score one tax or spending proposal.  \n"
            "**Compare Policies** — compare multiple proposals side-by-side.  \n"
            "**Policy Packages** — combine multiple proposals into one plan."
        ),
    )

    preset_policies = deps.PRESET_POLICIES
    if workflow_mode != SINGLE_POLICY_MODE:
        st_module.info(
            "Use the main tabs to configure this workflow. "
            "No single-policy inputs are required."
        )
        return {
            "mode": workflow_mode,
            "is_spending": False,
            "preset_policies": preset_policies,
            "tax_inputs": {},
            "spending_inputs": {},
            "calculate": False,
        }

    # ── Single-policy combined choice: preset / custom / spending ─────────
    analysis_mode = st_module.radio(
        "Analyze:",
        ["📋 Tax proposal (preset)", "✏️ Custom tax policy", "💰 Spending program"],
        horizontal=False,
        help=(
            "**Tax proposal** — pick from 25+ real-world policies calibrated to CBO/JCT estimates.  \n"
            "**Custom tax policy** — set your own rate change, threshold, and parameters.  \n"
            "**Spending program** — infrastructure, defense, transfers, etc."
        ),
    )
    is_spending = analysis_mode == "💰 Spending program"
    use_preset = analysis_mode == "📋 Tax proposal (preset)"

    tax_inputs: dict[str, Any] = {}
    spending_inputs: dict[str, Any] = {}

    # Support query param pre-selection
    query_params = getattr(st_module, "query_params", {})
    default_preset = query_params.get("policy") or query_params.get("preset")

    if is_spending:
        spending_inputs = deps.render_spending_policy_inputs(st_module)
    else:
        tax_inputs = deps.render_tax_policy_inputs(
            st_module, preset_policies, use_preset=use_preset, default_preset=default_preset
        )

    st_module.markdown("---")

    # Show input guardrails for tax policies
    if not is_spending and tax_inputs:
        render_input_guardrails(st_module=st_module, tax_inputs=tax_inputs)

    return {
        "mode": workflow_mode,
        "is_spending": is_spending,
        "preset_policies": preset_policies,
        "tax_inputs": tax_inputs,
        "spending_inputs": spending_inputs,
        "calculate": False,  # Set by caller after Model settings rendered
    }


def ensure_results_state(st_module: Any) -> None:
    """Initialize results slot in session state when missing."""
    if SK.RESULTS not in st_module.session_state:
        st_module.session_state[SK.RESULTS] = None


def execute_calculation_if_requested(
    st_module: Any,
    deps: Any,
    app_root: Path,
    model_available: bool,
    calc_context: dict[str, Any],
    settings: dict[str, Any],
) -> None:
    """Execute selected calculation branch and write to session state."""
    if calc_context.get("mode") != SINGLE_POLICY_MODE:
        return

    if not (calc_context["calculate"] and model_available):
        return

    run_id = calc_context.get("run_id")
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
            st_module.session_state[SK.RESULTS] = deps.run_microsim_calculation(
                preset_choice=tax_inputs.get("preset_choice", "Custom Policy"),
                base_dir=app_root,
                micro_tax_calculator_cls=deps.MicroTaxCalculator,
                synthetic_population_cls=deps.SyntheticPopulation,
                pd_module=deps.pd,
            )

        ok = run_with_spinner_feedback(
            st_module=st_module,
            spinner_message="Running microsimulation on individual tax units...",
            success_message="Microsimulation complete!",
            error_prefix="Microsimulation failed",
            action_fn=_run_microsim,
        )
        if ok and run_id:
            st_module.session_state[SK.LAST_RUN_ID] = run_id
            st_module.session_state[SK.RESULTS_RUN_ID] = run_id
            st_module.session_state[SK.LAST_RUN_AT] = time.time()
        return

    if is_spending:
        def _run_spending() -> None:
            st_module.session_state[SK.RESULTS] = deps.calculate_spending_policy_result(
                spending_inputs=spending_inputs,
                spending_policy_cls=deps.SpendingPolicy,
                policy_type_discretionary_nondefense=deps.PolicyType.DISCRETIONARY_NONDEFENSE,
                fiscal_policy_scorer_cls=deps.FiscalPolicyScorer,
                use_real_data=use_real_data,
                dynamic_scoring=dynamic_scoring,
            )

        ok = run_with_spinner_feedback(
            st_module=st_module,
            spinner_message="Calculating spending program impact...",
            success_message="Calculation complete!",
            error_prefix="Error calculating spending impact",
            action_fn=_run_spending,
        )
        if ok and run_id:
            st_module.session_state[SK.LAST_RUN_ID] = run_id
            st_module.session_state[SK.RESULTS_RUN_ID] = run_id
            st_module.session_state[SK.LAST_RUN_AT] = time.time()
        return

    def _run_tax() -> None:
        st_module.session_state[SK.RESULTS] = deps.calculate_tax_policy_result(
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

    ok = run_with_spinner_feedback(
        st_module=st_module,
        spinner_message="Scoring policy using IRS data and CBO methodology...",
        success_message="Calculation complete!",
        error_prefix="Error calculating policy impact",
        action_fn=_run_tax,
    )
    if ok and run_id:
        st_module.session_state[SK.LAST_RUN_ID] = run_id
        st_module.session_state[SK.RESULTS_RUN_ID] = run_id
        st_module.session_state[SK.LAST_RUN_AT] = time.time()
