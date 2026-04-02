"""
Smoke tests for UI controllers and stale-run behavior.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from fiscal_model.ui.calculation_controller import (
    COMPARE_POLICIES_MODE,
    POLICY_PACKAGES_MODE,
    SINGLE_POLICY_MODE,
    execute_calculation_if_requested,
    render_sidebar_inputs,
)
from fiscal_model.ui.tabs_controller import render_result_tabs


class _DummyContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        del exc_type, exc, tb
        return False


class _DummyStreamlit:
    def __init__(self, radio_values: list[str]) -> None:
        self._radio_values = list(radio_values)
        self.session_state = SimpleNamespace(results=None)
        self.warnings: list[str] = []
        self.infos: list[str] = []

    def radio(self, *args, **kwargs):
        del args, kwargs
        return self._radio_values.pop(0)

    def markdown(self, *args, **kwargs):
        del args, kwargs
        return None

    def info(self, message: str, *args, **kwargs):
        del args, kwargs
        self.infos.append(message)

    def warning(self, message: str, *args, **kwargs):
        del args, kwargs
        self.warnings.append(message)

    def success(self, *args, **kwargs):
        del args, kwargs
        return None

    def error(self, *args, **kwargs):
        del args, kwargs
        return None

    def spinner(self, *args, **kwargs):
        del args, kwargs
        return _DummyContext()

    def subheader(self, *args, **kwargs):
        del args, kwargs
        return None

    def caption(self, *args, **kwargs):
        del args, kwargs
        return None


def test_render_sidebar_inputs_compare_mode_short_circuits():
    st_module = _DummyStreamlit(radio_values=[COMPARE_POLICIES_MODE])
    deps = SimpleNamespace(
        PRESET_POLICIES={"Custom Policy": {}},
        render_tax_policy_inputs=lambda *args, **kwargs: {"unused": True},
        render_spending_policy_inputs=lambda *args, **kwargs: {"unused": True},
    )

    context = render_sidebar_inputs(st_module=st_module, deps=deps)
    assert context["mode"] == COMPARE_POLICIES_MODE
    assert context["is_spending"] is False
    assert context["tax_inputs"] == {}
    assert context["spending_inputs"] == {}


def test_render_sidebar_inputs_single_mode_uses_tax_inputs():
    st_module = _DummyStreamlit(
        radio_values=[SINGLE_POLICY_MODE, "📋 Tax proposal (preset)"]
    )
    deps = SimpleNamespace(
        PRESET_POLICIES={"Custom Policy": {}},
        render_tax_policy_inputs=lambda *args, **kwargs: {"preset_choice": "Custom Policy"},
        render_spending_policy_inputs=lambda *args, **kwargs: {"program_name": "Infra"},
    )

    context = render_sidebar_inputs(st_module=st_module, deps=deps)
    assert context["mode"] == SINGLE_POLICY_MODE
    assert context["is_spending"] is False
    assert context["tax_inputs"]["preset_choice"] == "Custom Policy"


def test_execute_calculation_non_single_mode_does_not_run(monkeypatch):
    st_module = _DummyStreamlit(radio_values=[])
    st_module.session_state.results = None

    deps = SimpleNamespace(
        calculate_tax_policy_result=lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("Should not run in non-single mode")
        ),
        calculate_spending_policy_result=lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("Should not run in non-single mode")
        ),
        run_microsim_calculation=lambda **kwargs: (_ for _ in ()).throw(
            AssertionError("Should not run in non-single mode")
        ),
    )

    calc_context = {
        "mode": POLICY_PACKAGES_MODE,
        "calculate": True,
        "run_id": "abc123",
        "is_spending": False,
        "preset_policies": {},
        "tax_inputs": {},
        "spending_inputs": {},
    }
    settings = {"dynamic_scoring": False, "use_real_data": True, "use_microsim": False, "data_year": 2022}

    execute_calculation_if_requested(
        st_module=st_module,
        deps=deps,
        app_root=Path("."),
        model_available=True,
        calc_context=calc_context,
        settings=settings,
    )
    assert st_module.session_state.results is None


def test_execute_calculation_single_mode_updates_run_state(monkeypatch):
    st_module = _DummyStreamlit(radio_values=[])
    st_module.session_state.results = None

    monkeypatch.setattr(
        "fiscal_model.ui.calculation_controller.run_with_spinner_feedback",
        lambda st_module, spinner_message, success_message, error_prefix, action_fn: (
            action_fn() or True
        ),
    )

    deps = SimpleNamespace(
        create_policy_from_preset=lambda preset: preset,
        FiscalPolicyScorer=object,
        TaxPolicy=object,
        CapitalGainsPolicy=object,
        PolicyType=SimpleNamespace(DISCRETIONARY_NONDEFENSE="disc"),
        calculate_tax_policy_result=lambda **kwargs: {"policy": object(), "result": object()},
    )

    calc_context = {
        "mode": SINGLE_POLICY_MODE,
        "calculate": True,
        "run_id": "run-1",
        "is_spending": False,
        "preset_policies": {"Custom Policy": {}},
        "tax_inputs": {
            "preset_choice": "Custom Policy",
            "policy_type": "Income Tax Rate",
            "policy_name": "Custom Policy",
            "rate_change_pct": 1.0,
            "rate_change": 0.01,
            "threshold": 400000,
            "duration": 10,
            "phase_in": 0,
            "eti": 0.25,
            "manual_taxpayers": 1.0,
            "manual_avg_income": 500000.0,
            "cg_base_year": 2024,
            "baseline_cg_rate": 0.2,
            "baseline_realizations": 0.0,
            "realization_elasticity": 0.5,
            "short_run_elasticity": 0.8,
            "long_run_elasticity": 0.4,
            "transition_years": 3,
            "use_time_varying": True,
            "eliminate_step_up": False,
            "step_up_exemption": 1000000.0,
            "gains_at_death": 54.0,
            "step_up_lock_in_multiplier": 2.0,
        },
        "spending_inputs": {},
    }
    settings = {
        "dynamic_scoring": False,
        "use_real_data": True,
        "use_microsim": False,
        "data_year": 2022,
    }

    execute_calculation_if_requested(
        st_module=st_module,
        deps=deps,
        app_root=Path("."),
        model_available=True,
        calc_context=calc_context,
        settings=settings,
    )

    assert st_module.session_state.results is not None
    assert st_module.session_state.results_run_id == "run-1"
    assert st_module.session_state.last_run_id == "run-1"


def test_render_result_tabs_shows_stale_warnings():
    st_module = _DummyStreamlit(radio_values=[])
    st_module.session_state = SimpleNamespace(
        results={"policy": object()},
        current_run_id="current",
        results_run_id="prior",
        last_run_id="prior",
    )

    deps = SimpleNamespace(
        CBO_SCORE_MAP={},
        PRESET_POLICIES={},
        PRESET_POLICY_PACKAGES={},
        PolicyType=SimpleNamespace(INCOME_TAX="income_tax"),
        FiscalPolicyScorer=object,
        TaxPolicy=object,
        create_policy_from_preset=lambda x: x,
        DistributionalEngine=object,
        IncomeGroupType=object,
        format_distribution_table=lambda *args, **kwargs: None,
        generate_winners_losers_summary=lambda *args, **kwargs: None,
        MacroScenario=object,
        FRBUSAdapterLite=object,
        SimpleMultiplierAdapter=object,
        SolowGrowthModel=object,
        build_macro_scenario=lambda *args, **kwargs: None,
        render_results_summary_tab=lambda **kwargs: None,
        render_distribution_tab=lambda **kwargs: None,
        render_dynamic_scoring_tab=lambda **kwargs: None,
        render_detailed_results_tab=lambda **kwargs: None,
        render_long_run_growth_tab=lambda **kwargs: None,
        render_policy_comparison_tab=lambda **kwargs: None,
        render_policy_package_tab=lambda **kwargs: None,
    )
    tabs = {
        "tab_summary": _DummyContext(),
        "tab_distribution": _DummyContext(),
        "tab_dynamic": _DummyContext(),
        "tab_details": _DummyContext(),
        "tab_long_run": _DummyContext(),
        "tab_comparison": _DummyContext(),
        "tab_packages": _DummyContext(),
    }
    settings = {
        "dynamic_scoring": False,
        "macro_model": "FRBUSAdapterLite",
        "data_year": 2022,
        "use_real_data": True,
        "use_microsim_distribution": False,
    }

    render_result_tabs(
        st_module=st_module,
        deps=deps,
        tabs=tabs,
        settings=settings,
        model_available=True,
        is_spending=False,
        mode=SINGLE_POLICY_MODE,
    )

    assert any("Inputs changed since the last run" in msg for msg in st_module.warnings)
