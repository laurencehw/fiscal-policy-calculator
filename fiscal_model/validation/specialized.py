"""
Backward-compatible facade for specialized validation runners.

The category-specific implementations now live in focused modules:
- `specialized_capital_gains.py`
- `specialized_tcja.py`
- `specialized_business.py`
- `specialized_household.py`
- `specialized_benefits.py`
- `specialized_sectoral.py` (international, trade, pharma, enforcement, climate)
- `specialized_pl119_21.py` (P.L. 119-21 JCT line items)
"""

from .specialized_benefits import (
    validate_all_amt,
    validate_all_ptc,
    validate_amt_policy,
    validate_ptc_policy,
)
from .specialized_business import (
    validate_all_corporate,
    validate_all_expenditures,
    validate_corporate_policy,
    validate_expenditure_policy,
)
from .specialized_capital_gains import (
    validate_all_capital_gains,
    validate_capital_gains_policy,
)
from .specialized_household import (
    validate_all_credits,
    validate_all_estate,
    validate_all_payroll,
    validate_credit_policy,
    validate_estate_policy,
    validate_payroll_policy,
)
from .specialized_pl119_21 import (
    validate_all_pl119_21,
    validate_pl119_21_provision,
)
from .specialized_sectoral import (
    validate_all_climate,
    validate_all_enforcement,
    validate_all_international,
    validate_all_pharma,
    validate_all_trade,
    validate_sectoral_policy,
)
from .specialized_tcja import validate_all_tcja, validate_tcja_extension

__all__ = [
    "validate_all_amt",
    "validate_all_capital_gains",
    "validate_all_climate",
    "validate_all_corporate",
    "validate_all_credits",
    "validate_all_enforcement",
    "validate_all_estate",
    "validate_all_expenditures",
    "validate_all_international",
    "validate_all_payroll",
    "validate_all_pharma",
    "validate_all_pl119_21",
    "validate_all_ptc",
    "validate_all_tcja",
    "validate_all_trade",
    "validate_amt_policy",
    "validate_capital_gains_policy",
    "validate_corporate_policy",
    "validate_credit_policy",
    "validate_estate_policy",
    "validate_expenditure_policy",
    "validate_payroll_policy",
    "validate_pl119_21_provision",
    "validate_ptc_policy",
    "validate_sectoral_policy",
    "validate_tcja_extension",
]
