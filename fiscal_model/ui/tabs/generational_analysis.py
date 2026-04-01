"""
Generational Analysis tab — OLG model results with cohort burden charts.

Displays:
  1. Long-run steady-state GDP/capital/wage effects
  2. Transition path chart (GDP % change over 75 years)
  3. Cohort burden chart (lifetime net tax change by age)
  4. Generational accounting summary table
  5. Model confidence disclaimer

All OLG outputs carry the "Model estimate — wide uncertainty band" label.

Caching: uses st.cache_data for the expensive OLG computation.
"""

from __future__ import annotations

from typing import Any

import numpy as np


# ---------------------------------------------------------------------------
# Confidence disclaimer
# ---------------------------------------------------------------------------

_OLG_DISCLAIMER = """
⚠️ **Model estimate — wide uncertainty band.**
OLG results depend on long-run structural parameters (discount rate, labour
elasticity, demographic projections) that are uncertain.  These projections
are best interpreted as directional — they identify *who* bears the long-run
burden and *which* steady state is reached — rather than point estimates.
Contrast with the static CBO-validated scores in the Results tab.
"""


# ---------------------------------------------------------------------------
# Main render function
# ---------------------------------------------------------------------------

def render_generational_analysis_tab(
    st_module: Any,
    result_data: dict | None,
    run_id: str | None = None,
) -> None:
    """
    Render the Generational Analysis tab.

    Parameters
    ----------
    st_module : streamlit
        The streamlit module (injected for testability).
    result_data : dict | None
        Session-state results from the main calculation.
    run_id : str | None
        Cache key for st.cache_data.
    """
    st_module.header("🌐 Generational Analysis (OLG Model)")
    st_module.markdown(_OLG_DISCLAIMER)

    if result_data is None or not result_data:
        st_module.info(
            "Run a policy calculation first, then select a reform below "
            "to see generational effects."
        )
        _render_demo_section(st_module)
        return

    # ── Policy controls ──────────────────────────────────────────────
    st_module.markdown("---")
    st_module.subheader("Reform Parameters")
    st_module.caption(
        "The OLG model is separate from the main CBO-style scorer. "
        "Specify the long-run parameter changes below."
    )

    col1, col2, col3 = st_module.columns(3)
    with col1:
        tau_k = st_module.slider(
            "Capital tax rate (%)",
            min_value=5, max_value=60, value=30, step=1,
            help="Effective capital income tax rate (corporate + individual).",
        ) / 100.0
    with col2:
        tau_ss = st_module.slider(
            "SS payroll tax rate (%)",
            min_value=0, max_value=20, value=12, step=1,
            help="Combined SS payroll tax rate (employee + employer).",
        ) / 100.0
    with col3:
        ss_rep = st_module.slider(
            "SS replacement rate (%)",
            min_value=0, max_value=80, value=40, step=5,
            help="SS benefit as % of average wage.",
        ) / 100.0

    compute = st_module.button("Run OLG Analysis", type="primary")

    cache_key = f"olg:{run_id}:{tau_k:.3f}:{tau_ss:.3f}:{ss_rep:.3f}"
    olg_result = st_module.session_state.get(cache_key)

    if compute or (olg_result is None and st_module.session_state.get("olg_auto", False)):
        with st_module.spinner("Running OLG model (this takes ~5–15 seconds)..."):
            olg_result = _run_olg(tau_k, tau_ss, ss_rep)
        st_module.session_state[cache_key] = olg_result

    if olg_result is None:
        st_module.info("Click **Run OLG Analysis** to compute results.")
        return

    _render_results(st_module, olg_result)


# ---------------------------------------------------------------------------
# OLG computation (cached via session state above; expose for st.cache_data)
# ---------------------------------------------------------------------------

