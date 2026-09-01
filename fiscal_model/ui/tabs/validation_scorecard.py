"""
Validation tab — live scorecard of model accuracy against published
CBO/JCT/Treasury revenue scores.

Surfaces the same data as the ``/validation/scorecard`` API endpoint so
users can verify, in-app, what's actually been validated and at what
error margin — instead of relying on a static table in the README.
"""

from __future__ import annotations

import logging
from typing import Any

from fiscal_model.validation.provenance import MODEL_ESTIMATE
from fiscal_model.validation.scorecard import (
    ScorecardEntry,
    ScorecardSummary,
    cached_default_scorecard,
)

_logger = logging.getLogger(__name__)

_RATING_COLOR = {
    "Excellent": "🟢",
    "Good": "🟢",
    "Acceptable": "🟡",
    "Poor": "🔴",
    "Error": "⚫",
}


def _format_signed_billions(value: float) -> str:
    sign = "+" if value > 0 else ""
    return f"{sign}{value:,.1f}"


def _format_pct(value: float) -> str:
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.1f}%"


_PROVENANCE_LABEL = {
    "line_item": "Line item",
    "line_item_differs": "Line item (differs)",
    "secondhand": "Secondhand",
    "model_estimate": "Model estimate",
    "unclassified": "Unclassified",
}


def _entry_to_row(entry: ScorecardEntry) -> dict[str, Any]:
    return {
        "Status": _RATING_COLOR.get(entry.rating, "⚪"),
        "Category": entry.category,
        "Policy": entry.policy_name,
        "Official ($B)": _format_signed_billions(entry.official_10yr_billions),
        "Model ($B)": _format_signed_billions(entry.model_10yr_billions),
        "Δ%": _format_pct(entry.percent_difference),
        "Rating": entry.rating,
        "Source": entry.official_source,
        "Target provenance": _PROVENANCE_LABEL.get(entry.provenance, entry.provenance),
    }


def published_entries(summary: ScorecardSummary) -> list[ScorecardEntry]:
    """Entries whose target is a published figure — the benchmarks.

    The complement (:func:`illustration_entries`) has no official score at
    all, so an accuracy statistic computed over it measures the model against
    itself. The two are reported in separate tables for that reason.
    """
    return [e for e in summary.entries if e.provenance != MODEL_ESTIMATE]


def illustration_entries(summary: ScorecardSummary) -> list[ScorecardEntry]:
    """Entries scored against a model estimate rather than a published score."""
    return [e for e in summary.entries if e.provenance == MODEL_ESTIMATE]


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2.0


def _render_summary(st_module: Any, summary: ScorecardSummary) -> None:
    # Every headline statistic is computed over the *published* benchmarks
    # only. Folding the illustrations in would let rows with no official
    # score move a number captioned "against published estimates".
    entries = published_entries(summary)
    n = len(entries)
    within_15 = sum(1 for e in entries if e.abs_percent_difference <= 15.0)
    direction = sum(1 for e in entries if e.direction_match)
    cols = st_module.columns(4)
    cols[0].metric("Benchmarked policies", n)
    cols[1].metric(
        "Within 15%",
        f"{within_15}/{n}",
        f"{(within_15 / n * 100):.0f}%" if n else None,
    )
    cols[2].metric(
        "Direction match",
        f"{direction}/{n}",
        f"{(direction / n * 100):.0f}%" if n else None,
    )
    cols[3].metric(
        "Median |Δ%|",
        f"{_median([e.abs_percent_difference for e in entries]):.1f}%",
    )
    illustrations = summary.model_estimate_entries
    transcribed = summary.transcribed_entries
    st_module.caption(
        f"{n} benchmarks against a published figure "
        f"({transcribed} transcribed from a primary document, "
        f"{summary.line_item_differs_entries} of those disagreeing with the "
        f"target this app carries) · {illustrations} illustrations with no "
        "official score are listed separately below and are excluded from "
        "every number above."
    )


def _render_category_table(st_module: Any, summary: ScorecardSummary) -> None:
    st_module.subheader("Accuracy by category")
    rows = []
    for cat, sub in summary.by_category.items():
        n = sub["n"]
        if n == 0:
            continue
        within = sub["within_15pct"]
        ratings = sub.get("ratings", {})
        rows.append({
            "Category": cat,
            "n": n,
            "Within 15%": f"{within}/{n}",
            "Mean |Δ%|": f"{sub['mean_abs_percent_difference']:.1f}%",
            "Excellent": ratings.get("Excellent", 0),
            "Good": ratings.get("Good", 0),
            "Acceptable": ratings.get("Acceptable", 0),
            "Poor": ratings.get("Poor", 0),
        })
    if rows:
        st_module.dataframe(rows, hide_index=True, width="stretch")


