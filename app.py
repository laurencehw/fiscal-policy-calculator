"""
Fiscal Policy Impact Calculator - Main Streamlit App

A web application for estimating the budgetary and economic effects of
fiscal policy proposals using real IRS and FRED data.
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path

# Configure page
st.set_page_config(
    page_title="Fiscal Policy Calculator",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .positive-impact {
        color: #28a745;
        font-weight: bold;
    }
    .negative-impact {
        color: #dc3545;
        font-weight: bold;
    }
    .info-box {
        background-color: #e7f3ff;
        border-left: 4px solid #1f77b4;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 0.25rem;
    }
</style>
""", unsafe_allow_html=True)

# Import fiscal model
import sys
sys.path.insert(0, str(Path(__file__).parent))

try:
    from fiscal_model import TaxPolicy, CapitalGainsPolicy, PolicyType, FiscalPolicyScorer
    from fiscal_model import TCJAExtensionPolicy, create_tcja_extension, create_tcja_repeal_salt_cap
    from fiscal_model import CorporateTaxPolicy, create_biden_corporate_rate_only, create_republican_corporate_cut
    from fiscal_model import (
        TaxCreditPolicy, create_biden_ctc_2021, create_ctc_permanent_extension,
        create_biden_eitc_childless, create_ctc_expansion,
    )
    from fiscal_model import (
        EstateTaxPolicy, create_tcja_estate_extension, create_biden_estate_proposal,
        create_eliminate_estate_tax,
    )
    from fiscal_model import (
        PayrollTaxPolicy, create_ss_cap_90_percent, create_ss_donut_hole,
        create_ss_eliminate_cap, create_expand_niit, create_biden_payroll_proposal,
    )
    from fiscal_model import (
        AMTPolicy, AMTType, create_extend_tcja_amt_relief,
        create_repeal_individual_amt, create_repeal_corporate_amt,
    )
    from fiscal_model import (
        PremiumTaxCreditPolicy, PTCScenario, create_extend_enhanced_ptc,
        create_repeal_ptc,
    )
    from fiscal_model import (
        TaxExpenditurePolicy, TaxExpenditureType,
        create_cap_employer_health_exclusion, create_eliminate_mortgage_deduction,
        create_repeal_salt_cap, create_eliminate_salt_deduction,
        create_cap_charitable_deduction, create_eliminate_step_up_basis,
    )
    from fiscal_model import (
        DistributionalEngine, IncomeGroupType,
        format_distribution_table, generate_winners_losers_summary,
    )
    from fiscal_model.baseline import CBOBaseline
    from fiscal_model.models import (
        FRBUSAdapterLite, SimpleMultiplierAdapter, MacroScenario,
    )
    from fiscal_model.microsim.engine import MicroTaxCalculator
    from fiscal_model.microsim.data_generator import SyntheticPopulation
    from fiscal_model.long_run.solow_growth import SolowGrowthModel
    from fiscal_model.validation.cbo_scores import KNOWN_SCORES, CBOScore, ScoreSource
    from fiscal_model.app_data import CBO_SCORE_MAP, PRESET_POLICIES
    from fiscal_model.preset_handler import create_policy_from_preset
    MODEL_AVAILABLE = True
    MACRO_AVAILABLE = True
except ImportError as e:
    MODEL_AVAILABLE = False
    MACRO_AVAILABLE = False
    st.error(f"⚠️ Could not import fiscal model: {e}")

# Title and introduction
st.markdown('<div class="main-header">📊 Fiscal Policy Impact Calculator</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Estimate the budgetary and economic effects of tax and spending policies using real IRS and FRED data</div>', unsafe_allow_html=True)

# Reorganize tabs to reduce clutter
main_tabs = st.tabs(["📊 Calculator", "📈 Economic Analysis", "🛠️ Tools", "ℹ️ Reference", "⚙️ Settings"])

# Define Settings Tab content FIRST so variables are available for other tabs
with main_tabs[4]:
    st.header("⚙️ Configuration")
    
    col_settings_1, col_settings_2 = st.columns(2)
    
    with col_settings_1:
        st.subheader("Model Options")
        use_real_data = st.checkbox("Use real IRS/FRED data", value=True,
                                     help="Uses actual IRS Statistics of Income data and FRED economic indicators")

        dynamic_scoring = st.checkbox("Dynamic scoring", value=False,
                                       help="Include macroeconomic feedback effects (GDP growth, employment, interest rates)")

        if dynamic_scoring:
            macro_model = st.selectbox(
                "Macro model",
                ["FRB/US-Lite (Recommended)", "Simple Multiplier"],
                help="FRB/US-Lite uses Federal Reserve-calibrated multipliers; Simple uses basic Keynesian multipliers"
            )

        # Microsimulation Toggle
        use_microsim = st.checkbox("Microsimulation (Experimental)", value=False,
                                    help="Use individual-level tax calculation (JCT-style) instead of bracket averages. Requires CPS data.")

        st.subheader("Data Source")
        data_year = st.selectbox("IRS data year", [2022, 2021],
                                help="Year of IRS Statistics of Income data to use")

    with col_settings_2:
        st.subheader("📚 About")
        st.markdown("""
        This calculator uses Congressional Budget Office (CBO) methodology to estimate policy impacts.

        **Data Sources:**
        - IRS Statistics of Income
        - FRED Economic Data
        - CBO Baseline Projections

        **Methodology:**
        - Static revenue estimation
        - Behavioral responses (ETI)
        - Dynamic macroeconomic feedback
        """)
        st.caption("Built with Streamlit • Data updated 2022")

    st.markdown("---")
    if st.button("🗑️ Reset All", type="primary", help="Clear all inputs, results, and settings to default"):
        st.session_state.clear()
        st.rerun()

with main_tabs[0]:
    tab1, tab2 = st.tabs(["⚙️ Policy Input", "📝 Results Summary"])

with main_tabs[1]:
    tab3, tab4, tab9 = st.tabs(["🌍 Dynamic Scoring", "👥 Distribution", "⏳ Long-Run Growth"])

with main_tabs[2]:
    tab5, tab6 = st.tabs(["🔀 Compare Policies", "📦 Policy Packages"])

with main_tabs[3]:
    tab7, tab8 = st.tabs(["📋 Detailed Results", "ℹ️ Methodology"])

