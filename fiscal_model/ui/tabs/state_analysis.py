"""
State Analysis tab renderer.

Shows combined federal + state tax impact for a selected policy,
including SALT interaction effects and a cross-state comparison table.
"""

from __future__ import annotations

from typing import Any


def render_state_analysis_tab(
    st_module: Any,
    state: str,
    result_data: dict | None,
    run_id: str | None = None,
) -> None:
    """
    Render the State Analysis tab.

    Args:
        st_module: Streamlit module
        state: 2-letter state code selected by the user (e.g. "CA")
        result_data: Session results dict from the main calculation (may be None)
        run_id: Current run identifier for caching
    """
    from fiscal_model.models.state import (
        STATE_NAMES,
    )

    state_name = STATE_NAMES.get(state, state)

    st_module.subheader(f"State Analysis: {state_name} ({state})")
    st_module.caption(
        f"*{_confidence_label(state)}*  —  "
        "Local taxes (property, sales, municipal income) are not modeled. "
        "State estimates are approximate."
    )

    # ------------------------------------------------------------------
    # Load state profile
    # ------------------------------------------------------------------
    try:
        db = _load_db(st_module)
        profile = db.get_state(state)
    except Exception as exc:
        st_module.error(f"Could not load state tax data: {exc}")
        return

    # ------------------------------------------------------------------
    # State tax summary cards
    # ------------------------------------------------------------------
    col1, col2, col3 = st_module.columns(3)
    with col1:
        if profile.has_income_tax:
            if profile.flat_rate is not None:
                rate_str = f"{profile.flat_rate * 100:.2f}% flat"
            else:
                rate_str = f"Up to {profile.top_rate * 100:.1f}%"
        else:
            rate_str = "No income tax"
        st_module.metric("State Income Tax", rate_str)
    with col2:
        st_module.metric(
            "Median Household Income",
            f"${profile.median_household_income:,.0f}",
            help="Census ACS estimate",
        )
    with col3:
        st_module.metric(
            "Avg SALT Deduction (itemizers)",
            f"${profile.avg_salt_deduction_itemizers:,.0f}",
            help="Average SALT deduction claimed by filers who itemize",
        )

    st_module.markdown("---")

    # ------------------------------------------------------------------
    # Effective rate curves (always shown, independent of a policy run)
    # ------------------------------------------------------------------
    _render_rate_curves(st_module, state, profile)

    st_module.markdown("---")

    # ------------------------------------------------------------------
    # Policy-specific analysis (requires a calculation to have been run)
    # ------------------------------------------------------------------
    if result_data is None or not result_data:
        st_module.info(
            "Run a federal calculation first to see how it affects "
            f"{state_name} taxpayers specifically."
        )
    else:
        _render_policy_impact(st_module, state, state_name, result_data, profile)
        st_module.markdown("---")

    # ------------------------------------------------------------------
    # SALT interaction analysis
    # ------------------------------------------------------------------
    _render_salt_section(st_module, state, state_name, profile, db)

    st_module.markdown("---")

    # ------------------------------------------------------------------
    # Cross-state comparison table (top 10)
    # ------------------------------------------------------------------
    _render_state_comparison_table(st_module, db)


# ------------------------------------------------------------------
# Sub-renderers
# ------------------------------------------------------------------

