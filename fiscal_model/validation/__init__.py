"""
Validation module for comparing model outputs to published CBO scores.

This module provides:
- Database of known CBO/JCT revenue estimates
- Comparison functions for accuracy analysis
- Validation reports
"""

from .cbo_scores import (
    KNOWN_SCORES,
    CBOScore,
    get_score,
    get_scores_by_type,
    list_available_policies,
)
from .scorecard import (
    DEFAULT_RUNNERS,
    ScorecardEntry,
    ScorecardSummary,
    cached_default_scorecard,
    compute_scorecard,
    reset_scorecard_cache,
    scorecard_to_dict,
)
from .compare import (
    AMT_VALIDATION_SCENARIOS_COMPARE,
    CAPITAL_GAINS_VALIDATION_SCENARIOS,
    CORPORATE_VALIDATION_SCENARIOS,
    ESTATE_TAX_VALIDATION_SCENARIOS,
    PAYROLL_TAX_VALIDATION_SCENARIOS,
    PTC_VALIDATION_SCENARIOS_COMPARE,
    TAX_CREDIT_VALIDATION_SCENARIOS,
    TAX_EXPENDITURE_VALIDATION_SCENARIOS_COMPARE,
    TCJA_VALIDATION_SCENARIOS,
    ValidationResult,
    generate_validation_report,
    quick_validate,
    run_validation_suite,
    validate_all,
    validate_all_amt,
    validate_all_capital_gains,
    validate_all_corporate,
    validate_all_credits,
    validate_all_estate,
    validate_all_expenditures,
    validate_all_payroll,
    validate_all_ptc,
    validate_all_tcja,
    # AMT validation
    validate_amt_policy,
    # Capital gains validation
    validate_capital_gains_policy,
    # Corporate tax validation
    validate_corporate_policy,
    # Tax credit validation
    validate_credit_policy,
    # Estate tax validation
    validate_estate_policy,
    # Tax expenditure validation
    validate_expenditure_policy,
    # Payroll tax validation
    validate_payroll_policy,
    validate_policy,
    # PTC validation
    validate_ptc_policy,
    # TCJA validation
    validate_tcja_extension,
)

__all__ = [
    'DEFAULT_RUNNERS',
    'ScorecardEntry',
    'ScorecardSummary',
    'cached_default_scorecard',
    'compute_scorecard',
    'reset_scorecard_cache',
    'scorecard_to_dict',
    'AMT_VALIDATION_SCENARIOS_COMPARE',
    'CAPITAL_GAINS_VALIDATION_SCENARIOS',
    'CORPORATE_VALIDATION_SCENARIOS',
    'ESTATE_TAX_VALIDATION_SCENARIOS',
    'KNOWN_SCORES',
    'PAYROLL_TAX_VALIDATION_SCENARIOS',
    'PTC_VALIDATION_SCENARIOS_COMPARE',
    'TAX_CREDIT_VALIDATION_SCENARIOS',
    'TAX_EXPENDITURE_VALIDATION_SCENARIOS_COMPARE',
    'TCJA_VALIDATION_SCENARIOS',
    # Score database
    'CBOScore',
    # Comparison
    'ValidationResult',
    'generate_validation_report',
    'get_score',
    'get_scores_by_type',
    'list_available_policies',
    'quick_validate',
    'run_validation_suite',
    'validate_all',
    'validate_all_amt',
    'validate_all_capital_gains',
    'validate_all_corporate',
    'validate_all_credits',
    'validate_all_estate',
    'validate_all_expenditures',
    'validate_all_payroll',
    'validate_all_ptc',
    'validate_all_tcja',
    # AMT validation
    'validate_amt_policy',
    # Capital gains validation
    'validate_capital_gains_policy',
    # Corporate tax validation
    'validate_corporate_policy',
    # Tax credit validation
    'validate_credit_policy',
    # Estate tax validation
    'validate_estate_policy',
    # Tax expenditure validation
    'validate_expenditure_policy',
    # Payroll tax validation
    'validate_payroll_policy',
    'validate_policy',
    # PTC validation
    'validate_ptc_policy',
    # TCJA validation
    'validate_tcja_extension',
]

