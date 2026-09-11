"""
Backward-compatible facade for policy parameter definitions.

The implementation now lives in focused modules:
- `policies_core.py` for policy enums and dataclasses
- `policies_factory.py` for convenience constructors
"""

from .policies_core import (
    DEFAULT_INCOME_MEASURE,
    DEFAULT_ORDINARY_INCOME_BASE,
    DEFAULT_THRESHOLD_INDEXATION,
    INCOME_MEASURE_AGI,
    INCOME_MEASURE_TAXABLE_INCOME,
    THRESHOLD_INDEXATION_INCOME,
    THRESHOLD_INDEXATION_NOMINAL,
    THRESHOLD_INDEXATION_STATUTORY,
    THRESHOLD_INDEXATIONS,
    CapitalGainsPolicy,
    Policy,
    PolicyPackage,
    PolicyType,
    SpendingPolicy,
    TaxPolicy,
    TransferPolicy,
    income_measure_for_preset,
    ordinary_income_base_for_preset,
)
from .policies_factory import (
    create_income_tax_cut,
    create_new_tax_credit,
    create_spending_increase,
)

__all__ = [
    "DEFAULT_INCOME_MEASURE",
    "DEFAULT_ORDINARY_INCOME_BASE",
    "DEFAULT_THRESHOLD_INDEXATION",
    "INCOME_MEASURE_AGI",
    "INCOME_MEASURE_TAXABLE_INCOME",
    "THRESHOLD_INDEXATIONS",
    "THRESHOLD_INDEXATION_INCOME",
    "THRESHOLD_INDEXATION_NOMINAL",
    "THRESHOLD_INDEXATION_STATUTORY",
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
    "income_measure_for_preset",
    "ordinary_income_base_for_preset",
]
