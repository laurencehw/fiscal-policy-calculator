"""
Backward-compatible facade for tax credit scoring.

The implementation now lives in focused modules:
- `credits_core.py` for types, constants, and calculator helpers
- `credits_factory.py` for common policy constructors
"""

from .credits_core import (
    BASELINE_CREDIT_COSTS,
    CREDIT_RECIPIENT_COUNTS,
    CREDIT_VALIDATION_SCENARIOS,
    CTC_CURRENT_LAW,
    EITC_CURRENT_LAW,
    CreditType,
    TaxCreditPolicy,
    estimate_credit_cost,
)
from .credits_factory import (
    create_arp_recovery_rebate,
    create_biden_ctc_2021,
    create_biden_eitc_childless,
    create_ctc_expansion,
    create_ctc_permanent_extension,
    create_eitc_expansion,
)

__all__ = [
    "BASELINE_CREDIT_COSTS",
    "CREDIT_RECIPIENT_COUNTS",
    "CREDIT_VALIDATION_SCENARIOS",
    "CTC_CURRENT_LAW",
    "EITC_CURRENT_LAW",
    "CreditType",
    "TaxCreditPolicy",
    "create_arp_recovery_rebate",
    "create_biden_ctc_2021",
    "create_biden_eitc_childless",
    "create_ctc_expansion",
    "create_ctc_permanent_extension",
    "create_eitc_expansion",
    "estimate_credit_cost",
]
