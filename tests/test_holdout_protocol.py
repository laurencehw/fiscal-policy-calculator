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
