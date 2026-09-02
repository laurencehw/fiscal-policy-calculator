"""
Spending policy sidebar inputs and execution helpers.
"""

from __future__ import annotations

from typing import Any

from ..spending_outlays import ACCOUNT_CLASS_LABELS, IMMEDIATE
from .session_state import (
    KEY_TAILOR_SPEND_ANNUAL,
    KEY_TAILOR_SPEND_CATEGORY,
    KEY_TAILOR_SPEND_DURATION,
    KEY_TAILOR_SPEND_GROWTH_RATE,
    KEY_TAILOR_SPEND_MULTIPLIER,
    KEY_TAILOR_SPEND_ONE_TIME,
    KEY_TAILOR_SPEND_OUTLAY_CLASS,
    KEY_TAILOR_SPEND_OUTLAY_SEEDED_FROM,
    KEY_TAILOR_SPEND_PRESET_APPLIED,
    KEY_TAILOR_SPEND_PROGRAM_NAME,
    forget_widget_value,
    mirror_widget_value,
    restore_widget_value,
    seed_widget_default,
)

# The program picker keeps its historic ``sidebar_*`` key (share links and
# tests/test_share_links.py depend on the literal); everything below it is
# newly keyed with the ``tailor_spend_*`` namespace.
_SPENDING_PRESET_KEY = "sidebar_spending_preset"

