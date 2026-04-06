"""
Real-Time Bill Tracker for the Fiscal Policy Calculator.

Connects to congress.gov, CBO, and the calculator's scoring pipeline to
provide live tracking of legislation with fiscal implications.

Pipeline:
  Congress.gov API → BillIngestor → ProvisionMapper (LLM) → AutoScorer → BillDatabase
  CBO website       → CBOScoreFetcher ────────────────────────────────→ BillDatabase
"""

from .auto_scorer import AutoScorer, BillScore
from .cbo_fetcher import CBOCostEstimate, CBOScoreFetcher, load_fallback_estimates
from .database import BillDatabase
from .freshness import FreshnessStatus, check_freshness
from .ingestor import BillIngestor, BillMetadata
from .provision_mapper import MappingResult, ProvisionMapper

__all__ = [
    "AutoScorer",
    "BillDatabase",
    "BillIngestor",
    "BillMetadata",
    "BillScore",
    "CBOCostEstimate",
    "CBOScoreFetcher",
    "FreshnessStatus",
    "MappingResult",
    "ProvisionMapper",
    "check_freshness",
    "load_fallback_estimates",
]
