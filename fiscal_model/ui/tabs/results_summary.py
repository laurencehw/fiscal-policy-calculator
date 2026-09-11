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
from collections.abc import Sequence
from datetime import date
from html import escape
from types import SimpleNamespace
from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from fiscal_model.amt import AMTPolicy
from fiscal_model.corporate import CORPORATE_MODE_REPORTED, CorporateTaxPolicy
from fiscal_model.credits_core import CreditType, TaxCreditPolicy
from fiscal_model.enforcement import IRSEnforcementPolicy
from fiscal_model.estate import EstateTaxPolicy
from fiscal_model.international import InternationalTaxPolicy
from fiscal_model.payroll import PayrollTaxPolicy
from fiscal_model.pharma import (
    PHARMA_BASELINE,
    DrugPricingPolicy,
    current_law_negotiated_molecules,
    part_d_federal_channels,
)
from fiscal_model.policies import INCOME_MEASURE_AGI, CapitalGainsPolicy, TaxPolicy
from fiscal_model.ptc import (
    CBO_OFFSETTING_SHARE,
    PTC_BASELINE_VINTAGE_LABELS,
    PTC_EXTENSION_GROSS_10YR_BILLIONS,
    PTC_EXTENSION_NET_10YR_BILLIONS,
    PremiumTaxCreditPolicy,
)
from fiscal_model.spending_outlays import IMMEDIATE, account_class_label
from fiscal_model.tax_expenditures_core import (
    BEHAVIORAL_ELASTICITIES,
    SALT_CAP_FLOOR,
    OffsetMagnitudeKind,
    SaltCapBaseline,
    TaxExpenditurePolicy,
    salt_cap_schedule,
)
from fiscal_model.trade import TRADE_BASELINE, TariffPolicy
from fiscal_model.ui.a11y import (
    ChartDescription,
    format_currency_rows,
    render_accessible_chart,
)
from fiscal_model.ui.charts import apply_base_layout, horizontal_legend
from fiscal_model.ui.helpers import (
    escape_markdown_dollars,
    unescape_markdown_dollars,
)
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


