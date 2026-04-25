"""
Tax policy sidebar inputs.
"""

from __future__ import annotations

from typing import Any

from .policy_input_presets import (
    _CATEGORY_ORDER,
    _extract_cbo_score,
    _preset_category,
    _short_display_name,
)


def render_tax_policy_inputs(
    st_module: Any,
    preset_policies: dict[str, dict[str, Any]],
    use_preset: bool = True,
    default_preset: str | None = None,
) -> dict[str, Any]:
    """Render tax policy input controls and return selected values."""
    preset_choice = default_preset or "Custom Policy"

    if use_preset:
        categorized: dict[str, list[str]] = {}
        for name, data in preset_policies.items():
            if name == "Custom Policy":
                continue
            category = _preset_category(data)
            categorized.setdefault(category, []).append(name)

        available_cats = [category for category in _CATEGORY_ORDER if category in categorized]
        default_cat_index = 0
        if default_preset and default_preset in preset_policies:
            default_cat = _preset_category(preset_policies[default_preset])
            if default_cat in available_cats:
                default_cat_index = available_cats.index(default_cat)

        area_key = "sidebar_policy_area"
        if (
            area_key in st_module.session_state
            and st_module.session_state[area_key] not in available_cats
        ):
            del st_module.session_state[area_key]

        selected_cat = st_module.selectbox(
            "Policy area",
            options=available_cats,
            index=default_cat_index,
            key=area_key,
            help="Filter proposals by policy area.",
        )

        cat_presets = categorized.get(selected_cat, [])
        short_names = {_short_display_name(name): name for name in cat_presets}
        default_short = (
            _short_display_name(default_preset)
            if default_preset and default_preset in short_names.values()
            else next(iter(short_names.keys()))
        )

        preset_key = "sidebar_preset_choice"
        if (
            preset_key in st_module.session_state
            and st_module.session_state[preset_key] not in short_names
        ):
            del st_module.session_state[preset_key]

        selected_short = st_module.selectbox(
            "Select a proposal",
            options=list(short_names.keys()),
            index=list(short_names.keys()).index(default_short) if default_short in short_names else 0,
            key=preset_key,
            help="Each proposal is pre-configured with parameters matching official estimates.",
        )
        preset_choice = short_names[selected_short]
        preset_data = preset_policies[preset_choice]

        cbo_score = _extract_cbo_score(preset_choice)
        if cbo_score:
            st_module.caption(f"Official estimate: {cbo_score}")

        from fiscal_model.ui.preset_validation import get_validation_badge

        badge = get_validation_badge(preset_choice)
        if badge:
            st_module.caption(
                f"{badge['icon']} Model accuracy vs {badge['source']}: "
                f"{badge['signed_pct']:+.1f}% ({badge['rating']})"
            )

        description = preset_data["description"]

        import re as _re

        score_match = _re.search(r"\((?:CBO|JCT):\s*(-?\$[\d.]+[TB])\)", preset_choice)
        if score_match and score_match.group(1).startswith("-"):
            direction_icon = "✅"
        elif score_match:
            direction_icon = "⚠️"
        else:
            direction_icon = "📋"

        with st_module.expander(f"{direction_icon} {selected_short}", expanded=False):
            st_module.markdown(description)

    policy_name = preset_choice if use_preset else "Tax Rate Change"
    policy_type = "Income Tax Rate"
    rate_change_pct = 0.0
    rate_change = 0.0
    threshold = 0
    duration = 10
    phase_in = 0
    manual_taxpayers = 0.0
    manual_avg_income = 0
    eti = 0.25

    cg_base_year = 2024
    baseline_cg_rate = 0.20
    baseline_realizations = 0.0
    use_time_varying = True
    short_run_elasticity = 0.8
    long_run_elasticity = 0.4
    transition_years = 3
    realization_elasticity = 0.5
    eliminate_step_up = False
    step_up_exemption = 0.0
    gains_at_death = 54.0
    step_up_lock_in_multiplier = 2.0

    if not use_preset:
        st_module.markdown("---")
        st_module.markdown("#### Define your policy")

        policy_name = st_module.text_input(
            "Policy name",
            "Tax Rate Change",
            help="A short label for your policy (used in charts and exports).",
        )

        policy_type = st_module.selectbox(
            "What type of tax?",
            ["Income Tax Rate", "Capital Gains", "Corporate Tax", "Payroll Tax"],
            index=0,
            help=(
                "**Income Tax Rate** — changes to individual marginal rates  \n"
                "**Capital Gains** — changes to rates on investment gains  \n"
                "**Corporate Tax** — changes to the 21% corporate rate  \n"
                "**Payroll Tax** — changes to Social Security / Medicare taxes"
            ),
        )

        st_module.markdown("##### Rate and scope")

        rate_change_pct = st_module.slider(
            "Rate change (percentage points)",
            min_value=-10.0,
            max_value=10.0,
            value=-2.0,
            step=0.5,
            help=(
                "How much to change the tax rate. "
                "**Positive** = tax increase (raises revenue), "
                "**Negative** = tax cut (costs revenue). "
                "Example: +2.6pp restores the pre-TCJA top rate."
            ),
        )
        rate_change = rate_change_pct / 100

        threshold_options = {
            "All taxpayers ($0+)": 0,
            "Middle income ($50K+)": 50000,
            "Upper-middle ($100K+)": 100000,
            "Higher income ($200K+)": 200000,
            "Top earners ($400K+)": 400000,
            "High income ($500K+)": 500000,
            "Millionaires ($1M+)": 1000000,
            "Custom amount": None,
        }

        threshold_choice = st_module.selectbox(
            "Who is affected?",
            options=list(threshold_options.keys()),
            index=4,
            help=(
                "The income threshold above which the rate change applies. "
                "Only income *above* this threshold is affected — not total income."
            ),
        )

        if threshold_choice == "Custom amount":
            threshold = st_module.number_input(
                "Custom income threshold ($)",
                min_value=0,
                max_value=10_000_000,
                value=400_000,
                step=50_000,
                format="%d",
            )
        else:
            threshold = threshold_options[threshold_choice]

        with st_module.expander("Policy timing", expanded=False):
            duration = st_module.slider(
                "Duration (years)",
                min_value=1,
                max_value=10,
                value=10,
                help="Standard CBO budget window is 10 years.",
            )
            phase_in = st_module.slider(
                "Phase-in period (years)",
                min_value=0,
                max_value=5,
                value=0,
                help="Years to gradually ramp up to the full rate change. 0 = immediate.",
            )

        if policy_type == "Capital Gains":
            with st_module.expander("Capital gains parameters", expanded=True):
                st_module.caption(
                    "Capital gains have unique behavioral dynamics — investors can "
                    "defer realizations, so short-run revenue effects differ from "
                    "long-run. These parameters control that response."
                )

                cg_base_year = st_module.selectbox(
                    "Baseline year",
                    [2024, 2023, 2022],
                    help="Year from which to draw baseline realizations data.",
                )
                baseline_cg_rate = st_module.number_input(
                    "Current effective CG rate",
                    min_value=0.0,
                    max_value=0.99,
                    value=0.238,
                    step=0.01,
                    help="Current combined rate including NIIT (20% + 3.8% = 23.8% for top bracket).",
                )
                baseline_realizations = st_module.number_input(
                    "Baseline realizations ($B/year)",
                    min_value=0.0,
                    max_value=10000.0,
                    value=0.0,
                    step=10.0,
                    help="Total taxable realizations. Leave at 0 to auto-populate from IRS data.",
                )

                st_module.markdown("**Behavioral elasticity**")
                st_module.caption(
                    "How much do investors change behavior in response to rate changes? "
                    "CBO uses ~0.7-1.0 short-run, ~0.3-0.5 long-run "
                    "([CBO 2012](https://www.cbo.gov/publication/43334))."
                )

                use_time_varying = st_module.checkbox(
                    "Use time-varying elasticity (recommended)",
                    value=True,
                    help="Short-run: timing effects dominate. Long-run: only permanent responses remain.",
                )

                if use_time_varying:
                    short_run_elasticity = st_module.number_input(
                        "Short-run elasticity (years 1-3)",
                        value=0.8,
                        step=0.1,
                        help="Higher because investors can time when to sell.",
                    )
                    long_run_elasticity = st_module.number_input(
                        "Long-run elasticity (years 4+)",
                        value=0.4,
                        step=0.1,
                        help="Lower because timing effects have dissipated.",
                    )
                    transition_years = st_module.slider(
                        "Transition period (years)",
                        min_value=1,
                        max_value=5,
                        value=3,
                    )
                    realization_elasticity = (
                        short_run_elasticity + long_run_elasticity
                    ) / 2
                else:
                    realization_elasticity = st_module.number_input(
                        "Realization elasticity (constant)",
                        value=0.5,
                        step=0.05,
                    )
                    short_run_elasticity = realization_elasticity
                    long_run_elasticity = realization_elasticity
                    transition_years = 1

                st_module.markdown("**Step-up basis at death**")
                st_module.caption(
                    "Under current law, unrealized gains are forgiven at death "
                    "(\"stepped-up basis\"). This creates a strong incentive to hold assets rather than sell."
                )
                eliminate_step_up = st_module.checkbox(
                    "Eliminate step-up at death",
                    value=False,
                    help="Tax unrealized gains at death (Biden proposed a $1M exemption).",
                )
                if eliminate_step_up:
                    step_up_exemption = st_module.number_input(
                        "Exemption per decedent ($)",
                        value=1_000_000,
                        step=100_000,
                    )
                    gains_at_death = st_module.number_input(
                        "Annual gains at death ($B)",
                        value=54.0,
                        step=5.0,
                        help="CBO estimates ~$54B/year in unrealized gains transferred at death.",
                    )
                    step_up_lock_in_multiplier = 1.0
                else:
                    step_up_exemption = 0.0
                    gains_at_death = 54.0
                    step_up_lock_in_multiplier = st_module.slider(
                        "Lock-in multiplier",
                        min_value=1.0,
                        max_value=6.0,
                        value=2.0,
                        step=0.5,
                        help="How much step-up increases the incentive to defer. 2.0 = calibrated to Penn Wharton estimates.",
                    )
        else:
            with st_module.expander("Advanced parameters", expanded=False):
                st_module.caption(
                    "These are auto-populated from IRS Statistics of Income data when left at zero. "
                    "Override only if you have specific values."
                )
                manual_taxpayers = st_module.number_input(
                    "Affected taxpayers (millions)",
                    min_value=0.0,
                    max_value=200.0,
                    value=0.0,
                    step=0.1,
                    help="Number of tax filers above the income threshold. Leave at 0 to pull from IRS SOI Table 1.1 automatically.",
                )
                manual_avg_income = st_module.number_input(
                    "Average taxable income ($)",
                    min_value=0,
                    max_value=100_000_000,
                    value=0,
                    step=50_000,
                    help="Mean AGI of affected filers. Leave at 0 to pull from IRS SOI data automatically.",
                )
                eti = st_module.number_input(
                    "Elasticity of Taxable Income (ETI)",
                    min_value=0.0,
                    max_value=2.0,
                    value=0.25,
                    step=0.05,
                    help=(
                        "How much taxable income changes in response to tax rate changes. "
                        "The consensus estimate is **0.25** "
                        "([Saez, Slemrod & Giertz 2012](https://eml.berkeley.edu/~saez/saez-slemrod-giertzJEL12.pdf)). "
                        "Higher = more behavioral response = less revenue."
                    ),
                )

    return {
        "preset_choice": preset_choice,
        "policy_name": policy_name,
        "rate_change_pct": rate_change_pct,
        "rate_change": rate_change,
        "threshold": threshold,
        "policy_type": policy_type,
        "duration": duration,
        "phase_in": phase_in,
        "manual_taxpayers": manual_taxpayers,
        "manual_avg_income": manual_avg_income,
        "eti": eti,
        "cg_base_year": cg_base_year,
        "cg_rate_source": "Statutory/NIIT proxy (by AGI bracket)",
        "baseline_cg_rate": baseline_cg_rate,
        "baseline_realizations": baseline_realizations,
        "use_time_varying": use_time_varying,
        "short_run_elasticity": short_run_elasticity,
        "long_run_elasticity": long_run_elasticity,
        "transition_years": transition_years,
        "realization_elasticity": realization_elasticity,
        "eliminate_step_up": eliminate_step_up,
        "step_up_exemption": step_up_exemption,
        "gains_at_death": gains_at_death,
        "step_up_lock_in_multiplier": step_up_lock_in_multiplier,
    }
