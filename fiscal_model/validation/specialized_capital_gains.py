"""
Capital gains validation runners.
"""

from ..scoring import FiscalPolicyScorer
from .cbo_scores import KNOWN_SCORES
from .core import (
    ValidationResult,
    build_validation_result,
    create_capital_gains_policy_from_score,
)
from .scenarios import CAPITAL_GAINS_VALIDATION_SCENARIOS


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
    )

    # Only structural fields are read off the scenario: the behavioural
    # parameters are the module's one frozen literature set.
    for field_name in (
        "step_up_at_death",
        "eliminate_step_up",
        "step_up_exemption",
        "score_gains_at_death",
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
            "persistent_elasticity": policy.persistent_elasticity,
            "transitory_elasticity": policy.transitory_elasticity,
            "elasticity_reference_rate": policy.elasticity_reference_rate,
            "lock_in_wedge": policy.lock_in_wedge(),
            "eliminate_step_up": policy.eliminate_step_up,
            # Wave 2's L1 deleted the three per-case elasticity/lock-in tuples,
            # which were the only constants ever fitted to these three targets.
            # What scores them now is one frozen literature set, so a miss here
            # is a finding about the module rather than a calibration
            # regression - which is exactly what calibrated_to_target=False
            # means, and which moves these rows into the unfitted-
            # reconstruction tier where the sectoral runners already sit.
            "calibrated_to_target": False,
        },
        notes=scenario.get("notes", ""),
        benchmark_date=score.source_date,
        benchmark_url=score.source_url,
        benchmark_kind=scenario.get("benchmark_kind"),
        known_limitations=scenario.get("limitations"),
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
        print(f"  Persistent elasticity: {policy.persistent_elasticity:.2f}")
        print(f"  Transitory elasticity: {policy.transitory_elasticity:.2f}")
        print(f"  Lock-in wedge (with/without step-up): {policy.lock_in_wedge():.2f}x")
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
