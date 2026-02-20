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
    run_id: str | None = None,
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

        # Parameters
        with st_module.expander("⚙️ Model Assumptions", expanded=False):
            crowding_out = st_module.slider(
                "Crowding Out % (Share of deficit reducing investment)",
                min_value=0,
                max_value=100,
                value=33,
                step=1,
                help="Percentage of the deficit that crowds out domestic private investment. "
                     "CBO assumes ~33% (meaning 67% is offset by foreign capital inflows). "
                     "100% = Closed Economy (Maximum Impact). 0% = Small Open Economy (No Impact)."
            ) / 100.0
            
            st_module.caption(
                f"Current assumption: For every $1.00 of deficit, private investment falls by ${crowding_out:.2f}. "
                f"Foreign capital inflows cover the remaining ${(1-crowding_out):.2f}."
            )

        deficit_path = res_obj.static_deficit_effect + res_obj.behavioral_offset
        crowding_out_pct = int(round(crowding_out * 100))
        cache_key = f"solow:{run_id}:{crowding_out_pct}" if run_id else None

        lr_res = st_module.session_state.get(cache_key) if cache_key else None
        if lr_res is None:
            solow = solow_growth_model_cls(crowding_out_pct=crowding_out)
            lr_res = solow.run_simulation(deficits=deficit_path, horizon=30)
            if cache_key:
                st_module.session_state[cache_key] = lr_res

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
            (Capital Share = 0.35, Depreciation = 5%). The "Crowding Out" parameter determines how much
            government deficits reduce private investment.
            """
        )
    elif session_results is not None and session_results.get("is_microsim"):
        st_module.info("Long-run growth projections are not available for microsimulation results.")
    else:
        st_module.info("👆 Calculate a policy impact in the first tab to see long-run projections.")
