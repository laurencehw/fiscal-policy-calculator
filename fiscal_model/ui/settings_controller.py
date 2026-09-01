"""
Settings tab rendering helpers.
"""

from __future__ import annotations

import datetime
from typing import Any

from .session_state import (
    KEY_SETTING_DARK_MODE,
    KEY_SETTING_DATA_YEAR,
    KEY_SETTING_MACRO_MODEL,
    KEY_SETTING_USE_MICROSIM,
    KEY_SETTING_USE_MICROSIM_DISTRIBUTION,
    KEY_SETTING_USE_REAL_DATA,
)

# Pre-existing widget key: share_links.py writes it and tests/test_share_links.py
# pins the literal, so it keeps the now-stale ``sidebar_`` prefix. New settings
# widgets use the ``setting_*`` namespace.
_DYNAMIC_SCORING_KEY = "sidebar_setting_dynamic_scoring"


def _seed_widget_default(st_module: Any, key: str, default: Any) -> None:
    """Seed a widget key before the widget is instantiated.

    Five of the seven model settings were unkeyed, so their values lived only
    in Streamlit's positional widget identity and would reset when the panel
    moves out of the sidebar. Passing both ``key=`` and ``value=``/``index=``
    triggers Streamlit's "created with a default value but also had its value
    set via Session State" warning once the key exists, so defaults are seeded
    here and omitted on the widget.
    """
    if key not in st_module.session_state:
        st_module.session_state[key] = default


def _available_irs_data_years() -> list[int]:
    """
    Discover IRS SOI data years shipped under fiscal_model/data_files/irs_soi.

    Returns the years sorted newest-first so the selectbox defaults to the
    most recent vintage. Falls back to the historical default [2022, 2021]
    if the data directory is unreadable — this keeps the UI functional on
    a partial checkout without masking real problems loudly in the logs.
    """
    try:
        from fiscal_model.data.irs_soi import IRSSOIData

        years = IRSSOIData().get_data_years_available()
        if years:
            return sorted(years, reverse=True)
    except Exception:
        pass
    return [2022, 2021]


def render_settings_tab(st_module: Any, settings_tab: Any) -> dict[str, Any]:
    """
    Render settings panel and return selected configuration values.
    """
    macro_model = None

    with settings_tab:
        # Dark mode toggle (persisted in session state)
        if "dark_mode" not in st_module.session_state:
            st_module.session_state.dark_mode = False

        # The widget key is distinct from the ``dark_mode`` code key on purpose:
        # the block below writes ``dark_mode`` *after* the widget renders, which
        # Streamlit forbids for a key bound to an already-instantiated widget.
        _seed_widget_default(
            st_module, KEY_SETTING_DARK_MODE, bool(st_module.session_state.dark_mode)
        )
        dark_mode = st_module.checkbox(
            "🌙 Dark mode",
            key=KEY_SETTING_DARK_MODE,
            help="Toggle between light and dark theme. Persists during session.",
        )
        if dark_mode != st_module.session_state.dark_mode:
            st_module.session_state.dark_mode = dark_mode
            # Force rerun to apply CSS changes
            st_module.rerun()

        dynamic_scoring = st_module.checkbox(
            "Enable dynamic scoring",
            value=bool(st_module.session_state.get(_DYNAMIC_SCORING_KEY, False)),
            key=_DYNAMIC_SCORING_KEY,
            help=(
                "Add macroeconomic feedback to the estimate. "
                "A tax cut that boosts GDP generates some offsetting revenue; "
                "a spending increase may crowd out private investment. "
                "Uses FRB/US-calibrated multipliers from the Federal Reserve."
            ),
        )
        if dynamic_scoring:
            _seed_widget_default(
                st_module, KEY_SETTING_MACRO_MODEL, "FRB/US-Lite (recommended)"
            )
            macro_model = st_module.selectbox(
                "Macro model",
                ["FRB/US-Lite (recommended)", "Simple Multiplier"],
                key=KEY_SETTING_MACRO_MODEL,
                help=(
                    "**FRB/US-Lite** — Federal Reserve-calibrated multipliers "
                    "(spending 1.4x, tax 0.7x, with decay). "
                    "**Simple Multiplier** — basic Keynesian approach."
                ),
            )

        with st_module.expander("Data & methodology"):
            _seed_widget_default(st_module, KEY_SETTING_USE_REAL_DATA, True)
            use_real_data = st_module.checkbox(
                "Use real IRS/FRED data",
                key=KEY_SETTING_USE_REAL_DATA,
                help=(
                    "When enabled, the model auto-populates taxpayer counts and "
                    "income levels from IRS Statistics of Income tables, and GDP "
                    "from the St. Louis Fed (FRED). When disabled, uses CBO-based "
                    "hardcoded estimates."
                ),
            )

            # The option list is discovered from the shipped data files, so a
            # stored year can go stale (or start as the schema's ``None``).
            # Fall back to the newest available vintage, matching the old
            # unkeyed default of ``index=0``.
            available_years = _available_irs_data_years()
            if st_module.session_state.get(KEY_SETTING_DATA_YEAR) not in available_years:
                st_module.session_state[KEY_SETTING_DATA_YEAR] = available_years[0]
            data_year = st_module.selectbox(
                "IRS data year",
                available_years,
                key=KEY_SETTING_DATA_YEAR,
                help=(
                    "Which year of IRS Statistics of Income data to use for "
                    "taxpayer counts and income distributions. Options are "
                    "discovered from fiscal_model/data_files/irs_soi/, so "
                    "dropping in a new table_1_1_<year>.csv makes it available "
                    "here without a code change."
                ),
            )

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

            _seed_widget_default(st_module, KEY_SETTING_USE_MICROSIM, False)
            use_microsim_general = st_module.checkbox(
                "Microsimulation mode for revenue scoring (experimental)",
                key=KEY_SETTING_USE_MICROSIM,
                help=(
                    "Score revenue via individual tax units (JCT-style) instead of "
                    "bracket averages. More accurate for phase-outs, but requires "
                    "CPS microdata and is slower. Leave off for the validated "
                    "aggregate revenue path."
                ),
            )

            _seed_widget_default(st_module, KEY_SETTING_USE_MICROSIM_DISTRIBUTION, True)
            use_microsim_distribution = st_module.checkbox(
                "Return-level microsim for distributional analysis",
                key=KEY_SETTING_USE_MICROSIM_DISTRIBUTION,
                help=(
                    "Default on. Uses return-level microsimulation for who-pays "
                    "tables (ordinary vs preferential rates, SALT, refundable "
                    "credits). Uncheck to force the synthetic bracket path."
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
        "use_microsim": use_microsim_general,
        "use_microsim_distribution": use_microsim_distribution,
        "data_year": data_year,
        "dark_mode": dark_mode,
    }
