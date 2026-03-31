"""
Settings tab rendering helpers.
"""

from __future__ import annotations

from typing import Any


def render_settings_tab(st_module: Any, settings_tab: Any) -> dict[str, Any]:
    """
    Render settings panel and return selected configuration values.
    """
    macro_model = None

    with settings_tab:
        dynamic_scoring = st_module.checkbox(
            "Enable dynamic scoring",
            value=False,
            help=(
                "Add macroeconomic feedback to the estimate. "
                "A tax cut that boosts GDP generates some offsetting revenue; "
                "a spending increase may crowd out private investment. "
                "Uses FRB/US-calibrated multipliers from the Federal Reserve."
            ),
        )
        if dynamic_scoring:
            macro_model = st_module.selectbox(
                "Macro model",
                ["FRB/US-Lite (recommended)", "Simple Multiplier"],
                help=(
                    "**FRB/US-Lite** — Federal Reserve-calibrated multipliers "
                    "(spending 1.4x, tax 0.7x, with decay). "
                    "**Simple Multiplier** — basic Keynesian approach."
                ),
            )

        with st_module.expander("Data & methodology"):
            use_real_data = st_module.checkbox(
                "Use real IRS/FRED data",
                value=True,
                help=(
                    "When enabled, the model auto-populates taxpayer counts and "
                    "income levels from IRS Statistics of Income tables, and GDP "
                    "from the St. Louis Fed (FRED). When disabled, uses CBO-based "
                    "hardcoded estimates."
                ),
            )

            data_year = st_module.selectbox(
                "IRS data year",
                [2022, 2021],
                help=(
                    "Which year of IRS Statistics of Income data to use for "
                    "taxpayer counts and income distributions."
                ),
            )

            import datetime
            current_year = datetime.date.today().year
            data_age = current_year - data_year
            if data_age >= 3:
                st_module.warning(
                    f"IRS data is {data_age} years old. Taxpayer distributions "
                    f"may have shifted. Consider updating to more recent data."
                )
            elif data_age >= 2:
                st_module.caption(
                    f"Note: Using {data_year} IRS data ({data_age} years old). "
                    f"This is normal — IRS SOI data has a ~2 year publication lag."
                )

            use_microsim = st_module.checkbox(
                "Microsimulation mode (experimental)",
                value=False,
                help=(
                    "Calculate taxes for individual households (JCT-style) instead of "
                    "bracket averages. More accurate for policies with phase-outs, "
                    "but requires CPS microdata and is slower."
                ),
            )

            st_module.markdown("---")
            st_module.caption(
                "**Methodology:** CBO-style static scoring with behavioral "
                "adjustments (ETI = 0.25). Data from IRS SOI, FRED, and "
                "CBO Baseline Projections. "
                "[Full methodology →](https://github.com/laurencehw/fiscal-policy-calculator/blob/main/docs/METHODOLOGY.md)"
            )

    return {
        "use_real_data": use_real_data,
        "dynamic_scoring": dynamic_scoring,
        "macro_model": macro_model,
        "use_microsim": use_microsim,
        "data_year": data_year,
    }
