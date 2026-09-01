"""
Tax policy sidebar inputs.
"""

from __future__ import annotations

from typing import Any

from fiscal_model.preset_ids import resolve_preset

from .policy_input_presets import (
    _CATEGORY_ORDER,
    _extract_cbo_score,
    _preset_category,
    _short_display_name,
)
from .session_state import (
    KEY_TAILOR_TAX_CG_BASE_YEAR,
    KEY_TAILOR_TAX_CG_BASELINE_RATE,
    KEY_TAILOR_TAX_CG_BASELINE_REALIZATIONS,
    KEY_TAILOR_TAX_CG_ELIMINATE_STEP_UP,
    KEY_TAILOR_TAX_CG_GAINS_AT_DEATH,
    KEY_TAILOR_TAX_CG_LOCK_IN_MULTIPLIER,
    KEY_TAILOR_TAX_CG_LONG_RUN_ELASTICITY,
    KEY_TAILOR_TAX_CG_REALIZATION_ELASTICITY,
    KEY_TAILOR_TAX_CG_SHORT_RUN_ELASTICITY,
    KEY_TAILOR_TAX_CG_STEP_UP_EXEMPTION,
    KEY_TAILOR_TAX_CG_TIME_VARYING,
    KEY_TAILOR_TAX_CG_TRANSITION_YEARS,
    KEY_TAILOR_TAX_CUSTOM_THRESHOLD,
    KEY_TAILOR_TAX_DURATION,
    KEY_TAILOR_TAX_ETI,
    KEY_TAILOR_TAX_MANUAL_AVG_INCOME,
    KEY_TAILOR_TAX_MANUAL_TAXPAYERS,
    KEY_TAILOR_TAX_ORDINARY_BASE,
    KEY_TAILOR_TAX_PHASE_IN,
    KEY_TAILOR_TAX_POLICY_NAME,
    KEY_TAILOR_TAX_RATE_CHANGE_PCT,
    KEY_TAILOR_TAX_THRESHOLD_CHOICE,
    KEY_TAILOR_TAX_TYPE,
    forget_widget_value,
    mirror_widget_value,
    restore_widget_value,
    seed_widget_default,
)

# Preset pickers above keep their historic ``sidebar_*`` keys (share links and
# tests/test_share_links.py depend on the literals); the custom-policy form
# below is newly keyed with the ``tailor_tax_*`` namespace.
_POLICY_AREA_KEY = "sidebar_policy_area"
_PRESET_CHOICE_KEY = "sidebar_preset_choice"


#: Policy-type options, in the order the Tailor segmented control shows them.
TAX_TYPE_OPTIONS: tuple[str, ...] = (
    "Income Tax Rate",
    "Capital Gains",
    "Corporate Tax",
    "Payroll Tax",
)


def _seed_widget_default(st_module: Any, key: str, default: Any) -> None:
    """Seed a widget key once, before the widget is instantiated.

    Every control in the custom-policy form used to be unkeyed, so its value
    lived only in Streamlit's positional widget identity and would be lost the
    moment the form moved to a different page. Giving each widget a stable key
    fixes that, but passing both ``key=`` and ``value=``/``index=`` triggers
    Streamlit's "created with a default value but also had its value set via
    Session State" warning once the key is pre-seeded. So: seed here, and omit
    the default on the widget. The rendered value is unchanged.

    A stable key is necessary but *not sufficient* under ``st.navigation``:
    Streamlit scopes widget state by ``active_script_hash`` and drops the state
    of widgets that did not render on the page just left, so a round trip
    through ``/explore`` re-seeded every field here to its default.
    ``seed_widget_default`` also mirrors the value to a plain (non-widget)
    session key and restores it — see ``ui/session_state.py``.
    """
    seed_widget_default(st_module, key, default)


