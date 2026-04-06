"""
Multi-model comparison tab renderer.
"""

from __future__ import annotations

from contextlib import suppress
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from fiscal_model.preset_handler import create_policy_from_preset

STATIC_MODEL = "CBO-Style (Static + ETI)"
DYNAMIC_MODEL = "FRB/US-Lite (Dynamic)"


def _build_policy_for_comparison(
    preset_name: str,
    preset: dict[str, Any],
    tax_policy_cls: Any,
    policy_type_income_tax: Any,
    data_year: int,
) -> Any:
    policy = create_policy_from_preset(preset)
    if policy is not None:
        if hasattr(policy, "data_year"):
            with suppress(Exception):
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


def _extract_annual_effects(result: Any, policy: Any) -> np.ndarray:
    for attr in ("final_deficit_effect", "static_deficit_effect", "static_revenue_effect"):
        effects = getattr(result, attr, None)
        if effects is not None:
            return np.asarray(effects, dtype=float)

    horizon = max(1, int(getattr(policy, "duration_years", 1) or 1))
    return np.zeros(horizon, dtype=float)


def _extract_years(result: Any, policy: Any, annual_effects: np.ndarray) -> np.ndarray:
    years = getattr(getattr(result, "baseline", None), "years", None)
    if years is not None:
        return np.asarray(years)

    start_year = int(getattr(policy, "start_year", 1))
    return np.arange(start_year, start_year + len(annual_effects))


def _score_model(
    policy_name: str,
    model_name: str,
    policy: Any,
    scorer: Any,
    dynamic: bool,
) -> dict[str, Any]:
    result = scorer.score_policy(policy, dynamic=dynamic)
    annual_effects = _extract_annual_effects(result, policy)
    years = _extract_years(result, policy, annual_effects)

    return {
        "policy": policy_name,
        "model": model_name,
        "ten_year_cost": float(annual_effects.sum()),
        "annual_effects": annual_effects,
        "years": years,
        "result": result,
    }


def _format_billions(value: float) -> str:
    sign = "+" if value >= 0 else "-"
    return f"{sign}${abs(value):,.1f}B"