def _run_olg(tau_k: float, tau_ss: float, ss_rep: float):
    """Run OLG model and return OLGPolicyResult."""
    from fiscal_model.models.olg import OLGModel, OLGParameters

    params = OLGParameters()
    baseline_tau_k = params.capital_tax_rate
    baseline_tau_ss = params.ss_payroll_rate
    baseline_ss_rep = params.ss_replacement_rate

    overrides: dict = {}
    if abs(tau_k - baseline_tau_k) > 0.001:
        overrides["tau_k"] = tau_k
    if abs(tau_ss - baseline_tau_ss) > 0.001:
        overrides["tau_ss"] = tau_ss
    if abs(ss_rep - baseline_ss_rep) > 0.001:
        overrides["ss_replacement_rate"] = ss_rep

    if not overrides:
        # No change — return baseline comparison
        model = OLGModel(params)
        baseline = model.get_baseline()
        from fiscal_model.models.olg.model import OLGPolicyResult
        from fiscal_model.models.olg.solver import TransitionPath
        T = params.transition_years
        years = np.arange(2026, 2026 + T)
        dummy_path = TransitionPath(
            years=years,
            K_path=np.full(T, baseline.K),
            L_path=np.full(T, baseline.L),
            Y_path=np.full(T, baseline.Y),
            r_path=np.full(T, baseline.r),
            w_path=np.full(T, baseline.w),
            tau_l_path=np.full(T, baseline.tau_l),
            debt_path=np.full(T, baseline.debt),
        )
        return OLGPolicyResult(
            baseline=baseline,
            reform=baseline,
            transition=dummy_path,
            gen_accounts=None,
            policy_name="No change (baseline)",
        )

    model = OLGModel(params)
    return model.analyze_policy(
        reform_overrides=overrides,
        policy_name=f"OLG Reform (τ_k={tau_k:.0%}, τ_ss={tau_ss:.0%}, rep={ss_rep:.0%})",
        compute_gen_accounts=True,
        compute_transition=True,
        start_year=2026,
    )


# ---------------------------------------------------------------------------
# Results rendering
# ---------------------------------------------------------------------------

def _render_results(st_module: Any, olg_result) -> None:
    """Render OLG results: steady-state metrics, transition chart, gen accounts."""
    import plotly.express as px
    import plotly.graph_objects as go

    baseline = olg_result.baseline
    reform = olg_result.reform

    # ── Steady-state metrics ──────────────────────────────────────────
    st_module.markdown("---")
    st_module.subheader("Long-Run Steady-State Effects")
    st_module.caption(olg_result.confidence_label)

    c1, c2, c3, c4 = st_module.columns(4)
    with c1:
        st_module.metric(
            "Long-run GDP",
            f"{olg_result.long_run_gdp_pct_change:+.2f}%",
            help="Percent change in steady-state GDP (reform vs baseline).",
        )
    with c2:
        st_module.metric(
            "Capital stock",
            f"{olg_result.long_run_capital_pct_change:+.2f}%",
            help="Percent change in steady-state capital K.",
        )
    with c3:
        st_module.metric(
            "Real wage",
            f"{olg_result.long_run_wage_pct_change:+.2f}%",
            help="Percent change in steady-state wage per efficiency unit.",
        )
    with c4:
        st_module.metric(
            "Interest rate",
            f"{olg_result.long_run_interest_rate_change:+.2f} pp",
            help="Change in steady-state net interest rate (percentage points).",
        )

    c5, c6, c7 = st_module.columns(3)
    with c5:
        st_module.metric(
            "K/Y ratio (baseline)",
            f"{baseline.capital_output_ratio:.2f}",
        )
    with c6:
        st_module.metric(
            "K/Y ratio (reform)",
            f"{reform.capital_output_ratio:.2f}",
        )
    with c7:
        st_module.metric(
            "Year-30 GDP effect",
            f"{olg_result.year_30_gdp_effect():+.2f}%",
        )

    # ── Transition path chart ─────────────────────────────────────────
    st_module.markdown("---")
    st_module.subheader("Transition Path (75 years)")

    trans = olg_result.transition
    gdp_pct = olg_result.gdp_transition_pct_change()

    fig_trans = go.Figure()
    fig_trans.add_trace(go.Scatter(
        x=trans.years, y=gdp_pct,
        mode="lines", name="GDP % change from baseline",
        line=dict(color="#1f77b4", width=2),
    ))
    fig_trans.add_hline(y=0, line_dash="dash", line_color="gray")
    fig_trans.update_layout(
        title="GDP Change Along Transition Path (% from baseline)",
        xaxis_title="Year",
        yaxis_title="% change from baseline",
        height=380,
        margin=dict(l=40, r=40, t=60, b=40),
    )
    st_module.plotly_chart(fig_trans, use_container_width=True)

    # Capital and interest rate sub-charts
    col_a, col_b = st_module.columns(2)
    with col_a:
        k_pct = (trans.K_path - baseline.K) / max(baseline.K, 1e-10) * 100
        fig_k = px.line(
            x=trans.years, y=k_pct,
            labels={"x": "Year", "y": "% change"},
            title="Capital Stock (% change)",
        )
        fig_k.add_hline(y=0, line_dash="dash", line_color="gray")
        st_module.plotly_chart(fig_k, use_container_width=True)

    with col_b:
        rate_ppts = (trans.r_path - baseline.r) * 100
        fig_r = px.line(
            x=trans.years, y=rate_ppts,
            labels={"x": "Year", "y": "pp change"},
            title="Interest Rate (pp change)",
        )
        fig_r.add_hline(y=0, line_dash="dash", line_color="gray")
        st_module.plotly_chart(fig_r, use_container_width=True)

    # ── Generational accounts ─────────────────────────────────────────
    if olg_result.gen_accounts is not None:
        _render_gen_accounts(st_module, olg_result.gen_accounts)

    # ── Summary text ──────────────────────────────────────────────────
    with st_module.expander("📋 Full OLG Summary", expanded=False):
        st_module.code(olg_result.summary())


