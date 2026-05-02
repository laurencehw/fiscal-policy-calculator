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
from .credibility import (
    ConfidenceBand,
    ResultCredibility,
    credibility_to_dict,
    estimate_uncertainty_dollars,
    format_band_caption,
    get_band_for_policy_type,
    get_band_for_preset_area,
    get_band_for_result,
    get_credibility_for_result,
    reset_confidence_cache,
)
from .holdout import (
    DEFAULT_HOLDOUT_PROTOCOL,
    HoldoutProtocol,
    category_holdout_status,
    evidence_type_for_entry,
    holdout_entries,
    holdout_status_for_entry,
    summarize_holdout_protocol,
    validation_role_for_entry,
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

__all__ = [
    'AMT_VALIDATION_SCENARIOS_COMPARE',
    'CAPITAL_GAINS_VALIDATION_SCENARIOS',
    'CORPORATE_VALIDATION_SCENARIOS',
    'DEFAULT_HOLDOUT_PROTOCOL',
    'DEFAULT_RUNNERS',
    'ESTATE_TAX_VALIDATION_SCENARIOS',
    'KNOWN_SCORES',
    'PAYROLL_TAX_VALIDATION_SCENARIOS',
    'PTC_VALIDATION_SCENARIOS_COMPARE',
    'TAX_CREDIT_VALIDATION_SCENARIOS',
    'TAX_EXPENDITURE_VALIDATION_SCENARIOS_COMPARE',
    'TCJA_VALIDATION_SCENARIOS',
    'CBOScore',
    'ConfidenceBand',
    'HoldoutProtocol',
    'ResultCredibility',
    'ScorecardEntry',
    'ScorecardSummary',
    'ValidationResult',
    'cached_default_scorecard',
    'category_holdout_status',
    'compute_scorecard',
    'credibility_to_dict',
    'estimate_uncertainty_dollars',
    'evidence_type_for_entry',
    'format_band_caption',
    'generate_validation_report',
    'get_band_for_policy_type',
    'get_band_for_preset_area',
    'get_band_for_result',
    'get_credibility_for_result',
    'get_score',
    'get_scores_by_type',
    'holdout_entries',
    'holdout_status_for_entry',
    'list_available_policies',
    'quick_validate',
    'reset_confidence_cache',
    'reset_scorecard_cache',
    'run_validation_suite',
    'scorecard_to_dict',
    'summarize_holdout_protocol',
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
    'validate_amt_policy',
    'validate_capital_gains_policy',
    'validate_corporate_policy',
    'validate_credit_policy',
    'validate_estate_policy',
    'validate_expenditure_policy',
    'validate_payroll_policy',
    'validate_policy',
    'validate_ptc_policy',
    'validate_tcja_extension',
    'validation_role_for_entry',
]

