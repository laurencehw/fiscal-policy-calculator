"""
Centralized constants for the Fiscal Policy Calculator.

All magic numbers, growth rates, elasticities, and calibration factors
are collected here with source citations. This makes assumptions transparent
and easy to update.
"""

# =============================================================================
# Budget Window
# =============================================================================
BUDGET_WINDOW_YEARS = 10  # Standard CBO 10-year budget window

# =============================================================================
# Elasticities (Behavioral Response Parameters)
# =============================================================================
# Elasticity of Taxable Income — Saez, Slemrod & Giertz (2012)
DEFAULT_ETI = 0.25

# Capital gains realization elasticities — CBO (2012), Dowd et al. (2015)
CG_SHORT_RUN_ELASTICITY = 0.8   # Years 1-3: timing/anticipation effects
CG_LONG_RUN_ELASTICITY = 0.4    # Years 4+: permanent behavioral response
CG_TRANSITION_YEARS = 3

# Labor supply elasticity — CBO (2012), Chetty et al. (2011)
DEFAULT_LABOR_SUPPLY_ELASTICITY = 0.1   # Compensated, extensive margin
DEFAULT_CAPITAL_ELASTICITY = 0.25       # Response of capital to after-tax return

# Corporate elasticity — Gruber & Rauh (2007)
DEFAULT_CORPORATE_ELASTICITY = 0.25

# Step-up basis lock-in multiplier — calibrated to PWBM revenue estimates
STEP_UP_LOCK_IN_MULTIPLIER = 2.0

# =============================================================================
# Growth Rates (Annual, Nominal)
# =============================================================================
# Used in scoring.py for year-over-year revenue growth by policy type
GROWTH_RATES = {
    "corporate_profits": 0.04,       # Corporate profit growth (~GDP + 1pp)
    "credits_inflation": 0.03,       # Credit costs grow with CPI + population
    "estate_wealth": 0.03,           # Wealth accumulation growth
    "payroll_wages": 0.04,           # Wage growth (~GDP growth)
    "amt_income": 0.03,              # Income growth for AMT-affected taxpayers
    "healthcare_costs": 0.04,        # Healthcare cost growth (CMS NHE projections)
    "default": 0.03,                 # Default growth for unspecified policy types
}

# Baseline projection growth rates (CBOBaseline)
BASELINE_GROWTH = {
    "bracket_creep_premium": 0.003,  # Extra income tax growth from real bracket creep
    "corporate_profit_premium": 0.01, # Corporate profits grow faster than GDP
    "social_security": 0.05,         # ~5% annual growth (demographics) — CBO 2024
    "medicare": 0.06,                # ~6% annual growth (demographics + costs) — CBO 2024
    "medicaid": 0.05,                # ~5% annual growth — CBO 2024
    "other_mandatory": 0.03,         # ~3% annual growth — CBO 2024
    "defense": 0.02,                 # ~2% discretionary caps — CBO 2024
    "nondefense": 0.01,              # ~1% discretionary caps — CBO 2024
    "other_revenue": 0.02,           # Excise, customs slower growth
}

# =============================================================================
# Fiscal Multipliers — Auerbach & Gorodnichenko (2012), Christiano et al. (2011)
# =============================================================================
SPENDING_MULTIPLIER_BASE = 1.0       # Normal times
TAX_MULTIPLIER_BASE = 0.5            # Tax cut multiplier (lower than spending)
TRANSFER_MULTIPLIER_BASE = 0.8       # Transfer multiplier
SPENDING_MULTIPLIER_DECAY = 0.7      # Annual decay rate for multiplier effects

# Dynamic scoring revenue feedback rate
MARGINAL_REVENUE_RATE = 0.25         # Combined federal revenue/GDP ratio — CBO

# Crowding out
CROWDING_OUT_BASE = 0.03             # Interest rate increase per $100B deficit

