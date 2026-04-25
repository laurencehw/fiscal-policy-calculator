"""
Tests for the preset → validation-scorecard badge mapping.
"""

from __future__ import annotations

import pytest

from fiscal_model.app_data import PRESET_POLICIES
from fiscal_model.ui.preset_validation import (
    PRESET_TO_SCORECARD_ID,
    get_validation_badge,
    reset_scorecard_cache,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    """Make sure each test sees a fresh scorecard cache."""
    reset_scorecard_cache()
    yield
    reset_scorecard_cache()


def test_every_mapped_preset_exists_in_preset_policies():
    """The mapping cannot reference preset names that no longer exist."""
    missing = [name for name in PRESET_TO_SCORECARD_ID if name not in PRESET_POLICIES]
    assert not missing, f"Mapped presets missing from PRESET_POLICIES: {missing}"


def test_every_mapped_score_id_appears_in_scorecard():
    """The mapping cannot reference scorecard ids that no longer get computed."""
    from fiscal_model.validation import compute_scorecard

    summary = compute_scorecard()
    seen = {e.policy_id for e in summary.entries}
    missing = [
        sid for sid in PRESET_TO_SCORECARD_ID.values()
        if sid not in seen
    ]
    assert not missing, f"Mapped score ids missing from scorecard: {missing}"


def test_get_validation_badge_for_known_preset():
    badge = get_validation_badge("🏛️ TCJA Full Extension (CBO: $4.6T)")
    assert badge is not None
    assert badge["rating"] in {"Excellent", "Good", "Acceptable", "Poor", "Error"}
    assert "icon" in badge and badge["icon"]
    assert "signed_pct" in badge
    assert badge["policy_name"]


def test_get_validation_badge_unknown_preset_returns_none():
    assert get_validation_badge("Custom Policy") is None
    assert get_validation_badge("nonexistent") is None


def test_badge_lookup_is_cached():
    """Repeated lookups must hit the lru_cache rather than recomputing."""
    from fiscal_model.ui.preset_validation import _scorecard_index

    reset_scorecard_cache()
    assert _scorecard_index.cache_info().hits == 0

    get_validation_badge("🏛️ TCJA Full Extension (CBO: $4.6T)")
    get_validation_badge("🏢 Biden Corporate 28% (CBO: -$1.35T)")
    get_validation_badge("⚖️ Repeal Corporate AMT (-$220B)")

    info = _scorecard_index.cache_info()
    # One miss (first call computes), two hits for the follow-up lookups.
    assert info.misses == 1
    assert info.hits == 2


def test_badge_returns_none_when_compute_fails(monkeypatch):
    """A scorecard failure must not break the sidebar — fall back to no badge."""
    from fiscal_model.ui import preset_validation as module

    def _boom():
        raise RuntimeError("boom")

    monkeypatch.setattr(module, "_scorecard_index", _boom)
    reset_scorecard_cache()

    assert get_validation_badge("🏛️ TCJA Full Extension (CBO: $4.6T)") is None
