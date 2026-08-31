"""
Burden-concentration ranking for the preset revenue library.

The composer needs one number per revenue preset — "how much of this
raiser's burden lands in the top quintile?" — so it can tell a
progressive package from a broad-base one. The number comes from the
same :class:`~fiscal_model.distribution.DistributionalEngine` the
Distribution tab uses, run at ``IncomeGroupType.QUINTILE``.

Not every preset is representable there. The engine returns an all-zero
table for payroll, estate, international, tariff, carbon, drug-pricing,
IRS-enforcement and premium-credit policies — their bases live outside
the return-level AGI tables it works from. Rather than reading those
zeros as "nobody pays", each unrepresentable preset falls back to a
documented *incidence family* whose indicative top-quintile share is
declared in :data:`INCIDENCE_FALLBACKS` below.

**The fallback shares are ranking inputs, not scored results.** They
order presets for selection and summarize a composed mix; they never
enter ``ScoredMix.revenue_distribution_rows``, which carries engine
output only. The composer emits a caveat naming every component that
took the fallback path.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# Group name used by DistributionalEngine for the top quintile.
TOP_QUINTILE_GROUP = "Top Quintile"

# Roughly the top quintile's share of the national tax base. A raiser
# whose burden share sits near this line is close to proportional, which
# is what "broad base" means operationally in ``composer.py``.
PROPORTIONAL_TOP_QUINTILE_SHARE = 0.45


@dataclass(frozen=True)
class IncidenceFallback:
    """Indicative top-quintile share for a family the engine cannot score."""

    share: float
    note: str
    # Corporate-side raisers are flagged rather than treated as a
    # household-level quintile share (the burden reaches households
    # through capital and wages, not a line on a return).
    is_corporate: bool = False
    # False when the raiser is not a household tax at all, so its share is
    # a placeholder and must not be read as "roughly proportional".
    is_household_tax: bool = True


# Documented fallbacks, keyed by incidence family. Shares are indicative
# and deliberately coarse — they express "who is in the base", not a
# distributional estimate.
INCIDENCE_FALLBACKS: dict[str, IncidenceFallback] = {
    "payroll_above_cap": IncidenceFallback(
        0.98,
        "Base is wages above the Social Security cap (~$168K), which sits "
        "just below the top-quintile floor used by the distribution engine "
        "($170K), so essentially the whole base is top-quintile.",
    ),
    "niit": IncidenceFallback(
        0.99,
        "NIIT applies above $200K/$250K MAGI — entirely above the "
        "top-quintile floor.",
    ),
    "estate": IncidenceFallback(
        1.00,
        "Estate tax reaches estates above a multi-million-dollar exemption; "
        "the whole base is top-quintile (in fact top-1%).",
    ),
    "corporate": IncidenceFallback(
        0.66,
        "Corporate-side raiser. Under the CBO/JCT 75/25 capital/labor split "
        "the engine's own corporate calculator puts about two thirds of the "
        "burden on top-quintile filers; the share is carried as a flag "
        "rather than a scored household distribution.",
        is_corporate=True,
    ),
    "consumption": IncidenceFallback(
        0.40,
        "Tariffs and carbon taxes are paid through prices, so the burden "
        "tracks consumption rather than income and is far less concentrated "
        "than an income-tax raiser.",
    ),
    "credit_repeal": IncidenceFallback(
        0.60,
        "Repealing energy tax credits withdraws benefits claimed both by "
        "firms and by the households that can afford the qualifying "
        "purchases, so the burden skews upward without being top-only.",
    ),
    "compliance": IncidenceFallback(
        0.85,
        "Enforcement revenue comes from unreported income, which is "
        "concentrated in high-income and pass-through returns.",
    ),
    "outlay_side": IncidenceFallback(
        0.50,
        "Raises money by cutting outlays (drug pricing) rather than by "
        "taxing households, so there is no household tax base to "
        "distribute; the share is a neutral placeholder for ranking only.",
        is_household_tax=False,
    ),
    "subsidy_repeal": IncidenceFallback(
        0.05,
        "Repealing premium credits withdraws subsidies concentrated well "
        "below the top quintile, so the burden falls mostly on lower- and "
        "middle-income households.",
    ),
    "unclassified": IncidenceFallback(
        PROPORTIONAL_TOP_QUINTILE_SHARE,
        "No incidence family matched this preset; ranked as proportional.",
    ),
}


@dataclass(frozen=True)
class PresetIncidence:
    """Where one revenue preset's burden lands, and how we know."""

    preset_name: str
    top_quintile_share: float
    representable: bool          # True when the engine produced a real table
    source: str                  # "microsim" | "synthetic" | "fallback:<family>"
    family: str                  # incidence family, always classified
    is_corporate: bool = False
    is_household_tax: bool = True
    # Engine rows, signed $B by group name (positive = tax increase for
    # that group). Empty when not representable. Displayed tables must
    # keep the sign — a group that nets a cut under a raising preset is
    # not "bearing burden"; only the *ranking* uses absolute magnitudes.
    quintile_billions: tuple[tuple[str, float], ...] = ()

    @property
    def note(self) -> str:
        """One-line explanation of where ``top_quintile_share`` came from."""
        if self.representable:
            return (
                f"Quintile table from the {self.source} distributional path."
            )
        return INCIDENCE_FALLBACKS[self.family].note


