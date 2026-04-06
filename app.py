"""
Fiscal Policy Impact Calculator - Main Streamlit App.

URL routing:
  /              — Main calculator
  /?mode=classroom&assignment=laffer_curve  — Classroom mode
"""

from pathlib import Path

import pandas as pd
import streamlit as st

# Route to classroom mode before setting page config.
# Support query params for deep linking: ?policy=TCJA+Full+Extension&dynamic=true
_mode = st.query_params.get("mode", "")

if _mode == "classroom":
    from classroom_app import render_classroom_app
    render_classroom_app()
else:
    st.set_page_config(
        page_title="Fiscal Policy Impact Calculator — CBO-Validated Budget Scoring",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <meta name="description" content="Estimate the budgetary impact of tax and spending proposals. 25+ policies validated within 15% of CBO/JCT scores.">
        <meta property="og:title" content="Fiscal Policy Impact Calculator — CBO-Validated Budget Scoring">
        <meta property="og:description" content="Estimate the budgetary impact of tax and spending proposals. 25+ policies validated within 15% of CBO/JCT scores.">
        <meta property="og:type" content="website">
        <meta name="twitter:card" content="summary">
        <meta name="twitter:title" content="Fiscal Policy Impact Calculator — CBO-Validated Budget Scoring">
        <meta name="twitter:description" content="Estimate the budgetary impact of tax and spending proposals. 25+ policies validated within 15% of CBO/JCT scores.">
        """,
        unsafe_allow_html=True,
    )

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
