"""
Shared page-level Streamlit orchestration.

``app.py`` is the ``st.navigation`` router and ``app_pages/`` holds one module
per surface; this module holds what those pages share — the per-run bootstrap,
the error boundary, the quick-start cards, the Data Status panel, and the
score-a-policy workbench used by ``/explore`` and ``/tailor``.
"""

from __future__ import annotations

import logging
from typing import Any

from .a11y import inject_a11y_styles
from .helpers import TEXTBOOK_LINKS
from .session_state import (
    KEY_PENDING_SIDEBAR_UPDATES,
    KEY_QS_CALCULATE,
    initialize_session_state,
)

_HOW_SCORED_MARKDOWN = (
    "The calculator applies three steps:\n\n"
    "1. **Static scoring** — direct revenue effect of the policy change\n"
    "2. **Behavioral response** — how taxpayers adjust based on the Elasticity of "
    "Taxable Income (ETI = 0.25, "
    "[Saez et al. 2012](https://eml.berkeley.edu/~saez/saez-slemrod-giertzJEL12.pdf))\n"
    "3. **Dynamic feedback** *(optional)* — GDP and employment effects using "
    "FRB/US-calibrated multipliers\n\n"
    "**How to read the numbers (model maturity):**\n\n"
    "- **Core (green)** — revenue, distribution, and dynamic scoring. Calibrated "
    "reference models reproduce official decompositions (\\~5% mean error); "
    "genuine out-of-sample predictions are \\~8% mean error.\n"
    "- **Specialized (yellow)** — TCJA, corporate, credits, payroll, etc. Tuned "
    "reconstructions of published scores — transparent, not independent confirmation.\n"
    "- **Exploratory (blue)** — Ask, Bill Tracker, multi-model pilot. Useful UX; "
    "not validated estimates.\n\n"
    "Data: IRS Statistics of Income, FRED, CBO Baseline Projections. "
    "Every result shows a validation-evidence card — never collapse calibrated "
    "and out-of-sample accuracy into one \"validated within X%\" claim.\n\n"
    "For background, see "
    f"[Optimal Taxation (Ch 16)]({TEXTBOOK_LINKS['optimal_taxation']}) and "
    f"[The Federal Budget (Ch 22)]({TEXTBOOK_LINKS['federal_budget']}) in the textbook."
)

# Re-exported for back-compat with existing tests. Prefer the canonical
# constant from ``fiscal_model.ui.session_state`` for new code.
_PENDING_SIDEBAR_UPDATES_KEY = KEY_PENDING_SIDEBAR_UPDATES

_SECTION_ERROR_MESSAGES: dict[str, str] = {
    "Calculator": (
        "The Calculator encountered an issue. "
        "Please try reloading the page or clearing your inputs."
    ),
    "Explore": (
        "Explore encountered an issue. "
        "Please try reloading the page or picking a different proposal."
    ),
    "Tailor": (
        "Tailor encountered an issue. "
        "Please try reloading the page or clearing your inputs."
    ),
    "Build": (
        "Build encountered an issue. "
        "Please try reloading the page or clearing your selections."
    ),
    "Classroom": (
        "Classroom Mode failed to start. "
        "Please reload the page or check the deployment logs."
    ),
    "Budget Builder": (
        "The Budget Builder encountered an issue. "
        "Please try reloading the page or clearing your inputs."
    ),
    "Bill Tracker": (
        "The Bill Tracker encountered an issue. "
        "Please try reloading the page."
    ),
    "Methodology": (
        "The Methodology tab encountered an issue. "
        "Please try reloading the page."
    ),
    "Ask": (
        "The Ask assistant encountered an issue. "
        "Check that ANTHROPIC_API_KEY is set or supply a key in the tab."
    ),
    "Admin": (
        "The admin dashboard encountered an issue reading the usage db."
    ),
}


def _render_section_error(st_module: Any, section_label: str, exc: Exception) -> None:
    """Render a contained top-level section failure."""
    logging.getLogger(__name__).exception("%s section error", section_label)
    st_module.error(
        _SECTION_ERROR_MESSAGES.get(
            section_label,
            f"The {section_label} section encountered an issue.",
        )
    )
    if hasattr(st_module, "caption"):
        st_module.caption(
            "Other sections remain available. Include this section name in a bug report."
        )
    if hasattr(st_module, "expander") and hasattr(st_module, "code"):
        with st_module.expander("Technical details", expanded=False):
            st_module.code(f"{type(exc).__name__}: {exc}", language="text")


def _render_guarded_section(
    st_module: Any,
    section_label: str,
    render_fn: Any,
) -> None:
    """Run a top-level app section behind an error boundary."""
    try:
        render_fn()
    except Exception as exc:
        _render_section_error(st_module, section_label, exc)


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


