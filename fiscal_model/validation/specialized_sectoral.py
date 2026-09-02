"""
Sectoral module validation runners — international, trade, pharma, IRS
enforcement, climate/energy.

Phase E, plan §5.3. Five modules ship in the app with presets that carry an
official number in ``CBO_SCORE_MAP``, but until now none of them had a
``validate_all_*`` runner, so the scorecard reported 29 calibrated benchmarks
while the app was quietly scoring 17 more against published figures nobody
checked.

Two things make these runners different from the nine older specialized
suites, and both are deliberate:

**Targets are read, never restated.** Each scenario names a ``preset`` key and
the runner reads ``CBO_SCORE_MAP[preset]["official_score"]``. The validation
layer therefore cannot drift away from the number the app shows a user, and
adding a runner cannot smuggle in a new target.

**Nothing was retuned to close a gap.** Several of these reconstructions miss
badly. Every one of those is reported as ``Poor`` with a ``known_limitations``
note naming the structural cause. Where the module *does* carry a constant
fitted to its benchmark (the IRA-enforcement ROI multiplier, the IRA-repeal
annual), the scenario records ``calibrated_to_target=True`` so a near-zero
error is read as bookkeeping rather than skill. **The two tariff entries that
used to carry that flag no longer do**: lane L8 replaced the 70% universal
coverage rate with a Census-derived figure and deleted the 50% China coverage
rate outright, so no ``TRADE_BASELINE`` constant is fitted to any target and
all five trade rows report as unfitted reconstructions. Both moved *away* from
their targets when the fitted constants went, which is what those constants
were concealing.

Sign convention: ``CBO_SCORE_MAP`` and ``ScoringResult.total_10_year_cost``
both use deficit effect — negative reduces the deficit — so targets and model
output are directly comparable with no sign flip.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from ..app_data import CBO_SCORE_MAP
from ..scoring import FiscalPolicyScorer
from .benchmark_sources import provenance_for
from .core import (
    ValidationResult,
    build_validation_result,
    calculate_percent_difference,
)
from .scenarios import (
    CLIMATE_VALIDATION_SCENARIOS_COMPARE,
    ENFORCEMENT_VALIDATION_SCENARIOS_COMPARE,
    INTERNATIONAL_VALIDATION_SCENARIOS_COMPARE,
    PHARMA_VALIDATION_SCENARIOS_COMPARE,
    TRADE_VALIDATION_SCENARIOS_COMPARE,
)

logger = logging.getLogger(__name__)

#: Scorecard category → scenario registry. Also the registry the scorecard
#: iterates when wiring ``DEFAULT_RUNNERS``.
SECTORAL_SCENARIO_REGISTRIES: dict[str, dict[str, dict]] = {
    "International": INTERNATIONAL_VALIDATION_SCENARIOS_COMPARE,
    "Trade": TRADE_VALIDATION_SCENARIOS_COMPARE,
    "Pharma": PHARMA_VALIDATION_SCENARIOS_COMPARE,
    "Enforcement": ENFORCEMENT_VALIDATION_SCENARIOS_COMPARE,
    "Climate": CLIMATE_VALIDATION_SCENARIOS_COMPARE,
}

#: Every sectoral entry is a reconstruction of a published figure, not an
#: independent confirmation of it. Stated on the entry so report consumers do
#: not have to infer it from the category name.
SECTORAL_BENCHMARK_KIND = "Calibrated reconstruction"

#: Match ``Policy.start_year`` (2025) and the FY2025-2034 window these targets
#: are quoted for, rather than the scorer's own 2026 default. In practice the
#: five sectoral modules build their effect paths from the policy's start year
#: and their own duration, so this choice moves no score —
#: ``test_sectoral_scores_do_not_depend_on_the_scorer_start_year`` pins that,
#: and would catch a module that later became baseline-window sensitive.
_SCORER_START_YEAR = 2025


def official_target_for(scenario: dict) -> float:
    """Return the official 10-year target for a sectoral scenario.

    Read from :data:`fiscal_model.app_data.CBO_SCORE_MAP` via the scenario's
    ``preset`` key so the validation layer and the app can never disagree
    about what a policy's published score is.
    """
    preset = scenario["preset"]
    record = CBO_SCORE_MAP.get(preset)
    if record is None:
        raise KeyError(
            f"Preset {preset!r} is not in CBO_SCORE_MAP; a sectoral validation "
            "scenario must point at a preset that carries an official score."
        )
    if "official_score" not in record:
        raise KeyError(f"CBO_SCORE_MAP entry {preset!r} has no 'official_score'.")
    return float(record["official_score"])


def validate_sectoral_policy(
    category: str,
    scenario_id: str,
    verbose: bool = True,
) -> ValidationResult:
    """Validate one sectoral module preset against its published figure."""
    registry = SECTORAL_SCENARIO_REGISTRIES.get(category)
    if registry is None:
        raise ValueError(
            f"Unknown sectoral category: {category}. "
            f"Available: {list(SECTORAL_SCENARIO_REGISTRIES)}"
        )
    if scenario_id not in registry:
        raise ValueError(
            f"Unknown scenario: {scenario_id}. Available: {list(registry)}"
        )

    scenario = registry[scenario_id]
    official_10yr = official_target_for(scenario)
    policy = scenario["policy_factory"]()

    scorer = FiscalPolicyScorer(start_year=_SCORER_START_YEAR, use_real_data=False)
    result = scorer.score_policy(policy, dynamic=False)

    validation_result = build_validation_result(
        policy_id=scenario_id,
        policy_name=scenario["description"],
        official_10yr=official_10yr,
        official_source=scenario["official_source"],
        model_10yr=result.total_10_year_cost,
        model_first_year=result.final_deficit_effect[0],
        model_parameters={
            "preset": scenario["preset"],
            "provenance": provenance_for(scenario_id),
            # False = the module carries no constant fitted to this target, so a
            # miss here is a finding about the module, not a calibration
            # regression. Consumed by the readiness gate.
            "calibrated_to_target": bool(scenario.get("calibrated_to_target", False)),
            "policy_type": getattr(policy.policy_type, "value", str(policy.policy_type)),
        },
        notes=scenario.get("notes", ""),
        benchmark_date=scenario.get("benchmark_date"),
        benchmark_url=scenario.get("benchmark_url"),
        benchmark_kind=SECTORAL_BENCHMARK_KIND,
        known_limitations=scenario.get("limitations"),
    )

    if verbose:
        print(f"\n{'=' * 70}")
        print(f"{category} Validation: {scenario['description']}")
        print(f"{'=' * 70}")
        print(f"Preset: {scenario['preset']}")
        print(
            f"Official ({scenario['official_source']}): "
            f"${official_10yr:,.0f}B  [provenance: {provenance_for(scenario_id)}]"
        )
        print(f"Model estimate: ${validation_result.model_10yr:,.0f}B")
        print(
            f"Difference: ${validation_result.difference:+,.0f}B "
            f"({validation_result.percent_difference:+.1f}%)"
        )
        print(f"Direction match: {'Yes' if validation_result.direction_match else 'NO'}")
        print(f"Rating: {validation_result.accuracy_rating}")
        if not scenario.get("calibrated_to_target", False):
            print(
                "Note: no module constant is fitted to this target — this is an "
                "uncalibrated reconstruction."
            )
        for limitation in validation_result.known_limitations:
            print(f"  - {limitation}")

    return validation_result


def _error_result(
    category: str, scenario_id: str, exc: Exception
) -> ValidationResult:
    """Return a placeholder ``Error`` row for a scenario that failed to score.

    The official target is still readable from ``CBO_SCORE_MAP`` even when the
    module blows up, so the row keeps its real target and reports a zero model
    score with an ``Error`` rating rather than vanishing from the scorecard.
    """
    scenario = SECTORAL_SCENARIO_REGISTRIES[category][scenario_id]
    try:
        official = official_target_for(scenario)
    except Exception:  # pragma: no cover - only if the preset key also broke
        official = 0.0

    return ValidationResult(
        policy_id=scenario_id,
        policy_name=scenario.get("description", scenario_id),
        official_10yr=official,
        official_source=scenario.get("official_source", "unknown"),
        model_10yr=0.0,
        model_first_year=0.0,
        difference=-official,
        # A zero model score against a non-zero target is a 100% miss, not a
        # perfect match. Reporting 0.0 here would let a broken runner count
        # itself inside every accuracy band and drag the tier mean down.
        percent_difference=calculate_percent_difference(0.0, official),
        direction_match=False,
        accuracy_rating="Error",
        model_parameters={
            "preset": scenario.get("preset"),
            "provenance": provenance_for(scenario_id),
            "calibrated_to_target": bool(scenario.get("calibrated_to_target", False)),
            "error": f"{type(exc).__name__}: {exc}",
        },
        notes=f"Scoring raised {type(exc).__name__}: {exc}",
        benchmark_kind=SECTORAL_BENCHMARK_KIND,
        benchmark_date=scenario.get("benchmark_date"),
        benchmark_url=scenario.get("benchmark_url"),
        known_limitations=[
            f"This benchmark could not be scored: {type(exc).__name__}: {exc}",
        ],
    )


def _run_suite(
    category: str,
    verbose: bool,
    banner: str,
) -> list[ValidationResult]:
    """Run every scenario in one sectoral registry."""
    registry = SECTORAL_SCENARIO_REGISTRIES[category]
    results: list[ValidationResult] = []

    if verbose:
        print("\n" + "=" * 70)
        print(banner)
        print("=" * 70)

    for scenario_id in registry:
        try:
            results.append(validate_sectoral_policy(category, scenario_id, verbose=verbose))
        except Exception as exc:
            # Never drop the row. The older suites swallow the exception and
            # return a shorter list, which silently shrinks the calibrated tier
            # and hides the failure from the readiness gate and the API. An
            # explicit Error row keeps one entry per registered scenario, and
            # readiness hard-fails on an Error rating in any tier — which is
            # exactly the right response to a runner that stopped working.
            logger.exception("Sectoral validation failed: %s/%s", category, scenario_id)
            if verbose:
                print(f"\nError validating {scenario_id}: {exc}")
            results.append(_error_result(category, scenario_id, exc))

    if verbose and results:
        accurate = sum(1 for result in results if result.is_accurate)
        direction_ok = sum(1 for result in results if result.direction_match)
        uncalibrated = sum(
            1
            for scenario in registry.values()
            if not scenario.get("calibrated_to_target", False)
        )
        print("\n" + "-" * 70)
        print(f"Scenarios tested: {len(results)}")
        print(f"Within 20%: {accurate}/{len(results)}")
        print(f"Direction match: {direction_ok}/{len(results)}")
        print(f"Uncalibrated reconstructions: {uncalibrated}/{len(registry)}")

    return results


def validate_all_international(verbose: bool = True) -> list[ValidationResult]:
    """Validate the international tax module against its published figures."""
    return _run_suite("International", verbose, "INTERNATIONAL TAX MODULE VALIDATION")


def validate_all_trade(verbose: bool = True) -> list[ValidationResult]:
    """Validate the tariff module against its published figures."""
    return _run_suite("Trade", verbose, "TRADE / TARIFF MODULE VALIDATION")


def validate_all_pharma(verbose: bool = True) -> list[ValidationResult]:
    """Validate the drug-pricing module against its published figures."""
    return _run_suite("Pharma", verbose, "DRUG PRICING MODULE VALIDATION")


def validate_all_enforcement(verbose: bool = True) -> list[ValidationResult]:
    """Validate the IRS enforcement module against its published figures."""
    return _run_suite("Enforcement", verbose, "IRS ENFORCEMENT MODULE VALIDATION")


def validate_all_climate(verbose: bool = True) -> list[ValidationResult]:
    """Validate the climate/energy module against its published figures."""
    return _run_suite("Climate", verbose, "CLIMATE / ENERGY MODULE VALIDATION")


#: Category → runner, in the order the scorecard should report them.
SECTORAL_RUNNERS: dict[str, Callable[..., list[ValidationResult]]] = {
    "International": validate_all_international,
    "Trade": validate_all_trade,
    "Pharma": validate_all_pharma,
    "Enforcement": validate_all_enforcement,
    "Climate": validate_all_climate,
}


__all__ = [
    "SECTORAL_BENCHMARK_KIND",
    "SECTORAL_RUNNERS",
    "SECTORAL_SCENARIO_REGISTRIES",
    "official_target_for",
    "validate_all_climate",
    "validate_all_enforcement",
    "validate_all_international",
    "validate_all_pharma",
    "validate_all_trade",
    "validate_sectoral_policy",
]
