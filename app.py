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
    from fiscal_model.validation.cbo_scores import KNOWN_SCORES, CBOScore, ScoreSource
    MODEL_AVAILABLE = True
    MACRO_AVAILABLE = True
except ImportError as e:
    MODEL_AVAILABLE = False
    MACRO_AVAILABLE = False
    st.error(f"⚠️ Could not import fiscal model: {e}")

# =============================================================================
# CBO SCORE MAPPING - Maps preset policy names to official CBO/JCT scores
# =============================================================================
CBO_SCORE_MAP = {
    # TCJA Extension
    "🏛️ TCJA Full Extension (CBO: $4.6T)": {
        "official_score": 4600.0,
        "source": "CBO",
        "source_date": "May 2024",
        "source_url": "https://www.cbo.gov/publication/59710",
        "notes": "Extend all individual TCJA provisions beyond 2025 sunset",
    },
    "🏛️ TCJA Extension (No SALT Cap)": {
        "official_score": 6500.0,  # ~$4.6T + $1.9T SALT
        "source": "CBO/JCT",
        "source_date": "2024",
        "notes": "TCJA extension + repeal $10K SALT cap (~$1.9T additional)",
    },
    "🏛️ TCJA Rates Only": {
        "official_score": 3200.0,
        "source": "CBO",
        "source_date": "2024",
        "notes": "Extend only individual rate bracket cuts",
    },
    # Corporate
    "🏢 Biden Corporate 28% (CBO: -$1.35T)": {
        "official_score": -1347.0,
        "source": "Treasury",
        "source_date": "March 2024",
        "source_url": "https://home.treasury.gov/system/files/131/General-Explanations-FY2025.pdf",
        "notes": "Increase corporate rate from 21% to 28%",
    },
    "🏢 Trump Corporate 15%": {
        "official_score": 673.0,  # ~$67.3B/yr based on CRFB estimates
        "source": "CRFB",
        "source_date": "2024",
        "notes": "Reduce corporate rate from 21% to 15%",
    },
    # Tax Credits
    "👶 Biden CTC 2021 ($1.6T)": {
        "official_score": 1600.0,
        "source": "JCT",
        "source_date": "2021",
        "notes": "$3,600/$3,000 per child, fully refundable, monthly payments",
    },
    "👶 CTC Permanent Extension ($600B)": {
        "official_score": 600.0,
        "source": "CBO",
        "source_date": "2024",
        "notes": "Extend current $2,000 CTC beyond 2025",
    },
    "👷 EITC Childless Expansion": {
        "official_score": 178.0,
        "source": "JCT",
        "source_date": "2021",
        "notes": "Triple EITC for childless workers, expand age range",
    },
    # Estate Tax
    "🏠 Estate: Extend TCJA ($167B)": {
        "official_score": 167.0,
        "source": "CBO",
        "source_date": "2024",
        "notes": "Maintain doubled exemption ($13.6M) beyond 2025",
    },
    "🏠 Estate: Biden Reform (-$450B)": {
        "official_score": -450.0,
        "source": "Treasury",
        "source_date": "2024",
        "notes": "Return to 2009 parameters: $3.5M exemption, 45% rate",
    },
    "🏠 Estate: Eliminate Tax": {
        "official_score": 300.0,  # ~$30B/yr
        "source": "JCT",
        "source_date": "2024",
        "notes": "Repeal federal estate tax entirely",
    },
    # Payroll Tax
    "💼 SS Cap to 90% Coverage (-$800B)": {
        "official_score": -800.0,
        "source": "CBO",
        "source_date": "2024",
        "notes": "Raise SS wage cap from $168K to ~$305K",
    },
    "💼 SS Donut Hole $250K (-$2.7T)": {
        "official_score": -2700.0,
        "source": "SS Trustees",
        "source_date": "2024",
        "notes": "Apply payroll tax above $250K (donut hole)",
    },
    "💼 Eliminate SS Cap (-$3.2T)": {
        "official_score": -3200.0,
        "source": "SS Trustees",
        "source_date": "2024",
        "notes": "Apply SS tax to all wages (no cap)",
    },
    "💼 Expand NIIT (-$250B)": {
        "official_score": -250.0,
        "source": "JCT",
        "source_date": "2024",
        "notes": "Apply 3.8% NIIT to pass-through business income",
    },
    # AMT
    "⚖️ AMT: Extend TCJA Relief ($450B)": {
        "official_score": 450.0,
        "source": "CBO",
        "source_date": "2024",
        "notes": "Maintain high AMT exemption beyond 2025",
    },
    "⚖️ Repeal Individual AMT ($450B)": {
        "official_score": 450.0,
        "source": "CBO",
        "source_date": "2024",
        "notes": "Eliminate individual AMT (post-TCJA sunset baseline)",
    },
    "⚖️ Repeal Corporate AMT (-$220B)": {
        "official_score": -220.0,
        "source": "CBO",
        "source_date": "2024",
        "notes": "Repeal 15% corporate book minimum tax (CAMT)",
    },
    # Premium Tax Credits
    "🏥 Extend Enhanced PTCs ($350B)": {
        "official_score": 350.0,
        "source": "CBO",
        "source_date": "2024",
        "notes": "Extend ACA enhanced premium subsidies beyond 2025",
    },
    "🏥 Repeal All PTCs (-$1.1T)": {
        "official_score": -1100.0,
        "source": "CBO",
        "source_date": "2024",
        "notes": "Eliminate all ACA premium tax credits",
    },
    # Tax Expenditures
    "💊 Cap Employer Health Exclusion (-$450B)": {
        "official_score": -450.0,
        "source": "JCT",
        "source_date": "2024",
        "notes": "Cap exclusion at 28% rate or ~$25K",
    },
    "🏠 Eliminate Mortgage Deduction (-$300B)": {
        "official_score": -300.0,
        "source": "JCT",
        "source_date": "2024",
        "notes": "Repeal mortgage interest deduction",
    },
    "📍 Repeal SALT Cap ($1.1T)": {
        "official_score": 1100.0,
        "source": "JCT",
        "source_date": "2024",
        "notes": "Remove $10K cap on state/local tax deduction",
    },
    "📍 Eliminate SALT Deduction (-$1.2T)": {
        "official_score": -1200.0,
        "source": "JCT",
        "source_date": "2024",
        "notes": "Repeal state/local tax deduction entirely",
    },
    "🎁 Cap Charitable Deduction (-$200B)": {
        "official_score": -200.0,
        "source": "Treasury",
        "source_date": "2024",
        "notes": "Limit charitable deduction to 28% rate",
    },
    "💀 Eliminate Step-Up Basis (-$500B)": {
        "official_score": -500.0,
        "source": "Treasury",
        "source_date": "2024",
        "notes": "Tax unrealized gains at death (with exemptions)",
    },
    # Income Tax
    "Biden $400K+ Tax Increase": {
        "official_score": -252.0,
        "source": "Treasury",
        "source_date": "March 2024",
        "source_url": "https://home.treasury.gov/system/files/131/General-Explanations-FY2025.pdf",
        "notes": "Restore 39.6% top rate for income above $400K",
    },
}

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
                                   help="Include macroeconomic feedback effects (GDP growth, employment, interest rates)")

    if dynamic_scoring:
        macro_model = st.selectbox(
            "Macro model",
            ["FRB/US-Lite (Recommended)", "Simple Multiplier"],
            help="FRB/US-Lite uses Federal Reserve-calibrated multipliers; Simple uses basic Keynesian multipliers"
        )

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
tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs(["💰 Tax Policy", "📈 Results & Charts", "🌍 Dynamic Scoring", "👥 Distribution", "🔀 Compare Policies", "📦 Policy Packages", "📋 Details", "ℹ️ Methodology"])

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
                "description": "Design your own policy",
                "is_tcja": False,
            },
        "🏛️ TCJA Full Extension (CBO: $4.6T)": {
            "rate_change": 0.0,
            "threshold": 0,
            "description": "Extend all TCJA individual provisions beyond 2025 sunset. Includes rate cuts, doubled standard deduction, SALT cap, pass-through deduction, CTC expansion.",
            "is_tcja": True,
            "tcja_type": "full",
        },
        "🏛️ TCJA Extension (No SALT Cap)": {
            "rate_change": 0.0,
            "threshold": 0,
            "description": "Extend TCJA but repeal the $10K SALT cap (adds ~$1.9T to cost). Popular bipartisan proposal.",
            "is_tcja": True,
            "tcja_type": "no_salt",
        },
        "🏛️ TCJA Rates Only": {
            "rate_change": 0.0,
            "threshold": 0,
            "description": "Extend only the individual rate bracket cuts, not other TCJA provisions (~$3.2T).",
            "is_tcja": True,
            "tcja_type": "rates_only",
        },
        "🏢 Biden Corporate 28% (CBO: -$1.35T)": {
            "rate_change": 0.0,
            "threshold": 0,
            "description": "Raise corporate rate from 21% to 28%. CBO estimate: raises ~$1.35T over 10 years.",
            "is_tcja": False,
            "is_corporate": True,
            "corporate_type": "biden_28",
        },
        "🏢 Trump Corporate 15%": {
            "rate_change": 0.0,
            "threshold": 0,
            "description": "Lower corporate rate from 21% to 15%. Estimated cost: ~$1.9T over 10 years.",
            "is_tcja": False,
            "is_corporate": True,
            "corporate_type": "trump_15",
        },
        "👶 Biden CTC Expansion (CBO: $1.6T)": {
            "rate_change": 0.0,
            "threshold": 0,
            "description": "Expand CTC to $3,600/$3,000 per child, fully refundable. Based on 2021 ARP expansion.",
            "is_tcja": False,
            "is_corporate": False,
            "is_credit": True,
            "credit_type": "biden_ctc_2021",
        },
        "👶 CTC Extension (CBO: $600B)": {
            "rate_change": 0.0,
            "threshold": 0,
            "description": "Extend current $2,000 CTC beyond 2025 sunset. Without extension, reverts to $1,000.",
            "is_tcja": False,
            "is_corporate": False,
            "is_credit": True,
            "credit_type": "ctc_extension",
        },
        "💼 EITC Childless Expansion (CBO: $178B)": {
            "rate_change": 0.0,
            "threshold": 0,
            "description": "Triple EITC for childless workers (~$1,500 max), expand age range to 19-65+.",
            "is_tcja": False,
            "is_corporate": False,
            "is_credit": True,
            "credit_type": "biden_eitc_childless",
        },
        "🏠 Estate Tax: Extend TCJA (CBO: $167B)": {
            "rate_change": 0.0,
            "threshold": 0,
            "description": "Keep ~$14M exemption (vs $6.4M if TCJA expires). Costs ~$167B over 10 years.",
            "is_tcja": False,
            "is_corporate": False,
            "is_credit": False,
            "is_estate": True,
            "estate_type": "extend_tcja",
        },
        "🏠 Biden Estate Reform (-$450B)": {
            "rate_change": 0.0,
            "threshold": 0,
            "description": "Lower exemption to $3.5M, raise rate to 45%. Raises ~$450B over 10 years.",
            "is_tcja": False,
            "is_corporate": False,
            "is_credit": False,
            "is_estate": True,
            "estate_type": "biden_reform",
        },
        "🏠 Eliminate Estate Tax ($350B)": {
            "rate_change": 0.0,
            "threshold": 0,
            "description": "Repeal federal estate tax entirely. Costs ~$350B over 10 years.",
            "is_tcja": False,
            "is_corporate": False,
            "is_credit": False,
            "is_estate": True,
            "estate_type": "eliminate",
        },
        "💰 SS Cap to 90% (CBO: -$800B)": {
            "rate_change": 0.0,
            "threshold": 0,
            "description": "Raise Social Security cap to cover 90% of wages (~$305K). Raises ~$800B.",
            "is_tcja": False,
            "is_corporate": False,
            "is_payroll": True,
            "payroll_type": "cap_90",
        },
        "💰 SS Donut Hole $250K (-$2.7T)": {
            "rate_change": 0.0,
            "threshold": 0,
            "description": "Apply SS tax to wages above $250K (donut hole). Raises ~$2.7T over 10 years.",
            "is_tcja": False,
            "is_corporate": False,
            "is_payroll": True,
            "payroll_type": "donut_250k",
        },
        "💰 Eliminate SS Cap (-$3.2T)": {
            "rate_change": 0.0,
            "threshold": 0,
            "description": "Eliminate Social Security wage cap entirely. Raises ~$3.2T over 10 years.",
            "is_tcja": False,
            "is_corporate": False,
            "is_payroll": True,
            "payroll_type": "eliminate_cap",
        },
        "💰 Expand NIIT (JCT: -$250B)": {
            "rate_change": 0.0,
            "threshold": 0,
            "description": "Apply 3.8% NIIT to S-corp/partnership income. Raises ~$250B over 10 years.",
            "is_tcja": False,
            "is_corporate": False,
            "is_payroll": True,
            "payroll_type": "expand_niit",
        },
        "⚖️ AMT: Extend TCJA Relief ($450B)": {
            "rate_change": 0.0,
            "threshold": 0,
            "description": "Extend TCJA's higher AMT exemptions ($88K single, $137K MFJ) past 2025. Costs ~$450B.",
            "is_tcja": False,
            "is_corporate": False,
            "is_amt": True,
            "amt_type": "extend_tcja",
        },
        "⚖️ Repeal Individual AMT ($450B)": {
            "rate_change": 0.0,
            "threshold": 0,
            "description": "Fully repeal individual AMT. After TCJA expires, would cost ~$450B over 10 years.",
            "is_tcja": False,
            "is_corporate": False,
            "is_amt": True,
            "amt_type": "repeal_individual",
        },
        "⚖️ Repeal Corporate AMT (-$220B)": {
            "rate_change": 0.0,
            "threshold": 0,
            "description": "Repeal 15% book minimum tax (CAMT) from IRA 2022. Costs ~$220B over 10 years.",
            "is_tcja": False,
            "is_corporate": False,
            "is_amt": True,
            "amt_type": "repeal_corporate",
        },
        "🏥 Extend ACA Enhanced PTCs ($350B)": {
            "rate_change": 0.0,
            "threshold": 0,
            "description": "Extend enhanced premium tax credits (ARPA/IRA) past 2025. Costs ~$350B over 10 years.",
            "is_tcja": False,
            "is_corporate": False,
            "is_ptc": True,
            "ptc_type": "extend_enhanced",
        },
        "🏥 Repeal ACA Premium Credits (-$1.1T)": {
            "rate_change": 0.0,
            "threshold": 0,
            "description": "Repeal all ACA premium subsidies. Saves ~$1.1T but ~19M lose subsidized coverage.",
            "is_tcja": False,
            "is_corporate": False,
            "is_ptc": True,
            "ptc_type": "repeal",
        },
        "📋 Cap Employer Health Exclusion (-$450B)": {
            "rate_change": 0.0,
            "threshold": 0,
            "description": "Cap tax exclusion for employer health insurance at $50K. Raises ~$450B over 10 years.",
            "is_tcja": False,
            "is_corporate": False,
            "is_expenditure": True,
            "expenditure_type": "cap_employer_health",
        },
        "📋 Repeal SALT Cap ($1.1T)": {
            "rate_change": 0.0,
            "threshold": 0,
            "description": "Remove $10K cap on state and local tax deduction. Costs ~$1.1T over 10 years.",
            "is_tcja": False,
            "is_corporate": False,
            "is_expenditure": True,
            "expenditure_type": "repeal_salt_cap",
        },
        "📋 Eliminate Step-Up Basis (-$500B)": {
            "rate_change": 0.0,
            "threshold": 0,
            "description": "Tax capital gains at death with $1M exemption. Raises ~$500B over 10 years.",
            "is_tcja": False,
            "is_corporate": False,
            "is_expenditure": True,
            "expenditure_type": "eliminate_step_up",
        },
        "📋 Cap Charitable Deduction (-$200B)": {
            "rate_change": 0.0,
            "threshold": 0,
            "description": "Limit charitable deduction value to 28% rate. Raises ~$200B over 10 years.",
            "is_tcja": False,
            "is_corporate": False,
            "is_expenditure": True,
            "expenditure_type": "cap_charitable",
        },
        "Biden 2025 Proposal": {
            "rate_change": 2.6,
            "threshold": 400000,
            "description": "Restore top rate to 39.6% for AGI > $400K",
            "is_tcja": False,
            "is_corporate": False,
        },
        "Progressive Millionaire Tax": {
            "rate_change": 5.0,
            "threshold": 1000000,
            "description": "5pp surtax on millionaires",
            "is_tcja": False,
        },
        "Middle Class Tax Cut": {
            "rate_change": -2.0,
            "threshold": 50000,
            "description": "2pp cut for households earning $50K+",
            "is_tcja": False,
        },
        "Flat Tax Reform": {
            "rate_change": -5.0,
            "threshold": 0,
            "description": "Simplified flat tax with lower rates across the board",
            "is_tcja": False,
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
                # Check if this is a TCJA extension policy
                preset_data = preset_policies[preset_choice]
                is_tcja_policy = preset_data.get("is_tcja", False)

                if is_tcja_policy:
                    # Create TCJA extension policy
                    tcja_type = preset_data.get("tcja_type", "full")

                    if tcja_type == "full":
                        policy = create_tcja_extension(extend_all=True, keep_salt_cap=True)
                    elif tcja_type == "no_salt":
                        policy = create_tcja_repeal_salt_cap()
                    elif tcja_type == "rates_only":
                        policy = create_tcja_extension(
                            extend_all=False,
                            extend_rate_cuts=True,
                            extend_standard_deduction=False,
                            keep_exemption_elimination=False,
                            extend_passthrough=False,
                            extend_ctc=False,
                            extend_estate=False,
                            extend_amt=False,
                            keep_salt_cap=False,
                        )
                    else:
                        policy = create_tcja_extension(extend_all=True)

                    # Score TCJA policy
                    scorer = FiscalPolicyScorer(start_year=2026, use_real_data=False)
                    result = scorer.score_policy(policy, dynamic=dynamic_scoring)

                    # Store in session state
                    st.session_state.results = {
                        'policy': policy,
                        'result': result,
                        'scorer': scorer,
                        'is_spending': False,
                        'is_tcja': True,
                        'tcja_type': tcja_type,
                        'policy_name': preset_choice,
                    }

                    st.success("✅ Calculation complete!")

                elif preset_data.get("is_corporate", False):
                    # Corporate tax policy
                    corporate_type = preset_data.get("corporate_type", "biden_28")

                    if corporate_type == "biden_28":
                        policy = create_biden_corporate_rate_only()
                    elif corporate_type == "trump_15":
                        policy = create_republican_corporate_cut()
                    else:
                        policy = create_biden_corporate_rate_only()

                    # Score corporate policy
                    scorer = FiscalPolicyScorer(start_year=2025, use_real_data=False)
                    result = scorer.score_policy(policy, dynamic=dynamic_scoring)

                    # Store in session state
                    st.session_state.results = {
                        'policy': policy,
                        'result': result,
                        'scorer': scorer,
                        'is_spending': False,
                        'is_tcja': False,
                        'is_corporate': True,
                        'corporate_type': corporate_type,
                        'policy_name': preset_choice,
                    }

                    st.success("✅ Calculation complete!")

                elif preset_data.get("is_credit", False):
                    # Tax credit policy
                    credit_type = preset_data.get("credit_type", "biden_ctc_2021")

                    if credit_type == "biden_ctc_2021":
                        policy = create_biden_ctc_2021()
                    elif credit_type == "ctc_extension":
                        policy = create_ctc_permanent_extension()
                    elif credit_type == "biden_eitc_childless":
                        policy = create_biden_eitc_childless()
                    else:
                        policy = create_biden_ctc_2021()

                    # Score credit policy
                    scorer = FiscalPolicyScorer(start_year=policy.start_year, use_real_data=False)
                    result = scorer.score_policy(policy, dynamic=dynamic_scoring)

                    # Store in session state
                    st.session_state.results = {
                        'policy': policy,
                        'result': result,
                        'scorer': scorer,
                        'is_spending': False,
                        'is_tcja': False,
                        'is_corporate': False,
                        'is_credit': True,
                        'credit_type': credit_type,
                        'policy_name': preset_choice,
                    }

                    st.success("✅ Calculation complete!")

                elif preset_data.get("is_estate", False):
                    # Estate tax policy
                    estate_type = preset_data.get("estate_type", "extend_tcja")

                    if estate_type == "extend_tcja":
                        policy = create_tcja_estate_extension()
                    elif estate_type == "biden_reform":
                        policy = create_biden_estate_proposal()
                    elif estate_type == "eliminate":
                        policy = create_eliminate_estate_tax()
                    else:
                        policy = create_tcja_estate_extension()

                    # Score estate policy
                    scorer = FiscalPolicyScorer(start_year=policy.start_year, use_real_data=False)
                    result = scorer.score_policy(policy, dynamic=dynamic_scoring)

                    # Store in session state
                    st.session_state.results = {
                        'policy': policy,
                        'result': result,
                        'scorer': scorer,
                        'is_spending': False,
                        'is_tcja': False,
                        'is_corporate': False,
                        'is_credit': False,
                        'is_estate': True,
                        'estate_type': estate_type,
                        'policy_name': preset_choice,
                    }

                    st.success("✅ Calculation complete!")

                elif preset_data.get("is_payroll", False):
                    # Payroll tax policy
                    payroll_type = preset_data.get("payroll_type", "cap_90")

                    if payroll_type == "cap_90":
                        policy = create_ss_cap_90_percent()
                    elif payroll_type == "donut_250k":
                        policy = create_ss_donut_hole()
                    elif payroll_type == "eliminate_cap":
                        policy = create_ss_eliminate_cap()
                    elif payroll_type == "expand_niit":
                        policy = create_expand_niit()
                    else:
                        policy = create_ss_cap_90_percent()

                    # Score payroll policy
                    scorer = FiscalPolicyScorer(start_year=policy.start_year, use_real_data=False)
                    result = scorer.score_policy(policy, dynamic=dynamic_scoring)

                    # Store in session state
                    st.session_state.results = {
                        'policy': policy,
                        'result': result,
                        'scorer': scorer,
                        'is_spending': False,
                        'is_tcja': False,
                        'is_corporate': False,
                        'is_credit': False,
                        'is_estate': False,
                        'is_payroll': True,
                        'payroll_type': payroll_type,
                        'policy_name': preset_choice,
                    }

                    st.success("✅ Calculation complete!")

                elif preset_data.get("is_amt", False):
                    # AMT policy
                    amt_type = preset_data.get("amt_type", "extend_tcja")

                    if amt_type == "extend_tcja":
                        policy = create_extend_tcja_amt_relief()
                    elif amt_type == "repeal_individual":
                        # Use start_year=2026 to match CBO $450B estimate (post-TCJA sunset)
                        policy = create_repeal_individual_amt(start_year=2026)
                    elif amt_type == "repeal_corporate":
                        policy = create_repeal_corporate_amt()
                    else:
                        policy = create_extend_tcja_amt_relief()

                    # Score AMT policy
                    scorer = FiscalPolicyScorer(start_year=policy.start_year, use_real_data=False)
                    result = scorer.score_policy(policy, dynamic=dynamic_scoring)

                    # Store in session state
                    st.session_state.results = {
                        'policy': policy,
                        'result': result,
                        'scorer': scorer,
                        'is_spending': False,
                        'is_tcja': False,
                        'is_corporate': False,
                        'is_credit': False,
                        'is_estate': False,
                        'is_payroll': False,
                        'is_amt': True,
                        'policy_name': preset_choice,
                        'amt_type': amt_type,
                    }

                    st.success("✅ Calculation complete!")

                elif preset_data.get("is_ptc", False):
                    # Premium Tax Credit policy
                    ptc_type = preset_data.get("ptc_type", "extend_enhanced")

                    if ptc_type == "extend_enhanced":
                        policy = create_extend_enhanced_ptc()
                    elif ptc_type == "repeal":
                        policy = create_repeal_ptc()
                    else:
                        policy = create_extend_enhanced_ptc()

                    # Score PTC policy
                    scorer = FiscalPolicyScorer(start_year=policy.start_year, use_real_data=False)
                    result = scorer.score_policy(policy, dynamic=dynamic_scoring)

                    # Store in session state
                    st.session_state.results = {
                        'policy': policy,
                        'result': result,
                        'scorer': scorer,
                        'is_spending': False,
                        'is_tcja': False,
                        'is_corporate': False,
                        'is_credit': False,
                        'is_estate': False,
                        'is_payroll': False,
                        'is_amt': False,
                        'is_ptc': True,
                        'policy_name': preset_choice,
                        'ptc_type': ptc_type,
                    }

                    st.success("✅ Calculation complete!")

                elif preset_data.get("is_expenditure", False):
                    # Tax Expenditure policy
                    expenditure_type = preset_data.get("expenditure_type", "cap_employer_health")

                    if expenditure_type == "cap_employer_health":
                        policy = create_cap_employer_health_exclusion()
                    elif expenditure_type == "repeal_salt_cap":
                        policy = create_repeal_salt_cap()
                    elif expenditure_type == "eliminate_step_up":
                        policy = create_eliminate_step_up_basis()
                    elif expenditure_type == "cap_charitable":
                        policy = create_cap_charitable_deduction()
                    else:
                        policy = create_cap_employer_health_exclusion()

                    # Score expenditure policy
                    scorer = FiscalPolicyScorer(start_year=policy.start_year, use_real_data=False)
                    result = scorer.score_policy(policy, dynamic=dynamic_scoring)

                    # Store in session state
                    st.session_state.results = {
                        'policy': policy,
                        'result': result,
                        'scorer': scorer,
                        'is_spending': False,
                        'is_tcja': False,
                        'is_corporate': False,
                        'is_credit': False,
                        'is_estate': False,
                        'is_payroll': False,
                        'is_amt': False,
                        'is_ptc': False,
                        'is_expenditure': True,
                        'policy_name': preset_choice,
                        'expenditure_type': expenditure_type,
                    }

                    st.success("✅ Calculation complete!")

                else:
                    # Non-TCJA, non-corporate tax policy
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

        # =================================================================
        # COMPARE TO CBO/JCT SECTION
        # =================================================================
        # Check if this policy has an official CBO/JCT score to compare
        policy_name = result_data.get('policy_name', '')
        cbo_data = CBO_SCORE_MAP.get(policy_name)

        if cbo_data:
            st.markdown("---")
            st.subheader("🏛️ Compare to Official Score")

            official_score = cbo_data['official_score']
            # CBO convention: positive = cost (deficit increase), negative = revenue (deficit decrease)
            # Our model: positive = revenue gain, negative = revenue loss
            # So we negate our score to match CBO convention
            model_score = -net_total

            # Calculate error
            if official_score != 0:
                error_pct = ((model_score - official_score) / abs(official_score)) * 100
                abs_error_pct = abs(error_pct)
            else:
                error_pct = 0
                abs_error_pct = 0

            # Determine accuracy rating
            if abs_error_pct <= 5:
                accuracy_rating = "Excellent"
                rating_color = "#28a745"  # green
                rating_emoji = "🎯"
            elif abs_error_pct <= 10:
                accuracy_rating = "Good"
                rating_color = "#17a2b8"  # blue
                rating_emoji = "✅"
            elif abs_error_pct <= 15:
                accuracy_rating = "Acceptable"
                rating_color = "#ffc107"  # yellow
                rating_emoji = "⚠️"
            else:
                accuracy_rating = "Needs Review"
                rating_color = "#dc3545"  # red
                rating_emoji = "❌"

            # Display comparison
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    f"Official ({cbo_data['source']})",
                    f"${official_score:,.0f}B",
                    help=f"Source: {cbo_data['source']} ({cbo_data['source_date']})"
                )

            with col2:
                st.metric(
                    "Model Estimate",
                    f"${model_score:,.0f}B",
                    help="Our model's 10-year estimate"
                )

            with col3:
                st.metric(
                    "Difference",
                    f"${model_score - official_score:+,.0f}B",
                    delta=f"{error_pct:+.1f}%",
                    delta_color="off"
                )

            with col4:
                st.markdown(f"""
                <div style="text-align: center; padding: 0.5rem;">
                    <span style="font-size: 2rem;">{rating_emoji}</span>
                    <br>
                    <span style="color: {rating_color}; font-weight: bold; font-size: 1.1rem;">
                        {accuracy_rating}
                    </span>
                    <br>
                    <span style="color: #666; font-size: 0.9rem;">
                        {abs_error_pct:.1f}% error
                    </span>
                </div>
                """, unsafe_allow_html=True)

            # Visual comparison bar
            st.markdown("##### Score Comparison")

            # Create horizontal bar chart
            fig_compare = go.Figure()

            # Determine colors based on direction
            official_color = '#1f77b4'
            model_color = '#2ca02c' if abs_error_pct <= 10 else '#ff7f0e'

            fig_compare.add_trace(go.Bar(
                y=['Official Score', 'Model Estimate'],
                x=[official_score, model_score],
                orientation='h',
                marker_color=[official_color, model_color],
                text=[f"${official_score:,.0f}B", f"${model_score:,.0f}B"],
                textposition='auto',
            ))

            fig_compare.update_layout(
                height=150,
                margin=dict(l=20, r=20, t=20, b=20),
                xaxis_title="10-Year Budget Impact ($B)",
                showlegend=False,
            )

            st.plotly_chart(fig_compare, use_container_width=True)

            # Source details
            with st.expander("📋 Source Details"):
                st.markdown(f"""
                **Official Estimate:** ${official_score:,.0f}B over 10 years

                **Source:** {cbo_data['source']} ({cbo_data['source_date']})

                **Policy Description:** {cbo_data['notes']}

                **Model Accuracy:**
                - Error: {error_pct:+.1f}% ({accuracy_rating})
                - Difference: ${model_score - official_score:+,.0f}B
                """)

                if cbo_data.get('source_url'):
                    st.markdown(f"[View Original Source]({cbo_data['source_url']})")

                st.markdown("""
                ---
                **Accuracy Ratings:**
                - 🎯 **Excellent**: Within 5% of official score
                - ✅ **Good**: Within 10% of official score
                - ⚠️ **Acceptable**: Within 15% of official score
                - ❌ **Needs Review**: More than 15% difference
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
        if 'preset_policies' not in dir() or is_spending:
            st.info("📊 Policy comparison is available for tax policies. Select a tax policy category in the sidebar to use this feature.")
            policies_to_compare = []
        else:
            st.markdown("""
            <div class="info-box">
            💡 <strong>Compare scenarios:</strong> Select 2-3 policies from the preset library to see how they compare side-by-side.
            </div>
            """, unsafe_allow_html=True)

            # Multi-select for policies to compare
            comparison_options = [k for k in preset_policies.keys() if k != "Custom Policy"]
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

    # =========================================================================
    # TAB 6: POLICY PACKAGES
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

        # Add TCJA policies
        if 'preset_policies' in dir():
            for name, data in preset_policies.items():
                if name != "Custom Policy" and data.get("is_tcja"):
                    all_scorable_policies[name] = {"category": "TCJA", "data": data}
                elif name != "Custom Policy" and data.get("is_corporate"):
                    all_scorable_policies[name] = {"category": "Corporate", "data": data}
                elif name != "Custom Policy" and data.get("is_credit"):
                    all_scorable_policies[name] = {"category": "Tax Credits", "data": data}
                elif name != "Custom Policy" and data.get("is_estate"):
                    all_scorable_policies[name] = {"category": "Estate Tax", "data": data}
                elif name != "Custom Policy" and data.get("is_payroll"):
                    all_scorable_policies[name] = {"category": "Payroll Tax", "data": data}
                elif name != "Custom Policy" and data.get("is_amt"):
                    all_scorable_policies[name] = {"category": "AMT", "data": data}
                elif name != "Custom Policy" and data.get("is_ptc"):
                    all_scorable_policies[name] = {"category": "Premium Tax Credits", "data": data}
                elif name != "Custom Policy" and data.get("is_expenditure"):
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

                        # Create and score the policy based on type
                        if policy_data.get("is_tcja"):
                            tcja_type = policy_data.get("tcja_type", "full")
                            if tcja_type == "full":
                                policy = create_tcja_extension(extend_all=True, keep_salt_cap=True)
                            elif tcja_type == "no_salt":
                                policy = create_tcja_repeal_salt_cap()
                            elif tcja_type == "rates_only":
                                policy = create_tcja_extension(extend_all=False, extend_rate_cuts=True)
                            else:
                                policy = create_tcja_extension(extend_all=True)
                            scorer = FiscalPolicyScorer(start_year=2026, use_real_data=False)

                        elif policy_data.get("is_corporate"):
                            corporate_type = policy_data.get("corporate_type", "biden_28")
                            if corporate_type == "biden_28":
                                policy = create_biden_corporate_rate_only()
                            elif corporate_type == "trump_15":
                                policy = create_republican_corporate_cut()
                            else:
                                policy = create_biden_corporate_rate_only()
                            scorer = FiscalPolicyScorer(start_year=2025, use_real_data=False)

                        elif policy_data.get("is_credit"):
                            credit_type = policy_data.get("credit_type", "ctc_2021")
                            if credit_type == "ctc_2021":
                                policy = create_biden_ctc_2021()
                            elif credit_type == "ctc_extension":
                                policy = create_ctc_permanent_extension()
                            elif credit_type == "eitc_childless":
                                policy = create_biden_eitc_childless()
                            else:
                                policy = create_biden_ctc_2021()
                            scorer = FiscalPolicyScorer(start_year=policy.start_year, use_real_data=False)

                        elif policy_data.get("is_estate"):
                            estate_type = policy_data.get("estate_type", "extend_tcja")
                            if estate_type == "extend_tcja":
                                policy = create_tcja_estate_extension()
                            elif estate_type == "biden_reform":
                                policy = create_biden_estate_proposal()
                            elif estate_type == "eliminate":
                                policy = create_eliminate_estate_tax()
                            else:
                                policy = create_tcja_estate_extension()
                            scorer = FiscalPolicyScorer(start_year=policy.start_year, use_real_data=False)

                        elif policy_data.get("is_payroll"):
                            payroll_type = policy_data.get("payroll_type", "cap_90")
                            if payroll_type == "cap_90":
                                policy = create_ss_cap_90_percent()
                            elif payroll_type == "donut_250k":
                                policy = create_ss_donut_hole()
                            elif payroll_type == "eliminate_cap":
                                policy = create_ss_eliminate_cap()
                            elif payroll_type == "expand_niit":
                                policy = create_expand_niit()
                            else:
                                policy = create_ss_cap_90_percent()
                            scorer = FiscalPolicyScorer(start_year=policy.start_year, use_real_data=False)

                        elif policy_data.get("is_amt"):
                            amt_type = policy_data.get("amt_type", "extend_tcja")
                            if amt_type == "extend_tcja":
                                policy = create_extend_tcja_amt_relief()
                            elif amt_type == "repeal_individual":
                                policy = create_repeal_individual_amt()
                            elif amt_type == "repeal_corporate":
                                policy = create_repeal_corporate_amt()
                            else:
                                policy = create_extend_tcja_amt_relief()
                            scorer = FiscalPolicyScorer(start_year=policy.start_year, use_real_data=False)

                        elif policy_data.get("is_ptc"):
                            ptc_type = policy_data.get("ptc_type", "extend_enhanced")
                            if ptc_type == "extend_enhanced":
                                policy = create_extend_enhanced_ptc()
                            elif ptc_type == "repeal_all":
                                policy = create_repeal_ptc()
                            else:
                                policy = create_extend_enhanced_ptc()
                            scorer = FiscalPolicyScorer(start_year=policy.start_year, use_real_data=False)

                        elif policy_data.get("is_expenditure"):
                            exp_type = policy_data.get("expenditure_type", "cap_employer_health")
                            if exp_type == "cap_employer_health":
                                policy = create_cap_employer_health_exclusion()
                            elif exp_type == "eliminate_mortgage":
                                policy = create_eliminate_mortgage_deduction()
                            elif exp_type == "repeal_salt_cap":
                                policy = create_repeal_salt_cap()
                            elif exp_type == "eliminate_salt":
                                policy = create_eliminate_salt_deduction()
                            elif exp_type == "cap_charitable":
                                policy = create_cap_charitable_deduction()
                            elif exp_type == "eliminate_step_up":
                                policy = create_eliminate_step_up_basis()
                            else:
                                policy = create_cap_employer_health_exclusion()
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

                df_components = pd.DataFrame(package_results)
                df_components["10-Year Impact"] = df_components["cbo_net"].apply(lambda x: f"${x:,.0f}B")
                df_components["Official Score"] = df_components["official"].apply(
                    lambda x: f"${x:,.0f}B" if x is not None else "N/A"
                )
                df_components["Category"] = df_components["category"]
                df_components["Policy"] = df_components["name"]

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
                    st.download_button(
                        "📥 Download as JSON",
                        data=pd.io.json.dumps(export_data, indent=2),
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

    with tab7:
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

with tab8:
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
