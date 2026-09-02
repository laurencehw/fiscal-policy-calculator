"""
Results summary rendering — and the one place the result numbers are derived.

``summarize_result`` is the single implementation of "what does this run say?".
:class:`components.results.ScoredResult` wraps its output; every surface
(headline, Key Metrics, decomposition, Copy Summary, CSV, text export, share
link) renders from that one summary, so they cannot drift apart.

Two rules this module enforces, stated once and applied everywhere:

1. **Sign convention: positive increases the deficit, negative reduces it.**
2. **The headline is the conventional score** (static + behavioral). Dynamic
   scoring never moves it; it adds a labeled "Dynamic view" showing revenue
   feedback, debt service, and the dynamic total. See
   ``fiscal_model/ui/tabs/dynamic_scoring.py`` for the shared computation.
"""

from __future__ import annotations

import re
from datetime import date
from html import escape
from types import SimpleNamespace
from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from fiscal_model.spending_outlays import IMMEDIATE, account_class_label
from fiscal_model.ui.a11y import (
    ChartDescription,
    format_currency_rows,
    render_accessible_chart,
)
from fiscal_model.ui.charts import apply_base_layout, horizontal_legend
from fiscal_model.ui.helpers import unescape_markdown_dollars
from fiscal_model.ui.share_links import build_share_url

#: Stated once, rendered under the headline on every result panel.
SIGN_CONVENTION_CAPTION = (
    "Sign convention: **+ increases the deficit**, − reduces it. "
    "The same convention is used in every chart, metric and export below."
)

DEFAULT_BASELINE_VINTAGE = "CBO Feb 2026"


# ---------------------------------------------------------------------------
# Derivation — the single source of the numbers
# ---------------------------------------------------------------------------


def _window_label(result: Any) -> tuple[int, int, str]:
    """Return ``(start, end, "FY2026-FY2035")`` for the scored budget window."""
    try:
        start = int(result.baseline.start_year)
        end = start + len(result.baseline.years) - 1
    except Exception:
        start, end = 0, 0
    if not start:
        return 0, 0, "10-year budget window"
    return start, end, f"FY{start}–FY{end}"


def _resolve_tier(policy_name: str | None, cbo_score_map: dict | None) -> tuple[str, str]:
    """Classify a run into the maturity tier the app promises to report.

    ``calibrated`` — a preset whose specialized validator was tuned to
    reproduce the official decomposition (agreement is by construction).
    ``benchmarked`` — an official score exists but no calibrated validator.
    ``generic`` — bottom-up from SOI with no official counterpart; the
    genuinely out-of-sample tier.
    """
    try:
        from fiscal_model.ui.preset_validation import PRESET_TO_SCORECARD_ID

        if policy_name and policy_name in PRESET_TO_SCORECARD_ID:
            return "calibrated", "Calibrated reference"
    except Exception:
        pass
    if policy_name and cbo_score_map and policy_name in cbo_score_map:
        return "benchmarked", "Benchmarked preset"
    return "generic", "Generic · uncalibrated"


def _nearest_benchmark(
    headline: float,
    policy_name: str | None,
    cbo_score_map: dict | None,
) -> dict[str, Any] | None:
    """Exact benchmark for this policy, else the nearest validated one.

    "Nearest" is the same-signed official score closest in magnitude: a
    deficit-reducing custom policy is anchored against deficit-reducing
    benchmarks, never against a $4.6T tax cut that happens to be numerically
    close in absolute distance.
    """
    if not cbo_score_map:
        return None

    def _entry(name: str, data: dict, *, exact: bool) -> dict[str, Any]:
        return {
            "name": name,
            "official_billions": float(data.get("official_score", 0.0)),
            "source": str(data.get("source", "")),
            "source_date": str(data.get("source_date", "")),
            "source_url": data.get("source_url"),
            "notes": str(data.get("notes", "")),
            "is_exact": exact,
        }

    if policy_name and policy_name in cbo_score_map:
        return _entry(policy_name, cbo_score_map[policy_name], exact=True)

    if headline == 0:
        return None
    same_sign = [
        (name, data)
        for name, data in cbo_score_map.items()
        if float(data.get("official_score", 0.0)) * headline > 0
    ]
    if not same_sign:
        return None
    name, data = min(
        same_sign,
        key=lambda item: abs(abs(float(item[1].get("official_score", 0.0))) - abs(headline)),
    )
    return _entry(name, data, exact=False)


#: Narrower than this ($B over the whole window) is not a range, it is the
#: point estimate printed twice.
_MIN_BAND_WIDTH_BILLIONS = 0.1

#: Shown in place of the range when no honest one exists. Deliberately says
#: only what is true on every path that reaches it — the behavioural channel is
#: zero *and* the engine's uncertainty path is flat. It must not assert that
#: the score is a calibrated reference: spending runs, custom policies and any
#: near-zero score land here too (Cursor review, 2026-09-01).
_NO_BAND_REASON = (
    "No sensitivity range: nothing in this score varies independently of the "
    "point estimate — the behavioural channel is zero and the model's "
    "uncertainty path is flat — so a range would print the same number twice."
)


def _sensitivity_band(
    result: Any,
    policy: Any,
    *,
    static_total: float,
    behavioral_total: float,
    is_spending: bool,
) -> tuple[tuple[float, float] | None, str]:
    """ETI ±0.1 band around the conventional score, or the engine's own band.

    Reported for generic runs where the behavioral parameter is the dominant
    uncertainty. Calibrated presets embed their behavioral response in the
    calibration, so their band comes from the engine's uncertainty path.

    That second sentence described the intent but not the code until
    2026-09-01. The ETI branch was entered on ``taxable_income_elasticity``
    alone — which every ``TaxPolicy`` subclass inherits at 0.25 — while the
    calibrated module factories zero the *offset* rather than the elasticity
    (``tcja.estimate_behavioral_offset`` returns 0.0 outright; estate, payroll,
    AMT and PTC set their own elasticities to 0.0). Flexing an elasticity that
    multiplies a zero offset moves nothing, so both ends landed on the point
    estimate and Explore printed ``Sensitivity range: $+4,581.9B to
    $+4,581.9B (ETI 0.15–0.35)`` — a band of zero width, presented as a range
    (external UI review, 2026-09-01). Credits presets were the tell: they
    escape it only because their factory zeroes the elasticity itself.

    The ETI branch now requires a behavioral channel that actually responds.
    Returns ``(None, reason)`` when no honest band can be drawn, so the caller
    can say why rather than print a width that is not there.
    """
    base_eti = getattr(policy, "taxable_income_elasticity", None)
    if base_eti and not is_spending and base_eti > 0 and behavioral_total:
        eti_low = max(0.05, base_eti - 0.1)
        eti_high = base_eti + 0.1
        low = static_total + behavioral_total * (eti_low / base_eti)
        high = static_total + behavioral_total * (eti_high / base_eti)
        if abs(high - low) >= _MIN_BAND_WIDTH_BILLIONS:
            note = f"ETI {eti_low:.2f}–{eti_high:.2f}"
            return (min(low, high), max(low, high)), note
    try:
        low = float(np.asarray(result.low_estimate).sum())
        high = float(np.asarray(result.high_estimate).sum())
    except Exception:
        # The arrays could not be read, so nothing is known about the width.
        # Say nothing rather than explain an absence we cannot account for.
        return None, ""
    if abs(high - low) < _MIN_BAND_WIDTH_BILLIONS:
        return None, _NO_BAND_REASON
    return (min(low, high), max(low, high)), "model uncertainty band"


