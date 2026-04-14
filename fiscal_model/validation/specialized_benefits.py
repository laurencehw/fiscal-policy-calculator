"""
Benefit-side validation runners for AMT and premium tax credits.
"""

from ..scoring import FiscalPolicyScorer
from .core import ValidationResult, build_validation_result
from .scenarios import (
    AMT_VALIDATION_SCENARIOS_COMPARE,
    PTC_VALIDATION_SCENARIOS_COMPARE,
)


def validate_amt_policy(
    scenario_id: str,
    verbose: bool = True,
) -> ValidationResult:
    """Validate AMT scoring against CBO/JCT estimates."""
    if scenario_id not in AMT_VALIDATION_SCENARIOS_COMPARE:
        raise ValueError(
            f"Unknown scenario: {scenario_id}. "
            f"Available: {list(AMT_VALIDATION_SCENARIOS_COMPARE.keys())}"
        )

    scenario = AMT_VALIDATION_SCENARIOS_COMPARE[scenario_id]
    policy = scenario["policy_factory"](**scenario.get("kwargs", {}))
    expected_10yr = scenario["expected_10yr"]
    official_source = scenario.get("source", "CBO/JCT")
    result = FiscalPolicyScorer(start_year=policy.start_year, use_real_data=False).score_policy(
        policy,
        dynamic=False,
    )
    validation_result = build_validation_result(
        policy_id=scenario_id,
        policy_name=scenario["description"],
        official_10yr=expected_10yr,
        official_source=official_source,
        model_10yr=result.total_10_year_cost,
        model_first_year=result.final_deficit_effect[0],
        model_parameters={
            "amt_type": str(policy.amt_type.value) if hasattr(policy, "amt_type") else "unknown",
            "extend_tcja_relief": getattr(policy, "extend_tcja_relief", False),
            "repeal_individual_amt": getattr(policy, "repeal_individual_amt", False),
            "repeal_corporate_amt": getattr(policy, "repeal_corporate_amt", False),
        },
        notes=scenario.get("notes", ""),
        benchmark_date=scenario.get("benchmark_date"),
        benchmark_url=scenario.get("benchmark_url"),
        benchmark_kind=scenario.get("benchmark_kind"),
        known_limitations=scenario.get("limitations"),
    )

    if verbose:
        print(f"\n{'='*70}")
        print(f"AMT Validation: {scenario['description']}")
        print(f"{'='*70}")
        print(f"Expected ({official_source}): ${expected_10yr:,.0f}B")
        print(f"Model estimate: ${validation_result.model_10yr:,.0f}B")
        print(
            f"Difference: ${validation_result.difference:+,.0f}B "
            f"({validation_result.percent_difference:+.1f}%)"
        )
        print(f"Direction match: {'Yes' if validation_result.direction_match else 'NO'}")
        print(f"Rating: {validation_result.accuracy_rating}")
        print("\nYear-by-year:")
        for year, cost in zip(result.years, result.final_deficit_effect, strict=False):
            print(f"  {year}: ${cost:,.0f}B")
        if scenario.get("notes"):
            print(f"\nNotes: {scenario['notes']}")

    return validation_result


def validate_all_amt(verbose: bool = True) -> list[ValidationResult]:
    """Run validation against all AMT scenarios."""
    results = []

    if verbose:
        print("\n" + "=" * 70)
        print("AMT MODEL VALIDATION")
        print("=" * 70)

    for scenario_id in AMT_VALIDATION_SCENARIOS_COMPARE:
        try:
            results.append(validate_amt_policy(scenario_id, verbose=verbose))
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
        print("KEY CONTEXT: AMT Scoring")
        print("-" * 70)
        print("Individual AMT exemptions (under TCJA, through 2025):")
        print("  - Single: $88,100 | MFJ: $137,000")
        print("  - ~200,000 taxpayers affected, ~$5B/year revenue")
        print("")
        print("After TCJA sunset (2026+):")
        print("  - Single: ~$60,000 | MFJ: ~$93,000")
        print("  - ~7.3M taxpayers affected")
        print("  - Revenue: ~$60-75B/year by 2030")
        print("")
        print("Corporate AMT (CAMT from IRA 2022):")
        print("  - 15% book minimum tax on $1B+ corporations")
        print("  - Revenue: ~$22B/year")

    return results


