"""Mapping-confidence rules for the bill tracker.

A bill is never "high" confidence when only some of its provisions are mapped.
The coverage label (``N of M provisions mapped``) is what the UI prints next
to the confidence word.
"""

from __future__ import annotations

from typing import Any


def split_provisions(
    policies: list[dict[str, Any]] | None,
    unmapped_provisions: list[str] | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Return ``(mapped_policy_dicts, unmapped_texts)``."""
    mapped: list[dict[str, Any]] = []
    unmapped: list[str] = []
    for policy in policies or []:
        if not isinstance(policy, dict):
            continue
        if policy.get("mapped") is False or policy.get("policy_type") == "other":
            text = str(policy.get("provision_text") or policy.get("parameters", {}).get("description") or "")
            if text:
                unmapped.append(text)
        else:
            mapped.append(policy)
    for text in unmapped_provisions or []:
        if text and text not in unmapped:
            unmapped.append(text)
    return mapped, unmapped


def coverage_label(mapped_count: int, unmapped_count: int) -> str:
    total = mapped_count + unmapped_count
    if total <= 0:
        return "no provisions mapped"
    return f"{mapped_count} of {total} provisions mapped"


def coverage_from_policies(
    policies: list[dict[str, Any]] | None,
    unmapped_provisions: list[str] | None = None,
) -> dict[str, Any]:
    mapped, unmapped = split_provisions(policies, unmapped_provisions)
    return {
        "mapped_count": len(mapped),
        "unmapped_count": len(unmapped),
        "label": coverage_label(len(mapped), len(unmapped)),
    }


def mapping_confidence(
    policies: list[dict[str, Any]] | None,
    unmapped_provisions: list[str] | None = None,
) -> tuple[str, str]:
    """Return ``(confidence, reason)``. Confidence is never high if anything is unmapped."""
    mapped, unmapped = split_provisions(policies, unmapped_provisions)
    label = coverage_label(len(mapped), len(unmapped))
    if not mapped:
        return "low", f"No scoreable provisions identified; {label}"
    flags = [str(p.get("confidence") or "high") for p in mapped]
    if unmapped:
        if any(flag == "low" for flag in flags):
            return "low", f"Partial mapping with low-confidence provisions; {label}"
        return "medium", f"Partial mapping; {label}"
    if any(flag == "low" for flag in flags):
        return "low", f"One or more provisions have low confidence; {label}"
    if all(flag == "high" for flag in flags):
        return "high", f"{len(mapped)} provision(s) extracted with high confidence; {label}"
    return "medium", f"{len(mapped)} provision(s) extracted with mixed confidence; {label}"


def unmapped_policy_dicts(unmapped_provisions: list[str]) -> list[dict[str, Any]]:
    """Entries stored in ``policies_json`` so coverage survives a round-trip."""
    return [
        {
            "policy_type": "other",
            "mapped": False,
            "confidence": "low",
            "provision_text": text,
            "parameters": {},
        }
        for text in unmapped_provisions
        if text
    ]