def _sensitivity_band(
    result: Any,
    policy: Any,
    *,
    static_total: float,
    behavioral_total: float,
    is_spending: bool,
) -> tuple[tuple[float, float] | None, str]:
    """The headline's accuracy band: this policy class's own Tier 1 error spread.

    **What this replaced, and why (Wave C, H4).** Until 2026-09-11 this returned
    an ETI ±0.1 sweep, falling through to the engine's ``low_estimate`` /
    ``high_estimate`` path when the behavioural channel was zero. Both branches
    were measured across all 53 shipped presets and the three generic shapes,
    and **neither carried any information about accuracy**: for a plain
    ``TaxPolicy`` the headline is ``0.875 × static`` and the ETI sweep's width
    is ``0.8 × 0.125 × static``, so the band was ``0.1 / 0.875 = 11.43%`` of the
    headline for *every* policy, rate and threshold — Flat Tax Reform at
    +$6,239.4B and the Medicare surcharge at −$426.6B drew the identical ribbon
    — and the engine's fallback was a second fixed fraction, 38.0% for climate
    and pharma, 45.6% for estate, credits and payroll, 46.8–47.1% for TCJA, AMT
    and PTC. A restatement of a parameter is not a statement about error.

    What is drawn instead is the **observed out-of-sample error distribution of
    the policy's own class** — the class's mean as the typical miss, its worst
    row as the outer bound, both read off the 26 pre-registered Tier 1 rows and
    nothing else. ``fiscal_model/validation/credibility.py`` holds the band and
    ``validation/policy_classes.py`` the routing, which is the same routing the
    CI per-class gate uses.

    Returns ``(None, reason)`` when the pre-registered battery contains no row
    scoring a policy of this class — which is two thirds of the shipped catalog
    — so the caller says why rather than drawing a width that measures nothing.

    ``result``, ``static_total`` and ``is_spending`` are no longer read. They
    stay in the signature because ``summarize_result`` is the one caller and the
    engine's uncertainty arrays are exactly what this stopped reporting; keeping
    the shape makes that visible in the diff rather than hiding it in a rename.
    """
    from fiscal_model.validation.credibility import band_for_policy
    from fiscal_model.validation.policy_classes import no_tier1_class_reason

    headline = static_total + behavioral_total
    band = band_for_policy(policy)
    if band is None:
        return None, (
            f"No out-of-sample band: {no_tier1_class_reason(policy)}. The 26 "
            "pre-registered rows are the only tier that measures this model's "
            "accuracy against published scores."
        )

    low, high = band.inner_dollars(headline)
    if abs(high - low) < _MIN_BAND_WIDTH_BILLIONS:
        # A near-zero headline, or a class with a 0.0% row. Either way a range
        # here would print the same number twice.
        return None, (
            f"No out-of-sample band: this figure is too small for the "
            f"{band.class_label} class's ±{band.mean_abs_pct_error:.1f}% to "
            "separate from it."
        )

    if band.is_single_row:
        note = (
            f"{band.class_label} · the one pre-registered row misses by "
            f"{band.mean_abs_pct_error:.1f}% (n=1)"
        )
    else:
        note = (
            f"{band.class_label} · {band.n} pre-registered rows, mean "
            f"{band.mean_abs_pct_error:.1f}%, worst "
            f"{band.max_abs_pct_error:.1f}%"
        )
    return (min(low, high), max(low, high)), note


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
            # ``None`` where the policy's class has no out-of-sample row, and it
            # must stay ``None``: ``or 0.0`` would put "± 0.0%" on the tier chip
            # above the headline, which reads as perfect accuracy where the
            # truth is that nothing has been measured.
            raw_accuracy = getattr(credibility, "mean_abs_pct_error", None)
            accuracy_pct = None if raw_accuracy is None else float(raw_accuracy)
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
    """Build a compact accuracy-evidence card for a result.

    Two facts, kept apart on purpose. The **band** is what the out-of-sample
    tier says about policies of this class; the **row** is what this particular
    policy's own scorecard entry says, with the tier it sits in. Collapsing
    them is exactly the "validated within X%" claim CLAUDE.md forbids, and the
    card the H4 lane replaced did collapse them — it printed one category mean
    blended across fitted bookkeeping and unfitted reconstructions, under a
    single rating word.
    """
    if credibility is None:
        return ""

    class_label = getattr(credibility, "class_label", None)
    n_rows = int(getattr(credibility, "n_tier1_rows", 0) or 0)
    mean_error = getattr(credibility, "mean_abs_pct_error", None)
    median_error = getattr(credibility, "median_abs_pct_error", None)
    max_error = getattr(credibility, "max_abs_pct_error", None)
    inside = getattr(credibility, "rows_inside_mean_band", None)
    low = getattr(credibility, "uncertainty_low", None)
    high = getattr(credibility, "uncertainty_high", None)
    outer_low = getattr(credibility, "outer_low", None)
    outer_high = getattr(credibility, "outer_high", None)

    chips: list[str] = []
    if class_label and mean_error is not None:
        chips.append(f"Policy class: <strong>{escape(str(class_label))}</strong>")
        chips.append(
            f"Out-of-sample rows: <strong>{n_rows}</strong>"
            + (" (one observation, not a distribution)" if n_rows <= 1 else "")
        )
        chips.append(f"Mean error: <strong>±{float(mean_error):.1f}%</strong>")
        if n_rows > 1 and median_error is not None and max_error is not None:
            chips.append(
                f"Median <strong>{float(median_error):.1f}%</strong> · worst "
                f"<strong>{float(max_error):.1f}%</strong>"
            )
        if low is not None and high is not None:
            chips.append(f"Typical: <strong>${low:+,.0f}B to ${high:+,.0f}B</strong>")
        if (
            outer_low is not None
            and outer_high is not None
            and max_error is not None
            and float(max_error) > float(mean_error)
        ):
            chips.append(
                f"Worst row: <strong>${outer_low:+,.0f}B to ${outer_high:+,.0f}B</strong>"
            )
        if inside is not None and n_rows > 1:
            chips.append(f"<strong>{inside} of {n_rows}</strong> inside the mean")
    else:
        chips.append("<strong>No out-of-sample band</strong> for this policy class")

    row_tier_label = getattr(credibility, "own_row_tier_label", None)
    row_caption = str(getattr(credibility, "own_row_caption", "") or "")
    if row_tier_label:
        row_html = (
            f'<p style="margin:0.35rem 0 0 0; color:#3d4654;">'
            f"<strong>This policy&#39;s own scorecard row</strong> "
            f"({escape(str(row_tier_label))}): {escape(row_caption)}</p>"
        )
    else:
        row_html = (
            '<p style="margin:0.35rem 0 0 0; color:#526071;">'
            "No scorecard row scores this exact policy.</p>"
        )

    caption = escape(str(getattr(credibility, "caption", "")))
    holdout = escape(str(getattr(credibility, "holdout_status", "unknown")).replace("_", " "))
    limitations = [
        escape(str(item))
        for item in list(getattr(credibility, "limitations", []) or [])[:3]
    ]
    limitation_items = "".join(f"<li>{item}</li>" for item in limitations)
    if not limitation_items:
        limitation_items = "<li>No category-specific limitations are recorded.</li>"

    chip_html = "".join(f"<span>{chip}</span>" for chip in chips)

    return f"""
    <div class="fpc-evidence-card">
        <div class="fpc-evidence-card-title">
            Accuracy evidence
        </div>
        <div style="display:flex; flex-wrap:wrap; gap:0.75rem; margin-top:0.45rem;">
            {chip_html}
        </div>
        <p style="margin:0.55rem 0 0.35rem 0; color:#3d4654;">
            {caption}
        </p>
        {row_html}
        <p style="margin:0.25rem 0; color:#526071;">
            Holdout status: <strong>{holdout}</strong>. This is a model-accuracy
            band, not an official CBO/JCT score. Fitted reference models, unfitted
            reconstructions and out-of-sample predictions are three different
            tiers — only the third is a skill claim, and they never collapse into
            one accuracy number.
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
        f"{ratio:.2f} 10-year outlay/authority ratio. Profiles are fitted on "
        f"CBO options the validation battery does not score."
    )


def tariff_net_caption(policy: Any, result: Any) -> str:
    """One line saying that a tariff headline is net, and of what.

    A tariff's gross customs duty is not its budget effect: CBO, JCT and
    Treasury all score an indirect tax net of an income-and-payroll offset of
    about 25%, because duty paid is income not paid to labour and capital. The
    module used to show the gross figure, so the headline moved by roughly
    40-50% when the offset and the retaliation channel were wired in. That is a
    user-visible change in the number, and it ships with its explanation rather
    than in silence.

    Lane H8 then moved the headline again, and in the other direction: a
    conventional revenue estimate does not net foreign retaliation — Tax
    Foundation prints it in a third column beside its conventional and dynamic
    ones — so retaliation came out of the score and the two dynamic channels
    are named here instead. That is a second user-visible change in the number
    and it ships with its explanation too (Decision 6).

    Computed from the scored result, so it cannot drift from the figure above
    it. Returns ``""`` for anything that is not a tariff.
    """
    if not isinstance(policy, TariffPolicy):
        return ""
    gross = float(np.sum(result.static_revenue_effect))
    if gross == 0.0:
        return ""
    net = gross - float(np.sum(result.behavioral_offset))
    offset_pct = TRADE_BASELINE["income_payroll_offset_rate"]
    years = max(1, len(result.static_revenue_effect))
    gdp_loss = policy.estimate_gdp_feedback_revenue_loss(years)
    retaliation = (
        float(policy.estimate_retaliation_revenue_loss()) * years
        if policy.include_retaliation
        else 0.0
    )
    dynamic = net - gdp_loss - retaliation
    # On a dynamic run the headline above is the *engine's* figure, not this
    # one, and a caption quoting a number the headline does not show is the
    # defect PR #144's review caught on the ordinary-base caption. So the
    # conventional figure says what it is relative to the headline, and the
    # tail says plainly that these two channels are the tariff module's own
    # rather than the dynamic-scoring engine's feedback.
    scored_dynamically = getattr(result, "dynamic_effects", None) is not None
    conventional_label = (
        "conventional receipts - the figure before the dynamic feedback the "
        "headline above applies"
        if scored_dynamically
        else "conventional receipts"
    )
    tail = (
        f" A dynamic estimate would take it further: \\${gdp_loss:,.1f}B of "
        f"receipts lost as output falls"
        + (
            f" and \\${retaliation:,.1f}B lost to retaliation, "
            f"leaving \\${dynamic:,.1f}B"
            if retaliation
            else f", leaving \\${dynamic:,.1f}B"
        )
        + ". Published estimators report those as separate columns and so "
        "does this app - these are the tariff module's own channels, and "
        "neither is the dynamic-scoring engine's feedback."
    )
    return (
        f"Net of offsets: \\${gross:,.1f}B of gross customs duty becomes "
        f"\\${net:,.1f}B of {conventional_label} - a {net / gross:.2f} "
        f"net/gross ratio - after duty avoidance and the {offset_pct:.0%} "
        f"income-and-payroll offset CBO, JCT and Treasury apply to any "
        f"indirect tax. Import demand responds to the whole tariff "
        f"(near-complete border pass-through)." + tail
    )


def pharma_channels_caption(policy: Any, result: Any) -> str:
    """One line saying whose dollar a drug-pricing headline is, and how it was counted.

    Lane W4-pharma moved three of the four shipped drug-pricing presets, two of
    them by more than half, so the numbers ship with their explanation rather
    than in silence (Decision 6). Three things changed and each gets a clause,
    but only if the scored policy actually uses that channel:

    - **The federal share is three channels, re-weighted to the 2025 benefit.**
      Medicare pays Part D through a capitated direct subsidy, cost-based
      catastrophic reinsurance and the low-income subsidy. The IRA's redesign
      cut reinsurance from 80 percent of catastrophic cost to 20, and the 6
      percent cap on the base beneficiary premium pushed the difference onto the
      direct subsidy. Percentages are read off
      :func:`~fiscal_model.pharma.part_d_federal_channels`, so the caption
      cannot drift from the identity that produced the number above it.
    - **Negotiation runs against current law's own cumulative schedule.** The
      set reaches 160 molecules by 2034, not the 20 the module used to assume,
      and the molecules an expansion adds are priced off CMS's three published
      selection cycles as a rank-size ladder rather than as replicas of the
      first ten.
    - **A cost-sharing cap is a cost.** It moves liability onto plans, which
      Medicare subsidises at the statutory rate, so it widens the deficit.

    Returns ``""`` for anything that is not a drug-pricing policy.
    """
    if not isinstance(policy, DrugPricingPolicy):
        return ""

    clauses: list[str] = []

    # The three channels apportion a reduction in *drug cost*. A policy that
    # only moves cost sharing around reduces no drug cost, so it gets no such
    # clause - the same distinction the module draws between the insulin
    # channel's statutory 74.5% and ``part_d_federal_channels``.
    cuts_drug_cost = (
        policy.expand_negotiation
        or policy.reference_pricing
        or policy.manufacturer_discount_pct > 0
    )
    if cuts_drug_cost:
        channels = part_d_federal_channels()
        federal = sum(channels.values())
        clauses.append(
            "Federal share only: of every dollar Part D drug cost falls by, "
            f"Medicare keeps {channels['direct_subsidy']:.0%} through the "
            f"capitated direct subsidy, {channels['reinsurance']:.0%} through "
            f"catastrophic reinsurance and {channels['low_income_subsidy']:.0%} "
            f"through the low-income subsidy - {federal:.0%} in all, weighted to "
            "the IRA's 2025 benefit redesign rather than to the 2023 outturn. "
            "The rest is enrollee premiums and cost sharing, which never reached "
            "the Treasury."
        )

    if policy.expand_negotiation:
        end_year = int(policy.start_year) + int(policy.duration_years) - 1
        clauses.append(
            "Negotiation is scored against current law's own cumulative schedule "
            f"- {current_law_negotiated_molecules(end_year)} molecules by "
            f"{end_year}, not 20 - and the molecules an expansion adds are "
            "priced down CMS's three published selection cycles, so the "
            "hundredth is worth a fraction of the tenth."
        )

    if policy.reference_pricing:
        coverage = (
            PHARMA_BASELINE["rand_us_sales_share_in_comparison"]
            * PHARMA_BASELINE["rand_brand_share_of_contributing_us_sales"]
            / PHARMA_BASELINE["rand_brand_share_of_all_us_sales"]
        )
        clauses.append(
            f"Reference pricing reaches the {coverage:.0%} of US brand-originator "
            "sales RAND's index actually covers - it compares only presentations "
            "sold in both markets - and no utilisation response is modelled."
        )

    if policy.insulin_cap_monthly is not None or policy.oop_cap is not None:
        share = PHARMA_BASELINE["part_d_basic_benefit_federal_share"]
        clauses.append(
            "A cost-sharing cap saves nothing: it converts beneficiary liability "
            f"into plan liability, which Medicare subsidises at {share:.1%}, so "
            "it widens the deficit rather than narrowing it."
        )

    clauses.append("GDP feedback is not in this number.")
    return " ".join(clauses)


def gains_at_death_caption(policy: Any, result: Any) -> str:
    """One line saying what a realization-at-death headline does and does not tax.

    A proposal that ends stepped-up basis does not tax the whole flow of
    unrealized gain transferred by decedents, and no published one claims to:
    appreciated property left to charity generates no taxable gain, the
    section 121 exclusion covers a quarter-million dollars of gain on a
    principal residence, and the Treasury Green Books defer the tax on a
    family-owned and -operated business until the interest is sold. Wiring
    those in moved the headline on this form materially, so it ships with its
    explanation rather than in silence.

    Wave 7 added the clause about the distribution. Every one of those reliefs,
    and the per-donor exclusion itself, is a function of how big the estate is,
    and the model now integrates over a fitted size distribution of estates at
    death rather than five class averages. It moved this form's figures by 1-3
    percent, which is small; the sentence is there because a reader entitled to
    know that an exclusion applies *per decedent* is also entitled to know that
    the decedents differ.

    Wave C added the clause about how many of them there are, and that one is
    not small: the count moved from 408,532 a year to 3.4 million when the
    headcount stopped being a flow of estate dollars, and the figures on this
    form moved 19-31 percent with it.

    Computed by replaying the scorer's own death-channel loop over the same
    window, so it cannot drift from the figure above it. Returns ``""`` for
    anything that is not a step-up-elimination capital-gains policy.
    """
    if not isinstance(policy, CapitalGainsPolicy):
        return ""
    if not policy.eliminate_step_up or not policy.score_gains_at_death:
        return ""

    years = getattr(result, "years", None)
    if years is None or len(years) == 0:
        return ""
    death = 0.0
    for year in years:
        if not policy.is_active(int(year)):
            continue
        phase = policy.get_phase_in_factor(int(year))
        death += (
            policy.estimate_step_up_elimination_revenue(int(year) - policy.start_year)
            * phase
        )
    if death == 0.0:
        return ""

    exclusion = float(policy.step_up_exemption)
    deferral = (
        " Tax on a family-owned and -operated business is deferred until the "
        "interest is sold, so only what is sold inside the window is collected."
        if policy.defer_family_business_gains
        else ""
    )
    per_donor = (
        f" A \\${exclusion:,.0f} per-decedent exclusion then applies to what is "
        f"left, not to the whole gain, and it is subtracted across a fitted "
        f"distribution of estate sizes rather than from an average estate."
        if exclusion > 0
        else " This design states no per-decedent exclusion."
    )
    # Wave C (planning/lanes/HSC_h5_decedent_headcount.md). The count the flow
    # is divided across moved from 408,532 a year to 3.4 million, so a
    # per-decedent exclusion now reaches ordinary decedents rather than being
    # lost inside an average estate eight times too large. It moved this form's
    # figures by 19-31 percent, which is a Decision 6 move, so the sentence
    # ships with them.
    headcount = (
        " Those decedents are counted at an NCHS life-table death rate - about "
        "3.4 million a year - rather than at a flow of estate dollars that "
        "implied 408,532"
        + (
            ", so a fixed exclusion reaches far more of the gain than it used to."
            if exclusion > 0
            else ", so each one carries a gain of ordinary size."
        )
    )
    return (
        f"Gains at death: \\${-death:+,.1f}B of the static score above is "
        f"constructive realization at death - Poterba & Weisbenner's flow of "
        f"unrealized gain transferred by decedents, indexed to household net "
        f"worth. It is not the whole flow: bequests to charity and the "
        f"\\${policy.section_121_exclusion:,.0f} section 121 exclusion on a "
        f"principal residence come out first.{deferral}{per_donor}{headcount} "
        f"Inter-spousal transfers and tangible personal property are already "
        f"outside that flow, so neither is deducted twice."
    )


def realizations_projection_caption(policy: Any, result: Any) -> str:
    """One line saying that the realizations base grows across the window.

    A capital-gains rate change is priced on the income IRS SOI reports as
    taxed at the preferential rates in one tax year, and a ten-year score
    prices ten later years. Realizations are a flow off the accrued-gains stock
    at an observed hazard, so the base grows at the rate the stock already
    grows at; holding it flat would assert a hazard falling by that same rate
    every year. Wiring that in moved this form's headline materially, so it
    ships with its explanation rather than in silence.

    Computed from the policy's own projection factors, so it cannot drift from
    the figure above it. Returns ``""`` for anything with no projected rate
    channel - a policy whose base the caller supplied, or one that changes no
    rate.
    """
    if not isinstance(policy, CapitalGainsPolicy):
        return ""
    if getattr(policy, "_supplied_realizations", True):
        return ""
    if not policy.rate_change and policy.new_rate is None:
        return ""

    years = getattr(result, "years", None)
    if years is None or len(years) == 0:
        return ""
    base = float(getattr(policy, "baseline_realizations_billions", 0.0) or 0.0)
    if base <= 0:
        return ""

    first, last = int(years[0]), int(years[-1])
    try:
        source = policy._baseline_source()
        tax_year = source._resolve_year(policy._data_year(source))
        rate = source.realizations_growth_rate()
    except Exception:  # pragma: no cover - data-availability guard
        return ""
    start = base * policy.realizations_projection_factor(first)
    end = base * policy.realizations_projection_factor(last)
    if start <= 0 or end <= 0:
        return ""

    return (
        f"Realizations base: the rate change is priced on \\${base:,.0f}B of "
        f"gains and qualified dividends taxed at the preferential rates in IRS "
        f"SOI tax year {tax_year}, grown at {rate:.1%} a year - the rate the "
        f"accrued-gains stock it is a flow off already grows at - so the base "
        f"is \\${start:,.0f}B in {first} and \\${end:,.0f}B in {last}. "
        f"Holding it at its {tax_year} level instead would assert a realization "
        f"hazard falling {rate:.1%} a year."
    )


def ptc_repeal_baseline_caption(policy: Any, result: Any) -> str:
    """One line saying which credit a repeal removes, and what CBO nets out of it.

    Repealing IRC section 36B removes the credit, and the credit's cost is a
    published annual path rather than a level: CBO/JCT publication 51298's
    Table 2, outlays plus revenue reductions. It is not a smooth path — the
    ARPA/IRA enhancement lapsed at the end of calendar 2025, so on the February
    2026 baseline the two legs fall by a third between FY2026 and FY2028 before
    recovering. And the gross cost is not the deficit effect of removing it:
    CBO's own decomposition of the nearest section 36B change (publication
    60437) nets an offsetting increase in revenues out of it, primarily people
    returning to employment-based coverage and out of taxable wages.

    Until 2026-09-06 this module removed a fitted $83B/yr growing at 4%/yr, so
    the shipped preset moved by about 14% and Decision 6 says a moved number
    ships with its explanation rather than in silence. Until 2026-09-11 it
    netted a single **transferred** 19.28% out of that path; lane HSD/H11
    prices CBO's channels against the coverage change this repeal causes
    instead, which moved the preset again by about 9% and is why the sentence
    names the enrolment and the per-person rates rather than a ratio.

    Computed from the scored result, so it cannot drift from the figure above
    it. Returns ``""`` for any PTC policy that is not on the baseline path.
    """
    if not isinstance(policy, PremiumTaxCreditPolicy):
        return ""
    if not policy.uses_baseline_credit_path():
        return ""

    years = getattr(result, "years", None)
    if years is None or len(years) == 0:
        return ""
    static = np.asarray(result.static_revenue_effect, dtype=float)
    # A scorer whose window opens before ``policy.start_year`` phases those
    # early years to zero. They are not years of the repeal and must not be
    # reported as the window or mistaken for the trough.
    scored = static > 0
    if not scored.any():
        return ""
    gross = float(static.sum())
    behavioural = float(np.sum(result.behavioral_offset))
    net = gross - abs(behavioural)
    share = abs(behavioural) / gross
    scored_years = [int(year) for year, live in zip(years, scored, strict=False) if live]
    first, last = scored_years[0], scored_years[-1]
    peak_low = float(static[scored].min())

    coverage = policy.coverage_change()
    enrolment = abs(coverage.marketplace_subsidized)

    return (
        f"What a repeal removes: CBO and JCT's own projection of the credit, "
        rf"both legs — \${gross:,.0f}B of outlays plus revenue reductions over "
        f"FY{first}-FY{last} on the "
        f"{PTC_BASELINE_VINTAGE_LABELS.get(policy.baseline_vintage, policy.baseline_vintage)} "
        rf"baseline (publication 51298, Table 2), dipping to \${peak_low:,.0f}B "
        f"in the year the ARPA/IRA enhancement has fully lapsed. Of that, "
        f"{share:.1%} never reaches the deficit — priced channel by channel "
        f"against the {enrolment:,.1f}M subsidized enrollees a year this removes "
        f"(publication 51298, Table 1), at CBO's own rates for each: about "
        rf"\$2,970 a person-year of employment-based coverage regained, "
        rf"\$4,200 a person-year of Medicaid and CHIP, and nothing at all for "
        f"someone who becomes uninsured (publication 60437, which itemises "
        rf"\${PTC_EXTENSION_GROSS_10YR_BILLIONS:,.0f}B gross against "
        rf"\${PTC_EXTENSION_NET_10YR_BILLIONS:,.0f}B net for the nearest scored "
        rf"section 36B change). So the score is \${net:,.0f}B. Until 2026-09-06 "
        rf"this removed a fitted \$83B a year growing at 4%; until 2026-09-11 it "
        f"netted a single transferred {CBO_OFFSETTING_SHARE:.1%} instead of "
        f"pricing the channels."
    )


#: The published figure each SALT reform used to report, and the baseline it
#: was measured on. Keyed by the reform's action, because the two reforms are
#: scored by different houses against different counterfactuals and a caption
#: that named only one of them would be wrong for the other half the time.
_SALT_BASELINE_CONTRAST = {
    "expand": (
        r"Penn Wharton's \$1,169B, which this preset used to report, prices "
        r"the same repeal against a baseline where the \$10,000 cap is "
        r"permanent; the same paper prices it at \$197B against a baseline "
        r"where the cap lapses."
    ),
    "eliminate": (
        r"CBO's \$1,621B (Option 49) prices the same repeal against its "
        r"February 2024 baseline, in which the \$10,000 cap lapsed after 2025 "
        r"and the deduction is uncapped for nine of the ten years scored."
    ),
}

#: The sentence that stops a validation badge from being read as a check on
#: the figure above it. A benchmark is scored on **its own document's**
#: baseline, which for both SALT rows is not current law, so the scorecard's
#: percentage answers a different question from the headline — and a green
#: badge beside a number a third smaller than the published one would
#: otherwise read as a contradiction rather than as two baselines.
_SALT_BENCHMARK_DISCLAIMER = (
    "This model's validation row is scored on that published baseline rather "
    "than on this one, so the percentage it reports is a check on the "
    "benchmark and not on the figure above."
)


def salt_current_law_caption(policy: Any, result: Any) -> str:
    """One line saying which SALT cap the score is measured against.

    Every SALT score is a difference between two worlds, and the number a user
    reads is meaningless without the second one: Penn Wharton prices repealing
    the cap at $1,169B against a permanent $10,000 cap and at $197B against a
    world where it lapses, in the same paper. Until 2026-09-11 this module
    scored a fitted $96B/yr, which is the permanent-$10,000-cap answer, on a
    window in which the cap is $40,400 — so the shipped preset fell by about a
    third when the baseline became current law, and Decision 6 says a moved
    number ships with its explanation rather than in silence.

    Computed from the scored result and from ``salt_cap_schedule`` rather than
    from a stored figure, so the caption cannot drift from the number above it
    and the years it names come from the window actually scored. Returns ``""``
    for any expenditure policy that is not a SALT cap difference.
    """
    if not isinstance(policy, TaxExpenditurePolicy):
        return ""
    if not policy.uses_salt_cap_path():
        return ""
    if policy.salt_baseline is not SaltCapBaseline.CURRENT_LAW:
        return ""

    years = getattr(result, "years", None)
    if years is None or len(years) == 0:
        return ""
    static = np.asarray(result.static_revenue_effect, dtype=float)
    scored = np.abs(static) > 0
    if not scored.any():
        return ""
    scored_years = [int(year) for year, live in zip(years, scored, strict=False) if live]
    first, last = scored_years[0], scored_years[-1]

    total = float(np.sum(np.asarray(result.final_deficit_effect, dtype=float)))
    opening = salt_cap_schedule(first)
    reversion = next(
        (
            year
            for year in scored_years
            if salt_cap_schedule(year).limitation_amount == SALT_CAP_FLOOR
        ),
        None,
    )
    reversion_clause = (
        f", and back to \\${SALT_CAP_FLOOR:,.0f} in {reversion}"
        if reversion is not None
        else ""
    )

    return (
        f"Measured against **current law**, not against the baseline this "
        f"reform's published score uses. P.L. 119-21 sec. 70120 sets the "
        rf"limitation at \${opening.limitation_amount:,.0f} in {first}, rising "
        f"1% a year through 2029 and phasing down by 30 cents per dollar of "
        rf"modified AGI above \${opening.threshold_amount:,.0f}"
        f"{reversion_clause} — so over FY{first}-FY{last} this scores "
        rf"\${abs(total):,.0f}B. {_SALT_BASELINE_CONTRAST[policy.action]} The "
        f"target has not moved — the baseline the app scores on has. "
        f"{_SALT_BENCHMARK_DISCLAIMER}"
    )


def _preset_declares_agi_inclusive(policy_name: str) -> bool:
    """True when a catalog preset of this name declares an AGI-inclusive base.

    Read off ``PRESET_POLICIES`` rather than a hard-coded list of three names,
    so a preset that gains or loses the declaration carries or drops the
    caption with it. Imported lazily: ``app_data`` builds the whole catalog at
    import time and this module is on the landing page's path.
    """
    try:
        from fiscal_model.app_data import PRESET_POLICIES
    except Exception:  # pragma: no cover — defensive
        return False
    entry = PRESET_POLICIES.get(policy_name)
    return bool(entry and entry.get("agi_inclusive_base"))


def _cbo_score_map() -> Any:
    """``CBO_SCORE_MAP``, or an empty mapping when the catalog will not load."""
    try:
        from fiscal_model.app_data import CBO_SCORE_MAP

        return CBO_SCORE_MAP
    except Exception:  # pragma: no cover — defensive
        return {}


def _agi_marginal_ratio(policy: Any) -> float | None:
    """Marginal AGI over marginal taxable income for this policy's own SOI read.

    ``None`` unless the policy was scored on the AGI column by the pooled SOI
    path. Both averages come from the same read over the same filers, so this is
    exactly the factor that separated the two answers, and it lets each caption
    below reconstruct *only its own* change: the base-flag caption reports the
    move on the taxable column, and the column caption picks up where it stops.
    Without it the two would print two different "used to print" figures for one
    preset and neither would be a total this tree produces.
    """
    if getattr(policy, "income_measure", None) != INCOME_MEASURE_AGI:
        return None
    if getattr(policy, "threshold_by_filing_status", None):
        return None
    avg_agi = getattr(policy, "_soi_avg_agi_in_bracket", None)
    avg_taxable = float(getattr(policy, "avg_taxable_income_in_bracket", 0.0) or 0.0)
    if not avg_agi or avg_taxable <= 0:
        return None
    threshold = float(getattr(policy, "affected_income_threshold", 0.0))
    marginal_agi = float(avg_agi) if threshold == 0 else max(0.0, float(avg_agi) - threshold)
    marginal_taxable = avg_taxable if threshold == 0 else max(0.0, avg_taxable - threshold)
    if marginal_agi <= 0 or marginal_taxable <= 0:
        return None
    ratio = marginal_agi / marginal_taxable
    return ratio if ratio > 0 and abs(ratio - 1.0) >= 1e-9 else None


def agi_inclusive_base_caption(policy: Any, result: Any) -> str:
    """One line saying the preset's base came from its source, and what moved.

    Three shipped surtax presets are stated by their own sources on **total
    income above a threshold** — TPC scores the Warren surtax on AGI, and
    Treasury's FY2025 Green Book row applies the Medicare surcharge to
    "investment + wage income" — but no preset carried the attribute, so all
    three were scored on the *ordinary* base, which excludes long-term capital
    gains and qualified dividends. The app therefore printed −$134.6B beside a
    label quoting TPC's −$350B, a 61.5% gap, while the scorecard row for the
    same reform reported 19.0%, because validation had been reading the base
    off the record all along.

    The presets now declare it and the surfaces read it. Three numbers roughly
    doubled, so they ship with their explanation rather than in silence
    (Decision 6).

    Two things this caption must not get wrong, both found in review:

    * **The figure it quotes is the conventional score**, ``static +
      behavioral``, which is what the headline above it shows. Reading
      ``final_deficit_effect`` would subtract revenue feedback in a dynamic run
      and print a number that disagrees with the one it is explaining.
    * **The share comes from the policy**, not from a fourth hand-written copy
      of ``(avg − threshold) × filers``. That copy could not see the
      per-status split path, where four populations face four floors and the
      identity does not hold — so a preset with ``threshold_by_filing_status``
      would have had its "before" figure derived from the pooled base while its
      "now" figure came from the split one.

    The counterfactual is still **computed, not stored**: the ordinary-income
    share multiplies the base and nothing else, so the figure this preset used
    to print is this run's own conventional total times that share. Returns
    ``""`` for every policy whose number did not move.
    """
    if not isinstance(policy, TaxPolicy) or policy.ordinary_income_base:
        return ""
    if not _preset_declares_agi_inclusive(getattr(policy, "name", "")):
        return ""

    # The conventional score, matching ``summarize_result``'s headline. Dynamic
    # scoring never moves that, so this caption does not move with it either.
    total = float(
        np.asarray(result.static_deficit_effect).sum()
        + np.asarray(result.behavioral_offset).sum()
    )
    # On a policy since moved onto SOI's AGI column, report this move on the
    # column it was made on. The column change is its own caption below, and a
    # chain of two honest steps beats two captions each claiming the whole gap.
    column_ratio = _agi_marginal_ratio(policy)
    if column_ratio:
        total /= column_ratio
    if total == 0.0:
        return ""

    # One guard: a zero base, a non-income-tax policy and an unscored policy all
    # come back as 0.0 from the helper, so the checks they used to need here are
    # implied by this one.
    # On the AGI column the recorded base is the AGI one; this caption reports
    # the base-flag move on the taxable column, so it asks for that base's share.
    pref = (
        policy.preferential_share_of_base(base_dollars=policy.marginal_income_dollars())
        if column_ratio
        else policy.preferential_share_of_base()
    )
    if pref <= 0.0:
        return ""
    previous = total * (1.0 - pref)
    threshold = float(policy.affected_income_threshold)

    # A preset with a published score has a document that states its base; the
    # millionaire surtax has none, and the caption must not imply otherwise.
    sourced = getattr(policy, "name", "") in _cbo_score_map()
    provenance = (
        "its own source uses"
        if sourced
        else "this preset declares — a design choice, since no published score of "
        "this reform exists to read a base off"
    )
    return (
        f"Income base: this preset is scored on the **AGI-inclusive** base "
        f"{provenance} — the rate applies to all income above "
        rf"\${threshold:,.0f}, realized capital gains and qualified dividends "
        f"included. On the ordinary-bracket base, which excludes them, it "
        rf"would score \${previous:+,.1f}B rather than the \${total:+,.1f}B "
        f"above: the preferentially taxed income is {pref:.1%} of the marginal "
        f"income here. That is where this preset used to be scored. Nothing in "
        f"the model changed — the presets now carry the base attribute the "
        f"validation records always read, so the app and its own scorecard "
        f"price the same policy."
    )


def agi_income_column_caption(policy: Any, result: Any) -> str:
    """One line saying the base is AGI itself, because the source says AGI.

    IRS SOI Table 1.1's rows are **AGI size classes** and it publishes both an
    AGI column and a taxable-income column. Until 2026-09-10 the generic path
    read the taxable one for every policy, so a surtax whose source states it on
    AGI — TPC scores the Warren surtax on "AGI above \\$2M" — was priced by
    subtracting an AGI threshold from an average of *taxable* income. Same
    returns, same floor, two different quantities.

    The counterfactual is **computed, not stored**: the AGI and taxable averages
    come from the same SOI read over the same filers, so the ratio of the two
    marginal amounts is exactly the factor that separated the two answers, and
    dividing this run's own total by it reconstructs what this policy printed on
    the taxable column.

    It reconstructs **only this change**, which is the convention every caption
    in this file follows: :func:`agi_inclusive_base_caption` undoes the
    preferential correction and nothing else, and
    :func:`income_base_projection_caption` undoes the year projection and
    nothing else. On a policy that moved under two of them, no single caption's
    figure is the number the app printed a month ago, and each says which change
    its own figure isolates.

    Returns ``""`` for every policy scored on the taxable column, for one whose
    base the caller supplied, and for the per-filing-status path, whose ratio is
    not recoverable from an aggregate average (no shipped preset uses it).
    """
    if not isinstance(policy, TaxPolicy) or isinstance(policy, CapitalGainsPolicy):
        return ""
    ratio = _agi_marginal_ratio(policy)
    if ratio is None:
        return ""

    threshold = float(policy.affected_income_threshold)
    total = float(np.sum(result.final_deficit_effect))
    if total == 0.0:
        return ""
    previous = total / ratio

    return (
        f"Income column: the base is **AGI itself**, not taxable income, because "
        f"this policy's own source states the surtax on AGI. IRS SOI Table 1.1 "
        f"publishes both columns by AGI size class, and above "
        rf"\${threshold:,.0f} the AGI average exceeds the taxable-income "
        f"average by {ratio - 1:.1%}. Until 2026-09-10 the generic path "
        f"subtracted the AGI threshold from the *taxable* average — the same "
        f"returns and the same floor, but two different quantities — so this "
        rf"policy printed \${previous:+,.1f}B where it now prints "
        rf"\${total:+,.1f}B. Presets whose sources state taxable income, or a "
        f"base that is neither column, are unchanged."
    )


def income_base_projection_caption(policy: Any, result: Any) -> str:
    """One line saying the generic base is priced in the years being scored.

    The generic income-tax path reads IRS SOI Table 1.1 for its tax year, and a
    ten-year score prices ten later years. The base is projected onto each
    scored year by the ratio of the **scored baseline's own** nominal income
    index between the two years, which on the app's February 2026 vintage
    averages 1.356 across FY2026-2035. Held flat instead — one annual stamped
    on all ten years, ``yr1 == yr10`` to the cent — a FY2026-2035 question is
    answered with a TY2023 base.

    Two things this caption must not get wrong, one of them found in review:

    * **The figures it quotes are the conventional score**, ``static +
      behavioral``, which is what the headline above it shows. On a static run
      that array *is* ``final_deficit_effect``; on a **dynamic** run the final
      path also carries ``revenue_feedback``, a function of the deficit path's
      *level* that does not scale with the static projection factor. Reading it
      would print a "now" figure disagreeing with the one being explained *and*
      reconstruct a "before" this policy never printed.
    * **The counterfactual divides the scored path, it does not rebuild the
      base.** Every year's contribution was multiplied by that year's own
      factor, so dividing each year back out is exact — including on the
      per-status split path, where four populations face four floors and
      ``(avg − threshold) × filers`` does not hold.

    Returns ``""`` for every policy whose base did not come from SOI, and for a
    baseline carrying no GDP path.
    """
    if not isinstance(policy, TaxPolicy) or isinstance(policy, CapitalGainsPolicy):
        return ""
    soi_year = getattr(policy, "soi_base_tax_year", None)
    if soi_year is None:
        return ""

    baseline = getattr(result, "baseline", None)
    years = getattr(result, "years", None)
    if baseline is None or years is None or len(years) == 0:
        return ""
    index = getattr(baseline, "nominal_income_index", None)
    if index is None:
        return ""

    anchor = float(index(int(soi_year)))
    if anchor <= 0:
        return ""

    # The conventional path, for the reason in the docstring: it is the one the
    # projection is linear in, and on a static run it is final_deficit_effect
    # to the cent.
    path = np.asarray(result.static_deficit_effect, dtype=float) + np.asarray(
        result.behavioral_offset, dtype=float
    )
    factors = np.array([float(index(int(year))) / anchor for year in years])
    if not np.all(factors > 0) or np.allclose(factors, 1.0):
        return ""

    total = float(path.sum())
    previous = float(np.sum(path / factors))
    if total == 0.0 or previous == 0.0:
        return ""

    first, last = int(years[0]), int(years[-1])
    return (
        f"Base year: the filer counts and incomes behind this score are IRS SOI "
        f"tax year {int(soi_year)}, and they are projected onto each year being "
        f"scored — {factors[0]:.3f}× in FY{first} rising to {factors[-1]:.3f}× in "
        f"FY{last}, {factors.mean():.3f}× on the window average, off this "
        f"baseline's own nominal path. Held at TY{int(soi_year)} across all ten "
        rf"years, as a flat base, it would score \${previous:+,.1f}B rather than "
        rf"the \${total:+,.1f}B above. The index is the baseline's, not a "
        f"constant, so a run on a different vintage or window projects "
        f"differently."
    )


def cbo_baseline_transcription_caption(policy: Any, result: Any) -> str:
    """Decision 6 for R1: the baseline under this score is CBO's own table now.

    Until 2026-09-11 no vintage's budget levels were transcribed at all under
    the app's default ``use_real_data=True``: they were eleven ``GDP_RATIOS``
    applied to whatever nominal GDP FRED last reported, grown by hand-entered
    rates. ``fiscal_model/data_files/cbo_baseline/`` now carries CBO's own
    published tables, read from ``github.com/US-CBO`` at a pinned commit, and
    the app's February 2026 vintage reproduces CBO's own FY2026-2035 deficit of
    $23,143.3B where the reconstruction returned $29,529.1B.

    The generic income-tax base is projected onto each scored year by a ratio
    of that baseline's nominal path (:func:`income_base_projection_caption`
    explains the projection itself), so **correcting the path moved eight
    shipped presets by 2.97% in static mode**. This caption states that move.

    Three things it is careful about, each a trap a previous caption fell into:

    * **The counterfactual is computed, never stored.** The pre-transcription
      index is rebuilt from ``baseline._HAND_ENTERED_ASSUMPTIONS`` — the same
      literals the module still keeps as its fallback — so the "would have
      read" figure cannot drift away from the number above it.
    * **It quotes the conventional score**, ``static + behavioral``, because
      that is the quantity the projection is linear in; on a dynamic run the
      final path also carries revenue feedback, which does not scale with the
      factor, and reading it would print a figure disagreeing with the
      headline. PR #144's review found exactly that defect.
    * **Only ratios of the index are used**, so the FRED level the old rule
      anchored on cancels and the counterfactual is a pure function of the two
      growth paths.

    Returns ``""`` for a policy whose base did not come from SOI, for a vintage
    with no transcribed economic table, and whenever the two paths agree.
    """
    from fiscal_model.baseline import (
        _ASSUMPTION_FIRST_YEAR,
        _HAND_ENTERED_ASSUMPTIONS,
    )

    if not isinstance(policy, TaxPolicy) or isinstance(policy, CapitalGainsPolicy):
        return ""
    soi_year = getattr(policy, "soi_base_tax_year", None)
    if soi_year is None:
        return ""

    baseline = getattr(result, "baseline", None)
    years = getattr(result, "years", None)
    if baseline is None or years is None or len(years) == 0:
        return ""
    if not getattr(baseline, "published_nominal_gdp", None):
        return ""
    index = getattr(baseline, "nominal_income_index", None)
    if index is None:
        return ""

    vintage = _result_vintage(result)
    if vintage is None:
        return ""
    assumptions = _HAND_ENTERED_ASSUMPTIONS.get(vintage)
    if assumptions is None:
        return ""

    anchor_year = int(soi_year)
    window_first = _ASSUMPTION_FIRST_YEAR[vintage]
    growth = np.asarray(assumptions["real_gdp_growth"], dtype=float) + np.asarray(
        assumptions["inflation"], dtype=float
    )

    def old_level(year: int) -> float:
        """The old rule's index, up to a constant that cancels in the ratio."""
        if year >= window_first:
            steps = min(int(year) - window_first + 1, len(growth))
            level = float(np.prod(1.0 + growth[:steps]))
            if year - window_first + 1 > len(growth):
                level *= (1.0 + growth[-1]) ** (year - window_first + 1 - len(growth))
            return level
        # Before the window the old rule continued the first year's own rate.
        return (1.0 + growth[0]) ** -(window_first - 1 - int(year))

    old_anchor = old_level(anchor_year)
    new_anchor = float(index(anchor_year))
    if old_anchor <= 0 or new_anchor <= 0:
        return ""

    old_factors = np.array([old_level(int(y)) / old_anchor for y in years])
    new_factors = np.array([float(index(int(y))) / new_anchor for y in years])
    if not np.all(old_factors > 0) or np.allclose(old_factors, new_factors, rtol=1e-6):
        return ""

    path = np.asarray(result.static_deficit_effect, dtype=float) + np.asarray(
        result.behavioral_offset, dtype=float
    )
    total = float(path.sum())
    previous = float(np.sum(path / new_factors * old_factors))
    if total == 0.0 or previous == 0.0:
        return ""

    vintage_label = _VINTAGE_LABELS.get(vintage, "this")
    shift = (total - previous) / abs(previous) * 100.0
    return (
        f"Baseline corrected: the {vintage_label} budget baseline behind this "
        f"score is now CBO's own published table rather than this model's "
        f"reconstruction of it, so the base is aged on CBO's nominal path — "
        f"{new_factors.mean():.4f}× on the window average against the "
        f"reconstruction's {old_factors.mean():.4f}×. On the old path this "
        rf"policy scored \${previous:+,.1f}B; it now scores \${total:+,.1f}B, "
        f"a {shift:+.2f}% move. The same correction takes the vintage's "
        r"ten-year deficit from \$29,529.1B to CBO's own \$23,143.3B."
    )


