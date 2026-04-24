"""
Spending policy sidebar inputs and execution helpers.
"""

from __future__ import annotations

from typing import Any

SPENDING_PRESETS: dict[str, dict[str, Any]] = {
    "Custom program": {
        "annual_spending": 100.0,
        "category": "Infrastructure",
        "multiplier": 1.0,
        "growth_rate": 0.02,
        "duration": 10,
        "is_one_time": False,
        "description": "Define your own spending program with custom parameters.",
    },
    "Infrastructure Investment ($100B/yr)": {
        "annual_spending": 100.0,
        "category": "Infrastructure",
        "multiplier": 1.5,
        "growth_rate": 0.03,
        "duration": 10,
        "is_one_time": False,
        "description": (
            "Roads, bridges, broadband, water systems. High multiplier (~1.5) due to direct "
            "job creation and long-run productivity gains (CBO 2015)."
        ),
    },
    "Defense Spending Increase (+10%)": {
        "annual_spending": 90.0,
        "category": "Defense",
        "multiplier": 1.0,
        "growth_rate": 0.02,
        "duration": 10,
        "is_one_time": False,
        "description": (
            "~10% increase in base defense budget (~$900B FY2026). Moderate multiplier (~1.0) — "
            "less labor-intensive than civilian infrastructure."
        ),
    },
    "Universal Pre-K ($40B/yr)": {
        "annual_spending": 40.0,
        "category": "Education",
        "multiplier": 1.3,
        "growth_rate": 0.03,
        "duration": 10,
        "is_one_time": False,
        "description": (
            "Federal funding for universal preschool access. Moderate-to-high multiplier due to "
            "labor intensity and increased parental workforce participation."
        ),
    },
    "R&D Investment ($50B/yr)": {
        "annual_spending": 50.0,
        "category": "Research & Development",
        "multiplier": 1.2,
        "growth_rate": 0.04,
        "duration": 10,
        "is_one_time": False,
        "description": (
            "Federal R&D across NIH, NSF, DARPA, DOE. Moderate short-run multiplier but strong "
            "long-run productivity effects. Growth rate reflects expansion of research capacity."
        ),
    },
    "Discretionary Spending Cut (−$50B/yr)": {
        "annual_spending": -50.0,
        "category": "Non-Defense Discretionary",
        "multiplier": 0.9,
        "growth_rate": 0.02,
        "duration": 10,
        "is_one_time": False,
        "description": (
            "Across-the-board discretionary spending reduction. Multiplier of ~0.9 implies modest GDP drag per dollar saved."
        ),
    },
    "Disaster Relief ($30B one-time)": {
        "annual_spending": 30.0,
        "category": "Non-Defense Discretionary",
        "multiplier": 1.7,
        "growth_rate": 0.0,
        "duration": 1,
        "is_one_time": True,
        "description": (
            "One-time emergency appropriation. Very high multiplier (~1.7) because spending is rapid, "
            "targeted, and enters the economy during a period of slack."
        ),
    },
    "Student Debt Forgiveness ($400B one-time)": {
        "annual_spending": 400.0,
        "category": "Non-Defense Discretionary",
        "multiplier": 0.5,
        "growth_rate": 0.0,
        "duration": 1,
        "is_one_time": True,
        "description": (
            "One-time \\$10k-per-borrower federal loan cancellation affecting ~40M borrowers. "
            "Low multiplier (~0.5) because the spending flows to future-year consumption smoothing "
            "rather than immediate output (CBO Aug 2022 methodology)."
        ),
    },
    "Universal Childcare ($100B/yr)": {
        "annual_spending": 100.0,
        "category": "Non-Defense Discretionary",
        "multiplier": 1.3,
        "growth_rate": 0.03,
        "duration": 10,
        "is_one_time": False,
        "description": (
            "Federal subsidy capping childcare at 7% of family income for households <\\$300k. "
            "Moderate-to-high multiplier (~1.3) via labor-force participation of primary caregivers. "
            "Build Back Better-style (\\$381B/10yr in 2021 estimate, inflation-adjusted to ~\\$100B/yr)."
        ),
    },
    "Medicare Buy-in Age 55+ ($50B/yr)": {
        "annual_spending": 50.0,
        "category": "Medicare",
        "multiplier": 0.9,
        "growth_rate": 0.03,
        "duration": 10,
        "is_one_time": False,
        "description": (
            "Optional Medicare enrollment from age 55. Modest net federal cost (~\\$50B/yr) after "
            "premium offsets and reduced ACA marketplace subsidies. CBO 2019 scored at \\$487B/10yr."
        ),
    },
    "High-Speed Rail Program ($30B/yr)": {
        "annual_spending": 30.0,
        "category": "Infrastructure",
        "multiplier": 1.4,
        "growth_rate": 0.02,
        "duration": 10,
        "is_one_time": False,
        "description": (
            "Federal matching grants for regional high-speed rail corridors (e.g. Northeast, "
            "California, Texas Central). Infrastructure-grade multiplier (~1.4) and long-horizon "
            "productivity effects."
        ),
    },
}

