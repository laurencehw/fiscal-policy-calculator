"""
UI helper utilities for Streamlit app composition.
"""

from .app_controller import run_main_app
from .dependencies import build_app_dependencies
from .helpers import build_macro_scenario, build_scorable_policy_map
from .policy_execution import calculate_tax_policy_result, run_microsim_calculation
from .policy_input import (
    calculate_spending_policy_result,
    render_spending_policy_inputs,
    render_tax_policy_inputs,
)
from .policy_packages import PRESET_POLICY_PACKAGES
from .styles import APP_STYLES, apply_app_styles

__all__ = [
    "APP_STYLES",
    "PRESET_POLICY_PACKAGES",
    "apply_app_styles",
    "build_app_dependencies",
    "build_macro_scenario",
    "build_scorable_policy_map",
    "calculate_spending_policy_result",
    "calculate_tax_policy_result",
    "render_spending_policy_inputs",
    "render_tax_policy_inputs",
    "run_main_app",
    "run_microsim_calculation",
]
