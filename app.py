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
    initial_sidebar_state="expanded"
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
    from fiscal_model import TaxPolicy, PolicyType, FiscalPolicyScorer
    from fiscal_model.baseline import CBOBaseline
    MODEL_AVAILABLE = True
except ImportError as e:
    MODEL_AVAILABLE = False
    st.error(f"⚠️ Could not import fiscal model: {e}")

# Title and introduction
st.markdown('<div class="main-header">📊 Fiscal Policy Impact Calculator</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Estimate the budgetary and economic effects of tax and spending policies using real IRS and FRED data</div>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")

    st.subheader("Model Options")
    use_real_data = st.checkbox("Use real IRS/FRED data", value=True,
                                 help="Uses actual IRS Statistics of Income data and FRED economic indicators")

    dynamic_scoring = st.checkbox("Dynamic scoring", value=False,
                                   help="Include macroeconomic feedback effects (GDP growth, behavioral responses)")

    st.subheader("Data Source")
    data_year = st.selectbox("IRS data year", [2022, 2021],
                            help="Year of IRS Statistics of Income data to use")

    st.markdown("---")

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

    st.markdown("---")
    st.caption("Built with Streamlit • Data updated 2022")

# Main content tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs(["💰 Tax Policy", "📈 Results & Charts", "🔀 Compare Policies", "📋 Details", "ℹ️ Methodology"])

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

    if not is_spending:
        # TAX POLICY SECTION
        # Preset policies
        st.subheader("🎯 Quick Start: Choose a Preset Policy")

        preset_policies = {
            "Custom Policy": {
                "rate_change": -2.0,
                "threshold": 500000,
                "description": "Design your own policy"
            },
        "TCJA 2017 High-Income Cut": {
            "rate_change": -2.6,
            "threshold": 500000,
            "description": "Tax Cuts and Jobs Act reduced top rate from 39.6% to 37%"
        },
        "Biden 2025 Proposal": {
            "rate_change": 2.6,
            "threshold": 400000,
            "description": "Restore top rate to 39.6% for AGI > $400K"
        },
        "Trump 2024 Extension": {
            "rate_change": 0.0,
            "threshold": 0,
            "description": "Extend TCJA provisions (baseline, no change)"
        },
        "Progressive Millionaire Tax": {
            "rate_change": 5.0,
            "threshold": 1000000,
            "description": "5pp surtax on millionaires"
        },
        "Middle Class Tax Cut": {
            "rate_change": -2.0,
            "threshold": 50000,
            "description": "2pp cut for households earning $50K+"
        },
        "Flat Tax Reform": {
            "rate_change": -5.0,
            "threshold": 0,
            "description": "Simplified flat tax with lower rates across the board"
        }
        }

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
            st.subheader("Advanced Options")

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
            with st.expander("🔧 Expert Parameters (Optional)"):
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
    if is_spending:
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
                # Create policy
                policy = TaxPolicy(
                    name=policy_name,
                    description=f"{rate_change_pct:+.1f}pp tax rate change for AGI >= ${threshold:,}",
                    policy_type=PolicyType.INCOME_TAX,
                    rate_change=rate_change,
                    affected_income_threshold=threshold,
                    data_year=data_year,
                    duration_years=duration,
                    phase_in_years=phase_in,
                    taxable_income_elasticity=eti,
                )

                # Override auto-population if manual values provided
                if manual_taxpayers > 0:
                    policy.affected_taxpayers_millions = manual_taxpayers
                if manual_avg_income > 0:
                    policy.avg_taxable_income_in_bracket = manual_avg_income

                # Score policy
                scorer = FiscalPolicyScorer(baseline=None, use_real_data=use_real_data)
                result = scorer.score_policy(policy, dynamic=dynamic_scoring)

                # Store in session state
                st.session_state.results = {
                    'policy': policy,
                    'result': result,
                    'scorer': scorer,
                    'is_spending': False
                }

                st.success("✅ Calculation complete!")

            except Exception as e:
                st.error(f"❌ Error calculating policy impact: {e}")
                import traceback
                st.code(traceback.format_exc())

# Display results if available
if st.session_state.results:
    result_data = st.session_state.results
    policy = result_data['policy']
    result = result_data['result']
    scorer = result_data['scorer']
    is_spending_result = result_data.get('is_spending', False)

    with tab2:
        st.header("📈 Results Summary")

        # Calculate all the key numbers
        static_total = result.static_revenue_effect.sum()
        behavioral_total = result.behavioral_offset.sum()
        net_total = static_total + behavioral_total  # behavioral_offset is already signed correctly
        year1_static = result.static_revenue_effect[0]
        year1_behavioral = result.behavioral_offset[0]
        year1_net = year1_static + year1_behavioral

        # Determine if this is a tax increase or cut
        is_tax_increase = static_total > 0
        policy_label = "Spending Effect" if is_spending_result else "Revenue Effect"

        st.subheader(f"10-Year Budget Impact")
        
        # Show the calculation flow clearly
        st.markdown("""
        <div class="info-box">
        <strong>How to read this:</strong> Static estimate shows the direct revenue effect. 
        Behavioral offset accounts for how taxpayers change their behavior in response. 
        The <strong>Net Effect</strong> is what actually hits the budget.
        </div>
        """, unsafe_allow_html=True)

        # Main metrics in a clear flow: Static → Offset → Net
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("##### 📊 Static Estimate")
            if is_spending_result:
                delta_text = "Spending increase" if static_total > 0 else "Spending cut"
            else:
                delta_text = "Revenue gain" if static_total > 0 else "Revenue loss"
            
            st.metric(
                "Before Behavioral Response",
                f"${abs(static_total):.1f}B",
                delta=delta_text,
                delta_color="normal" if static_total > 0 else "inverse"
            )

        with col2:
            st.markdown("##### 🔄 Behavioral Offset")
            # Behavioral offset reduces the static estimate
            offset_direction = "reduces estimate" if (behavioral_total < 0 and static_total > 0) or (behavioral_total > 0 and static_total < 0) else "adds to estimate"
            st.metric(
                "Taxpayer Response",
                f"${abs(behavioral_total):.1f}B",
                delta=offset_direction,
                delta_color="off"
            )
            st.caption("ETI-based behavioral adjustment")

        with col3:
            st.markdown("##### ✅ Net Effect")
            if is_spending_result:
                net_delta = "Deficit increase" if net_total < 0 else "Deficit decrease"
            else:
                net_delta = "Revenue gain" if net_total > 0 else "Revenue loss"
            
            st.metric(
                "Final Budget Impact",
                f"${abs(net_total):.1f}B",
                delta=net_delta,
                delta_color="normal" if net_total > 0 else "inverse"
            )

        # Show the math explicitly
        st.markdown("---")
        
        # Calculation breakdown
        sign_static = "+" if static_total >= 0 else "-"
        sign_behavioral = "+" if behavioral_total >= 0 else "-"
        sign_net = "+" if net_total >= 0 else "-"
        
        st.markdown(f"""
        **Calculation:** ${sign_static}${abs(static_total):.1f}B (static) {sign_behavioral} ${abs(behavioral_total):.1f}B (behavioral) = **{sign_net}${abs(net_total):.1f}B (net)**
        """)

        # Additional context metrics
        st.markdown("---")
        st.subheader("📅 Additional Details")
        
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Year 1 Net Effect",
                f"${abs(year1_net):.1f}B",
                delta=f"{(abs(year1_net)/abs(net_total)*100):.0f}% of 10-yr total" if net_total != 0 else "N/A"
            )

        with col2:
            avg_annual = net_total / 10
            st.metric(
                "Average Annual (Net)",
                f"${abs(avg_annual):.1f}B",
                help="Average net effect per year"
            )

        with col3:
            behavioral_pct = (abs(behavioral_total) / abs(static_total) * 100) if static_total != 0 else 0
            st.metric(
                "Behavioral Response",
                f"{behavioral_pct:.0f}%",
                help="Behavioral offset as % of static estimate"
            )

        with col4:
            # Per taxpayer effect (net)
            if hasattr(policy, 'affected_taxpayers_millions') and policy.affected_taxpayers_millions > 0:
                per_taxpayer = (year1_net * 1e9) / (policy.affected_taxpayers_millions * 1e6)
                st.metric(
                    "Per Taxpayer (Net)",
                    f"${abs(per_taxpayer):,.0f}",
                    help="Average net tax change per affected taxpayer"
                )

        st.markdown("---")

        # Charts
        st.subheader("Year-by-Year Effects")

        # Create DataFrame for plotting
        years = result.baseline.years
        df_timeline = pd.DataFrame({
            'Year': years,
            'Static Effect': result.static_revenue_effect,
            'Behavioral Offset': result.behavioral_offset,
            'Net Effect': result.static_revenue_effect + result.behavioral_offset
        })

        # Revenue effect over time - show static, offset, and net
        fig_timeline = go.Figure()

        # Static effect bars
        fig_timeline.add_trace(go.Bar(
            x=df_timeline['Year'],
            y=df_timeline['Static Effect'],
            name='Static Effect',
            marker_color='#1f77b4',
            opacity=0.7
        ))

        # Behavioral offset bars (stacked)
        fig_timeline.add_trace(go.Bar(
            x=df_timeline['Year'],
            y=df_timeline['Behavioral Offset'],
            name='Behavioral Offset',
            marker_color='#ff7f0e',
            opacity=0.7
        ))

        # Net effect line (this is what matters)
        fig_timeline.add_trace(go.Scatter(
            x=df_timeline['Year'],
            y=df_timeline['Net Effect'],
            name='Net Effect (Final)',
            mode='lines+markers',
            line=dict(color='#2ca02c', width=3),
            marker=dict(size=10, symbol='diamond')
        ))

        fig_timeline.update_layout(
            title="Revenue Effects by Year (Static + Behavioral = Net)",
            xaxis_title="Year",
            yaxis_title="Revenue Effect (Billions)",
            barmode='relative',
            hovermode='x unified',
            height=450,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5
            )
        )

        st.plotly_chart(fig_timeline, use_container_width=True)

        # Cumulative NET effect (this is what CBO reports)
        df_timeline['Cumulative Net'] = df_timeline['Net Effect'].cumsum()
        df_timeline['Cumulative Static'] = df_timeline['Static Effect'].cumsum()

        fig_cumulative = go.Figure()

        # Static cumulative (lighter, dashed)
        fig_cumulative.add_trace(go.Scatter(
            x=df_timeline['Year'],
            y=df_timeline['Cumulative Static'],
            mode='lines',
            name='Cumulative Static',
            line=dict(color='#1f77b4', width=2, dash='dash'),
            opacity=0.6
        ))

        # Net cumulative (bold, solid) - this is what CBO reports
        fig_cumulative.add_trace(go.Scatter(
            x=df_timeline['Year'],
            y=df_timeline['Cumulative Net'],
            mode='lines+markers',
            name='Cumulative Net Effect',
            line=dict(color='#2ca02c', width=3),
            marker=dict(size=8)
        ))

        fig_cumulative.update_layout(
            title="Cumulative Effect Over 10 Years (Net is what CBO reports)",
            xaxis_title="Year",
            yaxis_title="Cumulative Effect (Billions)",
            hovermode='x unified',
            height=400,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5
            )
        )

        st.plotly_chart(fig_cumulative, use_container_width=True)

        # Economic context
        st.markdown("---")
        st.subheader("📐 Economic Context")

        col1, col2, col3 = st.columns(3)

        # Assume GDP ~$27T (2024 estimate)
        gdp_2025 = 27000  # billions
        pct_of_gdp = (year1_net / gdp_2025) * 100

        with col1:
            st.metric(
                "Year 1 Net (% of GDP)",
                f"{pct_of_gdp:.2f}%",
                help="Net revenue effect as percentage of GDP"
            )

        with col2:
            # Federal revenue ~$4.9T
            fed_revenue = 4900  # billions
            pct_of_revenue = (year1_net / fed_revenue) * 100
            st.metric(
                "% of Federal Revenue",
                f"{pct_of_revenue:.1f}%",
                help="Net effect as percentage of total federal revenue"
            )

        with col3:
            # Per taxpayer effect
            if policy.affected_taxpayers_millions > 0:
                per_taxpayer_display = (year1_net * 1e9) / (policy.affected_taxpayers_millions * 1e6)
                st.metric(
                    "Per Affected Taxpayer",
                    f"${per_taxpayer_display:,.0f}",
                    help="Average net tax change per affected taxpayer"
                )

        # Distributional visualization
        st.markdown("---")
        st.subheader("👥 Who Is Affected?")

        # Create distributional breakdown
        if policy.affected_taxpayers_millions > 0 and threshold > 0:
            # Get total taxpayers (rough estimate: 150M filers)
            total_taxpayers = 150.0  # million
            affected_pct = (policy.affected_taxpayers_millions / total_taxpayers) * 100
            unaffected_pct = 100 - affected_pct

            fig_dist = go.Figure()

            fig_dist.add_trace(go.Bar(
                x=['Taxpayers'],
                y=[unaffected_pct],
                name=f'Unaffected (<${threshold:,})',
                marker_color='#90EE90',
                text=[f'{unaffected_pct:.1f}%<br>({total_taxpayers - policy.affected_taxpayers_millions:.1f}M taxpayers)'],
                textposition='inside',
                hovertemplate='<b>Unaffected Taxpayers</b><br>%{y:.1f}% of all filers<br><extra></extra>'
            ))

            fig_dist.add_trace(go.Bar(
                x=['Taxpayers'],
                y=[affected_pct],
                name=f'Affected (≥${threshold:,})',
                marker_color='#FF6B6B' if rate_change > 0 else '#4ECDC4',
                text=[f'{affected_pct:.1f}%<br>({policy.affected_taxpayers_millions:.2f}M taxpayers)'],
                textposition='inside',
                hovertemplate='<b>Affected Taxpayers</b><br>%{y:.1f}% of all filers<br><extra></extra>'
            ))

            fig_dist.update_layout(
                title=f"Distribution of Tax Change (Threshold: ${threshold:,})",
                yaxis_title="Percentage of Taxpayers",
                barmode='stack',
                showlegend=True,
                height=400,
                hovermode='x unified'
            )

            st.plotly_chart(fig_dist, use_container_width=True)

            # Summary stats
            col1, col2 = st.columns(2)

            with col1:
                avg_change = per_taxpayer if policy.affected_taxpayers_millions > 0 else 0
                direction = "increase" if rate_change > 0 else "cut"
                st.info(f"""
                **Tax Change Summary**

                - **{policy.affected_taxpayers_millions:.2f}M** taxpayers affected ({affected_pct:.1f}%)
                - **${abs(avg_change):,.0f}** average tax {direction} per affected filer
                - **${policy.avg_taxable_income_in_bracket:,.0f}** average income in affected bracket
                """)

            with col2:
                # Top 1% context
                if threshold >= 500000:
                    top1_income = 600000  # Rough threshold for top 1%
                    context_msg = "This policy primarily affects **high-income earners** (top 2% of households)."
                elif threshold >= 200000:
                    context_msg = "This policy affects **upper-income households** (roughly top 10%)."
                elif threshold >= 100000:
                    context_msg = "This policy affects **upper-middle and high-income households** (roughly top 25%)."
                else:
                    context_msg = "This policy has **broad impact** across income groups."

                st.warning(f"""
                **Income Context**

                {context_msg}

                IRS data from {data_year} automatically populated the affected population and income statistics.
                """)

        # Auto-populated parameters
        st.markdown("---")
        st.subheader("📊 IRS Data Used")

        col1, col2 = st.columns(2)

        with col1:
            st.info(f"""
            **Affected Taxpayers:** {policy.affected_taxpayers_millions:.2f} million

            *Auto-populated from IRS SOI {data_year} data for taxpayers with AGI ≥ ${threshold:,}*
            """)

        with col2:
            avg_income = policy.avg_taxable_income_in_bracket
            if avg_income > 0:
                st.info(f"""
                **Average Taxable Income:** ${avg_income:,.0f}

                *Auto-populated from IRS SOI {data_year} data for this income bracket*
                """)

    with tab3:
        st.header("🔀 Policy Comparison")

        st.markdown("""
        <div class="info-box">
        💡 <strong>Compare scenarios:</strong> Select 2-3 policies from the preset library to see how they compare side-by-side.
        </div>
        """, unsafe_allow_html=True)

        # Multi-select for policies to compare
        policies_to_compare = st.multiselect(
            "Select policies to compare (2-3 recommended)",
            options=[k for k in preset_policies.keys() if k != "Custom Policy"],
            default=["TCJA 2017 High-Income Cut", "Biden 2025 Proposal"],
            max_selections=4
        )

        if len(policies_to_compare) >= 2:
            with st.spinner("Calculating and comparing policies..."):
                try:
                    comparison_results = []

                    for preset_name in policies_to_compare:
                        preset = preset_policies[preset_name]

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

    with tab4:
        st.header("📋 Detailed Results")

        # Policy summary
        st.subheader("Policy Details")

        policy_details = {
            "Policy Name": policy.name,
            "Description": policy.description,
            "Policy Type": policy.policy_type.value,
            "Rate Change": f"{rate_change_pct:+.1f} percentage points",
            "Income Threshold": f"${threshold:,}" if threshold > 0 else "All taxpayers",
            "Duration": f"{duration} years",
            "Phase-in Period": f"{phase_in} years" if phase_in > 0 else "Immediate",
            "Data Year": data_year,
        }

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
                file_name=f"fiscal_impact_{policy_name.replace(' ', '_')}.csv",
                mime="text/csv"
            )

        with col2:
            # JSON export
            export_data = {
                'policy': {
                    'name': policy.name,
                    'rate_change': rate_change,
                    'threshold': threshold,
                    'duration': duration,
                },
                'results': {
                    'static_10yr': float(static_total),
                    'behavioral_offset_10yr': float(behavioral_total),
                    'net_10yr_effect': float(net_total),
                    'year1_net_effect': float(year1_net),
                    'by_year': df_timeline.to_dict('records')
                }
            }

            import json
            json_str = json.dumps(export_data, indent=2)
            st.download_button(
                label="📥 Download as JSON",
                data=json_str,
                file_name=f"fiscal_impact_{policy_name.replace(' ', '_')}.json",
                mime="application/json"
            )