SPENDING_PRESETS: dict[str, dict[str, Any]] = {
    "Custom program": {
        # A blank slate seeded as infrastructure, so it carries the class its
        # own category implies. Changing the category below re-derives it, and
        # Advanced parameters can override it outright.
        "outlay_account_class": "construction_and_capital",
        "annual_spending": 100.0,
        "category": "Infrastructure",
        "multiplier": 1.0,
        "growth_rate": 0.02,
        "duration": 10,
        "is_one_time": False,
        "description": "Define your own spending program with custom parameters.",
    },
    "Infrastructure Investment ($100B/yr)": {
        # Roads, bridges, broadband, water systems - capital construction, the
        # slowest-disbursing class in the federal budget.
        "outlay_account_class": "construction_and_capital",
        "annual_spending": 100.0,
        "category": "Infrastructure",
        "multiplier": 1.5,
        "growth_rate": 0.03,
        "duration": 10,
        "is_one_time": False,
        "description": (
            "Roads, bridges, broadband, water systems. High multiplier (\\~1.5) due to direct "
            "job creation and long-run productivity gains (CBO 2015)."
        ),
    },
    "Defense Spending Increase (+10%)": {
        # A rise in the base defence budget is predominantly force structure and
        # operation and maintenance - agency operations, not capital.
        "outlay_account_class": "operations_and_support",
        "annual_spending": 90.0,
        "category": "Defense",
        "multiplier": 1.0,
        "growth_rate": 0.02,
        "duration": 10,
        "is_one_time": False,
        "description": (
            "\\~10% increase in base defense budget (\\~$900B FY2026). Moderate multiplier (\\~1.0) — "
            "less labor-intensive than civilian infrastructure."
        ),
    },
    "Universal Pre-K ($40B/yr)": {
        # Formula and project grants to states and districts, disbursed as they
        # draw down their awards.
        "outlay_account_class": "grants_and_procurement",
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
        # Research awards and contracts at NIH, NSF, DARPA and DOE - assistance
        # awards and procurement.
        "outlay_account_class": "grants_and_procurement",
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
        # An across-the-board cut falls on the whole discretionary budget, which
        # is the account type the FRA caps carry in the validation battery.
        "outlay_account_class": "operations_and_support",
        "annual_spending": -50.0,
        "category": "Non-Defense Discretionary",
        "multiplier": 0.9,
        "growth_rate": 0.02,
        "duration": 10,
        "is_one_time": False,
        "description": (
            "Across-the-board discretionary spending reduction. Multiplier of \\~0.9 implies modest GDP drag per dollar saved."
        ),
    },
    "Disaster Relief ($30B one-time)": {
        # Public-assistance and individual-assistance awards. The "rapid" in the
        # description is about the multiplier, not the account: relief awards are
        # drawn down over several years even when obligated at once.
        "outlay_account_class": "grants_and_procurement",
        "annual_spending": 30.0,
        "category": "Non-Defense Discretionary",
        "multiplier": 1.7,
        "growth_rate": 0.0,
        "duration": 1,
        "is_one_time": True,
        "description": (
            "One-time emergency appropriation. Very high multiplier (\\~1.7) because spending is rapid, "
            "targeted, and enters the economy during a period of slack."
        ),
    },
    "Student Debt Forgiveness ($400B one-time)": {
        # A credit-subsidy write-down is recorded when the modification happens
        # rather than spent out - the one class here that is nearly the identity,
        # and classified that way because that is what the account does.
        "outlay_account_class": "mandatory_benefit",
        "annual_spending": 400.0,
        "category": "Non-Defense Discretionary",
        "multiplier": 0.5,
        "growth_rate": 0.0,
        "duration": 1,
        "is_one_time": True,
        "description": (
            "One-time \\$10k-per-borrower federal loan cancellation affecting \\~40M borrowers. "
            "Low multiplier (\\~0.5) because the spending flows to future-year consumption smoothing "
            "rather than immediate output (CBO Aug 2022 methodology)."
        ),
    },
    "Universal Childcare ($100B/yr)": {
        # Subsidy payments routed through state agencies - assistance awards
        # rather than federal operations.
        "outlay_account_class": "grants_and_procurement",
        "annual_spending": 100.0,
        "category": "Non-Defense Discretionary",
        "multiplier": 1.3,
        "growth_rate": 0.03,
        "duration": 10,
        "is_one_time": False,
        "description": (
            "Federal subsidy capping childcare at 7% of family income for households <\\$300k. "
            "Moderate-to-high multiplier (\\~1.3) via labor-force participation of primary caregivers. "
            "Build Back Better-style (\\$381B/10yr in 2021 estimate, inflation-adjusted to \\~\\$100B/yr)."
        ),
    },
    "Medicare Buy-in Age 55+ ($50B/yr)": {
        # Benefit payments made in the year they are owed; no authority-to-outlay
        # lag.
        "outlay_account_class": "mandatory_benefit",
        "annual_spending": 50.0,
        "category": "Medicare",
        "multiplier": 0.9,
        "growth_rate": 0.03,
        "duration": 10,
        "is_one_time": False,
        "description": (
            "Optional Medicare enrollment from age 55. Modest net federal cost (\\~\\$50B/yr) after "
            "premium offsets and reduced ACA marketplace subsidies. CBO 2019 scored at \\$487B/10yr."
        ),
    },
    "High-Speed Rail Program ($30B/yr)": {
        # Capital grants for rail corridors - construction, on multi-year
        # drawdowns.
        "outlay_account_class": "construction_and_capital",
        "annual_spending": 30.0,
        "category": "Infrastructure",
        "multiplier": 1.4,
        "growth_rate": 0.02,
        "duration": 10,
        "is_one_time": False,
        "description": (
            "Federal matching grants for regional high-speed rail corridors (e.g. Northeast, "
            "California, Texas Central). Infrastructure-grade multiplier (\\~1.4) and long-horizon "
            "productivity effects."
        ),
    },
}

#: Which spend-out profile a category implies when a preset does not state one
#: (the Custom program) or when the user changes the category out from under a
#: preset. This is the same *classification* the validation battery uses
#: (``validation/core.py``): the account type governs how fast authority
#: becomes an outlay. It is keyed to the account being funded, never to a
#: benchmark id, and no rate here was chosen by the number it produced.
_CATEGORY_TO_OUTLAY_CLASS = {
    "Infrastructure": "construction_and_capital",
    "Defense": "operations_and_support",
    "Non-Defense Discretionary": "operations_and_support",
    "Mandatory Programs": "mandatory_benefit",
    "Social Security": "mandatory_benefit",
    "Medicare": "mandatory_benefit",
    "Medicaid": "mandatory_benefit",
    "Education": "grants_and_procurement",
    "Research & Development": "grants_and_procurement",
}

