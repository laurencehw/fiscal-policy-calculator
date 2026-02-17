"""
Preset package definitions for the Policy Package Builder tab.
"""

PRESET_POLICY_PACKAGES = {
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