#: Human-readable vintage names for the caption above.
_VINTAGE_LABELS: dict[Any, str] = {}


def _result_vintage(result: Any) -> Any:
    """The :class:`BaselineVintage` a result was scored on, or ``None``."""
    from fiscal_model.baseline import BaselineVintage

    if not _VINTAGE_LABELS:
        _VINTAGE_LABELS.update({
            BaselineVintage.CBO_FEB_2024: "February 2024",
            BaselineVintage.CBO_JAN_2025: "January 2025",
            BaselineVintage.CBO_FEB_2026: "February 2026",
        })

    baseline = getattr(result, "baseline", None)
    for holder in (baseline, result):
        value = getattr(holder, "baseline_vintage", None)
        if isinstance(value, BaselineVintage):
            return value
    # ``BaselineProjection`` carries no vintage; infer it from the published
    # GDP table it was stamped with, which is unique per vintage.
    published = getattr(baseline, "published_nominal_gdp", None) or {}
    if not published:
        return None
    from fiscal_model import cbo_baseline_data as cbo_data

    for key, table in (cbo_data.economic_tables() or {}).items():
        if table.get("nominal_gdp") == published:
            try:
                return BaselineVintage(key)
            except ValueError:  # pragma: no cover - unknown id in the CSV
                return None
    return None