#: The spend-out profiles the Tailor form offers, in disbursement-speed order.
#: ``immediate`` stays on the list as an explicit choice - it is the identity,
#: one dollar of authority becoming one dollar of outlay in the year it is
#: provided - but it is no longer the default for any program.
OUTLAY_CLASS_ORDER: tuple[str, ...] = (
    "mandatory_benefit",
    "personnel_and_benefits",
    "operations_and_support",
    "grants_and_procurement",
    "construction_and_capital",
    IMMEDIATE,
)


def outlay_class_for(preset: dict[str, Any], category: str) -> str:
    """The account class a program spends out on.

    The preset's own declaration wins; a category the preset does not cover -
    the Custom program, or a category the user changed - falls back to what
    that category implies.
    """
    declared = preset.get("outlay_account_class")
    if declared and category == preset.get("category"):
        return str(declared)
    return _CATEGORY_TO_OUTLAY_CLASS.get(
        category, declared or "operations_and_support"
    )


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


def _seed_widget_default(
    st_module: Any, key: str, default: Any, *, force: bool = False
) -> None:
    """Seed a widget key before the widget is instantiated.

    Passing both ``key=`` and ``value=``/``index=`` triggers Streamlit's
    "created with a default value but also had its value set via Session
    State" warning once the key exists, so the defaults are seeded here and
    omitted on the widget itself.

    ``force=True`` re-seeds an existing key. That is what preserves the old
    unkeyed behaviour of the preset-driven fields: an unkeyed widget's identity
    includes its default, so switching programs rebuilt the widget with the new
    program's value. A stable key removes that identity change, so the re-seed
    has to be explicit — see ``_apply_preset_defaults``.

    The shared implementation also mirrors the value to a plain session key so
    it survives leaving ``/tailor`` and coming back: Streamlit scopes widget
    state by ``active_script_hash`` and drops the state of widgets that did not
    render on the page just left (``ui/session_state.py``).
    """
    seed_widget_default(st_module, key, default, force=force)


def _apply_preset_defaults(
    st_module: Any, selected_preset: str, defaults: dict[str, Any]
) -> None:
    """Push a spending preset's values into the keyed widgets it drives.

    Only fires when the selected program actually changed, so a user's manual
    override survives an unrelated rerun exactly as it did when the widgets
    were unkeyed.
    """
    changed = st_module.session_state.get(KEY_TAILOR_SPEND_PRESET_APPLIED) != selected_preset
    if changed:
        st_module.session_state[KEY_TAILOR_SPEND_PRESET_APPLIED] = selected_preset
    for key, value in defaults.items():
        _seed_widget_default(st_module, key, value, force=changed)