def summarize_result(
    result_data: dict[str, Any],
    *,
    dynamic_scoring: bool | None = None,
    dynamic_view: Any = None,
    cbo_score_map: dict[str, dict[str, Any]] | None = None,
    baseline_vintage: str | None = None,
) -> dict[str, Any]:
    """Derive every number and label a result surface needs, exactly once.

    ``dynamic_view`` is the :class:`~fiscal_model.ui.tabs.dynamic_scoring.
    DynamicView` produced by the calculation pipeline. When it is absent the
    run is reported as conventional-only — deliberately, rather than falling
    back to the engine's internal feedback model, which is what used to make
    Key Metrics disagree with the Economic Effects tab.
    """
    policy = result_data["policy"]
    result = result_data["result"]
    is_spending = bool(result_data.get("is_spending", False))
    policy_name = result_data.get("policy_name") or getattr(policy, "name", "")

    static_total = float(np.asarray(result.static_deficit_effect).sum())
    behavioral_total = float(np.asarray(result.behavioral_offset).sum())
    per_year = [
        float(value)
        for value in (
            np.asarray(result.static_deficit_effect) + np.asarray(result.behavioral_offset)
        )
    ]
    headline = static_total + behavioral_total

    # "dynamic" means *this run has a dynamic view to show*. Without a macro
    # adapter run there is no feedback number, and claiming the mode anyway is
    # how Key Metrics used to assert $0.0B while another tab reported a figure.
    if dynamic_scoring is None:
        dynamic_scoring = bool(getattr(result, "dynamic_effects", None))
    is_dynamic = bool(dynamic_scoring) and dynamic_view is not None

    feedback = float(getattr(dynamic_view, "feedback", 0.0) or 0.0)
    debt_service = float(getattr(dynamic_view, "debt_service", 0.0) or 0.0)
    dynamic_total = float(getattr(dynamic_view, "dynamic_total", headline) or headline)
    macro_model = getattr(dynamic_view, "model_name", None)

    window_start, window_end, window = _window_label(result)
    tier, tier_label = _resolve_tier(policy_name, cbo_score_map)
    benchmark = _nearest_benchmark(headline, policy_name, cbo_score_map)
    sensitivity, sensitivity_note = _sensitivity_band(
        result,
        policy,
        static_total=static_total,
        behavioral_total=behavioral_total,
        is_spending=is_spending,
    )

    status_text = None
    try:
        from fiscal_model.policy_status import get_policy_status

        status = get_policy_status(policy_name)
        if status is not None:
            status_text = f"{status.label} — {status.note}"
    except Exception:
        status_text = None
    if status_text is None:
        status_text = "Hypothetical — user-defined policy, no official status."

    credibility = None
    accuracy_pct = None
    try:
        from fiscal_model.validation.credibility import get_credibility_for_result

        credibility = get_credibility_for_result(
            point_estimate=headline,
            policy_name=policy_name,
            policy=policy,
        )
        if credibility is not None:
            accuracy_pct = float(getattr(credibility, "mean_abs_pct_error", 0.0) or 0.0)
    except Exception:
        credibility = None

    n_years = len(getattr(result, "years", [])) or 10

    return {
        "policy_name": policy_name,
        "display_name": getattr(policy, "name", policy_name),
        "mode": "dynamic" if is_dynamic else "conventional",
        "window": window,
        "window_start": window_start,
        "window_end": window_end,
        "n_years": n_years,
        "headline": headline,
        "static": static_total,
        "behavioral": behavioral_total,
        "feedback": feedback,
        "debt_service": debt_service,
        "dynamic_total": dynamic_total,
        "macro_model": macro_model,
        "per_year": per_year,
        "tier": tier,
        "tier_label": tier_label,
        "benchmark": benchmark,
        "baseline_vintage": baseline_vintage or DEFAULT_BASELINE_VINTAGE,
        "policy_status": status_text,
        "sensitivity": sensitivity,
        "sensitivity_note": sensitivity_note,
        "is_spending": is_spending,
        "accuracy_pct": accuracy_pct,
        "credibility": credibility,
    }


def ensure_summary(
    result_data: dict[str, Any],
    scored: Any = None,
    *,
    cbo_score_map: dict[str, dict[str, Any]] | None = None,
) -> Any:
    """Return the passed ``ScoredResult``, or derive a throwaway one."""
    if scored is not None:
        return scored
    return SimpleNamespace(**summarize_result(result_data, cbo_score_map=cbo_score_map))


# ---------------------------------------------------------------------------
# Small HTML builders (pinned by tests/test_results_summary_formatting.py)
# ---------------------------------------------------------------------------


def _build_interpretation_html(
    *,
    final_deficit_total: float,
    n_years: int,
    annual_avg: float,
    pct_of_gdp: float,
) -> str:
    """Build plain-English interpretation HTML without markdown currency parsing.

    Every branch quotes *two* amounts, which in plain markdown would be a KaTeX
    inline-math span. It is safe here — and only here — because the caller wraps
    the result in ``<p>…</p>`` and renders it with ``unsafe_allow_html=True``:
    an HTML block is opaque to ``remark-math``, so no math tokenizing happens
    inside it. Verified in a browser (Phase 6): the paragraph shows currency and
    the page contains no ``.katex`` node. **Do not** run
    ``escape_markdown_dollars`` over this string — markdown escapes are not
    processed inside an HTML block either, so ``\\$`` would render its backslash.
    """
    if final_deficit_total > 100:
        return (
            "This policy would <strong>add approximately "
            f"${final_deficit_total:,.0f} billion</strong> "
            f"to the federal deficit over {n_years} years, roughly "
            f"<strong>${abs(annual_avg):,.0f}B per year</strong>, or about "
            f"<strong>{pct_of_gdp:.1f}% of GDP annually</strong>."
        )
    if final_deficit_total < -100:
        return (
            "This policy would <strong>reduce the federal deficit by approximately "
            f"${abs(final_deficit_total):,.0f} billion</strong> over {n_years} years, "
            f"roughly <strong>${abs(annual_avg):,.0f}B per year</strong> "
            "in new revenue or savings, or about "
            f"<strong>{pct_of_gdp:.1f}% of GDP annually</strong>."
        )
    if abs(final_deficit_total) > 1:
        direction = "increase" if final_deficit_total > 0 else "decrease"
        return (
            f"This policy would <strong>{direction} the deficit by about "
            f"${abs(final_deficit_total):,.0f} billion</strong> over {n_years} years "
            f"(<strong>${abs(annual_avg):,.0f}B/year</strong>) "
            "with a relatively modest fiscal impact."
        )
    return f"This policy has <strong>negligible fiscal impact</strong> over the {n_years}-year window."


