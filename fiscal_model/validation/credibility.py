"""
Shared credibility metadata for model results.

The public scorecard answers "how close has this model been to published
benchmarks?" This module turns that scorecard into compact, machine-readable
metadata that both the Streamlit UI and FastAPI responses can attach to a
single result.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache
from typing import Any

# Map preset categories from PRESET_POLICIES (`_preset_category`) to scorecard
# categories from compute_scorecard. Where no calibrated specialized validator
# exists, fall back to ``Generic``.
PRESET_AREA_TO_SCORECARD_CATEGORY: dict[str, str] = {
    "TCJA / Individual": "TCJA",
    "Corporate": "Corporate",
    "Tax Credits": "Credits",
    "Estate Tax": "Estate",
    "Payroll / SS": "Payroll",
    "AMT": "AMT",
    "ACA / Healthcare": "PTC",
    "Tax Expenditures": "Expenditures",
    "Income Tax": "Generic",
    "International Tax": "Generic",
    "IRS Enforcement": "Generic",
    "Drug Pricing": "Generic",
    "Trade / Tariffs": "Generic",
    "Climate / Energy": "Generic",
}


# Map raw PolicyType enum values to scorecard categories.
POLICY_TYPE_TO_SCORECARD_CATEGORY: dict[str, str] = {
    "corporate_tax": "Corporate",
    "estate_tax": "Estate",
    "payroll_tax": "Payroll",
    "tax_credit": "Credits",
    "tax_deduction": "Expenditures",
    "capital_gains_tax": "CapitalGains",
    "income_tax": "Generic",
    "excise_tax": "Generic",
    "discretionary_defense": "Generic",
    "discretionary_nondefense": "Generic",
    "mandatory_spending": "Generic",
    "infrastructure": "Generic",
    "social_security": "Payroll",
    "medicare": "Generic",
    "medicaid": "Generic",
    "unemployment": "Generic",
    "snap": "Generic",
    "other_transfer": "Generic",
}


@dataclass(frozen=True)
class ConfidenceBand:
    """Calibration accuracy for one scorecard category."""

    category: str
    n_calibrated: int
    mean_abs_pct_error: float
    median_abs_pct_error: float
    within_15pct: int
    rating_label: str
    is_calibrated: bool


@dataclass(frozen=True)
class ResultCredibility:
    """Machine-readable credibility note for one scoring result."""

    category: str
    evidence_type: str
    n_benchmarks: int
    mean_abs_pct_error: float
    median_abs_pct_error: float
    within_15pct: int
    rating_label: str
    is_calibrated: bool
    holdout_status: str
    uncertainty_low: float | None
    uncertainty_high: float | None
    limitations: list[str]
    caption: str


_GENERIC_LIMITATIONS = [
    "Uses raw rate/threshold auto-population rather than a calibrated specialized validator.",
    "Treat as directional for one-off custom policies until matched to a published benchmark.",
]

_ALL_RESULTS_LIMITATIONS = [
    "holdout labels follow the locked post-2026-05-02 regression protocol; they are not retroactive historical out-of-sample claims.",
]


def _rating_label(mean_abs: float, is_calibrated: bool) -> str:
    if not is_calibrated:
        return "Limited (uncalibrated path)"
    if mean_abs <= 5:
        return "Excellent"
    if mean_abs <= 10:
        return "Good"
    if mean_abs <= 20:
        return "Acceptable"
    return "Approximate"


def _category_for_preset_area(area: str | None) -> str:
    if not area:
        return "Generic"
    return PRESET_AREA_TO_SCORECARD_CATEGORY.get(area, "Generic")


def _category_for_policy_type(policy_type: str | None) -> str:
    if not policy_type:
        return "Generic"
    return POLICY_TYPE_TO_SCORECARD_CATEGORY.get(policy_type, "Generic")


def _category_entry_limitations(category: str) -> list[str]:
    """Collect known limitations from scorecard entries in a category."""
    try:
        from fiscal_model.validation import cached_default_scorecard

        summary = cached_default_scorecard()
    except Exception:
        return []

    limitations: list[str] = []
    for entry in summary.entries:
        if entry.category != category:
            continue
        for limitation in entry.known_limitations:
            if limitation not in limitations:
                limitations.append(limitation)
    return limitations


def _category_holdout_status(category: str) -> str:
    """Return category-level holdout availability."""
    try:
        from fiscal_model.validation import cached_default_scorecard
        from fiscal_model.validation.holdout import category_holdout_status

        summary = cached_default_scorecard()
    except Exception:
        return "unknown"

    return category_holdout_status(category, list(summary.entries))


@lru_cache(maxsize=1)
def _category_index() -> dict[str, ConfidenceBand]:
    """Materialize the live scorecard once per process, keyed by category."""
    from fiscal_model.validation import cached_default_scorecard

    summary = cached_default_scorecard()
    out: dict[str, ConfidenceBand] = {}
    for cat, sub in summary.by_category.items():
        n = int(sub["n"])
        if n == 0:
            continue
        is_calibrated = cat != "Generic"
        out[cat] = ConfidenceBand(
            category=cat,
            n_calibrated=n,
            mean_abs_pct_error=float(sub["mean_abs_percent_difference"]),
            # Median per-category isn't stored on the summary; approximate with
            # the mean until the scorecard persists exact category medians.
            median_abs_pct_error=float(sub["mean_abs_percent_difference"]),
            within_15pct=int(sub["within_15pct"]),
            rating_label=_rating_label(
                float(sub["mean_abs_percent_difference"]),
                is_calibrated,
            ),
            is_calibrated=is_calibrated,
        )
    return out


def reset_confidence_cache() -> None:
    """Clear the memoized category index. Mainly for tests."""
    cache_clear = getattr(_category_index, "cache_clear", None)
    if cache_clear is not None:
        cache_clear()


def get_band_for_preset_area(area: str | None) -> ConfidenceBand | None:
    """Look up the confidence band for a sidebar preset's category."""
    cat = _category_for_preset_area(area)
    try:
        index = _category_index()
    except Exception:
        return None
    return index.get(cat)


