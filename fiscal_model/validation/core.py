"""
Core validation types and helpers.

This module contains the shared result model plus the generic validation
helpers used across the specialized policy validators.
"""

from dataclasses import dataclass, field

import numpy as np

from ..policies import CapitalGainsPolicy, PolicyType, TaxPolicy
from ..scoring import FiscalPolicyScorer
from .cbo_scores import CBOScore, get_validation_targets


@dataclass
class ValidationResult:
    """
    Result of validating model output against an official score.
    """

    policy_id: str
    policy_name: str

    official_10yr: float
    official_source: str
    model_10yr: float
    model_first_year: float
    difference: float
    percent_difference: float
    direction_match: bool
    accuracy_rating: str
    model_parameters: dict = field(default_factory=dict)
    notes: str = ""

    @property
    def is_accurate(self) -> bool:
        """Check if estimate is within acceptable tolerance (20%)."""
        return abs(self.percent_difference) <= 20.0

    def get_summary(self) -> str:
        """Get a one-line summary."""
        direction = "✓" if self.direction_match else "✗"
        return (
            f"{self.policy_name}: "
            f"Official ${self.official_10yr:,.0f}B vs "
            f"Model ${self.model_10yr:,.0f}B "
            f"({self.percent_difference:+.1f}%) "
            f"[{self.accuracy_rating}] {direction}"
        )


def _rate_accuracy(percent_diff: float) -> str:
    """Rate the accuracy of an estimate."""
    abs_diff = abs(percent_diff)
    if abs_diff <= 5:
        return "Excellent"
    if abs_diff <= 10:
        return "Good"
    if abs_diff <= 20:
        return "Acceptable"
    return "Poor"


def calculate_percent_difference(model_10yr: float, official_10yr: float) -> float:
    """Return the signed percent difference between model and official scores."""
    difference = model_10yr - official_10yr
    if official_10yr != 0:
        return (difference / abs(official_10yr)) * 100
    return 0.0 if model_10yr == 0 else 100.0


def direction_matches(model_10yr: float, official_10yr: float) -> bool:
    """Check whether the model and official score move in the same direction."""
    return (
        (model_10yr > 0 and official_10yr > 0)
        or (model_10yr < 0 and official_10yr < 0)
        or (model_10yr == 0 and official_10yr == 0)
    )


def build_validation_result(
    *,
    policy_id: str,
    policy_name: str,
    official_10yr: float,
    official_source: str,
    model_10yr: float,
    model_first_year: float,
    model_parameters: dict | None = None,
    notes: str = "",
    direction_match: bool | None = None,
) -> ValidationResult:
    """Construct a ValidationResult from shared metrics."""
    difference = model_10yr - official_10yr
    percent_diff = calculate_percent_difference(model_10yr, official_10yr)
    if direction_match is None:
        direction_match = direction_matches(model_10yr, official_10yr)

    return ValidationResult(
        policy_id=policy_id,
        policy_name=policy_name,
        official_10yr=official_10yr,
        official_source=official_source,
        model_10yr=model_10yr,
        model_first_year=model_first_year,
        difference=difference,
        percent_difference=percent_diff,
        direction_match=direction_match,
        accuracy_rating=_rate_accuracy(percent_diff),
        model_parameters=model_parameters or {},
        notes=notes,
    )


def create_policy_from_score(score: CBOScore) -> TaxPolicy | None:
    """
    Create a TaxPolicy object matching a known CBO score's parameters.

    Returns None if the score doesn't have enough parameters.
    """
    if score.policy_type != "income_tax":
        return None

    if score.rate_change is None:
        return None

    return TaxPolicy(
        name=f"Validation: {score.name}",
        description=score.description,
        policy_type=PolicyType.INCOME_TAX,
        rate_change=score.rate_change,
        affected_income_threshold=score.income_threshold or 0,
        start_year=2025,
        duration_years=10,
    )


def create_capital_gains_policy_from_score(
    score: CBOScore,
    *,
    baseline_capital_gains_rate: float,
    baseline_realizations_billions: float,
    short_run_elasticity: float = 0.8,
    long_run_elasticity: float = 0.4,
    transition_years: int = 3,
    use_time_varying: bool = True,
) -> CapitalGainsPolicy:
    """
    Create a CapitalGainsPolicy from a score entry plus required extra inputs.
    """
    if score.rate_change is None:
        raise ValueError("score.rate_change is required")

    return CapitalGainsPolicy(
        name=f"Validation: {score.name}",
        description=score.description,
        policy_type=PolicyType.CAPITAL_GAINS_TAX,
        rate_change=score.rate_change,
        affected_income_threshold=score.income_threshold or 0,
        start_year=2025,
        duration_years=10,
        baseline_capital_gains_rate=float(baseline_capital_gains_rate),
        baseline_realizations_billions=float(baseline_realizations_billions),
        short_run_elasticity=float(short_run_elasticity),
        long_run_elasticity=float(long_run_elasticity),
        transition_years=int(transition_years),
        use_time_varying_elasticity=use_time_varying,
    )


create_capital_gains_example_from_score = create_capital_gains_policy_from_score


