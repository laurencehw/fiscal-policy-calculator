"""
Validation module for comparing model outputs to published CBO scores.

This module provides:
- Database of known CBO/JCT revenue estimates
- Comparison functions for accuracy analysis
- Validation reports
"""

from .cbo_scores import (
    CBOScore,
    KNOWN_SCORES,
    get_score,
    get_scores_by_type,
    list_available_policies,
)

from .compare import (
    ValidationResult,
    validate_policy,
    validate_all,
    run_validation_suite,
    generate_validation_report,
    quick_validate,
)

__all__ = [
    # Score database
    'CBOScore',
    'KNOWN_SCORES',
    'get_score',
    'get_scores_by_type',
    'list_available_policies',
    # Comparison
    'ValidationResult',
    'validate_policy',
    'validate_all',
    'run_validation_suite',
    'generate_validation_report',
    'quick_validate',
]

