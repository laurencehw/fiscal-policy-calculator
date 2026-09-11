"""
Backward-compatible facade for policy parameter definitions.

The implementation now lives in focused modules:
- `policies_core.py` for policy enums and dataclasses
- `policies_factory.py` for convenience constructors
"""

from .policies_core import (
    DEFAULT_ORDINARY_INCOME_BASE,
    CapitalGainsPolicy,
    Policy,
    PolicyPackage,
    PolicyType,
    SpendingPolicy,
    TaxPolicy,
    TransferPolicy,
    ordinary_income_base_for_preset,
)
from .policies_factory import (
    create_income_tax_cut,
    create_new_tax_credit,
    create_spending_increase,
)

__all__ = [
    "DEFAULT_ORDINARY_INCOME_BASE",
    "CapitalGainsPolicy",
    "Policy",
    "PolicyPackage",
    "PolicyType",
    "SpendingPolicy",
    "TaxPolicy",
    "TransferPolicy",
    "create_income_tax_cut",
    "create_new_tax_credit",
    "create_spending_increase",
    "ordinary_income_base_for_preset",
]
