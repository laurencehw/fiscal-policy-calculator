"""
Macro Models and Multi-Model Comparison Module

Provides adapters for connecting fiscal policy scoring to macroeconomic models
for dynamic scoring analysis, plus a plugin system for side-by-side comparison.

Available Models:
- CBOConventionalModel: Static + behavioral (ETI) scoring
- DynamicScoringModel: Adds FRB/US-calibrated macro feedback
- MicrosimScoringModel: Individual-level CPS microsimulation
- SimpleMultiplierAdapter: Reduced-form fiscal multiplier model
- FRBUSAdapter: Federal Reserve's FRB/US model (requires pyfrbus)
- FRBUSAdapterLite: FRB/US-calibrated model (no pyfrbus required)
- OLG sub-package: 55-cohort Auerbach-Kotlikoff OLG model

Example usage:
    # Multi-model comparison
    from fiscal_model.models import compare_models
    from fiscal_model.tcja import create_tcja_extension

    comparison = compare_models(create_tcja_extension())
    print(comparison.to_dataframe())
    print(comparison.explain_divergence())

    # Single macro model
    from fiscal_model.models import SimpleMultiplierAdapter, MacroScenario

    adapter = SimpleMultiplierAdapter()
    scenario = MacroScenario(
        name="Tax Cut",
        receipts_change=np.array([-100] * 10),
    )
    result = adapter.run(scenario)
    print(f"GDP effect: {result.cumulative_gdp_effect:.2f}%")
"""

from .base import BaseScoringModel, ModelComparison, ModelResult
from .macro_adapter import (
    FiscalClosureType,
    FRBUSAdapter,
    FRBUSAdapterLite,
    MacroModelAdapter,
    MacroResult,
    MacroScenario,
    MonetaryPolicyRule,
    SimpleMultiplierAdapter,
    policy_to_scenario,
)
from .olg import OLGModel, OLGParameters, OLGPolicyResult, SimpleOLGModel
from .scoring_models import (
    CBOConventionalModel,
    DynamicScoringModel,
    MicrosimScoringModel,
    compare_models,
)

__all__ = [
    "BaseScoringModel",
    "CBOConventionalModel",
    "DynamicScoringModel",
    "FRBUSAdapter",
    "FRBUSAdapterLite",
    "FiscalClosureType",
    "MacroModelAdapter",
    "MacroResult",
    "MacroScenario",
    "MicrosimScoringModel",
    "ModelComparison",
    "ModelResult",
    "MonetaryPolicyRule",
    "OLGModel",
    "OLGParameters",
    "OLGPolicyResult",
    "SimpleMultiplierAdapter",
    "SimpleOLGModel",
    "compare_models",
    "policy_to_scenario",
]
