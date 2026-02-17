"""
Policy input helpers for the tab1 workflow.
"""

from __future__ import annotations

from typing import Any


def render_tax_policy_inputs(st_module: Any, preset_policies: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """
    Render tax policy input controls and return selected values.
    """
    st_module.subheader("🎯 Quick Start: Choose a Preset Policy")

    col_preset, col_info = st_module.columns([2, 3])
    with col_preset:
        preset_choice = st_module.selectbox(
            "Select a policy to analyze",
            options=list(preset_policies.keys()),
            help="Choose a real-world or example policy, or select 'Custom' to design your own",
        )

    with col_info:
        if preset_choice != "Custom Policy":
            st_module.info(f"📋 **{preset_choice}**\n\n{preset_policies[preset_choice]['description']}")

    st_module.markdown(
        """
        <div class="info-box">
        💡 <strong>How it works:</strong> The calculator uses real IRS data to automatically determine
        how many taxpayers are affected and calculates the revenue impact using CBO methodology.
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st_module.columns(2)
    with col1:
        st_module.subheader("Policy Parameters")
        preset_data = preset_policies[preset_choice]

        default_name = preset_choice if preset_choice != "Custom Policy" else "Tax Rate Change"
        policy_name = st_module.text_input("Policy Name", default_name, help="A short name for this policy")

        rate_change_pct = st_module.slider(
            "Tax Rate Change (percentage points)",
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

    with col2:
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

        with st_module.expander("🔧 Expert Parameters (Elasticities & Data)", expanded=False):
            if policy_type == "Capital Gains":
                st_module.markdown(
                    "*Capital gains requires a realizations base + baseline rate (IRS SOI tables here do not include realizations).*"
                )
            else:
                st_module.markdown("*Leave blank to auto-populate from IRS data*")

            manual_taxpayers = st_module.number_input(
                "Affected taxpayers (millions)",
                min_value=0.0,
                max_value=200.0,
                value=0.0,
                step=0.1,
                help="Leave at 0 to auto-populate from IRS data",
            )
            manual_avg_income = st_module.number_input(
                "Average taxable income in bracket ($)",
                min_value=0,
                max_value=100000000,
                value=0,
                step=50000,
                help="Leave at 0 to auto-populate from IRS data",
            )
            eti = st_module.number_input(
                "Elasticity of Taxable Income (ETI)",
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
                st_module.markdown("**Capital Gains (Realizations Model)**")
                cg_base_year = st_module.selectbox(
                    "Capital gains baseline year",
                    options=[2024, 2023, 2022],
                    index=0,
                    help="2022 uses IRS SOI preliminary net capital gain by AGI; 2023/2024 are estimated by scaling 2022 shares to Tax Foundation totals.",
                )
                cg_rate_source = st_module.selectbox(
                    "Baseline rate source",
                    options=[
                        "Statutory/NIIT proxy (by AGI bracket)",
                        "Tax Foundation avg effective (aggregate)",
                    ],
                    index=0,
                    help=(
                        "Statutory proxy computes a weighted baseline rate using AGI brackets (IRS) + a documented rate mapping. "
                        "Tax Foundation uses a single year-level effective rate (not by AGI). "
                        "Tax Foundation source: https://taxfoundation.org/data/all/federal/federal-capital-gains-tax-collections-historical-data/"
                    ),
                )
                baseline_cg_rate = st_module.number_input(
                    "Baseline capital gains tax rate",
                    min_value=0.0,
                    max_value=0.99,
                    value=0.20,
                    step=0.01,
                    help="Assumed baseline effective marginal capital gains rate for the affected group",
                )
                baseline_realizations = st_module.number_input(
                    "Baseline taxable capital gains realizations ($B/year)",
                    min_value=0.0,
                    max_value=10000.0,
                    value=0.0,
                    step=10.0,
                    help="If left at 0 and real-data is enabled, we'll auto-populate from IRS/Treasury-derived series (with documented assumptions).",
                )

                st_module.markdown("**Behavioral Response (Time-Varying Elasticity)**")
                use_time_varying = st_module.checkbox(
                    "Use time-varying elasticity",
                    value=True,
                    help="Short-run elasticity is higher (timing effects), long-run is lower (permanent response only). Based on CBO/JCT methodology.",
                )

                if use_time_varying:
                    col_sr, col_lr = st_module.columns(2)
                    with col_sr:
                        short_run_elasticity = st_module.number_input(
                            "Short-run elasticity (years 1-3)",
                            min_value=0.0,
                            max_value=3.0,
                            value=0.8,
                            step=0.1,
                            help="Higher elasticity in early years due to timing/anticipation effects. CBO: 0.7-1.0",
                        )
                    with col_lr:
                        long_run_elasticity = st_module.number_input(
                            "Long-run elasticity (years 4+)",
                            min_value=0.0,
                            max_value=2.0,
                            value=0.4,
                            step=0.1,
                            help="Lower elasticity once timing effects are exhausted. Literature: 0.3-0.5",
                        )
                    transition_years = st_module.slider(
                        "Transition period (years)",
                        min_value=1,
                        max_value=5,
                        value=3,
                        help="Years to transition from short-run to long-run elasticity",
                    )
                    realization_elasticity = (short_run_elasticity + long_run_elasticity) / 2
                else:
                    realization_elasticity = st_module.number_input(
                        "Realization elasticity (constant)",
                        min_value=0.0,
                        max_value=5.0,
                        value=0.5,
                        step=0.05,
                        help="Single elasticity value for all years (timing/lock-in response)",
                    )
                    short_run_elasticity = realization_elasticity
                    long_run_elasticity = realization_elasticity
                    transition_years = 1

                st_module.markdown("**Step-Up Basis at Death**")
                st_module.info(
                    "Under current law, unrealized capital gains are forgiven at death (step-up basis). "
                    "This creates strong incentive to hold assets until death, reducing realizations. "
                    "Eliminating step-up would tax gains at death and reduce lock-in."
                )

                eliminate_step_up = st_module.checkbox(
                    "Eliminate step-up basis at death",
                    value=False,
                    help="Tax unrealized capital gains at death (Biden proposal). Creates new revenue stream.",
                )

                if eliminate_step_up:
                    col_ex, col_gains = st_module.columns(2)
                    with col_ex:
                        step_up_exemption = st_module.number_input(
                            "Exemption per decedent ($)",
                            min_value=0,
                            max_value=10_000_000,
                            value=1_000_000,
                            step=100_000,
                            help="Biden proposal: $1M exemption. Gains below this are not taxed at death.",
                        )
                    with col_gains:
                        gains_at_death = st_module.number_input(
                            "Annual gains at death ($B)",
                            min_value=0.0,
                            max_value=200.0,
                            value=54.0,
                            step=5.0,
                            help="CBO estimates ~$54B/year in unrealized gains transferred at death.",
                        )
                    step_up_lock_in_multiplier = 1.0
                else:
                    step_up_exemption = 0.0
                    gains_at_death = 54.0
                    step_up_lock_in_multiplier = st_module.slider(
                        "Step-up lock-in multiplier",
                        min_value=1.0,
                        max_value=6.0,
                        value=2.0,
                        step=0.5,
                        help="How much step-up increases deferral. 5.3x matches PWBM. Higher = more lock-in.",
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
    st_module.subheader("🎯 Spending Program Calculator")

    st_module.markdown(
        """
        <div class="info-box">
        💡 <strong>Analyze spending programs:</strong> Calculate the budgetary impact of federal spending increases or cuts
        across different categories (infrastructure, defense, social programs, etc.).
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st_module.columns(2)

    with col1:
        st_module.subheader("Program Parameters")
        program_name = st_module.text_input(
            "Program Name",
            "Infrastructure Investment",
            help="A short name for this spending program",
        )

        annual_spending = st_module.number_input(
            "Annual Spending (Billions)",
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

    with col2:
        st_module.subheader("Economic Parameters")
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

    with st_module.expander("📋 Example Programs"):
        st_module.markdown(
            """
            **Infrastructure:**
            - $100B/year × 10 years (Biden Infrastructure Plan ~$110B/year)
            - Multiplier: 1.5

            **Defense Increase:**
            - $50B/year increase
            - Multiplier: 1.0

            **Social Program Expansion:**
            - $200B/year (e.g., childcare, paid leave)
            - Multiplier: 0.8

            **Disaster Relief:**
            - $50B one-time
            - Multiplier: 1.2
            """
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
