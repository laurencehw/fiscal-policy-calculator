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
    /* Dark mode support — only target our custom components, not broad selectors
       that conflict with Streamlit's own theming (e.g. white text on white bg). */
    .dark-mode .metric-card {
        background-color: #262730;
    }
    .dark-mode .info-box {
        background-color: #1e3a5f;
        border-left-color: #4da6ff;
    }
    /* Share button styling */
    .stButton button[data-testid="baseButton-secondary"] {
        border-radius: 6px;
    }
    /* ── Mobile: scrollable tab bar ───────────────────────────────────── */
    @media screen and (max-width: 640px) {
        .stTabs [data-baseweb="tab-list"] {
            gap: 0;
            overflow-x: auto;
            flex-wrap: nowrap;
            -webkit-overflow-scrolling: touch;
            scrollbar-width: none;
        }
        .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar {
            display: none;
        }
        .stTabs [data-baseweb="tab"] {
            white-space: nowrap;
            padding: 8px 10px;
            font-size: 0.8rem;
            min-width: fit-content;
        }
    }
</style>
"""


def apply_app_styles(st_module) -> None:
    """Apply shared CSS style block to the Streamlit app."""
    st_module.markdown(APP_STYLES, unsafe_allow_html=True)
