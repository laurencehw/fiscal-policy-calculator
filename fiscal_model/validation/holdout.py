"""
Locked validation holdout protocol.

The existing scorecard was built from published benchmark comparisons. This
module records the post-lock split used for release regression checks: some
specialized benchmarks remain calibration references, while a fixed subset is
reserved as holdout checkpoints for future model changes.

Important boundary: this is a post-lock regression holdout. It prevents future
changes from quietly overfitting to every benchmark, but it is not a claim that
the current historical estimates were developed without seeing these targets.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Literal

ValidationRole = Literal[
    "calibration_reference",
    "post_lock_holdout",
    "generic_reference",
]


@dataclass(frozen=True)
class HoldoutProtocol:
    """Manifest describing the locked scorecard split."""

    protocol_id: str
    locked_at: str
    description: str
    holdout_policy_ids: frozenset[str]
    minimum_holdout_entries: int
    required_categories: frozenset[str] = field(default_factory=frozenset)


DEFAULT_HOLDOUT_PROTOCOL = HoldoutProtocol(
    protocol_id="revenue-scorecard-post-lock-2026-05-02",
    locked_at="2026-05-02",
    description=(
        "Post-lock revenue scorecard split. Holdout entries are frozen "
        "regression checkpoints for future scoring changes; they are not "
        "retroactive proof of historical out-of-sample performance."
    ),
    minimum_holdout_entries=8,
    required_categories=frozenset({
        "Credits",
        "Estate",
        "Payroll",
        "AMT",
        "PTC",
        "CapitalGains",
        "Expenditures",
    }),
    holdout_policy_ids=frozenset({
        "biden_eitc_childless",
        "extend_tcja_exemption",
        "ss_cap_90_pct",
        "repeal_individual_amt",
        "repeal_corporate_amt",
        "repeal_ptc",
        "pwbm_39_with_stepup",
        "eliminate_mortgage",
        "repeal_salt_cap",
        "cap_charitable",
    }),
)


def validation_role_for_entry(
    entry: Any,
    *,
    protocol: HoldoutProtocol = DEFAULT_HOLDOUT_PROTOCOL,
) -> ValidationRole:
    """Classify a scorecard entry under the locked protocol."""
    if getattr(entry, "category", None) == "Generic":
        return "generic_reference"
    if getattr(entry, "policy_id", None) in protocol.holdout_policy_ids:
        return "post_lock_holdout"
    return "calibration_reference"


def holdout_status_for_entry(entry: Any) -> str:
    """API-facing holdout status for one scorecard entry."""
    return validation_role_for_entry(entry)


def evidence_type_for_entry(entry: Any) -> str:
    """API-facing evidence type for one scorecard entry."""
    role = validation_role_for_entry(entry)
    if role == "post_lock_holdout":
        return "locked_holdout_benchmark"
    if role == "generic_reference":
        return "generic_parameterized_estimate"
    return "specialized_benchmark_comparison"


def holdout_entries(entries: list[Any]) -> list[Any]:
    """Return scorecard entries marked as post-lock holdouts."""
    return [
        entry for entry in entries
        if validation_role_for_entry(entry) == "post_lock_holdout"
    ]


def category_holdout_status(category: str, entries: list[Any]) -> str:
    """Category-level holdout availability for result credibility metadata."""
    category_entries = [entry for entry in entries if getattr(entry, "category", None) == category]
    if category == "Generic":
        return "not_applicable_generic"
    if any(validation_role_for_entry(entry) == "post_lock_holdout" for entry in category_entries):
        return "post_lock_holdout_available"
    if category_entries:
        return "calibration_reference_only"
    return "unknown"


def summarize_holdout_protocol(
    entries: list[Any],
    *,
    protocol: HoldoutProtocol = DEFAULT_HOLDOUT_PROTOCOL,
) -> dict[str, Any]:
    """Build a compact validation summary for readiness and APIs."""
    live_ids = {getattr(entry, "policy_id", "") for entry in entries}
    missing_ids = sorted(protocol.holdout_policy_ids - live_ids)
    matched_entries = holdout_entries(entries)
    categories = Counter(getattr(entry, "category", "Unknown") for entry in matched_entries)
    ratings = Counter(getattr(entry, "rating", "Unknown") for entry in matched_entries)
    missing_categories = sorted(protocol.required_categories - set(categories))
    failing_entries = [
        entry for entry in matched_entries
        if getattr(entry, "rating", None) in {"Error", "Poor"}
        or not getattr(entry, "direction_match", True)
    ]

    return {
        "protocol_id": protocol.protocol_id,
        "locked_at": protocol.locked_at,
        "description": protocol.description,
        "holdout_entries": len(matched_entries),
        "minimum_holdout_entries": protocol.minimum_holdout_entries,
        "holdout_policy_ids": [getattr(entry, "policy_id", "unknown") for entry in matched_entries],
        "missing_policy_ids": missing_ids,
        "required_categories": sorted(protocol.required_categories),
        "covered_categories": dict(sorted(categories.items())),
        "missing_categories": missing_categories,
        "ratings": dict(sorted(ratings.items())),
        "failing_policy_ids": [
            getattr(entry, "policy_id", "unknown") for entry in failing_entries
        ],
    }


__all__ = [
    "DEFAULT_HOLDOUT_PROTOCOL",
    "HoldoutProtocol",
    "ValidationRole",
    "category_holdout_status",
    "evidence_type_for_entry",
    "holdout_entries",
    "holdout_status_for_entry",
    "summarize_holdout_protocol",
    "validation_role_for_entry",
]