#: Classes whose behavioural offset returned the **negation** of the contract
#: before the offset-sign sweep (2026-09-05), in every direction.
_OFFSET_SIGN_INVERTED = (AMTPolicy, EstateTaxPolicy, PremiumTaxCreditPolicy)


def _offset_sign_changed(policy: Any, behavioural: float) -> bool:
    """True when this policy's score differs from what it was before the sweep.

    Six modules returned an offset the engine's ``deficit = -revenue +
    behavioural`` magnified rather than eroded. They were wrong in two
    different ways, and the ways differ in *when* they bite:

    * ``AMTPolicy``, ``EstateTaxPolicy`` and ``PremiumTaxCreditPolicy``
      returned the negation, so every score through them moved.
    * ``CorporateTaxPolicy`` in ``reported`` mode, the ``TaxCreditPolicy``
      fallback branch, ``InternationalTaxPolicy`` and ``IRSEnforcementPolicy``
      returned ``abs(...)``, which agrees with the contract whenever the static
      effect is positive. Those moved **only** for a policy that loses revenue,
      which today is a corporate rate cut.

    So the caption fires on the second family only when the offset is negative
    — the tell that the static effect was negative too.
    """
    if behavioural == 0.0:
        return False
    if isinstance(policy, _OFFSET_SIGN_INVERTED):
        return True
    if isinstance(policy, CorporateTaxPolicy):
        return policy.mode == CORPORATE_MODE_REPORTED and behavioural < 0.0
    if isinstance(policy, TaxCreditPolicy):
        fallback = (
            policy.annual_revenue_change_billions is None
            and policy.credit_type
            not in (CreditType.CHILD_TAX_CREDIT, CreditType.EARNED_INCOME_CREDIT)
        )
        return fallback and behavioural < 0.0
    if isinstance(policy, (InternationalTaxPolicy, IRSEnforcementPolicy)):
        return behavioural < 0.0
    return False


