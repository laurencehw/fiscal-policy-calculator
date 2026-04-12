"""
Business-side validation runners for corporate and tax expenditure policies.
"""

from ..scoring import FiscalPolicyScorer
from .cbo_scores import KNOWN_SCORES
from .core import ValidationResult, build_validation_result
from .scenarios import (
    CORPORATE_VALIDATION_SCENARIOS,
    TAX_EXPENDITURE_VALIDATION_SCENARIOS_COMPARE,
)


def validate_corporate_policy(
    scenario_id: str = "biden_corporate_28",
    verbose: bool = True,
) -> ValidationResult:
    """Validate corporate tax scoring against CBO/Treasury estimates."""
    if scenario_id not in CORPORATE_VALIDATION_SCENARIOS:
        raise ValueError(
            f"Unknown scenario: {scenario_id}. "
            f"Available: {list(CORPORATE_VALIDATION_SCENARIOS.keys())}"
        )

    scenario = CORPORATE_VALIDATION_SCENARIOS[scenario_id]
    policy = scenario["policy_factory"]()
    expected_10yr = scenario["expected_10yr"]
    scorer = FiscalPolicyScorer(start_year=2025, use_real_data=False)
    result = scorer.score_policy(policy, dynamic=False)
    official_source = "CBO/Treasury"
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
            "rate_change": policy.rate_change,
            "baseline_rate": policy.baseline_rate,
            "corporate_elasticity": policy.corporate_elasticity,
        },
        notes=scenario.get("notes", ""),
    )

    if verbose:
        print(f"\n{'='*70}")
        print(f"Corporate Tax Validation: {scenario['description']}")
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
        for year, revenue in zip(result.years, result.final_deficit_effect, strict=False):
            print(f"  {year}: ${revenue:,.0f}B")
        if scenario.get("notes"):
            print(f"\nNotes: {scenario['notes']}")

        breakdown = policy.get_component_breakdown()
        if breakdown:
            print("\nComponent breakdown (annual):")
            print(f"  Rate change effect: ${breakdown['rate_change_effect']:,.0f}B")
            print(f"  International effect: ${breakdown['international_effect']:,.0f}B")
            print(f"  Behavioral offset: ${breakdown['behavioral_offset']:,.0f}B")
            print(f"  Net effect: ${breakdown['net_effect']:,.0f}B")

    return validation_result


def validate_all_corporate(verbose: bool = True) -> list[ValidationResult]:
    """Run validation against all corporate tax scenarios."""
    results = []

    if verbose:
        print("\n" + "=" * 70)
        print("CORPORATE TAX MODEL VALIDATION")
        print("=" * 70)

    for scenario_id in CORPORATE_VALIDATION_SCENARIOS:
        try:
            results.append(validate_corporate_policy(scenario_id, verbose=verbose))
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

    return results


def validate_expenditure_policy(
    scenario_id: str,
    verbose: bool = True,
) -> ValidationResult:
    """Validate tax expenditure scoring against CBO/JCT estimates."""
    if scenario_id not in TAX_EXPENDITURE_VALIDATION_SCENARIOS_COMPARE:
        raise ValueError(
            f"Unknown scenario: {scenario_id}. "
            f"Available: {list(TAX_EXPENDITURE_VALIDATION_SCENARIOS_COMPARE.keys())}"
        )

    scenario = TAX_EXPENDITURE_VALIDATION_SCENARIOS_COMPARE[scenario_id]
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
            "expenditure_type": (
                str(policy.expenditure_type.value)
                if hasattr(policy, "expenditure_type")
                else "unknown"
            ),
            "action": getattr(policy, "action", "unknown"),
        },
        notes=scenario.get("notes", ""),
    )

    if verbose:
        print(f"\n{'='*70}")
        print(f"Tax Expenditure Validation: {scenario['description']}")
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


def validate_all_expenditures(verbose: bool = True) -> list[ValidationResult]:
    """Run validation against all tax expenditure scenarios."""
    results = []

    if verbose:
        print("\n" + "=" * 70)
        print("TAX EXPENDITURE MODEL VALIDATION")
        print("=" * 70)

    for scenario_id in TAX_EXPENDITURE_VALIDATION_SCENARIOS_COMPARE:
        try:
            results.append(validate_expenditure_policy(scenario_id, verbose=verbose))
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
        print("KEY CONTEXT: Major Tax Expenditures (JCT 2024)")
        print("-" * 70)
        print("Largest tax expenditures (annual cost):")
        print("  - 401(k) and DC plans: ~$251B")
        print("  - Capital gains/dividends: ~$225B")
        print("  - Employer health insurance: ~$250B")
        print("  - Defined benefit pensions: ~$122B")
        print("  - Charitable contributions: ~$70B")
        print("  - SALT (with $10K cap): ~$25B")
        print("  - Mortgage interest: ~$25B")
        print("")
        print("Base broadening options:")
        print("  - Cap employer health: ~$450B revenue gain")
        print("  - Repeal SALT cap: ~$1.1T cost")
        print("  - Eliminate step-up: ~$500B revenue gain")

    return results