def render_data_status(
    st_module: Any,
    deps: Any,
    *,
    health: dict[str, Any] | None = None,
    show_banner: bool = True,
) -> None:
    """
    Render the Data Status panel: CBO baseline vintage, IRS SOI, FRED and
    runtime state, plus the degraded-data reasons.

    Since the redesign this renders inside the shared chrome's status popover
    (``components.chrome``) rather than at the bottom of a global sidebar.

    ``health`` lets a caller pass an already-computed ``check_health()``
    payload (the chrome computes one per run for the pill). ``show_banner=False``
    suppresses the degraded-data banner for callers that render it themselves —
    the per-component warnings stay suppressed either way, so the reasons are
    never listed twice.
    """
    try:
        from fiscal_model.health import check_health, summarize_data_degradation

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
            if source == "bundled" and cache_is_expired:
                return f"Stale bundled seed ({_age_label(cache_age_days)} days)"
            if source == "bundled":
                return f"Bundled seed ({_age_label(cache_age_days)} days)"
            if source == "fallback":
                return "Fallback (hardcoded values)"
            if api_available:
                return "API configured"
            return "Unavailable"

        health = check_health() if health is None else health
        baseline = health.get("baseline", {})
        irs_soi = health.get("irs_soi", {})
        fred = health.get("fred", {})
        runtime = health.get("runtime", {})

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

        # Prominent degraded-mode banner: don't make the user infer it from a
        # yellow dot. Summarises *why* the app is running on fallback data.
        degradation = summarize_data_degradation(health)
        degradation_banner_shown = degradation["is_degraded"]
        reason_lines = "\n".join(f"- {r}" for r in degradation["reasons"])
        if degradation_banner_shown and show_banner:
            if degradation["severity"] == "error":
                st_module.error(
                    "🔴 **Data error — results may be unreliable**\n\n" + reason_lines
                )
            else:
                st_module.warning(
                    "🟡 **Some data sources are running on older snapshots**\n\n"
                    + reason_lines
                )
        elif degradation_banner_shown:
            # ``show_banner=False`` means the caller (the shared chrome) owns
            # the page-level notice — and since 2026-09-01 it raises one only
            # for sources past their release-calendar tolerance, once per
            # session. The caveats it deliberately does not shout about still
            # have to be readable *somewhere*, so the panel behind the pill
            # lists every reason, quietly, on every page.
            st_module.caption(reason_lines)

        st_module.markdown(
            f"{_status_icon(baseline.get('status'))} **Baseline:** {baseline_summary}"
        )
        st_module.markdown(
            f"{_status_icon(irs_soi.get('status'))} **IRS SOI:** {irs_summary}"
        )
        st_module.markdown(
            f"{_status_icon(fred.get('status'))} **FRED:** {fred_summary}"
        )
        if runtime:
            st_module.markdown(
                f"{_status_icon(runtime.get('status'))} "
                f"**Runtime:** Python {runtime.get('python_version', 'unknown')}"
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

        # The degradation banner above already lists these same conditions as
        # reason lines — repeating each as its own warning doubled the banner.
        # Only fall back to per-component warnings when no banner rendered.
        if not degradation_banner_shown:
            if baseline_freshness.get("is_stale"):
                st_module.warning(
                    "CBO baseline is past its expected refresh window; results "
                    "reflect older economic assumptions."
                )
            elif baseline.get("source") == "hardcoded_fallback":
                st_module.warning(
                    "Baseline fell back to hardcoded values; treat results as "
                    "approximate rather than publication-ready."
                )

            if irs_freshness.get("is_stale"):
                st_module.warning(
                    "IRS Statistics of Income tables are older than expected; "
                    "revenue baselines may lag the latest filings."
                )

            if runtime.get("status") == "degraded":
                st_module.warning(
                    runtime.get("message", "Python runtime is unsupported.")
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
                f"**FRED data age:** {_age_label(fred.get('cache_age_days'))}\n\n"
                f"**GDP source for baseline:** {baseline.get('gdp_source', 'unknown')}\n\n"
                f"**Python runtime:** {runtime.get('python_version', 'unknown')}\n\n"
                f"**Runtime support:** {runtime.get('supported_range', 'unknown')}"
                + microdata_detail
            )

            if microdata.get("status") in {"ok", "degraded"}:
                _render_augmentation_preview(st_module, microdata)
    except Exception as exc:
        # Don't let a data-status rendering failure vanish silently — the
        # sidebar indicator is itself a signal, so surface that it broke.
        st_module.caption(f"⚪ Data status unavailable ({type(exc).__name__}).")


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
        "don't model individual-level behaviour. The project's validation "
        "notes on GitHub carry the full caveat."
    )


