"""
Confidence-band helper: turn the live validation scorecard into a
short, honest "expect ±X%" indicator for a given policy or bill.

The Validation tab already shows the full scorecard. This helper
lets the *Results* and *Bill Tracker* tabs reference it inline, so a
user reading "$4.6T to deficit" also sees "model averages ±5.5% on
TCJA-style policies (3 calibrated runs)" — making the headline number
defensible without forcing a tab-switch.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any


# Map preset categories from PRESET_POLICIES (`_preset_category`) to
# scorecard categories from compute_scorecard. Where no calibrated
# specialized validator exists, we fall back to ``Generic``.
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


# Map raw PolicyType enum values (as appearing on bill auto-score
# provisions) to scorecard categories.
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
    rating_label: str        # e.g., "Excellent" | "Good" | "Acceptable" | "Limited"
    is_calibrated: bool      # True for specialized categories, False for Generic


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


@lru_cache(maxsize=1)
def _category_index() -> dict[str, ConfidenceBand]:
    """Materialize the live scorecard once per process, keyed by category.

    Backed by ``cached_default_scorecard`` so the API, Validation tab,
    preset badge, and this helper all share one underlying compute per
    process.
    """
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
            # Median per-category isn't stored on the summary; approximate
            # with the mean for now (per-entry data is also available via
            # compute_scorecard().entries if a future caller needs exact
            # medians).
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


def _category_for_preset_area(area: str | None) -> str:
    if not area:
        return "Generic"
    return PRESET_AREA_TO_SCORECARD_CATEGORY.get(area, "Generic")


def _category_for_policy_type(policy_type: str | None) -> str:
    if not policy_type:
        return "Generic"
    return POLICY_TYPE_TO_SCORECARD_CATEGORY.get(policy_type, "Generic")


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
    """Resolve the most accurate band for a scoring result.

    Preference order:

    1. If ``policy_name`` matches a preset, use the preset's UI category
       (so TCJA Extension correctly maps to ``TCJA`` not ``Generic`` —
       the underlying TaxPolicy has ``policy_type=INCOME_TAX`` even
       though it has a calibrated specialized validator).
    2. Otherwise, fall back to ``policy.policy_type``.

    Returns ``None`` for results that can't be classified, or if the
    scorecard fails to compute.
    """
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
    """Render a human-readable one-liner for the band.

    Example:
        Model accuracy in TCJA category: ±5.5% mean error across
        3 calibrated runs (Excellent).
    """
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
    """Rough ± dollar interval implied by the category mean abs % error.

    Returned value is the half-width of the interval in the same units
    as ``point_estimate`` (typically billions). Capped at the magnitude
    of the point estimate so we never imply the sign could flip without
    more analysis.
    """
    half_width = abs(point_estimate) * (band.mean_abs_pct_error / 100.0)
    return min(half_width, abs(point_estimate))


__all__ = [
    "POLICY_TYPE_TO_SCORECARD_CATEGORY",
    "PRESET_AREA_TO_SCORECARD_CATEGORY",
    "ConfidenceBand",
    "estimate_uncertainty_dollars",
    "format_band_caption",
    "get_band_for_policy_type",
    "get_band_for_preset_area",
    "get_band_for_result",
    "reset_confidence_cache",
]
