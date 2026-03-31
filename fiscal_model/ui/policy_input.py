"""
Policy input helpers — sidebar UI for selecting and configuring policies.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Preset category helpers
# ---------------------------------------------------------------------------

_CATEGORY_ORDER = [
    "TCJA / Individual",
    "Corporate",
    "International Tax",
    "Tax Credits",
    "Estate Tax",
    "Payroll / SS",
    "AMT",
    "ACA / Healthcare",
    "Tax Expenditures",
    "IRS Enforcement",
    "Drug Pricing",
    "Trade / Tariffs",
    "Climate / Energy",
    "Income Tax",
]


def _preset_category(preset: dict[str, Any]) -> str:
    if preset.get("is_tcja"):
        return "TCJA / Individual"
    if preset.get("is_corporate"):
        return "Corporate"
    if preset.get("is_international"):
        return "International Tax"
    if preset.get("is_credit"):
        return "Tax Credits"
    if preset.get("is_estate"):
        return "Estate Tax"
    if preset.get("is_payroll"):
        return "Payroll / SS"
    if preset.get("is_amt"):
        return "AMT"
    if preset.get("is_ptc"):
        return "ACA / Healthcare"
    if preset.get("is_expenditure"):
        return "Tax Expenditures"
    if preset.get("is_enforcement"):
        return "IRS Enforcement"
    if preset.get("is_pharma"):
        return "Drug Pricing"
    if preset.get("is_trade"):
        return "Trade / Tariffs"
    if preset.get("is_climate"):
        return "Climate / Energy"
    return "Income Tax"


def _strip_emoji_prefix(name: str) -> str:
    """Remove leading emoji + space from preset names for cleaner display."""
    for ch in name:
        if ch.isalpha() or ch == "(":
            return name[name.index(ch):]
    return name


# ---------------------------------------------------------------------------
# Tax policy inputs
# ---------------------------------------------------------------------------

def render_tax_policy_inputs(
    st_module: Any, preset_policies: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Render tax policy input controls and return selected values."""

    # ── Step 1: Choose a starting point ──────────────────────────────────
    approach = st_module.radio(
        "How would you like to start?",
        ["Analyze a known proposal", "Design a custom policy"],
        index=0,
        help=(
            "**Known proposal** — pick from 25+ real-world policies already "
            "calibrated to CBO/JCT estimates.  \n"
            "**Custom policy** — set your own tax rate change, threshold, and parameters."
        ),
    )
    use_preset = approach == "Analyze a known proposal"

    # ── Preset path ──────────────────────────────────────────────────────
    preset_choice = "Custom Policy"

    if use_preset:
        # Group presets by category for easy scanning
        categorized: dict[str, list[str]] = {}
        for name, data in preset_policies.items():
            if name == "Custom Policy":
                continue
            cat = _preset_category(data)
            categorized.setdefault(cat, []).append(name)

        # Category filter
        available_cats = [c for c in _CATEGORY_ORDER if c in categorized]
        selected_cat = st_module.selectbox(
            "Policy area",
            options=available_cats,
            index=0,
            help="Filter proposals by policy area.",
        )

        # Preset selector (within category)
        cat_presets = categorized.get(selected_cat, [])
        display_names = {_strip_emoji_prefix(n): n for n in cat_presets}

        selected_display = st_module.selectbox(
            "Select a proposal",
            options=list(display_names.keys()),
            help="Each proposal is pre-configured with parameters matching official estimates.",
        )
        preset_choice = display_names[selected_display]
        preset_data = preset_policies[preset_choice]

        # Show what this preset does with fiscal direction indicator
        display_name = _strip_emoji_prefix(preset_choice)
        desc = preset_data["description"]

        # Use the CBO score sign from the preset name to determine direction
        # Names like "(CBO: -$1.35T)" indicate revenue-raising (negative = reduces deficit)
        # Names like "(CBO: $4.6T)" indicate deficit-increasing (positive = costs money)
        import re as _re
        score_match = _re.search(r'\((?:CBO|JCT):\s*(-?\$[\d.]+[TB])\)', preset_choice)
        if score_match and score_match.group(1).startswith("-"):
            st_module.success(f"**{display_name}**\n\n{desc}")
        elif score_match:
            st_module.warning(f"**{display_name}**\n\n{desc}")
        else:
            st_module.info(f"**{display_name}**\n\n{desc}")

        # Show the methodology note
        with st_module.expander("How is this scored?", expanded=False):
            st_module.markdown(
                "This proposal uses a **pre-calibrated model** that matches "
                "the official CBO/JCT/Treasury score. The calculator applies:\n\n"
                "1. **Static scoring** — direct revenue effect of the policy change\n"
                "2. **Behavioral response** — how taxpayers adjust (e.g., work less, "
                "shift income) based on the Elasticity of Taxable Income (ETI = 0.25, "
                "[Saez et al. 2012](https://eml.berkeley.edu/~saez/saez-slemrod-giertzJEL12.pdf))\n"
                "3. **Dynamic feedback** *(optional)* — GDP and employment effects "
                "using FRB/US-calibrated multipliers\n\n"
                "Data sources: IRS Statistics of Income, FRED, CBO Baseline Projections."
            )

    # ── Custom path ──────────────────────────────────────────────────────
    # Default values for the return dict
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

    # Capital gains defaults
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
            index=4,  # Default to $400K+
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

        # ── Policy timing ────────────────────────────────────────────────
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

        # ── Capital gains–specific parameters ────────────────────────────
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
                    help="Current combined rate including NIIT "
                    "(20% + 3.8% = 23.8% for top bracket).",
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
                    help="Short-run: timing effects dominate. "
                    "Long-run: only permanent responses remain.",
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
                        "Transition period (years)", min_value=1, max_value=5, value=3,
                    )
                    realization_elasticity = (short_run_elasticity + long_run_elasticity) / 2
                else:
                    realization_elasticity = st_module.number_input(
                        "Realization elasticity (constant)", value=0.5, step=0.05,
                    )
                    short_run_elasticity = realization_elasticity
                    long_run_elasticity = realization_elasticity
                    transition_years = 1

                st_module.markdown("**Step-up basis at death**")
                st_module.caption(
                    "Under current law, unrealized gains are forgiven at death "
                    "(\"stepped-up basis\"). This creates a strong incentive to hold "
                    "assets rather than sell."
                )
                eliminate_step_up = st_module.checkbox(
                    "Eliminate step-up at death",
                    value=False,
                    help="Tax unrealized gains at death (Biden proposed a $1M exemption).",
                )
                if eliminate_step_up:
                    step_up_exemption = st_module.number_input(
                        "Exemption per decedent ($)", value=1_000_000, step=100_000,
                    )
                    gains_at_death = st_module.number_input(
                        "Annual gains at death ($B)", value=54.0, step=5.0,
                        help="CBO estimates ~$54B/year in unrealized gains transferred at death.",
                    )
                    step_up_lock_in_multiplier = 1.0
                else:
                    step_up_exemption = 0.0
                    gains_at_death = 54.0
                    step_up_lock_in_multiplier = st_module.slider(
                        "Lock-in multiplier",
                        min_value=1.0, max_value=6.0, value=2.0, step=0.5,
                        help=(
                            "How much step-up increases the incentive to defer. "
                            "2.0 = calibrated to Penn Wharton estimates."
                        ),
                    )

        # ── Income tax expert parameters ─────────────────────────────────
        else:
            with st_module.expander("Advanced parameters", expanded=False):
                st_module.caption(
                    "These are auto-populated from IRS Statistics of Income data when "
                    "left at zero. Override only if you have specific values."
                )
                manual_taxpayers = st_module.number_input(
                    "Affected taxpayers (millions)",
                    min_value=0.0,
                    max_value=200.0,
                    value=0.0,
                    step=0.1,
                    help=(
                        "Number of tax filers above the income threshold. "
                        "Leave at 0 to pull from IRS SOI Table 1.1 automatically."
                    ),
                )
                manual_avg_income = st_module.number_input(
                    "Average taxable income ($)",
                    min_value=0,
                    max_value=100_000_000,
                    value=0,
                    step=50_000,
                    help=(
                        "Mean AGI of affected filers. "
                        "Leave at 0 to pull from IRS SOI data automatically."
                    ),
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
                        "([Saez, Slemrod & Giertz 2012]"
                        "(https://eml.berkeley.edu/~saez/saez-slemrod-giertzJEL12.pdf)). "
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


# ---------------------------------------------------------------------------
# Spending policy inputs
# ---------------------------------------------------------------------------

def render_spending_policy_inputs(st_module: Any) -> dict[str, Any]:
    """Render spending policy input controls and return selected values."""

    st_module.markdown("#### Define spending program")

    program_name = st_module.text_input(
        "Program name",
        "Infrastructure Investment",
        help="A short label for this spending program.",
    )

    annual_spending = st_module.number_input(
        "Annual spending change ($B)",
        min_value=-500.0,
        max_value=500.0,
        value=100.0,
        step=10.0,
        help="**Positive** = spending increase, **Negative** = spending cut.",
    )

    spending_category = st_module.selectbox(
        "Category",
        [
            "Infrastructure",
            "Defense",
            "Non-Defense Discretionary",
            "Mandatory Programs",
            "Social Security",
            "Medicare",
            "Medicaid",
            "Education",
            "Research & Development",
        ],
        help="Affects baseline projections used for scoring.",
    )

    with st_module.expander("Economic parameters", expanded=False):
        st_module.caption(
            "These control how the spending flows through the economy. "
            "Defaults are based on empirical estimates from CBO and the "
            "economics literature."
        )
        duration = st_module.slider(
            "Duration (years)",
            min_value=1,
            max_value=10,
            value=10,
            help="Standard CBO budget window is 10 years.",
        )

        growth_rate = st_module.slider(
            "Annual real growth rate (%)",
            min_value=-5.0,
            max_value=10.0,
            value=2.0,
            step=0.5,
            help="How fast spending grows each year after the first.",
        ) / 100

        multiplier = st_module.slider(
            "Fiscal multiplier",
            min_value=0.0,
            max_value=2.0,
            value=1.0,
            step=0.1,
            help=(
                "GDP impact per dollar spent. Typical values: "
                "infrastructure ~1.5, defense ~1.0, transfers ~0.8. "
                "([CBO 2015 estimates](https://www.cbo.gov/publication/49958))"
            ),
        )

        is_one_time = st_module.checkbox(
            "One-time expenditure",
            value=False,
            help="Check for one-time spending (e.g., disaster relief) rather than recurring.",
        )

    return {
        "program_name": program_name,
        "annual_spending": annual_spending,
        "spending_category": spending_category,
        "duration": duration,
        "growth_rate": growth_rate,
        "multiplier": multiplier,
        "is_one_time": is_one_time,
    }


def calculate_spending_policy_result(
    spending_inputs: dict[str, Any],
    spending_policy_cls: Any,
    policy_type_discretionary_nondefense: Any,
    fiscal_policy_scorer_cls: Any,
    use_real_data: bool,
    dynamic_scoring: bool,
) -> dict[str, Any]:
    """Build and score a spending policy from UI inputs."""
    policy = spending_policy_cls(
        name=spending_inputs["program_name"],
        description=(
            f"${spending_inputs['annual_spending']:+.1f}B annual spending for "
            f"{spending_inputs['spending_category']}"
        ),
        policy_type=policy_type_discretionary_nondefense,
        annual_spending_change_billions=spending_inputs["annual_spending"],
        annual_growth_rate=spending_inputs["growth_rate"],
        gdp_multiplier=spending_inputs["multiplier"],
        is_one_time=spending_inputs["is_one_time"],
        category="nondefense",
        duration_years=spending_inputs["duration"],
    )

    scorer = fiscal_policy_scorer_cls(baseline=None, use_real_data=use_real_data)
    result = scorer.score_policy(policy, dynamic=dynamic_scoring)

    return {
        "policy": policy,
        "result": result,
        "scorer": scorer,
        "is_spending": True,
    }
