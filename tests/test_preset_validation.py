"""
Tests for the preset → validation-scorecard badge mapping.

Addressed by **stable preset id** wherever possible: the display labels embed
the official score and move whenever a target does, so a test keyed on a label
breaks on a rename that is not a defect.
"""

from __future__ import annotations

import pytest

from fiscal_model.app_data import PRESET_POLICIES
from fiscal_model.preset_ids import PRESET_ID_BY_LABEL, label_for_preset_id
from fiscal_model.ui.preset_validation import (
    BADGE_SCORECARD_ID_BY_LABEL,
    LEGACY_CALIBRATED_PRESET_IDS,
    PRESET_ID_TO_SCORECARD_ID,
    PRESET_TO_SCORECARD_ID,
    TIER_FITTED,
    TIER_OUT_OF_SAMPLE,
    TIER_RECONSTRUCTION,
    badge_tier,
    get_validation_badge,
    is_calibrated_reference,
    reset_scorecard_cache,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    """Make sure each test sees a fresh scorecard cache."""
    reset_scorecard_cache()
    yield
    reset_scorecard_cache()


def test_every_mapped_preset_exists_in_the_catalog():
    """The mapping cannot reference presets that no longer exist."""
    known = set(PRESET_ID_BY_LABEL.values())
    missing = [pid for pid in PRESET_ID_TO_SCORECARD_ID if pid not in known]
    assert not missing, f"Mapped preset ids missing from preset_ids: {missing}"

    missing_labels = [
        name for name in BADGE_SCORECARD_ID_BY_LABEL if name not in PRESET_POLICIES
    ]
    assert not missing_labels, f"Mapped labels missing from the catalog: {missing_labels}"


def test_every_mapped_score_id_appears_in_scorecard():
    """The mapping cannot reference scorecard ids that no longer get computed."""
    from fiscal_model.validation import compute_scorecard

    summary = compute_scorecard()
    seen = {e.policy_id for e in summary.entries}
    missing = [sid for sid in PRESET_ID_TO_SCORECARD_ID.values() if sid not in seen]
    assert not missing, f"Mapped score ids missing from scorecard: {missing}"


def test_the_label_views_are_derived_from_the_id_map():
    """Labels are a view, never a second source of truth.

    H1 is renaming five preset labels in a parallel lane; a label-keyed map
    would drop those entries on merge without anything noticing.
    """
    assert BADGE_SCORECARD_ID_BY_LABEL == {
        label_for_preset_id(pid): sid for pid, sid in PRESET_ID_TO_SCORECARD_ID.items()
    }
    assert PRESET_TO_SCORECARD_ID == {
        label_for_preset_id(pid): sid
        for pid, sid in PRESET_ID_TO_SCORECARD_ID.items()
        if pid in LEGACY_CALIBRATED_PRESET_IDS
    }


def test_the_legacy_map_keeps_the_members_two_other_modules_read():
    """``composer._tier_for`` and ``results_summary._resolve_tier`` read this
    map's *membership* as "calibrated reference". Widening it would relabel
    every tariff, pharma and enforcement preset on a user-visible surface, so
    the new coverage lives in the id map instead. Pinned so that a later widening
    is a deliberate act with those two call sites moved in the same commit."""
    assert len(PRESET_TO_SCORECARD_ID) == 24
    assert len(PRESET_ID_TO_SCORECARD_ID) == 44
    assert LEGACY_CALIBRATED_PRESET_IDS <= set(PRESET_ID_TO_SCORECARD_ID)


def test_get_validation_badge_accepts_an_id_or_a_label():
    by_id = get_validation_badge("tcja-full-extension")
    by_label = get_validation_badge(label_for_preset_id("tcja-full-extension"))
    assert by_id == by_label
    assert by_id is not None
    assert by_id["rating"] in {"Excellent", "Good", "Acceptable", "Poor", "Error"}
    assert by_id["icon"]
    assert "signed_pct" in by_id
    assert by_id["policy_name"]


def test_get_validation_badge_unknown_preset_returns_none():
    assert get_validation_badge("Custom Policy") is None
    assert get_validation_badge("nonexistent") is None


def test_a_fitted_badge_says_calibrated_rather_than_excellent():
    """The rating on a fitted row is measuring arithmetic — the constant was set
    to the target. "Estate: n=3, 0.0%, Excellent" is the failure mode.

    The example was the SS donut until H9 moved its target onto CBO Option 62
    alternative 2 and it left the fitted tier; the cap-elimination preset's
    target was examined and left, so it is still fitted."""
    badge = get_validation_badge("ss-cap-eliminate")
    assert badge is not None
    assert badge["tier"] == TIER_FITTED
    assert badge["rating"] == "Excellent"  # the underlying figure is unchanged
    assert badge["rating_label"] == "Calibrated"
    assert "Excellent" not in badge["caption"]
    assert "by construction" in badge["caption"]
    assert is_calibrated_reference("ss-cap-eliminate")


def test_a_reconstruction_badge_says_it_is_unfitted_and_prints_its_error():
    badge = get_validation_badge("drug-reference-pricing")
    assert badge is not None
    assert badge["tier"] == TIER_RECONSTRUCTION
    assert badge["rating_label"] == "Poor"
    assert "Unfitted reconstruction" in badge["caption"]
    assert "701.0%" in badge["caption"]
    assert not is_calibrated_reference("drug-reference-pricing")


def test_a_tier_1_row_is_reported_as_out_of_sample_not_as_fitted():
    """A ``Generic`` row carries ``calibrated_to_target=True`` by default, so a
    tier resolved off the flag alone would report the repository's only
    out-of-sample predictions as fitted ones."""
    badge = get_validation_badge("medicare-surcharge-2pp")
    assert badge is not None
    assert badge["category"] == "Generic"
    assert badge["calibrated_to_target"] is True
    assert badge["tier"] == TIER_OUT_OF_SAMPLE
    assert "Out-of-sample prediction" in badge["caption"]
    assert "pre-registered" in badge["caption"]


def test_a_range_target_reports_containment_rather_than_a_percentage():
    inside = get_validation_badge("pillar-two-adoption")
    assert inside is not None
    assert inside["within_range"] is True
    assert inside["rating_label"] == "Within published range"
    assert "not a measure of accuracy" in inside["caption"]

    outside = get_validation_badge("corporate-15pct")
    assert outside is not None
    assert outside["within_range"] is False
    assert "outside it" in outside["caption"]


def test_small_amounts_keep_a_decimal_so_a_distance_is_not_rounded_away():
    """``_money`` prints a *distance to a published range* as well as a target,
    and whole billions are the wrong resolution for one: ``reciprocal_tariffs``
    sits $3.2B outside its nearer bound, and "$3B" understates it while a
    sub-$0.5B distance would print "$0B" — which reads as *inside* the range,
    the one thing the field exists to distinguish."""
    from fiscal_model.ui.preset_validation import _money

    assert _money(3.2) == "$3.2B"
    assert _money(-3.2) == "-$3.2B"
    assert _money(0.4) == "$0.4B"
    assert _money(0.0) == "$0.0B"
    # At and above $10B whole billions are right, and the big end is unchanged.
    assert _money(11.4) == "$11B"
    assert _money(162.6) == "$163B"
    assert _money(-1347.0) == "-$1.35T"


def test_the_reciprocal_tariff_distance_survives_into_the_caption():
    """The end-to-end version of the case above, on the row that has it."""
    badge = get_validation_badge("tariff-reciprocal")
    assert badge is not None
    assert badge["within_range"] is False
    assert "$3.2B" in badge["caption"], badge["caption"]


def test_a_model_estimate_target_says_so():
    """Six calibrated rows score the repository against its own output."""
    badge = get_validation_badge("drug-negotiation-expand")
    assert badge is not None
    assert badge["provenance"] == "model_estimate"
    assert "this model's own estimate" in badge["caption"]


def test_badge_tier_for_a_preset_with_no_row():
    assert badge_tier("across-the-board-rate-cut-5pp") == "no_row"
    assert not is_calibrated_reference("across-the-board-rate-cut-5pp")


def test_badge_lookup_is_cached():
    """Repeated lookups must hit the lru_cache rather than recomputing.

    The scorecard costs ~6.5s on a scored route (MODELING_IMPROVEMENT §6.2 item
    39); nothing this lane added may buy a second one.
    """
    from fiscal_model.ui.preset_validation import _scorecard_index

    reset_scorecard_cache()
    assert _scorecard_index.cache_info().hits == 0

    get_validation_badge("tcja-full-extension")
    get_validation_badge("corporate-28pct")
    get_validation_badge("amt-repeal-corporate")
    badge_tier("tariff-universal-10pct")

    info = _scorecard_index.cache_info()
    # One miss (first call computes), three hits for the follow-up lookups.
    assert info.misses == 1
    assert info.hits == 3


def test_badge_returns_none_when_compute_fails(monkeypatch):
    """A scorecard failure must not break the sidebar — fall back to no badge."""
    from fiscal_model.ui import preset_validation as module

    def _boom():
        raise RuntimeError("boom")

    monkeypatch.setattr(module, "_scorecard_index", _boom)
    reset_scorecard_cache()

    assert get_validation_badge("tcja-full-extension") is None
