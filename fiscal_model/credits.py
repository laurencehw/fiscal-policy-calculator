"""
Backward-compatible facade for tax credit scoring.

The implementation now lives in focused modules:
- `credits_core.py` for types, constants, and calculator helpers
- `credits_factory.py` for common policy constructors
- `credits_microdata.py` for the per-unit CPS scoring path (`derived` mode)
"""

from .credits_core import (
    BASELINE_CREDIT_COSTS,
    CREDIT_APP_MODE,
    CREDIT_HELD_OUT_MODE,
    CREDIT_MODE_DERIVED,
    CREDIT_MODE_REPORTED,
    CREDIT_MODES,
    CREDIT_RECIPIENT_COUNTS,
    CREDIT_SCORECARD_MODE,
    CREDIT_VALIDATION_SCENARIOS,
    CTC_CURRENT_LAW,
    CTC_SUNSET_YEAR,
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
    "CREDIT_APP_MODE",
    "CREDIT_HELD_OUT_MODE",
    "CREDIT_MODES",
    "CREDIT_MODE_DERIVED",
    "CREDIT_MODE_REPORTED",
    "CREDIT_RECIPIENT_COUNTS",
    "CREDIT_SCORECARD_MODE",
    "CREDIT_VALIDATION_SCENARIOS",
    "CTC_CURRENT_LAW",
    "CTC_SUNSET_YEAR",
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