def _build_credibility_html(credibility: Any) -> str:
    """Build a compact validation-evidence card for a result."""
    if credibility is None:
        return ""

    low = getattr(credibility, "uncertainty_low", None)
    high = getattr(credibility, "uncertainty_high", None)
    if low is not None and high is not None:
        range_text = f"${low:+,.0f}B to ${high:+,.0f}B"
    else:
        range_text = "Not available"

    evidence = escape(str(getattr(credibility, "evidence_type", "unknown")).replace("_", " "))
    category = escape(str(getattr(credibility, "category", "Unknown")))
    rating = escape(str(getattr(credibility, "rating_label", "Unknown")))
    holdout = escape(str(getattr(credibility, "holdout_status", "unknown")).replace("_", " "))
    caption = escape(str(getattr(credibility, "caption", "")))
    n_benchmarks = int(getattr(credibility, "n_benchmarks", 0) or 0)
    mean_error = float(getattr(credibility, "mean_abs_pct_error", 0.0) or 0.0)
    limitations = [
        escape(str(item))
        for item in list(getattr(credibility, "limitations", []) or [])[:3]
    ]
    limitation_items = "".join(f"<li>{item}</li>" for item in limitations)
    if not limitation_items:
        limitation_items = "<li>No category-specific limitations are recorded.</li>"

    return f"""
    <div class="fpc-evidence-card">
        <div class="fpc-evidence-card-title">
            Validation evidence
        </div>
        <div style="display:flex; flex-wrap:wrap; gap:0.75rem; margin-top:0.45rem;">
            <span><strong>{rating}</strong> confidence</span>
            <span>Category: <strong>{category}</strong></span>
            <span>Benchmarks: <strong>{n_benchmarks}</strong></span>
            <span>Mean error: <strong>±{mean_error:.1f}%</strong></span>
            <span>Range: <strong>{range_text}</strong></span>
        </div>
        <p style="margin:0.55rem 0 0.35rem 0; color:#3d4654;">
            {caption}
        </p>
        <p style="margin:0.25rem 0; color:#526071;">
            Evidence type: <strong>{evidence}</strong> · Holdout status: <strong>{holdout}</strong>.
            This is a model-validation range, not an official CBO/JCT score.
            Calibrated reconstructions (~5% mean) and out-of-sample predictions (~8% mean)
            are different tiers — do not collapse them into one accuracy claim.
        </p>
        <details style="margin-top:0.45rem;">
            <summary style="cursor:pointer; color:#334155; font-weight:600;">Known caveats</summary>
            <ul style="margin:0.45rem 0 0 1.15rem; padding:0;">{limitation_items}</ul>
        </details>
    </div>
    """


def _dataframe(st_module: Any, frame: Any, **kwargs: Any) -> None:
    """``st.dataframe`` at full width, without the deprecated kwarg.

    ``use_container_width`` renders a deprecation notice inside the app from
    Streamlit 1.56; the fallback keeps the UI tests' ``st_module`` fakes working.
    """
    try:
        st_module.dataframe(frame, width="stretch", **kwargs)
    except TypeError:  # pragma: no cover - older Streamlit / test fakes
        st_module.dataframe(frame, **kwargs)


def _tier_badge_html(scored: Any) -> str:
    """Render the wireframe's tier chip: tier · calibration · accuracy."""
    tier = getattr(scored, "tier", "generic")
    label = escape(str(getattr(scored, "tier_label", tier)).upper())
    accuracy = getattr(scored, "accuracy_pct", None)
    parts = [label]
    if accuracy is not None:
        parts.append(f"±{float(accuracy):.1f}%")
    mode = str(getattr(scored, "mode", "conventional"))
    parts.append("DYNAMIC VIEW ON" if mode == "dynamic" else "CONVENTIONAL")
    background = "#eef6ee" if tier == "calibrated" else "#f4f2ec"
    color = "#2f6b34" if tier == "calibrated" else "#6b5b2f"
    body = " · ".join(parts)
    return (
        f'<div style="display:inline-block; background:{background}; color:{color}; '
        'font-size:0.72rem; font-weight:700; letter-spacing:0.08em; '
        'padding:0.2rem 0.55rem; border-radius:0.3rem; margin-bottom:0.4rem;">'
        f"{body}</div>"
    )


# ---------------------------------------------------------------------------
# Composable render blocks
# ---------------------------------------------------------------------------


def spend_out_caption(policy: Any, result: Any) -> str:
    """One line saying that outlays lag authority, and by how much.

    Spending presets book budget authority and spend it out on the profile
    their account type implies, so the headline is smaller than the funding
    the program provides. That is a user-visible change in the number, and it
    ships with its explanation rather than in silence. Returns ``""`` for
    anything that is not a spending policy or that outlays immediately.
    """
    account_class = getattr(policy, "outlay_account_class", None)
    if not account_class or account_class == IMMEDIATE:
        return ""
    authority = float(getattr(result, "total_budget_authority", 0.0) or 0.0)
    if authority == 0.0:
        return ""
    outlays = float(np.sum(result.static_spending_effect))
    ratio = outlays / authority
    return (
        f"Spend-out: outlays follow the **{account_class_label(account_class)}** "
        f"profile, so \\${authority:+,.1f}B of budget authority becomes "
        f"\\${outlays:+,.1f}B of outlays inside the window - a "
        f"{ratio:.2f} 10-year outlay/authority ratio. Change it under "
        f"Economic parameters."
    )