_MONTH_ABBREVIATIONS: dict[str, str] = {
    "january": "Jan",
    "february": "Feb",
    "march": "Mar",
    "april": "Apr",
    "may": "May",
    "june": "Jun",
    "july": "Jul",
    "august": "Aug",
    "september": "Sep",
    "october": "Oct",
    "november": "Nov",
    "december": "Dec",
}

# Dot colours mirror ``_status_icon`` inside ``render_data_status`` so the
# compact pill and the full panel never disagree about severity.
_PILL_DOTS: dict[str, str] = {
    "ok": "🟢",
    "degraded": "🟡",
    "error": "🔴",
}


def _short_vintage(vintage: Any) -> str:
    """``"February 2026"`` -> ``"Feb 2026"``; anything unexpected passes through."""
    text = str(vintage or "").strip()
    if not text:
        return "unknown"
    parts = text.split()
    if len(parts) == 2 and parts[0].lower() in _MONTH_ABBREVIATIONS:
        return f"{_MONTH_ABBREVIATIONS[parts[0].lower()]} {parts[1]}"
    return text


def data_status_pill(health: dict[str, Any]) -> dict[str, Any]:
    """Build the compact data-status pill shown in the shared chrome.

    Returns ``{"label", "dot", "severity"}`` where ``label`` is the
    ``CBO Feb 2026 · SOI 2023`` string and ``severity`` is the worst component
    status ("ok" / "degraded" / "error"). Reuses the same freshness payload the
    full Data Status panel renders, so the dot cannot drift from the panel.
    """
    baseline = health.get("baseline") or {}
    irs_soi = health.get("irs_soi") or {}

    baseline_label = f"CBO {_short_vintage(baseline.get('vintage'))}"
    latest_year = irs_soi.get("latest_year")
    soi_label = f"SOI {latest_year}" if latest_year else "SOI unavailable"

    statuses = {
        str((health.get(component) or {}).get("status") or "")
        for component in ("baseline", "irs_soi", "fred", "runtime", "microdata")
    }
    if "error" in statuses:
        severity = "error"
    elif "degraded" in statuses:
        severity = "degraded"
    else:
        severity = "ok"

    return {
        "label": f"{baseline_label} · {soi_label}",
        "dot": _PILL_DOTS.get(severity, "⚪"),
        "severity": severity,
    }


_QUICK_START_CARDS: tuple[dict[str, Any], ...] = (
    {
        "key": "tcja",
        "question": "What did extending the TCJA cost?",
        "context": (
            "The individual TCJA provisions were extended by the July 2025 "
            "reconciliation law — this scores extension as CBO evaluated it "
            "beforehand"
        ),
        "headline": "▲ +$4.6T to deficit",
        "headline_color": "#d9534f",
        "source": "10-yr, CBO May 2024",
        "preset": {
            "sidebar_analysis_mode": "📋 Tax proposal (preset)",
            "sidebar_policy_area": "TCJA / Individual",
            "sidebar_preset_choice": "TCJA Full Extension",
        },
    },
    {
        "key": "biden400k",
        "question": "What if we restored the 39.6% top rate?",
        "context": "Biden proposal to raise the top rate on income above $400K",
        "headline": "▼ −$252B from deficit",
        "headline_color": "#5cb85c",
        "source": "10-yr, Treasury",
        "preset": {
            "sidebar_analysis_mode": "📋 Tax proposal (preset)",
            "sidebar_policy_area": "TCJA / Individual",
            "sidebar_preset_choice": "Biden 2025 Proposal",
        },
    },
    {
        "key": "corp28",
        "question": "How much would a 28% corporate rate raise?",
        "context": "Reverse the TCJA corporate cut from 21% back toward Obama-era 35%",
        "headline": "▼ −$1.35T from deficit",
        "headline_color": "#5cb85c",
        "source": "10-yr, Treasury",
        "preset": {
            "sidebar_analysis_mode": "📋 Tax proposal (preset)",
            "sidebar_policy_area": "Corporate",
            "sidebar_preset_choice": "Biden Corporate 28%",
        },
    },
    {
        "key": "tariff10",
        "question": "Could a universal 10% tariff replace income taxes?",
        "context": "Trump's universal tariff plus retaliation and consumer costs",
        "headline": "▼ −$2.0T from deficit",
        "headline_color": "#5cb85c",
        "source": "10-yr, TPC",
        "preset": {
            "sidebar_analysis_mode": "📋 Tax proposal (preset)",
            "sidebar_policy_area": "Trade / Tariffs",
            "sidebar_preset_choice": "Trump Universal 10% Tariff (-$2T)",
        },
    },
    {
        "key": "ssc",
        "question": "Would lifting the SS payroll cap fix Social Security?",
        "context": "Eliminate the wage cap so all earnings are subject to OASDI tax",
        "headline": "▼ −$3.2T from deficit",
        "headline_color": "#5cb85c",
        "source": "10-yr, CBO",
        "preset": {
            "sidebar_analysis_mode": "📋 Tax proposal (preset)",
            "sidebar_policy_area": "Payroll / SS",
            "sidebar_preset_choice": "Eliminate SS Cap (-$3.2T)",
        },
    },
    {
        "key": "ctc",
        "question": "How expensive is a permanent expanded CTC?",
        "context": "Make the 2021 ARP-style \\$3,600/\\$3,000 child tax credit permanent",
        "headline": "▲ +$1.6T to deficit",
        "headline_color": "#d9534f",
        "source": "10-yr, CBO",
        "preset": {
            "sidebar_analysis_mode": "📋 Tax proposal (preset)",
            "sidebar_policy_area": "Tax Credits",
            "sidebar_preset_choice": "Biden CTC Expansion",
        },
    },
)


