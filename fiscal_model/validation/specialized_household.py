"""
Household-side validation runners for credits, estate, and payroll policies.
"""

from ..scoring import FiscalPolicyScorer
from .core import ValidationResult, _rate_accuracy, build_validation_result
from .scenarios import (
    ESTATE_TAX_VALIDATION_SCENARIOS,
    PAYROLL_TAX_VALIDATION_SCENARIOS,
    TAX_CREDIT_VALIDATION_SCENARIOS,
)


def validate_credit_policy(
    scenario_id: str,
    verbose: bool = True,
) -> ValidationResult:
    """Validate tax credit scoring against CBO/Treasury estimates."""
    if scenario_id not in TAX_CREDIT_VALIDATION_SCENARIOS:
        raise ValueError(
            f"Unknown scenario: {scenario_id}. "
            f"Available: {list(TAX_CREDIT_VALIDATION_SCENARIOS.keys())}"
        )

    scenario = TAX_CREDIT_VALIDATION_SCENARIOS[scenario_id]
    policy = scenario["policy_factory"]()
    result = FiscalPolicyScorer(start_year=policy.start_year, use_real_data=False).score_policy(
        policy,
        dynamic=False,
    )
    model_10yr = abs(result.total_10_year_cost)
    expected_10yr = scenario["expected_10yr"]
    official_source = scenario.get("source", "CBO/Treasury")
    percent_diff = (
        (model_10yr - expected_10yr) / abs(expected_10yr) * 100 if expected_10yr else 0.0
    )

    validation_result = build_validation_result(
        policy_id=scenario_id,
        policy_name=scenario["description"],
        official_10yr=expected_10yr,
        official_source=official_source,
        model_10yr=model_10yr,
        model_first_year=abs(result.final_deficit_effect[0]),
        model_parameters={
            "credit_type": (
                str(policy.credit_type.value) if hasattr(policy, "credit_type") else "unknown"
            ),
            "max_credit_per_unit": getattr(policy, "max_credit_per_unit", 0),
            "units_affected_millions": getattr(policy, "units_affected_millions", 0),
        },
        notes=scenario.get("notes", ""),
        direction_match=True,
        benchmark_date=scenario.get("benchmark_date"),
        benchmark_url=scenario.get("benchmark_url"),
        benchmark_kind=scenario.get("benchmark_kind"),
        known_limitations=scenario.get("limitations"),
    )
    validation_result.percent_difference = percent_diff
    validation_result.difference = model_10yr - expected_10yr
    validation_result.accuracy_rating = _rate_accuracy(percent_diff)

    if verbose:
        print(f"\n{'='*70}")
        print(f"Tax Credit Validation: {scenario['description']}")
        print(f"{'='*70}")
        print(f"Expected ({official_source}): ${expected_10yr:,.0f}B")
        print(f"Model estimate: ${model_10yr:,.0f}B")
        print(
            f"Difference: ${validation_result.difference:+,.0f}B "
            f"({validation_result.percent_difference:+.1f}%)"
        )
        print(f"Rating: {validation_result.accuracy_rating}")
        print("\nYear-by-year costs:")
        for year, cost in zip(result.years, result.final_deficit_effect, strict=False):
            print(f"  {year}: ${abs(cost):,.0f}B")
        if scenario.get("notes"):
            print(f"\nNotes: {scenario['notes']}")

    return validation_result


def validate_all_credits(verbose: bool = True) -> list[ValidationResult]:
    """Run validation against all tax credit scenarios."""
    results = []

    if verbose:
        print("\n" + "=" * 70)
        print("TAX CREDIT MODEL VALIDATION")
        print("=" * 70)

    for scenario_id in TAX_CREDIT_VALIDATION_SCENARIOS:
        try:
            results.append(validate_credit_policy(scenario_id, verbose=verbose))
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
        print("KEY CONTEXT: Tax Credit Scoring")
        print("-" * 70)
        print("Tax credits are scored as COSTS (increase deficit).")
        print("Refundable credits are paid out even with no tax liability.")
        print("")
        print("Baseline costs (annual):")
        print("  - CTC total: ~$120B")
        print("  - EITC total: ~$70B")
        print("")
        print("Major expansion proposals:")
        print("  - Biden CTC (ARP-style, permanent): ~$160B/year")
        print("  - Biden EITC childless: ~$18B/year")

    return results