def _render_gen_accounts(st_module: Any, gen_accounts) -> None:
    """Render cohort burden chart and generational accounting table."""
    import plotly.graph_objects as go

    st_module.markdown("---")
    st_module.subheader("Generational Burden Analysis")
    st_module.caption(
        "Lifetime net tax burden change by current age. "
        "Positive = reform increases lifetime taxes on this cohort."
    )

    # Metrics
    c1, c2, c3 = st_module.columns(3)
    with c1:
        st_module.metric(
            "Newborn (age 21) burden change",
            f"{gen_accounts.newborn_burden_change:+.4f}",
            help="Change in PV of lifetime net taxes for a cohort entering the labour market.",
        )
    with c2:
        st_module.metric(
            "Weighted avg burden change",
            f"{gen_accounts.weighted_burden_change():+.4f}",
            help="Population-weighted average change across all living cohorts.",
        )
    with c3:
        imb = gen_accounts.generational_imbalance
        st_module.metric(
            "Generational imbalance",
            f"{imb:+.4f}",
            help=(
                "Reform burden on newborns relative to baseline burden. "
                "Positive = reform shifts burden to younger/future generations."
            ),
        )

    # Cohort burden chart
    df = gen_accounts.to_dataframe()

    fig_burden = go.Figure()
    # Baseline burden
    fig_burden.add_trace(go.Scatter(
        x=df["age"], y=df["baseline_burden"],
        mode="lines", name="Baseline",
        line=dict(color="#aec7e8", dash="dot"),
    ))
    # Reform burden
    fig_burden.add_trace(go.Scatter(
        x=df["age"], y=df["reform_burden"],
        mode="lines", name="Reform",
        line=dict(color="#1f77b4"),
    ))
    # Change (bar)
    colours = ["#d62728" if x > 0 else "#2ca02c" for x in df["burden_change"]]
    fig_burden.add_trace(go.Bar(
        x=df["age"], y=df["burden_change"],
        name="Burden change (reform − baseline)",
        marker_color=colours,
        yaxis="y2",
        opacity=0.5,
    ))
    fig_burden.update_layout(
        title="Lifetime Net Tax Burden by Cohort Age",
        xaxis_title="Current age",
        yaxis_title="Remaining lifetime burden (model units)",
        yaxis2=dict(
            title="Burden change",
            overlaying="y", side="right", showgrid=False,
        ),
        height=420,
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=40, r=60, t=60, b=40),
    )
    st_module.plotly_chart(fig_burden, use_container_width=True)

    # Table
    with st_module.expander("📊 Burden table by age group", expanded=False):
        import pandas as pd
        display_df = df[["age", "baseline_burden", "reform_burden", "burden_change"]].copy()
        display_df.columns = ["Age", "Baseline burden", "Reform burden", "Change"]
        display_df = display_df[display_df["age"].isin(range(21, 76, 5))]
        st_module.dataframe(display_df.set_index("Age").round(4), use_container_width=True)


def _render_demo_section(st_module: Any) -> None:
    """Show a brief explanation of what the tab will show."""
    st_module.markdown("---")
    st_module.markdown("""
**What is generational analysis?**

The Overlapping Generations (OLG) model tracks how fiscal reforms affect
different age cohorts over their *entire lifetimes*.  Unlike the 10-year
CBO window, the OLG model captures:

- **Long-run crowding out**: higher deficits reduce capital formation,
  lowering wages for future workers
- **Who pays**: younger cohorts bear the capital-depletion cost of today's
  deficit; older cohorts may benefit from benefit expansions
- **Generational accounting** (Auerbach-Gokhale-Kotlikoff 1991): the present
  value of lifetime net taxes for each cohort

**Interpreting results**

All OLG outputs show "Model estimate — wide uncertainty band."
The *direction* of effects is more reliable than the *magnitude*.
Use alongside the CBO-calibrated static scores in the Results tab.
    """)
