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
    # Capital gains validation
    validate_capital_gains_policy,
    validate_all_capital_gains,
    CAPITAL_GAINS_VALIDATION_SCENARIOS,
    # TCJA validation
    validate_tcja_extension,
    validate_all_tcja,
    TCJA_VALIDATION_SCENARIOS,
    # Corporate tax validation
    validate_corporate_policy,
    validate_all_corporate,
    CORPORATE_VALIDATION_SCENARIOS,
    # Tax credit validation
    validate_credit_policy,
    validate_all_credits,
    TAX_CREDIT_VALIDATION_SCENARIOS,
    # Estate tax validation
    validate_estate_policy,
    validate_all_estate,
    ESTATE_TAX_VALIDATION_SCENARIOS,
    # Payroll tax validation
    validate_payroll_policy,
    validate_all_payroll,
    PAYROLL_TAX_VALIDATION_SCENARIOS,
    # AMT validation
    validate_amt_policy,
    validate_all_amt,
    AMT_VALIDATION_SCENARIOS_COMPARE,
    # PTC validation
    validate_ptc_policy,
    validate_all_ptc,
    PTC_VALIDATION_SCENARIOS_COMPARE,
    # Tax expenditure validation
    validate_expenditure_policy,
    validate_all_expenditures,
    TAX_EXPENDITURE_VALIDATION_SCENARIOS_COMPARE,
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
    # Capital gains validation
    'validate_capital_gains_policy',
    'validate_all_capital_gains',
    'CAPITAL_GAINS_VALIDATION_SCENARIOS',
    # TCJA validation
    'validate_tcja_extension',
    'validate_all_tcja',
    'TCJA_VALIDATION_SCENARIOS',
    # Corporate tax validation
    'validate_corporate_policy',
    'validate_all_corporate',
    'CORPORATE_VALIDATION_SCENARIOS',
    # Tax credit validation
    'validate_credit_policy',
    'validate_all_credits',
    'TAX_CREDIT_VALIDATION_SCENARIOS',
    # Estate tax validation
    'validate_estate_policy',
    'validate_all_estate',
    'ESTATE_TAX_VALIDATION_SCENARIOS',
    # Payroll tax validation
    'validate_payroll_policy',
    'validate_all_payroll',
    'PAYROLL_TAX_VALIDATION_SCENARIOS',
    # AMT validation
    'validate_amt_policy',
    'validate_all_amt',
    'AMT_VALIDATION_SCENARIOS_COMPARE',
    # PTC validation
    'validate_ptc_policy',
    'validate_all_ptc',
    'PTC_VALIDATION_SCENARIOS_COMPARE',
    # Tax expenditure validation
    'validate_expenditure_policy',
    'validate_all_expenditures',
    'TAX_EXPENDITURE_VALIDATION_SCENARIOS_COMPARE',
]