def _render_quick_start_card(
    st_module: Any,
    container: Any,
    card: dict[str, Any],
) -> None:
    with container, st_module.container(border=True):
        st_module.markdown(f"**{card['question']}**")
        st_module.caption(card["context"])
        st_module.markdown(
            f'<span style="color:{card["headline_color"]};font-weight:600">'
            f'{card["headline"]}</span>'
            f' &nbsp;*({card["source"]})*',
            unsafe_allow_html=True,
        )
        if st_module.button(
            "Try this →",
            key=f"qs_btn_{card['key']}",
            width="stretch",
        ):
            _queue_sidebar_updates(st_module=st_module, **card["preset"])
            st_module.rerun()


def render_quick_start(st_module: Any, calculating: bool = False) -> None:
    """
    Render a dismissible quick-start guide with a guided first-score path
    plus a short list of question-led policy cards.
    """
    if "quick_start_dismissed" not in st_module.session_state:
        st_module.session_state.quick_start_dismissed = False

    # Auto-dismiss once results have been calculated — including the run the
    # calculation happens on (this renders before the calculation executes,
    # so waiting for `results` alone leaves the full-height card pushing the
    # fresh results ~1,000px below the fold on the first Calculate click).
    if calculating or st_module.session_state.get("results"):
        st_module.session_state.quick_start_dismissed = True

    if st_module.session_state.quick_start_dismissed:
        return

    col1, col2 = st_module.columns([20, 1])
    with col1:
        st_module.markdown(
            "### Start here\n"
            "1. Pick a question below (or a proposal from the picker)\n"
            "2. Click **Calculate Impact**\n"
            "3. Read the headline deficit number and the **Validation evidence** card\n\n"
            "Optional depth: Distribution, Economic Effects, and Scoring Models tabs."
        )
    with col2:
        if st_module.button("✕", key="dismiss_quick_start"):
            st_module.session_state.quick_start_dismissed = True
            st_module.rerun()

    # Lead with one featured card, then a compact second row.
    featured = _QUICK_START_CARDS[0]
    featured_cols = st_module.columns(1)
    _render_quick_start_card(st_module, featured_cols[0], featured)

    st_module.caption("More examples")
    cards = list(_QUICK_START_CARDS[1:4])
    cols = st_module.columns(len(cards))
    for col, card in zip(cols, cards, strict=True):
        _render_quick_start_card(st_module, col, card)

    with st_module.expander("More policy questions", expanded=False):
        more = list(_QUICK_START_CARDS[4:])
        more_cols = st_module.columns(len(more))
        for col, card in zip(more_cols, more, strict=True):
            _render_quick_start_card(st_module, col, card)

    st_module.markdown("---")


# ---------------------------------------------------------------------------
# Page shell (multipage router)
# ---------------------------------------------------------------------------
#
# Before the ask-first redesign this module owned ``run_main_app``: a single
# ``st.tabs`` call plus a global ``with st.sidebar`` block. ``app.py`` is now an
# ``st.navigation`` router and each surface in ``app_pages/`` renders itself, so
# what remains here are the pieces every page shares.


def bootstrap_page(st_module: Any) -> None:
    """Per-run bootstrap shared by every page.

    Seeds declared session-state defaults before any widget is constructed and
    injects the accessibility CSS + skip-to-content link. Idempotent, and safe
    to call once per page render.
    """
    initialize_session_state(st_module)
    inject_a11y_styles(st_module)


CLASSROOM_BLURB = (
    "**Interactive assignments for Public Economics courses.**\n\n"
    "7 guided assignments with hints, auto-grading, and PDF export for student "
    "submissions. Covers Laffer curves, TCJA, distributional analysis, and more.\n\n"
    "[➡️ Open Classroom Mode](?mode=classroom)"
)