# =============================================================================
# Production Function — Standard Cobb-Douglas
# =============================================================================
LABOR_SHARE = 0.65                   # Labor's share of output — BLS
CAPITAL_SHARE = 0.35                 # Capital's share of output
TFP_GROWTH = 0.01                    # Annual total factor productivity growth

# =============================================================================
# Employment Conversion — Okun's Law
# =============================================================================
# 1% GDP change ≈ 1.5M jobs (150K thousands) — Ball, Leigh & Loungani (2017)
JOBS_PER_GDP_PERCENT = 150_000       # In thousands-of-jobs per percent GDP

# =============================================================================
# Baseline Budget Values (FY2024, billions) — CBO February 2024 Outlook
# =============================================================================
FALLBACK_BASELINE = {
    "gdp": 28_500,
    "individual_income_tax": 2_500,
    "corporate_tax": 450,
    "payroll_tax": 1_700,
    "other_revenue": 400,
    "social_security": 1_500,
    "medicare": 900,
    "medicaid": 600,
    "other_mandatory": 900,
    "defense": 900,
    "nondefense": 750,
    "debt": 28_000,
}

# GDP ratios for data-driven baseline (when IRS/FRED data available)
GDP_RATIOS = {
    "corporate_tax_to_income_tax": 0.18,  # Historical ~18%
    "payroll_tax_to_gdp": 0.06,           # Historical ~6%
    "other_revenue_to_gdp": 0.014,        # Estate, excise, customs ~1.4%
    "social_security_to_gdp": 0.053,      # ~5.3% — CBO 2024
    "medicare_to_gdp": 0.032,             # ~3.2% — CBO 2024
    "medicaid_to_gdp": 0.021,             # ~2.1% — CBO 2024
    "other_mandatory_to_gdp": 0.032,      # ~3.2% — CBO 2024
    "defense_to_gdp": 0.032,              # ~3.2% — CBO 2024
    "nondefense_to_gdp": 0.026,           # ~2.6% — CBO 2024
    "debt_to_gdp": 0.98,                  # ~98% — CBO 2024
    "income_tax_to_gdp": 0.088,           # ~8.8% — historical average
}

# =============================================================================
# Uncertainty Parameters — CBO Uncertainty Analysis
# =============================================================================
BASE_UNCERTAINTY = 0.10              # Base uncertainty for year 1
UNCERTAINTY_GROWTH_PER_YEAR = 0.02   # Additional uncertainty per year out
TAX_UNCERTAINTY_FACTOR = 1.2         # Tax revenue more uncertain than spending
SPENDING_UNCERTAINTY_FACTOR = 0.8    # Spending more predictable
DYNAMIC_UNCERTAINTY_FACTOR = 1.5     # Dynamic scoring adds uncertainty
ASYMMETRY_LOW = 0.9                  # Low estimate factor (costs tend higher)
ASYMMETRY_HIGH = 1.1                 # High estimate factor

# =============================================================================
# Corporate Tax Parameters — CBO/JCT
# =============================================================================
CURRENT_CORPORATE_RATE_PCT = 0.21    # TCJA corporate rate (21%)

# =============================================================================
# Interest Rate Parameters
# =============================================================================
EFFECTIVE_RATE_MULTIPLIER = 0.75     # Effective rate < 10yr due to maturity mix

# =============================================================================
# Income Tax Affected Share Heuristics
# (Used as fallback when IRS SOI data unavailable)
# =============================================================================
AFFECTED_SHARE_BY_THRESHOLD = [
    (500_000, 0.20),   # Income above $500K is ~20% of income tax base
    (200_000, 0.40),   # Above $200K is ~40%
    (100_000, 0.55),   # Above $100K is ~55%
    (50_000, 0.75),    # Above $50K is ~75%
    (0, 0.90),         # All income
]
AVG_EFFECTIVE_INCOME_TAX_RATE = 0.18  # Average effective rate — IRS SOI
