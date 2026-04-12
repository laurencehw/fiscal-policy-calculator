"""
Backward-compatible facade for distributional analysis.

The implementation now lives in focused modules:
- `distribution_core.py` for types and constants
- `distribution_grouping.py` for bucket construction helpers
- `distribution_effects.py` for policy-specific calculations
- `distribution_engine.py` for orchestration
- `distribution_reporting.py` for table/summary output
"""

from .distribution_core import (
    DECILE_THRESHOLDS_2024,
    JCT_DOLLAR_BRACKETS,
    QUINTILE_THRESHOLDS_2024,
    TOP_INCOME_THRESHOLDS_2024,
    DistributionalAnalysis,
    DistributionalResult,
    IncomeGroup,
    IncomeGroupType,
)
from .distribution_engine import DistributionalEngine
from .distribution_reporting import (
    format_distribution_table,
    generate_winners_losers_summary,
)

__all__ = [
    "DECILE_THRESHOLDS_2024",
    "JCT_DOLLAR_BRACKETS",
    "QUINTILE_THRESHOLDS_2024",
    "TOP_INCOME_THRESHOLDS_2024",
    "DistributionalAnalysis",
    "DistributionalEngine",
    "DistributionalResult",
    "IncomeGroup",
    "IncomeGroupType",
    "format_distribution_table",
    "generate_winners_losers_summary",
]