def _render_entry_table(st_module: Any, summary: ScorecardSummary) -> None:
    st_module.subheader("Per-policy detail")
    sort_options = {
        "By |Δ%| (worst first)": lambda e: -e.abs_percent_difference,
        "By |Δ%| (best first)": lambda e: e.abs_percent_difference,
        "By category": lambda e: (e.category, e.abs_percent_difference),
    }
    choice = st_module.radio(
        "Sort by",
        list(sort_options.keys()),
        horizontal=True,
        key="validation_scorecard_sort",
    )
    rows = sorted(published_entries(summary), key=sort_options[choice])
    st_module.dataframe(
        [_entry_to_row(e) for e in rows],
        hide_index=True,
        width="stretch",
    )


def _render_illustrations_table(st_module: Any, summary: ScorecardSummary) -> None:
    """Rows with no official score, kept visible but never counted.

    Plan §5.2. Deleting them would hide model behaviour a user can still
    trigger from the app; counting them as "validated" would claim agreement
    with an agency that never scored the policy. So they are shown here,
    under their own heading, with the Δ% column deliberately labelled as
    self-comparison.
    """
    rows = illustration_entries(summary)
    if not rows:
        return
    st_module.subheader("Illustrations (no official score)")
    st_module.caption(
        "No agency has published a score for these policy shapes, so the "
        "\"official\" column is a model or illustrative estimate and the Δ% "
        "measures internal consistency, not accuracy. They are excluded from "
        "every count and every accuracy statistic on this page."
    )
    st_module.dataframe(
        [
            {
                "Category": e.category,
                "Policy": e.policy_name,
                "Illustrative ($B)": _format_signed_billions(
                    e.official_10yr_billions
                ),
                "Model ($B)": _format_signed_billions(e.model_10yr_billions),
                "Δ% (self-comparison)": _format_pct(e.percent_difference),
                "Stated source": e.official_source,
            }
            for e in sorted(rows, key=lambda e: (e.category, e.policy_name))
        ],
        hide_index=True,
        width="stretch",
    )


def _render_caveats(st_module: Any, summary: ScorecardSummary) -> None:
    flagged = [
        e for e in summary.entries
        if e.known_limitations or e.rating in {"Poor", "Error"}
    ]
    if not flagged:
        return
    st_module.subheader("Known limitations & outliers")
    for e in flagged:
        title = f"{_RATING_COLOR.get(e.rating, '⚪')} {e.policy_name} ({e.percent_difference:+.1f}%)"
        with st_module.expander(title, expanded=False):
            st_module.markdown(
                f"**Source:** {e.official_source}"
                + (f"  \n**Date:** {e.benchmark_date}" if e.benchmark_date else "")
            )
            if e.benchmark_url:
                st_module.markdown(f"[Official document]({e.benchmark_url})")
            if e.notes:
                st_module.markdown(f"**Notes:** {e.notes}")
            if e.known_limitations:
                st_module.markdown("**Modeling limitations:**")
                for lim in e.known_limitations:
                    st_module.markdown(f"- {lim}")


def render_validation_scorecard_tab(st_module: Any) -> None:
    """Render the Validation tab with live model-vs-official comparisons."""
    st_module.header("Validation scorecard")
    st_module.markdown(
        "Live comparison of this model's revenue scores against published "
        "CBO/JCT/Treasury/PWBM estimates.\n\n"
        "Ratings: 🟢 **Excellent** ≤5%, 🟢 **Good** ≤10%, 🟡 **Acceptable** ≤20%, "
        "🔴 **Poor** >20%. The **Generic** category uses raw "
        "rate/threshold parameters and is expected to drift — calibrated "
        "specialized paths drive the headline accuracy."
    )

    try:
        summary = cached_default_scorecard()
    except Exception:
        _logger.exception("Failed to compute validation scorecard")
        st_module.error(
            "Could not compute the validation scorecard. "
            "Please reload the page or check the deployment logs."
        )
        return

    if summary.total_entries == 0:
        st_module.info("No validation entries available.")
        return

    _render_summary(st_module, summary)
    _render_category_table(st_module, summary)
    _render_entry_table(st_module, summary)
    _render_illustrations_table(st_module, summary)
    _render_caveats(st_module, summary)


__all__ = [
    "illustration_entries",
    "published_entries",
    "render_validation_scorecard_tab",
]