_CATEGORY_TO_MODEL = {
    "Infrastructure": "nondefense",
    "Defense": "defense",
    "Non-Defense Discretionary": "nondefense",
    "Mandatory Programs": "mandatory",
    "Social Security": "mandatory",
    "Medicare": "mandatory",
    "Medicaid": "mandatory",
    "Education": "nondefense",
    "Research & Development": "nondefense",
}


def render_spending_policy_inputs(
    st_module: Any,
    default_preset: str | None = None,
) -> dict[str, Any]:
    """Render spending policy input controls and return selected values."""
    st_module.markdown("#### Spending program")

    preset_names = list(SPENDING_PRESETS.keys())
    spending_key = "sidebar_spending_preset"
    if (
        spending_key in st_module.session_state
        and st_module.session_state[spending_key] not in preset_names
    ):
        del st_module.session_state[spending_key]

    selected_preset = st_module.selectbox(
        "Select a program",
        options=preset_names,
        index=preset_names.index(default_preset) if default_preset in preset_names else 0,
        key=spending_key,
        help="Choose a pre-configured spending scenario or define a custom program.",
    )
    preset = SPENDING_PRESETS[selected_preset]

    if selected_preset != "Custom program":
        st_module.caption(preset["description"])

    is_custom = selected_preset == "Custom program"

    program_name = (
        st_module.text_input(
            "Program name",
            "Infrastructure Investment",
            help="A short label for this spending program.",
        )
        if is_custom
        else selected_preset.split("(")[0].strip()
    )

    annual_spending = st_module.number_input(
        "Annual spending change ($B)",
        min_value=-500.0,
        max_value=500.0,
        value=float(preset["annual_spending"]),
        step=10.0,
        help="**Positive** = spending increase, **Negative** = spending cut.",
    )

    all_categories = [
        "Infrastructure",
        "Defense",
        "Non-Defense Discretionary",
        "Mandatory Programs",
        "Social Security",
        "Medicare",
        "Medicaid",
        "Education",
        "Research & Development",
    ]
    default_cat_index = (
        all_categories.index(preset["category"]) if preset["category"] in all_categories else 0
    )

    spending_category = st_module.selectbox(
        "Category",
        all_categories,
        index=default_cat_index,
        help="Affects fiscal multiplier defaults and baseline projections.",
    )

    with st_module.expander("Economic parameters", expanded=False):
        st_module.caption(
            "Pre-populated from the selected program. Override if you have specific values "
            "from CBO or the economics literature."
        )
        duration = st_module.slider(
            "Duration (years)",
            min_value=1,
            max_value=10,
            value=int(preset["duration"]),
            help="Standard CBO budget window is 10 years.",
        )

        growth_rate = st_module.slider(
            "Annual real growth rate (%)",
            min_value=-5.0,
            max_value=10.0,
            value=float(preset["growth_rate"]) * 100,
            step=0.5,
            help="How fast spending grows each year after the first.",
        ) / 100

        multiplier = st_module.slider(
            "Fiscal multiplier",
            min_value=0.0,
            max_value=2.0,
            value=float(preset["multiplier"]),
            step=0.1,
            help=(
                "GDP impact per dollar spent. Typical values: infrastructure ~1.5, defense ~1.0, "
                "transfers ~0.8. ([CBO 2015 estimates](https://www.cbo.gov/publication/49958))"
            ),
        )

        is_one_time = st_module.checkbox(
            "One-time expenditure",
            value=bool(preset["is_one_time"]),
            help="Check for one-time spending (e.g., disaster relief) rather than recurring.",
        )

    return {
        "selected_preset": selected_preset,
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
    """Build and score a spending policy from UI inputs."""
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
        category=_CATEGORY_TO_MODEL.get(spending_inputs["spending_category"], "nondefense"),
        duration_years=spending_inputs["duration"],
    )

    scorer = fiscal_policy_scorer_cls(baseline=None, use_real_data=use_real_data)
    result = scorer.score_policy(policy, dynamic=dynamic_scoring)

    return {
        "policy": policy,
        "result": result,
        "scorer": scorer,
        "is_spending": True,
        "policy_name": spending_inputs.get("selected_preset", spending_inputs["program_name"]),
        "selected_spending_preset": spending_inputs.get("selected_preset"),
    }
