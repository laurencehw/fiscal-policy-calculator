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
        color: #fafafa;
    }
    .dark-mode .info-box {
        background-color: #1e3a5f;
        border-left-color: #4da6ff;
        color: #fafafa;
    }
    /* Share button styling */
    .stButton button[data-testid="baseButton-secondary"] {
        border-radius: 6px;
    }
    /* ── Mobile (≤640px): stack columns, larger taps, smaller headers ─── */
    @media screen and (max-width: 640px) {
        /* Bigger tap targets — 44px is the iOS/Material accessibility floor. */
        .stButton button {
            min-height: 44px;
            padding: 0.5rem 1rem;
            font-size: 1rem;
        }
        /* Stack horizontal column groups vertically on phones. Streamlit
           renders st.columns() as flex rows; turning them into flex
           columns makes the quick-start cards, distribution callouts,
           and bill cards readable on a 360px viewport. */
        div[data-testid="stHorizontalBlock"] {
            flex-direction: column;
            gap: 0.5rem;
        }
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {
            width: 100% !important;
            min-width: 100% !important;
        }
        /* Shrink the main hero header and tighten metric cards. */
        .main-header {
            font-size: 1.6rem;
        }
        h1 { font-size: 1.6rem; }
        h2 { font-size: 1.3rem; }
        h3 { font-size: 1.1rem; }
        .info-box {
            padding: 0.75rem;
            margin: 0.5rem 0;
        }
        /* Dataframes: allow horizontal scroll instead of squashing. */
        div[data-testid="stDataFrame"],
        div[data-testid="stTable"] {
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
        }
        /* Tighten metric values so the deficit number doesn't truncate. */
        div[data-testid="stMetric"] {
            padding: 0.5rem 0;
        }
        div[data-testid="stMetricValue"] {
            font-size: 1.25rem;
        }
        /* Sidebar: reduce padding so more content fits behind the
           hamburger toggle. */
        section[data-testid="stSidebar"] > div {
            padding-top: 0.5rem;
            padding-left: 0.75rem;
            padding-right: 0.75rem;
        }
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
    /* ── Tablet (641-1024px): keep columns but tighten gutters ────────── */
    @media screen and (min-width: 641px) and (max-width: 1024px) {
        .main-header { font-size: 2rem; }
        div[data-testid="stHorizontalBlock"] { gap: 0.5rem; }
        .stButton button { min-height: 40px; }
    }
</style>
"""


def apply_app_styles(st_module) -> None:
    """Apply shared CSS style block to the Streamlit app."""
    st_module.markdown(APP_STYLES, unsafe_allow_html=True)
