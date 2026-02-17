"""
Settings tab rendering helpers.
"""

from __future__ import annotations

from typing import Any


def render_settings_tab(st_module: Any, settings_tab: Any) -> dict[str, Any]:
    """
    Render settings panel and return selected configuration values.
    """
    macro_model = None

    with settings_tab:
        st_module.header("⚙️ Configuration")

        col_settings_1, col_settings_2 = st_module.columns(2)
        with col_settings_1:
            st_module.subheader("Model Options")
            use_real_data = st_module.checkbox(
                "Use real IRS/FRED data",
                value=True,
                help="Uses actual IRS Statistics of Income data and FRED economic indicators",
            )
            dynamic_scoring = st_module.checkbox(
                "Dynamic scoring",
                value=False,
                help="Include macroeconomic feedback effects (GDP growth, employment, interest rates)",
            )
            if dynamic_scoring:
                macro_model = st_module.selectbox(
                    "Macro model",
                    ["FRB/US-Lite (Recommended)", "Simple Multiplier"],
                    help="FRB/US-Lite uses Federal Reserve-calibrated multipliers; Simple uses basic Keynesian multipliers",
                )

            use_microsim = st_module.checkbox(
                "Microsimulation (Experimental)",
                value=False,
                help="Use individual-level tax calculation (JCT-style) instead of bracket averages. Requires CPS data.",
            )
            data_year = st_module.selectbox(
                "IRS data year",
                [2022, 2021],
                help="Year of IRS Statistics of Income data to use",
            )

        with col_settings_2:
            st_module.subheader("📚 About")
            st_module.markdown(
                """
        This calculator uses Congressional Budget Office (CBO) methodology to estimate policy impacts.

        **Data Sources:**
        - IRS Statistics of Income
        - FRED Economic Data
        - CBO Baseline Projections

        **Methodology:**
        - Static revenue estimation
        - Behavioral responses (ETI)
        - Dynamic macroeconomic feedback
        """
            )
            st_module.caption("Built with Streamlit • Data updated 2022")

        st_module.markdown("---")
        if st_module.button("🗑️ Reset All", type="primary", help="Clear all inputs, results, and settings to default"):
            st_module.session_state.clear()
            st_module.rerun()

    return {
        "use_real_data": use_real_data,
        "dynamic_scoring": dynamic_scoring,
        "macro_model": macro_model,
        "use_microsim": use_microsim,
        "data_year": data_year,
    }
