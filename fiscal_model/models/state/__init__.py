"""
State-level tax modeling for the fiscal policy calculator.

Scope (v1): Top 10 US states by population:
  CA, TX, FL, NY, PA, IL, OH, GA, NC, MI (~55% US population)

Key classes:
- StateTaxDatabase   — loads Tax Foundation parameters for 10 states
- StateTaxProfile    — tax parameters for a single state/year
- FederalStateCalculator — combined federal + state tax microsimulation
- SALTInteractionResult  — result from SALT deduction cap analysis
- compute_salt_interaction — compute SALT interaction for one state
- compute_salt_across_states — compute SALT interaction for all states
- TAXSIMClient       — NBER TAXSIM35 API client for validation
"""

from .calculator import FederalStateCalculator
from .database import STATE_NAMES, SUPPORTED_STATES, StateTaxDatabase, StateTaxProfile
from .salt_interaction import (
    SALTInteractionResult,
    compute_salt_across_states,
    compute_salt_interaction,
)
from .validation import TAXSIMClient, ValidationReport

__all__ = [
    "FederalStateCalculator",
    "StateTaxDatabase",
    "StateTaxProfile",
    "STATE_NAMES",
    "SUPPORTED_STATES",
    "SALTInteractionResult",
    "compute_salt_interaction",
    "compute_salt_across_states",
    "TAXSIMClient",
    "ValidationReport",
]
