"""
Top-level Streamlit app orchestration.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from .a11y import inject_a11y_styles
from .calculation_controller import (
    ensure_results_state,
    execute_calculation_if_requested,
    render_sidebar_inputs,
)
from .controller_utils import compute_run_id
from .helpers import TEXTBOOK_HOME, TEXTBOOK_LINKS
from .session_state import (
    KEY_PENDING_SIDEBAR_UPDATES,
    KEY_QS_CALCULATE,
    initialize_session_state,
)
from .settings_controller import render_settings_tab
from .tabs_controller import build_main_tabs, render_footer, render_result_tabs

_HOW_SCORED_MARKDOWN = (
    "The calculator applies three steps:\n\n"
    "1. **Static scoring** — direct revenue effect of the policy change\n"
    "2. **Behavioral response** — how taxpayers adjust based on the Elasticity of "
    "Taxable Income (ETI = 0.25, "
    "[Saez et al. 2012](https://eml.berkeley.edu/~saez/saez-slemrod-giertzJEL12.pdf))\n"
    "3. **Dynamic feedback** *(optional)* — GDP and employment effects using "
    "FRB/US-calibrated multipliers\n\n"
    "Data: IRS Statistics of Income, FRED, CBO Baseline Projections. "
    "25+ policies validated within 15% of official CBO/JCT scores.\n\n"
    "For background, see "
    f"[Optimal Taxation (Ch 16)]({TEXTBOOK_LINKS['optimal_taxation']}) and "
    f"[The Federal Budget (Ch 22)]({TEXTBOOK_LINKS['federal_budget']}) in the textbook."
)

# Re-exported for back-compat with existing tests. Prefer the canonical
# constant from ``fiscal_model.ui.session_state`` for new code.
_PENDING_SIDEBAR_UPDATES_KEY = KEY_PENDING_SIDEBAR_UPDATES


def _queue_sidebar_updates(st_module: Any, **updates: Any) -> None:
    """Queue sidebar widget state updates for the next rerun."""
    st_module.session_state[KEY_PENDING_SIDEBAR_UPDATES] = updates
    st_module.session_state[KEY_QS_CALCULATE] = True


def _apply_pending_sidebar_updates(st_module: Any) -> None:
    """Apply deferred sidebar widget state before sidebar widgets are created."""
    updates = st_module.session_state.pop(KEY_PENDING_SIDEBAR_UPDATES, None)
    if not updates:
        return

    for key, value in updates.items():
        st_module.session_state[key] = value


def render_data_status(st_module: Any, deps: Any) -> None:
    """
    Render a data status indicator in the sidebar showing CBO baseline vintage
    and FRED data status. Placed at the bottom of the sidebar.
    """
    try:
        from fiscal_model.health import check_health

        def _status_icon(status: str | None) -> str:
            if status == "ok":
                return "🟢"
            if status == "degraded":
                return "🟡"
            if status == "error":
                return "🔴"
            return "⚪"

        def _age_label(days: Any) -> str:
            if isinstance(days, int | float):
                return str(int(days))
            return "n/a"

        def _format_fred_summary(component: dict[str, Any]) -> str:
            source = component.get("source")
            cache_age_days = component.get("cache_age_days")
            cache_is_expired = bool(component.get("cache_is_expired", False))
            api_available = bool(component.get("api_available", False))

            if source == "live":
                return "Live (FRED API)"
            if source == "cache" and cache_is_expired:
                return f"Stale cache ({_age_label(cache_age_days)} days)"
            if source == "cache":
                return f"Cache ({_age_label(cache_age_days)} days)"
            if source == "fallback":
                return "Fallback (hardcoded values)"
            if api_available:
                return "API configured"
            return "Unavailable"

        health = check_health()
        baseline = health.get("baseline", {})
        irs_soi = health.get("irs_soi", {})
        fred = health.get("fred", {})

        baseline_freshness = baseline.get("freshness") or {}
        irs_freshness = irs_soi.get("freshness") or {}

        baseline_summary = str(baseline.get("vintage", "Unknown"))
        if baseline_freshness.get("message"):
            baseline_summary = (
                f"{baseline_summary} ({baseline_freshness['message']})"
            )

        latest_irs_year = irs_soi.get("latest_year")
        irs_summary = str(latest_irs_year) if latest_irs_year else "Unavailable"
        if irs_freshness.get("message"):
            irs_summary = f"{irs_summary} ({irs_freshness['message']})"

        fred_summary = _format_fred_summary(fred)

        st_module.markdown("---")
        st_module.markdown("**📊 Data Status**")

        st_module.markdown(
            f"{_status_icon(baseline.get('status'))} **Baseline:** {baseline_summary}"
        )
        st_module.markdown(
            f"{_status_icon(irs_soi.get('status'))} **IRS SOI:** {irs_summary}"
        )
        st_module.markdown(
            f"{_status_icon(fred.get('status'))} **FRED:** {fred_summary}"
        )

        microdata = health.get("microdata", {})
        if microdata.get("status") in {"ok", "degraded"}:
            returns_pct = microdata.get("returns_coverage_pct")
            agi_pct = microdata.get("agi_coverage_pct")
            if returns_pct is not None and agi_pct is not None:
                microdata_summary = (
                    f"{returns_pct:.0f}% returns, {agi_pct:.0f}% AGI "
                    f"vs SOI {microdata.get('calibration_year', '?')}"
                )
            else:
                microdata_summary = microdata.get("notes", "present")
            st_module.markdown(
                f"{_status_icon(microdata.get('status'))} "
                f"**Microdata:** {microdata_summary}"
            )

        if baseline_freshness.get("is_stale"):
            st_module.warning(
                "CBO baseline is past its expected refresh window; results "
                "reflect older economic assumptions."
            )
        elif baseline.get("source") == "hardcoded_fallback":
            st_module.warning(
                "Baseline fell back to hardcoded values; check the data layer "
                "before treating results as publication-ready."
            )

        if irs_freshness.get("is_stale"):
            st_module.warning(
                "IRS Statistics of Income tables are stale; refresh "
                "`fiscal_model/data_files/irs_soi/`."
            )

        with st_module.expander("ℹ️ Data details", expanded=False):
            baseline_fred = baseline.get("fred", {})
            baseline_load_error = baseline.get("load_error") or "None"
            last_updated = (
                fred.get("last_updated")
                or baseline_fred.get("last_updated")
                or "Not available"
            )
            microdata_detail = ""
            if microdata.get("status") in {"ok", "degraded"}:
                microdata_detail = (
                    f"\n\n**Microdata path:** "
                    f"{microdata.get('path', 'Unknown')}\n\n"
                    f"**Microdata provenance:** {microdata.get('notes', '')}\n\n"
                    f"**Weighted tax units:** "
                    f"{microdata.get('weighted_tax_units', 0) / 1e6:.1f}M\n\n"
                    f"**Microsim vs SOI "
                    f"{microdata.get('calibration_year', '?')}:** "
                    f"returns {microdata.get('returns_coverage_pct', 0):.0f}%, "
                    f"AGI {microdata.get('agi_coverage_pct', 0):.0f}%"
                )
            st_module.markdown(
                f"**CBO baseline vintage:** {baseline.get('vintage', 'Unknown')}\n\n"
                f"**Baseline source:** {baseline.get('source', 'Unknown')}\n\n"
                f"**Baseline load error:** {baseline_load_error}\n\n"
                f"**IRS SOI latest year:** {irs_soi.get('latest_year', 'Unavailable')}\n\n"
                f"**FRED source:** {fred.get('source', 'unknown')}\n\n"
                f"**FRED last updated:** {last_updated}\n\n"
                f"**FRED cache age:** {_age_label(fred.get('cache_age_days'))}\n\n"
                f"**GDP source for baseline:** {baseline.get('gdp_source', 'unknown')}"
                + microdata_detail
            )

            if microdata.get("status") in {"ok", "degraded"}:
                _render_augmentation_preview(st_module, microdata)
    except Exception:
        pass


def _render_augmentation_preview(st_module: Any, microdata: dict) -> None:
    """
    Show a diagnostic preview of what top-tail augmentation would do to
    the microdata's SOI coverage. Enable via a checkbox in the Data
    details expander; disabled by default because augmentation is an
    opt-in operation that changes distributional results when plumbed
    through the engine.
    """
    st_module.markdown("---")
    show = st_module.checkbox(
        "Preview top-tail augmentation",
        value=False,
        key="augmentation_preview_toggle",
        help=(
            "Shows how SOI-based top-tail augmentation would change "
            "microdata coverage at \\$1M+. Diagnostic only — does not "
            "affect the policy scoring above."
        ),
    )
    if not show:
        return

    try:
        from fiscal_model.data.cps_asec import load_tax_microdata
        from fiscal_model.microsim.soi_calibration import calibrate_to_soi
        from fiscal_model.microsim.top_tail import augment_top_tail
    except Exception as exc:
        st_module.caption(f"Augmentation modules unavailable: {exc}")
        return

    try:
        calibration_year = int(microdata.get("calibration_year") or 2022)
        base_df, _ = load_tax_microdata()
        augmented_df, report = augment_top_tail(base_df, year=calibration_year)
        before = calibrate_to_soi(base_df, year=calibration_year).summary()
        after = calibrate_to_soi(augmented_df, year=calibration_year).summary()
    except Exception as exc:
        st_module.caption(f"Could not compute augmentation preview: {exc}")
        return

    st_module.markdown(
        "**Augmentation preview** (SOI "
        f"{calibration_year}, floor \\$2M, "
        f"{report.synthetic_records:,} synthetic records):"
    )
    st_module.markdown(
        f"- Returns coverage: "
        f"{before['returns_coverage_pct']:.0f}% → "
        f"**{after['returns_coverage_pct']:.0f}%**\n"
        f"- AGI coverage: "
        f"{before['agi_coverage_pct']:.0f}% → "
        f"**{after['agi_coverage_pct']:.0f}%**\n"
        f"- Synthetic top-tail AGI added: "
        f"\\${report.synthetic_agi_billions:,.1f}B"
    )
    st_module.caption(
        "Augmentation is a *coverage* fix, not a *representation* fix. "
        "Synthetic records carry SOI-aggregate income composition but "
        "don't model individual-level behaviour. See "
        "`docs/VALIDATION_NOTES.md` for the full caveat."
    )


def render_quick_start(st_module: Any) -> None:
    """
    Render a dismissible quick-start guide with clickable policy cards.
    Auto-dismissed once results exist.
    """
    if "quick_start_dismissed" not in st_module.session_state:
        st_module.session_state.quick_start_dismissed = False

    # Auto-dismiss once results have been calculated
    if st_module.session_state.get("results"):
        st_module.session_state.quick_start_dismissed = True

    if not st_module.session_state.quick_start_dismissed:
        col1, col2 = st_module.columns([20, 1])
        with col1:
            st_module.markdown(
                "👋 Estimate the 10-year budget impact of any U.S. tax or spending proposal, "
                "backed by IRS data and CBO methodology. "
                "Click a card below to load a preset and run a calculation instantly."
            )
        with col2:
            if st_module.button("✕", key="dismiss_quick_start"):
                st_module.session_state.quick_start_dismissed = True
                st_module.rerun()

        c1, c2, c3 = st_module.columns(3)

        with c1, st_module.container(border=True):
            st_module.markdown("**TCJA Extension**")
            st_module.caption("Extend all individual TCJA provisions beyond the 2025 sunset")
            st_module.markdown(
                '<span style="color:#d9534f;font-weight:600">▲ +$4.6T to deficit</span>'
                " &nbsp;*(10-yr, CBO)*",
                unsafe_allow_html=True,
            )
            if st_module.button("Try this →", key="qs_btn_tcja", use_container_width=True):
                _queue_sidebar_updates(
                    st_module=st_module,
                    sidebar_analysis_mode="📋 Tax proposal (preset)",
                    sidebar_policy_area="TCJA / Individual",
                    sidebar_preset_choice="TCJA Full Extension",
                )
                st_module.rerun()

        with c2, st_module.container(border=True):
            st_module.markdown("**Biden 400K+ Tax**")
            st_module.caption("Restore 39.6% top rate on income above $400K")
            st_module.markdown(
                '<span style="color:#5cb85c;font-weight:600">▼ −$252B from deficit</span>'
                " &nbsp;*(10-yr, Treasury)*",
                unsafe_allow_html=True,
            )
            if st_module.button("Try this →", key="qs_btn_biden", use_container_width=True):
                _queue_sidebar_updates(
                    st_module=st_module,
                    sidebar_analysis_mode="📋 Tax proposal (preset)",
                    sidebar_policy_area="Income Tax",
                    sidebar_preset_choice="Biden 2025 Proposal",
                )
                st_module.rerun()

        with c3, st_module.container(border=True):
            st_module.markdown("**Infrastructure $100B/yr**")
            st_module.caption("Federal investment in roads, broadband, and water systems")
            st_module.markdown(
                '<span style="color:#d9534f;font-weight:600">▲ +$1.0T to deficit</span>'
                " &nbsp;*(10-yr, est.)*",
                unsafe_allow_html=True,
            )
            if st_module.button("Try this →", key="qs_btn_infra", use_container_width=True):
                _queue_sidebar_updates(
                    st_module=st_module,
                    sidebar_analysis_mode="💰 Spending program",
                    sidebar_spending_preset="Infrastructure Investment ($100B/yr)",
                )
                st_module.rerun()

        st_module.markdown("---")


def run_main_app(st_module: Any, deps: Any, model_available: bool, app_root: Path) -> None:
    """
    Render and orchestrate the full Streamlit app flow.
    Top-level tabs: Calculator | Budget Builder | Generational | State | Bill Tracker | Methodology
    """
    # Ensure every known session key has its declared default before any
    # widgets are constructed. Safe to call on every rerun — does not
    # overwrite existing values.
    initialize_session_state(st_module)

    # Inject a11y CSS (sr-only, focus rings) and the skip-to-main-content
    # link before rendering any content. Idempotent per-render.
    inject_a11y_styles(st_module)

    st_module.title("Fiscal Policy Impact Calculator")
    st_module.markdown(
        "Estimate the 10-year budgetary and economic effects of U.S. tax and "
        "spending proposals. Powered by IRS data, FRED, and CBO methodology. "
        f"Companion to the [Public Economics textbook]({TEXTBOOK_HOME}). "
        "🎓 [**Classroom Mode**](?mode=classroom) — interactive assignments for Public Economics courses.\n\n"
        "🆕 **Can you balance the budget?** Try the **⚖️ Budget Builder** tab →"
    )

    top_tabs = st_module.tabs([
        "📊 Calculator",
        "⚖️ Budget Builder",
        "🌐 Generational",
        "🗺️ State",
        "📋 Bill Tracker",
        "✅ Validation",
        "📖 Methodology",
    ])

    with top_tabs[0]:
        _render_calculator(
            st_module=st_module,
            deps=deps,
            model_available=model_available,
            app_root=app_root,
        )
        render_footer(st_module=st_module)

    _logger = logging.getLogger(__name__)

    with top_tabs[1]:
        try:
            _render_budget_builder(st_module=st_module, deps=deps)
        except Exception:
            _logger.exception("Budget Builder error")
            st_module.error(
                "The Budget Builder encountered an issue. "
                "Please try reloading the page or clearing your inputs."
            )
        render_footer(st_module=st_module)

    with top_tabs[2]:
        try:
            _render_generational(st_module=st_module, deps=deps)
        except Exception:
            _logger.exception("Generational analysis error")
            st_module.error(
                "The Generational analysis encountered an issue. "
                "Please try adjusting your parameters or reloading the page."
            )
        render_footer(st_module=st_module)

    with top_tabs[3]:
        try:
            _render_state(st_module=st_module, deps=deps)
        except Exception:
            _logger.exception("State analysis error")
            st_module.error(
                "The State analysis encountered an issue. "
                "Please try reloading the page."
            )
        render_footer(st_module=st_module)

    with top_tabs[4]:
        try:
            deps.render_bill_tracker_tab(st_module=st_module)
        except Exception:
            _logger.exception("Bill Tracker error")
            st_module.error(
                "The Bill Tracker encountered an issue. "
                "Please try reloading the page."
            )
        render_footer(st_module=st_module)

    with top_tabs[5]:
        try:
            from .tabs.validation_scorecard import render_validation_scorecard_tab
            render_validation_scorecard_tab(st_module=st_module)
        except Exception:
            _logger.exception("Validation scorecard error")
            st_module.error(
                "The Validation scorecard encountered an issue. "
                "Please try reloading the page."
            )
        render_footer(st_module=st_module)

    with top_tabs[6]:
        try:
            deps.render_methodology_tab(st_module=st_module)
        except Exception:
            _logger.exception("Methodology tab error")
            st_module.error(
                "The Methodology tab encountered an issue. "
                "Please try reloading the page."
            )
        render_footer(st_module=st_module)


def _render_calculator(
    st_module: Any,
    deps: Any,
    model_available: bool,
    app_root: Path,
) -> None:
    """Render the Calculator tab: sidebar inputs + results tabs."""
    # ── Sidebar ──────────────────────────────────────────────────────────
    _apply_pending_sidebar_updates(st_module=st_module)

    with st_module.sidebar:
        st_module.header("Policy Configuration")

        # 1. Policy inputs (no Calculate button yet)
        calc_context = render_sidebar_inputs(st_module=st_module, deps=deps)

        # 2. Model settings expander (above Calculate button)
        settings = render_settings_tab(
            st_module=st_module,
            settings_tab=st_module.expander("⚙️ Model settings", expanded=False),
        )

        # Apply dark mode via CSS class (better compatibility)
        if settings.get("dark_mode", False):
            st_module.markdown(
                '<style>'
                'body, .stApp {background-color: #0e1117 !important; color: #fafafa !important;} '
                '.stMarkdown, p, h1, h2, h3, label {color: #fafafa !important;} '
                '.metric-card {background-color: #262730 !important;}'
                '</style>',
                unsafe_allow_html=True,
            )

        # 3. Calculate button
        st_module.markdown("---")
        calculate = st_module.button(
            "Calculate Impact",
            type="primary",
            use_container_width=True,
        )
        # Auto-trigger from quick-start card click
        if getattr(st_module.session_state, KEY_QS_CALCULATE, False):
            del st_module.session_state[KEY_QS_CALCULATE]
            calculate = True
        calc_context["calculate"] = calculate

        # 4. Data Status (bottom of sidebar — infrastructure, not decision-relevant)
        render_data_status(st_module=st_module, deps=deps)

        with st_module.expander("🎓 Classroom Mode", expanded=False):
            st_module.markdown(
                "**Interactive assignments for Public Economics courses.**\n\n"
                "7 guided assignments with hints, auto-grading, and PDF export for student submissions. "
                "Covers Laffer curves, TCJA, distributional analysis, and more.\n\n"
                "[➡️ Open Classroom Mode](?mode=classroom)"
            )

    # ── Main content ─────────────────────────────────────────────────────
    calc_context["run_id"] = compute_run_id(calc_context=calc_context, settings=settings)
    st_module.session_state.current_run_id = calc_context["run_id"]

    # Dismissible welcome guide (auto-hides after first calculation)
    render_quick_start(st_module=st_module)

    # "How is this scored?" — prominent in main content below title
    with st_module.expander("🔍 How is this scored?", expanded=False):
        st_module.markdown(_HOW_SCORED_MARKDOWN)

    tabs = build_main_tabs(
        st_module=st_module,
        mode=calc_context["mode"],
    )

    ensure_results_state(st_module=st_module)
    execute_calculation_if_requested(
        st_module=st_module,
        deps=deps,
        app_root=app_root,
        model_available=model_available,
        calc_context=calc_context,
        settings=settings,
    )

    render_result_tabs(
        st_module=st_module,
        deps=deps,
        tabs=tabs,
        settings=settings,
        model_available=model_available,
        is_spending=calc_context["is_spending"],
        mode=calc_context["mode"],
    )


def _render_budget_builder(st_module: Any, deps: Any) -> None:
    """Render the Budget Builder tab — standalone deficit reduction planner."""
    from fiscal_model.ui.tabs.deficit_target import render_deficit_target_tab

    render_deficit_target_tab(
        st_module=st_module,
        cbo_score_map=deps.CBO_SCORE_MAP,
        fiscal_policy_scorer_cls=deps.FiscalPolicyScorer,
        use_real_data=True,
    )


def _render_generational(st_module: Any, deps: Any) -> None:
    """Render the top-level Generational Analysis tab."""
    result_data = st_module.session_state.get("results")
    run_id = st_module.session_state.get("results_run_id") or st_module.session_state.get("last_run_id")
    deps.render_generational_analysis_tab(
        st_module=st_module,
        result_data=result_data,
        run_id=run_id,
    )


def _render_state(st_module: Any, deps: Any) -> None:
    """Render the top-level State Analysis tab with its own state selector."""
    from fiscal_model.models.state.database import STATE_NAMES, SUPPORTED_STATES

    state_selection = st_module.selectbox(
        "State",
        options=SUPPORTED_STATES,
        format_func=lambda code: f"{code} — {STATE_NAMES[code]}",
        key="top_level_state_select",
        help="Select a state for combined federal + state analysis.",
    )
    selected_state = state_selection if state_selection else "CA"

    result_data = st_module.session_state.get("results")
    run_id = st_module.session_state.get("results_run_id") or st_module.session_state.get("last_run_id")
    deps.render_state_analysis_tab(
        st_module=st_module,
        state=selected_state,
        result_data=result_data,
        run_id=run_id,
    )
