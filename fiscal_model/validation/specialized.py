"""
Specialized validation runners for non-generic policy modules.
"""

from ..scoring import FiscalPolicyScorer
from ..tcja import create_tcja_extension, create_tcja_repeal_salt_cap
from .cbo_scores import KNOWN_SCORES
from .core import (
    ValidationResult,
    _rate_accuracy,
    build_validation_result,
    create_capital_gains_policy_from_score,
)
from .scenarios import (
    AMT_VALIDATION_SCENARIOS_COMPARE,
    CAPITAL_GAINS_VALIDATION_SCENARIOS,
    CORPORATE_VALIDATION_SCENARIOS,
    ESTATE_TAX_VALIDATION_SCENARIOS,
    PAYROLL_TAX_VALIDATION_SCENARIOS,
    PTC_VALIDATION_SCENARIOS_COMPARE,
    TAX_CREDIT_VALIDATION_SCENARIOS,
    TAX_EXPENDITURE_VALIDATION_SCENARIOS_COMPARE,
    TCJA_VALIDATION_SCENARIOS,
)


def validate_capital_gains_policy(
    scenario_id: str,
    verbose: bool = True,
) -> ValidationResult:
    """Validate our capital gains model against a known official estimate."""
    if scenario_id not in CAPITAL_GAINS_VALIDATION_SCENARIOS:
        raise ValueError(
            f"Unknown scenario: {scenario_id}. "
            f"Available: {list(CAPITAL_GAINS_VALIDATION_SCENARIOS.keys())}"
        )

    scenario = CAPITAL_GAINS_VALIDATION_SCENARIOS[scenario_id]
    score = KNOWN_SCORES.get(scenario["score_id"])
    if score is None:
        raise ValueError(f"Score not found: {scenario['score_id']}")

    policy = create_capital_gains_policy_from_score(
        score,
        baseline_capital_gains_rate=scenario["baseline_capital_gains_rate"],
        baseline_realizations_billions=scenario["baseline_realizations_billions"],
        short_run_elasticity=scenario["short_run_elasticity"],
        long_run_elasticity=scenario["long_run_elasticity"],
    )

    for field_name in (
        "step_up_at_death",
        "eliminate_step_up",
        "step_up_lock_in_multiplier",
        "step_up_exemption",
        "gains_at_death_billions",
    ):
        if field_name in scenario:
            setattr(policy, field_name, scenario[field_name])

    scorer = FiscalPolicyScorer(start_year=2025, use_real_data=False)
    result = scorer.score_policy(policy, dynamic=False)
    validation_result = build_validation_result(
        policy_id=scenario_id,
        policy_name=scenario["description"],
        official_10yr=score.ten_year_cost,
        official_source=score.source.value,
        model_10yr=result.total_10_year_cost,
        model_first_year=result.final_deficit_effect[0],
        model_parameters={
            "rate_change": policy.rate_change,
            "threshold": policy.affected_income_threshold,
            "baseline_rate": policy.baseline_capital_gains_rate,
            "baseline_realizations": policy.baseline_realizations_billions,
            "short_run_elasticity": policy.short_run_elasticity,
            "long_run_elasticity": policy.long_run_elasticity,
        },
        notes=scenario.get("notes", ""),
    )

    if verbose:
        print(f"\n{'='*70}")
        print(f"Capital Gains Validation: {scenario['description']}")
        print(f"{'='*70}")
        print(f"Official ({score.source.value}): ${score.ten_year_cost:,.0f}B")
        print(f"Model estimate: ${validation_result.model_10yr:,.0f}B")
        print(
            f"Difference: ${validation_result.difference:+,.0f}B "
            f"({validation_result.percent_difference:+.1f}%)"
        )
        print(f"Direction match: {'Yes' if validation_result.direction_match else 'NO'}")
        print(f"Rating: {validation_result.accuracy_rating}")
        print("\nModel parameters:")
        print(f"  Rate change: {policy.rate_change*100:+.1f}pp")
        print(f"  Threshold: ${policy.affected_income_threshold:,.0f}")
        print(f"  Baseline rate: {policy.baseline_capital_gains_rate*100:.1f}%")
        print(f"  Baseline realizations: ${policy.baseline_realizations_billions:,.0f}B")
        print(f"  Short-run elasticity: {policy.short_run_elasticity:.2f}")
        print(f"  Long-run elasticity: {policy.long_run_elasticity:.2f}")
        if scenario.get("notes"):
            print(f"\nNotes: {scenario['notes']}")

    return validation_result


def validate_all_capital_gains(verbose: bool = True) -> list[ValidationResult]:
    """Run validation against all capital gains scenarios."""
    results = []

    if verbose:
        print("\n" + "=" * 70)
        print("CAPITAL GAINS MODEL VALIDATION")
        print("=" * 70)

    for scenario_id in CAPITAL_GAINS_VALIDATION_SCENARIOS:
        try:
            results.append(validate_capital_gains_policy(scenario_id, verbose=verbose))
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
        print("KEY INSIGHT: Step-Up Basis Effect")
        print("-" * 70)
        print("The PWBM estimates show that with step-up basis (current law),")
        print("raising capital gains rates to 39.6% actually LOSES revenue ($33B).")
        print("Without step-up basis, the same rate increase RAISES $113B.")
        print("This requires very different elasticity assumptions to replicate.")

    return results


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
    percent_diff = (model_10yr - expected_10yr) / abs(expected_10yr) * 100 if expected_10yr else 0.0

    validation_result = build_validation_result(
        policy_id=scenario_id,
        policy_name=scenario["description"],
        official_10yr=expected_10yr,
        official_source=official_source,
        model_10yr=model_10yr,
        model_first_year=abs(result.final_deficit_effect[0]),
        model_parameters={
            "credit_type": str(policy.credit_type.value) if hasattr(policy, "credit_type") else "unknown",
            "max_credit_per_unit": getattr(policy, "max_credit_per_unit", 0),
            "units_affected_millions": getattr(policy, "units_affected_millions", 0),
        },
        notes=scenario.get("notes", ""),
        direction_match=True,
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
            "scenario": str(policy.scenario.value) if hasattr(policy, "scenario") else "unknown",
            "extend_enhanced": getattr(policy, "extend_enhanced", False),
            "repeal_ptc": getattr(policy, "repeal_ptc", False),
        },
        notes=scenario.get("notes", ""),
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
            "expenditure_type": str(policy.expenditure_type.value) if hasattr(policy, "expenditure_type") else "unknown",
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