def get_band_for_policy_type(policy_type: str | None) -> ConfidenceBand | None:
    """Look up the confidence band for a bill provision's policy type."""
    cat = _category_for_policy_type(policy_type)
    try:
        index = _category_index()
    except Exception:
        return None
    return index.get(cat)


def get_band_for_result(
    *,
    policy_name: str | None = None,
    policy: Any = None,
) -> ConfidenceBand | None:
    """Resolve the most accurate band for a scoring result."""
    if policy_name:
        try:
            from fiscal_model.app_data import PRESET_POLICIES
            from fiscal_model.ui.policy_input_presets import _preset_category

            preset = PRESET_POLICIES.get(policy_name)
            if preset is not None:
                area = _preset_category(preset)
                band = get_band_for_preset_area(area)
                if band is not None:
                    return band
        except Exception:
            # Preset lookup is best-effort; fall through to policy_type.
            pass

    if policy is not None:
        raw = getattr(getattr(policy, "policy_type", None), "value", None)
        if raw:
            return get_band_for_policy_type(raw)

    return None


def format_band_caption(band: ConfidenceBand, *, prefix: str = "Model accuracy") -> str:
    """Render a human-readable one-liner for the band."""
    base = (
        f"{prefix} in {band.category} category: "
        f"±{band.mean_abs_pct_error:.1f}% mean error across "
        f"{band.n_calibrated} calibrated run{'s' if band.n_calibrated != 1 else ''}"
        f" ({band.rating_label})"
    )
    if not band.is_calibrated:
        base += (
            ". This category uses raw rate/threshold auto-population "
            "rather than a calibrated specialized validator."
        )
    return base


def estimate_uncertainty_dollars(point_estimate: float, band: ConfidenceBand) -> float:
    """Rough ± dollar interval implied by the category mean abs % error."""
    half_width = abs(point_estimate) * (band.mean_abs_pct_error / 100.0)
    return min(half_width, abs(point_estimate))


def get_credibility_for_result(
    *,
    point_estimate: float,
    policy_name: str | None = None,
    policy: Any = None,
) -> ResultCredibility | None:
    """Build credibility metadata for one scoring result."""
    band = get_band_for_result(policy_name=policy_name, policy=policy)
    if band is None:
        return None

    half_width = estimate_uncertainty_dollars(point_estimate, band)
    limitations = list(_ALL_RESULTS_LIMITATIONS)
    if not band.is_calibrated:
        limitations.extend(_GENERIC_LIMITATIONS)
    for limitation in _category_entry_limitations(band.category):
        if limitation not in limitations:
            limitations.append(limitation)

    evidence_type = (
        "specialized_benchmark_comparison"
        if band.is_calibrated
        else "generic_parameterized_estimate"
    )

    return ResultCredibility(
        category=band.category,
        evidence_type=evidence_type,
        n_benchmarks=band.n_calibrated,
        mean_abs_pct_error=band.mean_abs_pct_error,
        median_abs_pct_error=band.median_abs_pct_error,
        within_15pct=band.within_15pct,
        rating_label=band.rating_label,
        is_calibrated=band.is_calibrated,
        holdout_status=_category_holdout_status(band.category),
        uncertainty_low=point_estimate - half_width,
        uncertainty_high=point_estimate + half_width,
        limitations=limitations,
        caption=format_band_caption(band, prefix="Validation evidence"),
    )


def credibility_to_dict(credibility: ResultCredibility | None) -> dict[str, Any] | None:
    """Serialize credibility metadata for API responses."""
    if credibility is None:
        return None
    return asdict(credibility)


__all__ = [
    "POLICY_TYPE_TO_SCORECARD_CATEGORY",
    "PRESET_AREA_TO_SCORECARD_CATEGORY",
    "ConfidenceBand",
    "ResultCredibility",
    "credibility_to_dict",
    "estimate_uncertainty_dollars",
    "format_band_caption",
    "get_band_for_policy_type",
    "get_band_for_preset_area",
    "get_band_for_result",
    "get_credibility_for_result",
    "reset_confidence_cache",
]
