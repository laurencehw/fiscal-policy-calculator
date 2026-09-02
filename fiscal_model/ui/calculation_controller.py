"""
Calculation workflow helpers.
"""

from __future__ import annotations

import contextlib
import logging
import time
from pathlib import Path
from typing import Any

from .controller_utils import render_input_guardrails, run_with_spinner_feedback
from .share_links import apply_share_query_params

logger = logging.getLogger(__name__)

SINGLE_POLICY_MODE = "📊 Single Policy"
COMPARE_POLICIES_MODE = "🔀 Compare Policies"
POLICY_PACKAGES_MODE = "📦 Policy Packages"

# Analysis modes. These literals are the stored value of the
# ``sidebar_analysis_mode`` widget key and are written by share links
# (``ui/share_links.py``) and quick-start cards, so they must not change.
PRESET_ANALYSIS_MODE = "📋 Tax proposal (preset)"
CUSTOM_ANALYSIS_MODE = "✏️ Custom tax policy"
SPENDING_ANALYSIS_MODE = "💰 Spending program"
ALL_ANALYSIS_MODES: tuple[str, ...] = (
    PRESET_ANALYSIS_MODE,
    CUSTOM_ANALYSIS_MODE,
    SPENDING_ANALYSIS_MODE,
)

_ANALYSIS_MODE_KEY = "sidebar_analysis_mode"


