"""
Goal-driven policy composer — "describe what you want, get scored mixes".

Pipeline:

    user text ──(translate.py: LLM or canned fallback)──▶ GoalSpec
    GoalSpec ──(composer.py: deterministic, preset library)──▶ [PolicyMix]
    PolicyMix ──(existing FiscalPolicyScorer / DistributionalEngine)──▶ ScoredMix

The LLM appears only in the translation step; everything downstream is the
validated scoring engine, so results are reproducible and cheap.
"""

from .contracts import MixComponent, PolicyMix, ScoredMix
from .goal_spec import (
    CANNED_GOAL_SPECS,
    DEFICIT_STANCES,
    REVENUE_PHILOSOPHIES,
    SPENDING_CATEGORIES,
    GoalSpec,
    SpendingGoal,
)

__all__ = [
    "CANNED_GOAL_SPECS",
    "DEFICIT_STANCES",
    "GoalSpec",
    "MixComponent",
    "PolicyMix",
    "REVENUE_PHILOSOPHIES",
    "SPENDING_CATEGORIES",
    "ScoredMix",
    "SpendingGoal",
]