def _render_rate_curves(
    st_module: Any,
    state: str,
    profile: Any,
) -> None:
    """Render combined federal + state effective rate curves."""
    import pandas as pd

    st_module.markdown("#### Combined Federal + State Effective Tax Rates")
    st_module.caption(
        "Effective rate = taxes paid / AGI at each income level. "
        "Federal uses 2025 law (TCJA in effect, $10K SALT cap)."
    )

    try:
        calc = _load_calculator(st_module, state)
        curve = calc.effective_rate_curve()
    except Exception as exc:
        st_module.warning(f"Could not compute rate curves: {exc}")
        return

    # Format for display
    display_df = pd.DataFrame({
        "Income (AGI)": [f"${r['agi']:,.0f}" for _, r in curve.iterrows()],
        "Federal Rate": [f"{r['federal_rate'] * 100:.1f}%" for _, r in curve.iterrows()],
        f"{profile.state} State Rate": [
            f"{r['state_rate'] * 100:.1f}%" for _, r in curve.iterrows()
        ],
        "Combined Rate": [f"{r['combined_rate'] * 100:.1f}%" for _, r in curve.iterrows()],
    })

    st_module.dataframe(display_df, use_container_width=True, hide_index=True)

    # Try to render a chart
    try:
        import plotly.graph_objects as go

        fig = go.Figure()
        incomes = curve["agi"].tolist()

        fig.add_trace(go.Scatter(
            x=incomes,
            y=(curve["federal_rate"] * 100).tolist(),
            mode="lines",
            name="Federal",
            line=dict(color="#1f77b4", width=2),
        ))
        fig.add_trace(go.Scatter(
            x=incomes,
            y=(curve["state_rate"] * 100).tolist(),
            mode="lines",
            name=f"{profile.state} State",
            line=dict(color="#ff7f0e", width=2),
        ))
        fig.add_trace(go.Scatter(
            x=incomes,
            y=(curve["combined_rate"] * 100).tolist(),
            mode="lines",
            name="Combined",
            line=dict(color="#2ca02c", width=2, dash="dash"),
        ))

        fig.update_layout(
            xaxis_title="AGI ($)",
            yaxis_title="Effective Rate (%)",
            xaxis_type="log",
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
            margin=dict(l=0, r=0, t=30, b=0),
            height=340,
        )
        st_module.plotly_chart(fig, use_container_width=True)
    except ImportError:
        pass  # Plotly not available; table already shown


def _render_policy_impact(
    st_module: Any,
    state: str,
    state_name: str,
    result_data: dict,
    profile: Any,
) -> None:
    """Show how the scored policy affects this state's taxpayers."""
    policy = result_data.get("policy")
    static_effect = result_data.get("static_revenue_effect", 0)
    final_effect = result_data.get("final_deficit_effect", static_effect)

    # Rough state share of national income tax revenue
    state_share = _state_revenue_share(state)

    state_federal_impact = final_effect * state_share
    policy_name = getattr(policy, "name", "Selected policy")

    st_module.markdown(f"#### {policy_name} — Impact on {state_name}")

    col1, col2, col3 = st_module.columns(3)
    with col1:
        sign = "+" if state_federal_impact > 0 else ""
        st_module.metric(
            f"Federal Impact on {state} Taxpayers",
            f"{sign}${state_federal_impact:.1f}B / yr",
            help=f"~{state_share * 100:.0f}% of national impact (state's share of federal income tax)",
        )
    with col2:
        st_module.metric(
            "State Tax Interaction",
            "—",
            help=(
                "Direct state revenue effects require state-level dynamic scoring "
                "(planned for v2). Federal changes can affect state conforming income."
            ),
        )
    with col3:
        st_module.metric(
            "Top State Rate",
            f"{profile.top_rate * 100:.1f}%",
            help="Existing state marginal rate; combined burden context",
        )

    if profile.has_local_tax_caveat if hasattr(profile, "has_local_tax_caveat") else False:
        st_module.caption(
            f"Note: Local income taxes in {state_name} are not modeled "
            "(e.g., NYC local tax, PA municipal wage taxes)."
        )


