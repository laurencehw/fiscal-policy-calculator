"""
Long-run growth tab renderer.
"""

from __future__ import annotations

from typing import Any

import plotly.express as px


def render_long_run_growth_tab(
    st_module: Any,
    session_results: Any,
    solow_growth_model_cls: Any,
) -> None:
    """
    Render long-run growth and crowding-out tab content.
    """
    st_module.header("⏳ Long-Run Growth & Crowding Out")

    st_module.markdown(
        """
        <div class="info-box">
        💡 <strong>Capital Crowding Out:</strong> This model simulates how fiscal deficits affect the
        nation's capital stock over a 30-year horizon. Larger deficits reduce private investment,
        leading to lower future GDP and wages.
        </div>
        """,
        unsafe_allow_html=True,
    )

    if session_results is not None and not session_results.get("is_microsim"):
        res_obj = session_results.get("result")
        if res_obj is None:
            st_module.info("Long-run projections require aggregate model results. Run a policy calculation first.")
            return

        deficit_path = res_obj.static_deficit_effect + res_obj.behavioral_offset
        solow = solow_growth_model_cls()
        lr_res = solow.run_simulation(deficits=deficit_path, horizon=30)

        col1, col2, col3 = st_module.columns(3)
        with col1:
            st_module.metric("GDP Effect (Year 10)", f"{lr_res.gdp_pct_change[9]:.2f}%")
        with col2:
            st_module.metric("GDP Effect (Year 30)", f"{lr_res.gdp_pct_change[29]:.2f}%")
        with col3:
            st_module.metric(
                "Long-Run Wage Effect",
                f"{lr_res.gdp_pct_change[29] * 0.7:.2f}%",
                help="Estimated impact on real wages driven by capital stock changes.",
            )

        st_module.markdown("---")
        c1, c2 = st_module.columns(2)

        with c1:
            st_module.subheader("GDP Trajectory (% Change)")
            fig_gdp = px.line(
                x=lr_res.years,
                y=lr_res.gdp_pct_change,
                labels={"x": "Year", "y": "% Change from Baseline"},
            )
            fig_gdp.add_hline(y=0, line_dash="dash", line_color="gray")
            st_module.plotly_chart(fig_gdp, use_container_width=True)

        with c2:
            st_module.subheader("Capital Stock (% Change)")
            cap_pct_change = (lr_res.capital_stock / lr_res.capital_stock[0] - 1) * 100
            fig_cap = px.line(
                x=lr_res.years,
                y=cap_pct_change,
                labels={"x": "Year", "y": "% Change in Capital"},
            )
            st_module.plotly_chart(fig_cap, use_container_width=True)

        st_module.info(
            """
                **Methodology Note:** This projection uses a Solow-Swan growth model calibrated to the US economy
                (Capital Share = 0.35, Depreciation = 5%). It assumes that 100% of the deficit increase
                reduces private investment (crowding out). This matches the 'closed economy' assumptions
                often used as a conservative benchmark by CBO and Penn Wharton.
                """
        )
    elif session_results is not None and session_results.get("is_microsim"):
        st_module.info("Long-run growth projections are not available for microsimulation results.")
    else:
        st_module.info("👆 Calculate a policy impact in the first tab to see long-run projections.")