def validate_ptc_policy(
    scenario_id: str,
    verbose: bool = True,
) -> ValidationResult:
    """Validate PTC scoring against CBO estimates."""
    if scenario_id not in PTC_VALIDATION_SCENARIOS_COMPARE:
        raise ValueError(
            f"Unknown scenario: {scenario_id}. "
            f"Available: {list(PTC_VALIDATION_SCENARIOS_COMPARE.keys())}"
        )

    scenario = PTC_VALIDATION_SCENARIOS_COMPARE[scenario_id]
    policy = scenario["policy_factory"](**scenario.get("kwargs", {}))
    expected_10yr = scenario["expected_10yr"]
    official_source = scenario.get("source", "CBO")
    result = FiscalPolicyScorer(start_year=policy.start_year, use_real_data=False).score_policy(
        policy,
        dynamic=False,
    )
    validation_result = build_validation_result(
        policy_id=scenario_id,
        policy_name=scenario["description"],
        official_10yr=expected_10yr,
        official_source=official_source,
        model_10yr=result.total_10_year_cost,
        model_first_year=result.final_deficit_effect[0],
        model_parameters={
            "scenario": (
                str(policy.scenario.value) if hasattr(policy, "scenario") else "unknown"
            ),
            "extend_enhanced": getattr(policy, "extend_enhanced", False),
            "repeal_ptc": getattr(policy, "repeal_ptc", False),
        },
        notes=scenario.get("notes", ""),
        benchmark_date=scenario.get("benchmark_date"),
        benchmark_url=scenario.get("benchmark_url"),
        benchmark_kind=scenario.get("benchmark_kind"),
        known_limitations=scenario.get("limitations"),
    )

    if verbose:
        print(f"\n{'='*70}")
        print(f"PTC Validation: {scenario['description']}")
        print(f"{'='*70}")
        print(f"Expected ({official_source}): ${expected_10yr:,.0f}B")
        print(f"Model estimate: ${validation_result.model_10yr:,.0f}B")
        print(
            f"Difference: ${validation_result.difference:+,.0f}B "
            f"({validation_result.percent_difference:+.1f}%)"
        )
        print(f"Direction match: {'Yes' if validation_result.direction_match else 'NO'}")
        print(f"Rating: {validation_result.accuracy_rating}")
        print("\nYear-by-year:")
        for year, cost in zip(result.years, result.final_deficit_effect, strict=False):
            print(f"  {year}: ${cost:,.0f}B")
        if scenario.get("notes"):
            print(f"\nNotes: {scenario['notes']}")

    return validation_result


def validate_all_ptc(verbose: bool = True) -> list[ValidationResult]:
    """Run validation against all PTC scenarios."""
    results = []

    if verbose:
        print("\n" + "=" * 70)
        print("PREMIUM TAX CREDIT MODEL VALIDATION")
        print("=" * 70)

    for scenario_id in PTC_VALIDATION_SCENARIOS_COMPARE:
        try:
            results.append(validate_ptc_policy(scenario_id, verbose=verbose))
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
        print("KEY CONTEXT: Premium Tax Credits (ACA)")
        print("-" * 70)
        print("Enhanced PTCs (ARPA 2021 / IRA 2022 extension through 2025):")
        print("  - Income range: 100%+ FPL (no upper limit)")
        print("  - Premium cap: 0-8.5% of income")
        print("  - ~22M marketplace enrollees, ~19M receiving PTCs")
        print("")
        print("After 2025 sunset (original ACA):")
        print("  - Income range: 100-400% FPL only")
        print("  - ~4 million would lose coverage")
        print("  - Premium increase: ~114% avg")
        print("")
        print("CBO estimates:")
        print("  - Extend enhanced PTCs: ~$350B cost over 10 years")
        print("  - Repeal all PTCs: ~$1.1T savings (major coverage loss)")

    return results