def behavioural_sign_caption(policy: Any, result: Any) -> str:
    """One line saying that the behavioural response now erodes, not magnifies.

    The scoring engine books ``deficit = -revenue + behavioural``, so an offset
    carrying the static effect's sign shrinks the score in both directions — a
    tax increase raises less than its static figure, a cut loses less. Six
    modules returned the opposite sign, or an absolute value, and so *added* to
    the score instead. Two shipped presets moved when that was corrected —
    Trump Corporate 15% by about 22% and Repeal ACA Premium Credits by about
    18% — so the numbers ship with their explanation rather than in silence
    (Decision 6).

    Computed from the scored result, so it cannot drift from the figure above
    it. Returns ``""`` for any policy whose number did not move.
    """
    behavioural = float(np.sum(result.behavioral_offset))
    if not _offset_sign_changed(policy, behavioural):
        return ""
    static = float(np.sum(result.static_deficit_effect))
    current = static + behavioural
    previous = static - behavioural
    direction = "erodes" if abs(current) < abs(static) else "offsets"
    return (
        rf"Behavioural response: \${abs(behavioural):,.1f}B {direction} a "
        rf"static \${static:+,.1f}B to \${current:+,.1f}B. The response "
        f"carries the static effect's sign, so a tax increase raises less than "
        f"its static figure and a cut loses less. This module returned the "
        f"other sign until 2026-09-05, which added the same amount instead - "
        rf"the headline above would have read \${previous:+,.1f}B. No "
        f"elasticity changed; only the direction the response is applied in."
    )


