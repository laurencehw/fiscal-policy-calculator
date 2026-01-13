"""
Application data for the Fiscal Policy Calculator.

Contains:
- CBO_SCORE_MAP: Official CBO/JCT scores for preset policies
- PRESET_POLICIES: Preset policy configurations
"""

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
    "👶 Biden CTC Expansion (CBO: $1.6T)": {
        "official_score": 1600.0,
        "source": "JCT",
        "source_date": "2021",
        "notes": "$3,600/$3,000 per child, fully refundable, monthly payments",
    },
    "👶 CTC Extension (CBO: $600B)": {
        "official_score": 600.0,
        "source": "CBO",
        "source_date": "2024",
        "notes": "Extend current $2,000 CTC beyond 2025",
    },
    "💼 EITC Childless Expansion (CBO: $178B)": {
        "official_score": 178.0,
        "source": "JCT",
        "source_date": "2021",
        "notes": "Triple EITC for childless workers, expand age range",
    },
    # Estate Tax
    "🏠 Estate Tax: Extend TCJA (CBO: $167B)": {
        "official_score": 167.0,
        "source": "CBO",
        "source_date": "2024",
        "notes": "Maintain doubled exemption ($13.6M) beyond 2025",
    },
    "🏠 Biden Estate Reform (-$450B)": {
        "official_score": -450.0,
        "source": "Treasury",
        "source_date": "2024",
        "notes": "Return to 2009 parameters: $3.5M exemption, 45% rate",
    },
    "🏠 Eliminate Estate Tax ($350B)": {
        "official_score": 350.0,  # ~$35B/yr
        "source": "JCT",
        "source_date": "2024",
        "notes": "Repeal federal estate tax entirely",
    },
    # Payroll Tax
    "💰 SS Cap to 90% (CBO: -$800B)": {
        "official_score": -800.0,
        "source": "CBO",
        "source_date": "2024",
        "notes": "Raise SS wage cap from $168K to ~$305K",
    },
    "💰 SS Donut Hole $250K (-$2.7T)": {
        "official_score": -2700.0,
        "source": "SS Trustees",
        "source_date": "2024",
        "notes": "Apply payroll tax above $250K (donut hole)",
    },
    "💰 Eliminate SS Cap (-$3.2T)": {
        "official_score": -3200.0,
        "source": "SS Trustees",
        "source_date": "2024",
        "notes": "Apply SS tax to all wages (no cap)",
    },
    "💰 Expand NIIT (JCT: -$250B)": {
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
    "🏥 Extend ACA Enhanced PTCs ($350B)": {
        "official_score": 350.0,
        "source": "CBO",
        "source_date": "2024",
        "notes": "Extend ACA enhanced premium subsidies beyond 2025",
    },
    "🏥 Repeal ACA Premium Credits (-$1.1T)": {
        "official_score": -1100.0,
        "source": "CBO",
        "source_date": "2024",
        "notes": "Eliminate all ACA premium tax credits",
    },
    # Tax Expenditures
    "📋 Cap Employer Health Exclusion (-$450B)": {
        "official_score": -450.0,
        "source": "JCT",
        "source_date": "2024",
        "notes": "Cap exclusion at 28% rate or ~$25K",
    },
    "📋 Eliminate Mortgage Deduction (-$300B)": {
        "official_score": -300.0,
        "source": "JCT",
        "source_date": "2024",
        "notes": "Repeal mortgage interest deduction",
    },
    "📋 Repeal SALT Cap ($1.1T)": {
        "official_score": 1100.0,
        "source": "JCT",
        "source_date": "2024",
        "notes": "Remove $10K cap on state/local tax deduction",
    },
    "📋 Eliminate SALT Deduction (-$1.2T)": {
        "official_score": -1200.0,
        "source": "JCT",
        "source_date": "2024",
        "notes": "Repeal state/local tax deduction entirely",
    },
    "📋 Cap Charitable Deduction (-$200B)": {
        "official_score": -200.0,
        "source": "Treasury",
        "source_date": "2024",
        "notes": "Limit charitable deduction to 28% rate",
    },
    "📋 Eliminate Step-Up Basis (-$500B)": {
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


# =============================================================================
# PRESET POLICIES - Preset policy configurations for the UI
# =============================================================================
PRESET_POLICIES = {
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
        "description": "Lower all rates by 5pp (illustrative)",
        "is_tcja": False,
    },
}
