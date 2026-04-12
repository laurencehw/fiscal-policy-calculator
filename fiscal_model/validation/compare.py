"""
Backward-compatible facade for validation helpers.

The validation implementation now lives in smaller modules:
- `core.py` for shared result types and generic validation helpers
- `reporting.py` for markdown report rendering
- `scenarios.py` for specialized validation scenario registries
- `specialized.py` for category-specific validation runners
"""

from .core import (
    ValidationResult,
    _rate_accuracy,
    create_capital_gains_example_from_score,
    create_capital_gains_policy_from_score,
    create_policy_from_score,
    quick_validate,
    run_validation_suite,
    validate_all,
    validate_policy,
)
from .reporting import generate_validation_report
from .scenarios import (
    AMT_VALIDATION_SCENARIOS_COMPARE,
    CAPITAL_GAINS_VALIDATION_SCENARIOS,
    CORPORATE_VALIDATION_SCENARIOS,
    ESTATE_TAX_VALIDATION_SCENARIOS,
    PAYROLL_TAX_VALIDATION_SCENARIOS,
    PTC_VALIDATION_SCENARIOS_COMPARE,
    TAX_CREDIT_VALIDATION_SCENARIOS,
    TAX_EXPENDITURE_VALIDATION_SCENARIOS_COMPARE,
    TCJA_VALIDATION_SCENARIOS,
)
from .specialized import (
    validate_all_amt,
    validate_all_capital_gains,
    validate_all_corporate,
    validate_all_credits,
    validate_all_estate,
    validate_all_expenditures,
    validate_all_payroll,
    validate_all_ptc,
    validate_all_tcja,
    validate_amt_policy,
    validate_capital_gains_policy,
    validate_corporate_policy,
    validate_credit_policy,
    validate_estate_policy,
    validate_expenditure_policy,
    validate_payroll_policy,
    validate_ptc_policy,
    validate_tcja_extension,
)

__all__ = [
    "AMT_VALIDATION_SCENARIOS_COMPARE",
    "CAPITAL_GAINS_VALIDATION_SCENARIOS",
    "CORPORATE_VALIDATION_SCENARIOS",
    "ESTATE_TAX_VALIDATION_SCENARIOS",
    "PAYROLL_TAX_VALIDATION_SCENARIOS",
    "PTC_VALIDATION_SCENARIOS_COMPARE",
    "TAX_CREDIT_VALIDATION_SCENARIOS",
    "TAX_EXPENDITURE_VALIDATION_SCENARIOS_COMPARE",
    "TCJA_VALIDATION_SCENARIOS",
    "ValidationResult",
    "_rate_accuracy",
    "create_capital_gains_example_from_score",
    "create_capital_gains_policy_from_score",
    "create_policy_from_score",
    "generate_validation_report",
    "quick_validate",
    "run_validation_suite",
    "validate_all",
    "validate_all_amt",
    "validate_all_capital_gains",
    "validate_all_corporate",
    "validate_all_credits",
    "validate_all_estate",
    "validate_all_expenditures",
    "validate_all_payroll",
    "validate_all_ptc",
    "validate_all_tcja",
    "validate_amt_policy",
    "validate_capital_gains_policy",
    "validate_corporate_policy",
    "validate_credit_policy",
    "validate_estate_policy",
    "validate_expenditure_policy",
    "validate_payroll_policy",
    "validate_policy",
    "validate_ptc_policy",
    "validate_tcja_extension",
]