def expenditure_offset_magnitude_caption(policy: Any, result: Any) -> str:
    """One line saying where this reform's behavioural size comes from.

    The tax-expenditure module multiplies a reform's static revenue effect by a
    share, and until 2026-09-11 all five of those shares were unsourced numbers
    — lane W7 settled which *direction* each response points and said in terms
    that a magnitude cannot be read off the same sentence. Lane H7 asked each
    of the five for a document and two of them have one, so the share is now
    read from the source rather than assumed:

    * **mortgage repeal** — Poterba & Sinai (NBER WP 14253) price the same
      repeal twice, at \\$72.4B with no behavioural response and \\$61.9B once
      households sell taxable assets to retire mortgage debt, so the erosion is
      their own ratio rather than a round 10%;
    * **the charitable benefit-rate ceiling** — CRS R40518's central price
      elasticity of giving (0.5), converted on the reform's own SOI deduction
      distribution, because a price elasticity and a share of a revenue effect
      are different quantities and the module needs the second.

    The shipped **Cap Charitable Deduction** preset moved by about 13% when
    that landed, so the number ships with its explanation rather than in
    silence (Decision 6).

    Computed from the scored result and from the module's own resolution, so it
    cannot drift from the figure above it, and it reconstructs the previous
    headline from ``BEHAVIORAL_ELASTICITIES`` — the table that *was* the answer
    — rather than from a literal written here. The headline is the conventional
    score, static plus behavioural, in both engine modes, so this is computed
    from those two and never from ``final_deficit_effect``, which on a dynamic
    run also carries revenue feedback.

    Returns ``""`` for any policy whose share is not sourced.
    """
    if not isinstance(policy, TaxExpenditurePolicy):
        return ""
    rule = policy.offset_magnitude_rule()
    if rule is None:
        return ""
    behavioural = float(np.sum(result.behavioral_offset))
    if behavioural == 0.0:
        return ""
    share = policy.resolved_offset_magnitude()
    previous_share = BEHAVIORAL_ELASTICITIES.get(policy.expenditure_type)
    if not share or not previous_share:
        return ""

    static = float(np.sum(result.static_deficit_effect))
    current = static + behavioural
    previous = static + behavioural * (previous_share / share)
    if rule.kind is OffsetMagnitudeKind.PUBLISHED_SHARE:
        provenance = (
            "Poterba and Sinai price this same repeal twice - "
            r"\$72.4B with no behavioural response and \$61.9B once households "
            "sell taxable assets to retire mortgage debt, 'about 85 percent' "
            "(NBER Working Paper 14253, Table 8) - so the erosion is the ratio "
            "of their two published figures"
        )
    else:
        provenance = (
            f"a {float(policy.cap_rate or 0.0):.0%} ceiling raises the price of "
            "a deductible dollar for every filer above it, and CRS R40518 - a "
            "whole report on this reform - settles the giving response at a "
            f"central price elasticity of {abs(float(rule.price_elasticity or 0.0)):.1f} "
            "(Appendix A, report p. 27). Converted on this deduction's own SOI "
            "distribution, because a price elasticity and a share of a revenue "
            "effect are different quantities"
        )
    return (
        f"Behavioural response, {share:.1%} of the static effect: {provenance}. "
        f"This module carried an unsourced {previous_share:.0%} until "
        rf"2026-09-11, which would have put the headline at \${previous:+,.1f}B "
        rf"instead of \${current:+,.1f}B. No direction changed and no fitted "
        f"constant was retuned; only where the size comes from."
    )


#: Corporate provisions this module can price that **no** published row in
#: ``corporate_rate_scores.csv`` prices as part of a statutory-rate score.
#: Attribute name -> how the caption names it. A run carrying any of these is
#: not comparable per point with the record, and the caption says so instead of
#: dividing a bundled total by a rate step.
_CORPORATE_BUNDLED_FIELDS: tuple[tuple[str, str], ...] = (
    ("extend_bonus_depreciation", "100% bonus depreciation"),
    ("gilti_rate_change", "a GILTI rate change"),
    ("eliminate_fdii", "FDII repeal"),
    ("fdii_rate_change", "an FDII rate change"),
    ("restore_rd_expensing", "R&D expensing"),
    ("adjust_book_minimum", "the book minimum tax"),
    ("book_minimum_rate_change", "a book-minimum rate change"),
)


def _corporate_bundled_provisions(policy: Any) -> tuple[str, ...]:
    """Which non-rate corporate channels this run also prices."""
    return tuple(
        label
        for attribute, label in _CORPORATE_BUNDLED_FIELDS
        if getattr(policy, attribute, None)
    )


def _corporate_rate_change_pp(policy: Any) -> float:
    """This run's statutory rate step, in percentage points, signed.

    Read through the same ``_get_reform_rate() - baseline_rate`` the scorer
    itself prices, so a policy that states ``new_rate`` instead of
    ``rate_change`` is converted on the step it is actually scored at rather
    than on a field that happens to be zero.
    """
    try:
        return (float(policy._get_reform_rate()) - float(policy.baseline_rate)) * 100.0
    except Exception:  # pragma: no cover — defensive
        return float(getattr(policy, "rate_change", 0.0) or 0.0) * 100.0


def _scorecard_id_for(policy: Any, policy_name: str) -> str:
    """Scorecard ``policy_id`` for this run, or ``""``.

    Tried on the preset label first — the key ``PRESET_TO_SCORECARD_ID`` is
    written in — then on the policy object's own name, because a run reached
    through a share link or the API may carry only one of the two. A Tailor
    custom run matches neither, which is correct: no benchmark scores it.

    The legacy 24-entry view is consulted first and the **whole** badge map
    after it. That widening is strictly additive — every label the legacy view
    resolved resolves to the same id — and it is what lets the published-range
    caption reach ``pillar_two_adoption`` and ``reciprocal_tariffs``, which H6
    added to the badge map and which the legacy view has never held.
    """
    try:
        from fiscal_model.ui.preset_validation import (
            BADGE_SCORECARD_ID_BY_LABEL,
            PRESET_TO_SCORECARD_ID,
        )
    except Exception:  # pragma: no cover — defensive
        return ""
    for view in (PRESET_TO_SCORECARD_ID, BADGE_SCORECARD_ID_BY_LABEL):
        for key in (policy_name, getattr(policy, "name", "")):
            if key and key in view:
                return view[key]
    return ""


def published_range_caption(
    policy: Any, result: Any, policy_name: str = ""
) -> str:
    """This benchmark's published range, wherever its scorekeepers disagree.

    Four calibrated targets are ranges rather than points, because two or more
    houses scored the same reform and printed figures an editorial midpoint
    would hide. H3a shipped the display for corporate runs; this is the same
    object rendered for every other policy that carries one, which today means
    **Pillar Two Adoption** ([−$102.6B, +$56.5B], JCT JCX-22-23 Table 2) and
    **Reciprocal Tariffs** ([−$1,800B, −$1,400B], CRFB / Tax Foundation / Yale
    on one announced schedule, 29% apart).

    Yields to ``corporate_estimator_range_captions`` on a corporate rate run so
    no benchmark prints its range twice. Everything is read live from the target
    ledger, so a revision reaches the app without a second edit.
    """
    if isinstance(policy, CorporateTaxPolicy) and _corporate_rate_change_pp(policy):
        return ""
    policy_id = _scorecard_id_for(policy, policy_name)
    if not policy_id:
        return ""

    from fiscal_model.ui.estimator_ranges import published_range_for

    published = published_range_for(policy_id)
    if published is None:
        return ""

    model_billions = float(np.sum(result.static_deficit_effect)) + float(
        np.sum(result.behavioral_offset)
    )
    if published.contains(model_billions):
        where = "**inside** it"
    else:
        where = rf"\${published.distance(model_billions):,.1f}B **outside** it"
    return (
        f"**This benchmark carries a published range.** Its scorekeepers — "
        f"{published.source_name} — scored this reform and printed "
        rf"\${published.low_billions:+,.1f}B to "
        rf"\${published.high_billions:+,.1f}B; this run's "
        rf"\${model_billions:+,.1f}B is {where}. The percentage the scorecard "
        f"reports for this row is a distance from one house's point inside "
        f"that range, not a measurement of accuracy against all of them."
    )


def corporate_estimator_range_captions(
    policy: Any, result: Any, policy_name: str = ""
) -> tuple[str, ...]:
    """What the other houses scored, beside what this run scored.

    A corporate-rate number quoted alone reads as a consensus, and this model's
    is not one: on CBO's February 2024 baseline over FY2025-2034, a statutory
    point is worth 55.1% of the vintage's average corporate base to Tax
    Foundation, 55.9% to JCT, 64.4% to PWBM and 79.5% to Treasury OTA — whose
    row is the only one of the four that is not rate-only — while this module
    sits above all four. ``biden_corporate_28``'s 3.7% is agreement with the
    highest estimator on the record, not with the record
    (``planning/memos/CORPORATE_PER_POINT_YIELD.md`` section 4b).

    Returns up to three lines: the converted range and where this run sits in
    it; how the conversion is done and why per-point dollars do not compare
    across scopes or directions; and, when the run matches a benchmark that
    carries one, that benchmark's own published range or scope verdict.

    Every figure is computed — from the four rows of the shipped record, from
    the live target ledger, and from *this run's* own headline — so none of it
    can drift from the number above it. Returns ``()`` for anything that is not
    a corporate policy with a statutory rate step, which includes the corporate
    AMT presets: a policy that moves no rate has no per-point yield to compare.
    """
    if not isinstance(policy, CorporateTaxPolicy):
        return ()
    rate_change_pp = _corporate_rate_change_pp(policy)
    if not rate_change_pp:
        return ()

    from fiscal_model.ui.estimator_ranges import (
        CORPORATE_RECORD_MEMO,
        corporate_estimator_range,
    )

    # The headline's own definition — static + behavioural — rather than
    # ``final_deficit_effect``, so the range is anchored on the figure printed
    # directly above it even if the two ever diverge.
    model_billions = float(np.sum(result.static_deficit_effect)) + float(
        np.sum(result.behavioral_offset)
    )
    bundled = _corporate_bundled_provisions(policy)
    spread = corporate_estimator_range(
        rate_change_pp=rate_change_pp,
        model_billions=model_billions,
        bundled=bundled,
    )
    if spread is None:  # pragma: no cover — record unreadable
        return ()

    # Listed in the same order as the span above it — ascending signed value —
    # so the two do not read as contradicting each other on a negative range.
    named = ", ".join(
        rf"{est.estimator} \${est.value_billions:+,.1f}B"
        + (f" ({est.scope_label})" if est.scope_label != "rate only" else "")
        for est in spread.estimates
    )
    position = {
        "inside": "sits inside that range",
        "larger": rf"prices it **larger than any of the four**, by \${spread.distance_to_range_billions:,.1f}B",
        "smaller": rf"prices it **smaller than all four**, by \${spread.distance_to_range_billions:,.1f}B",
    }[spread.model_position]
    lines = [
        f"**Estimator range.** Four houses have scored a corporate statutory-rate "
        f"change on {spread.window}. Converted to this policy's "
        f"{rate_change_pp:+.1f}pp step they span "
        rf"**\${spread.low_billions:+,.1f}B to \${spread.high_billions:+,.1f}B** "
        rf"— {named}. This run's \${model_billions:+,.1f}B {position}."
    ]

    shares = ", ".join(
        f"{est.marginal_share:.1%} {est.estimator}"
        for est in spread.estimates
        if est.marginal_share is not None
    )
    how = (
        f"**How that range is built.** {spread.basis.capitalize()} — every row "
        f"scored on {spread.window} against {spread.baseline_label}, "
        f"transcribed in `corporate_rate_scores.csv` and read in "
        f"`{CORPORATE_RECORD_MEMO}`. {spread.caveat}"
    )
    if spread.model_marginal_share is not None:
        beaten = spread.estimates_below_model_share
        total = len(spread.estimates)
        comparison = (
            "above every published estimator on the record"
            if beaten == total
            else f"above {beaten} of the {total}"
            if beaten
            else f"below all {total}"
        )
        how += (
            f" On the metric that removes the baseline level — the share of the "
            f"vintage's average corporate base one statutory point reaches — "
            f"this run sits at **{spread.model_marginal_share:.1%}**, "
            f"{comparison} ({shares})."
        )
    else:
        how += (
            f" **And this run is one of those.** It also prices "
            f"{_join_clauses(bundled)}, so dividing its total by the rate step "
            f"would report a bundled figure as a property of the rate, and its "
            f"own share is not quoted here. The four published shares are "
            f"{shares}."
        )
    lines.append(how)

    lines.extend(
        _corporate_benchmark_captions(
            policy, policy_name, spread=spread, model_billions=model_billions
        )
    )
    return tuple(lines)


