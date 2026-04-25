"""
Map preset canonical names to validation scorecard ``policy_id``.

Used by the sidebar to surface live model-vs-official accuracy badges
next to each preset, so users can see at a glance how well-calibrated
the underlying scoring is. Driven by the same data shown on the
Validation tab (``/validation/scorecard``).
"""

from __future__ import annotations

from functools import lru_cache

# Mapping from canonical PRESET_POLICIES key to scorecard policy_id.
# Only presets that have a calibrated specialized validator are listed —
# others render without a badge.
PRESET_TO_SCORECARD_ID: dict[str, str] = {
    "🏛️ TCJA Full Extension (CBO: $4.6T)":  "tcja_full_extension",
    "🏛️ TCJA Extension (No SALT Cap)":       "tcja_no_salt_cap",
    "🏛️ TCJA Rates Only":                    "tcja_rates_only",
    "🏢 Biden Corporate 28% (CBO: -$1.35T)": "biden_corporate_28",
    "🏢 Trump Corporate 15%":                "trump_corporate_15",
    "👶 Biden CTC Expansion (CBO: $1.6T)":   "biden_ctc_2021",
    "👶 CTC Extension (CBO: $600B)":         "ctc_extension",
    "💼 EITC Childless Expansion (CBO: $178B)": "biden_eitc_childless",
    "🏠 Estate Tax: Extend TCJA (CBO: $167B)":  "extend_tcja_exemption",
    "🏠 Biden Estate Reform (-$450B)":       "biden_estate_reform",
    "🏠 Eliminate Estate Tax ($350B)":       "eliminate_estate_tax",
    "💰 SS Cap to 90% (CBO: -$800B)":        "ss_cap_90_pct",
    "💰 SS Donut Hole $250K (-$2.7T)":       "ss_donut_250k",
    "💰 Eliminate SS Cap (-$3.2T)":          "ss_eliminate_cap",
    "💰 Expand NIIT (JCT: -$250B)":          "expand_niit",
    "⚖️ AMT: Extend TCJA Relief ($450B)":   "extend_tcja_amt",
    "⚖️ Repeal Individual AMT ($450B)":     "repeal_individual_amt",
    "⚖️ Repeal Corporate AMT (-$220B)":     "repeal_corporate_amt",
    "🏥 Extend ACA Enhanced PTCs ($350B)":   "extend_enhanced_ptc",
    "🏥 Repeal ACA Premium Credits (-$1.1T)": "repeal_ptc",
    "📋 Cap Employer Health Exclusion (-$450B)": "cap_employer_health",
    "📋 Repeal SALT Cap ($1.1T)":            "repeal_salt_cap",
    "📋 Eliminate Step-Up Basis (-$500B)":   "eliminate_step_up",
    "📋 Cap Charitable Deduction (-$200B)":  "cap_charitable",
}


_RATING_ICON = {
    "Excellent": "🟢",
    "Good": "🟢",
    "Acceptable": "🟡",
    "Poor": "🔴",
    "Error": "⚫",
}


@lru_cache(maxsize=1)
def _scorecard_index() -> dict[str, dict]:
    """Materialize the live scorecard once per process and key by policy_id.

    Cached so repeat sidebar renders during the same Streamlit run don't
    recompute 37 specialized validators. The Validation tab also calls
    ``compute_scorecard`` directly, so the cache is shared via the
    aggregated runners' own caching layers.
    """
    from fiscal_model.validation import compute_scorecard

    summary = compute_scorecard()
    return {
        e.policy_id: {
            "rating": e.rating,
            "abs_pct": e.abs_percent_difference,
            "signed_pct": e.percent_difference,
            "policy_name": e.policy_name,
            "official": e.official_10yr_billions,
            "model": e.model_10yr_billions,
            "source": e.official_source,
            "url": e.benchmark_url,
        }
        for e in summary.entries
    }


def reset_scorecard_cache() -> None:
    """Clear the memoized scorecard. Mainly for tests."""
    cache_clear = getattr(_scorecard_index, "cache_clear", None)
    if cache_clear is not None:
        cache_clear()


def get_validation_badge(preset_name: str) -> dict | None:
    """Return validation accuracy info for a preset, or ``None`` if untracked.

    The returned dict contains the rating, signed % difference, official and
    model 10-year amounts, source label, and link to the source document
    (when available). Suitable for direct rendering by the sidebar.
    """
    score_id = PRESET_TO_SCORECARD_ID.get(preset_name)
    if score_id is None:
        return None
    try:
        index = _scorecard_index()
    except Exception:
        return None
    entry = index.get(score_id)
    if entry is None:
        return None
    return {
        **entry,
        "icon": _RATING_ICON.get(entry["rating"], "⚪"),
    }


__all__ = [
    "PRESET_TO_SCORECARD_ID",
    "get_validation_badge",
    "reset_scorecard_cache",
]
