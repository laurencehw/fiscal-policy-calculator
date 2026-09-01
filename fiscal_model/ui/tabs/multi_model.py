"""
Multi-model comparison tab: run one policy through every pluggable backend.

The existing "Policy Comparison" tab toggles between the built-in static
and dynamic paths of the default scorer. This tab instead uses the
``compare_policy_models`` pipeline in ``fiscal_model.models.comparison``
so a single policy can be scored under structurally different backends
(CBO-style and TPC-microsim pilot by default) with the results rendered side
by side. PWBM-OLG remains an experimental CLI-audit backend until its adapter
clears feasibility sanity bounds.

Rendering is defensive: each model runs independently with
``continue_on_error=True`` so one backend failing (e.g. missing
microdata or an unsupported policy family) does not hide the others.
Unsupported engines are labeled "not representable" via the capability
matrix rather than swallowed as silent zeros.
"""

from __future__ import annotations

from contextlib import suppress
from typing import Any

import pandas as pd

from fiscal_model.feasibility import assess_model_pilot_comparison
from fiscal_model.models.capabilities import (
    TPC_ENGINE,
    engine_support_matrix,
    policy_family,
    support_label,
)
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
        ordinary_income_base=not bool(preset.get("agi_inclusive_base", False)),
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


def _classify_skip_reason(reason: str) -> str:
    """Label hard failures vs explicit not-representable capability skips."""
    soft_markers = (
        "does not map",
        "not in the microsim",
        "outside the",
        "firm-level",
        "not yet mapped",
        "not mapped",
        "multi-provision",
        "no corporate tax module",
        "marketplace enrollment",
    )
    lowered = reason.lower()
    if any(marker in lowered for marker in soft_markers):
        return "Not representable in this pilot"
    return "Backend error"


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
        "and see where they agree and disagree. This is the CBO × TPC "
        "side-by-side view — a pilot today, with the PWBM-OLG adapter held "
        "out of the default UI until it clears feasibility sanity bounds.\n\n"
        "- **CBO-Style** — the calculator's default static + ETI path "
        "(specialized modules: corporate, credits, payroll, estate, …).\n"
        "- **TPC-Microsim Pilot** — return-level microsim for policies that "
        "map to reforms (income-tax rates, CTC, EITC, SALT, AMT exemption). "
        "Corporate / OASDI payroll / estate / TCJA composites are reported as "
        "**not representable**, not as fake agreement.\n"
        "- **PWBM-OLG Pilot** — held out of the app until its adapter "
        "clears calibration checks (developers can run it via the offline "
        "feasibility audit)."
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

    # Build policies once so selectbox labels can show CBO+TPC vs CBO only.
    built: dict[str, Any] = {}
    labeled_options: list[str] = []
    label_to_name: dict[str, str] = {}
    for name in preset_names:
        try:
            policy = _build_policy(
                preset_name=name,
                preset=preset_policies[name],
                tax_policy_cls=tax_policy_cls,
                policy_type_income_tax=policy_type_income_tax,
                data_year=data_year,
            )
        except Exception:
            continue
        built[name] = policy
        label = f"{name}  ·  {support_label(policy)}"
        labeled_options.append(label)
        label_to_name[label] = name

    if not labeled_options:
        st_module.warning("Could not construct any preset policies for comparison.")
        return

    dual = sum(1 for p in built.values() if support_label(p) == "CBO+TPC")
    st_module.caption(
        f"{dual} of {len(built)} presets are comparable on both default pilots "
        "(CBO+TPC). Others still run on CBO-Style; TPC reports "
        '"not representable" instead of inventing a score.'
    )

    selected_label = st_module.selectbox(
        "Policy",
        options=labeled_options,
        index=0,
        help=(
            "CBO+TPC = both default pilots can score this family. "
            "CBO only = specialized module runs on CBO-Style; TPC skips honestly."
        ),
    )
    preset_name = label_to_name[selected_label]
    policy = built[preset_name]

    matrix = engine_support_matrix(policy)
    family = policy_family(policy)
    st_module.markdown(f"**Policy family:** `{family}`")
    for row in matrix:
        icon = "✅" if row.supported else "⏭"
        st_module.caption(f"{icon} **{row.engine}** — {row.reason}")

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
            "No backend produced a result. Check the skip / error notes below."
        )
    else:
        assessment = assess_model_pilot_comparison(bundle)
        if not assessment.ready_for_spike:
            st_module.warning(
                "Pilot quality blocker: this multi-model comparison has "
                "implausible gaps and should not be treated as decision-grade."
            )
            for blocker in assessment.blockers:
                st_module.markdown(f"- {blocker}")
        elif assessment.warnings:
            for warning in assessment.warnings:
                st_module.caption(f"Pilot model warning: {warning}")

        summary = _bundle_to_summary_frame(bundle)
        st_module.dataframe(summary, hide_index=True, width="stretch")

        ran = {result.model_name for result in bundle.results}
        skipped = set(bundle.errors)
        st_module.caption(
            f"Engines that ran: {', '.join(sorted(ran)) or 'none'}. "
            f"Skipped: {', '.join(sorted(skipped)) or 'none'}."
        )

        if bundle.max_gap is not None and TPC_ENGINE in ran and len(bundle.results) >= 2:
            st_module.metric(
                "Max spread across models (10-year cost)",
                _format_cost_billions(float(bundle.max_gap)),
                help=(
                    "The largest pairwise difference between model 10-year "
                    "estimates. Large spreads signal model risk; small "
                    "spreads suggest the result is robust."
                ),
            )
            gap = float(bundle.max_gap)
            costs = [float(r.ten_year_cost) for r in bundle.results]
            if len(costs) >= 2 and max(abs(c) for c in costs) > 1:
                rel = abs(gap) / max(abs(c) for c in costs) * 100
                if rel >= 25:
                    st_module.warning(
                        f"Models disagree by ~{rel:.0f}% of the largest "
                        "estimate — treat the headline as directional and "
                        "read the methodology notes below."
                    )
                elif rel >= 10:
                    st_module.info(
                        f"Models disagree by ~{rel:.0f}% of the largest "
                        "estimate. Divergence usually reflects bracket "
                        "aggregates vs return-level interactions."
                    )
                else:
                    st_module.success(
                        f"Models agree within ~{rel:.0f}% — result looks "
                        "robust across the pilot backends."
                    )
        elif len(bundle.results) == 1:
            st_module.info(
                "Only one default pilot could score this policy, so there is "
                "no cross-model spread. Pick a **CBO+TPC** preset (income-tax "
                "rate, CTC, EITC, or SALT) to compare engines."
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
            kind = _classify_skip_reason(reason)
            st_module.markdown(f"- **{model_name}** ({kind}): {reason}")

    with st_module.expander("What am I looking at?"):
        st_module.markdown(
            "Each backend uses a different methodology, so disagreement "
            "is informative:\n\n"
            "- **CBO vs TPC-Microsim** gap ≈ the distributional / "
            "return-level effect. Large gaps on policies with thresholds "
            "and phase-outs suggest bracket-aggregate data is missing "
            "real interactions (details in the project's validation notes "
            "on GitHub).\n"
            "- **Max spread** is only shown when ≥2 engines produce costs. "
            "A corporate or payroll preset that TPC cannot represent will "
            "not invent agreement.\n"
            "- **PWBM-OLG** is intentionally omitted from the default view "
            "until its adapter clears calibration checks."
        )


__all__ = ["render_multi_model_tab"]
