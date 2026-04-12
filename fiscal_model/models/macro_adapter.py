"""
Macro Model Adapter Interface

Stable import facade for macroeconomic model adapters.
"""

from .macro_adapter_conversion import policy_to_scenario
from .macro_adapter_core import (
    FiscalClosureType,
    MacroModelAdapter,
    MacroResult,
    MacroScenario,
    MonetaryPolicyRule,
)
from .macro_adapter_frbus import FRBUSAdapter, FRBUSAdapterLite
from .macro_adapter_simple import SimpleMultiplierAdapter

__all__ = [
    "FRBUSAdapter",
    "FRBUSAdapterLite",
    "FiscalClosureType",
    "MacroModelAdapter",
    "MacroResult",
    "MacroScenario",
    "MonetaryPolicyRule",
    "SimpleMultiplierAdapter",
    "policy_to_scenario",
]
