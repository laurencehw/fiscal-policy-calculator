"""
CBO-Style Fiscal Policy Scoring Model

A comprehensive framework for analyzing fiscal policy proposals
using Congressional Budget Office methodology.
"""

from .policies import (
    Policy,
    TaxPolicy,
    SpendingPolicy,
    TransferPolicy,
    PolicyPackage,
    PolicyType,
    create_income_tax_cut,
    create_new_tax_credit,
    create_spending_increase,
)
from .baseline import BaselineProjection, CBOBaseline
from .scoring import FiscalPolicyScorer, ScoringResult
from .economics import EconomicModel, DynamicEffects, EconomicConditions
from .uncertainty import UncertaintyAnalysis
from .reporting import BudgetReport

__version__ = "1.0.0"
__all__ = [
    "Policy",
    "TaxPolicy",
    "SpendingPolicy",
    "TransferPolicy",
    "PolicyPackage",
    "PolicyType",
    "create_income_tax_cut",
    "create_new_tax_credit",
    "create_spending_increase",
    "BaselineProjection",
    "CBOBaseline",
    "FiscalPolicyScorer",
    "ScoringResult",
    "EconomicModel",
    "EconomicConditions",
    "DynamicEffects",
    "UncertaintyAnalysis",
    "BudgetReport",
]