def reported_mode_total_billions(policy: Any, window_years: int) -> float:
    """What this corporate policy would have scored under the old app default.

    ``CORPORATE_APP_MODE`` was ``reported`` until 2026-09-11, so every corporate
    figure the app served was priced against
    :data:`~fiscal_model.corporate.BASELINE_TAXABLE_PROFITS_BILLIONS` — a
    constant whose own comment calls it calibrated — grown at 4%/yr, with a flat
    ``static x elasticity x 0.5`` offset. This reproduces that number from the
    policy's own parameters, in revenue space, using the four lines
    ``ScoringEngine._score_growth_tax_policy`` uses for a ``reported`` corporate
    policy: the static effect asked for once, the engine's growth factor, the
    base-class phase, and the offset computed on the phased revenue.

    It is a reconstruction rather than a re-score because constructing a second
    :class:`~fiscal_model.scoring.FiscalPolicyScorer` costs ~300ms on a path PR
    #129 spent a lane making fast. ``tests/test_corporate_mode_flip.py`` scores
    both shipped presets through the real engine and asserts this returns the
    engine's own ``reported`` figure to the cent, so the shortcut cannot drift.

    Returned in **deficit** space, like ``result.static_deficit_effect``, so it
    is comparable with the headline it sits under: the engine books
    ``deficit = -revenue + behavioural``, which is why the offset erodes rather
    than adds.
    """
    from dataclasses import replace

    from fiscal_model.corporate import CORPORATE_BASE_GROWTH, CORPORATE_MODE_REPORTED

    previous = replace(policy, mode=CORPORATE_MODE_REPORTED)
    static_annual = previous.estimate_static_revenue_effect(0.0, use_real_data=True)
    total = 0.0
    for offset_years in range(window_years):
        year = previous.start_year + offset_years
        phase = previous.get_phase_in_factor(year)
        revenue = static_annual * (1 + CORPORATE_BASE_GROWTH) ** offset_years * phase
        total += previous.estimate_behavioral_offset(revenue) - revenue
    return total


def corporate_mode_flip_caption(policy: Any, result: Any) -> str:
    """One line saying the corporate default moved, and what it moved from.

    Owner decision ⑤ held ``CORPORATE_APP_MODE`` at ``reported`` until lane R5
    could re-measure Decision 1 once, and on the finished tree ``derived`` won
    both metrics the repository records: the mean absolute error over the three
    published corporate targets (**61.43% against 62.75%**), and H3a's
    four-house estimator span, where at the +7pp step every shipped corporate
    preset uses ``derived`` lands **inside** the published range and
    ``reported`` lands $47.3B outside it. So the app now scores the corporate
    rate channel against CBO's own projected receipts path rather than against a
    fitted profits aggregate, two shipped presets moved, and the numbers ship
    with their explanation rather than in silence (Decision 6).

    Neither mode was retuned to win: ``BASELINE_TAXABLE_PROFITS_BILLIONS`` is
    untouched and still the constant ``reported`` reads. And the flip is not an
    accuracy claim — ``derived`` is nearer on the mean while *losing* two of the
    three rows head to head, winning the one whose scope matches what the
    factory builds.

    Computed from the scored result and the policy's own parameters, so it
    cannot drift from the figure above it. Returns ``""`` for any policy whose
    number did not move.
    """
    from fiscal_model.corporate import CORPORATE_MODE_DERIVED

    if not isinstance(policy, CorporateTaxPolicy):
        return ""
    if policy.mode != CORPORATE_MODE_DERIVED:
        return ""
    if not _corporate_rate_change_pp(policy):
        return ""

    static = np.asarray(result.static_deficit_effect, dtype=float)
    current = float(np.sum(static)) + float(np.sum(result.behavioral_offset))
    previous = reported_mode_total_billions(policy, len(static))
    if previous == 0.0 or abs(current - previous) < 0.05:
        return ""

    change = (current - previous) / abs(previous) * 100.0
    return (
        rf"Scoring mode: this run prices the rate change at \${current:+,.1f}B. "
        rf"Until 2026-09-11 the app's corporate default was `reported`, which "
        rf"would have read \${previous:+,.1f}B ({change:+.1f}%). The default is "
        f"now `derived`: the base is CBO's own projected corporate receipts "
        f"path converted at one ratio measured on completed history, instead of "
        f"a profits aggregate the module's own comment calls calibrated. It was "
        f"changed because `derived` is nearer on the three published corporate "
        f"targets (61.4% against 62.8% mean absolute error) **and** lands inside "
        f"the four-house estimator range at this step where `reported` lands "
        f"outside it. No constant was retuned in either mode."
    )


def _join_clauses(items: Sequence[str]) -> str:
    """``"a, b and c"`` — for prose, where ``", ".join`` reads as a list."""
    items = list(items)
    if len(items) <= 1:
        return items[0] if items else ""
    return f"{', '.join(items[:-1])} and {items[-1]}"


def _corporate_benchmark_captions(
    policy: Any, policy_name: str, *, spread: Any, model_billions: float
) -> list[str]:
    """This benchmark's own published range or scope verdict, read from the ledger.

    Two of the repository's corporate rows carry something a single target
    figure cannot say, and both are read live rather than restated here:
    ``trump_corporate_15`` has a **published range** because two houses scored
    21% -> 15% directly and disagree, and ``biden_corporate_28`` has a **scope
    verdict** because its figures agree with Treasury's to 0.2% while the
    reforms do not.
    """
    from fiscal_model.ui.estimator_ranges import published_range_for, scope_verdict_for

    policy_id = _scorecard_id_for(policy, policy_name)
    if not policy_id:
        return []

    published = published_range_for(policy_id)
    scope = scope_verdict_for(policy_id)

    lines: list[str] = []
    if published is not None:
        where = (
            "inside it"
            if published.contains(model_billions)
            else rf"\${published.distance(model_billions):,.1f}B outside it"
        )
        line = (
            f"**This benchmark carries a published range.** Its scorekeepers — "
            f"{published.source_name} — scored this exact reform and printed "
            rf"\${published.low_billions:+,.1f}B to "
            rf"\${published.high_billions:+,.1f}B; this run's "
            rf"\${model_billions:+,.1f}B is {where}."
        )
        overlaps = (
            published.low_billions <= spread.high_billions
            and spread.low_billions <= published.high_billions
        )
        if not overlaps:
            line += (
                " That band and the converted one above do **not** overlap: "
                "scoring this reform directly and extrapolating a per-point "
                "yield to it give different answers, which is the "
                "direction-and-scope asymmetry measured rather than argued. "
                "Neither is adjusted onto the other."
            )
        lines.append(line)
    if scope:
        lines.append(
            f"**Scope: the benchmark and this run price different reforms.** "
            f"{escape_markdown_dollars(scope)}"
        )
    return lines
#: How close the scored ten-year figure must sit to the carried target before
#: the caption is willing to say it reproduces it. Both presets score the target
#: exactly today; this is a guard, not a rounding allowance.
_PAYROLL_TARGET_TOLERANCE_BILLIONS = 0.05

#: The two shipped Social Security presets whose ten-year figure reproduces its
#: carried target to the cent, keyed by scorecard id.
#:
#: Each entry is matched on the *design* (``ss_eliminate_cap`` /
#: ``ss_donut_hole_start``) **and** on the fitted annual, so a payroll policy
#: built at another threshold — which does not print a carried target — gets no
#: caption. ``held_out_10yr`` is the leave-one-out score
#: ``fiscal_model.validation.loo.run_payroll_loo`` returns when the case's own
#: covered-wage anchor is withheld and refitted from the other two anchors'
#: Pareto slope.
#:
#: The figures are **pinned rather than computed**: ``run_payroll_loo`` re-scores
#: three benchmarks through the full runner, and a page render is not the place
#: for that (PR #129 measured the footer's whole-scorecard call at 8.68s of a
#: 9.38s first paint; PR #135 replaced it with a generated artifact). The drift
#: test in ``tests/test_payroll_target_caption.py`` calls the suite and fails if
#: either constant stops matching — and it did its job on 2026-09-09, when lane
#: H9 moved ``ss_donut_250k``'s target to CBO Option 62 alternative 2. That is
#: why two figures are pinned per row rather than one:
#:
#: * ``by_construction_10yr`` — what the module *returns*, because its
#:   covered-wage base is this figure divided by ten and by 12.4%. The caption's
#:   guard compares the scored run to this one, so a change to the scoring path
#:   still silences the caption rather than letting it lie.
#: * ``carried_target_10yr`` — what the scorecard *scores against*. The two were
#:   the same number until H9, and conflating them is what would have had the
#:   app call -$2,700.0B "the carried target" after the ledger moved that target
#:   to -$1,426.8B.
_PAYROLL_FITTED_TARGETS: dict[str, dict[str, Any]] = {
    "ss_eliminate_cap": {
        "eliminate_cap": True,
        "donut_start": None,
        "fitted_annual": 320.0,
        "by_construction_10yr": -3_200.0,
        "carried_target_10yr": -3_200.0,
        "held_out_10yr": -3_319.5,
        "provision": "E2.1",
        "payroll_pct": 2.55,
        "depletion_year": 2059,
        "cross_check": (
            r"Tax Foundation scores the same design — the cap lifted, no "
            r"benefit credit — at \$3.2 trillion over 2027-2036 on a "
            r"conventional basis (Durante, 24 June 2026)"
        ),
    },
    "ss_donut_250k": {
        "eliminate_cap": False,
        "donut_start": 250_000.0,
        "fitted_annual": 270.0,
        "by_construction_10yr": -2_700.0,
        # Moved 2026-09-09 by lane H9 (target_revisions.ss_donut_250k.v2).
        "carried_target_10yr": -1_426.8,
        "held_out_10yr": -2_664.0,
        "provision": "E2.5",
        "payroll_pct": 2.50,
        "depletion_year": 2057,
        "cross_check": (
            r"that is now the carried target — CBO, Options for Reducing the "
            r"Deficit: 2025 to 2034, Option 62 alternative 2, report p. 73, "
            r"\$1,426.8B over FY2025-2034 for the identical donut"
        ),
    },
}


