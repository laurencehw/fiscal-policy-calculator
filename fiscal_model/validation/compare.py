"""
Comparison and validation functions for model outputs vs official scores.

Provides tools to:
- Compare model estimates to published CBO/JCT scores
- Calculate accuracy metrics
- Generate validation reports
"""

from dataclasses import dataclass, field
from typing import Optional
import numpy as np

from .cbo_scores import CBOScore, KNOWN_SCORES, get_validation_targets
from ..policies import TaxPolicy, PolicyType
from ..scoring import FiscalPolicyScorer, ScoringResult


@dataclass
class ValidationResult:
    """
    Result of validating model output against an official score.
    """
    policy_id: str
    policy_name: str
    
    # Official estimate
    official_10yr: float  # Official 10-year cost in billions
    official_source: str
    
    # Model estimate
    model_10yr: float  # Our model's 10-year estimate
    model_first_year: float  # Our model's first year estimate
    
    # Comparison metrics
    difference: float  # Model - Official (billions)
    percent_difference: float  # (Model - Official) / |Official| * 100
    
    # Direction check
    direction_match: bool  # Does model agree on sign (cost vs savings)?
    
    # Accuracy rating
    accuracy_rating: str  # "Excellent", "Good", "Acceptable", "Poor"
    
    # Details
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
    elif abs_diff <= 10:
        return "Good"
    elif abs_diff <= 20:
        return "Acceptable"
    else:
        return "Poor"


def create_policy_from_score(score: CBOScore) -> Optional[TaxPolicy]:
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
        # Let auto-population handle taxpayer counts
    )


def validate_policy(
    score: CBOScore,
    scorer: Optional[FiscalPolicyScorer] = None,
    dynamic: bool = False
) -> Optional[ValidationResult]:
    """
    Validate model output against a known CBO score.
    
    Args:
        score: The official score to validate against
        scorer: Pre-initialized scorer (creates new one if None)
        dynamic: Whether to use dynamic scoring
        
    Returns:
        ValidationResult or None if policy can't be replicated
    """
    # Create matching policy
    policy = create_policy_from_score(score)
    if policy is None:
        return None
    
    # Initialize scorer if needed
    if scorer is None:
        scorer = FiscalPolicyScorer(start_year=2025, use_real_data=True)
    
    # Score the policy
    try:
        result = scorer.score_policy(policy, dynamic=dynamic)
    except Exception as e:
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
            notes=f"Model error: {str(e)}"
        )
    
    # Calculate metrics
    # Note: Our model returns deficit effect (positive = increases deficit)
    # CBO scores use same convention (positive = cost/increases deficit)
    model_10yr = result.total_10_year_cost
    model_first_year = result.final_deficit_effect[0]
    
    difference = model_10yr - score.ten_year_cost
    
    # Percent difference (handle zero carefully)
    if score.ten_year_cost != 0:
        percent_diff = (difference / abs(score.ten_year_cost)) * 100
    else:
        percent_diff = 0.0 if model_10yr == 0 else 100.0
    
    # Check direction
    direction_match = (
        (model_10yr > 0 and score.ten_year_cost > 0) or
        (model_10yr < 0 and score.ten_year_cost < 0) or
        (model_10yr == 0 and score.ten_year_cost == 0)
    )
    
    return ValidationResult(
        policy_id=score.policy_id,
        policy_name=score.name,
        official_10yr=score.ten_year_cost,
        official_source=score.source.value,
        model_10yr=model_10yr,
        model_first_year=model_first_year,
        difference=difference,
        percent_difference=percent_diff,
        direction_match=direction_match,
        accuracy_rating=_rate_accuracy(percent_diff),
        model_parameters={
            "rate_change": policy.rate_change,
            "threshold": policy.affected_income_threshold,
            "taxpayers_millions": policy.affected_taxpayers_millions,
            "avg_income": policy.avg_taxable_income_in_bracket,
        },
        notes=score.notes or ""
    )