def render_headline_block(st_module: Any, scored: Any, result_data: dict[str, Any]) -> None:
    """Tier badge, headline number, interpretation, sensitivity, provenance."""
    policy = result_data["policy"]
    result = result_data["result"]
    headline = float(scored.headline)

    # Colours live in ``ui/styles.py`` (light) and ``components/chrome.py``
    # (dark), keyed off these classes. Inline hex here would survive the
    # dark-mode overlay's text rule and leave the headline number — the single
    # most-read figure in the app — white on a pale grey card.
    if headline < 0:
        impact_class, impact_label = "fpc-impact-down", "Deficit Reduction"
    elif headline > 0:
        impact_class, impact_label = "fpc-impact-up", "Deficit Increase"
    else:
        impact_class, impact_label = "fpc-impact-flat", "No Change"

    st_module.markdown(_tier_badge_html(scored), unsafe_allow_html=True)
    st_module.markdown(
        f"""
        <div class="fpc-result-card">
            <h3 class="fpc-result-card-title">{escape(scored.window)} Deficit Impact (conventional)</h3>
            <h1 class="fpc-impact {impact_class}">
                ${headline:+,.1f}B
            </h1>
            <p class="fpc-result-card-note">
                {impact_label}{' (Spending Policy)' if scored.is_spending else ''}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st_module.caption(SIGN_CONVENTION_CAPTION)

    spend_out = spend_out_caption(policy, result)
    if spend_out:
        st_module.caption(spend_out)

    credibility_html = _build_credibility_html(getattr(scored, "credibility", None))
    if credibility_html:
        st_module.markdown(credibility_html, unsafe_allow_html=True)

    st_module.code(build_headline_copy(scored), language=None)

    band = getattr(scored, "sensitivity", None)
    note = getattr(scored, "sensitivity_note", "")
    if band and abs(band[1] - band[0]) >= _MIN_BAND_WIDTH_BILLIONS:
        # ``<small>`` is an *inline* tag, so this is a markdown paragraph with
        # raw HTML in it — not an opaque HTML block like the interpretation
        # card. KaTeX therefore does parse it, and unescaped
        # ``$+4,581.9B to $`` rendered as an italic math span with the dollar
        # signs eaten (caught in a browser, Phase 6). Escape the currency.
        st_module.markdown(
            f"<small><b>Sensitivity range:</b> \\${band[0]:+,.1f}B "
            f"to \\${band[1]:+,.1f}B"
            + (f" ({escape(note)})" if note else "")
            + "</small>",
            unsafe_allow_html=True,
        )
    elif note:
        # Belt and braces: a degenerate pair is truthy, and "X to X" reads as
        # a broken widget rather than as the absence of a range. Say which it
        # is instead.
        st_module.caption(note)

    benchmark = getattr(scored, "benchmark", None)
    if benchmark and benchmark.get("is_exact"):
        official = benchmark["official_billions"]
        error_pct = ((headline - official) / abs(official) * 100) if official else 0.0
        st_module.markdown(
            f"<p><small>📌 <b>{escape(benchmark['source'])} estimate:</b> "
            f"${official:+,.0f}B &nbsp;·&nbsp; <b>Model:</b> ${headline:+,.0f}B "
            f"&nbsp;·&nbsp; <b>Difference:</b> {error_pct:+.1f}%</small></p>",
            unsafe_allow_html=True,
        )
    elif benchmark:
        st_module.caption(
            "No official score exists for this exact policy — nearest validated "
            f"benchmark: {benchmark['name']} , ${benchmark['official_billions']:+,.0f}B "
            f"({benchmark['source']}, {benchmark['source_date']})."
        )

    st_module.caption(
        f"Scored against the {scored.baseline_vintage} baseline over "
        f"{scored.window} · policy status: {scored.policy_status}"
    )

    n_years = int(scored.n_years)
    annual_avg = headline / n_years if n_years else headline
    try:
        gdp_baseline = float(result.baseline.nominal_gdp[0]) or 30_000.0
    except Exception:
        gdp_baseline = 30_000.0
    pct_of_gdp = abs(annual_avg) / gdp_baseline * 100
    st_module.markdown(
        "<p>"
        + _build_interpretation_html(
            final_deficit_total=headline,
            n_years=n_years,
            annual_avg=annual_avg,
            pct_of_gdp=pct_of_gdp,
        )
        + "</p>",
        unsafe_allow_html=True,
    )
    del policy


def render_dynamic_view_block(st_module: Any, scored: Any) -> None:
    """The labeled Dynamic view — feedback, debt service, dynamic total.

    Rendered only when dynamic scoring is on. The three numbers are the ones
    :func:`~fiscal_model.ui.tabs.dynamic_scoring.compute_dynamic_view` produced
    for this run; the Economic Effects tab prints the identical set.
    """
    if str(getattr(scored, "mode", "conventional")) != "dynamic":
        return
    st_module.subheader("🌍 Dynamic view")
    st_module.caption(
        "The headline above stays conventional. This block shows what macro "
        f"feedback would add or subtract, from {scored.macro_model or 'the macro adapter'}. "
        "Debt service is netted against feedback here and on the Economic "
        "Effects tab — CBO's dynamic analyses charge the interest cost of the "
        "added deficit against growth feedback."
    )
    d1, d2, d3 = st_module.columns(3)
    with d1:
        st_module.metric(
            "Revenue Feedback (10Y)",
            f"${scored.feedback:+,.1f}B",
            help="Additional revenue from macro feedback. Subtracted from the conventional score.",
        )
    with d2:
        st_module.metric(
            "Debt Service (10Y)",
            f"${scored.debt_service:+,.1f}B",
            help="Interest cost of the added deficit (positive = adds to the deficit).",
        )
    with d3:
        st_module.metric(
            "Dynamic Total (10Y)",
            f"${scored.dynamic_total:+,.1f}B",
            help="Conventional − feedback + debt service. Not the headline.",
        )


def render_metrics_block(st_module: Any, scored: Any, result_data: dict[str, Any]) -> None:
    """Key Metrics, the Dynamic view, and the decomposition waterfall."""
    result = result_data["result"]
    static_total = float(scored.static)
    behavioral_total = float(scored.behavioral)
    headline = float(scored.headline)
    year1 = float(scored.per_year[0]) if scored.per_year else 0.0

    st_module.subheader("📊 Key Metrics")
    m1, m2 = st_module.columns(2)
    with m1:
        st_module.metric(
            "Static Deficit Effect (10Y)",
            f"${static_total:+.1f}B",
            help="Static effect on the deficit before behavioral and macro feedback (positive = deficit increase).",
        )
    with m2:
        behavioral_pct = (
            abs(behavioral_total) / abs(static_total) * 100 if static_total else 0.0
        )
        st_module.metric(
            "Behavioral Response (10Y)",
            f"${behavioral_total:+.1f}B",
            delta=f"{behavioral_pct:.0f}% of static",
            delta_color="off",
            help="Micro behavioral response (e.g., ETI / realizations). Positive increases deficit vs static.",
        )

    m3, m4 = st_module.columns(2)
    with m3:
        # One feedback number app-wide: the macro adapter's, computed by
        # dynamic_scoring.compute_dynamic_view. A static run says so rather
        # than asserting $0.0B while the Economic Effects tab reports its own.
        if str(getattr(scored, "mode", "conventional")) == "dynamic":
            st_module.metric(
                "Revenue Feedback (10Y)",
                f"${scored.feedback:+.1f}B",
                help=(
                    f"From {scored.macro_model or 'the macro adapter'} — the same "
                    "number the Economic Effects tab shows. Shown separately "
                    "from the headline, which stays conventional."
                ),
            )
        else:
            st_module.metric(
                "Revenue Feedback (10Y)",
                "Not included",
                help=(
                    "This score is static + behavioral only. Turn on dynamic "
                    "scoring beside the Score button to add the Dynamic view."
                ),
            )
    with m4:
        st_module.metric(
            "Year 1 Deficit Impact",
            f"${year1:+.1f}B",
            help="Conventional deficit impact in the first budget year.",
        )

    render_dynamic_view_block(st_module, scored)

    st_module.subheader("🧮 Decomposition (10-Year)")
    steps_x = ["Static", "Behavioral", "Conventional"]
    steps_measure = ["relative", "relative", "total"]
    steps_y = [static_total, behavioral_total, headline]

    if str(getattr(scored, "mode", "conventional")) == "dynamic":
        steps_x = [
            "Static",
            "Behavioral",
            "Conventional",
            "Feedback",
            "Debt service",
            "Dynamic total",
        ]
        steps_measure = ["relative", "relative", "total", "relative", "relative", "total"]
        steps_y = [
            static_total,
            behavioral_total,
            headline,
            -float(scored.feedback),
            float(scored.debt_service),
            float(scored.dynamic_total),
        ]

    fig_waterfall = go.Figure(
        go.Waterfall(
            orientation="v",
            measure=steps_measure,
            x=steps_x,
            y=steps_y,
            text=[f"${v:+.0f}B" for v in steps_y],
            textposition="outside",
            increasing={"marker": {"color": "#dc3545"}},
            decreasing={"marker": {"color": "#28a745"}},
            totals={"marker": {"color": "#1f77b4"}},
        )
    )
    apply_base_layout(
        fig_waterfall,
        margin=dict(l=20, r=20, t=10, b=10),
        height=320,
        yaxis_title="Deficit Impact ($B, + = increases deficit)",
        showlegend=False,
    )
    render_accessible_chart(
        st_module,
        fig_waterfall,
        ChartDescription(
            title="Deficit Impact Decomposition",
            summary=(
                "Waterfall chart decomposing the deficit impact from static "
                "scoring through behavioral and (when enabled) dynamic "
                "effects. Positive bars increase the deficit; negative bars "
                "decrease it. The headline is the conventional total."
            ),
            data_rows=format_currency_rows(zip(steps_x, steps_y)),
        ),
    )
    del result


def render_context_block(
    st_module: Any,
    scored: Any,
    result_data: dict[str, Any],
    cbo_score_map: dict[str, dict[str, Any]],
) -> None:
    """Official benchmark card, or the distribution-context fallback."""
    policy = result_data["policy"]
    benchmark = getattr(scored, "benchmark", None)
    headline = float(scored.headline)

    if benchmark and benchmark.get("is_exact"):
        st_module.subheader("🏛️ Official Benchmark")
        official = benchmark["official_billions"]
        error_pct = ((headline - official) / abs(official) * 100) if official else 0.0
        abs_error = abs(error_pct)

        if abs_error <= 5:
            icon, rating = "🎯", "Excellent"
        elif abs_error <= 10:
            icon, rating = "✅", "Good"
        elif abs_error <= 15:
            icon, rating = "⚠️", "Acceptable"
        else:
            icon, rating = "❌", "Needs Review"

        c1, c2 = st_module.columns(2)
        with c1:
            st_module.metric(
                f"Official ({benchmark['source']})",
                f"${official:+,.0f}B",
                delta=f"{error_pct:+.1f}% error",
                delta_color="off",
            )
        with c2:
            st_module.markdown(f"**Accuracy:** {icon} {rating}")
            st_module.caption(benchmark.get("notes", ""))
            if getattr(scored, "tier", "") == "calibrated":
                st_module.caption(
                    "ℹ️ Calibrated to reproduce this benchmark — agreement is "
                    "by construction, not an independent test. See the "
                    "Validation tab for the out-of-sample tier."
                )
            st_module.caption(
                "Compared against the conventional score, so the comparison is "
                "unchanged by the dynamic-scoring toggle."
            )
    else:
        st_module.subheader("👥 Distribution Context")
        affected = getattr(policy, "affected_taxpayers_millions", 0) or 0
        if affected > 0:
            st_module.metric("Affected Taxpayers", f"{affected:.2f} Million")
            if hasattr(policy, "avg_taxable_income_in_bracket"):
                st_module.metric(
                    "Avg Income of Affected",
                    f"${policy.avg_taxable_income_in_bracket:,.0f}",
                )
        else:
            st_module.info("No distribution data available for this policy type.")
    del cbo_score_map


def render_charts_block(st_module: Any, scored: Any, result_data: dict[str, Any]) -> None:
    """Year-by-year and cumulative deficit charts."""
    result = result_data["result"]
    years = result.baseline.years
    df_timeline = pd.DataFrame({"Year": years, "Deficit Impact": list(scored.per_year)})

    c_chart1, c_chart2 = st_module.columns(2)

    with c_chart1:
        st_module.subheader("Year-by-Year Deficit Impact")
        fig_timeline = go.Figure()
        fig_timeline.add_trace(
            go.Bar(
                x=df_timeline["Year"],
                y=df_timeline["Deficit Impact"],
                marker_color=[
                    "#dc3545" if v > 0 else "#28a745" if v < 0 else "#999"
                    for v in df_timeline["Deficit Impact"]
                ],
            )
        )
        apply_base_layout(
            fig_timeline,
            margin=dict(l=20, r=20, t=20, b=20),
            height=300,
            xaxis_title=None,
            yaxis_title="Deficit Impact ($B)",
        )
        render_accessible_chart(
            st_module,
            fig_timeline,
            ChartDescription(
                title="Year-by-Year Deficit Impact",
                summary=(
                    "Bar chart showing the annual conventional deficit impact "
                    "in billions of dollars across the budget window."
                ),
                data_rows=format_currency_rows(
                    (str(int(year)), float(val))
                    for year, val in zip(df_timeline["Year"], df_timeline["Deficit Impact"])
                ),
            ),
        )

    with c_chart2:
        st_module.subheader("Cumulative Deficit Impact")
        df_timeline = df_timeline.assign(
            Cumulative=df_timeline["Deficit Impact"].cumsum(),
            Cum_Low=np.asarray(result.low_estimate).cumsum(),
            Cum_High=np.asarray(result.high_estimate).cumsum(),
        )

        fig_cum = go.Figure()
        fig_cum.add_trace(
            go.Scatter(
                x=list(df_timeline["Year"]) + list(df_timeline["Year"][::-1]),
                y=list(df_timeline["Cum_High"]) + list(df_timeline["Cum_Low"][::-1]),
                fill="toself",
                fillcolor="rgba(44, 160, 44, 0.15)",
                line=dict(color="rgba(255,255,255,0)"),
                name="Uncertainty range",
                showlegend=True,
            )
        )
        fig_cum.add_trace(
            go.Scatter(
                x=df_timeline["Year"],
                y=df_timeline["Cumulative"],
                mode="lines+markers",
                line=dict(color="#2ca02c", width=3),
                name="Central estimate",
            )
        )
        apply_base_layout(
            fig_cum,
            margin=dict(l=20, r=20, t=20, b=20),
            height=300,
            xaxis_title=None,
            yaxis_title="Cumulative Deficit Impact ($B)",
            legend=horizontal_legend(align="right"),
        )
        render_accessible_chart(
            st_module,
            fig_cum,
            ChartDescription(
                title="Cumulative Deficit Impact",
                summary=(
                    "Line chart with a shaded uncertainty band showing the "
                    "running total deficit impact across the budget window."
                ),
                data_rows=format_currency_rows(
                    (str(int(year)), float(val))
                    for year, val in zip(df_timeline["Year"], df_timeline["Cumulative"])
                ),
            ),
        )
        st_module.caption(
            "Shaded area shows uncertainty range. "
            "Uncertainty grows over time, consistent with CBO methodology."
        )


def render_assumptions_block(st_module: Any, scored: Any, result_data: dict[str, Any]) -> None:
    """Assumptions / data-source columns."""
    policy = result_data["policy"]
    result = result_data["result"]
    with st_module.expander("Assumptions and data sources"):
        a1, a2, a3 = st_module.columns(3)
        with a1:
            st_module.markdown("**Behavioral**")
            if hasattr(policy, "taxable_income_elasticity"):
                st_module.markdown(f"- ETI: {policy.taxable_income_elasticity}")
            if hasattr(policy, "short_run_elasticity") and hasattr(policy, "long_run_elasticity"):
                st_module.markdown(
                    f"- CG elasticity: {policy.short_run_elasticity} "
                    f"(short) / {policy.long_run_elasticity} (long)"
                )
        with a2:
            st_module.markdown("**Data**")
            st_module.markdown("- IRS Statistics of Income")
            st_module.markdown("- FRED Economic Data")
            st_module.markdown(
                f"- {scored.baseline_vintage} baseline, scored over {scored.window}"
            )
        with a3:
            st_module.markdown("**Methodology**")
            st_module.markdown("- Static + behavioral scoring (the headline)")
            if str(getattr(scored, "mode", "")) == "dynamic":
                st_module.markdown(f"- Dynamic view: {scored.macro_model}")
            st_module.markdown(f"- {scored.window} budget window")
            st_module.markdown(
                "- [Full docs](https://github.com/laurencehw/fiscal-policy-calculator/blob/main/docs/METHODOLOGY.md)"
            )
    del result


# ---------------------------------------------------------------------------
# Exports — every artifact carries name, status, vintage, window, tier, mode
# ---------------------------------------------------------------------------


def build_headline_copy(scored: Any) -> str:
    """One-line quick-copy headline (rendered in an ``st.code`` copy box).

    ``st.code`` is literal, and some policy names carry a markdown ``\\$``
    escape for the benefit of the markdown surfaces — so the escape has to come
    back off here, or the line the reader copies and pastes says
    "Carbon Tax (\\$50/ton)".
    """
    direction = "Deficit Reduction" if scored.headline < 0 else "Deficit Increase"
    return unescape_markdown_dollars(
        f"{scored.display_name}: ${scored.headline:+,.1f}B over {scored.window} "
        f"({direction}, conventional score) — {scored.tier_label}, "
        f"{scored.baseline_vintage} baseline — Fiscal Policy Calculator, "
        f"{date.today().strftime('%Y-%m-%d')}"
    )


def _export_metadata_lines(scored: Any, share_url: str | None) -> list[tuple[str, str]]:
    """The provenance block every export carries (acceptance criterion §9.10)."""
    lines = [
        ("Policy", str(scored.display_name)),
        ("Policy status", str(scored.policy_status)),
        ("Baseline vintage", str(scored.baseline_vintage)),
        ("Window", str(scored.window)),
        ("Tier", f"{scored.tier} ({scored.tier_label})"),
        ("Mode", str(scored.mode)),
    ]
    if str(scored.mode) == "dynamic" and scored.macro_model:
        lines.append(("Macro model", str(scored.macro_model)))
    lines.append(("Export date", date.today().isoformat()))
    lines.append(("Model version", "1.0.0"))
    if share_url:
        lines.append(("Share URL", share_url))
    return lines


def build_csv_export(scored: Any, result_data: dict[str, Any], share_url: str | None = None) -> str:
    """CSV with a commented provenance header and the per-year decomposition."""
    result = result_data["result"]
    years = result.baseline.years
    export_data = {
        "Year": years,
        "Static Revenue Effect ($B)": result.static_revenue_effect,
        "Static Spending Effect ($B)": result.static_spending_effect,
        "Static Deficit Effect ($B)": result.static_deficit_effect,
        "Behavioral Offset ($B)": result.behavioral_offset,
        "Conventional Deficit Effect ($B)": list(scored.per_year),
        "Low Estimate ($B)": result.low_estimate,
        "High Estimate ($B)": result.high_estimate,
    }
    if getattr(result, "dynamic_effects", None) is not None:
        export_data["GDP Effect ($B)"] = result.dynamic_effects.gdp_level_change
        export_data["GDP Effect (%)"] = result.dynamic_effects.gdp_percent_change
        export_data["Employment (thousands)"] = result.dynamic_effects.employment_change

    header = "".join(
        f"# {label}: {value}\n" for label, value in _export_metadata_lines(scored, share_url)
    )
    header += (
        "# Sign convention: positive = increases the deficit\n"
        "# Headline: conventional (static + behavioral); dynamic scoring never moves it\n"
    )
    if str(scored.mode) == "dynamic":
        header += (
            f"# Dynamic view: feedback {scored.feedback:+,.1f}B, "
            f"debt service {scored.debt_service:+,.1f}B, "
            f"dynamic total {scored.dynamic_total:+,.1f}B\n"
        )
    header += "# Methodology: Static + behavioral scoring with FRB/US-calibrated dynamic effects\n#\n"
    return header + pd.DataFrame(export_data).to_csv(index=False)


def build_text_summary(scored: Any, result_data: dict[str, Any], share_url: str | None = None) -> str:
    """Plain-text summary used for both the download and the Copy Summary box."""
    policy = result_data["policy"]
    result = result_data["result"]

    meta = "".join(
        f"{label}: {value}\n" for label, value in _export_metadata_lines(scored, share_url)
    )
    if str(scored.mode) == "dynamic":
        feedback_lines = (
            f"\nDynamic view ({scored.macro_model}) — not the headline:\n"
            f"  Revenue Feedback: ${scored.feedback:+,.1f}B\n"
            f"  Debt Service: ${scored.debt_service:+,.1f}B\n"
            f"  Dynamic Total: ${scored.dynamic_total:+,.1f}B\n"
        )
    else:
        feedback_lines = "\n  Revenue Feedback: not included (conventional score)\n"

    text = (
        "FISCAL POLICY IMPACT ANALYSIS\n"
        f"{meta}"
        "\nSign convention: positive = increases the deficit.\n"
        f"\n{scored.window} Deficit Impact (conventional): ${scored.headline:+,.1f}B\n"
        # The static term here is the static *deficit* effect. It used to be
        # labeled "Static Revenue Effect", which is the opposite sign of what
        # was printed (NOTES §4.4 item 5 / §11 item 20).
        f"  Static Deficit Effect: ${scored.static:+,.1f}B\n"
        f"  Behavioral Offset: ${scored.behavioral:+,.1f}B\n"
        f"{feedback_lines}"
        "\nYear-by-Year Breakdown (conventional):\n"
    )
    for year, impact in zip(result.years, scored.per_year):
        text += f"  {year}: ${impact:+,.1f}B\n"

    text += "\nAssumptions:\n"
    if hasattr(policy, "taxable_income_elasticity"):
        text += f"  Elasticity of Taxable Income (ETI): {policy.taxable_income_elasticity}\n"
    if hasattr(policy, "rate_change"):
        text += f"  Rate Change: {policy.rate_change * 100:+.2f}pp\n"
    if hasattr(policy, "affected_income_threshold"):
        text += f"  Income Threshold: ${policy.affected_income_threshold:,.0f}\n"
    band = getattr(scored, "sensitivity", None)
    if band and abs(band[1] - band[0]) >= _MIN_BAND_WIDTH_BILLIONS:
        text += (
            f"  Sensitivity: ${band[0]:+,.1f}B to ${band[1]:+,.1f}B "
            f"({scored.sensitivity_note})\n"
        )
    elif getattr(scored, "sensitivity_note", ""):
        text += f"  Sensitivity: {scored.sensitivity_note}\n"

    benchmark = getattr(scored, "benchmark", None)
    if benchmark:
        kind = "Official benchmark" if benchmark["is_exact"] else "Nearest validated benchmark"
        text += (
            f"\n{kind}: {benchmark['name']} = ${benchmark['official_billions']:+,.0f}B "
            f"({benchmark['source']}, {benchmark['source_date']})\n"
        )

    try:
        from fiscal_model.data.irs_soi import IRSSOIData

        soi_year = max(IRSSOIData().get_data_years_available())
    except Exception:
        soi_year = 2022
    text += (
        f"\nData Sources:\n  - IRS Statistics of Income ({soi_year})\n"
        "  - FRED Economic Data\n"
        f"  - {scored.baseline_vintage} baseline, scored over {scored.window}\n"
    )
    text += (
        "\nMethodology: conventional (static + behavioral) headline; dynamic "
        "scoring is reported as a separate view with FRB/US-calibrated "
        "multipliers and netted debt service.\n"
    )
    # Plain text, downloaded and pasted: markdown escapes carried by policy
    # names have no business in it.
    return unescape_markdown_dollars(text)


def _file_stem(scored: Any) -> str:
    return re.sub(r"[^\w\-]", "_", str(scored.display_name)).strip("_").lower() or "policy"


def render_export_block(st_module: Any, scored: Any, result_data: dict[str, Any]) -> None:
    """CSV / share link / text download, plus the Copy Summary box."""
    with st_module.expander("📥 Export Results", expanded=True):
        # ``scored`` carries the provenance the link stamps: the baseline
        # vintage printed two lines below in the same export, the policy-spec
        # hash, and the scoring mode.
        share_url = build_share_url(result_data=result_data, scored=scored)
        csv_data = build_csv_export(scored, result_data, share_url)
        text_summary = build_text_summary(scored, result_data, share_url)
        stem = _file_stem(scored)

        col1, col2, col3 = st_module.columns(3)
        with col1:
            st_module.download_button(
                label="📊 Download as CSV",
                data=csv_data,
                file_name=f"fiscal_results_{stem}.csv",
                mime="text/csv",
            )
        with col2:
            st_module.markdown("**🔗 Share this result**")
            if share_url:
                st_module.code(share_url, language=None)
                st_module.caption(
                    "Opening this link restores the preset and runs the calculation automatically."
                )
            else:
                st_module.caption(
                    "Share links cover preset tax proposals and preset spending programs. "
                    "Custom policies and microsimulation results require local export."
                )
        with col3:
            st_module.download_button(
                label="📄 Download as Text",
                data=text_summary,
                file_name=f"fiscal_summary_{stem}.txt",
                mime="text/plain",
            )

        st_module.markdown("---")
        st_module.subheader("Copy Summary for Reports")
        st_module.caption("Select all text below and copy to paste into documents:")
        st_module.code(text_summary, language="text")


def render_compare_block(
    st_module: Any,
    scored: Any,
    cbo_score_map: dict[str, dict[str, Any]],
) -> None:
    """Side-by-side comparison against another official score."""
    st_module.markdown("---")
    st_module.subheader("Compare to another proposal")

    compare_presets = list(cbo_score_map.keys())
    if not compare_presets:
        return

    compare_choice = st_module.selectbox(
        "Select a proposal to compare against",
        options=["(none)", *compare_presets],
        key="compare_policy_select",
        help="See how this policy's fiscal impact compares to another.",
        # Display only: the value still keys ``cbo_score_map``. A selectbox
        # option is plain text, so a preset name carrying the markdown ``\$``
        # escape read "Carbon Tax \$50/ton" in the dropdown.
        format_func=unescape_markdown_dollars,
    )
    if compare_choice == "(none)":
        return

    compare_data = cbo_score_map[compare_choice]
    compare_official = compare_data["official_score"]
    headline = float(scored.headline)

    c1, c2, c3 = st_module.columns(3)
    with c1:
        st_module.markdown("**Current policy**")
        st_module.metric(scored.display_name, f"${headline:+,.0f}B")
    with c2:
        st_module.markdown("**Comparison**")
        st_module.metric(
            compare_choice,
            f"${compare_official:+,.0f}B",
            help=f"Official {compare_data['source']} estimate",
        )
    with c3:
        delta = headline - compare_official
        st_module.markdown("**Difference**")
        st_module.metric(
            "Net difference",
            f"${delta:+,.0f}B",
            delta="More costly" if delta > 0 else "Less costly",
            delta_color="inverse" if delta > 0 else "normal",
        )


def render_sensitivity_block(st_module: Any, scored: Any, result_data: dict[str, Any]) -> None:
    """ETI sensitivity table for individual income-tax policies."""
    policy = result_data["policy"]
    st_module.markdown("---")
    with st_module.expander("Sensitivity analysis"):
        is_individual_tax = (
            hasattr(policy, "rate_change")
            and policy.rate_change != 0
            and hasattr(policy, "policy_type")
            and str(getattr(policy.policy_type, "value", "")) == "income_tax"
        )
        if not is_individual_tax:
            st_module.info(
                "Sensitivity analysis is available for policies with rate "
                "changes. Preset policies use pre-calibrated models where "
                "ETI sensitivity is embedded in the calibration."
            )
            return

        st_module.markdown(
            "How would results change with different behavioral assumptions? "
            "The Elasticity of Taxable Income (ETI) is the most influential "
            "parameter for individual income tax policies."
        )
        base_eti = getattr(policy, "taxable_income_elasticity", 0.25) or 0.25
        rows = []
        for eti_val in (0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50):
            scale = eti_val / base_eti if base_eti > 0 else 1.0
            adjusted = float(scored.static) + float(scored.behavioral) * scale
            rows.append(
                {
                    "ETI": eti_val,
                    "10-Year Impact ($B)": round(adjusted, 1),
                    "vs. Central": f"${adjusted - float(scored.headline):+,.0f}B",
                }
            )
        _dataframe(st_module, pd.DataFrame(rows), hide_index=True)
        st_module.caption(
            "Simplified linear projection around the conventional score — "
            "actual model results may differ due to bracket effects and "
            "interaction terms. Central estimate uses ETI = 0.25 "
            "(Saez et al. 2012)."
        )


def render_details_block(
    st_module: Any,
    scored: Any,
    result_data: dict[str, Any],
    cbo_score_map: dict[str, dict[str, Any]],
) -> None:
    """Everything below the fold: charts, assumptions, compare, sensitivity.

    Used by the shared result panel's "Details" deep view so the panel above it
    stays short, and by the legacy Results & Details tab.
    """
    render_charts_block(st_module, scored, result_data)
    st_module.markdown("---")
    render_assumptions_block(st_module, scored, result_data)
    render_compare_block(st_module, scored, cbo_score_map)
    render_sensitivity_block(st_module, scored, result_data)


# ---------------------------------------------------------------------------
# Microsim branch + legacy full-tab composition
# ---------------------------------------------------------------------------


def render_microsim_summary(st_module: Any, result_data: dict[str, Any]) -> None:
    """Render the microsimulation prototype's own summary."""
    st_module.header("🔬 Microsimulation Results")
    st_module.markdown(result_data["source_msg"])

    col1, col2, col3 = st_module.columns(3)
    rev_change = result_data["revenue_change_billions"]

    with col1:
        st_module.metric(
            "Revenue Change (Year 1)",
            f"${rev_change:+.1f}B",
            delta="Revenue Gain" if rev_change > 0 else "Revenue Loss",
            delta_color="normal" if rev_change > 0 else "inverse",
        )
    with col2:
        st_module.metric("Baseline Revenue", f"${result_data['baseline_revenue']:,.1f}B")
    with col3:
        st_module.metric("Reform Revenue", f"${result_data['reform_revenue']:,.1f}B")

    st_module.markdown("---")
    st_module.subheader("👨‍👩‍👧‍👦 Impact by Family Size")
    st_module.caption(
        "Average tax change per household by number of children. (Negative = Tax Cut)"
    )

    dist_kids = result_data["distribution_kids"]
    fig = px.bar(
        dist_kids,
        x="children",
        y="avg_tax_change",
        labels={"children": "Number of Children", "avg_tax_change": "Average Tax Change ($)"},
        color="avg_tax_change",
        color_continuous_scale="RdBu_r",
    )
    render_accessible_chart(
        st_module,
        fig,
        ChartDescription(
            title="Average Tax Change by Family Size",
            summary=(
                "Average tax change per household by number of children "
                "(negative values indicate a tax cut)."
            ),
            data_rows=[
                (f"{int(row['children'])} children", f"${row['avg_tax_change']:+,.0f}")
                for _, row in dist_kids.iterrows()
            ],
        ),
    )

    st_module.info(
        """
        **Why Microsimulation?**
        Aggregate models use average incomes. Microsimulation calculates taxes for *individual households*,
        capturing complex interactions like how the Child Tax Credit phase-out overlaps with other provisions.
        """
    )


def render_results_summary_tab(
    st_module: Any,
    result_data: dict[str, Any],
    cbo_score_map: dict[str, dict[str, Any]],
    scored: Any = None,
) -> None:
    """Legacy full-page composition (the old "Results & Details" tab body).

    The redesigned pages call the blocks directly through
    ``components.results.render_results``; this composition is kept so the tab
    surface, the UI test-suite seams and any embedder keep working.
    """
    if result_data.get("is_microsim"):
        render_microsim_summary(st_module, result_data)
        return

    scored = ensure_summary(result_data, scored, cbo_score_map=cbo_score_map)

    st_module.header("📈 Results Summary")
    render_headline_block(st_module, scored, result_data)

    col_metrics, col_context = st_module.columns([1, 1])
    with col_metrics:
        render_metrics_block(st_module, scored, result_data)
    with col_context:
        render_context_block(st_module, scored, result_data, cbo_score_map)

    st_module.markdown("---")
    render_charts_block(st_module, scored, result_data)

    st_module.markdown("---")
    render_assumptions_block(st_module, scored, result_data)

    st_module.markdown("---")
    render_export_block(st_module, scored, result_data)

    render_compare_block(st_module, scored, cbo_score_map)
    render_sensitivity_block(st_module, scored, result_data)