def render_policy_inputs(
    st_module: Any,
    deps: Any,
    modes: tuple[str, ...] = ALL_ANALYSIS_MODES,
    tax_input_kwargs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Render policy input controls and return interaction context.

    ``modes`` is the subset of analysis modes this surface offers. The redesign
    splits them across two pages — ``/explore`` offers the preset flow only and
    ``/tailor`` offers custom + spending — so a single-entry ``modes`` renders no
    radio at all. The Calculate button is rendered by the caller so page-level
    layout stays with the page.
    """
    if not modes:
        raise ValueError("render_policy_inputs requires at least one analysis mode")

    workflow_mode = SINGLE_POLICY_MODE
    preset_policies = deps.PRESET_POLICIES
    apply_share_query_params(st_module=st_module)

    # ── Single-policy combined choice: preset / custom / spending ─────────
    if len(modes) == 1:
        analysis_mode = modes[0]
    else:
        # A share link or quick-start card may have primed the key with a mode
        # this page does not offer (e.g. "preset" while on /tailor). Evict it
        # rather than let Streamlit reject an out-of-range widget value — same
        # pattern the preset pickers use for stale selections.
        #
        # ``None`` is evicted too: ``initialize_session_state`` seeds this key
        # with ``None``, and a radio whose session value is ``None`` renders
        # with *nothing selected*. Dropping it lets the widget fall back to
        # index 0, which is the mode the page then scores anyway.
        stored_mode = st_module.session_state.get(_ANALYSIS_MODE_KEY)
        if stored_mode not in modes:
            st_module.session_state.pop(_ANALYSIS_MODE_KEY, None)

        n_presets = sum(1 for name in preset_policies if name != "Custom Policy")
        analysis_mode = st_module.radio(
            "Analyze:",
            list(modes),
            horizontal=False,
            key=_ANALYSIS_MODE_KEY,
            help=(
                f"**Tax proposal** — pick from {n_presets} real-world policies, "
                "benchmarked against CBO/JCT estimates where official scores exist.  \n"
                "**Custom tax policy** — set your own rate change, threshold, and parameters.  \n"
                "**Spending program** — infrastructure, defense, transfers, etc."
            ),
        )
    is_spending = analysis_mode == SPENDING_ANALYSIS_MODE
    use_preset = analysis_mode == PRESET_ANALYSIS_MODE

    tax_inputs: dict[str, Any] = {}
    spending_inputs: dict[str, Any] = {}

    # Support query param or quick-start card pre-selection
    query_params = getattr(st_module, "query_params", {})
    default_preset = (
        query_params.get("policy")
        or query_params.get("preset")
        or getattr(st_module.session_state, "qs_preset", None)
    )
    default_spending_preset = query_params.get("spending_preset")

    if is_spending:
        spending_inputs = deps.render_spending_policy_inputs(
            st_module,
            default_preset=default_spending_preset,
        )
    else:
        # ``tax_input_kwargs`` lets a page turn off a control it renders itself
        # (Tailor owns the policy-type chips), without a second widget on the
        # same session key.
        tax_inputs = deps.render_tax_policy_inputs(
            st_module,
            preset_policies,
            use_preset=use_preset,
            default_preset=default_preset,
            **(tax_input_kwargs or {}),
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


def render_sidebar_inputs(st_module: Any, deps: Any) -> dict[str, Any]:
    """Back-compat alias for :func:`render_policy_inputs` with all modes.

    The global sidebar is gone; the name survives because it is part of the
    public ``fiscal_model.ui`` surface and is exercised by the UI test suite.
    """
    return render_policy_inputs(st_module=st_module, deps=deps)


def ensure_results_state(st_module: Any) -> None:
    """Initialize results slot in session state when missing."""
    if "results" not in st_module.session_state:
        st_module.session_state.results = None


def _record_run_outcome(st_module: Any, ok: bool, run_id: str | None) -> None:
    """Persist run bookkeeping, discarding stale results after a failed run.

    Without the failure branch, an errored calculation leaves the previous
    policy's results rendered under the error message — easy to misread as
    the new policy's answer.
    """
    if ok:
        if run_id:
            st_module.session_state.last_run_id = run_id
            st_module.session_state.results_run_id = run_id
            st_module.session_state.last_run_at = time.time()
        return
    st_module.session_state.results = None
    st_module.session_state.results_run_id = None
    _store_scored_result(st_module, None)


def _store_scored_result(st_module: Any, scored: Any) -> None:
    """Write the single result object, tolerating stripped-down session fakes."""
    try:
        from components.results import store_scored_result

        store_scored_result(st_module, scored)
    except Exception:  # pragma: no cover — components/ absent (library-only use)
        with contextlib.suppress(Exception):
            st_module.session_state["scored_result"] = scored


def _finalize_run(
    st_module: Any,
    deps: Any,
    ok: bool,
    calc_context: dict[str, Any],
    settings: dict[str, Any],
) -> None:
    """Record the run and publish its :class:`ScoredResult` — one place, once."""
    _record_run_outcome(st_module, ok, calc_context.get("run_id"))
    if not ok:
        return
    _store_scored_result(
        st_module, build_scored_result(st_module, deps, calc_context, settings)
    )


def build_scored_result(
    st_module: Any,
    deps: Any,
    calc_context: dict[str, Any],
    settings: dict[str, Any],
) -> Any:
    """Assemble the single result object at the one point a run completes.

    Runs the macro adapter exactly once when dynamic scoring is on, so the
    Results panel, the Economic Effects tab and every export quote the *same*
    feedback and debt-service numbers (``planning/redesign/NOTES.md`` §4.4).
    Failure is non-fatal: the raw ``results`` dict is still usable, the panel
    just falls back to its invalidation notice.
    """
    result_data = st_module.session_state.get("results")
    if not result_data or result_data.get("is_microsim"):
        return None

    try:
        from components.results import ScoredResult, resolve_baseline_vintage

        dynamic_view = None
        if settings.get("dynamic_scoring"):
            from .policy_execution import run_dynamic_view

            dynamic_view, macro_result = run_dynamic_view(
                policy=result_data["policy"],
                result=result_data["result"],
                is_spending=bool(result_data.get("is_spending", False)),
                macro_model_name=settings.get("macro_model"),
                macro_scenario_cls=deps.MacroScenario,
                frbus_adapter_lite_cls=deps.FRBUSAdapterLite,
                simple_multiplier_adapter_cls=deps.SimpleMultiplierAdapter,
                build_macro_scenario_fn=deps.build_macro_scenario,
            )
            # Prime the Economic Effects tab's cache with this exact run so the
            # tab does not re-run (and possibly re-estimate) the same scenario.
            run_id = calc_context.get("run_id")
            if macro_result is not None and run_id:
                st_module.session_state[f"macro:{run_id}:{settings.get('macro_model')}"] = (
                    macro_result
                )

        return ScoredResult.from_pipeline(
            result_data=result_data,
            policy_spec_hash=str(calc_context.get("run_id") or ""),
            dynamic_scoring=bool(settings.get("dynamic_scoring")),
            dynamic_view=dynamic_view,
            cbo_score_map=getattr(deps, "CBO_SCORE_MAP", None),
            baseline_vintage=resolve_baseline_vintage(),
        )
    except Exception:
        logger.exception("Could not build the ScoredResult for this run")
        return None


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

        ok = run_with_spinner_feedback(
            st_module=st_module,
            spinner_message="Running microsimulation on individual tax units...",
            success_message="Microsimulation complete!",
            error_prefix="Microsimulation failed",
            action_fn=_run_microsim,
        )
        _finalize_run(st_module, deps, ok, calc_context, settings)
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

        ok = run_with_spinner_feedback(
            st_module=st_module,
            spinner_message="Calculating spending program impact...",
            success_message="Calculation complete!",
            error_prefix="Error calculating spending impact",
            action_fn=_run_spending,
        )
        _finalize_run(st_module, deps, ok, calc_context, settings)
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
            ordinary_income_base=bool(tax_inputs.get("ordinary_income_base", True)),
            manual_taxpayers=tax_inputs["manual_taxpayers"],
            manual_avg_income=tax_inputs["manual_avg_income"],
            cg_base_year=tax_inputs["cg_base_year"],
            baseline_cg_rate=float(tax_inputs["baseline_cg_rate"]),
            baseline_realizations=float(tax_inputs["baseline_realizations"]),
            realization_elasticity=float(tax_inputs["realization_elasticity"]),
            persistent_elasticity=float(tax_inputs["persistent_elasticity"]),
            transitory_elasticity=float(tax_inputs["transitory_elasticity"]),
            use_time_varying=bool(tax_inputs["use_time_varying"]),
            eliminate_step_up=bool(tax_inputs["eliminate_step_up"]),
            step_up_exemption=float(tax_inputs["step_up_exemption"]),
        )

    ok = run_with_spinner_feedback(
        st_module=st_module,
        spinner_message="Scoring policy using IRS data and CBO methodology...",
        success_message="Calculation complete!",
        error_prefix="Error calculating policy impact",
        action_fn=_run_tax,
    )
    _finalize_run(st_module, deps, ok, calc_context, settings)