def incidence_family(preset_data: dict[str, Any]) -> str:
    """Classify a preset into a documented incidence family.

    Reads the same ``is_*`` flags ``preset_handler.create_policy_from_preset``
    routes on, so the classification cannot drift from the policy the
    composer actually builds.
    """
    if preset_data.get("is_payroll"):
        return "niit" if preset_data.get("payroll_type") == "expand_niit" else "payroll_above_cap"
    if preset_data.get("is_estate"):
        return "estate"
    if preset_data.get("is_corporate") or preset_data.get("is_international"):
        return "corporate"
    if preset_data.get("is_amt") and preset_data.get("amt_type") == "repeal_corporate":
        return "corporate"
    if preset_data.get("is_trade"):
        return "consumption"
    if preset_data.get("is_climate"):
        # A carbon tax is paid at the pump; repealing a credit is not.
        carbon = str(preset_data.get("climate_type", "")).startswith("carbon")
        return "consumption" if carbon else "credit_repeal"
    if preset_data.get("is_enforcement"):
        return "compliance"
    if preset_data.get("is_pharma"):
        return "outlay_side"
    if preset_data.get("is_ptc"):
        return "subsidy_repeal"
    return "unclassified"


def measure_incidence(
    preset_name: str,
    preset_data: dict[str, Any],
    policy: Any,
    engine: Any,
    group_type: Any,
) -> PresetIncidence:
    """Run the distribution engine for one preset, falling back when it is silent.

    ``engine`` is a :class:`DistributionalEngine` and ``group_type`` an
    ``IncomeGroupType`` — injected so the composer owns the (expensive)
    engine instance and this module stays import-light.
    """
    family = incidence_family(preset_data)
    rows: tuple[tuple[str, float], ...] = ()
    engine_name = "synthetic"

    try:
        analysis = engine.analyze_policy(policy, group_type=group_type)
        engine_name = getattr(analysis, "engine", "synthetic")
        rows = tuple(
            (result.income_group.name, float(result.tax_change_total))
            for result in analysis.results
        )
    except Exception as exc:  # engine failure is a fallback, never a crash
        logger.warning(
            "Distributional path failed for preset '%s' (%s); using the %s "
            "incidence fallback.",
            preset_name,
            exc,
            family,
        )
        rows = ()

    # The concentration *ranking* uses absolute magnitudes so a group's
    # net cut still counts as engagement with that group; the signed rows
    # themselves are preserved for display.
    total = sum(abs(value) for _, value in rows)
    if total > 0:
        top = sum(
            abs(value) for name, value in rows if name == TOP_QUINTILE_GROUP
        )
        return PresetIncidence(
            preset_name=preset_name,
            top_quintile_share=top / total,
            representable=True,
            source=engine_name,
            family=family,
            is_corporate=INCIDENCE_FALLBACKS[family].is_corporate,
            is_household_tax=INCIDENCE_FALLBACKS[family].is_household_tax,
            quintile_billions=rows,
        )

    fallback = INCIDENCE_FALLBACKS[family]
    return PresetIncidence(
        preset_name=preset_name,
        top_quintile_share=fallback.share,
        representable=False,
        source=f"fallback:{family}",
        family=family,
        is_corporate=fallback.is_corporate,
        is_household_tax=fallback.is_household_tax,
    )


def weighted_top_quintile_share(
    weighted_shares: list[tuple[float, float]],
) -> float:
    """Revenue-weighted mean top-quintile share for a set of components.

    ``weighted_shares`` is ``[(revenue_magnitude_billions, top_share), ...]``.
    Returns 0.0 for an empty or zero-weight set. This is the mix-level
    "burden concentration" number the Package Studio compares across
    variants; like its inputs it mixes engine output with documented
    fallbacks, so it is a ranking summary rather than a scored table.
    """
    total = sum(weight for weight, _ in weighted_shares)
    if total <= 0:
        return 0.0
    return sum(weight * share for weight, share in weighted_shares) / total


__all__ = [
    "INCIDENCE_FALLBACKS",
    "PROPORTIONAL_TOP_QUINTILE_SHARE",
    "TOP_QUINTILE_GROUP",
    "IncidenceFallback",
    "PresetIncidence",
    "incidence_family",
    "measure_incidence",
    "weighted_top_quintile_share",
]
