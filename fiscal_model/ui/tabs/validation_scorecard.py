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

from fiscal_model.validation.scorecard import (
    ScorecardEntry,
    ScorecardSummary,
    compute_scorecard,
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
    }


def _render_summary(st_module: Any, summary: ScorecardSummary) -> None:
    n = summary.total_entries
    cols = st_module.columns(4)
    cols[0].metric("Validated policies", n)
    cols[1].metric(
        "Within 15%",
        f"{summary.within_15pct}/{n}",
        f"{(summary.within_15pct / n * 100):.0f}%" if n else None,
    )
    cols[2].metric(
        "Direction match",
        f"{summary.direction_match}/{n}",
        f"{(summary.direction_match / n * 100):.0f}%" if n else None,
    )
    cols[3].metric(
        "Median |Δ%|",
        f"{summary.median_abs_percent_difference:.1f}%",
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
        st_module.dataframe(rows, hide_index=True, use_container_width=True)


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
    rows = sorted(summary.entries, key=sort_options[choice])
    st_module.dataframe(
        [_entry_to_row(e) for e in rows],
        hide_index=True,
        use_container_width=True,
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
        "CBO/JCT/Treasury/PWBM estimates. Computed on every page load — "
        "no static cache.\n\n"
        "Ratings: 🟢 **Excellent** ≤5%, 🟢 **Good** ≤10%, 🟡 **Acceptable** ≤20%, "
        "🔴 **Poor** >20%. The **Generic** category uses raw "
        "rate/threshold parameters and is expected to drift — calibrated "
        "specialized paths drive the headline accuracy."
    )

    try:
        summary = compute_scorecard()
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
    _render_caveats(st_module, summary)


__all__ = ["render_validation_scorecard_tab"]
