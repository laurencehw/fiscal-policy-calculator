"""
Side-by-side policy comparison tab.

Lets users select two proposals and compare their 10-year budgetary effects,
annual trajectories, and key metrics in a visual diff layout.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import plotly.graph_objects as go

from fiscal_model.preset_handler import create_policy_from_preset


def _build_policy(
    preset_name: str,
    preset: dict[str, Any],
    tax_policy_cls: Any,
    policy_type_income_tax: Any,
    data_year: int,
) -> Any:
    """Build a policy object from a preset dict."""
    policy = create_policy_from_preset(preset)
    if policy is not None:
        from contextlib import suppress

        with suppress(Exception):
            if hasattr(policy, "data_year"):
                policy.data_year = data_year
        return policy

    return tax_policy_cls(
        name=preset_name,
        description=preset.get("description", ""),
        policy_type=policy_type_income_tax,
        rate_change=preset.get("rate_change", 0.0) / 100,
        affected_income_threshold=preset.get("threshold", 0),
        data_year=data_year,
        duration_years=max(1, int(preset.get("duration_years", 10))),
        phase_in_years=max(1, int(preset.get("phase_in_years", 1))),
        taxable_income_elasticity=float(preset.get("eti", 0.25)),
    )


def _score(policy: Any, scorer: Any, dynamic: bool) -> dict[str, Any]:
    """Score a policy and return summary dict."""
    result = scorer.score_policy(policy, dynamic=dynamic)

    for attr in ("final_deficit_effect", "static_deficit_effect", "static_revenue_effect"):
        effects = getattr(result, attr, None)
        if effects is not None:
            annual = np.asarray(effects, dtype=float)
            break
    else:
        annual = np.zeros(10, dtype=float)

    years = getattr(getattr(result, "baseline", None), "years", None)
    if years is not None:
        years = np.asarray(years)
    else:
        start = int(getattr(policy, "start_year", 2025))
        years = np.arange(start, start + len(annual))

    return {
        "annual": annual,
        "years": years,
        "ten_year": float(annual.sum()),
        "result": result,
    }


def _fmt(value: float) -> str:
    sign = "+" if value >= 0 else "-"
    return f"{sign}${abs(value):,.0f}B"


def _fmt_abs(value: float) -> str:
    return f"${abs(value):,.0f}B"


def render_side_by_side_tab(
    st_module: Any,
    preset_policies: dict[str, dict[str, Any]],
    tax_policy_cls: Any,
    policy_type_income_tax: Any,
    fiscal_policy_scorer_cls: Any,
    data_year: int,
    use_real_data: bool,
    dynamic_scoring: bool,
) -> None:
    """Render interactive side-by-side policy comparison."""

    st_module.header("🔀 Compare Policies")
    st_module.markdown(
        "Select two proposals to compare their 10-year budgetary effects side by side."
    )

    options = [name for name in preset_policies if name != "Custom Policy"]

    if len(options) < 2:
        st_module.info("At least two preset policies are needed for comparison.")
        return

    col_left, col_right = st_module.columns(2)

    with col_left:
        policy_a_name = st_module.selectbox(
            "Policy A",
            options=options,
            index=0,
            key="side_by_side_a",
        )
    with col_right:
        default_b = min(1, len(options) - 1)
        policy_b_name = st_module.selectbox(
            "Policy B",
            options=options,
            index=default_b,
            key="side_by_side_b",
        )

    if policy_a_name == policy_b_name:
        st_module.warning("Select two different policies to compare.")
        return

    compare_clicked = st_module.button("Compare", type="primary", key="side_by_side_btn")

    if not compare_clicked:
        st_module.caption(
            "Choose two proposals above and click **Compare** to see a side-by-side breakdown."
        )
        return

    with st_module.spinner("Scoring both policies..."):
        scorer = fiscal_policy_scorer_cls(baseline=None, use_real_data=use_real_data)

        policy_a = _build_policy(
            policy_a_name, preset_policies[policy_a_name],
            tax_policy_cls, policy_type_income_tax, data_year,
        )
        policy_b = _build_policy(
            policy_b_name, preset_policies[policy_b_name],
            tax_policy_cls, policy_type_income_tax, data_year,
        )

        result_a = _score(policy_a, scorer, dynamic_scoring)
        result_b = _score(policy_b, scorer, dynamic_scoring)

    # ── Headline metrics ─────────────────────────────────────────────
    st_module.subheader("10-Year Totals")

    m1, m2, m3 = st_module.columns(3)
    with m1:
        st_module.metric("Policy A", _fmt(result_a["ten_year"]))
        st_module.caption(policy_a_name)
    with m2:
        st_module.metric("Policy B", _fmt(result_b["ten_year"]))
        st_module.caption(policy_b_name)
    with m3:
        diff = result_b["ten_year"] - result_a["ten_year"]
        st_module.metric("Difference (B − A)", _fmt(diff))

    # ── Bar chart comparison ─────────────────────────────────────────
    st_module.markdown("---")
    st_module.subheader("10-Year Effect")

    fig_bar = go.Figure()
    colors = ["#2563EB", "#DC2626"]
    for i, (name, res) in enumerate([(policy_a_name, result_a), (policy_b_name, result_b)]):
        fig_bar.add_trace(go.Bar(
            name=name,
            x=[name],
            y=[res["ten_year"]],
            text=[_fmt(res["ten_year"])],
            textposition="outside",
            marker_color=colors[i],
        ))
    fig_bar.update_layout(
        yaxis_title="10-Year Effect (Billions $)",
        showlegend=False,
        height=400,
        bargap=0.4,
    )
    st_module.plotly_chart(fig_bar, use_container_width=True)

    # ── Year-by-year overlay ─────────────────────────────────────────
    st_module.markdown("---")
    st_module.subheader("Year-by-Year Trajectory")

    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(
        x=result_a["years"], y=result_a["annual"],
        mode="lines+markers", name=policy_a_name,
        line=dict(width=3, color="#2563EB"), marker=dict(size=7),
    ))
    fig_line.add_trace(go.Scatter(
        x=result_b["years"], y=result_b["annual"],
        mode="lines+markers", name=policy_b_name,
        line=dict(width=3, color="#DC2626"), marker=dict(size=7),
    ))
    fig_line.add_hline(y=0, line_dash="dot", line_color="gray", opacity=0.5)
    fig_line.update_layout(
        xaxis_title="Year",
        yaxis_title="Annual Effect (Billions $)",
        hovermode="x unified",
        height=450,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st_module.plotly_chart(fig_line, use_container_width=True)

    # ── Annual comparison table ──────────────────────────────────────
    st_module.markdown("---")
    st_module.subheader("Annual Breakdown")

    min_len = min(len(result_a["years"]), len(result_b["years"]))
    table_data = []
    for i in range(min_len):
        a_val = float(result_a["annual"][i])
        b_val = float(result_b["annual"][i])
        table_data.append({
            "Year": int(result_a["years"][i]),
            f"A: {policy_a_name}": _fmt(a_val),
            f"B: {policy_b_name}": _fmt(b_val),
            "Difference": _fmt(b_val - a_val),
        })

    import pandas as pd

    st_module.dataframe(
        pd.DataFrame(table_data),
        use_container_width=True,
        hide_index=True,
    )

    # ── Summary insight ──────────────────────────────────────────────
    st_module.markdown("---")
    bigger = policy_a_name if abs(result_a["ten_year"]) > abs(result_b["ten_year"]) else policy_b_name
    st_module.markdown(
        f"**{bigger}** has the larger absolute 10-year effect. "
        f"The difference between the two proposals is **{_fmt_abs(diff)}** over 10 years."
    )
