"""
TCJA validation runners.
"""

from ..scoring import FiscalPolicyScorer
from ..tcja import create_tcja_extension, create_tcja_repeal_salt_cap
from .cbo_scores import KNOWN_SCORES
from .core import ValidationResult, build_validation_result
from .scenarios import TCJA_VALIDATION_SCENARIOS


def validate_tcja_extension(
    scenario_id: str = "tcja_full_extension",
    verbose: bool = True,
) -> ValidationResult:
    """Validate TCJA extension scoring against CBO estimates."""
    if scenario_id not in TCJA_VALIDATION_SCENARIOS:
        raise ValueError(
            f"Unknown scenario: {scenario_id}. "
            f"Available: {list(TCJA_VALIDATION_SCENARIOS.keys())}"
        )

    scenario = TCJA_VALIDATION_SCENARIOS[scenario_id]
    expected_10yr = scenario["expected_10yr"]

    if scenario.get("extend_all", True):
        if scenario.get("keep_salt_cap", True):
            policy = create_tcja_extension(extend_all=True, keep_salt_cap=True)
        else:
            policy = create_tcja_repeal_salt_cap()
    else:
        policy = create_tcja_extension(
            extend_all=False,
            extend_rate_cuts=scenario.get("extend_rates", True),
            extend_standard_deduction=scenario.get("extend_standard_deduction", True),
            keep_exemption_elimination=scenario.get("keep_exemption_elimination", True),
            extend_passthrough=scenario.get("extend_passthrough", True),
            extend_ctc=scenario.get("extend_ctc", True),
            extend_estate=scenario.get("extend_estate", True),
            extend_amt=scenario.get("extend_amt", True),
            keep_salt_cap=scenario.get("keep_salt_cap", True),
        )

    scorer = FiscalPolicyScorer(start_year=2026, use_real_data=False)
    result = scorer.score_policy(policy, dynamic=False)
    official_source = "CBO"
    score = None
    if scenario.get("score_id"):
        score = KNOWN_SCORES.get(scenario["score_id"])
        if score:
            expected_10yr = score.ten_year_cost
            official_source = score.source.value

    validation_result = build_validation_result(
        policy_id=scenario_id,
        policy_name=scenario["description"],
        official_10yr=expected_10yr,
        official_source=official_source,
        model_10yr=result.total_10_year_cost,
        model_first_year=result.final_deficit_effect[0],
        model_parameters={
            "extend_all": scenario.get("extend_all", True),
            "keep_salt_cap": scenario.get("keep_salt_cap", True),
            "calibration_factor": policy.calibration_factor,
        },
        notes=scenario.get("notes", ""),
        benchmark_date=score.source_date if score else scenario.get("benchmark_date"),
        benchmark_url=score.source_url if score else scenario.get("benchmark_url"),
        benchmark_kind=scenario.get("benchmark_kind"),
        known_limitations=scenario.get("limitations"),
    )

    if verbose:
        print(f"\n{'='*70}")
        print(f"TCJA Validation: {scenario['description']}")
        print(f"{'='*70}")
        print(f"Expected ({official_source}): ${expected_10yr:,.0f}B")
        print(f"Model estimate: ${validation_result.model_10yr:,.0f}B")
        print(
            f"Difference: ${validation_result.difference:+,.0f}B "
            f"({validation_result.percent_difference:+.1f}%)"
        )
        print(f"Direction match: {'Yes' if validation_result.direction_match else 'NO'}")
        print(f"Rating: {validation_result.accuracy_rating}")
        print("\nYear-by-year costs:")
        for year, cost in zip(result.years, result.final_deficit_effect, strict=False):
            print(f"  {year}: ${cost:,.0f}B")
        if scenario.get("notes"):
            print(f"\nNotes: {scenario['notes']}")

        breakdown = policy.get_component_breakdown()
        if breakdown:
            print("\nComponent breakdown (calibrated):")
            for component in breakdown.values():
                sign = "+" if component["ten_year_cost"] > 0 else ""
                offset_marker = " (offset)" if component["is_offset"] else ""
                print(
                    f"  {component['name']}: "
                    f"{sign}${component['ten_year_cost']:,.0f}B{offset_marker}"
                )

    return validation_result


def validate_all_tcja(verbose: bool = True) -> list[ValidationResult]:
    """Run validation against all TCJA extension scenarios."""
    results = []

    if verbose:
        print("\n" + "=" * 70)
        print("TCJA EXTENSION MODEL VALIDATION")
        print("=" * 70)

    for scenario_id in TCJA_VALIDATION_SCENARIOS:
        try:
            results.append(validate_tcja_extension(scenario_id, verbose=verbose))
        except Exception as exc:
            if verbose:
                print(f"\nError validating {scenario_id}: {exc}")

    if verbose and results:
        accurate = sum(1 for result in results if result.is_accurate)
        direction_ok = sum(1 for result in results if result.direction_match)
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Scenarios tested: {len(results)}")
        print(f"Within 20% accuracy: {accurate}/{len(results)}")
        print(f"Direction match: {direction_ok}/{len(results)}")
        print("\n" + "-" * 70)
        print("KEY CONTEXT: TCJA Extension Scoring")
        print("-" * 70)
        print("TCJA individual provisions sunset after 2025. CBO's baseline")
        print("assumes they expire, so 'extension' is scored as a COST.")
        print("")
        print("Major cost components:")
        print("  - Rate cuts: ~$1.8T (largest)")
        print("  - Standard deduction: ~$720B")
        print("  - Pass-through (199A): ~$700B")
        print("  - CTC expansion: ~$550B")
        print("  - AMT relief: ~$450B")
        print("")
        print("Major offsets (provisions that RAISE revenue):")
        print("  - SALT cap: ~$1.1T (keeps high-tax state deductions capped)")
        print("  - Personal exemption elimination: ~$650B")

    return results