def _render_salt_section(
    st_module: Any,
    state: str,
    state_name: str,
    profile: Any,
    db: Any,
) -> None:
    """SALT interaction analysis subsection."""
    from fiscal_model.models.state import compute_salt_across_states, compute_salt_interaction

    st_module.markdown("#### SALT Deduction Interaction")

    col1, col2 = st_module.columns(2)
    with col1:
        st_module.markdown(
            f"**Current law (TCJA):** \\$10,000 SALT cap\n\n"
            f"- {profile.pct_itemizers * 100:.1f}% of {state_name} filers itemize\n"
            f"- Average SALT deduction (itemizers): \\${profile.avg_salt_deduction_itemizers:,.0f}\n"
            f"- Effective combined state+local rate: {profile.effective_salt_rate * 100:.1f}%"
        )

    # Compute effect of eliminating cap
    try:
        result_lift = compute_salt_interaction(
            state=state,
            baseline_cap=10_000,
            reform_cap=None,  # Lift cap entirely
            db=db,
        )
        with col2:
            st_module.markdown("**If SALT cap were lifted (pre-TCJA law):**")
            st_module.markdown(
                f"- Affected filers: ~{result_lift.affected_filers:.1f}M\n"
                f"- Avg deduction increase: ${result_lift.avg_deduction_change:,.0f}\n"
                f"- Federal revenue cost: ${result_lift.federal_revenue_change_billions:.1f}B / yr\n"
                f"- Effective state rate change: {result_lift.effective_rate_change * 100:+.2f}pp"
            )
    except Exception:
        pass

    # Cross-state SALT comparison
    with st_module.expander("SALT impact across all 10 states", expanded=False):
        try:
            salt_df = compute_salt_across_states(
                baseline_cap=10_000,
                reform_cap=None,
            )
            display_cols = [
                "State Name",
                "Affected Filers (M)",
                "Avg Deduction Change ($)",
                "Federal Revenue Change ($B)",
            ]
            st_module.dataframe(
                salt_df[display_cols],
                use_container_width=True,
                hide_index=True,
            )
            st_module.caption(
                "Revenue effect of lifting SALT cap entirely. "
                "Positive = federal revenue gain; negative = revenue loss."
            )
        except Exception as exc:
            st_module.warning(f"Could not compute cross-state SALT comparison: {exc}")


def _render_state_comparison_table(st_module: Any, db: Any) -> None:
    """Side-by-side comparison of key tax parameters across all 10 states."""
    import pandas as pd

    from fiscal_model.models.state.database import STATE_NAMES, SUPPORTED_STATES

    st_module.markdown("#### Top 10 States: Tax Parameter Comparison")

    records = []
    for state in SUPPORTED_STATES:
        try:
            p = db.get_state(state)
            records.append({
                "State": STATE_NAMES.get(state, state),
                "Income Tax": "None" if not p.has_income_tax else (
                    f"{p.flat_rate * 100:.2f}% flat" if p.flat_rate else f"Up to {p.top_rate * 100:.1f}%"
                ),
                "Top Rate": f"{p.top_rate * 100:.1f}%",
                "Std Ded (Single)": f"${p.std_ded_single:,.0f}" if p.std_ded_single else "—",
                "Effective SALT Rate": f"{p.effective_salt_rate * 100:.1f}%",
                "Itemizer %": f"{p.pct_itemizers * 100:.1f}%",
                "Median HH Income": f"${p.median_household_income:,.0f}",
            })
        except Exception:
            continue

    if records:
        st_module.dataframe(
            pd.DataFrame(records),
            use_container_width=True,
            hide_index=True,
        )
        st_module.caption(
            "Source: Tax Foundation State Tax Rates (2025), Census ACS 2023. "
            "SALT rates include state income, property, and local taxes weighted by itemizer usage."
        )
    else:
        st_module.warning("Could not load state comparison data.")


# ------------------------------------------------------------------
# Helpers / caching
# ------------------------------------------------------------------


def _load_db(st_module: Any, year: int = 2025) -> Any:
    """Load StateTaxDatabase with st.cache_data if available."""
    try:
        return st_module.cache_data(_load_db_impl)(year)
    except Exception:
        from fiscal_model.models.state import StateTaxDatabase
        return StateTaxDatabase(year)


def _load_db_impl(year: int = 2025):
    from fiscal_model.models.state import StateTaxDatabase
    return StateTaxDatabase(year)


def _load_calculator(st_module: Any, state: str, year: int = 2025) -> Any:
    """Load FederalStateCalculator."""
    from fiscal_model.models.state import FederalStateCalculator
    return FederalStateCalculator(state, year)


def _confidence_label(state: str) -> str:
    return "Model estimate — state approximation"


def _state_revenue_share(state: str) -> float:
    """Approximate state's share of federal income tax revenue (IRS SOI)."""
    shares = {
        "CA": 0.155,
        "TX": 0.087,
        "FL": 0.067,
        "NY": 0.095,
        "PA": 0.042,
        "IL": 0.045,
        "OH": 0.033,
        "GA": 0.030,
        "NC": 0.028,
        "MI": 0.027,
    }
    return shares.get(state, 0.03)