def render_tax_policy_inputs(
    st_module: Any,
    preset_policies: dict[str, dict[str, Any]],
    use_preset: bool = True,
    default_preset: str | None = None,
    show_type_selector: bool = True,
) -> dict[str, Any]:
    """Render tax policy input controls and return selected values.

    ``show_type_selector=False`` is the Tailor layout: the page renders the
    policy-type choice as a segmented control at the top of its form card and
    writes ``tailor_tax_type`` itself, so this module must not instantiate a
    second widget on the same key (Streamlit raises ``DuplicateWidgetID``).
    """
    # ``default_preset`` reaches us from a URL (``?preset=tcja-full-extension``
    # or a legacy emoji label), a quick-start card, or a caller passing the
    # canonical label. Fold every spelling to the catalog key before it is used
    # as one — a stable id is not a ``PRESET_POLICIES`` key.
    if default_preset:
        default_preset = resolve_preset(default_preset) or default_preset

    # A lingering preset pre-selection (query param or quick-start card) must
    # never leak into Custom mode: scoring would silently use the preset and
    # ignore the user's custom inputs.
    preset_choice = (default_preset if use_preset else None) or "Custom Policy"

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

        area_key = _POLICY_AREA_KEY
        # Restore across a page switch *before* the stale-option guard, so the
        # guard judges the value the user actually chose.
        restore_widget_value(st_module, area_key)
        if (
            area_key in st_module.session_state
            and st_module.session_state[area_key] not in available_cats
        ):
            forget_widget_value(st_module, area_key)

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

        preset_key = _PRESET_CHOICE_KEY
        restore_widget_value(st_module, preset_key)
        if (
            preset_key in st_module.session_state
            and st_module.session_state[preset_key] not in short_names
        ):
            forget_widget_value(st_module, preset_key)

        selected_short = st_module.selectbox(
            "Select a proposal",
            options=list(short_names.keys()),
            index=list(short_names.keys()).index(default_short) if default_short in short_names else 0,
            key=preset_key,
            help="Each proposal is pre-configured with parameters matching official estimates.",
        )
        mirror_widget_value(st_module, area_key)
        mirror_widget_value(st_module, preset_key)

        preset_choice = short_names[selected_short]
        preset_data = preset_policies[preset_choice]

        cbo_score = _extract_cbo_score(preset_choice)
        if cbo_score:
            st_module.caption(f"Official estimate: {cbo_score}")

        from fiscal_model.ui.preset_validation import get_validation_badge

        badge = get_validation_badge(preset_choice)
        if badge:
            # Every preset in this map runs a calibrated specialized
            # validator, so a near-zero difference is agreement by
            # construction — label it that way instead of presenting a
            # "±0.0% (Excellent)" range that reads like an independent test.
            st_module.caption(
                f"{badge['icon']} Matches {badge['source']} within "
                f"{badge['signed_pct']:+.1f}% — calibrated to reproduce "
                f"this benchmark, not an independent test."
            )

        from fiscal_model.policy_status import get_policy_status

        policy_status = get_policy_status(preset_choice)
        if policy_status:
            st_module.caption(
                f"{policy_status.icon} **{policy_status.label}** — "
                f"{policy_status.note}"
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
    phase_in = 1
    manual_taxpayers = 0.0
    manual_avg_income = 0
    eti = 0.25
    ordinary_income_base = True

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

    if use_preset:
        # Specialized modules create their own policy via create_policy_from_preset.
        # Simple income-tax presets fall through to TaxPolicy construction, so mirror
        # rate / threshold / ETI / base selection from the preset dict here.
        rate_change_pct = float(preset_data.get("rate_change", 0.0) or 0.0)
        rate_change = rate_change_pct / 100.0
        threshold = int(preset_data.get("threshold", 0) or 0)
        duration = int(preset_data.get("duration_years", 10) or 10)
        phase_in = int(preset_data.get("phase_in_years", 1) or 1)
        eti = float(preset_data.get("eti", 0.25) or 0.25)
        ordinary_income_base = not bool(preset_data.get("agi_inclusive_base", False))

    if not use_preset:
        st_module.markdown("---")
        st_module.markdown("#### Define your policy")

        _seed_widget_default(st_module, KEY_TAILOR_TAX_POLICY_NAME, "Tax Rate Change")
        policy_name = st_module.text_input(
            "Policy name",
            key=KEY_TAILOR_TAX_POLICY_NAME,
            help="A short label for your policy (used in charts and exports).",
        )

        _seed_widget_default(st_module, KEY_TAILOR_TAX_TYPE, "Income Tax Rate")
        policy_type = st_module.session_state.get(KEY_TAILOR_TAX_TYPE, "Income Tax Rate")
        if show_type_selector:
            policy_type = st_module.selectbox(
                "What type of tax?",
                list(TAX_TYPE_OPTIONS),
                key=KEY_TAILOR_TAX_TYPE,
                help=(
                    "**Income Tax Rate** — changes to individual marginal rates  \n"
                    "**Capital Gains** — changes to rates on investment gains  \n"
                    "**Corporate Tax** — changes to the 21% corporate rate  \n"
                    "**Payroll Tax** — changes to Social Security / Medicare taxes"
                ),
            )

        st_module.markdown("##### Rate and scope")

        _seed_widget_default(st_module, KEY_TAILOR_TAX_RATE_CHANGE_PCT, -2.0)
        rate_change_pct = st_module.slider(
            "Rate change (percentage points)",
            min_value=-10.0,
            max_value=10.0,
            step=0.5,
            key=KEY_TAILOR_TAX_RATE_CHANGE_PCT,
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

        _seed_widget_default(
            st_module, KEY_TAILOR_TAX_THRESHOLD_CHOICE, "Top earners ($400K+)"
        )
        threshold_choice = st_module.selectbox(
            "Who is affected?",
            options=list(threshold_options.keys()),
            key=KEY_TAILOR_TAX_THRESHOLD_CHOICE,
            help=(
                "The income threshold above which the rate change applies. "
                "Only income *above* this threshold is affected — not total income."
            ),
        )
        if policy_type == "Corporate Tax":
            st_module.caption(
                "Corporate rate changes score off taxable profits, so there is "
                "no income threshold — this control is ignored."
            )

        if threshold_choice == "Custom amount":
            _seed_widget_default(st_module, KEY_TAILOR_TAX_CUSTOM_THRESHOLD, 400_000)
            threshold = st_module.number_input(
                "Custom income threshold ($)",
                min_value=0,
                max_value=10_000_000,
                step=50_000,
                format="%d",
                key=KEY_TAILOR_TAX_CUSTOM_THRESHOLD,
            )
        else:
            threshold = threshold_options[threshold_choice]

        with st_module.expander("Policy timing", expanded=False):
            _seed_widget_default(st_module, KEY_TAILOR_TAX_DURATION, 10)
            duration = st_module.slider(
                "Duration (years)",
                min_value=1,
                max_value=10,
                key=KEY_TAILOR_TAX_DURATION,
                help="Standard CBO budget window is 10 years.",
            )
            _seed_widget_default(st_module, KEY_TAILOR_TAX_PHASE_IN, 1)
            phase_in = st_module.slider(
                "Phase-in period (years)",
                min_value=1,
                max_value=5,
                key=KEY_TAILOR_TAX_PHASE_IN,
                help=(
                    "Years to gradually ramp up to the full rate change. "
                    "1 = full effect from the first year."
                ),
            )

        if policy_type == "Capital Gains":
            with st_module.expander("Capital gains parameters", expanded=True):
                st_module.caption(
                    "Capital gains have unique behavioral dynamics — investors can "
                    "defer realizations, so short-run revenue effects differ from "
                    "long-run. These parameters control that response."
                )

                _seed_widget_default(st_module, KEY_TAILOR_TAX_CG_BASE_YEAR, 2024)
                cg_base_year = st_module.selectbox(
                    "Baseline year",
                    [2024, 2023, 2022],
                    key=KEY_TAILOR_TAX_CG_BASE_YEAR,
                    help="Year from which to draw baseline realizations data.",
                )
                _seed_widget_default(st_module, KEY_TAILOR_TAX_CG_BASELINE_RATE, 0.238)
                baseline_cg_rate = st_module.number_input(
                    "Current effective CG rate",
                    min_value=0.0,
                    max_value=0.99,
                    step=0.01,
                    key=KEY_TAILOR_TAX_CG_BASELINE_RATE,
                    help="Current combined rate including NIIT (20% + 3.8% = 23.8% for top bracket).",
                )
                _seed_widget_default(
                    st_module, KEY_TAILOR_TAX_CG_BASELINE_REALIZATIONS, 0.0
                )
                baseline_realizations = st_module.number_input(
                    "Baseline realizations ($B/year)",
                    min_value=0.0,
                    max_value=10000.0,
                    step=10.0,
                    key=KEY_TAILOR_TAX_CG_BASELINE_REALIZATIONS,
                    help="Total taxable realizations. Leave at 0 to auto-populate from IRS data.",
                )

                st_module.markdown("**Behavioral elasticity**")
                st_module.caption(
                    "How much do investors change behavior in response to rate changes? "
                    "CBO uses ~0.7-1.0 short-run, ~0.3-0.5 long-run "
                    "([CBO 2012](https://www.cbo.gov/publication/43334))."
                )

                _seed_widget_default(st_module, KEY_TAILOR_TAX_CG_TIME_VARYING, True)
                use_time_varying = st_module.checkbox(
                    "Use time-varying elasticity (recommended)",
                    key=KEY_TAILOR_TAX_CG_TIME_VARYING,
                    help="Short-run: timing effects dominate. Long-run: only permanent responses remain.",
                )

                if use_time_varying:
                    _seed_widget_default(
                        st_module, KEY_TAILOR_TAX_CG_SHORT_RUN_ELASTICITY, 0.8
                    )
                    short_run_elasticity = st_module.number_input(
                        "Short-run elasticity (years 1-3)",
                        step=0.1,
                        key=KEY_TAILOR_TAX_CG_SHORT_RUN_ELASTICITY,
                        help="Higher because investors can time when to sell.",
                    )
                    _seed_widget_default(
                        st_module, KEY_TAILOR_TAX_CG_LONG_RUN_ELASTICITY, 0.4
                    )
                    long_run_elasticity = st_module.number_input(
                        "Long-run elasticity (years 4+)",
                        step=0.1,
                        key=KEY_TAILOR_TAX_CG_LONG_RUN_ELASTICITY,
                        help="Lower because timing effects have dissipated.",
                    )
                    _seed_widget_default(st_module, KEY_TAILOR_TAX_CG_TRANSITION_YEARS, 3)
                    transition_years = st_module.slider(
                        "Transition period (years)",
                        min_value=1,
                        max_value=5,
                        key=KEY_TAILOR_TAX_CG_TRANSITION_YEARS,
                    )
                    realization_elasticity = (
                        short_run_elasticity + long_run_elasticity
                    ) / 2
                else:
                    _seed_widget_default(
                        st_module, KEY_TAILOR_TAX_CG_REALIZATION_ELASTICITY, 0.5
                    )
                    realization_elasticity = st_module.number_input(
                        "Realization elasticity (constant)",
                        step=0.05,
                        key=KEY_TAILOR_TAX_CG_REALIZATION_ELASTICITY,
                    )
                    short_run_elasticity = realization_elasticity
                    long_run_elasticity = realization_elasticity
                    transition_years = 1

                st_module.markdown("**Step-up basis at death**")
                st_module.caption(
                    "Under current law, unrealized gains are forgiven at death "
                    "(\"stepped-up basis\"). This creates a strong incentive to hold assets rather than sell."
                )
                _seed_widget_default(
                    st_module, KEY_TAILOR_TAX_CG_ELIMINATE_STEP_UP, False
                )
                eliminate_step_up = st_module.checkbox(
                    "Eliminate step-up at death",
                    key=KEY_TAILOR_TAX_CG_ELIMINATE_STEP_UP,
                    help="Tax unrealized gains at death (Biden proposed a $1M exemption).",
                )
                if eliminate_step_up:
                    _seed_widget_default(
                        st_module, KEY_TAILOR_TAX_CG_STEP_UP_EXEMPTION, 1_000_000
                    )
                    step_up_exemption = st_module.number_input(
                        "Exemption per decedent ($)",
                        step=100_000,
                        key=KEY_TAILOR_TAX_CG_STEP_UP_EXEMPTION,
                    )
                    _seed_widget_default(
                        st_module, KEY_TAILOR_TAX_CG_GAINS_AT_DEATH, 54.0
                    )
                    gains_at_death = st_module.number_input(
                        "Annual gains at death ($B)",
                        step=5.0,
                        key=KEY_TAILOR_TAX_CG_GAINS_AT_DEATH,
                        help="CBO estimates ~$54B/year in unrealized gains transferred at death.",
                    )
                    step_up_lock_in_multiplier = 1.0
                else:
                    step_up_exemption = 0.0
                    gains_at_death = 54.0
                    _seed_widget_default(
                        st_module, KEY_TAILOR_TAX_CG_LOCK_IN_MULTIPLIER, 2.0
                    )
                    step_up_lock_in_multiplier = st_module.slider(
                        "Lock-in multiplier",
                        min_value=1.0,
                        max_value=6.0,
                        step=0.5,
                        key=KEY_TAILOR_TAX_CG_LOCK_IN_MULTIPLIER,
                        help="How much step-up increases the incentive to defer. 2.0 = calibrated to Penn Wharton estimates.",
                    )
        else:
            with st_module.expander("Advanced parameters", expanded=False):
                st_module.caption(
                    "These are auto-populated from IRS Statistics of Income data when left at zero. "
                    "Override only if you have specific values."
                )
                _seed_widget_default(st_module, KEY_TAILOR_TAX_MANUAL_TAXPAYERS, 0.0)
                manual_taxpayers = st_module.number_input(
                    "Affected taxpayers (millions)",
                    min_value=0.0,
                    max_value=200.0,
                    step=0.1,
                    key=KEY_TAILOR_TAX_MANUAL_TAXPAYERS,
                    help="Number of tax filers above the income threshold. Leave at 0 to pull from IRS SOI Table 1.1 automatically.",
                )
                _seed_widget_default(st_module, KEY_TAILOR_TAX_MANUAL_AVG_INCOME, 0)
                manual_avg_income = st_module.number_input(
                    "Average taxable income ($)",
                    min_value=0,
                    max_value=100_000_000,
                    step=50_000,
                    key=KEY_TAILOR_TAX_MANUAL_AVG_INCOME,
                    help="Mean AGI of affected filers. Leave at 0 to pull from IRS SOI data automatically.",
                )
                _seed_widget_default(st_module, KEY_TAILOR_TAX_ETI, 0.25)
                eti = st_module.number_input(
                    "Elasticity of Taxable Income (ETI)",
                    min_value=0.0,
                    max_value=2.0,
                    step=0.05,
                    key=KEY_TAILOR_TAX_ETI,
                    help=(
                        "How much taxable income changes in response to tax rate changes. "
                        "The consensus estimate is **0.25** "
                        "([Saez, Slemrod & Giertz 2012](https://eml.berkeley.edu/~saez/saez-slemrod-giertzJEL12.pdf)). "
                        "Higher = more behavioral response = less revenue."
                    ),
                )
                _seed_widget_default(st_module, KEY_TAILOR_TAX_ORDINARY_BASE, True)
                ordinary_income_base = st_module.checkbox(
                    "Ordinary-income base (exclude LTCG/QDIV)",
                    key=KEY_TAILOR_TAX_ORDINARY_BASE,
                    help=(
                        "Ordinary-bracket rate changes do not apply to long-term capital "
                        "gains or qualified dividends. Uncheck for AGI-inclusive surtaxes "
                        "that tax all income above the threshold."
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
        "ordinary_income_base": ordinary_income_base,
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