def validate_policy(
    score: CBOScore,
    scorer: FiscalPolicyScorer | None = None,
    dynamic: bool = False,
) -> ValidationResult | None:
    """
    Validate model output against a known CBO score.

    Args:
        score: The official score to validate against
        scorer: Pre-initialized scorer (creates new one if None)
        dynamic: Whether to use dynamic scoring

    Returns:
        ValidationResult or None if policy can't be replicated
    """
    policy = create_policy_from_score(score)
    if policy is None:
        return None

    if scorer is None:
        scorer = FiscalPolicyScorer(start_year=2025, use_real_data=True)

    try:
        result = scorer.score_policy(policy, dynamic=dynamic)
    except Exception as exc:
        return ValidationResult(
            policy_id=score.policy_id,
            policy_name=score.name,
            official_10yr=score.ten_year_cost,
            official_source=score.source.value,
            model_10yr=0.0,
            model_first_year=0.0,
            difference=score.ten_year_cost,
            percent_difference=100.0,
            direction_match=False,
            accuracy_rating="Error",
            notes=f"Model error: {exc!s}",
        )

    return build_validation_result(
        policy_id=score.policy_id,
        policy_name=score.name,
        official_10yr=score.ten_year_cost,
        official_source=score.source.value,
        model_10yr=result.total_10_year_cost,
        model_first_year=result.final_deficit_effect[0],
        model_parameters={
            "rate_change": policy.rate_change,
            "threshold": policy.affected_income_threshold,
            "taxpayers_millions": policy.affected_taxpayers_millions,
            "avg_income": policy.avg_taxable_income_in_bracket,
        },
        notes=score.notes or "",
    )


def validate_all(dynamic: bool = False, verbose: bool = True) -> list[ValidationResult]:
    """
    Run validation against all suitable policies in the database.
    """
    targets = get_validation_targets()

    if verbose:
        print(f"\nRunning validation against {len(targets)} policies...")
        print("=" * 70)

    scorer = FiscalPolicyScorer(start_year=2025, use_real_data=True)

    results = []
    for score in targets:
        if verbose:
            print(f"\nValidating: {score.name}...")

        result = validate_policy(score, scorer=scorer, dynamic=dynamic)
        if result:
            results.append(result)
            if verbose:
                print(f"  {result.get_summary()}")

    return results


def run_validation_suite(verbose: bool = True) -> dict:
    """
    Run complete validation suite and return summary statistics.
    """
    results = validate_all(dynamic=False, verbose=verbose)

    if not results:
        return {"error": "No policies could be validated"}

    accurate_count = sum(1 for result in results if result.is_accurate)
    direction_match_count = sum(1 for result in results if result.direction_match)
    percent_diffs = [abs(result.percent_difference) for result in results]

    summary = {
        "total_policies": len(results),
        "accurate_count": accurate_count,
        "accuracy_rate": accurate_count / len(results) * 100,
        "direction_match_count": direction_match_count,
        "direction_match_rate": direction_match_count / len(results) * 100,
        "mean_percent_error": np.mean(percent_diffs),
        "median_percent_error": np.median(percent_diffs),
        "max_percent_error": np.max(percent_diffs),
        "min_percent_error": np.min(percent_diffs),
        "ratings": {
            "Excellent": sum(1 for result in results if result.accuracy_rating == "Excellent"),
            "Good": sum(1 for result in results if result.accuracy_rating == "Good"),
            "Acceptable": sum(1 for result in results if result.accuracy_rating == "Acceptable"),
            "Poor": sum(1 for result in results if result.accuracy_rating == "Poor"),
        },
        "results": results,
    }

    if verbose:
        print("\n" + "=" * 70)
        print("VALIDATION SUMMARY")
        print("=" * 70)
        print(f"Policies tested: {summary['total_policies']}")
        print(
            f"Within 20% accuracy: {summary['accurate_count']} "
            f"({summary['accuracy_rate']:.0f}%)"
        )
        print(
            f"Direction match: {summary['direction_match_count']} "
            f"({summary['direction_match_rate']:.0f}%)"
        )
        print(f"Mean error: {summary['mean_percent_error']:.1f}%")
        print(f"Median error: {summary['median_percent_error']:.1f}%")
        print("\nRatings breakdown:")
        for rating, count in summary["ratings"].items():
            print(f"  {rating}: {count}")

    return summary


def quick_validate(
    rate_change: float,
    income_threshold: float,
    expected_10yr: float,
    policy_name: str = "Test Policy",
) -> ValidationResult:
    """
    Quick validation of a specific policy configuration.
    """
    policy = TaxPolicy(
        name=policy_name,
        description=f"{rate_change*100:+.1f}pp rate change for income ≥${income_threshold:,.0f}",
        policy_type=PolicyType.INCOME_TAX,
        rate_change=rate_change,
        affected_income_threshold=income_threshold,
    )

    scorer = FiscalPolicyScorer(start_year=2025, use_real_data=True)
    result = scorer.score_policy(policy, dynamic=False)
    direction_match = True if expected_10yr == 0 else direction_matches(
        result.total_10_year_cost,
        expected_10yr,
    )

    return build_validation_result(
        policy_id="quick_test",
        policy_name=policy_name,
        official_10yr=expected_10yr,
        official_source="User-provided",
        model_10yr=result.total_10_year_cost,
        model_first_year=result.final_deficit_effect[0],
        model_parameters={
            "rate_change": rate_change,
            "threshold": income_threshold,
            "taxpayers_millions": policy.affected_taxpayers_millions,
            "avg_income": policy.avg_taxable_income_in_bracket,
        },
        direction_match=direction_match,
    )