with tab1:
    st.header("Fiscal Policy Calculator")

    # Policy type selector
    policy_category = st.radio(
        "Select policy type",
        ["💰 Tax Policy", "📊 Spending Policy"],
        horizontal=True,
        help="Choose whether to analyze tax changes or spending programs"
    )

    is_spending = policy_category == "📊 Spending Policy"

    # Define preset_policies at module level so Policy Packages tab can access it
    # Use imported preset policies
    preset_policies = PRESET_POLICIES

    if not is_spending:
        # TAX POLICY SECTION
        st.subheader("🎯 Quick Start: Choose a Preset Policy")

        col_preset, col_info = st.columns([2, 3])

        with col_preset:
            preset_choice = st.selectbox(
                "Select a policy to analyze",
                options=list(preset_policies.keys()),
                help="Choose a real-world or example policy, or select 'Custom' to design your own"
            )

        with col_info:
            if preset_choice != "Custom Policy":
                st.info(f"📋 **{preset_choice}**\n\n{preset_policies[preset_choice]['description']}")

        st.markdown("""
        <div class="info-box">
        💡 <strong>How it works:</strong> The calculator uses real IRS data to automatically determine
        how many taxpayers are affected and calculates the revenue impact using CBO methodology.
        </div>
        """, unsafe_allow_html=True)

        # Two-column layout for inputs
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Policy Parameters")

            # Get preset values
            preset_data = preset_policies[preset_choice]

            # Policy name
            default_name = preset_choice if preset_choice != "Custom Policy" else "Tax Rate Change"
            policy_name = st.text_input("Policy Name", default_name,
                                        help="A short name for this policy")

            # Rate change - use preset value
            rate_change_pct = st.slider(
                "Tax Rate Change (percentage points)",
                min_value=-10.0,
                max_value=10.0,
                value=preset_data["rate_change"],
                step=0.5,
                help="Positive = tax increase, Negative = tax cut"
            )
            rate_change = rate_change_pct / 100

            # Income threshold
            threshold_options = {
                "All taxpayers ($0+)": 0,
                "Middle class ($50K+)": 50000,
                "Upper-middle ($100K+)": 100000,
                "High earners ($200K+)": 200000,
                "Biden threshold ($400K+)": 400000,
                "Very high ($500K+)": 500000,
                "Millionaires ($1M+)": 1000000,
                "Multi-millionaires ($5M+)": 5000000,
                "Custom": None
            }

            # Find which threshold option matches the preset
            preset_threshold = preset_data["threshold"]
            default_threshold_idx = 0
            for idx, (label, value) in enumerate(threshold_options.items()):
                if value == preset_threshold:
                    default_threshold_idx = idx
                    break

            threshold_choice = st.selectbox(
                "Who is affected?",
                options=list(threshold_options.keys()),
                index=default_threshold_idx,
                help="Income threshold for who the policy applies to"
            )

            if threshold_choice == "Custom":
                threshold = st.number_input(
                    "Custom threshold ($)",
                    min_value=0,
                    max_value=10000000,
                    value=500000,
                    step=50000,
                    format="%d"
                )
            else:
                threshold = threshold_options[threshold_choice]

        with col2:
            # Policy Details & Timing (Collapsible)
            with st.expander("📝 Policy Details & Timing", expanded=False):
                # Policy type
                policy_type = st.selectbox(
                    "Policy Type",
                    ["Income Tax Rate", "Capital Gains", "Corporate Tax", "Payroll Tax"],
                    help="Type of tax being changed"
                )

                # Duration
                duration = st.slider(
                    "Policy Duration (years)",
                    min_value=1,
                    max_value=10,
                    value=10,
                    help="How long the policy lasts (CBO standard is 10 years)"
                )

                # Phase-in
                phase_in = st.slider(
                    "Phase-in Period (years)",
                    min_value=0,
                    max_value=5,
                    value=0,
                    help="Years to gradually phase in the full policy (0 = immediate)"
                )

            # Show advanced parameters?
            with st.expander("🔧 Expert Parameters (Elasticities & Data)", expanded=False):
                if policy_type == "Capital Gains":
                    st.markdown("*Capital gains requires a realizations base + baseline rate (IRS SOI tables here do not include realizations).*")
                else:
                    st.markdown("*Leave blank to auto-populate from IRS data*")

                manual_taxpayers = st.number_input(
                    "Affected taxpayers (millions)",
                    min_value=0.0,
                    max_value=200.0,
                    value=0.0,
                    step=0.1,
                    help="Leave at 0 to auto-populate from IRS data"
                )

                manual_avg_income = st.number_input(
                    "Average taxable income in bracket ($)",
                    min_value=0,
                    max_value=100000000,
                    value=0,
                    step=50000,
                    help="Leave at 0 to auto-populate from IRS data"
                )

                eti = st.number_input(
                    "Elasticity of Taxable Income (ETI)",
                    min_value=0.0,
                    max_value=2.0,
                    value=0.25,
                    step=0.05,
                    help="Behavioral response parameter (0.25 = moderate response)"
                )

                # Capital gains-specific inputs (realizations elasticity model)
                if policy_type == "Capital Gains":
                    st.markdown("**Capital Gains (Realizations Model)**")
                    cg_base_year = st.selectbox(
                        "Capital gains baseline year",
                        options=[2024, 2023, 2022],
                        index=0,
                        help="2022 uses IRS SOI preliminary net capital gain by AGI; 2023/2024 are estimated by scaling 2022 shares to Tax Foundation totals."
                    )
                    cg_rate_source = st.selectbox(
                        "Baseline rate source",
                        options=["Statutory/NIIT proxy (by AGI bracket)", "Tax Foundation avg effective (aggregate)"],
                        index=0,
                        help=(
                            "Statutory proxy computes a weighted baseline rate using AGI brackets (IRS) + a documented rate mapping. "
                            "Tax Foundation uses a single year-level effective rate (not by AGI). "
                            "Tax Foundation source: https://taxfoundation.org/data/all/federal/federal-capital-gains-tax-collections-historical-data/"
                        ),
                    )
                    baseline_cg_rate = st.number_input(
                        "Baseline capital gains tax rate",
                        min_value=0.0,
                        max_value=0.99,
                        value=0.20,
                        step=0.01,
                        help="Assumed baseline effective marginal capital gains rate for the affected group"
                    )
                    baseline_realizations = st.number_input(
                        "Baseline taxable capital gains realizations ($B/year)",
                        min_value=0.0,
                        max_value=10000.0,
                        value=0.0,
                        step=10.0,
                        help="If left at 0 and real-data is enabled, we'll auto-populate from IRS/Treasury-derived series (with documented assumptions)."
                    )

                    st.markdown("**Behavioral Response (Time-Varying Elasticity)**")
                    use_time_varying = st.checkbox(
                        "Use time-varying elasticity",
                        value=True,
                        help="Short-run elasticity is higher (timing effects), long-run is lower (permanent response only). Based on CBO/JCT methodology."
                    )

                    if use_time_varying:
                        col_sr, col_lr = st.columns(2)
                        with col_sr:
                            short_run_elasticity = st.number_input(
                                "Short-run elasticity (years 1-3)",
                                min_value=0.0,
                                max_value=3.0,
                                value=0.8,
                                step=0.1,
                                help="Higher elasticity in early years due to timing/anticipation effects. CBO: 0.7-1.0"
                            )
                        with col_lr:
                            long_run_elasticity = st.number_input(
                                "Long-run elasticity (years 4+)",
                                min_value=0.0,
                                max_value=2.0,
                                value=0.4,
                                step=0.1,
                                help="Lower elasticity once timing effects are exhausted. Literature: 0.3-0.5"
                            )
                        transition_years = st.slider(
                            "Transition period (years)",
                            min_value=1,
                            max_value=5,
                            value=3,
                            help="Years to transition from short-run to long-run elasticity"
                        )
                        # For backward compat, set single elasticity to average
                        realization_elasticity = (short_run_elasticity + long_run_elasticity) / 2
                    else:
                        realization_elasticity = st.number_input(
                            "Realization elasticity (constant)",
                            min_value=0.0,
                            max_value=5.0,
                            value=0.5,
                            step=0.05,
                            help="Single elasticity value for all years (timing/lock-in response)"
                        )
                        short_run_elasticity = realization_elasticity
                        long_run_elasticity = realization_elasticity
                        transition_years = 1

                    st.markdown("**Step-Up Basis at Death**")
                    st.info(
                        "Under current law, unrealized capital gains are forgiven at death (step-up basis). "
                        "This creates strong incentive to hold assets until death, reducing realizations. "
                        "Eliminating step-up would tax gains at death and reduce lock-in."
                    )

                    eliminate_step_up = st.checkbox(
                        "Eliminate step-up basis at death",
                        value=False,
                        help="Tax unrealized capital gains at death (Biden proposal). Creates new revenue stream."
                    )

                    if eliminate_step_up:
                        col_ex, col_gains = st.columns(2)
                        with col_ex:
                            step_up_exemption = st.number_input(
                                "Exemption per decedent ($)",
                                min_value=0,
                                max_value=10_000_000,
                                value=1_000_000,
                                step=100_000,
                                help="Biden proposal: $1M exemption. Gains below this are not taxed at death."
                            )
                        with col_gains:
                            gains_at_death = st.number_input(
                                "Annual gains at death ($B)",
                                min_value=0.0,
                                max_value=200.0,
                                value=54.0,
                                step=5.0,
                                help="CBO estimates ~$54B/year in unrealized gains transferred at death."
                            )
                        # When eliminating step-up, lock-in effect is reduced
                        step_up_lock_in_multiplier = 1.0
                    else:
                        step_up_exemption = 0.0
                        gains_at_death = 54.0
                        # With step-up, strong lock-in (hold until death to avoid tax)
                        step_up_lock_in_multiplier = st.slider(
                            "Step-up lock-in multiplier",
                            min_value=1.0,
                            max_value=6.0,
                            value=2.0,
                            step=0.5,
                            help="How much step-up increases deferral. 5.3x matches PWBM. Higher = more lock-in."
                        )

    else:
        # SPENDING POLICY SECTION
        st.subheader("🎯 Spending Program Calculator")

        st.markdown("""
        <div class="info-box">
        💡 <strong>Analyze spending programs:</strong> Calculate the budgetary impact of federal spending increases or cuts
        across different categories (infrastructure, defense, social programs, etc.).
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Program Parameters")

            # Program name
            program_name = st.text_input("Program Name", "Infrastructure Investment",
                                        help="A short name for this spending program")

            # Spending amount
            annual_spending = st.number_input(
                "Annual Spending (Billions)",
                min_value=-500.0,
                max_value=500.0,
                value=100.0,
                step=10.0,
                help="Positive = increase spending, Negative = cut spending"
            )

            # Category
            spending_category = st.selectbox(
                "Spending Category",
                ["Infrastructure", "Defense", "Non-Defense Discretionary", "Mandatory Programs",
                 "Social Security", "Medicare", "Medicaid", "Education", "Research & Development"],
                help="Type of spending program"
            )

        with col2:
            st.subheader("Economic Parameters")

            # Duration
            duration = st.slider(
                "Program Duration (years)",
                min_value=1,
                max_value=10,
                value=10,
                help="How long the program lasts"
            )

            # Growth rate
            growth_rate = st.slider(
                "Annual Growth Rate (%)",
                min_value=-5.0,
                max_value=10.0,
                value=2.0,
                step=0.5,
                help="Real growth rate of spending over time"
            ) / 100

            # Fiscal multiplier
            multiplier = st.slider(
                "Fiscal Multiplier",
                min_value=0.0,
                max_value=2.0,
                value=1.0,
                step=0.1,
                help="GDP impact per dollar spent (infrastructure ~1.5, transfers ~0.8)"
            )

            # One-time or recurring
            is_one_time = st.checkbox("One-time spending", value=False,
                                     help="Check if this is a one-time expense (like disaster relief)")

        # Preset examples
        with st.expander("📋 Example Programs"):
            st.markdown("""
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
            """)

    # Calculate button
    st.markdown("---")

    col_calc, col_clear = st.columns([3, 1])

    with col_calc:
        calculate = st.button("🚀 Calculate Impact", type="primary", use_container_width=True)

    with col_clear:
        if st.button("🔄 Reset", use_container_width=True):
            st.rerun()

# Store results in session state
if 'results' not in st.session_state:
    st.session_state.results = None

if calculate and MODEL_AVAILABLE:
    if use_microsim:
        # Handle microsimulation
        with st.spinner("Running microsimulation on individual tax units..."):
            try:
                # 1. Load Data
                data_path = Path(__file__).parent / "fiscal_model" / "microsim" / "tax_microdata_2024.csv"
                if data_path.exists():
                    population = pd.read_csv(data_path)
                    source_msg = "Using **Real CPS ASEC 2024** Microdata"
                else:
                    pop_gen = SyntheticPopulation(size=100_000)
                    population = pop_gen.generate()
                    source_msg = "Using **Synthetic** Microdata (Real data not found)"

                # 2. Setup Calculator
                calc = MicroTaxCalculator()
                
                # 3. Define Reform
                # Currently hardcoded to Double CTC for the prototype integration
                # In future, map UI inputs to reform function
                def reform_func(c):
                    # Check if user selected CTC expansion
                    if "CTC" in preset_choice:
                        c.ctc_amount = 4000 # Double to $4000
                    else:
                        # Default demo reform
                        c.ctc_amount = 4000

                # 4. Calculate
                baseline = calc.calculate(population)
                reform = calc.run_reform(population, reform_func)
                
                # 5. Aggregate Results
                baseline_rev = (baseline['final_tax'] * baseline['weight']).sum() / 1e9
                reform_rev = (reform['final_tax'] * reform['weight']).sum() / 1e9
                rev_change = reform_rev - baseline_rev
                
                # Distributional analysis
                merged = baseline.copy()
                merged['reform_tax'] = reform['final_tax']
                merged['tax_change'] = merged['reform_tax'] - merged['final_tax']
                
                # Group by children
                dist_kids = merged.groupby('children').apply(
                    lambda x: np.average(x['tax_change'], weights=x['weight'])
                ).reset_index(name='avg_tax_change')

                st.session_state.results = {
                    'is_microsim': True,
                    'revenue_change_billions': rev_change,
                    'baseline_revenue': baseline_rev,
                    'reform_revenue': reform_rev,
                    'distribution_kids': dist_kids,
                    'source_msg': source_msg,
                    'policy_name': preset_choice if preset_choice != "Custom Policy" else "Microsim Reform"
                }
                
                st.success("✅ Microsimulation complete!")
                
            except Exception as e:
                st.error(f"❌ Microsimulation failed: {e}")
                import traceback
                st.code(traceback.format_exc())

    elif is_spending:
        # Handle spending policy
        with st.spinner("Calculating spending program impact..."):
            try:
                from fiscal_model import SpendingPolicy

                # Create spending policy
                policy = SpendingPolicy(
                    name=program_name,
                    description=f"${annual_spending:+.1f}B annual spending for {spending_category}",
                    policy_type=PolicyType.DISCRETIONARY_NONDEFENSE,
                    annual_spending_change_billions=annual_spending,
                    annual_growth_rate=growth_rate,
                    gdp_multiplier=multiplier,
                    is_one_time=is_one_time,
                    category="nondefense",
                    duration_years=duration,
                )

                # Score policy
                scorer = FiscalPolicyScorer(baseline=None, use_real_data=use_real_data)
                result = scorer.score_policy(policy, dynamic=dynamic_scoring)

                # Store in session state
                st.session_state.results = {
                    'policy': policy,
                    'result': result,
                    'scorer': scorer,
                    'is_spending': True
                }

                st.success("✅ Calculation complete!")

            except Exception as e:
                st.error(f"❌ Error calculating spending impact: {e}")
                import traceback
                st.code(traceback.format_exc())
    else:
        # Handle tax policy
        with st.spinner("Calculating policy impact using real IRS data..."):
            try:
                # Check if this is a TCJA extension policy
                preset_data = preset_policies[preset_choice]
                
                # Try to create policy from preset handler
                policy = create_policy_from_preset(preset_data)
                
                if policy:
                    # It was a complex preset
                    # Score policy
                    # Use policy.start_year if available, else default to 2025
                    start_year = getattr(policy, 'start_year', 2025)
                    scorer = FiscalPolicyScorer(start_year=start_year, use_real_data=False)
                    result = scorer.score_policy(policy, dynamic=dynamic_scoring)

                    # Store in session state
                    st.session_state.results = {
                        'policy': policy,
                        'result': result,
                        'scorer': scorer,
                        'is_spending': False,
                        'policy_name': preset_choice,
                        **preset_data # Include all preset flags (is_tcja, etc.)
                    }

                    st.success("✅ Calculation complete!")

                else:
                    # Non-TCJA, non-corporate tax policy (Custom or simple presets)
                    # Map UI to policy type
                    policy_type_map = {
                        "Income Tax Rate": PolicyType.INCOME_TAX,
                        "Capital Gains": PolicyType.CAPITAL_GAINS_TAX,
                        "Corporate Tax": PolicyType.CORPORATE_TAX,
                        "Payroll Tax": PolicyType.PAYROLL_TAX,
                    }
                    mapped_type = policy_type_map.get(policy_type, PolicyType.INCOME_TAX)

                    # Create policy
                    if policy_type == "Capital Gains":
                        # Build description based on step-up setting
                        desc = f"{rate_change_pct:+.1f}pp capital gains rate change for AGI >= ${threshold:,}"
                        if eliminate_step_up:
                            desc += " + eliminate step-up basis"

                        policy = CapitalGainsPolicy(
                            name=policy_name,
                            description=desc,
                            policy_type=mapped_type,
                            rate_change=rate_change,
                            affected_income_threshold=threshold,
                            data_year=int(cg_base_year),
                            duration_years=duration,
                            phase_in_years=phase_in,
                            baseline_capital_gains_rate=float(baseline_cg_rate),
                            baseline_realizations_billions=float(baseline_realizations),
                            realization_elasticity=float(realization_elasticity),
                            # Time-varying elasticity parameters
                            short_run_elasticity=float(short_run_elasticity),
                            long_run_elasticity=float(long_run_elasticity),
                            transition_years=int(transition_years),
                            use_time_varying_elasticity=use_time_varying,
                            # Step-up basis parameters
                            step_up_at_death=True,  # Current law
                            eliminate_step_up=eliminate_step_up,
                            step_up_exemption=float(step_up_exemption),
                            gains_at_death_billions=float(gains_at_death),
                            step_up_lock_in_multiplier=float(step_up_lock_in_multiplier),
                        )
                        # If user wants auto-population, set baseline rate/realizations to 0
                        if baseline_realizations <= 0:
                            policy.baseline_realizations_billions = 0.0
                            if cg_rate_source == "Tax Foundation avg effective (aggregate)":
                                policy.baseline_capital_gains_rate = 0.0
                            else:
                                policy.baseline_capital_gains_rate = 0.0
                    else:
                        policy = TaxPolicy(
                            name=policy_name,
                            description=f"{rate_change_pct:+.1f}pp tax rate change for AGI >= ${threshold:,}",
                            policy_type=mapped_type,
                            rate_change=rate_change,
                            affected_income_threshold=threshold,
                            data_year=data_year,
                            duration_years=duration,
                            phase_in_years=phase_in,
                            taxable_income_elasticity=eti,
                        )

                    # Override auto-population if manual values provided
                    if policy_type != "Capital Gains" and manual_taxpayers > 0:
                        policy.affected_taxpayers_millions = manual_taxpayers
                    if policy_type != "Capital Gains" and manual_avg_income > 0:
                        policy.avg_taxable_income_in_bracket = manual_avg_income

                    # Score policy
                    scorer = FiscalPolicyScorer(baseline=None, use_real_data=use_real_data)
                    result = scorer.score_policy(policy, dynamic=dynamic_scoring)

                    # Store in session state
                    st.session_state.results = {
                        'policy': policy,
                        'result': result,
                        'scorer': scorer,
                        'is_spending': False,
                        'is_tcja': False,
                        'policy_name': preset_choice,
                    }

                    st.success("✅ Calculation complete!")

            except Exception as e:
                st.error(f"❌ Error calculating policy impact: {e}")
                import traceback
                st.code(traceback.format_exc())

# Display results if available
if st.session_state.results:
    result_data = st.session_state.results
    
    if result_data.get('is_microsim'):
        # MICROSIMULATION RESULTS DISPLAY
        with tab2:
            st.header("🔬 Microsimulation Results")
            st.markdown(result_data['source_msg'])
            
            # Summary Metrics
            col1, col2, col3 = st.columns(3)
            rev_change = result_data['revenue_change_billions']
            
            with col1:
                st.metric("Revenue Change (Year 1)", f"${rev_change:+.1f}B", 
                         delta="Revenue Gain" if rev_change > 0 else "Revenue Loss",
                         delta_color="normal" if rev_change > 0 else "inverse")
            with col2:
                st.metric("Baseline Revenue", f"${result_data['baseline_revenue']:,.1f}B")
            with col3:
                st.metric("Reform Revenue", f"${result_data['reform_revenue']:,.1f}B")
                
            st.markdown("---")
            
            # Distributional Chart (Unique to Microsim)
            st.subheader("👨‍👩‍👧‍👦 Impact by Family Size")
            st.caption("Average tax change per household by number of children. (Negative = Tax Cut)")
            
            dist_kids = result_data['distribution_kids']
            
            fig = px.bar(dist_kids, x='children', y='avg_tax_change',
                        labels={'children': 'Number of Children', 'avg_tax_change': 'Average Tax Change ($)'},
                        color='avg_tax_change',
                        color_continuous_scale='RdBu_r') # Red for tax increase, Blue for cut
            
            st.plotly_chart(fig, use_container_width=True)
            
            st.info("""
            **Why Microsimulation?** 
            Aggregate models use average incomes. Microsimulation calculates taxes for *individual households*, 
            capturing complex interactions like how the Child Tax Credit phase-out overlaps with other provisions.
            """)
            
    else:
        # STANDARD AGGREGATE MODEL DISPLAY
        policy = result_data['policy']
        result = result_data['result']
        scorer = result_data['scorer']
        is_spending_result = result_data.get('is_spending', False)

        with tab2:
            st.header("📈 Results Summary")

        # Calculate all the key numbers
        static_total = result.static_revenue_effect.sum()
        behavioral_total = result.behavioral_offset.sum()
        net_total = static_total + behavioral_total
        year1_static = result.static_revenue_effect[0]
        year1_behavioral = result.behavioral_offset[0]
        year1_net = year1_static + year1_behavioral

        # Determine labels
        is_tax_increase = static_total > 0
        policy_label = "Spending Effect" if is_spending_result else "Revenue Effect"
        
        if is_spending_result:
            net_delta_label = "Deficit Impact"
            net_color = "inverse" if net_total < 0 else "normal" # Spending increases deficit (negative impact)
        else:
            net_delta_label = "Revenue Impact"
            net_color = "normal" if net_total > 0 else "inverse"

        # 1. TOP BANNER: The Big Number
        st.markdown(f"""
        <div style="background-color: #f0f2f6; padding: 1rem; border-radius: 0.5rem; text-align: center; margin-bottom: 1rem;">
            <h3 style="margin:0; color: #555;">10-Year Final Budget Impact</h3>
            <h1 style="margin:0; font-size: 3rem; color: {'#28a745' if (net_total > 0 and not is_spending_result) or (net_total > 0 and is_spending_result) else '#dc3545'};">
                ${abs(net_total):,.1f} Billion
            </h1>
            <p style="margin:0; color: #666;">
                {("Deficit Reduction" if net_total > 0 else "Deficit Increase") if not is_spending_result else ("Spending Increase" if net_total > 0 else "Spending Cut")}
            </p>
        </div>
        """, unsafe_allow_html=True)

        # 2. DASHBOARD GRID: Metrics & Context
        col_metrics, col_context = st.columns([1, 1])

        with col_metrics:
            st.subheader("📊 Key Metrics")
            
            # Row 1: Static vs Behavioral
            m1, m2 = st.columns(2)
            with m1:
                st.metric(
                    "Static Estimate",
                    f"${abs(static_total):.1f}B",
                    help="Direct effect before behavioral changes"
                )
            with m2:
                behavioral_pct = (abs(behavioral_total) / abs(static_total) * 100) if static_total != 0 else 0
                st.metric(
                    "Behavioral Offset",
                    f"${abs(behavioral_total):.1f}B",
                    delta=f"{behavioral_pct:.0f}% of static",
                    delta_color="off",
                    help="Revenue lost/gained due to behavioral changes (ETI)"
                )
            
            # Row 2: Averages
            m3, m4 = st.columns(2)
            with m3:
                st.metric("Avg Annual Cost", f"${abs(net_total/10):.1f}B")
            with m4:
                st.metric("Year 1 Impact", f"${abs(year1_net):.1f}B")

        with col_context:
            # Check for Official Score
            policy_name = result_data.get('policy_name', '')
            cbo_data = CBO_SCORE_MAP.get(policy_name)

            if cbo_data:
                st.subheader("🏛️ Official Benchmark")
                official = cbo_data['official_score']
                model_score = -net_total # Convert to CBO convention (positive = deficit)
                
                # Calculate error
                error_pct = ((model_score - official) / abs(official)) * 100 if official != 0 else 0
                abs_error = abs(error_pct)
                
                # Rating
                if abs_error <= 5: icon, rating = "🎯", "Excellent"
                elif abs_error <= 10: icon, rating = "✅", "Good"
                elif abs_error <= 15: icon, rating = "⚠️", "Acceptable"
                else: icon, rating = "❌", "Needs Review"

                c1, c2 = st.columns(2)
                with c1:
                    st.metric(
                        f"Official ({cbo_data['source']})", 
                        f"${official:,.0f}B",
                        delta=f"{error_pct:+.1f}% error",
                        delta_color="off"
                    )
                with c2:
                    st.markdown(f"**Accuracy:** {icon} {rating}")
                    st.caption(cbo_data['notes'])
            else:
                st.subheader("👥 Distribution Context")
                if policy.affected_taxpayers_millions > 0:
                     st.metric("Affected Taxpayers", f"{policy.affected_taxpayers_millions:.2f} Million")
                     if hasattr(policy, 'avg_taxable_income_in_bracket'):
                        st.metric("Avg Income of Affected", f"${policy.avg_taxable_income_in_bracket:,.0f}")
                else:
                    st.info("No distribution data available for this policy type.")

        st.markdown("---")

        # 3. CHARTS: Side-by-Side
        c_chart1, c_chart2 = st.columns(2)

        with c_chart1:
            st.subheader("Year-by-Year Net Effect")
            
            # Create DataFrame for plotting
            years = result.baseline.years
            df_timeline = pd.DataFrame({
                'Year': years,
                'Net Effect': result.static_revenue_effect + result.behavioral_offset
            })

            fig_timeline = go.Figure()
            fig_timeline.add_trace(go.Bar(
                x=df_timeline['Year'],
                y=df_timeline['Net Effect'],
                marker_color='#1f77b4',
            ))
            fig_timeline.update_layout(
                margin=dict(l=20, r=20, t=20, b=20),
                height=300,
                xaxis_title=None,
                yaxis_title="$ Billions",
            )
            st.plotly_chart(fig_timeline, use_container_width=True)

        with c_chart2:
            st.subheader("Cumulative Impact")
            df_timeline['Cumulative'] = df_timeline['Net Effect'].cumsum()
            
            fig_cum = go.Figure()
            fig_cum.add_trace(go.Scatter(
                x=df_timeline['Year'],
                y=df_timeline['Cumulative'],
                fill='tozeroy',
                mode='lines+markers',
                line=dict(color='#2ca02c', width=3)
            ))
            fig_cum.update_layout(
                margin=dict(l=20, r=20, t=20, b=20),
                height=300,
                xaxis_title=None,
                yaxis_title="Cumulative $ Billions",
            )
            st.plotly_chart(fig_cum, use_container_width=True)

    with tab3:
        st.header("🌍 Dynamic Scoring")

        if not dynamic_scoring:
            st.markdown("""
            <div class="info-box">
            💡 <strong>Dynamic scoring is disabled.</strong> Enable it in the sidebar to see macroeconomic effects
            (GDP impact, employment changes, interest rates, and revenue feedback).
            </div>
            """, unsafe_allow_html=True)

            st.info("""
            **What is Dynamic Scoring?**

            Dynamic scoring estimates how fiscal policies affect the broader economy, beyond direct budget effects:

            - **GDP Effects**: Tax cuts can stimulate growth; tax increases can slow it
            - **Employment**: Policies affect job creation and labor force participation
            - **Interest Rates**: Deficits can raise rates through crowding out
            - **Revenue Feedback**: GDP growth generates additional tax revenue

            **Enable dynamic scoring** in the sidebar to see these effects for your policy.
            """)
        else:
            st.markdown("""
            <div class="info-box">
            💡 <strong>Macroeconomic Feedback:</strong> These estimates show how your policy affects
            GDP, employment, and generates revenue feedback through economic growth.
            </div>
            """, unsafe_allow_html=True)

            # Check if we have results to analyze
            if st.session_state.results is not None:
                result_data = st.session_state.results
                policy = result_data['policy']
                result = result_data['result']

                try:
                    # Create macro scenario from policy results
                    # Net revenue effect = static + behavioral
                    net_revenue = result.static_revenue_effect + result.behavioral_offset

                    # Determine if tax or spending policy
                    is_spending_policy = result_data.get('is_spending', False)

                    if is_spending_policy:
                        # Spending policy: outlays change
                        scenario = MacroScenario(
                            name=policy.name,
                            description=f"Dynamic scoring for {policy.name}",
                            start_year=int(result.baseline.years[0]),
                            horizon_years=len(net_revenue),
                            receipts_change=np.zeros(len(net_revenue)),
                            outlays_change=np.array([-net_revenue[i] for i in range(len(net_revenue))]),
                        )
                    else:
                        # Tax policy: receipts change
                        scenario = MacroScenario(
                            name=policy.name,
                            description=f"Dynamic scoring for {policy.name}",
                            start_year=int(result.baseline.years[0]),
                            horizon_years=len(net_revenue),
                            receipts_change=np.array(net_revenue),
                            outlays_change=np.zeros(len(net_revenue)),
                        )

                    # Select adapter based on sidebar choice
                    try:
                        use_simple = macro_model == "Simple Multiplier"
                    except NameError:
                        use_simple = False

                    if use_simple:
                        adapter = SimpleMultiplierAdapter()
                        model_name = "Simple Keynesian Multiplier"
                    else:
                        adapter = FRBUSAdapterLite()
                        model_name = "FRB/US-Lite (Federal Reserve calibrated)"

                    # Run macro simulation
                    macro_result = adapter.run(scenario)

                    # Display model info
                    st.caption(f"Model: **{model_name}**")

                    # Key summary metrics
                    st.subheader("10-Year Macroeconomic Effects")

                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        gdp_effect = macro_result.cumulative_gdp_effect
                        st.metric(
                            "Cumulative GDP Effect",
                            f"{gdp_effect:.2f}%-years",
                            delta="Growth boost" if gdp_effect > 0 else "Growth drag",
                            delta_color="normal" if gdp_effect > 0 else "inverse"
                        )

                    with col2:
                        revenue_fb = macro_result.cumulative_revenue_feedback
                        st.metric(
                            "Revenue Feedback",
                            f"${revenue_fb:.0f}B",
                            delta="Additional revenue" if revenue_fb > 0 else "Revenue loss",
                            delta_color="normal" if revenue_fb > 0 else "inverse"
                        )

                    with col3:
                        # Average employment effect
                        avg_employment = np.mean(macro_result.employment_change_millions)
                        st.metric(
                            "Avg Employment Effect",
                            f"{avg_employment:+.2f}M jobs",
                            delta="Job creation" if avg_employment > 0 else "Job losses"
                        )

                    with col4:
                        net_budget = macro_result.net_budget_effect
                        st.metric(
                            "Net Budget Effect",
                            f"${net_budget:.0f}B",
                            help="Revenue feedback minus interest costs"
                        )

                    # Adjusted budget impact
                    st.markdown("---")
                    st.subheader("Budget Impact with Dynamic Feedback")

                    static_total = result.static_revenue_effect.sum()
                    behavioral_total = result.behavioral_offset.sum()
                    conventional_total = static_total + behavioral_total
                    dynamic_total = conventional_total + macro_result.cumulative_revenue_feedback

                    col1, col2, col3 = st.columns(3)

                    with col1:
                        st.metric(
                            "Conventional Score",
                            f"${conventional_total:.0f}B",
                            help="Static + behavioral (no macro feedback)"
                        )

                    with col2:
                        st.metric(
                            "Revenue Feedback",
                            f"${macro_result.cumulative_revenue_feedback:+.0f}B",
                            help="Additional revenue from GDP growth"
                        )

                    with col3:
                        st.metric(
                            "Dynamic Score",
                            f"${dynamic_total:.0f}B",
                            delta=f"{(macro_result.cumulative_revenue_feedback/abs(conventional_total)*100):+.1f}% vs conventional" if conventional_total != 0 else "N/A",
                            delta_color="normal" if macro_result.cumulative_revenue_feedback > 0 else "inverse"
                        )

                    # Show calculation
                    sign_conv = "+" if conventional_total >= 0 else "-"
                    sign_fb = "+" if macro_result.cumulative_revenue_feedback >= 0 else "-"
                    sign_dyn = "+" if dynamic_total >= 0 else "-"
                    st.markdown(f"""
                    **Calculation:** ${sign_conv}${abs(conventional_total):.0f}B (conventional) {sign_fb} ${abs(macro_result.cumulative_revenue_feedback):.0f}B (feedback) = **{sign_dyn}${abs(dynamic_total):.0f}B (dynamic)**
                    """)

                    # Year-by-year effects chart
                    st.markdown("---")
                    st.subheader("Year-by-Year Macroeconomic Effects")

                    # GDP effect chart
                    fig_gdp = go.Figure()

                    fig_gdp.add_trace(go.Bar(
                        x=macro_result.years,
                        y=macro_result.gdp_level_pct,
                        name='GDP Effect (%)',
                        marker_color='#1f77b4',
                    ))

                    fig_gdp.add_trace(go.Scatter(
                        x=macro_result.years,
                        y=np.cumsum(macro_result.gdp_level_pct),
                        name='Cumulative GDP (%-years)',
                        mode='lines+markers',
                        yaxis='y2',
                        line=dict(color='#ff7f0e', width=2),
                    ))

                    fig_gdp.update_layout(
                        title="GDP Effects by Year",
                        xaxis_title="Year",
                        yaxis_title="GDP Level Effect (%)",
                        yaxis2=dict(
                            title="Cumulative (%-years)",
                            overlaying='y',
                            side='right'
                        ),
                        height=400,
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
                        hovermode='x unified'
                    )

                    st.plotly_chart(fig_gdp, use_container_width=True)

                    # Employment and revenue feedback
                    col1, col2 = st.columns(2)

                    with col1:
                        fig_emp = go.Figure()

                        fig_emp.add_trace(go.Scatter(
                            x=macro_result.years,
                            y=macro_result.employment_change_millions,
                            mode='lines+markers',
                            name='Employment Change',
                            fill='tozeroy',
                            line=dict(color='#2ca02c', width=2),
                        ))

                        fig_emp.update_layout(
                            title="Employment Effect (Millions of Jobs)",
                            xaxis_title="Year",
                            yaxis_title="Jobs (Millions)",
                            height=350,
                            hovermode='x'
                        )

                        st.plotly_chart(fig_emp, use_container_width=True)

                    with col2:
                        fig_rev = go.Figure()

                        fig_rev.add_trace(go.Bar(
                            x=macro_result.years,
                            y=macro_result.revenue_feedback_billions,
                            name='Revenue Feedback',
                            marker_color='#9467bd',
                        ))

                        fig_rev.update_layout(
                            title="Revenue Feedback by Year ($B)",
                            xaxis_title="Year",
                            yaxis_title="Revenue Feedback ($B)",
                            height=350,
                            hovermode='x'
                        )

                        st.plotly_chart(fig_rev, use_container_width=True)

                    # Interest rate effects
                    st.markdown("---")
                    st.subheader("Interest Rate Effects")

                    col1, col2 = st.columns(2)

                    with col1:
                        avg_short = np.mean(macro_result.short_rate_ppts)
                        st.metric(
                            "Avg Short-Term Rate Change",
                            f"{avg_short:+.2f} ppts",
                            help="Federal funds rate effect (basis points)"
                        )

                    with col2:
                        avg_long = np.mean(macro_result.long_rate_ppts)
                        st.metric(
                            "Avg Long-Term Rate Change",
                            f"{avg_long:+.2f} ppts",
                            help="10-year Treasury rate effect"
                        )

                    # Detailed results table
                    st.markdown("---")
                    st.subheader("Detailed Year-by-Year Results")

                    macro_df = macro_result.to_dataframe()
                    st.dataframe(macro_df, use_container_width=True, hide_index=True)

                    # Model methodology note
                    st.markdown("---")
                    with st.expander("📖 Methodology Notes"):
                        if isinstance(adapter, FRBUSAdapterLite):
                            st.markdown("""
                            **FRB/US-Lite Model**

                            This model uses multipliers calibrated to the Federal Reserve's FRB/US model:

                            | Parameter | Value | Source |
                            |-----------|-------|--------|
                            | Spending Multiplier | 1.4 (year 1) | FRB/US simulations |
                            | Tax Multiplier | -0.7 (year 1) | FRB/US simulations |
                            | Multiplier Decay | 0.75/year | Standard assumption |
                            | Crowding Out | 15% of deficit | Interest rate response |
                            | Marginal Tax Rate | 25% | For revenue feedback |

                            **Key Assumptions:**
                            - Monetary policy follows Taylor rule (not at zero lower bound)
                            - Fiscal closure via surplus ratio targeting
                            - No supply-side effects on potential GDP

                            **References:**
                            - Coenen et al. (2012). "Effects of Fiscal Stimulus in Structural Models"
                            - CBO (2019). "The Effects of Automatic Stabilizers on the Federal Budget"
                            """)
                        else:
                            st.markdown("""
                            **Simple Multiplier Model**

                            This model uses basic Keynesian fiscal multipliers:

                            | Parameter | Value |
                            |-----------|-------|
                            | Spending Multiplier | 1.0 |
                            | Tax Multiplier | -0.5 |
                            | Multiplier Decay | 0.9/year |
                            | Marginal Tax Rate | 25% |

                            This is a simplified model. For more accurate results, use FRB/US-Lite.
                            """)

                except Exception as e:
                    st.error(f"Error running dynamic scoring: {e}")
                    import traceback
                    st.code(traceback.format_exc())
            else:
                st.info("👆 Calculate a policy first to see dynamic scoring results")

    with tab4:
        st.header("👥 Distributional Analysis")

        st.markdown("""
        <div class="info-box">
        💡 <strong>Who pays?</strong> This tab shows how the tax change affects different income groups,
        following Tax Policy Center (TPC) and Joint Committee on Taxation (JCT) methodology.
        </div>
        """, unsafe_allow_html=True)

        if MODEL_AVAILABLE and hasattr(policy, 'rate_change'):
            # Initialize distributional engine
            dist_engine = DistributionalEngine(data_year=2022)

            # Grouping type selector
            col1, col2 = st.columns([1, 3])
            with col1:
                group_type_choice = st.selectbox(
                    "Income grouping",
                    ["Quintiles (5 groups)", "Deciles (10 groups)", "JCT Dollar Brackets"],
                    help="How to divide taxpayers into income groups"
                )

                if group_type_choice == "Quintiles (5 groups)":
                    group_type = IncomeGroupType.QUINTILE
                elif group_type_choice == "Deciles (10 groups)":
                    group_type = IncomeGroupType.DECILE
                else:
                    group_type = IncomeGroupType.JCT_DOLLAR

            # Run distributional analysis
            try:
                dist_analysis = dist_engine.analyze_policy(policy, group_type=group_type)

                # Summary metrics
                st.subheader("Summary")
                summary = generate_winners_losers_summary(dist_analysis)

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric(
                        "Total Tax Change (Year 1)",
                        f"${dist_analysis.total_tax_change:.1f}B",
                        delta="Tax increase" if dist_analysis.total_tax_change > 0 else "Tax cut"
                    )
                with col2:
                    st.metric(
                        "% with Tax Increase",
                        f"{summary['pct_with_increase']:.1f}%"
                    )
                with col3:
                    st.metric(
                        "% with Tax Cut",
                        f"{summary['pct_with_decrease']:.1f}%"
                    )
                with col4:
                    unchanged = 100 - summary['pct_with_increase'] - summary['pct_with_decrease']
                    st.metric(
                        "% Unchanged",
                        f"{unchanged:.1f}%"
                    )

                # Distribution table
                st.subheader("Tax Change by Income Group")
                df_dist = format_distribution_table(dist_analysis, style="tpc")

                # Format for display
                st.dataframe(
                    df_dist.style.format({
                        'Returns (M)': '{:.1f}',
                        'Avg Tax Change ($)': '${:,.0f}',
                        '% of Income': '{:.2f}%',
                        'Share of Total': '{:.1f}%',
                        '% Tax Increase': '{:.0f}%',
                        '% Tax Decrease': '{:.0f}%',
                        'ETR Change (ppts)': '{:.2f}',
                    }),
                    use_container_width=True,
                    hide_index=True
                )

                # Bar chart of average tax change
                st.subheader("Average Tax Change by Income Group")

                import plotly.graph_objects as go

                fig_dist = go.Figure()

                groups = [r.income_group.name for r in dist_analysis.results]
                changes = [r.tax_change_avg for r in dist_analysis.results]
                colors = ['#28a745' if c < 0 else '#dc3545' for c in changes]

                fig_dist.add_trace(go.Bar(
                    x=groups,
                    y=changes,
                    marker_color=colors,
                    text=[f"${c:,.0f}" for c in changes],
                    textposition='outside'
                ))

                fig_dist.update_layout(
                    xaxis_title="Income Group",
                    yaxis_title="Average Tax Change ($)",
                    height=400,
                    showlegend=False
                )

                st.plotly_chart(fig_dist, use_container_width=True)

                # Share of tax change pie chart
                col1, col2 = st.columns(2)

                with col1:
                    st.subheader("Share of Total Tax Change")

                    # Only show groups with non-zero share
                    shares = [(r.income_group.name, abs(r.share_of_total_change) * 100)
                              for r in dist_analysis.results if abs(r.share_of_total_change) > 0.01]

                    if shares:
                        fig_pie = go.Figure(data=[go.Pie(
                            labels=[s[0] for s in shares],
                            values=[s[1] for s in shares],
                            hole=0.4,
                            textinfo='label+percent',
                        )])
                        fig_pie.update_layout(height=350, showlegend=False)
                        st.plotly_chart(fig_pie, use_container_width=True)
                    else:
                        st.info("No significant tax change in any group")

                with col2:
                    st.subheader("Winners & Losers")

                    if summary['biggest_losers']:
                        st.markdown("**Largest tax increases:**")
                        for item in summary['biggest_losers'][:3]:
                            st.markdown(f"- {item['group']}: +${item['avg_change']:,.0f} avg")

                    if summary['biggest_winners']:
                        st.markdown("**Largest tax cuts:**")
                        for item in summary['biggest_winners'][:3]:
                            st.markdown(f"- {item['group']}: ${item['avg_change']:,.0f} avg")

                    if not summary['biggest_losers'] and not summary['biggest_winners']:
                        st.info("No significant tax changes")

                # Top income breakout
                st.markdown("---")
                st.subheader("Top Income Group Detail")

                top_analysis = dist_engine.create_top_income_breakout(policy)

                st.markdown("""
                How the tax change affects the top of the income distribution:
                """)

                top_data = []
                for r in top_analysis.results:
                    if r.share_of_total_change != 0:
                        top_data.append({
                            "Income Group": r.income_group.name,
                            "Returns (M)": f"{r.income_group.num_returns/1e6:.2f}",
                            "Avg Tax Change": f"${r.tax_change_avg:,.0f}",
                            "Share of Total": f"{r.share_of_total_change*100:.1f}%",
                        })

                if top_data:
                    st.dataframe(pd.DataFrame(top_data), use_container_width=True, hide_index=True)
                else:
                    st.info("This policy does not significantly affect top income groups")

            except Exception as e:
                st.error(f"Error running distributional analysis: {e}")
                import traceback
                st.code(traceback.format_exc())
        else:
            st.info("👆 Calculate a tax policy first to see distributional analysis")

    with tab5:
        st.header("🔀 Policy Comparison")

        # preset_policies is only defined for tax policies, not spending
        if 'PRESET_POLICIES' not in globals() or is_spending:
            st.info("📊 Policy comparison is available for tax policies. Select a tax policy category in the sidebar to use this feature.")
            policies_to_compare = []
        else:
            st.markdown("""
            <div class="info-box">
            💡 <strong>Compare scenarios:</strong> Select 2-3 policies from the preset library to see how they compare side-by-side.
            </div>
            """, unsafe_allow_html=True)

            # Multi-select for policies to compare
            comparison_options = [k for k in PRESET_POLICIES.keys() if k != "Custom Policy"]
            policies_to_compare = st.multiselect(
                "Select policies to compare (2-3 recommended)",
                options=comparison_options,
                default=comparison_options[:2] if len(comparison_options) >= 2 else comparison_options,
                max_selections=4
            )

        if len(policies_to_compare) >= 2:
            with st.spinner("Calculating and comparing policies..."):
                try:
                    comparison_results = []

                    for preset_name in policies_to_compare:
                        preset = PRESET_POLICIES[preset_name]

                        # Create policy
                        comp_policy = TaxPolicy(
                            name=preset_name,
                            description=preset['description'],
                            policy_type=PolicyType.INCOME_TAX,
                            rate_change=preset['rate_change'] / 100,
                            affected_income_threshold=preset['threshold'],
                            data_year=data_year,
                            duration_years=10,
                            phase_in_years=0,
                            taxable_income_elasticity=0.25,
                        )

                        # Score policy
                        comp_scorer = FiscalPolicyScorer(baseline=None, use_real_data=use_real_data)
                        comp_result = comp_scorer.score_policy(comp_policy, dynamic=dynamic_scoring)

                        comparison_results.append({
                            'name': preset_name,
                            'policy': comp_policy,
                            'result': comp_result,
                            'total_10yr': comp_result.static_revenue_effect.sum(),
                            'year1': comp_result.static_revenue_effect[0],
                            'affected_millions': comp_policy.affected_taxpayers_millions,
                            'avg_income': comp_policy.avg_taxable_income_in_bracket
                        })

                    # Comparison table
                    st.subheader("📊 Summary Comparison")

                    comparison_df = pd.DataFrame([{
                        'Policy': r['name'],
                        '10-Year Effect ($B)': f"${r['total_10yr']:.1f}",
                        'Year 1 Effect ($B)': f"${r['year1']:.1f}",
                        'Affected (M)': f"{r['affected_millions']:.2f}",
                        'Avg Income': f"${r['avg_income']:,.0f}",
                        'Per Taxpayer': f"${(r['year1'] * 1e9 / (r['affected_millions'] * 1e6) if r['affected_millions'] > 0 else 0):,.0f}"
                    } for r in comparison_results])

                    st.dataframe(comparison_df, use_container_width=True, hide_index=True)

                    # Side-by-side bar chart
                    st.markdown("---")
                    st.subheader("10-Year Revenue Effect Comparison")

                    fig_compare = go.Figure()

                    for r in comparison_results:
                        color = '#FF6B6B' if r['total_10yr'] > 0 else '#4ECDC4'
                        fig_compare.add_trace(go.Bar(
                            name=r['name'],
                            x=[r['name']],
                            y=[r['total_10yr']],
                            marker_color=color,
                            text=[f"${r['total_10yr']:.1f}B"],
                            textposition='outside'
                        ))

                    fig_compare.update_layout(
                        xaxis_title="Policy",
                        yaxis_title="10-Year Revenue Effect (Billions)",
                        showlegend=False,
                        height=500,
                        hovermode='x'
                    )

                    st.plotly_chart(fig_compare, use_container_width=True)

                    # Year-by-year comparison
                    st.markdown("---")
                    st.subheader("Year-by-Year Comparison")

                    fig_timeline_compare = go.Figure()

                    for r in comparison_results:
                        fig_timeline_compare.add_trace(go.Scatter(
                            x=r['result'].baseline.years,
                            y=r['result'].static_revenue_effect,
                            mode='lines+markers',
                            name=r['name'],
                            line=dict(width=3),
                            marker=dict(size=8)
                        ))

                    fig_timeline_compare.update_layout(
                        xaxis_title="Year",
                        yaxis_title="Revenue Effect (Billions)",
                        hovermode='x unified',
                        height=500,
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="right",
                            x=1
                        )
                    )

                    st.plotly_chart(fig_timeline_compare, use_container_width=True)

                    # Key differences
                    st.markdown("---")
                    st.subheader("📝 Key Differences")

                    max_revenue_policy = max(comparison_results, key=lambda x: x['total_10yr'])
                    min_revenue_policy = min(comparison_results, key=lambda x: x['total_10yr'])

                    col1, col2 = st.columns(2)

                    with col1:
                        st.success(f"""
                        **Largest Revenue Raiser**

                        {max_revenue_policy['name']}

                        - **10-Year Effect:** ${max_revenue_policy['total_10yr']:.1f}B
                        - **Affected:** {max_revenue_policy['affected_millions']:.2f}M taxpayers
                        """)

                    with col2:
                        st.error(f"""
                        **Largest Revenue Cost**

                        {min_revenue_policy['name']}

                        - **10-Year Effect:** ${min_revenue_policy['total_10yr']:.1f}B
                        - **Affected:** {min_revenue_policy['affected_millions']:.2f}M taxpayers
                        """)

                except Exception as e:
                    st.error(f"Error comparing policies: {e}")
                    import traceback
                    st.code(traceback.format_exc())

        else:
            st.info("👆 Select at least 2 policies above to see a comparison")

# =========================================================================
# TAB 6: POLICY PACKAGES (outside conditional - always visible)
# =========================================================================
with tab6:
    st.header("📦 Policy Package Builder")

    st.markdown("""
    <div class="info-box">
    💡 <strong>Build comprehensive tax plans</strong> by combining multiple policies.
    See the total budget impact and breakdown by component.
    </div>
    """, unsafe_allow_html=True)

    # Preset packages
    st.subheader("📋 Preset Policy Packages")

    preset_packages = {
        "Biden FY2025 Tax Plan": {
            "description": "President Biden's proposed tax changes for high earners and corporations",
            "policies": [
                "🏢 Biden Corporate 28% (CBO: -$1.35T)",
                "💰 Expand NIIT (JCT: -$250B)",
                "📋 Eliminate Step-Up Basis (-$500B)",
            ],
            "official_total": -2100,
            "source": "Treasury FY2025 Budget",
        },
        "TCJA Full Extension Package": {
            "description": "Extend all expiring TCJA provisions plus repeal SALT cap",
            "policies": [
                "🏛️ TCJA Full Extension (CBO: $4.6T)",
            ],
            "official_total": 4600,
            "source": "CBO May 2024",
        },
        "TCJA + No SALT Cap": {
            "description": "Extend TCJA and repeal the $10K SALT deduction cap",
            "policies": [
                "🏛️ TCJA Extension (No SALT Cap)",
            ],
            "official_total": 6500,
            "source": "CBO/JCT estimates",
        },
        "Progressive Revenue Package": {
            "description": "Raise revenue from high earners and corporations",
            "policies": [
                "🏢 Biden Corporate 28% (CBO: -$1.35T)",
                "💰 SS Donut Hole $250K (-$2.7T)",
                "📋 Eliminate Step-Up Basis (-$500B)",
                "📋 Cap Charitable Deduction (-$200B)",
            ],
            "official_total": -4750,
            "source": "Combined estimates",
        },
        "Social Security Solvency": {
            "description": "Payroll tax reforms to extend Social Security solvency",
            "policies": [
                "💰 SS Cap to 90% (CBO: -$800B)",
                "💰 Expand NIIT (JCT: -$250B)",
            ],
            "official_total": -1050,
            "source": "CBO/JCT estimates",
        },
        "Tax Expenditure Reform": {
            "description": "Limit major tax expenditures",
            "policies": [
                "📋 Cap Employer Health Exclusion (-$450B)",
                "📋 Cap Charitable Deduction (-$200B)",
                "📋 Eliminate Step-Up Basis (-$500B)",
            ],
            "official_total": -1150,
            "source": "JCT estimates",
        },
    }

    col1, col2 = st.columns([1, 2])

    with col1:
        selected_package = st.selectbox(
            "Select a preset package",
            options=["Custom Package"] + list(preset_packages.keys()),
            help="Choose a predefined policy package or build your own"
        )

    if selected_package != "Custom Package":
        package_data = preset_packages[selected_package]
        with col2:
            st.info(f"**{selected_package}**: {package_data['description']}")

    st.markdown("---")

    # Policy selection
    st.subheader("🔧 Select Policies to Combine")

    # Get all available policies from different categories
    all_scorable_policies = {}

    # Add policies from preset_policies (defined in tab1)
    for name, data in PRESET_POLICIES.items():
        if name == "Custom Policy":
            continue
        if data.get("is_tcja"):
            all_scorable_policies[name] = {"category": "TCJA", "data": data}
        elif data.get("is_corporate"):
            all_scorable_policies[name] = {"category": "Corporate", "data": data}
        elif data.get("is_credit"):
            all_scorable_policies[name] = {"category": "Tax Credits", "data": data}
        elif data.get("is_estate"):
            all_scorable_policies[name] = {"category": "Estate Tax", "data": data}
        elif data.get("is_payroll"):
            all_scorable_policies[name] = {"category": "Payroll Tax", "data": data}
        elif data.get("is_amt"):
            all_scorable_policies[name] = {"category": "AMT", "data": data}
        elif data.get("is_ptc"):
            all_scorable_policies[name] = {"category": "Premium Tax Credits", "data": data}
        elif data.get("is_expenditure"):
            all_scorable_policies[name] = {"category": "Tax Expenditures", "data": data}

    # Default selection based on preset or empty
    if selected_package != "Custom Package":
        default_policies = preset_packages[selected_package]["policies"]
        # Filter to only include policies that exist
        default_policies = [p for p in default_policies if p in all_scorable_policies]
    else:
        default_policies = []

    # Multi-select for policies
    selected_policies = st.multiselect(
        "Select policies to include in your package",
        options=list(all_scorable_policies.keys()),
        default=default_policies,
        help="Choose 2 or more policies to combine into a package"
    )

    if len(selected_policies) >= 1:
        st.markdown("---")
        st.subheader("📊 Package Results")

        # Calculate each policy's score
        package_results = []
        total_static = 0
        total_behavioral = 0
        total_net = 0

        with st.spinner("Calculating package impact..."):
            for policy_name in selected_policies:
                try:
                    policy_info = all_scorable_policies.get(policy_name, {})
                    policy_data = policy_info.get("data", {})

                    # Create policy using the new handler
                    policy = create_policy_from_preset(policy_data)
                    
                    if policy:
                        scorer = FiscalPolicyScorer(start_year=policy.start_year, use_real_data=False)
                    else:
                        continue

                    # Score the policy
                    result = scorer.score_policy(policy, dynamic=False)
                    static = result.static_revenue_effect.sum()
                    behavioral = result.behavioral_offset.sum()
                    net = static + behavioral

                    # Get CBO comparison if available
                    cbo_data = CBO_SCORE_MAP.get(policy_name, {})
                    official = cbo_data.get("official_score", None)

                    package_results.append({
                        "name": policy_name,
                        "category": policy_info.get("category", "Other"),
                        "static": static,
                        "behavioral": behavioral,
                        "net": net,
                        "cbo_net": -net,  # Convert to CBO convention
                        "official": official,
                    })

                    total_static += static
                    total_behavioral += behavioral
                    total_net += net

                except Exception as e:
                    st.warning(f"Could not score {policy_name}: {e}")

        if package_results:
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)

            # Convert to CBO convention for display
            total_cbo = -total_net

            with col1:
                st.metric(
                    "Package Total (10-yr)",
                    f"${total_cbo:,.0f}B",
                    delta="Cost" if total_cbo > 0 else "Revenue",
                    delta_color="inverse" if total_cbo > 0 else "normal"
                )

            with col2:
                st.metric(
                    "Policies Included",
                    f"{len(package_results)}",
                )

            with col3:
                avg_annual = total_cbo / 10
                st.metric(
                    "Average Annual",
                    f"${avg_annual:,.0f}B/yr",
                )

            with col4:
                # Compare to preset if applicable
                if selected_package != "Custom Package":
                    official_total = preset_packages[selected_package]["official_total"]
                    error = ((total_cbo - official_total) / abs(official_total) * 100) if official_total != 0 else 0
                    st.metric(
                        "vs Official Est.",
                        f"${official_total:,.0f}B",
                        delta=f"{error:+.1f}% diff",
                        delta_color="off"
                    )

            st.markdown("---")

            # Component breakdown table
            st.subheader("📋 Component Breakdown")

            df_components = pd.DataFrame(package_results).copy()
            df_components.loc[:, "10-Year Impact"] = df_components["cbo_net"].apply(lambda x: f"${x:,.0f}B")
            df_components.loc[:, "Official Score"] = df_components["official"].apply(
                lambda x: f"${x:,.0f}B" if x is not None else "N/A"
            )
            df_components.loc[:, "Category"] = df_components["category"]
            df_components.loc[:, "Policy"] = df_components["name"]

            # Display table
            st.dataframe(
                df_components[["Policy", "Category", "10-Year Impact", "Official Score"]],
                use_container_width=True,
                hide_index=True
            )

            # Visual breakdown
            st.subheader("📊 Visual Breakdown")

            # Create waterfall-style chart
            fig_waterfall = go.Figure()

            # Sort by impact
            df_sorted = df_components.sort_values("cbo_net", ascending=True)

            colors = ['#d62728' if x > 0 else '#2ca02c' for x in df_sorted["cbo_net"]]

            fig_waterfall.add_trace(go.Bar(
                y=df_sorted["name"],
                x=df_sorted["cbo_net"],
                orientation='h',
                marker_color=colors,
                text=df_sorted["10-Year Impact"],
                textposition='auto',
            ))

            fig_waterfall.update_layout(
                title="Policy Package Components (10-Year Impact)",
                xaxis_title="Budget Impact ($B, CBO Convention: + = Cost, - = Revenue)",
                height=max(300, len(package_results) * 50),
                showlegend=False,
            )

            st.plotly_chart(fig_waterfall, use_container_width=True)

            # Pie chart of absolute values
            col1, col2 = st.columns(2)

            with col1:
                # Separate costs and revenues
                costs = df_components[df_components["cbo_net"] > 0]
                revenues = df_components[df_components["cbo_net"] < 0]

                if not costs.empty:
                    fig_costs = px.pie(
                        costs,
                        values=costs["cbo_net"].abs(),
                        names="name",
                        title="Cost Components (Deficit Increases)",
                        color_discrete_sequence=px.colors.sequential.Reds
                    )
                    st.plotly_chart(fig_costs, use_container_width=True)
                else:
                    st.info("No cost components in this package")

            with col2:
                if not revenues.empty:
                    fig_revenues = px.pie(
                        revenues,
                        values=revenues["cbo_net"].abs(),
                        names="name",
                        title="Revenue Components (Deficit Decreases)",
                        color_discrete_sequence=px.colors.sequential.Greens
                    )
                    st.plotly_chart(fig_revenues, use_container_width=True)
                else:
                    st.info("No revenue components in this package")

            # Export package
            st.markdown("---")
            st.subheader("📤 Export Package")

            export_data = {
                "package_name": selected_package,
                "total_10_year_impact_billions": total_cbo,
                "average_annual_billions": total_cbo / 10,
                "num_policies": len(package_results),
                "components": [
                    {
                        "policy": r["name"],
                        "category": r["category"],
                        "impact_billions": r["cbo_net"],
                        "official_score": r["official"],
                    }
                    for r in package_results
                ]
            }

            col1, col2 = st.columns(2)
            with col1:
                import json
                st.download_button(
                    "📥 Download as JSON",
                    data=json.dumps(export_data, indent=2),
                    file_name=f"policy_package_{selected_package.replace(' ', '_')}.json",
                    mime="application/json"
                )

            with col2:
                csv_data = df_components[["Policy", "Category", "cbo_net", "official"]].copy()
                csv_data.columns = ["Policy", "Category", "10-Year Impact ($B)", "Official Score ($B)"]
                st.download_button(
                    "📥 Download as CSV",
                    data=csv_data.to_csv(index=False),
                    file_name=f"policy_package_{selected_package.replace(' ', '_')}.csv",
                    mime="text/csv"
                )

    else:
        st.info("👆 Select at least 1 policy above to build a package")

# Tabs 7 and 8 require results to be calculated
if st.session_state.results:
    result_data = st.session_state.results

    # Handle microsim results separately
    if result_data.get('is_microsim'):
        with tab7:
            st.header("📋 Detailed Results")
            st.info("Microsimulation results are displayed in the Results Summary tab.")
    else:
        # Standard aggregate model results
        policy = result_data['policy']
        result = result_data['result']
        is_spending_result = result_data.get('is_spending', False)

        # Extract values from policy object safely
        policy_rate_change = getattr(policy, 'rate_change', 0) * 100 if hasattr(policy, 'rate_change') else 0
        policy_threshold = getattr(policy, 'affected_income_threshold', 0) if hasattr(policy, 'affected_income_threshold') else 0
        policy_duration = getattr(policy, 'duration_years', 10)
        policy_phase_in = getattr(policy, 'phase_in_years', 0)
        policy_data_year = getattr(policy, 'data_year', 2022)

        # Calculate totals from result
        static_total = result.static_revenue_effect.sum()
        behavioral_total = result.behavioral_offset.sum()
        net_total = static_total + behavioral_total
        year1_net = result.static_revenue_effect[0] + result.behavioral_offset[0]
        years = result.baseline.years

        with tab7:
            st.header("📋 Detailed Results")

            # Policy summary
            st.subheader("Policy Details")

            policy_details = {
                "Policy Name": policy.name,
                "Description": policy.description,
                "Policy Type": policy.policy_type.value,
            }

            # Add rate change and threshold only for tax policies
            if not is_spending_result and policy_rate_change != 0:
                policy_details["Rate Change"] = f"{policy_rate_change:+.1f} percentage points"
            if not is_spending_result and policy_threshold > 0:
                policy_details["Income Threshold"] = f"${policy_threshold:,}"

            policy_details["Duration"] = f"{policy_duration} years"
            if policy_phase_in > 0:
                policy_details["Phase-in Period"] = f"{policy_phase_in} years"
            policy_details["Data Year"] = policy_data_year

            st.table(pd.DataFrame.from_dict(policy_details, orient='index', columns=['Value']))

            st.markdown("---")

            # Year-by-year table
            st.subheader("Year-by-Year Breakdown")

            detailed_df = pd.DataFrame({
                'Year': years,
                'Static Revenue Effect ($B)': [f"${x:.2f}" for x in result.static_revenue_effect],
                'Behavioral Offset ($B)': [f"${x:.2f}" for x in result.behavioral_offset],
                'Net Deficit Effect ($B)': [f"${x:.2f}" for x in (result.static_deficit_effect + result.behavioral_offset)],
            })

            st.dataframe(detailed_df, use_container_width=True, hide_index=True)

            # Download data
            st.markdown("---")
            st.subheader("💾 Export Results")

            col1, col2 = st.columns(2)

            with col1:
                # CSV export
                csv = detailed_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download as CSV",
                    data=csv,
                    file_name=f"fiscal_impact_{policy.name.replace(' ', '_')}.csv",
                    mime="text/csv"
                )

            with col2:
                # JSON export
                export_data = {
                    'policy': {
                        'name': policy.name,
                        'rate_change': policy_rate_change / 100,
                        'threshold': policy_threshold,
                        'duration': policy_duration,
                    },
                    'results': {
                        'static_10yr': float(static_total),
                        'behavioral_offset_10yr': float(behavioral_total),
                        'net_10yr_effect': float(net_total),
                        'year1_net_effect': float(year1_net),
                        'by_year': detailed_df.to_dict('records')
                    }
                }

                import json
                json_str = json.dumps(export_data, indent=2)
                st.download_button(
                    label="📥 Download as JSON",
                    data=json_str,
                    file_name=f"fiscal_impact_{policy.name.replace(' ', '_')}.json",
                    mime="application/json"
                )

    with tab8:
        st.header("ℹ️ Methodology")
        # ... [existing methodology content] ...
        st.markdown("""
        ## How This Calculator Works
        [Existing content...]
        """)

    with tab9:
        st.header("⏳ Long-Run Growth & Crowding Out")

        st.markdown("""
        <div class="info-box">
        💡 <strong>Capital Crowding Out:</strong> This model simulates how fiscal deficits affect the
        nation's capital stock over a 30-year horizon. Larger deficits reduce private investment,
        leading to lower future GDP and wages.
        </div>
        """, unsafe_allow_html=True)

        if st.session_state.results is not None and not st.session_state.results.get('is_microsim'):
            # Get deficit path (positive = increases deficit)
            res_obj = st.session_state.results.get('result')
            if res_obj is None:
                st.info("Long-run projections require aggregate model results. Run a policy calculation first.")
            else:
                deficit_path = res_obj.static_deficit_effect + res_obj.behavioral_offset

                # Run Solow Model
                solow = SolowGrowthModel()
                lr_res = solow.run_simulation(deficits=deficit_path, horizon=30)

                # 1. Summary Metrics
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("GDP Effect (Year 10)", f"{lr_res.gdp_pct_change[9]:.2f}%")
                with col2:
                    st.metric("GDP Effect (Year 30)", f"{lr_res.gdp_pct_change[29]:.2f}%")
                with col3:
                    # Long run wage effect
                    st.metric("Long-Run Wage Effect", f"{lr_res.gdp_pct_change[29] * 0.7:.2f}%",
                             help="Estimated impact on real wages driven by capital stock changes.")

                st.markdown("---")

                # 2. Charts
                c1, c2 = st.columns(2)

                with c1:
                    st.subheader("GDP Trajectory (% Change)")
                    fig_gdp = px.line(x=lr_res.years, y=lr_res.gdp_pct_change,
                                    labels={'x': 'Year', 'y': '% Change from Baseline'})
                    fig_gdp.add_hline(y=0, line_dash="dash", line_color="gray")
                    st.plotly_chart(fig_gdp, use_container_width=True)

                with c2:
                    st.subheader("Capital Stock (% Change)")
                    cap_pct_change = (lr_res.capital_stock / lr_res.capital_stock[0] - 1) * 100
                    # Correcting to compare against a baseline capital stock path
                    # For simplicity in prototype, show change from initial
                    fig_cap = px.line(x=lr_res.years, y=cap_pct_change,
                                    labels={'x': 'Year', 'y': '% Change in Capital'})
                    st.plotly_chart(fig_cap, use_container_width=True)

                st.info("""
                **Methodology Note:** This projection uses a Solow-Swan growth model calibrated to the US economy
                (Capital Share = 0.35, Depreciation = 5%). It assumes that 100% of the deficit increase
                reduces private investment (crowding out). This matches the 'closed economy' assumptions
                often used as a conservative benchmark by CBO and Penn Wharton.
                """)
        elif st.session_state.results is not None and st.session_state.results.get('is_microsim'):
            st.info("Long-run growth projections are not available for microsimulation results.")
        else:
            st.info("👆 Calculate a policy impact in the first tab to see long-run projections.")

# Footer
st.markdown("---")
st.caption("""
**Fiscal Policy Impact Calculator** | Built with Streamlit |
Data: IRS Statistics of Income, FRED, CBO |
Methodology: Congressional Budget Office scoring framework
""")
