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
        "notes": "TCJA extension + repeal \\$10K SALT cap (~\\$1.9T additional)",
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
        "notes": "\\$3,600/\\$3,000 per child, fully refundable, monthly payments",
    },
    "👶 CTC Extension (CBO: $600B)": {
        "official_score": 600.0,
        "source": "CBO",
        "source_date": "2024",
        "notes": "Extend current \\$2,000 CTC beyond 2025",
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
        "notes": "Maintain doubled exemption (\\$13.6M) beyond 2025",
    },
    "🏠 Biden Estate Reform (-$450B)": {
        "official_score": -450.0,
        "source": "Treasury",
        "source_date": "2024",
        "notes": "Return to 2009 parameters: \\$3.5M exemption, 45% rate",
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
        "notes": "Raise SS wage cap from \\$168K to ~\\$305K",
    },
    "💰 SS Donut Hole $250K (-$2.7T)": {
        "official_score": -2700.0,
        "source": "SS Trustees",
        "source_date": "2024",
        "notes": "Apply payroll tax above \\$250K (donut hole)",
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
        "notes": "Cap exclusion at 28% rate or ~\\$25K",
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
        "notes": "Remove \\$10K cap on state/local tax deduction",
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
    "Biden 2025 Proposal": {
        "official_score": -252.0,
        "source": "Treasury",
        "source_date": "March 2024",
        "source_url": "https://home.treasury.gov/system/files/131/General-Explanations-FY2025.pdf",
        "notes": "Restore 39.6% top rate for income above \\$400K",
    },
    "Warren Ultra-Millionaire Surtax": {
        "official_score": -350.0,
        "source": "TPC",
        "source_date": "2020",
        "source_url": "https://www.taxpolicycenter.org/",
        "notes": "3pp surtax on AGI >\\$2M; TPC-range estimate",
    },
    "Top Rate to 45%": {
        "official_score": -420.0,
        "source": "TPC",
        "source_date": "2023",
        "source_url": "https://www.taxpolicycenter.org/",
        "notes": "Raise top marginal rate from 37% to 45%; TPC-range estimate",
    },
    "High-Earner Medicare Surcharge 2pp": {
        "official_score": -310.0,
        "source": "Treasury",
        "source_date": "2024",
        "source_url": "https://home.treasury.gov/system/files/131/General-Explanations-FY2025.pdf",
        "notes": "+2pp Medicare surcharge on investment + wage income >\\$400K",
    },
    # International Tax
    "🌍 Biden GILTI Reform (-$280B)": {
        "official_score": -280.0,
        "source": "Treasury",
        "source_date": "FY2025 Green Book",
        "notes": "Country-by-country GILTI at 21%, eliminate QBAI exemption",
    },
    "🌍 Repeal FDII (-$200B)": {
        "official_score": -200.0,
        "source": "Treasury",
        "source_date": "FY2025",
        "notes": "Repeal Foreign-Derived Intangible Income deduction",
    },
    "🌍 Pillar Two Adoption (-$80B)": {
        "official_score": -80.0,
        "source": "JCT",
        "source_date": "2023",
        "notes": "Adopt OECD Pillar Two 15% global minimum tax",
    },
    "🌍 Biden International Package (-$700B)": {
        "official_score": -700.0,
        "source": "Treasury",
        "source_date": "FY2025",
        "notes": "Full package: GILTI reform + FDII repeal + UTPR",
    },
    # IRS Enforcement
    "🔍 IRA Enforcement Funding (-$200B)": {
        "official_score": -200.0,
        "source": "CBO",
        "source_date": "2022",
        "notes": "IRA \\$80B enforcement funding, ~\\$200B net revenue",
    },
    "🔍 Double IRS Enforcement (-$340B)": {
        "official_score": -340.0,
        "source": "Treasury/Sarin-Summers",
        "source_date": "2021",
        "notes": "Double enforcement budget beyond IRA levels",
    },
    # Pharmaceutical
    "💊 Expand Drug Negotiation (-$500B)": {
        "official_score": -500.0,
        "source": "CBO/Estimate",
        "source_date": "2023",
        "notes": "Negotiate 50 drugs, remove exclusivity delays",
    },
    "💊 Universal Insulin Cap (-$15B)": {
        "official_score": -15.0,
        "source": "CBO",
        "source_date": "2022",
        "notes": "\\$35/month insulin cap for Medicare and private insurance",
    },
    "💊 International Reference Pricing (-$100B)": {
        "official_score": -100.0,
        "source": "RAND/Estimate",
        "source_date": "2021",
        "notes": "Cap Medicare drug prices at 120% of international average",
    },
    # Trade / Tariffs
    "🏭 Trump Universal 10% Tariff (-$2T)": {
        "official_score": -2000.0,
        "source": "Tax Foundation / Yale Budget Lab",
        "source_date": "2024",
        "notes": "10% tariff on all imports, ~\\$1,700/household cost",
    },
    "🏭 Trump 60% China Tariff (-$500B)": {
        "official_score": -500.0,
        "source": "Tax Foundation",
        "source_date": "2024",
        "notes": "60% tariff on Chinese imports",
    },
    "🏭 25% Auto Tariff (-$100B)": {
        "official_score": -100.0,
        "source": "CRFB",
        "source_date": "2024",
        "notes": "25% tariff on auto imports",
    },
    "🏭 25% Steel & Aluminum Tariff (-$60B)": {
        "official_score": -60.0,
        "source": "Tax Foundation",
        "source_date": "2024",
        "notes": "25% tariff on steel and aluminum imports",
    },
    "🏭 Reciprocal Tariffs (~20pp) (-$1.2T)": {
        "official_score": -1200.0,
        "source": "Tax Foundation / Yale Budget Lab",
        "source_date": "2024",
        "notes": "Match trading partners\\' tariff rates (~20pp average increase)",
    },
    # Climate / Energy
    "🌱 Repeal IRA Clean Energy Credits ($783B)": {
        "official_score": -783.0,
        "source": "CBO",
        "source_date": "March 2024",
        "notes": "Full repeal of IRA clean energy tax credits",
    },
    "🌱 Carbon Tax \\$50/ton (-$1.7T)": {
        "official_score": -1700.0,
        "source": "CBO-style estimate",
        "source_date": "2024",
        "notes": "\\$50/ton CO2 tax with 5% annual escalator",
    },
    "🌱 Repeal EV Credits ($200B)": {
        "official_score": -200.0,
        "source": "CBO",
        "source_date": "2024",
        "notes": "Repeal \\$7,500 EV tax credit",
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
        "description": "Extend TCJA but repeal the \\$10K SALT cap (adds ~\\$1.9T to cost). Popular bipartisan proposal.",
        "is_tcja": True,
        "tcja_type": "no_salt",
    },
    "🏛️ TCJA Rates Only": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Extend only the individual rate bracket cuts, not other TCJA provisions (~\\$3.2T).",
        "is_tcja": True,
        "tcja_type": "rates_only",
    },
    "🏢 Biden Corporate 28% (CBO: -$1.35T)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Raise corporate rate from 21% to 28%. CBO estimate: raises ~\\$1.35T over 10 years.",
        "is_tcja": False,
        "is_corporate": True,
        "corporate_type": "biden_28",
    },
    "🏢 Trump Corporate 15%": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Lower corporate rate from 21% to 15%. Estimated cost: ~\\$1.9T over 10 years.",
        "is_tcja": False,
        "is_corporate": True,
        "corporate_type": "trump_15",
    },
    "👶 Biden CTC Expansion (CBO: $1.6T)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Expand CTC to \\$3,600/\\$3,000 per child, fully refundable. Based on 2021 ARP expansion.",
        "is_tcja": False,
        "is_corporate": False,
        "is_credit": True,
        "credit_type": "biden_ctc_2021",
    },
    "👶 CTC Extension (CBO: $600B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Extend current \\$2,000 CTC beyond 2025 sunset. Without extension, reverts to \\$1,000.",
        "is_tcja": False,
        "is_corporate": False,
        "is_credit": True,
        "credit_type": "ctc_extension",
    },
    "💼 EITC Childless Expansion (CBO: $178B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Triple EITC for childless workers (~\\$1,500 max), expand age range to 19-65+.",
        "is_tcja": False,
        "is_corporate": False,
        "is_credit": True,
        "credit_type": "biden_eitc_childless",
    },
    "🏠 Estate Tax: Extend TCJA (CBO: $167B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Keep ~\\$14M exemption (vs \\$6.4M if TCJA expires). Costs ~\\$167B over 10 years.",
        "is_tcja": False,
        "is_corporate": False,
        "is_credit": False,
        "is_estate": True,
        "estate_type": "extend_tcja",
    },
    "🏠 Biden Estate Reform (-$450B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Lower exemption to \\$3.5M, raise rate to 45%. Raises ~\\$450B over 10 years.",
        "is_tcja": False,
        "is_corporate": False,
        "is_credit": False,
        "is_estate": True,
        "estate_type": "biden_reform",
    },
    "🏠 Eliminate Estate Tax ($350B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Repeal federal estate tax entirely. Costs ~\\$350B over 10 years.",
        "is_tcja": False,
        "is_corporate": False,
        "is_credit": False,
        "is_estate": True,
        "estate_type": "eliminate",
    },
    "💰 SS Cap to 90% (CBO: -$800B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Raise Social Security cap to cover 90% of wages (~\\$305K). Raises ~\\$800B.",
        "is_tcja": False,
        "is_corporate": False,
        "is_payroll": True,
        "payroll_type": "cap_90",
    },
    "💰 SS Donut Hole $250K (-$2.7T)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Apply SS tax to wages above \\$250K (donut hole). Raises ~\\$2.7T over 10 years.",
        "is_tcja": False,
        "is_corporate": False,
        "is_payroll": True,
        "payroll_type": "donut_250k",
    },
    "💰 Eliminate SS Cap (-$3.2T)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Eliminate Social Security wage cap entirely. Raises ~\\$3.2T over 10 years.",
        "is_tcja": False,
        "is_corporate": False,
        "is_payroll": True,
        "payroll_type": "eliminate_cap",
    },
    "💰 Expand NIIT (JCT: -$250B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Apply 3.8% NIIT to S-corp/partnership income. Raises ~\\$250B over 10 years.",
        "is_tcja": False,
        "is_corporate": False,
        "is_payroll": True,
        "payroll_type": "expand_niit",
    },
    "⚖️ AMT: Extend TCJA Relief ($450B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Extend TCJA's higher AMT exemptions (\\$88K single, \\$137K MFJ) past 2025. Costs ~\\$450B.",
        "is_tcja": False,
        "is_corporate": False,
        "is_amt": True,
        "amt_type": "extend_tcja",
    },
    "⚖️ Repeal Individual AMT ($450B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Fully repeal individual AMT. After TCJA expires, would cost ~\\$450B over 10 years.",
        "is_tcja": False,
        "is_corporate": False,
        "is_amt": True,
        "amt_type": "repeal_individual",
    },
    "⚖️ Repeal Corporate AMT (-$220B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Repeal 15% book minimum tax (CAMT) from IRA 2022. Costs ~\\$220B over 10 years.",
        "is_tcja": False,
        "is_corporate": False,
        "is_amt": True,
        "amt_type": "repeal_corporate",
    },
    "🏥 Extend ACA Enhanced PTCs ($350B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Extend enhanced premium tax credits (ARPA/IRA) past 2025. Costs ~\\$350B over 10 years.",
        "is_tcja": False,
        "is_corporate": False,
        "is_ptc": True,
        "ptc_type": "extend_enhanced",
    },
    "🏥 Repeal ACA Premium Credits (-$1.1T)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Repeal all ACA premium subsidies. Saves ~\\$1.1T but ~19M lose subsidized coverage.",
        "is_tcja": False,
        "is_corporate": False,
        "is_ptc": True,
        "ptc_type": "repeal",
    },
    "📋 Cap Employer Health Exclusion (-$450B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Cap tax exclusion for employer health insurance at \\$50K. Raises ~\\$450B over 10 years.",
        "is_tcja": False,
        "is_corporate": False,
        "is_expenditure": True,
        "expenditure_type": "cap_employer_health",
    },
    "📋 Repeal SALT Cap ($1.1T)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Remove \\$10K cap on state and local tax deduction. Costs ~\\$1.1T over 10 years.",
        "is_tcja": False,
        "is_corporate": False,
        "is_expenditure": True,
        "expenditure_type": "repeal_salt_cap",
    },
    "📋 Eliminate Step-Up Basis (-$500B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Tax capital gains at death with \\$1M exemption. Raises ~\\$500B over 10 years.",
        "is_tcja": False,
        "is_corporate": False,
        "is_expenditure": True,
        "expenditure_type": "eliminate_step_up",
    },
    "📋 Cap Charitable Deduction (-$200B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Limit charitable deduction value to 28% rate. Raises ~\\$200B over 10 years.",
        "is_tcja": False,
        "is_corporate": False,
        "is_expenditure": True,
        "expenditure_type": "cap_charitable",
    },
    "Biden 2025 Proposal": {
        "rate_change": 2.6,
        "threshold": 400000,
        "description": (
            "+2.6pp on income above \\$400K, restoring the pre-TCJA 39.6% top rate. "
            "Treasury FY2025 Green Book estimate: raises ~\\$252B over 10 years."
        ),
        "is_tcja": False,
        "is_corporate": False,
        "ui_category": "TCJA / Individual",
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
        "description": "2pp cut for households earning \\$50K+",
        "is_tcja": False,
    },
    "Flat Tax Reform": {
        "rate_change": -5.0,
        "threshold": 0,
        "description": "Lower all rates by 5pp (illustrative)",
        "is_tcja": False,
    },
    "Warren Ultra-Millionaire Surtax": {
        "rate_change": 3.0,
        "threshold": 2_000_000,
        "description": (
            "3pp surtax on taxable income above \\$2M, Warren-style. Raises "
            "roughly \\$300-400B over 10 years depending on behavioral response."
        ),
        "is_tcja": False,
        "ui_category": "Income Tax",
    },
    "Top Rate to 45%": {
        "rate_change": 8.0,
        "threshold": 609_350,
        "description": (
            "Raise the top marginal rate from 37% to 45% on income above "
            "the current 37% bracket floor (\\$609,350 single, 2025). "
            "Illustrative of the upper end of progressive proposals."
        ),
        "is_tcja": False,
        "ui_category": "Income Tax",
    },
    "High-Earner Medicare Surcharge 2pp": {
        "rate_change": 2.0,
        "threshold": 400_000,
        "description": (
            "+2pp Medicare surcharge on wage + investment income above \\$400K. "
            "Extends the NIIT's 3.8% surtax logic to a broader base. Similar in "
            "structure to the Biden 2025 Medicare surtax proposal."
        ),
        "is_tcja": False,
        "ui_category": "Income Tax",
    },
    # International Tax Presets
    "🌍 Biden GILTI Reform (-$280B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Country-by-country GILTI at 21%, eliminate QBAI exemption. Raises ~\\$280B over 10 years.",
        "is_tcja": False,
        "is_international": True,
        "international_type": "biden_gilti",
    },
    "🌍 Repeal FDII (-$200B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Repeal Foreign-Derived Intangible Income deduction. Raises ~\\$200B over 10 years.",
        "is_tcja": False,
        "is_international": True,
        "international_type": "fdii_repeal",
    },
    "🌍 Pillar Two Adoption (-$80B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Adopt OECD Pillar Two 15% global minimum tax. JCT estimate: raises ~\\$80B.",
        "is_tcja": False,
        "is_international": True,
        "international_type": "pillar_two",
    },
    "🌍 Biden International Package (-$700B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Full Biden international reform: GILTI at 21% per-country + FDII repeal + UTPR. Raises ~\\$700B.",
        "is_tcja": False,
        "is_international": True,
        "international_type": "biden_full",
    },
    # IRS Enforcement Presets
    "🔍 IRA Enforcement Funding (-$200B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "IRA \\$80B IRS enforcement over 10 years. CBO: raises ~\\$200B net after costs.",
        "is_tcja": False,
        "is_enforcement": True,
        "enforcement_type": "ira",
    },
    "🔍 Double IRS Enforcement (-$340B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Double IRS enforcement beyond IRA levels (~\\$16B/year). Raises ~\\$340B with diminishing returns.",
        "is_tcja": False,
        "is_enforcement": True,
        "enforcement_type": "double",
    },
    "🔍 High-Income Enforcement (-$250B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Targeted enforcement for >\\$400K returns and large partnerships. \\$5B/year, high ROI.",
        "is_tcja": False,
        "is_enforcement": True,
        "enforcement_type": "high_income",
    },
    # Pharmaceutical Presets
    "💊 Expand Drug Negotiation (-$500B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Negotiate 50 Medicare drugs (vs IRA's 20), remove exclusivity delays. Saves ~\\$500B.",
        "is_tcja": False,
        "is_pharma": True,
        "pharma_type": "expand_negotiation",
    },
    "💊 Universal Insulin Cap (-$15B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "\\$35/month insulin cap for Medicare and private insurance. Saves ~\\$15B over 10 years.",
        "is_tcja": False,
        "is_pharma": True,
        "pharma_type": "insulin_cap",
    },
    "💊 International Reference Pricing (-$100B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Cap Medicare drug prices at 120% of OECD international average. Saves ~\\$100B.",
        "is_tcja": False,
        "is_pharma": True,
        "pharma_type": "reference_pricing",
    },
    "💊 Comprehensive Drug Reform (-$600B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Expanded negotiation + insulin cap + manufacturer discounts. Saves ~\\$600B over 10 years.",
        "is_tcja": False,
        "is_pharma": True,
        "pharma_type": "comprehensive",
    },
    # Trade / Tariff Presets
    "🏭 Trump Universal 10% Tariff (-$2T)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "10% tariff on all imports. Raises ~\\$2T but costs ~\\$1,700/household in higher prices.",
        "is_tcja": False,
        "is_trade": True,
        "trade_type": "universal_10",
    },
    "🏭 Trump 60% China Tariff (-$500B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "60% tariff on all Chinese imports (~\\$430B base). Raises ~\\$500B over 10 years.",
        "is_tcja": False,
        "is_trade": True,
        "trade_type": "china_60",
    },
    "🏭 25% Auto Tariff (-$100B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "25% tariff on imported vehicles and parts (~\\$380B base). Raises ~\\$100B.",
        "is_tcja": False,
        "is_trade": True,
        "trade_type": "auto_25",
    },
    "🏭 25% Steel/Aluminum Tariff (-$15B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "25% tariff on steel and aluminum imports (~\\$50B base).",
        "is_tcja": False,
        "is_trade": True,
        "trade_type": "steel_25",
    },
    "🏭 Reciprocal Tariffs (-$1.2T)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Match trading partners' tariff rates (~20pp average increase). Raises ~\\$1.2T.",
        "is_tcja": False,
        "is_trade": True,
        "trade_type": "reciprocal",
    },
    # Climate / Energy Presets
    "🌱 Repeal IRA Clean Energy Credits ($783B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Full repeal of IRA clean energy tax credits. Saves ~\\$783B over 10 years (CBO March 2024).",
        "is_tcja": False,
        "is_climate": True,
        "climate_type": "repeal_ira",
    },
    "🌱 Carbon Tax \\$50/ton (-$1.7T)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "\\$50/ton CO2 tax with 5% annual escalator. Raises ~\\$1.7T over 10 years.",
        "is_tcja": False,
        "is_climate": True,
        "climate_type": "carbon_50",
    },
    "🌱 Carbon Tax \\$25/ton (-$1.0T)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "\\$25/ton CO2 starter tax with 5% annual escalator. Raises ~\\$1.0T over 10 years.",
        "is_tcja": False,
        "is_climate": True,
        "climate_type": "carbon_25",
    },
    "🌱 Repeal EV Credits ($200B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Repeal \\$7,500 EV tax credit. Saves ~\\$200B over 10 years.",
        "is_tcja": False,
        "is_climate": True,
        "climate_type": "repeal_ev",
    },
    "🌱 Extend IRA Credits Beyond 2032 ($400B)": {
        "rate_change": 0.0,
        "threshold": 0,
        "description": "Extend IRA clean energy credits 5 years beyond 2032 sunset. Costs ~\\$400B additional.",
        "is_tcja": False,
        "is_climate": True,
        "climate_type": "extend_ira",
    },
}
