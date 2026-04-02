"""
Centralized Streamlit session state keys.

All session state key strings used across the UI should be defined here
to prevent typos and key collisions. Dynamic keys (e.g., cache keys
with run_id) use helper functions.
"""

# =============================================================================
# CORE RESULTS
# =============================================================================
RESULTS = "results"
RESULTS_RUN_ID = "results_run_id"
LAST_RUN_ID = "last_run_id"
LAST_RUN_AT = "last_run_at"
CURRENT_RUN_ID = "current_run_id"

# =============================================================================
# UI STATE
# =============================================================================
QUICK_START_DISMISSED = "quick_start_dismissed"
OLG_AUTO = "olg_auto"

# =============================================================================
# BILL TRACKER
# =============================================================================
BT_SHOW_DETAIL_PREFIX = "bt_show_detail_"


def bt_show_detail_key(bill_id: str) -> str:
    """Session state key for bill tracker detail toggle."""
    return f"{BT_SHOW_DETAIL_PREFIX}{bill_id}"


# =============================================================================
# CACHE KEYS (dynamic, based on run_id + tab)
# =============================================================================

def dist_cache_key(run_id: str, suffix: str = "") -> str:
    """Session state key for distributional analysis cache."""
    return f"dist_{run_id}{suffix}"


def macro_cache_key(run_id: str, model: str = "") -> str:
    """Session state key for macro/dynamic scoring cache."""
    return f"macro_{run_id}_{model}" if model else f"macro_{run_id}"


def olg_cache_key(run_id: str) -> str:
    """Session state key for OLG model cache."""
    return f"olg_{run_id}"


def growth_cache_key(run_id: str) -> str:
    """Session state key for long-run growth cache."""
    return f"growth_{run_id}"