def render_policy_comparison_tab(
    st_module: Any,
    is_spending: bool,
    preset_policies: dict[str, dict[str, Any]],
    tax_policy_cls: Any,
    policy_type_income_tax: Any,
    fiscal_policy_scorer_cls: Any,
    data_year: int,
    use_real_data: bool,
    dynamic_scoring: bool,
) -> None:
    """
    Render multi-model comparison tab content.
    """
    st_module.header("🔀 Multi-Model Comparison")
    st_module.markdown(
        """
        <div class="info-box">
        💡 Select preset policies to compare across models. Current models: CBO-style
        (static + ETI) and FRB/US-Lite (dynamic). Complex presets like TCJA and
        climate policies are loaded through the preset factory, so they use the same
        construction path as the main calculator.
        </div>
        """,
        unsafe_allow_html=True,
    )

    if is_spending or not preset_policies:
        st_module.info("Policy comparison is available for preset tax and climate policies.")
        return

    comparison_options = [name for name in preset_policies if name != "Custom Policy"]
    policies_to_compare = st_module.multiselect(
        "Select policies to compare (1-3 recommended)",
        options=comparison_options,
        default=comparison_options[:1],
        max_selections=4,
    )
    model_options = [STATIC_MODEL]
    default_models = [STATIC_MODEL]
    if dynamic_scoring:
        model_options.append(DYNAMIC_MODEL)
        default_models.append(DYNAMIC_MODEL)
    else:
        st_module.caption("Enable dynamic scoring in Model settings to compare against FRB/US-Lite.")
    selected_models = st_module.multiselect(
        "Models to compare",
        options=model_options,
        default=default_models,
        max_selections=2,
    )

    if not policies_to_compare:
        st_module.info("Select at least one preset to compare across models.")
        return
    if not selected_models:
        st_module.info("Select at least one model to compare.")
        return

    with st_module.spinner("Running multi-model comparison..."):
        try:
            model_results: list[dict[str, Any]] = []
            comparison_scorer = fiscal_policy_scorer_cls(baseline=None, use_real_data=use_real_data)

            for preset_name in policies_to_compare:
                preset = preset_policies[preset_name]
                policy = _build_policy_for_comparison(
                    preset_name=preset_name,
                    preset=preset,
                    tax_policy_cls=tax_policy_cls,
                    policy_type_income_tax=policy_type_income_tax,
                    data_year=data_year,
                )

                for model_name in selected_models:
                    model_results.append(
                        _score_model(
                            policy_name=preset_name,
                            model_name=model_name,
                            policy=policy,
                            scorer=comparison_scorer,
                            dynamic=(model_name == DYNAMIC_MODEL),
                        )
                    )

            st_module.subheader("📊 Multi-Model Summary")
            comparison_df = pd.DataFrame(
                [
                    {
                        "Policy": row["policy"],
                        "Model": row["model"],
                        "10-Year Effect": _format_billions(row["ten_year_cost"]),
                    }
                    for row in model_results
                ]
            )
            st_module.dataframe(comparison_df, use_container_width=True, hide_index=True)

            divergence_rows: list[dict[str, float | str]] = []
            for policy_name in policies_to_compare:
                policy_rows = [row for row in model_results if row["policy"] == policy_name]
                if len(policy_rows) < 2:
                    continue
                costs = [float(row["ten_year_cost"]) for row in policy_rows]
                divergence_rows.append(
                    {
                        "Policy": policy_name,
                        "Min Estimate": min(costs),
                        "Max Estimate": max(costs),
                        "Range": max(costs) - min(costs),
                    }
                )

            if divergence_rows:
                max_range = max(float(row["Range"]) for row in divergence_rows)
                st_module.metric(
                    "Largest Model Divergence",
                    _format_billions(max_range),
                    help="Difference between the highest and lowest selected model estimate for a policy.",
                )

                divergence_df = pd.DataFrame(
                    [
                        {
                            "Policy": row["Policy"],
                            "Min Estimate": _format_billions(float(row["Min Estimate"])),
                            "Max Estimate": _format_billions(float(row["Max Estimate"])),
                            "Range": _format_billions(float(row["Range"])),
                        }
                        for row in divergence_rows
                    ]
                )
                st_module.dataframe(divergence_df, use_container_width=True, hide_index=True)

            st_module.markdown("---")
            st_module.subheader("10-Year Effect by Model")
            fig_compare = go.Figure()
            for model_name in selected_models:
                model_rows = [row for row in model_results if row["model"] == model_name]
                fig_compare.add_trace(
                    go.Bar(
                        name=model_name,
                        x=[row["policy"] for row in model_rows],
                        y=[row["ten_year_cost"] for row in model_rows],
                        text=[_format_billions(row["ten_year_cost"]) for row in model_rows],
                        textposition="outside",
                    )
                )
            fig_compare.update_layout(
                xaxis_title="Policy",
                yaxis_title="10-Year Effect (Billions $)",
                barmode="group",
                height=500,
                hovermode="x",
            )
            st_module.plotly_chart(fig_compare, use_container_width=True)

            st_module.markdown("---")
            st_module.subheader("Year-by-Year Comparison")
            fig_timeline = go.Figure()
            for row in model_results:
                fig_timeline.add_trace(
                    go.Scatter(
                        x=row["years"],
                        y=row["annual_effects"],
                        mode="lines+markers",
                        name=f"{row['policy']} · {row['model']}",
                        line=dict(width=3),
                        marker=dict(size=7),
                    )
                )
            fig_timeline.update_layout(
                xaxis_title="Year",
                yaxis_title="Annual Effect (Billions $)",
                hovermode="x unified",
                height=500,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            )
            st_module.plotly_chart(fig_timeline, use_container_width=True)

            st_module.markdown("---")
            st_module.subheader("📝 Model Divergence & Insights")
            insight_lines = []
            if divergence_rows:
                for row in divergence_rows:
                    insight_lines.append(
                        f"- `{row['Policy']}` differs by {_format_billions(float(row['Range']))} across the selected models."
                    )
            if DYNAMIC_MODEL in selected_models and STATIC_MODEL in selected_models:
                insight_lines.append(
                    "- The dynamic model includes macroeconomic feedback, so it can moderate or amplify the static estimate depending on GDP and revenue feedback."
                )
            if not insight_lines:
                insight_lines.append("- Select at least two models for the same policy to see divergence analysis.")
            st_module.markdown("\n".join(insight_lines))

        except Exception as exc:
            import traceback

            st_module.error(f"Error comparing policies: {exc}")
            st_module.code(traceback.format_exc())
