"""
Dependency assembly for Streamlit app bootstrap.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fiscal_model.app_data import CBO_SCORE_MAP, PRESET_POLICIES
from fiscal_model.distribution import (
    DistributionalEngine,
    IncomeGroupType,
    format_distribution_table,
    generate_winners_losers_summary,
)
from fiscal_model.long_run.solow_growth import SolowGrowthModel
from fiscal_model.models.base import BaseScoringModel, CBOStyleModel
from fiscal_model.models.macro_adapter import (
    FRBUSAdapterLite,
    MacroScenario,
    SimpleMultiplierAdapter,
)
from fiscal_model.policies import CapitalGainsPolicy, PolicyType, SpendingPolicy, TaxPolicy
from fiscal_model.preset_handler import create_policy_from_preset
from fiscal_model.scoring import FiscalPolicyScorer

from .app_controller import run_main_app
from .helpers import build_macro_scenario
from .policy_execution import calculate_tax_policy_result, run_microsim_calculation
from .policy_input import (
    calculate_spending_policy_result,
    render_spending_policy_inputs,
    render_tax_policy_inputs,
)
from .policy_packages import PRESET_POLICY_PACKAGES
from .styles import apply_app_styles


def _render_results_summary_tab(**kwargs: Any) -> Any:
    from .tabs.results_summary import render_results_summary_tab

    return render_results_summary_tab(**kwargs)


def _render_dynamic_scoring_tab(**kwargs: Any) -> Any:
    from .tabs.dynamic_scoring import render_dynamic_scoring_tab

    return render_dynamic_scoring_tab(**kwargs)


def _render_distribution_tab(**kwargs: Any) -> Any:
    from .tabs.distribution_analysis import render_distribution_tab

    return render_distribution_tab(**kwargs)


def _render_policy_comparison_tab(**kwargs: Any) -> Any:
    from .tabs.policy_comparison import render_policy_comparison_tab

    return render_policy_comparison_tab(**kwargs)


def _render_policy_package_tab(**kwargs: Any) -> Any:
    from .tabs.package_builder import render_policy_package_tab

    return render_policy_package_tab(**kwargs)


def _render_detailed_results_tab(**kwargs: Any) -> Any:
    from .tabs.detailed_results import render_detailed_results_tab

    return render_detailed_results_tab(**kwargs)


def _render_methodology_tab(**kwargs: Any) -> Any:
    from .tabs.methodology import render_methodology_tab

    return render_methodology_tab(**kwargs)


def _render_long_run_growth_tab(**kwargs: Any) -> Any:
    from .tabs.long_run_growth import render_long_run_growth_tab

    return render_long_run_growth_tab(**kwargs)


def _render_generational_analysis_tab(**kwargs: Any) -> Any:
    from .tabs.generational_analysis import render_generational_analysis_tab

    return render_generational_analysis_tab(**kwargs)


def _render_bill_tracker_tab(**kwargs: Any) -> Any:
    from .tabs.bill_tracker import render_bill_tracker_tab

    return render_bill_tracker_tab(**kwargs)


def _render_state_analysis_tab(**kwargs: Any) -> Any:
    from .tabs.state_analysis import render_state_analysis_tab

    return render_state_analysis_tab(**kwargs)


@dataclass(frozen=True)
class AppDependencies:
    PRESET_POLICIES: dict[str, dict[str, Any]]
    PRESET_POLICY_PACKAGES: dict[str, dict[str, Any]]
    CBO_SCORE_MAP: dict[str, dict[str, Any]]
    TaxPolicy: type[TaxPolicy]
    CapitalGainsPolicy: type[CapitalGainsPolicy]
    SpendingPolicy: type[SpendingPolicy]
    PolicyType: type[PolicyType]
    FiscalPolicyScorer: type[FiscalPolicyScorer]
    DistributionalEngine: type[DistributionalEngine]
    IncomeGroupType: type[IncomeGroupType]
    FRBUSAdapterLite: type[FRBUSAdapterLite]
    SimpleMultiplierAdapter: type[SimpleMultiplierAdapter]
    MacroScenario: type[MacroScenario]
    MicroTaxCalculator: Any
    SyntheticPopulation: Any
    SolowGrowthModel: type[SolowGrowthModel]
    create_policy_from_preset: Any
    format_distribution_table: Any
    generate_winners_losers_summary: Any
    render_tax_policy_inputs: Any
    render_spending_policy_inputs: Any
    calculate_tax_policy_result: Any
    calculate_spending_policy_result: Any
    run_microsim_calculation: Any
    build_macro_scenario: Any
    render_results_summary_tab: Any
    render_dynamic_scoring_tab: Any
    render_distribution_tab: Any
    render_policy_comparison_tab: Any
    render_policy_package_tab: Any
    render_detailed_results_tab: Any
    render_methodology_tab: Any
    render_long_run_growth_tab: Any
    render_generational_analysis_tab: Any
    render_bill_tracker_tab: Any
    render_state_analysis_tab: Any
    BaseScoringModel: type[BaseScoringModel]
    CBOStyleModel: type[CBOStyleModel]
    apply_app_styles: Any
    run_main_app: Any
    pd: Any


def build_app_dependencies(pd_module: Any) -> AppDependencies:
    """
    Build all runtime dependencies needed by the app controller.

    Heavy UI tab modules are loaded lazily through wrapper callables to
    reduce cold-start import cost in Streamlit.
    """
    from fiscal_model.microsim.data_generator import SyntheticPopulation
    from fiscal_model.microsim.engine import MicroTaxCalculator

    return AppDependencies(
        PRESET_POLICIES=PRESET_POLICIES,
        PRESET_POLICY_PACKAGES=PRESET_POLICY_PACKAGES,
        CBO_SCORE_MAP=CBO_SCORE_MAP,
        TaxPolicy=TaxPolicy,
        CapitalGainsPolicy=CapitalGainsPolicy,
        SpendingPolicy=SpendingPolicy,
        PolicyType=PolicyType,
        FiscalPolicyScorer=FiscalPolicyScorer,
        DistributionalEngine=DistributionalEngine,
        IncomeGroupType=IncomeGroupType,
        FRBUSAdapterLite=FRBUSAdapterLite,
        SimpleMultiplierAdapter=SimpleMultiplierAdapter,
        MacroScenario=MacroScenario,
        MicroTaxCalculator=MicroTaxCalculator,
        SyntheticPopulation=SyntheticPopulation,
        SolowGrowthModel=SolowGrowthModel,
        create_policy_from_preset=create_policy_from_preset,
        format_distribution_table=format_distribution_table,
        generate_winners_losers_summary=generate_winners_losers_summary,
        render_tax_policy_inputs=render_tax_policy_inputs,
        render_spending_policy_inputs=render_spending_policy_inputs,
        calculate_tax_policy_result=calculate_tax_policy_result,
        calculate_spending_policy_result=calculate_spending_policy_result,
        run_microsim_calculation=run_microsim_calculation,
        build_macro_scenario=build_macro_scenario,
        render_results_summary_tab=_render_results_summary_tab,
        render_dynamic_scoring_tab=_render_dynamic_scoring_tab,
        render_distribution_tab=_render_distribution_tab,
        render_policy_comparison_tab=_render_policy_comparison_tab,
        render_policy_package_tab=_render_policy_package_tab,
        render_detailed_results_tab=_render_detailed_results_tab,
        render_methodology_tab=_render_methodology_tab,
        render_long_run_growth_tab=_render_long_run_growth_tab,
        render_generational_analysis_tab=_render_generational_analysis_tab,
        render_bill_tracker_tab=_render_bill_tracker_tab,
        render_state_analysis_tab=_render_state_analysis_tab,
        BaseScoringModel=BaseScoringModel,
        CBOStyleModel=CBOStyleModel,
        apply_app_styles=apply_app_styles,
        run_main_app=run_main_app,
        pd=pd_module,
    )
