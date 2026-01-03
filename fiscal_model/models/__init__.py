"""
Macro Models Module

Provides adapters for connecting fiscal policy scoring to macroeconomic models
for dynamic scoring analysis.

Available Models:
- SimpleMultiplierAdapter: Reduced-form fiscal multiplier model
- FRBUSAdapter: Federal Reserve's FRB/US model (requires pyfrbus)
- FRBUSAdapterLite: FRB/US-calibrated model (no pyfrbus required)

Example usage:
    from fiscal_model.models import SimpleMultiplierAdapter, MacroScenario

    adapter = SimpleMultiplierAdapter()
    scenario = MacroScenario(
        name="Tax Cut",
        receipts_change=np.array([-100] * 10),  # $100B revenue loss per year
    )
    result = adapter.run(scenario)
    print(f"GDP effect: {result.cumulative_gdp_effect:.2f}%")

    # For FRB/US-calibrated results without pyfrbus:
    from fiscal_model.models import FRBUSAdapterLite
    adapter = FRBUSAdapterLite()
    result = adapter.run(scenario)
"""

from .macro_adapter import (
    FiscalClosureType,
    MonetaryPolicyRule,
    MacroScenario,
    MacroResult,
    MacroModelAdapter,
    SimpleMultiplierAdapter,
    FRBUSAdapter,
    FRBUSAdapterLite,
    policy_to_scenario,
)

__all__ = [
    "FiscalClosureType",
    "MonetaryPolicyRule",
    "MacroScenario",
    "MacroResult",
    "MacroModelAdapter",
    "SimpleMultiplierAdapter",
    "FRBUSAdapter",
    "FRBUSAdapterLite",
    "policy_to_scenario",
]
