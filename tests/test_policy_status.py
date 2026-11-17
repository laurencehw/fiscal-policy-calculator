"""Tests for the curated policy-status map ("date the law")."""

from __future__ import annotations

from fiscal_model.policy_status import (
    POLICY_STATUS_MAP,
    PRE_2025_SCORE_SENTENCE,
    PolicyStatus,
    get_policy_status,
    scored_on_current_baseline,
)
from fiscal_model.preset_ids import CATALOG_PRESET_IDS, PRESET_ID_BY_LABEL

# JCX-35-25 rows that overtook these presets. Scores are not recomputed.
_PL119_21_NOT_ON_CURRENT_BASELINE = {
    "tcja-full-extension": "superseded",  # rates, std. deduction, CTC, QBI, estate, AMT
    "tcja-rates-only": "superseded",  # Ch.1 item 1, rate schedule made permanent
    "tcja-extension-no-salt-cap": "superseded",  # extension happened; unlimited SALT did not
    "estate-extend-tcja": "superseded",  # Ch.1 item 6, $15M exemption
    "amt-extend-tcja-relief": "superseded",  # Ch.1 item 7, AMT exemption extended
    "ctc-extension": "superseded",  # Ch.1 item 4, CTC extended (to $2,200, indexed)
    "ev-credit-repeal": "superseded",  # Ch.5 A.2/A.3, clean-vehicle credits terminated
    "ira-clean-energy-repeal": "partially",  # Ch.5 subchapter A terminated many, not all
}


def test_every_status_key_is_a_real_preset():
    """A renamed preset must not silently orphan its status curation."""
    unknown = [preset_id for preset_id in POLICY_STATUS_MAP if preset_id not in CATALOG_PRESET_IDS]
    assert unknown == [], f"status entries for unknown presets: {unknown}"


def test_statuses_are_valid_and_carry_notes():
    valid = {"proposed", "enacted", "superseded", "partially"}
    for preset_id, status in POLICY_STATUS_MAP.items():
        assert status.status in valid, preset_id
        assert status.note, preset_id
        assert status.label
        assert status.badge
        assert status.icon


def test_lookup_accepts_stable_id_and_display_label():
    by_id = get_policy_status("tcja-full-extension")
    by_label = get_policy_status("🏛️ TCJA Full Extension (CBO: $4.6T)")
    assert by_id is not None and by_id is by_label
    assert by_id.status == "superseded"
    assert by_id.badge == "Superseded by P.L. 119-21"
    assert not by_id.on_current_baseline
    assert "July 2025" in by_id.note


def test_pl119_21_presets_that_price_what_the_baseline_already_contains():
    """The eight Explore scores that still answer a pre-2025-law question."""
    assert {
        preset_id: get_policy_status(preset_id).status  # type: ignore[union-attr]
        for preset_id in _PL119_21_NOT_ON_CURRENT_BASELINE
    } == _PL119_21_NOT_ON_CURRENT_BASELINE
    off_baseline = {
        preset_id
        for preset_id, status in POLICY_STATUS_MAP.items()
        if not status.on_current_baseline
    }
    assert off_baseline == set(_PL119_21_NOT_ON_CURRENT_BASELINE)
    for preset_id in off_baseline:
        status = POLICY_STATUS_MAP[preset_id]
        assert status.law == "P.L. 119-21"
        assert "P.L. 119-21" in status.badge
        exported = status.to_export()
        assert exported["on_current_baseline"] is False
        assert exported["baseline_sentence"] == PRE_2025_SCORE_SENTENCE
        assert not scored_on_current_baseline(preset_id)
        label = next(name for name, pid in PRESET_ID_BY_LABEL.items() if pid == preset_id)
        assert not scored_on_current_baseline(label)


def test_salt_cap_repeal_is_superseded_but_scored_on_current_law():
    """PR #161 moved the score onto the $40k current-law cap; do not relabel it."""
    status = get_policy_status("salt-cap-repeal")
    assert status is not None
    assert status.status == "superseded"
    assert status.on_current_baseline
    assert status.to_export()["baseline_sentence"] is None
    assert scored_on_current_baseline("salt-cap-repeal")


def test_ev_credits_were_terminated_ira_repeal_was_not_complete():
    ev = get_policy_status("ev-credit-repeal")
    ira = get_policy_status("ira-clean-energy-repeal")
    assert ev is not None and ev.status == "superseded"
    assert ira is not None and ira.status == "partially"
    assert ira.badge == "Partly overtaken by P.L. 119-21"
    assert "terminated many" in ira.note.lower() or "not the full repeal" in ira.note.lower()


def test_green_book_proposals_marked_proposed():
    for preset_id in ("corporate-28pct", "estate-exemption-3-5m", "international-package"):
        status = get_policy_status(preset_id)
        assert status is not None and status.status == "proposed", preset_id
        assert status.on_current_baseline


def test_unknown_preset_returns_none():
    assert get_policy_status("Custom Policy") is None
    assert get_policy_status(None) is None
    assert get_policy_status("Not A Preset") is None
    assert scored_on_current_baseline("Custom Policy")
    assert scored_on_current_baseline(None)


def test_status_dataclass_is_frozen():
    from dataclasses import FrozenInstanceError

    import pytest

    status = PolicyStatus("proposed", "note")
    with pytest.raises(FrozenInstanceError):
        status.status = "enacted"  # type: ignore[misc]
