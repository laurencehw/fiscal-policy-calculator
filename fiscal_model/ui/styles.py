"""
Centralized Streamlit style definitions.
"""

APP_STYLES = """
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .positive-impact {
        color: #28a745;
        font-weight: bold;
    }
    .negative-impact {
        color: #dc3545;
        font-weight: bold;
    }
    .info-box {
        background-color: #e7f3ff;
        border-left: 4px solid #1f77b4;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 0.25rem;
    }
</style>
"""


def apply_app_styles(st_module) -> None:
    """Apply shared CSS style block to the Streamlit app."""
    st_module.markdown(APP_STYLES, unsafe_allow_html=True)
