"""
Tests for the locked validation holdout protocol.
"""

from __future__ import annotations

from fiscal_model.validation.holdout import (
    DEFAULT_HOLDOUT_PROTOCOL,
    category_holdout_status,
    evidence_type_for_entry,
    holdout_entries,
    summarize_holdout_protocol,
    validation_role_for_entry,
)
from fiscal_model.validation.scorecard import cached_default_scorecard


def test_locked_holdout_policy_ids_exist_in_live_scorecard():
    summary = cached_default_scorecard()
    live_ids = {entry.policy_id for entry in summary.entries}

    assert DEFAULT_HOLDOUT_PROTOCOL.holdout_policy_ids <= live_ids


def test_holdout_protocol_covers_required_categories():
    summary = cached_default_scorecard()
    details = summarize_holdout_protocol(list(summary.entries))

    assert details["holdout_entries"] >= details["minimum_holdout_entries"]
    assert details["missing_policy_ids"] == []
    assert details["missing_categories"] == []
    assert details["failing_policy_ids"] == []


def test_a_poor_holdout_entry_must_carry_its_reason_to_be_tolerated():
    """The protocol was locked on 2026-05-02 over a scorecard in which every
    capital-gains scenario carried its own fitted elasticity/lock-in tuple.
    Wave 2's L1 deleted those tuples, so ``pwbm_39_with_stepup`` is now scored
    by one frozen literature set and rates Poor - with the direction right,
    which the old calibration needed a 5.3x multiplier to achieve. It stays in
    the battery: removing it to go green is the failure mode the protocol
    exists to prevent. What it must do instead is say why, in
    ``known_limitations``, which is the same bar ``_scorecard_checks`` already
    holds a documented Poor entry to. A Poor entry with nothing written down
    still lands in ``failing_policy_ids`` and still fails readiness.
    """
    summary = cached_default_scorecard()
    details = summarize_holdout_protocol(list(summary.entries))

    for policy_id in details["documented_poor_policy_ids"]:
        entry = next(e for e in summary.entries if e.policy_id == policy_id)
        assert entry.known_limitations
        assert entry.direction_match


def test_holdout_roles_and_evidence_types_are_entry_specific():
    summary = cached_default_scorecard()
    holdout = holdout_entries(list(summary.entries))[0]
    generic = next(entry for entry in summary.entries if entry.category == "Generic")
    calibrated = next(
        entry for entry in summary.entries
        if entry.category != "Generic" and entry.policy_id not in DEFAULT_HOLDOUT_PROTOCOL.holdout_policy_ids
    )

    assert validation_role_for_entry(holdout) == "post_lock_holdout"
    assert evidence_type_for_entry(holdout) == "locked_holdout_benchmark"
    assert validation_role_for_entry(generic) == "generic_reference"
    assert evidence_type_for_entry(generic) == "generic_parameterized_estimate"
    assert validation_role_for_entry(calibrated) == "calibration_reference"
    assert evidence_type_for_entry(calibrated) == "specialized_benchmark_comparison"


def test_category_holdout_status_distinguishes_generic_and_covered_categories():
    summary = cached_default_scorecard()

    assert category_holdout_status("Generic", list(summary.entries)) == "not_applicable_generic"
    assert category_holdout_status("Credits", list(summary.entries)) == "post_lock_holdout_available"
