"""Tests for the curated policy-status map ("date the law")."""

from __future__ import annotations

from fiscal_model.app_data import PRESET_POLICIES
from fiscal_model.policy_status import (
    POLICY_STATUS_MAP,
    PolicyStatus,
    get_policy_status,
)


def test_every_status_key_is_a_real_preset():
    """A renamed preset must not silently orphan its status curation."""
    unknown = [name for name in POLICY_STATUS_MAP if name not in PRESET_POLICIES]
    assert unknown == [], f"status entries for unknown presets: {unknown}"


def test_statuses_are_valid_and_carry_notes():
    valid = {"proposed", "enacted", "superseded", "partially"}
    for name, status in POLICY_STATUS_MAP.items():
        assert status.status in valid, name
        assert status.note, name
        assert status.label
        assert status.icon


def test_tcja_extension_is_superseded():
    status = get_policy_status("🏛️ TCJA Full Extension (CBO: $4.6T)")
    assert status is not None
    assert status.status == "superseded"
    assert "July 2025" in status.note


def test_green_book_proposals_marked_proposed():
    for name in (
        "🏢 Biden Corporate 28% (CBO: -$1.35T)",
        "🏠 Biden Estate Reform (-$450B)",
        "🌍 Biden International Package (-$700B)",
    ):
        status = get_policy_status(name)
        assert status is not None and status.status == "proposed", name


def test_unknown_preset_returns_none():
    assert get_policy_status("Custom Policy") is None
    assert get_policy_status(None) is None
    assert get_policy_status("Not A Preset") is None


def test_status_dataclass_is_frozen():
    from dataclasses import FrozenInstanceError

    import pytest

    status = PolicyStatus("proposed", "note")
    with pytest.raises(FrozenInstanceError):
        status.status = "enacted"  # type: ignore[misc]
