"""
Tab renderer modules for Streamlit app.
"""

from .detailed_results import render_detailed_results_tab
from .distribution_analysis import render_distribution_tab
from .dynamic_scoring import render_dynamic_scoring_tab
from .long_run_growth import render_long_run_growth_tab
from .methodology import render_methodology_tab
from .package_builder import render_policy_package_tab
from .policy_comparison import render_policy_comparison_tab
from .results_summary import render_results_summary_tab

__all__ = [
    "render_detailed_results_tab",
    "render_distribution_tab",
    "render_dynamic_scoring_tab",
    "render_long_run_growth_tab",
    "render_methodology_tab",
    "render_policy_package_tab",
    "render_policy_comparison_tab",
    "render_results_summary_tab",
]
