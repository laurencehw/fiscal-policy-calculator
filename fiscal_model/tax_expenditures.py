"""
Backward-compatible facade for tax expenditure scoring.

The implementation now lives in focused modules:
- `tax_expenditures_core.py` for types, constants, and helper functions
- `tax_expenditures_factory.py` for policy constructor helpers
"""

from .tax_expenditures_core import (
    JCT_TAX_EXPENDITURES,
    REFORM_ESTIMATES,
    TAX_EXPENDITURE_VALIDATION_SCENARIOS,
    TaxExpenditurePolicy,
    TaxExpenditureType,
    estimate_expenditure_revenue,
    get_all_expenditure_estimates,
)
from .tax_expenditures_factory import (
    create_cap_charitable_deduction,
    create_cap_employer_health_exclusion,
    create_cap_retirement_contributions,
    create_eliminate_like_kind_exchange,
    create_eliminate_mortgage_deduction,
    create_eliminate_salt_deduction,
    create_eliminate_step_up_basis,
    create_repeal_salt_cap,
)

__all__ = [
    "JCT_TAX_EXPENDITURES",
    "REFORM_ESTIMATES",
    "TAX_EXPENDITURE_VALIDATION_SCENARIOS",
    "TaxExpenditurePolicy",
    "TaxExpenditureType",
    "create_cap_charitable_deduction",
    "create_cap_employer_health_exclusion",
    "create_cap_retirement_contributions",
    "create_eliminate_like_kind_exchange",
    "create_eliminate_mortgage_deduction",
    "create_eliminate_salt_deduction",
    "create_eliminate_step_up_basis",
    "create_repeal_salt_cap",
    "estimate_expenditure_revenue",
    "get_all_expenditure_estimates",
]
