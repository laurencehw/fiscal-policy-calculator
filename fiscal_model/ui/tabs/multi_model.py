"""
Multi-model comparison tab: run one policy through every pluggable backend.

The existing "Policy Comparison" tab toggles between the built-in static
and dynamic paths of the default scorer. This tab instead uses the
``compare_policy_models`` pipeline in ``fiscal_model.models.comparison``
so a single policy can be scored under structurally different backends
(CBO-style, TPC-microsim pilot, PWBM-OLG pilot) with the results rendered
side by side.

Rendering is defensive: each model runs independently with
``continue_on_error=True`` so one backend failing (e.g. missing
microdata on a fresh clone) does not hide the others. Missing
backends are reported in an explicit "Notes" section rather than
swallowed.
"""

from __future__ import annotations

from contextlib import suppress
from typing import Any

import pandas as pd

from fiscal_model.models.comparison import (
    ComparisonBundle,
    UnsupportedModelPolicyError,
    build_default_comparison_models,
    compare_policy_models,
)
from fiscal_model.preset_handler import create_policy_from_preset


def _build_policy(
    preset_name: str,
    preset: dict[str, Any],
    tax_policy_cls: Any,
    policy_type_income_tax: Any,
    data_year: int,
) -> Any:
    policy = create_policy_from_preset(preset)
    if policy is not None:
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


def _format_cost_billions(value: float) -> str:
    if value == 0:
        return "$0B"
    sign = "+" if value > 0 else "-"
    magnitude = abs(value)
    if magnitude >= 1000:
        return f"{sign}${magnitude / 1000:.2f}T"
    return f"{sign}${magnitude:.1f}B"


def _bundle_to_summary_frame(bundle: ComparisonBundle) -> pd.DataFrame:
    rows = []
    for result in bundle.results:
        metadata = result.metadata or {}
        notes = metadata.get("notes") or []
        if isinstance(notes, list):
            note_str = "; ".join(notes)
        else:
            note_str = str(notes)
        rows.append(
            {
                "Model": result.model_name,
                "10-Year Cost": _format_cost_billions(float(result.ten_year_cost)),
                "Methodology": metadata.get("methodology", ""),
                "Confidence": metadata.get("confidence_label", "—"),
                "Notes": note_str,
            }
        )
    return pd.DataFrame(rows)


def _annual_effects_frame(bundle: ComparisonBundle) -> pd.DataFrame:
    frames = []
    for result in bundle.results:
        annual = list(result.annual_effects)
        if not annual:
            continue
        frames.append(
            pd.DataFrame(
                {
                    "Year offset": list(range(len(annual))),
                    "Deficit effect ($B)": [float(v) for v in annual],
                    "Model": [result.model_name] * len(annual),
                }
            )
        )
    if not frames:
        return pd.DataFrame(columns=["Year offset", "Deficit effect ($B)", "Model"])
    return pd.concat(frames, ignore_index=True)


def render_multi_model_tab(
    st_module: Any,
    *,
    is_spending: bool,
    preset_policies: dict[str, dict[str, Any]],
    tax_policy_cls: Any,
    policy_type_income_tax: Any,
    fiscal_policy_scorer_cls: Any,
    data_year: int,
    use_real_data: bool,
) -> None:
    """
    Render the multi-backend comparison tab.

    Parameters mirror the existing ``render_policy_comparison_tab`` so the
    tabs controller can inject them through the same dependency shim.
    """
    st_module.header("🔀 Multi-Model Comparison")
    st_module.markdown(
        "Run the same policy through **structurally different scoring models** "
        "and see where they agree and disagree. This is the CBO × TPC × PWBM "
        "side-by-side view — a pilot today, with two of the three backends "
        "running as early-stage adapters.\n\n"
        "- **CBO-Style** — the calculator's default static + ETI path.\n"
        "- **TPC-Microsim Pilot** — single-year microsimulation over the bundled "
        "tax-unit file. Works for policies that map to a supported reform.\n"
        "- **PWBM-OLG Pilot** — static fiscal path + OLG revenue feedback and "
        "interest-cost adjustment."
    )

    if is_spending or not preset_policies:
        st_module.info(
            "Multi-model comparison is currently available for preset tax "
            "policies. Support for spending and tariff policies is planned."
        )
        return

    preset_names = [name for name in preset_policies if name != "Custom Policy"]
    if not preset_names:
        st_module.info("No eligible presets available for comparison.")
        return

    preset_name = st_module.selectbox(
        "Policy",
        options=preset_names,
        index=0,
        help="Choose a preset tax policy to score under every backend.",
    )
    preset = preset_policies[preset_name]

    try:
        policy = _build_policy(
            preset_name=preset_name,
            preset=preset,
            tax_policy_cls=tax_policy_cls,
            policy_type_income_tax=policy_type_income_tax,
            data_year=data_year,
        )
    except Exception as exc:
        st_module.error(f"Could not construct policy for '{preset_name}': {exc}")
        return

    with st_module.spinner("Running every backend..."):
        models = build_default_comparison_models(
            fiscal_policy_scorer_cls,
            use_real_data=use_real_data,
        )
        try:
            bundle = compare_policy_models(
                policy,
                models,
                continue_on_error=True,
            )
        except UnsupportedModelPolicyError as exc:
            st_module.warning(
                "One or more backends do not support this policy type: "
                f"{exc}. Try a different preset."
            )
            return
        except Exception as exc:
            st_module.error(f"Comparison failed: {exc}")
            return

    if not bundle.results:
        st_module.warning(
            "No backend produced a result. Check the error notes below."
        )
    else:
        summary = _bundle_to_summary_frame(bundle)
        st_module.dataframe(summary, hide_index=True, use_container_width=True)

        if bundle.max_gap is not None:
            st_module.metric(
                "Max spread across models (10-year cost)",
                _format_cost_billions(float(bundle.max_gap)),
                help=(
                    "The largest pairwise difference between model 10-year "
                    "estimates. Large spreads signal model risk; small "
                    "spreads suggest the result is robust."
                ),
            )

        annual_frame = _annual_effects_frame(bundle)
        if not annual_frame.empty:
            st_module.subheader("Annual deficit effect by model")
            pivot = annual_frame.pivot(
                index="Year offset",
                columns="Model",
                values="Deficit effect ($B)",
            )
            st_module.line_chart(pivot)

    if bundle.errors:
        st_module.subheader("Backends that did not run")
        for model_name, reason in bundle.errors.items():
            st_module.markdown(f"- **{model_name}**: {reason}")

    with st_module.expander("What am I looking at?"):
        st_module.markdown(
            "Each backend uses a different methodology, so disagreement "
            "is informative:\n\n"
            "- **CBO vs PWBM** gap ≈ the macroeconomic / general-equilibrium "
            "effects. Large gaps on tax cuts usually mean crowding-out or "
            "labor-supply response is material.\n"
            "- **CBO vs TPC-Microsim** gap ≈ the distributional / "
            "return-level effect. Large gaps on policies with thresholds "
            "and phase-outs suggest bracket-aggregate data is missing "
            "real interactions (see `docs/VALIDATION_NOTES.md`).\n"
            "- **Max spread** is the honest uncertainty band for the "
            "estimate under reasonable methodological choices.\n\n"
            "This pilot is scaffolded — coverage expands as additional "
            "backends land. Tracked in `planning/ROADMAP.md`."
        )


__all__ = ["render_multi_model_tab"]
