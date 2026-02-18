"""
Policy input helpers for the tab1 workflow.
"""

from __future__ import annotations

from typing import Any


def render_tax_policy_inputs(st_module: Any, preset_policies: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """
    Render tax policy input controls and return selected values.
    """
    st_module.markdown("### 🎯 Quick Start")
    
    preset_choice = st_module.selectbox(
        "Select a policy to analyze",
        options=list(preset_policies.keys()),
        help="Choose a real-world or example policy, or select 'Custom' to design your own",
    )

    if preset_choice != "Custom Policy":
        st_module.info(f"📋 **{preset_choice}**\n\n{preset_policies[preset_choice]['description']}")

    st_module.markdown("---")
    st_module.markdown("### ⚙️ Policy Parameters")
    
    preset_data = preset_policies[preset_choice]

    default_name = preset_choice if preset_choice != "Custom Policy" else "Tax Rate Change"
    policy_name = st_module.text_input("Policy Name", default_name, help="A short name for this policy")

    rate_change_pct = st_module.slider(
        "Tax Rate Change (pp)",
        min_value=-10.0,
        max_value=10.0,
        value=preset_data["rate_change"],
        step=0.5,
        help="Positive = tax increase, Negative = tax cut",
    )
    rate_change = rate_change_pct / 100

    threshold_options = {
        "All taxpayers ($0+)": 0,
        "Middle class ($50K+)": 50000,
        "Upper-middle ($100K+)": 100000,
        "High earners ($200K+)": 200000,
        "Biden threshold ($400K+)": 400000,
        "Very high ($500K+)": 500000,
        "Millionaires ($1M+)": 1000000,
        "Multi-millionaires ($5M+)": 5000000,
        "Custom": None,
    }

    preset_threshold = preset_data["threshold"]
    default_threshold_idx = 0
    for idx, (_, value) in enumerate(threshold_options.items()):
        if value == preset_threshold:
            default_threshold_idx = idx
            break

    threshold_choice = st_module.selectbox(
        "Who is affected?",
        options=list(threshold_options.keys()),
        index=default_threshold_idx,
        help="Income threshold for who the policy applies to",
    )

    if threshold_choice == "Custom":
        threshold = st_module.number_input(
            "Custom threshold ($)",
            min_value=0,
            max_value=10000000,
            value=500000,
            step=50000,
            format="%d",
        )
    else:
        threshold = threshold_options[threshold_choice]

    with st_module.expander("📝 Policy Details & Timing", expanded=False):
        policy_type = st_module.selectbox(
            "Policy Type",
            ["Income Tax Rate", "Capital Gains", "Corporate Tax", "Payroll Tax"],
            help="Type of tax being changed",
        )
        duration = st_module.slider(
            "Policy Duration (years)",
            min_value=1,
            max_value=10,
            value=10,
            help="How long the policy lasts (CBO standard is 10 years)",
        )
        phase_in = st_module.slider(
            "Phase-in Period (years)",
            min_value=0,
            max_value=5,
            value=0,
            help="Years to gradually phase in the full policy (0 = immediate)",
        )

    with st_module.expander("🔧 Expert Parameters", expanded=False):
        if policy_type == "Capital Gains":
            st_module.caption(
                "*Capital gains requires a realizations base + baseline rate.*"
            )
        else:
            st_module.caption("*Leave blank to auto-populate from IRS data*")

        manual_taxpayers = st_module.number_input(
            "Affected taxpayers (millions)",
            min_value=0.0,
            max_value=200.0,
            value=0.0,
            step=0.1,
            help="Leave at 0 to auto-populate from IRS data",
        )
        manual_avg_income = st_module.number_input(
            "Average taxable income ($)",
            min_value=0,
            max_value=100000000,
            value=0,
            step=50000,
            help="Leave at 0 to auto-populate from IRS data",
        )
        eti = st_module.number_input(
            "Elasticity (ETI)",
            min_value=0.0,
            max_value=2.0,
            value=0.25,
            step=0.05,
            help="Behavioral response parameter (0.25 = moderate response)",
        )

        cg_base_year = 2024
        cg_rate_source = "Statutory/NIIT proxy (by AGI bracket)"
        baseline_cg_rate = 0.20
        baseline_realizations = 0.0
        use_time_varying = True
        short_run_elasticity = 0.8
        long_run_elasticity = 0.4
        transition_years = 3
        realization_elasticity = (short_run_elasticity + long_run_elasticity) / 2
        eliminate_step_up = False
        step_up_exemption = 0.0
        gains_at_death = 54.0
        step_up_lock_in_multiplier = 2.0

        if policy_type == "Capital Gains":
            st_module.markdown("**Capital Gains Model**")
            cg_base_year = st_module.selectbox(
                "Baseline year",
                options=[2024, 2023, 2022],
                index=0,
            )
            cg_rate_source = st_module.selectbox(
                "Baseline rate source",
                options=[
                    "Statutory/NIIT proxy (by AGI bracket)",
                    "Tax Foundation avg effective (aggregate)",
                ],
                index=0,
            )
            baseline_cg_rate = st_module.number_input(
                "Baseline CG tax rate",
                min_value=0.0,
                max_value=0.99,
                value=0.20,
                step=0.01,
            )
            baseline_realizations = st_module.number_input(
                "Baseline realizations ($B)",
                min_value=0.0,
                max_value=10000.0,
                value=0.0,
                step=10.0,
            )

            use_time_varying = st_module.checkbox(
                "Time-varying elasticity",
                value=True,
            )

            if use_time_varying:
                short_run_elasticity = st_module.number_input(
                    "Short-run elasticity",
                    value=0.8,
                    step=0.1,
                )
                long_run_elasticity = st_module.number_input(
                    "Long-run elasticity",
                    value=0.4,
                    step=0.1,
                )
                transition_years = st_module.slider(
                    "Transition (years)",
                    min_value=1,
                    max_value=5,
                    value=3,
                )
                realization_elasticity = (short_run_elasticity + long_run_elasticity) / 2
            else:
                realization_elasticity = st_module.number_input(
                    "Realization elasticity",
                    value=0.5,
                    step=0.05,
                )
                short_run_elasticity = realization_elasticity
                long_run_elasticity = realization_elasticity
                transition_years = 1

            st_module.markdown("**Step-Up Basis**")
            eliminate_step_up = st_module.checkbox(
                "Eliminate step-up at death",
                value=False,
            )

            if eliminate_step_up:
                step_up_exemption = st_module.number_input(
                    "Exemption ($)",
                    value=1_000_000,
                    step=100_000,
                )
                gains_at_death = st_module.number_input(
                    "Gains at death ($B)",
                    value=54.0,
                    step=5.0,
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
        "cg_rate_source": cg_rate_source,
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


def render_spending_policy_inputs(st_module: Any) -> dict[str, Any]:
    """
    Render spending policy input controls and return selected values.
    """
    st_module.markdown("### 🎯 Spending Program")

    st_module.markdown("### ⚙️ Program Parameters")
    program_name = st_module.text_input(
        "Program Name",
        "Infrastructure Investment",
        help="A short name for this spending program",
    )

    annual_spending = st_module.number_input(
        "Annual Spending ($B)",
        min_value=-500.0,
        max_value=500.0,
        value=100.0,
        step=10.0,
        help="Positive = increase spending, Negative = cut spending",
    )

    spending_category = st_module.selectbox(
        "Spending Category",
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
        help="Type of spending program",
    )

    st_module.markdown("### 📈 Economic Parameters")
    duration = st_module.slider(
        "Program Duration (years)",
        min_value=1,
        max_value=10,
        value=10,
        help="How long the program lasts",
    )

    growth_rate = st_module.slider(
        "Annual Growth Rate (%)",
        min_value=-5.0,
        max_value=10.0,
        value=2.0,
        step=0.5,
        help="Real growth rate of spending over time",
    ) / 100

    multiplier = st_module.slider(
        "Fiscal Multiplier",
        min_value=0.0,
        max_value=2.0,
        value=1.0,
        step=0.1,
        help="GDP impact per dollar spent (infrastructure ~1.5, transfers ~0.8)",
    )

    is_one_time = st_module.checkbox(
        "One-time spending",
        value=False,
        help="Check if this is a one-time expense (like disaster relief)",
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
    """
    Build and score a spending policy from UI inputs.
    """
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
