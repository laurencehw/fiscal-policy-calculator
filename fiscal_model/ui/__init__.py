"""
UI helper utilities for Streamlit app composition.
"""

from .styles import APP_STYLES, apply_app_styles
from .policy_packages import PRESET_POLICY_PACKAGES
from .helpers import build_macro_scenario, build_scorable_policy_map
from .policy_input import calculate_spending_policy_result, render_spending_policy_inputs, render_tax_policy_inputs
from .policy_execution import calculate_tax_policy_result, run_microsim_calculation
from .app_controller import run_main_app
from .dependencies import build_app_dependencies

__all__ = [
    "APP_STYLES",
    "apply_app_styles",
    "PRESET_POLICY_PACKAGES",
    "build_macro_scenario",
    "build_scorable_policy_map",
    "render_tax_policy_inputs",
    "render_spending_policy_inputs",
    "calculate_spending_policy_result",
    "calculate_tax_policy_result",
    "run_microsim_calculation",
    "run_main_app",
    "build_app_dependencies",
]
