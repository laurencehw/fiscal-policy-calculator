"""
Macro Models Module

Provides adapters for connecting fiscal policy scoring to macroeconomic models
for dynamic scoring analysis.

Available Models:
- SimpleMultiplierAdapter: Reduced-form fiscal multiplier model
- FRBUSAdapter: Federal Reserve's FRB/US model (requires pyfrbus)
- FRBUSAdapterLite: FRB/US-calibrated model (no pyfrbus required)
- OLG sub-package: 55-cohort Auerbach-Kotlikoff OLG model

Example usage:
    from fiscal_model.models import SimpleMultiplierAdapter, MacroScenario

    adapter = SimpleMultiplierAdapter()
    scenario = MacroScenario(
        name="Tax Cut",
        receipts_change=np.array([-100] * 10),  # $100B revenue loss per year
    )
    result = adapter.run(scenario)
    print(f"GDP effect: {result.cumulative_gdp_effect:.2f}%")

    # OLG model:
    from fiscal_model.models.olg import OLGModel, OLGParameters
    model = OLGModel()
    result = model.analyze_policy({"tau_k": 0.35}, policy_name="Corp 28%")
    print(result.summary())
"""

from .base import BaseScoringModel, CBOStyleModel, ModelResult
from .comparison import (
    ComparisonBundle,
    PWBMScoringModel,
    TPCMicrosimModel,
    UnsupportedModelPolicyError,
    build_default_comparison_models,
    compare_policy_models,
)
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

# OLG sub-package is available via fiscal_model.models.olg
# (imported lazily to avoid slowing down the main import)

__all__ = [
    "BaseScoringModel",
    "CBOStyleModel",
    "ComparisonBundle",
    "FRBUSAdapter",
    "FRBUSAdapterLite",
    "FiscalClosureType",
    "MacroModelAdapter",
    "MacroResult",
    "MacroScenario",
    "ModelResult",
    "MonetaryPolicyRule",
    "OLGModel",
    "OLGParameters",
    "OLGPolicyResult",
    "PWBMScoringModel",
    "SimpleMultiplierAdapter",
    "SimpleOLGModel",
    "TPCMicrosimModel",
    "UnsupportedModelPolicyError",
    "build_default_comparison_models",
    "compare_policy_models",
    "policy_to_scenario",
]
