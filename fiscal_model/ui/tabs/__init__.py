"""
Tab renderer modules for Streamlit app.
"""

from .deficit_target import render_deficit_target_tab
from .detailed_results import render_detailed_results_tab
from .distribution_analysis import render_distribution_tab
from .dynamic_scoring import render_dynamic_scoring_tab
from .generational_analysis import render_generational_analysis_tab
from .long_run_growth import render_long_run_growth_tab
from .methodology import render_methodology_tab
from .package_builder import render_policy_package_tab
from .policy_comparison import render_policy_comparison_tab
from .results_summary import render_results_summary_tab
from .bill_tracker import render_bill_tracker_tab
from .state_analysis import render_state_analysis_tab

__all__ = [
    "render_deficit_target_tab",
    "render_detailed_results_tab",
    "render_distribution_tab",
    "render_dynamic_scoring_tab",
    "render_generational_analysis_tab",
    "render_long_run_growth_tab",
    "render_methodology_tab",
    "render_policy_comparison_tab",
    "render_policy_package_tab",
    "render_results_summary_tab",
    "render_bill_tracker_tab",
    "render_state_analysis_tab",
]
