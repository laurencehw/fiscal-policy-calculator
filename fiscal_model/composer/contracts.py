"""
Result contracts for the policy composer.

``compose_and_score`` (fiscal_model/composer/composer.py) turns a GoalSpec
into these structures; the Package Studio tab renders them. Everything here
is plain data so mixes stay reproducible and shareable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class MixComponent:
    """One policy inside a mix.

    Revenue components come from the validated preset library and carry
    ``preset_name``; spending components are generic SpendingPolicy builds
    (uncalibrated) and carry ``preset_name=None``.
    """

    label: str                      # reader-facing name
    kind: str                       # "revenue" | "spending"
    preset_name: str | None         # PRESET_POLICIES key, None for spending
    ten_year_billions: float        # deficit convention: + increases deficit
    annual_billions: float          # average annual, same convention
    # Honesty metadata rendered as chips (may be None when untracked):
    validation_badge: dict[str, Any] | None = None   # preset_validation payload
    policy_status: Any | None = None                 # policy_status.PolicyStatus
    tier: str = "calibrated"        # "calibrated" | "generic" | "spending"


@dataclass(frozen=True)
class PolicyMix:
    """One composed package variant (e.g. "Top-heavy", "Broader base")."""

    name: str
    rationale: str                  # one sentence on how this mix reads the spec
    components: tuple[MixComponent, ...]


@dataclass(frozen=True)
class ScoredMix:
    """A mix plus its scored budget path and distributional profile."""

    mix: PolicyMix
    years: tuple[int, ...]
    # Deficit convention throughout (positive = increases the deficit):
    deficit_path_billions: tuple[float, ...]   # combined, by year
    ten_year_deficit_billions: float
    revenue_10yr_billions: float               # revenue components only (negative = raises)
    spending_10yr_billions: float              # spending components only (positive = spends)
    # Revenue-side quintile table (list of dict rows from DistributionalEngine);
    # spending incidence is NOT modeled — the tab must say so.
    revenue_distribution_rows: tuple[dict[str, Any], ...] = ()
    caveats: tuple[str, ...] = field(default_factory=tuple)


__all__ = ["MixComponent", "PolicyMix", "ScoredMix"]
