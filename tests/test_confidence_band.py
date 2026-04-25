"""
Tests for the validation-scorecard confidence band helper.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from fiscal_model.ui.confidence_band import (
    POLICY_TYPE_TO_SCORECARD_CATEGORY,
    PRESET_AREA_TO_SCORECARD_CATEGORY,
    ConfidenceBand,
    estimate_uncertainty_dollars,
    format_band_caption,
    get_band_for_policy_type,
    get_band_for_preset_area,
    get_band_for_result,
    reset_confidence_cache,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    reset_confidence_cache()
    yield
    reset_confidence_cache()


def test_get_band_for_known_preset_area_returns_calibrated_specialized():
    """Specialized validators (TCJA, Corporate, etc.) must surface as calibrated."""
    band = get_band_for_preset_area("TCJA / Individual")
    assert band is not None
    assert band.category == "TCJA"
    assert band.is_calibrated is True
    assert band.n_calibrated >= 1


def test_get_band_for_unmapped_area_falls_back_to_generic():
    band = get_band_for_preset_area("Trade / Tariffs")
    assert band is not None
    assert band.category == "Generic"
    assert band.is_calibrated is False


def test_get_band_for_none_area_returns_generic():
    """Untyped policies still get a band so the UI never has to handle a
    silent None for a calibrated path."""
    assert get_band_for_preset_area(None) is not None


def test_get_band_for_policy_type_handles_known_and_unknown():
    assert get_band_for_policy_type("corporate_tax").category == "Corporate"
    assert get_band_for_policy_type("estate_tax").category == "Estate"
    # Unknown policy_type -> Generic.
    assert get_band_for_policy_type("not_a_real_type").category == "Generic"
    # None also -> Generic.
    assert get_band_for_policy_type(None).category == "Generic"


def test_get_band_for_result_prefers_preset_category_over_policy_type():
    """A TCJAExtensionPolicy has policy_type=INCOME_TAX but should map to
    TCJA via its preset name. This is the critical bit — without preset
    routing, a calibrated TCJA result would otherwise be marked Generic."""
    policy = SimpleNamespace(policy_type=SimpleNamespace(value="income_tax"))
    band = get_band_for_result(
        policy_name="🏛️ TCJA Full Extension (CBO: $4.6T)",
        policy=policy,
    )
    assert band is not None
    assert band.category == "TCJA"
    assert band.is_calibrated is True


def test_get_band_for_result_falls_back_to_policy_type_when_no_preset():
    """Custom policies (no preset name match) should still classify."""
    policy = SimpleNamespace(policy_type=SimpleNamespace(value="corporate_tax"))
    band = get_band_for_result(
        policy_name="My One-Off Custom Corporate Hike",
        policy=policy,
    )
    assert band is not None
    assert band.category == "Corporate"


def test_get_band_for_result_returns_none_when_nothing_known():
    band = get_band_for_result(policy_name=None, policy=None)
    assert band is None


def test_format_band_caption_includes_required_fields():
    band = ConfidenceBand(
        category="TCJA",
        n_calibrated=3,
        mean_abs_pct_error=5.5,
        median_abs_pct_error=5.5,
        within_15pct=3,
        rating_label="Good",
        is_calibrated=True,
    )
    caption = format_band_caption(band)
    assert "TCJA" in caption
    assert "5.5%" in caption
    assert "3 calibrated runs" in caption
    assert "Good" in caption
    assert "uncalibrated" not in caption  # only shown for Generic


def test_format_band_caption_warns_on_uncalibrated_path():
    band = ConfidenceBand(
        category="Generic",
        n_calibrated=4,
        mean_abs_pct_error=29.0,
        median_abs_pct_error=29.0,
        within_15pct=2,
        rating_label="Limited (uncalibrated path)",
        is_calibrated=False,
    )
    caption = format_band_caption(band)
    assert "uncalibrated" in caption.lower()


def test_estimate_uncertainty_dollars_scales_with_pct_error():
    band = ConfidenceBand(
        category="TCJA",
        n_calibrated=3,
        mean_abs_pct_error=5.0,
        median_abs_pct_error=5.0,
        within_15pct=3,
        rating_label="Excellent",
        is_calibrated=True,
    )
    assert estimate_uncertainty_dollars(1000.0, band) == pytest.approx(50.0)
    # Sign of the point estimate doesn't change the half-width.
    assert estimate_uncertainty_dollars(-1000.0, band) == pytest.approx(50.0)


def test_estimate_uncertainty_caps_at_point_estimate_magnitude():
    """If a category has 200% mean error, we don't claim ±2x — the
    interval is capped so we never imply the sign could flip silently."""
    band = ConfidenceBand(
        category="Generic",
        n_calibrated=1,
        mean_abs_pct_error=200.0,
        median_abs_pct_error=200.0,
        within_15pct=0,
        rating_label="Approximate",
        is_calibrated=False,
    )
    assert estimate_uncertainty_dollars(100.0, band) == pytest.approx(100.0)


def test_mapping_dicts_cover_every_preset_area():
    """Every UI category produced by _preset_category should map somewhere."""
    from fiscal_model.app_data import PRESET_POLICIES
    from fiscal_model.ui.policy_input_presets import _preset_category

    seen_areas = {_preset_category(p) for p in PRESET_POLICIES.values()}
    missing = seen_areas - PRESET_AREA_TO_SCORECARD_CATEGORY.keys()
    assert not missing, f"preset areas missing from category map: {missing}"


def test_mapping_dicts_cover_every_policy_type_value():
    """Every PolicyType enum value must have a category mapping."""
    from fiscal_model.policies import PolicyType

    enum_values = {p.value for p in PolicyType}
    missing = enum_values - POLICY_TYPE_TO_SCORECARD_CATEGORY.keys()
    assert not missing, f"PolicyType values missing from map: {missing}"


def test_band_lookup_is_cached():
    """Repeated lookups must hit the lru_cache rather than recomputing."""
    from fiscal_model.ui.confidence_band import _category_index

    reset_confidence_cache()
    info_before = _category_index.cache_info()

    get_band_for_preset_area("TCJA / Individual")
    get_band_for_policy_type("corporate_tax")
    get_band_for_policy_type("payroll_tax")

    info_after = _category_index.cache_info()
    # One miss for the first call, two hits for the follow-ups.
    assert info_after.misses == info_before.misses + 1
    assert info_after.hits == info_before.hits + 2


def test_band_lookup_returns_none_when_compute_fails(monkeypatch):
    """A scorecard failure must not break callers — return None gracefully."""
    from fiscal_model.ui import confidence_band as module

    def _boom():
        raise RuntimeError("boom")

    monkeypatch.setattr(module, "_category_index", _boom)
    reset_confidence_cache()

    assert get_band_for_preset_area("TCJA / Individual") is None
    assert get_band_for_policy_type("corporate_tax") is None
