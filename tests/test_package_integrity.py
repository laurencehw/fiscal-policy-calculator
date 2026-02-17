"""
Regression tests for package wiring and baseline/data fallbacks.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from fiscal_model.app_data import CBO_SCORE_MAP, PRESET_POLICIES
from fiscal_model.baseline import CBOBaseline
from fiscal_model.data import CapitalGainsBaseline, FREDData, IRSSOIData
from fiscal_model.preset_handler import create_policy_from_preset
from fiscal_model.ui import (
    PRESET_POLICY_PACKAGES,
    build_app_dependencies,
    build_macro_scenario,
    build_scorable_policy_map,
    calculate_tax_policy_result,
    calculate_spending_policy_result,
    render_spending_policy_inputs,
    render_tax_policy_inputs,
    run_main_app,
    run_microsim_calculation,
)
from fiscal_model.ui.calculation_controller import (
    ensure_results_state,
    execute_calculation_if_requested,
    render_policy_input_tab,
)
from fiscal_model.ui.controller_utils import run_with_spinner_feedback
from fiscal_model.ui.settings_controller import render_settings_tab
from fiscal_model.ui.tabs_controller import build_nested_tabs, render_footer, render_result_tabs
from fiscal_model.ui.tabs import (
    render_detailed_results_tab,
    render_distribution_tab,
    render_dynamic_scoring_tab,
    render_long_run_growth_tab,
    render_methodology_tab,
    render_policy_package_tab,
    render_policy_comparison_tab,
    render_results_summary_tab,
)


def test_package_level_app_data_imports():
    assert isinstance(PRESET_POLICIES, dict)
    assert isinstance(CBO_SCORE_MAP, dict)
    assert len(PRESET_POLICIES) > 0


def test_preset_factory_covers_flagged_presets():
    flag_keys = [
        "is_tcja",
        "is_corporate",
        "is_credit",
        "is_estate",
        "is_payroll",
        "is_amt",
        "is_ptc",
        "is_expenditure",
    ]

    for name, preset in PRESET_POLICIES.items():
        if name == "Custom Policy":
            continue

        policy = create_policy_from_preset(preset)
        is_flagged = any(bool(preset.get(key, False)) for key in flag_keys)

        if is_flagged:
            assert policy is not None, f"Expected policy for preset: {name}"
        else:
            assert policy is None, f"Expected None for simple preset: {name}"


def test_irs_soi_loader_smoke():
    irs = IRSSOIData()
    years = irs.get_data_years_available()
    assert len(years) >= 1

    year = max(years)
    revenue = irs.get_total_revenue(year)
    assert revenue > 0

    filers = irs.get_filers_by_bracket(year=year, threshold=400_000)
    assert filers["num_filers"] > 0
    assert filers["avg_taxable_income"] >= 0


def test_capital_gains_baseline_smoke():
    baseline = CapitalGainsBaseline()
    result = baseline.get_baseline_above_threshold_with_rate_method(
        year=2024,
        threshold=400_000,
        rate_method="statutory_by_agi",
    )

    assert result["net_capital_gain_billions"] > 0
    assert 0 < result["average_effective_tax_rate"] < 1


def test_fred_data_is_available_returns_bool():
    fred = FREDData()
    assert isinstance(fred.is_available(), bool)


def test_cbo_baseline_fallback_when_data_load_fails(monkeypatch):
    def _raise_load_error(self):
        raise RuntimeError("forced load failure")

    monkeypatch.setattr(CBOBaseline, "_load_from_data_sources", _raise_load_error)

    baseline = CBOBaseline(use_real_data=True)
    projection = baseline.generate()

    assert len(projection.years) == 10
    assert projection.nominal_gdp[0] > 0


def test_build_macro_scenario_tax_policy_mapping():
    policy = SimpleNamespace(name="Test Tax Policy")
    result = SimpleNamespace(
        static_revenue_effect=np.array([100.0, 200.0]),
        behavioral_offset=np.array([10.0, -20.0]),
        baseline=SimpleNamespace(years=np.array([2025, 2026])),
    )

    class DummyScenario:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    scenario = build_macro_scenario(
        policy=policy,
        result=result,
        is_spending_policy=False,
        macro_scenario_cls=DummyScenario,
    )

    assert scenario.name == "Test Tax Policy"
    assert scenario.start_year == 2025
    assert scenario.receipts_change.tolist() == [110.0, 180.0]
    assert scenario.outlays_change.tolist() == [0.0, 0.0]


def test_build_macro_scenario_spending_policy_mapping():
    policy = SimpleNamespace(name="Test Spending Policy")
    result = SimpleNamespace(
        static_revenue_effect=np.array([-50.0, -60.0]),
        behavioral_offset=np.array([0.0, 5.0]),
        baseline=SimpleNamespace(years=np.array([2027, 2028])),
    )

    class DummyScenario:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    scenario = build_macro_scenario(
        policy=policy,
        result=result,
        is_spending_policy=True,
        macro_scenario_cls=DummyScenario,
    )

    assert scenario.name == "Test Spending Policy"
    assert scenario.start_year == 2027
    assert scenario.receipts_change.tolist() == [0.0, 0.0]
    assert scenario.outlays_change.tolist() == [50.0, 55.0]


def test_build_scorable_policy_map_categories():
    test_presets = {
        "Custom Policy": {},
        "TCJA Example": {"is_tcja": True},
        "AMT Example": {"is_amt": True},
        "Ignored Example": {"is_unknown": True},
    }
    mapped = build_scorable_policy_map(test_presets)

    assert "Custom Policy" not in mapped
    assert mapped["TCJA Example"]["category"] == "TCJA"
    assert mapped["AMT Example"]["category"] == "AMT"
    assert "Ignored Example" not in mapped


def test_preset_policy_packages_available():
    assert isinstance(PRESET_POLICY_PACKAGES, dict)
    assert "Biden FY2025 Tax Plan" in PRESET_POLICY_PACKAGES


def test_policy_package_tab_renderer_importable():
    assert callable(render_policy_package_tab)


def test_dynamic_scoring_tab_renderer_importable():
    assert callable(render_dynamic_scoring_tab)


def test_distribution_tab_renderer_importable():
    assert callable(render_distribution_tab)


def test_detailed_results_tab_renderer_importable():
    assert callable(render_detailed_results_tab)


def test_policy_comparison_tab_renderer_importable():
    assert callable(render_policy_comparison_tab)


def test_methodology_tab_renderer_importable():
    assert callable(render_methodology_tab)


def test_long_run_growth_tab_renderer_importable():
    assert callable(render_long_run_growth_tab)


def test_results_summary_tab_renderer_importable():
    assert callable(render_results_summary_tab)


def test_spending_policy_input_helpers_importable():
    assert callable(run_main_app)
    assert callable(build_app_dependencies)
    assert callable(render_settings_tab)
    assert callable(render_policy_input_tab)
    assert callable(ensure_results_state)
    assert callable(execute_calculation_if_requested)
    assert callable(run_with_spinner_feedback)
    assert callable(build_nested_tabs)
    assert callable(render_result_tabs)
    assert callable(render_footer)
    assert callable(render_tax_policy_inputs)
    assert callable(render_spending_policy_inputs)
    assert callable(calculate_spending_policy_result)


def test_calculate_spending_policy_result_mapping():
    class DummyPolicy:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class DummyScorer:
        def __init__(self, baseline, use_real_data):
            self.baseline = baseline
            self.use_real_data = use_real_data

        def score_policy(self, policy, dynamic):
            return SimpleNamespace(policy_name=policy.name, dynamic=dynamic)

    result = calculate_spending_policy_result(
        spending_inputs={
            "program_name": "Test Program",
            "annual_spending": 25.0,
            "spending_category": "Infrastructure",
            "duration": 5,
            "growth_rate": 0.02,
            "multiplier": 1.3,
            "is_one_time": False,
        },
        spending_policy_cls=DummyPolicy,
        policy_type_discretionary_nondefense="disc_nondefense",
        fiscal_policy_scorer_cls=DummyScorer,
        use_real_data=True,
        dynamic_scoring=False,
    )

    assert result["is_spending"] is True
    assert result["policy"].name == "Test Program"
    assert result["policy"].policy_type == "disc_nondefense"
    assert result["result"].policy_name == "Test Program"


def test_run_microsim_calculation_with_synthetic_data(tmp_path):
    import pandas as pd

    class DummyPopulation:
        def __init__(self, size):
            self.size = size

        def generate(self):
            return pd.DataFrame(
                {
                    "final_tax": [100.0, 200.0],
                    "weight": [1.0, 2.0],
                    "children": [0, 1],
                }
            )

    class DummyCalc:
        def calculate(self, population):
            return population.copy()

        def run_reform(self, population, reform_func):
            params = SimpleNamespace(ctc_amount=0)
            reform_func(params)
            assert params.ctc_amount == 4000
            reformed = population.copy()
            reformed.loc[:, "final_tax"] = reformed["final_tax"] - 10.0
            return reformed

    result = run_microsim_calculation(
        preset_choice="CTC Expansion Test",
        base_dir=tmp_path,
        micro_tax_calculator_cls=DummyCalc,
        synthetic_population_cls=DummyPopulation,
        pd_module=pd,
    )

    assert result["is_microsim"] is True
    assert "Synthetic" in result["source_msg"]
    assert "avg_tax_change" in result["distribution_kids"].columns


def test_calculate_tax_policy_result_simple_mapping():
    class DummyPolicyType:
        INCOME_TAX = "income_tax"
        CAPITAL_GAINS_TAX = "capital_gains_tax"
        CORPORATE_TAX = "corporate_tax"
        PAYROLL_TAX = "payroll_tax"

    class DummyPolicy:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
            self.affected_taxpayers_millions = 0.0
            self.avg_taxable_income_in_bracket = 0.0

    class DummyScorer:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def score_policy(self, policy, dynamic):
            return SimpleNamespace(policy_name=policy.name, dynamic=dynamic)

    result = calculate_tax_policy_result(
        preset_policies={"Custom Policy": {"description": "custom", "rate_change": 1.0, "threshold": 0}},
        preset_choice="Custom Policy",
        create_policy_from_preset_fn=lambda _: None,
        dynamic_scoring=False,
        use_real_data=True,
        fiscal_policy_scorer_cls=DummyScorer,
        tax_policy_cls=DummyPolicy,
        capital_gains_policy_cls=DummyPolicy,
        policy_type_cls=DummyPolicyType,
        policy_type="Income Tax Rate",
        policy_name="Test Income Tax",
        rate_change_pct=1.0,
        rate_change=0.01,
        threshold=400_000,
        data_year=2022,
        duration=10,
        phase_in=0,
        eti=0.25,
        manual_taxpayers=1.5,
        manual_avg_income=500_000,
        cg_base_year=2024,
        baseline_cg_rate=0.2,
        baseline_realizations=0.0,
        realization_elasticity=0.5,
        short_run_elasticity=0.8,
        long_run_elasticity=0.4,
        transition_years=3,
        use_time_varying=True,
        eliminate_step_up=False,
        step_up_exemption=0.0,
        gains_at_death=54.0,
        step_up_lock_in_multiplier=2.0,
    )

    assert result["is_spending"] is False
    assert result["policy"].name == "Test Income Tax"
    assert result["policy"].affected_taxpayers_millions == 1.5
    assert result["policy"].avg_taxable_income_in_bracket == 500_000
