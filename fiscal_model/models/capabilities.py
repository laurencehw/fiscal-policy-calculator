"""
Explicit per-engine support matrix for multi-model pilots.

CBO-Style (and PWBM when opted in) score any policy the core FiscalPolicyScorer
handles. TPC-Microsim only scores policies that map to a non-empty reform dict
via ``policy_to_microsim_reforms``. Unsupported engines must be reported as
"not representable" — never as silent zeros or fake agreement.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fiscal_model.distribution_effects import policy_to_microsim_reforms

# Display names must match BaseScoringModel.name on the pilot adapters.
CBO_ENGINE = "CBO-Style"
TPC_ENGINE = "TPC-Microsim Pilot"
PWBM_ENGINE = "PWBM-OLG Pilot"

DEFAULT_UI_ENGINES = (CBO_ENGINE, TPC_ENGINE)


@dataclass(frozen=True)
class EngineSupport:
    """Whether one pilot engine can represent a given policy."""

    engine: str
    supported: bool
    reason: str


def policy_family(policy: Any) -> str:
    """Short family label for UI captions (corporate, credit, payroll, …)."""
    type_name = type(policy).__name__
    mapping = {
        "CorporateTaxPolicy": "corporate",
        "TaxCreditPolicy": "credit",
        "PayrollTaxPolicy": "payroll",
        "EstateTaxPolicy": "estate",
        "AMTPolicy": "amt",
        "PremiumTaxCreditPolicy": "ptc",
        "TaxExpenditurePolicy": "tax_expenditure",
        "TCJAExtensionPolicy": "tcja",
        "InternationalTaxPolicy": "international",
        "TradePolicy": "trade",
        "ClimatePolicy": "climate",
        "EnforcementPolicy": "enforcement",
        "PharmaPolicy": "pharma",
        "CapitalGainsPolicy": "capital_gains",
        "TaxPolicy": "income_tax",
        "SpendingPolicy": "spending",
        "TransferPolicy": "transfer",
    }
    if type_name in mapping:
        return mapping[type_name]

    policy_type = getattr(policy, "policy_type", None)
    policy_type_name = getattr(policy_type, "name", None) or getattr(policy_type, "value", None)
    if policy_type_name:
        return str(policy_type_name).lower()
    return "other"


def _tpc_unsupported_reason(policy: Any) -> str:
    family = policy_family(policy)
    reasons = {
        "corporate": (
            "Corporate rate / international base changes are firm-level; the "
            "return-level microsim pilot has no corporate tax module."
        ),
        "payroll": (
            "OASDI wage-cap / donut-hole reforms are not in the microsim tax "
            "calculator (NIIT-only payroll edges may map in a later sprint)."
        ),
        "estate": (
            "Estate and gift tax are outside the individual income microsim."
        ),
        "ptc": (
            "ACA premium tax credits need marketplace enrollment data the "
            "pilot microdata does not carry."
        ),
        "international": (
            "GILTI / FDII / Pillar Two are firm-level international provisions."
        ),
        "trade": "Tariffs are scored outside the income-tax microsim.",
        "climate": "IRA / carbon policies are not mapped to microsim reforms yet.",
        "enforcement": "IRS enforcement ROI is aggregate, not return-level.",
        "pharma": "Drug pricing is outside the income-tax microsim.",
        "capital_gains": (
            "Preferential capital-gains rate reforms are not yet mapped to "
            "microsim reform keys."
        ),
        "tcja": (
            "Full TCJA packages are multi-provision; the pilot maps only "
            "simple rate / credit / SALT reforms, not the full composite."
        ),
        "spending": "Spending outlays are not income-tax microsim reforms.",
        "transfer": "Transfer programs are not income-tax microsim reforms.",
    }
    return reasons.get(
        family,
        (
            f"{getattr(policy, 'name', 'Policy')} ({type(policy).__name__}) "
            "does not map onto current microsim pilot reforms "
            "(income-tax rates, CTC, EITC, SALT, std deduction, AMT exemption)."
        ),
    )


def tpc_support(policy: Any, *, year: int | None = None) -> EngineSupport:
    """Return TPC-Microsim support for ``policy``."""
    score_year = int(year if year is not None else getattr(policy, "start_year", 2025) or 2025)
    reforms = policy_to_microsim_reforms(policy, year=score_year)
    if reforms:
        keys = ", ".join(sorted(reforms.keys()))
        return EngineSupport(
            engine=TPC_ENGINE,
            supported=True,
            reason=f"Maps to microsim reforms: {keys}.",
        )
    return EngineSupport(
        engine=TPC_ENGINE,
        supported=False,
        reason=_tpc_unsupported_reason(policy),
    )


def cbo_support(policy: Any) -> EngineSupport:
    """CBO-Style scores any policy the core scorer accepts."""
    del policy
    return EngineSupport(
        engine=CBO_ENGINE,
        supported=True,
        reason="Core FiscalPolicyScorer path (static + ETI).",
    )


def pwbm_support(policy: Any) -> EngineSupport:
    """PWBM-OLG wraps the core scorer plus OLG feedback when opted in."""
    del policy
    return EngineSupport(
        engine=PWBM_ENGINE,
        supported=True,
        reason=(
            "Experimental: core scorer fiscal path + OLG revenue-feedback "
            "(CLI / audit only until feasibility bounds clear)."
        ),
    )


def engine_support_matrix(
    policy: Any,
    *,
    engines: tuple[str, ...] = DEFAULT_UI_ENGINES,
    year: int | None = None,
) -> list[EngineSupport]:
    """Per-engine support rows for the UI and comparison pre-checks."""
    resolvers = {
        CBO_ENGINE: lambda: cbo_support(policy),
        TPC_ENGINE: lambda: tpc_support(policy, year=year),
        PWBM_ENGINE: lambda: pwbm_support(policy),
    }
    rows: list[EngineSupport] = []
    for engine in engines:
        resolver = resolvers.get(engine)
        if resolver is None:
            rows.append(
                EngineSupport(
                    engine=engine,
                    supported=False,
                    reason="Unknown pilot engine.",
                )
            )
            continue
        rows.append(resolver())
    return rows


def comparable_across_default_pilots(policy: Any) -> bool:
    """True when both default UI engines (CBO + TPC) can score the policy."""
    matrix = engine_support_matrix(policy)
    return all(row.supported for row in matrix)


def support_label(policy: Any) -> str:
    """Compact selectbox suffix: 'CBO+TPC' or 'CBO only'."""
    if comparable_across_default_pilots(policy):
        return "CBO+TPC"
    return "CBO only"


__all__ = [
    "CBO_ENGINE",
    "DEFAULT_UI_ENGINES",
    "PWBM_ENGINE",
    "TPC_ENGINE",
    "EngineSupport",
    "cbo_support",
    "comparable_across_default_pilots",
    "engine_support_matrix",
    "policy_family",
    "pwbm_support",
    "support_label",
    "tpc_support",
]
