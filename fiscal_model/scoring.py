"""
Backward-compatible scoring facade.
"""

from .scoring_engine import FiscalPolicyScorer, quick_score
from .scoring_result import ScoringResult

__all__ = ["FiscalPolicyScorer", "ScoringResult", "quick_score"]