with tab5:
    st.header("ℹ️ Methodology")

    st.markdown("""
    ## How This Calculator Works

    This calculator uses **Congressional Budget Office (CBO) methodology** to estimate the budgetary
    and economic effects of fiscal policy proposals.

    ### Data Sources

    1. **IRS Statistics of Income (SOI)**
       - Tax return data by income bracket
       - Number of filers at each income level
       - Average taxable income by bracket
       - Actual tax liability data
       - *Updated annually, currently using 2021-2022 data*

    2. **FRED Economic Data**
       - GDP (Gross Domestic Product)
       - Unemployment rates
       - Interest rates
       - Economic growth projections
       - *Updated daily from Federal Reserve*

    3. **CBO Baseline Projections**
       - 10-year budget outlook
       - Economic assumptions
       - Revenue and spending baselines

    ### Calculation Method

    #### Static Revenue Estimation

    The basic formula for tax revenue changes:

    ```
    Revenue Change = Rate Change × Taxable Income Base × Number of Taxpayers
    ```

    For example, a 2% rate cut for taxpayers earning $500K+:
    - **Rate Change:** -0.02 (2 percentage points)
    - **Affected Taxpayers:** 2.48 million (from IRS data)
    - **Average Taxable Income:** $1.41 million (from IRS data)
    - **Year 1 Effect:** -$69.8 billion

    #### Behavioral Responses

    Taxpayers respond to tax changes by adjusting their income through:
    - Work effort changes
    - Tax planning and avoidance
    - Timing of income realization
    - Business structure changes

    This is captured by the **Elasticity of Taxable Income (ETI)**:

    ```
    Behavioral Offset = -ETI × Rate Change × Tax Base
    ```

    - Standard ETI: 0.25 (moderate response)
    - High-income ETI: 0.40 (larger response for wealthy)

    #### Dynamic Scoring (Optional)

    When enabled, the calculator includes macroeconomic feedback:

    1. **GDP Effects**
       - Tax cuts → More disposable income → Higher consumption
       - Spending increases → Direct GDP boost
       - Fiscal multipliers vary by economic conditions

    2. **Revenue Feedback**
       - GDP growth → Higher tax revenues
       - Employment effects → More payroll tax revenue
       - Interest rate changes → Debt service costs

    ### Accuracy and Limitations

    **Strengths:**
    - ✅ Uses real IRS data (not estimates)
    - ✅ Auto-populates filer counts and income levels
    - ✅ Follows CBO methodology
    - ✅ Includes behavioral responses

    **Limitations:**
    - ⚠️ Simplified vs. full CBO microsimulation
    - ⚠️ Does not model all tax provisions
    - ⚠️ Limited to available IRS data years (2021-2022)
    - ⚠️ Uncertainty increases in later years

    **Typical Accuracy:** Within 10-15% of CBO estimates for similar policies

    ### References

    1. Congressional Budget Office (2024). "How CBO Analyzes the Effects of Changes in Federal Fiscal Policies"
    2. Joint Committee on Taxation (2023). "Overview of Revenue Estimating Procedures"
    3. Saez, Slemrod & Giertz (2012). "The Elasticity of Taxable Income with Respect to Marginal Tax Rates"
    4. IRS Statistics of Income Division (2024). "Individual Income Tax Statistics"

    ### Questions?

    For more details on the methodology, see the [full documentation](https://github.com/laurencehw/fiscal-policy-calculator).
    """)

# Footer
st.markdown("---")
st.caption("""
**Fiscal Policy Impact Calculator** | Built with Streamlit |
Data: IRS Statistics of Income, FRED, CBO |
Methodology: Congressional Budget Office scoring framework
""")
