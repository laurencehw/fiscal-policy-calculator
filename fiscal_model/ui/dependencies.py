"""
Dependency assembly for Streamlit app bootstrap.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from fiscal_model import (
    CapitalGainsPolicy,
    DistributionalEngine,
    FiscalPolicyScorer,
    IncomeGroupType,
    PolicyType,
    SpendingPolicy,
    TaxPolicy,
    format_distribution_table,
    generate_winners_losers_summary,
)
from fiscal_model.app_data import CBO_SCORE_MAP, PRESET_POLICIES
from fiscal_model.long_run.solow_growth import SolowGrowthModel
from fiscal_model.microsim.data_generator import SyntheticPopulation
from fiscal_model.microsim.engine import MicroTaxCalculator
from fiscal_model.models import FRBUSAdapterLite, MacroScenario, SimpleMultiplierAdapter
from fiscal_model.preset_handler import create_policy_from_preset

from .app_controller import run_main_app
from .helpers import build_macro_scenario
from .policy_execution import calculate_tax_policy_result, run_microsim_calculation
from .policy_input import calculate_spending_policy_result, render_spending_policy_inputs, render_tax_policy_inputs
from .policy_packages import PRESET_POLICY_PACKAGES
from .styles import apply_app_styles
from .tabs import (
    render_detailed_results_tab,
    render_distribution_tab,
    render_dynamic_scoring_tab,
    render_long_run_growth_tab,
    render_methodology_tab,
    render_policy_comparison_tab,
    render_policy_package_tab,
    render_results_summary_tab,
)


def build_app_dependencies(pd_module: Any) -> SimpleNamespace:
    """
    Build all runtime dependencies needed by the app controller.
    """
    return SimpleNamespace(
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
        render_results_summary_tab=render_results_summary_tab,
        render_dynamic_scoring_tab=render_dynamic_scoring_tab,
        render_distribution_tab=render_distribution_tab,
        render_policy_comparison_tab=render_policy_comparison_tab,
        render_policy_package_tab=render_policy_package_tab,
        render_detailed_results_tab=render_detailed_results_tab,
        render_methodology_tab=render_methodology_tab,
        render_long_run_growth_tab=render_long_run_growth_tab,
        apply_app_styles=apply_app_styles,
        run_main_app=run_main_app,
        pd=pd_module,
    )