def validate_all(
    dynamic: bool = False,
    verbose: bool = True
) -> list[ValidationResult]:
    """
    Run validation against all suitable policies in the database.
    
    Args:
        dynamic: Whether to use dynamic scoring
        verbose: Whether to print progress
        
    Returns:
        List of ValidationResult objects
    """
    # Get policies suitable for validation
    targets = get_validation_targets()
    
    if verbose:
        print(f"\nRunning validation against {len(targets)} policies...")
        print("=" * 70)
    
    # Initialize scorer once
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
    
    Returns:
        Dictionary with validation summary
    """
    results = validate_all(dynamic=False, verbose=verbose)
    
    if not results:
        return {"error": "No policies could be validated"}
    
    # Calculate summary statistics
    accurate_count = sum(1 for r in results if r.is_accurate)
    direction_match_count = sum(1 for r in results if r.direction_match)
    
    percent_diffs = [abs(r.percent_difference) for r in results]
    
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
            "Excellent": sum(1 for r in results if r.accuracy_rating == "Excellent"),
            "Good": sum(1 for r in results if r.accuracy_rating == "Good"),
            "Acceptable": sum(1 for r in results if r.accuracy_rating == "Acceptable"),
            "Poor": sum(1 for r in results if r.accuracy_rating == "Poor"),
        },
        "results": results,
    }
    
    if verbose:
        print("\n" + "=" * 70)
        print("VALIDATION SUMMARY")
        print("=" * 70)
        print(f"Policies tested: {summary['total_policies']}")
        print(f"Within 20% accuracy: {summary['accurate_count']} ({summary['accuracy_rate']:.0f}%)")
        print(f"Direction match: {summary['direction_match_count']} ({summary['direction_match_rate']:.0f}%)")
        print(f"Mean error: {summary['mean_percent_error']:.1f}%")
        print(f"Median error: {summary['median_percent_error']:.1f}%")
        print(f"\nRatings breakdown:")
        for rating, count in summary['ratings'].items():
            print(f"  {rating}: {count}")
    
    return summary


def generate_validation_report(results: list[ValidationResult]) -> str:
    """
    Generate a markdown validation report.
    
    Args:
        results: List of ValidationResult objects
        
    Returns:
        Markdown-formatted report string
    """
    lines = [
        "# Model Validation Report",
        "",
        f"**Date:** {__import__('datetime').datetime.now().strftime('%Y-%m-%d')}",
        f"**Policies Tested:** {len(results)}",
        "",
        "## Summary",
        "",
    ]
    
    if results:
        accurate = sum(1 for r in results if r.is_accurate)
        direction_ok = sum(1 for r in results if r.direction_match)
        mean_err = np.mean([abs(r.percent_difference) for r in results])
        
        lines.extend([
            f"- **Accuracy Rate:** {accurate}/{len(results)} within 20% ({accurate/len(results)*100:.0f}%)",
            f"- **Direction Match:** {direction_ok}/{len(results)} ({direction_ok/len(results)*100:.0f}%)",
            f"- **Mean Error:** {mean_err:.1f}%",
            "",
        ])
    
    # Results table
    lines.extend([
        "## Detailed Results",
        "",
        "| Policy | Official | Model | Diff | % Error | Rating |",
        "|--------|----------|-------|------|---------|--------|",
    ])
    
    for r in results:
        lines.append(
            f"| {r.policy_name[:30]} | "
            f"${r.official_10yr:,.0f}B | "
            f"${r.model_10yr:,.0f}B | "
            f"${r.difference:+,.0f}B | "
            f"{r.percent_difference:+.1f}% | "
            f"{r.accuracy_rating} |"
        )
    
    lines.extend([
        "",
        "## Methodology Notes",
        "",
        "- Model uses IRS SOI data for taxpayer counts and income distributions",
        "- Behavioral responses modeled via Elasticity of Taxable Income (ETI = 0.25)",
        "- Official scores may use different baselines and assumptions",
        "- Some variation expected due to data vintage differences",
        "",
        "## Interpretation Guide",
        "",
        "| Rating | % Error | Interpretation |",
        "|--------|---------|----------------|",
        "| Excellent | <=5% | Model closely matches official estimates |",
        "| Good | 5-10% | Model is reasonably accurate |",
        "| Acceptable | 10-20% | Model provides directional guidance |",
        "| Poor | >20% | Significant deviation - investigate methodology |",
    ])
    
    return "\n".join(lines)


# =============================================================================
# QUICK VALIDATION FUNCTIONS
# =============================================================================

def quick_validate(
    rate_change: float,
    income_threshold: float,
    expected_10yr: float,
    policy_name: str = "Test Policy"
) -> ValidationResult:
    """
    Quick validation of a specific policy configuration.
    
    Args:
        rate_change: Tax rate change (e.g., -0.02 for 2pp cut)
        income_threshold: Income threshold in dollars
        expected_10yr: Expected 10-year cost in billions
        policy_name: Name for the policy
        
    Returns:
        ValidationResult comparing model to expected value
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
    
    model_10yr = result.total_10_year_cost
    difference = model_10yr - expected_10yr
    
    if expected_10yr != 0:
        percent_diff = (difference / abs(expected_10yr)) * 100
    else:
        percent_diff = 0.0 if model_10yr == 0 else 100.0
    
    direction_match = (model_10yr > 0) == (expected_10yr > 0) if expected_10yr != 0 else True
    
    return ValidationResult(
        policy_id="quick_test",
        policy_name=policy_name,
        official_10yr=expected_10yr,
        official_source="User-provided",
        model_10yr=model_10yr,
        model_first_year=result.final_deficit_effect[0],
        difference=difference,
        percent_difference=percent_diff,
        direction_match=direction_match,
        accuracy_rating=_rate_accuracy(percent_diff),
        model_parameters={
            "rate_change": rate_change,
            "threshold": income_threshold,
            "taxpayers_millions": policy.affected_taxpayers_millions,
            "avg_income": policy.avg_taxable_income_in_bracket,
        }
    )

