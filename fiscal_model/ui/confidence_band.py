"""
UI compatibility wrapper for result credibility helpers.

The shared implementation lives in ``fiscal_model.validation.credibility`` so
FastAPI responses and Streamlit panels use the same evidence metadata. This
module preserves the older UI import path.
"""

from fiscal_model.validation.credibility import (
    POLICY_TYPE_TO_SCORECARD_CATEGORY,
    PRESET_AREA_TO_SCORECARD_CATEGORY,
    ConfidenceBand,
    _category_index,
    estimate_uncertainty_dollars,
    format_band_caption,
    get_band_for_policy_type,
    get_band_for_preset_area,
    get_band_for_result,
    reset_confidence_cache,
)

__all__ = [
    "POLICY_TYPE_TO_SCORECARD_CATEGORY",
    "PRESET_AREA_TO_SCORECARD_CATEGORY",
    "ConfidenceBand",
    "_category_index",
    "estimate_uncertainty_dollars",
    "format_band_caption",
    "get_band_for_policy_type",
    "get_band_for_preset_area",
    "get_band_for_result",
    "reset_confidence_cache",
]
