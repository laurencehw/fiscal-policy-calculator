"""
Smoke tests for UI controllers and stale-run behavior.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from fiscal_model.ui.app_controller import (
    _PENDING_SIDEBAR_UPDATES_KEY,
    _apply_pending_sidebar_updates,
    render_data_status,
    render_quick_start,
)
from fiscal_model.ui.calculation_controller import (
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


class _DummySessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


class _DummyStreamlit:
    def __init__(self, radio_values: list[str]) -> None:
        self._radio_values = list(radio_values)
        self.session_state = _DummySessionState(results=None)
        self.warnings: list[str] = []
        self.infos: list[str] = []
        self.markdowns: list[str] = []

    def radio(self, *args, **kwargs):
        del args, kwargs
        return self._radio_values.pop(0)

    def markdown(self, *args, **kwargs):
        self.markdowns.append(args[0] if args else "")
        del kwargs
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

    def expander(self, *args, **kwargs):
        del args, kwargs
        return _DummyContext()


class _LockedWidgetSessionState(_DummySessionState):
    def __init__(self, locked_keys: set[str], **kwargs):
        super().__init__(**kwargs)
        object.__setattr__(self, "_locked_keys", locked_keys)

    def __setitem__(self, key, value):
        if key in self._locked_keys:
            raise AssertionError(f"widget key {key} was mutated after creation")
        super().__setitem__(key, value)


class _QuickStartStreamlit(_DummyStreamlit):
    def __init__(self, clicked_button: str | None = None) -> None:
        super().__init__(radio_values=[])
        self.session_state = _LockedWidgetSessionState(
            {
                "sidebar_analysis_mode",
                "sidebar_policy_area",
                "sidebar_preset_choice",
                "sidebar_spending_preset",
            },
            results=None,
            quick_start_dismissed=False,
        )
        self.clicked_button = clicked_button
        self.rerun_called = False

    def columns(self, spec):
        if isinstance(spec, int):
            return [_DummyContext() for _ in range(spec)]
        return [_DummyContext() for _ in spec]

    def container(self, *args, **kwargs):
        del args, kwargs
        return _DummyContext()

    def button(self, label, key=None, **kwargs):
        del label, kwargs
        return key == self.clicked_button

    def rerun(self):
        self.rerun_called = True
        return None


def test_render_sidebar_inputs_single_mode_uses_tax_inputs():
    st_module = _DummyStreamlit(
        radio_values=["📋 Tax proposal (preset)"]
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
        render_side_by_side_tab=lambda **kwargs: None,
    )
    tabs = {
        "tab_summary": _DummyContext(),
        "tab_distribution": _DummyContext(),
        "tab_economic": _DummyContext(),
        "tab_scoring": _DummyContext(),
        "tab_compare": _DummyContext(),
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


def test_render_quick_start_defers_sidebar_updates_until_rerun():
    st_module = _QuickStartStreamlit(clicked_button="qs_btn_infra")

    render_quick_start(st_module=st_module)

    assert st_module.rerun_called is True
    assert _PENDING_SIDEBAR_UPDATES_KEY in st_module.session_state
    assert st_module.session_state[_PENDING_SIDEBAR_UPDATES_KEY] == {
        "sidebar_analysis_mode": "💰 Spending program",
        "sidebar_spending_preset": "Infrastructure Investment ($100B/yr)",
    }
    assert st_module.session_state["qs_calculate"] is True


def test_apply_pending_sidebar_updates_sets_widget_values_before_render():
    st_module = _DummyStreamlit(radio_values=[])
    st_module.session_state[_PENDING_SIDEBAR_UPDATES_KEY] = {
        "sidebar_analysis_mode": "📋 Tax proposal (preset)",
        "sidebar_policy_area": "TCJA / Individual",
        "sidebar_preset_choice": "TCJA Full Extension",
    }

    _apply_pending_sidebar_updates(st_module=st_module)

    assert _PENDING_SIDEBAR_UPDATES_KEY not in st_module.session_state
    assert st_module.session_state["sidebar_analysis_mode"] == "📋 Tax proposal (preset)"
    assert st_module.session_state["sidebar_policy_area"] == "TCJA / Individual"
    assert st_module.session_state["sidebar_preset_choice"] == "TCJA Full Extension"


def test_render_data_status_surfaces_fred_api_configuration(monkeypatch):
    monkeypatch.setattr(
        "fiscal_model.health.check_health",
        lambda: {
            "overall": "degraded",
            "timestamp": "2026-04-01T00:00:00Z",
            "baseline": {"status": "ok", "vintage": "February 2026", "source": "real_data"},
            "irs_soi": {"status": "ok", "latest_year": 2022},
            "fred": {
                "status": "ok",
                "source": None,
                "cache_age_days": None,
                "cache_is_expired": False,
                "api_available": True,
                "last_updated": "",
            },
        },
    )
    st_module = _DummyStreamlit(radio_values=[])

    render_data_status(st_module=st_module, deps=SimpleNamespace())

    assert any("**FRED:** API configured" in text for text in st_module.markdowns)


def test_render_data_status_surfaces_stale_cache(monkeypatch):
    monkeypatch.setattr(
        "fiscal_model.health.check_health",
        lambda: {
            "overall": "degraded",
            "timestamp": "2026-04-01T00:00:00Z",
            "baseline": {"status": "ok", "vintage": "February 2026", "source": "real_data"},
            "irs_soi": {"status": "ok", "latest_year": 2022},
            "fred": {
                "status": "degraded",
                "source": "cache",
                "cache_age_days": 45,
                "cache_is_expired": True,
                "api_available": False,
                "last_updated": "2026-03-01T00:00:00Z",
            },
        },
    )
    st_module = _DummyStreamlit(radio_values=[])

    render_data_status(st_module=st_module, deps=SimpleNamespace())

    assert any("**FRED:** Stale cache (45 days)" in text for text in st_module.markdowns)


def test_render_data_status_uses_health_payload_for_baseline_and_irs(monkeypatch):
    monkeypatch.setattr(
        "fiscal_model.health.check_health",
        lambda: {
            "overall": "degraded",
            "timestamp": "2026-04-01T00:00:00Z",
            "baseline": {
                "status": "ok",
                "vintage": "January 2025",
                "source": "real_data",
                "freshness": {
                    "level": "stale",
                    "message": "Stale (300d since publication)",
                    "is_stale": True,
                },
            },
            "irs_soi": {
                "status": "degraded",
                "latest_year": 2024,
                "freshness": {
                    "level": "fresh",
                    "message": "IRS SOI 2024 (lag 2y — within expected window)",
                    "is_stale": False,
                },
            },
            "fred": {
                "status": "ok",
                "source": "live",
                "cache_age_days": 0,
                "cache_is_expired": False,
                "api_available": True,
                "last_updated": "2026-04-01T00:00:00Z",
            },
        },
    )
    st_module = _DummyStreamlit(radio_values=[])

    render_data_status(st_module=st_module, deps=SimpleNamespace())

    assert any("**Baseline:** January 2025" in text for text in st_module.markdowns)
    assert any("**IRS SOI:** 2024" in text for text in st_module.markdowns)
    assert any("CBO baseline is past its expected refresh window" in msg for msg in st_module.warnings)