def _payroll_fitted_entry(policy: Any) -> dict[str, Any] | None:
    """Return the fitted-target entry this policy *is*, or ``None``.

    Matched on the design and the fitted annual together. A Tailor-built donut
    at $400,000, or an eliminate-cap policy carrying a different annual, is not
    one of the two shipped presets and must not be told it reproduces a target.
    """
    if not isinstance(policy, PayrollTaxPolicy):
        return None
    annual = policy.annual_revenue_change_billions
    if annual is None:
        return None
    for entry in _PAYROLL_FITTED_TARGETS.values():
        if bool(policy.ss_eliminate_cap) != entry["eliminate_cap"]:
            continue
        if policy.ss_donut_hole_start != entry["donut_start"]:
            continue
        if annual != entry["fitted_annual"]:
            continue
        return entry
    return None


def payroll_fitted_target_caption(policy: Any, result: Any) -> str:
    """One line saying that this figure is the target, and what the target is.

    ``ss_eliminate_cap`` and ``ss_donut_250k`` are two of the app's six largest
    headline numbers and both print their carried target to the cent, because
    ``payroll.py``'s covered-wage base for each *is* that target divided by ten
    and by the 12.4% OASDI rate (``BASELINE_WAGE_DATA`` states the arithmetic in
    its own comment: ``320 / 0.124`` and ``270 / 0.124``). A 0.0% validation row
    on either is measuring arithmetic.

    Both targets are ``secondhand``. SSA's Office of the Chief Actuary does score
    these two provisions — E2.1 and E2.5 — and publishes them **only** as a
    change in the long-range actuarial balance in percent of taxable payroll,
    plus trust-fund dates. There is no OCACT dollar figure at any horizon, so
    the round ten-year dollar amounts are a conversion nobody published.

    What the module returns without being told the answer is the honest figure,
    and it is a good one: held out, −$2,664.0B and −$3,319.5B. Printing it beside
    the shipped number is the whole point of this caption.

    The claim "reproduced to the cent" is **checked against this run** before it
    is printed: the caption asserts something about the number above it, so a
    score that stops equalling its figure silences the caption rather than
    letting it lie. ``result`` is read for exactly that.

    Since 2026-09-09 the two rows differ in a way the caption has to carry.
    ``ss_eliminate_cap``'s target is still the round -$3.2T nobody published,
    so its sentence is unchanged. ``ss_donut_250k``'s target has moved to CBO's
    -$1,426.8B (``target_revisions.ss_donut_250k.v2``) while the module still
    returns -$2,700.0B, so calling the figure above "the carried target" would
    now be false. The caption says the true thing instead, and states the miss.

    Returns ``""`` for every payroll policy that is not one of those two.
    """
    entry = _payroll_fitted_entry(policy)
    if entry is None:
        return ""

    by_construction = float(entry["by_construction_10yr"])
    carried = float(entry["carried_target_10yr"])
    scored = float(np.sum(result.static_deficit_effect)) + float(
        np.sum(result.behavioral_offset)
    )
    if abs(scored - by_construction) > _PAYROLL_TARGET_TOLERANCE_BILLIONS:
        return ""

    held_out = float(entry["held_out_10yr"])
    gap_pct = abs(held_out - by_construction) / abs(by_construction) * 100.0

    target_moved = abs(carried - by_construction) > _PAYROLL_TARGET_TOLERANCE_BILLIONS
    if target_moved:
        miss_pct = abs(by_construction - carried) / abs(carried) * 100.0
        opening = (
            rf"Where this number comes from: \${by_construction:+,.1f}B is what "
            f"the module returns, because the covered-wage base behind it is "
            f"that figure divided by ten and by the 12.4% OASDI rate — "
            f"bookkeeping, not agreement. It is no longer the carried target: "
            rf"that moved to \${carried:+,.1f}B on 2026-09-09, which this "
            f"figure misses by {miss_pct:.1f}%. "
        )
    else:
        opening = (
            rf"Where this number comes from: \${by_construction:+,.1f}B is the "
            f"carried target, reproduced to the cent because the covered-wage "
            f"base behind it is that target divided by ten and by the 12.4% "
            f"OASDI rate — bookkeeping, not agreement. "
        )

    return (
        opening
        + f"Held out, with this case's own wage "
        f"anchor withheld and refitted from the other two, the module returns "
        rf"\${held_out:+,.1f}B ({gap_pct:.1f}% away). And the round figure is "
        f"a dollar conversion nobody published: SSA's Office of the Chief "
        f"Actuary scores this provision as {entry['provision']} and reports "
        f"{entry['payroll_pct']:.2f}% of taxable payroll and a "
        f"{entry['depletion_year']} depletion date, with no dollar amount at "
        f"any horizon. For a published ten-year figure: {entry['cross_check']}."
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

    tariff_note = tariff_net_caption(policy, result)
    if tariff_note:
        st_module.caption(tariff_note)

    pharma_note = pharma_channels_caption(policy, result)
    if pharma_note:
        st_module.caption(pharma_note)
    death_note = gains_at_death_caption(policy, result)
    if death_note:
        st_module.caption(death_note)
    projection_note = realizations_projection_caption(policy, result)
    if projection_note:
        st_module.caption(projection_note)
    ptc_note = ptc_repeal_baseline_caption(policy, result)
    if ptc_note:
        st_module.caption(ptc_note)
    salt_note = salt_current_law_caption(policy, result)
    if salt_note:
        st_module.caption(salt_note)
    sign_note = behavioural_sign_caption(policy, result)
    if sign_note:
        st_module.caption(sign_note)
    magnitude_note = expenditure_offset_magnitude_caption(policy, result)
    if magnitude_note:
        st_module.caption(magnitude_note)
    base_note = agi_inclusive_base_caption(policy, result)
    if base_note:
        st_module.caption(base_note)
    column_note = agi_income_column_caption(policy, result)
    if column_note:
        st_module.caption(column_note)
    base_year_note = income_base_projection_caption(policy, result)
    if base_year_note:
        st_module.caption(base_year_note)
    transcription_note = cbo_baseline_transcription_caption(policy, result)
    if transcription_note:
        st_module.caption(transcription_note)
    mode_note = corporate_mode_flip_caption(policy, result)
    if mode_note:
        st_module.caption(mode_note)
    for corporate_note in corporate_estimator_range_captions(
        policy, result, getattr(scored, "policy_name", "") or ""
    ):
        st_module.caption(corporate_note)
    range_note = published_range_caption(
        policy, result, getattr(scored, "policy_name", "") or ""
    )
    if range_note:
        st_module.caption(range_note)
    payroll_note = payroll_fitted_target_caption(policy, result)
    if payroll_note:
        st_module.caption(payroll_note)

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
        line = (
            f"<small><b>Accuracy band:</b> \\${band[0]:+,.1f}B "
            f"to \\${band[1]:+,.1f}B"
            + (f" ({escape(note)})" if note else "")
        )
        credibility = getattr(scored, "credibility", None)
        outer_low = getattr(credibility, "outer_low", None)
        outer_high = getattr(credibility, "outer_high", None)
        mean_pct = getattr(credibility, "mean_abs_pct_error", None)
        max_pct = getattr(credibility, "max_abs_pct_error", None)
        # A class of one has a worst row equal to its mean; printing the same
        # interval twice under two labels would read as two findings.
        if (
            outer_low is not None
            and outer_high is not None
            and mean_pct is not None
            and max_pct is not None
            and max_pct > mean_pct
        ):
            line += (
                f"; \\${min(outer_low, outer_high):+,.1f}B to "
                f"\\${max(outer_low, outer_high):+,.1f}B at that class's worst "
                "observed row"
            )
        st_module.markdown(line + "</small>", unsafe_allow_html=True)
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
            f"  Accuracy band: ${band[0]:+,.1f}B to ${band[1]:+,.1f}B "
            f"({scored.sensitivity_note})\n"
        )
    elif getattr(scored, "sensitivity_note", ""):
        text += f"  Accuracy band: {scored.sensitivity_note}\n"

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

        _render_assignment_link(st_module, scored, result_data)

        st_module.markdown("---")
        st_module.subheader("Copy Summary for Reports")
        st_module.caption("Select all text below and copy to paste into documents:")
        st_module.code(text_summary, language="text")


def _render_assignment_link(
    st_module: Any, scored: Any, result_data: dict[str, Any]
) -> None:
    """The instructor's frozen-link control, shown only in classroom context.

    Gated on ``?classroom=1`` (and the ``?mode=classroom`` alias) rather than
    shown to everyone: a frozen link is a teaching artefact, and the plain
    share link above it is what a reader wants. ``/classroom`` links here with
    the flag set.
    """
    from fiscal_model.ui.frozen_links import (
        is_classroom_request,
        render_assignment_link_block,
    )

    query_params = getattr(st_module, "query_params", {}) or {}
    try:
        if not is_classroom_request(query_params):
            return
    except Exception:  # pragma: no cover — exotic query-param stand-ins
        return

    st_module.markdown("---")
    render_assignment_link_block(
        st_module,
        scored,
        result_data,
        engine=st_module.session_state.get("setting_macro_model"),
    )


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