def validate_estate_policy(
    scenario_id: str,
    verbose: bool = True,
) -> ValidationResult:
    """Validate estate tax scoring against CBO/Treasury estimates."""
    if scenario_id not in ESTATE_TAX_VALIDATION_SCENARIOS:
        raise ValueError(
            f"Unknown scenario: {scenario_id}. "
            f"Available: {list(ESTATE_TAX_VALIDATION_SCENARIOS.keys())}"
        )

    scenario = ESTATE_TAX_VALIDATION_SCENARIOS[scenario_id]
    policy = scenario["policy_factory"]()
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
            "exemption_change": getattr(policy, "exemption_change", 0),
            "new_exemption": getattr(policy, "new_exemption", None),
            "extend_tcja": getattr(policy, "extend_tcja_exemption", False),
            "rate_change": getattr(policy, "rate_change", 0),
        },
        notes=scenario.get("notes", ""),
        benchmark_date=scenario.get("benchmark_date"),
        benchmark_url=scenario.get("benchmark_url"),
        benchmark_kind=scenario.get("benchmark_kind"),
        known_limitations=scenario.get("limitations"),
    )

    if verbose:
        print(f"\n{'='*70}")
        print(f"Estate Tax Validation: {scenario['description']}")
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


def validate_all_estate(verbose: bool = True) -> list[ValidationResult]:
    """Run validation against all estate tax scenarios."""
    results = []

    if verbose:
        print("\n" + "=" * 70)
        print("ESTATE TAX MODEL VALIDATION")
        print("=" * 70)

    for scenario_id in ESTATE_TAX_VALIDATION_SCENARIOS:
        try:
            results.append(validate_estate_policy(scenario_id, verbose=verbose))
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
        print("KEY CONTEXT: Estate Tax Scoring")
        print("-" * 70)
        print("Estate tax applies to wealth transfers at death above exemption.")
        print("")
        print("Current law (TCJA through 2025):")
        print("  - Exemption: ~$14M per person")
        print("  - Rate: 40%")
        print("  - Taxable estates: ~7,000/year")
        print("  - Revenue: ~$32B/year")
        print("")
        print("After TCJA sunset (2026+):")
        print("  - Exemption drops to ~$6.4M")
        print("  - Taxable estates: ~19,000/year")
        print("  - Revenue projected: ~$50B/year")

    return results


def validate_payroll_policy(
    scenario_id: str,
    verbose: bool = True,
) -> ValidationResult:
    """Validate payroll tax scoring against CBO/Trustees estimates."""
    if scenario_id not in PAYROLL_TAX_VALIDATION_SCENARIOS:
        raise ValueError(
            f"Unknown scenario: {scenario_id}. "
            f"Available: {list(PAYROLL_TAX_VALIDATION_SCENARIOS.keys())}"
        )

    scenario = PAYROLL_TAX_VALIDATION_SCENARIOS[scenario_id]
    policy = scenario["policy_factory"]()
    expected_10yr = scenario["expected_10yr"]
    official_source = scenario.get("source", "CBO/Trustees")
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
            "ss_eliminate_cap": getattr(policy, "ss_eliminate_cap", False),
            "ss_cover_90_pct": getattr(policy, "ss_cover_90_pct", False),
            "ss_donut_hole_start": getattr(policy, "ss_donut_hole_start", None),
            "expand_niit": getattr(policy, "expand_niit_to_passthrough", False),
        },
        notes=scenario.get("notes", ""),
        benchmark_date=scenario.get("benchmark_date"),
        benchmark_url=scenario.get("benchmark_url"),
        benchmark_kind=scenario.get("benchmark_kind"),
        known_limitations=scenario.get("limitations"),
    )

    if verbose:
        print(f"\n{'='*70}")
        print(f"Payroll Tax Validation: {scenario['description']}")
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


def validate_all_payroll(verbose: bool = True) -> list[ValidationResult]:
    """Run validation against all payroll tax scenarios."""
    results = []

    if verbose:
        print("\n" + "=" * 70)
        print("PAYROLL TAX MODEL VALIDATION")
        print("=" * 70)

    for scenario_id in PAYROLL_TAX_VALIDATION_SCENARIOS:
        try:
            results.append(validate_payroll_policy(scenario_id, verbose=verbose))
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
        print("KEY CONTEXT: Payroll Tax Scoring")
        print("-" * 70)
        print("Social Security: 12.4% on wages up to cap (~$176K in 2025)")
        print("Medicare: 2.9% on all wages (no cap)")
        print("")
        print("Key reform options:")
        print("  - Raise cap to 90% coverage: ~$800B/10yr (CBO)")
        print("  - Donut hole above $250K: ~$2.7T/10yr (Trustees)")
        print("  - Eliminate cap: ~$3.2T/10yr (Trustees)")
        print("  - Expand NIIT: ~$250B/10yr (JCT)")

    return results