def render_spending_policy_inputs(
    st_module: Any,
    default_preset: str | None = None,
) -> dict[str, Any]:
    """Render spending policy input controls and return selected values."""
    st_module.markdown("#### Spending program")

    preset_names = list(SPENDING_PRESETS.keys())
    spending_key = _SPENDING_PRESET_KEY
    restore_widget_value(st_module, spending_key)
    if (
        spending_key in st_module.session_state
        and st_module.session_state[spending_key] not in preset_names
    ):
        forget_widget_value(st_module, spending_key)

    selected_preset = st_module.selectbox(
        "Select a program",
        options=preset_names,
        index=preset_names.index(default_preset) if default_preset in preset_names else 0,
        key=spending_key,
        help="Choose a pre-configured spending scenario or define a custom program.",
    )
    mirror_widget_value(st_module, spending_key)
    preset = SPENDING_PRESETS[selected_preset]

    if selected_preset != "Custom program":
        st_module.caption(preset["description"])

    is_custom = selected_preset == "Custom program"

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
    preset_category = (
        preset["category"] if preset["category"] in all_categories else all_categories[0]
    )

    # Re-seed every preset-driven field when the program changes (see
    # ``_apply_preset_defaults``); the program-name box is not preset-driven.
    _apply_preset_defaults(
        st_module,
        selected_preset,
        {
            KEY_TAILOR_SPEND_ANNUAL: float(preset["annual_spending"]),
            KEY_TAILOR_SPEND_CATEGORY: preset_category,
            KEY_TAILOR_SPEND_DURATION: int(preset["duration"]),
            KEY_TAILOR_SPEND_GROWTH_RATE: float(preset["growth_rate"]) * 100,
            KEY_TAILOR_SPEND_MULTIPLIER: float(preset["multiplier"]),
            KEY_TAILOR_SPEND_ONE_TIME: bool(preset["is_one_time"]),
        },
    )

    if is_custom:
        _seed_widget_default(
            st_module, KEY_TAILOR_SPEND_PROGRAM_NAME, "Infrastructure Investment"
        )
        program_name = st_module.text_input(
            "Program name",
            key=KEY_TAILOR_SPEND_PROGRAM_NAME,
            help="A short label for this spending program.",
        )
    else:
        program_name = selected_preset.split("(")[0].strip()

    annual_spending = st_module.number_input(
        "Annual spending change ($B)",
        min_value=-500.0,
        max_value=500.0,
        step=10.0,
        key=KEY_TAILOR_SPEND_ANNUAL,
        help="**Positive** = spending increase, **Negative** = spending cut.",
    )

    spending_category = st_module.selectbox(
        "Category",
        all_categories,
        key=KEY_TAILOR_SPEND_CATEGORY,
        help="Affects fiscal multiplier defaults and baseline projections.",
    )

    # The spend-out profile is a classification of the account being funded, so
    # it is re-derived whenever the program or the category changes. A manual
    # override survives every other rerun, exactly like the sliders below.
    seeded_from = f"{selected_preset}|{spending_category}"
    _seed_widget_default(
        st_module,
        KEY_TAILOR_SPEND_OUTLAY_CLASS,
        outlay_class_for(preset, spending_category),
        force=st_module.session_state.get(KEY_TAILOR_SPEND_OUTLAY_SEEDED_FROM)
        != seeded_from,
    )
    st_module.session_state[KEY_TAILOR_SPEND_OUTLAY_SEEDED_FROM] = seeded_from

    with st_module.expander("Economic parameters", expanded=False):
        st_module.caption(
            "Pre-populated from the selected program. Override if you have specific values "
            "from CBO or the economics literature."
        )
        duration = st_module.slider(
            "Duration (years)",
            min_value=1,
            max_value=10,
            key=KEY_TAILOR_SPEND_DURATION,
            help="Standard CBO budget window is 10 years.",
        )

        growth_rate = st_module.slider(
            "Annual real growth rate (%)",
            min_value=-5.0,
            max_value=10.0,
            step=0.5,
            key=KEY_TAILOR_SPEND_GROWTH_RATE,
            help="How fast spending grows each year after the first.",
        ) / 100

        multiplier = st_module.slider(
            "Fiscal multiplier",
            min_value=0.0,
            max_value=2.0,
            step=0.1,
            key=KEY_TAILOR_SPEND_MULTIPLIER,
            help=(
                "GDP impact per dollar spent. Typical values: infrastructure \\~1.5, defense \\~1.0, "
                "transfers \\~0.8. ([CBO 2015 estimates](https://www.cbo.gov/publication/49958))"
            ),
        )

        is_one_time = st_module.checkbox(
            "One-time expenditure",
            key=KEY_TAILOR_SPEND_ONE_TIME,
            help="Check for one-time spending (e.g., disaster relief) rather than recurring.",
        )

        outlay_account_class = st_module.selectbox(
            "Spend-out profile",
            options=list(OUTLAY_CLASS_ORDER),
            format_func=lambda name: ACCOUNT_CLASS_LABELS[name].capitalize(),
            key=KEY_TAILOR_SPEND_OUTLAY_CLASS,
            help=(
                "How fast budget authority becomes an outlay. Defaults to the "
                "account type this program funds; profiles are fitted on CBO "
                "options that the validation battery does not score. "
                "**Immediate** turns the spend-out off and books authority as "
                "outlays in the year it is provided."
            ),
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
        "outlay_account_class": outlay_account_class,
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
        # Spending presets spend out. A caller that omits the key keeps the
        # classification its category implies rather than silently reverting to
        # the identity, so an older share link scores like the current form.
        outlay_account_class=spending_inputs.get("outlay_account_class")
        or _CATEGORY_TO_OUTLAY_CLASS.get(
            spending_inputs["spending_category"], "operations_and_support"
        ),
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
