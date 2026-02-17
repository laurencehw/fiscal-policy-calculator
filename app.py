"""
Fiscal Policy Impact Calculator - Main Streamlit App.
"""

from pathlib import Path
import sys

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Fiscal Policy Calculator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

sys.path.insert(0, str(Path(__file__).parent))

try:
    from fiscal_model.ui.dependencies import build_app_dependencies

    deps = build_app_dependencies(pd_module=pd)
    MODEL_AVAILABLE = True
    MACRO_AVAILABLE = True
except ImportError as e:
    MODEL_AVAILABLE = False
    MACRO_AVAILABLE = False
    st.error(f"⚠️ Could not import fiscal model: {e}")

if MODEL_AVAILABLE:
    deps.apply_app_styles(st)
    deps.run_main_app(
        st_module=st,
        deps=deps,
        model_available=MODEL_AVAILABLE,
        app_root=Path(__file__).parent,
    )
