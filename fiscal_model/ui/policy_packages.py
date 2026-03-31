"""
Preset package definitions for the Policy Package Builder tab.
"""

PRESET_POLICY_PACKAGES = {
    # === Deficit Reduction Packages ===
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
    "Biden Full International Package": {
        "description": "GILTI reform + FDII repeal + IRS enforcement",
        "policies": [
            "🌍 Biden International Package (-$700B)",
            "🔍 IRA Enforcement Funding (-$200B)",
        ],
        "official_total": -900,
        "source": "Treasury FY2025",
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

    # === TCJA Packages ===
    "TCJA Full Extension Package": {
        "description": "Extend all expiring TCJA provisions",
        "policies": [
            "🏛️ TCJA Full Extension (CBO: $4.6T)",
        ],
        "official_total": 4600,
        "source": "CBO May 2024",
    },
    "TCJA + No SALT Cap": {
        "description": "Extend TCJA and repeal the \\$10K SALT deduction cap",
        "policies": [
            "🏛️ TCJA Extension (No SALT Cap)",
        ],
        "official_total": 6500,
        "source": "CBO/JCT estimates",
    },

    # === Social Security Reform Packages ===
    "SS Solvency: Raise the Cap": {
        "description": (
            "Address the Social Security shortfall by raising the taxable earnings cap. "
            "The SS trust fund is projected to be depleted by ~2033. These reforms extend solvency."
        ),
        "policies": [
            "💰 SS Donut Hole $250K (-$2.7T)",
            "💰 Expand NIIT (JCT: -$250B)",
        ],
        "official_total": -2950,
        "source": "CBO/JCT estimates",
    },
    "SS Solvency: Eliminate the Cap": {
        "description": (
            "Eliminate the Social Security wage cap entirely — all earnings subject to SS tax. "
            "Closes most of the 75-year shortfall."
        ),
        "policies": [
            "💰 Eliminate SS Cap (-$3.2T)",
        ],
        "official_total": -3200,
        "source": "CBO estimate",
    },
    "SS Solvency: Moderate Reform": {
        "description": (
            "Raise the cap to cover 90% of wages (the original intent of the 1983 reforms). "
            "Closes about 1/3 of the 75-year shortfall."
        ),
        "policies": [
            "💰 SS Cap to 90% (CBO: -$800B)",
        ],
        "official_total": -800,
        "source": "CBO estimate",
    },

    # === Trade Packages ===
    "Trump Trade Agenda": {
        "description": (
            "Universal 10% tariff + 60% China tariff. Raises significant revenue "
            "but increases consumer prices substantially."
        ),
        "policies": [
            "🏭 Trump Universal 10% Tariff (-$2T)",
            "🏭 Trump 60% China Tariff (-$500B)",
        ],
        "official_total": -2500,
        "source": "Tax Foundation / Yale Budget Lab",
    },

    # === Climate Packages ===
    "Carbon Tax + IRA Repeal": {
        "description": (
            "Replace IRA subsidies with a carbon tax. Revenue-positive and "
            "more economically efficient according to most economists."
        ),
        "policies": [
            "🌱 Carbon Tax \\$50/ton (-$1.7T)",
            "🌱 Repeal IRA Clean Energy Credits ($783B)",
        ],
        "official_total": -917,
        "source": "CBO-style estimate",
    },

    # === Comprehensive Healthcare ===
    "Drug Pricing + Enforcement": {
        "description": "Expand Medicare negotiation and boost IRS enforcement",
        "policies": [
            "💊 Expand Drug Negotiation (-$500B)",
            "🔍 IRA Enforcement Funding (-$200B)",
        ],
        "official_total": -700,
        "source": "CBO estimates",
    },
}
