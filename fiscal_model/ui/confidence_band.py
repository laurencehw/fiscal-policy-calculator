"""UI compatibility wrapper for the result accuracy band.

The shared implementation lives in ``fiscal_model.validation.credibility`` so
FastAPI responses and Streamlit panels use the same evidence metadata. This
module preserves the older UI import path.

The band this re-exports is **not** the category ``ConfidenceBand`` it used to
carry. Wave C's H4 replaced that object — a mean over ``summary.by_category``
that blended fitted bookkeeping with unfitted reconstructions, and that fell
back to the whole Tier 1 tier for every unmapped preset area — with
:class:`~fiscal_model.validation.credibility.EmpiricalBand`, read off the 26
pre-registered out-of-sample rows of the policy's **own class**. The old names
are gone rather than aliased: a stale caller reading ``mean_abs_pct_error`` off
a differently-populated object would print a wrong number silently, and an
``ImportError`` is the louder failure.
"""

from fiscal_model.validation.credibility import (
    POLICY_TYPE_TO_SCORECARD_CATEGORY,
    POLICY_TYPE_TO_TIER1_CLASS,
    PRESET_AREA_TO_SCORECARD_CATEGORY,
    EmpiricalBand,
    band_for_policy,
    band_for_policy_class,
    band_for_policy_type,
    format_band_caption,
    reset_confidence_cache,
    tier1_class_bands,
)

__all__ = [
    "POLICY_TYPE_TO_SCORECARD_CATEGORY",
    "POLICY_TYPE_TO_TIER1_CLASS",
    "PRESET_AREA_TO_SCORECARD_CATEGORY",
    "EmpiricalBand",
    "band_for_policy",
    "band_for_policy_class",
    "band_for_policy_type",
    "format_band_caption",
    "reset_confidence_cache",
    "tier1_class_bands",
]
