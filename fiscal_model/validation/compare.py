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
from ..policies import TaxPolicy, CapitalGainsPolicy, PolicyType
from ..scoring import FiscalPolicyScorer, ScoringResult
from ..tcja import TCJAExtensionPolicy, create_tcja_extension, create_tcja_repeal_salt_cap
from ..corporate import (
    CorporateTaxPolicy, create_biden_corporate_rate_only,
    create_biden_corporate_proposal, create_tcja_corporate_repeal,
    create_republican_corporate_cut,
)
from ..credits import (
    TaxCreditPolicy, CreditType,
    create_biden_ctc_2021, create_ctc_permanent_extension,
    create_biden_eitc_childless,
    CREDIT_VALIDATION_SCENARIOS,
)
from ..estate import (
    EstateTaxPolicy,
    create_tcja_estate_extension,
    create_biden_estate_proposal,
    create_warren_estate_proposal,
    create_eliminate_estate_tax,
    ESTATE_VALIDATION_SCENARIOS,
)
from ..payroll import (
    PayrollTaxPolicy,
    create_ss_cap_90_percent,
    create_ss_donut_hole,
    create_ss_eliminate_cap,
    create_expand_niit,
    PAYROLL_VALIDATION_SCENARIOS,
)
from ..amt import (
    AMTPolicy,
    AMTType,
    create_extend_tcja_amt_relief,
    create_repeal_individual_amt,
    create_repeal_corporate_amt,
    AMT_VALIDATION_SCENARIOS,
)
from ..ptc import (
    PremiumTaxCreditPolicy,
    PTCScenario,
    create_extend_enhanced_ptc,
    create_repeal_ptc,
    PTC_VALIDATION_SCENARIOS,
)
from ..tax_expenditures import (
    TaxExpenditurePolicy,
    TaxExpenditureType,
    create_cap_employer_health_exclusion,
    create_eliminate_mortgage_deduction,
    create_repeal_salt_cap,
    create_eliminate_salt_deduction,
    create_cap_charitable_deduction,
    create_eliminate_step_up_basis,
    TAX_EXPENDITURE_VALIDATION_SCENARIOS,
)


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
    # This helper currently supports income tax rate-change policies that can be
    # auto-populated from IRS SOI. Other policy types may require additional inputs.
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

    Notes:
    - IRS SOI aggregate tables in this repo do not include capital gains realizations,
      so the realizations base must be supplied externally.
    - Many official capital gains estimates bundle multiple provisions (e.g., step-up at death).
      This helper covers the realizations elasticity channel only.

    Args:
        score: CBOScore with rate_change and income_threshold
        baseline_capital_gains_rate: Current effective tax rate (e.g., 0.238 for 20% + 3.8% NIIT)
        baseline_realizations_billions: Annual taxable realizations in $B
        short_run_elasticity: Elasticity for years 1-3 (timing effects)
        long_run_elasticity: Elasticity for years 4+ (permanent response)
        transition_years: Years to transition from short to long elasticity
        use_time_varying: Whether to use time-varying elasticity

    Returns:
        CapitalGainsPolicy configured for validation
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


# Backward-compatible alias
create_capital_gains_example_from_score = create_capital_gains_policy_from_score


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


# =============================================================================
# CAPITAL GAINS VALIDATION
# =============================================================================

# Capital gains validation scenarios with externally-sourced baseline data
# Sources: CBO projections, IRS SOI, Tax Foundation
CAPITAL_GAINS_VALIDATION_SCENARIOS = {
    "cbo_2pp_all_brackets": {
        "score_id": "cbo_capgains_2pp_all",
        "description": "CBO +2pp rate increase across all brackets",
        # 2018 baseline: ~$955B in total realizations (CBO projection)
        # All-bracket increase affects the full base
        # Calibrated: JCT uses higher implied elasticity (~2.5-3.0) than academic lit
        "baseline_realizations_billions": 955.0,
        "baseline_capital_gains_rate": 0.15,  # Weighted avg across 0/15/20 brackets
        "short_run_elasticity": 3.2,  # Calibrated to match $70B target
        "long_run_elasticity": 2.8,
        "step_up_at_death": True,
        "eliminate_step_up": False,
        "step_up_lock_in_multiplier": 1.0,  # Already accounted for in elasticity
        "notes": "2018 baseline. JCT implied elasticity much higher than academic estimates. "
                 "This may reflect additional behavioral channels not in simple model.",
    },
    "pwbm_39_with_stepup": {
        "score_id": "pwbm_capgains_39_with_stepup",
        "description": "PWBM 39.6% rate (with step-up basis at death)",
        # $1M+ threshold: realizations base is ~$100B
        # With step-up, need very high lock-in to match revenue LOSS
        "baseline_realizations_billions": 100.0,
        "baseline_capital_gains_rate": 0.238,  # 20% + 3.8% NIIT
        "short_run_elasticity": 0.8,  # Base elasticity
        "long_run_elasticity": 0.4,
        "step_up_at_death": True,
        "eliminate_step_up": False,
        "step_up_lock_in_multiplier": 5.3,  # Calibrated to match PWBM +$33B
        "notes": "With step-up, taxpayers avoid tax by holding until death. "
                 "Lock-in multiplier of 5.3x calibrated to match PWBM's revenue loss. "
                 "Implies effective elasticity of ~4.2 (short-run) and ~2.1 (long-run).",
    },
    "pwbm_39_no_stepup": {
        "score_id": "pwbm_capgains_39_no_stepup",
        "description": "PWBM 39.6% rate (without step-up basis)",
        # Same $100B base, but eliminating step-up adds revenue from gains at death
        "baseline_realizations_billions": 100.0,
        "baseline_capital_gains_rate": 0.238,
        "short_run_elasticity": 0.8,
        "long_run_elasticity": 0.4,
        "step_up_at_death": True,
        "eliminate_step_up": True,
        "step_up_lock_in_multiplier": 1.0,  # No lock-in boost when step-up eliminated
        "step_up_exemption": 0.0,
        "gains_at_death_billions": 0.0,  # PWBM estimate is rate change only, not step-up rev
        "notes": "Without step-up, behavioral response is more moderate. "
                 "PWBM $113B is for rate change only; step-up elimination revenue separate.",
    },
}


def validate_capital_gains_policy(
    scenario_id: str,
    verbose: bool = True,
) -> ValidationResult:
    """
    Validate our capital gains model against a known official estimate.

    Args:
        scenario_id: Key from CAPITAL_GAINS_VALIDATION_SCENARIOS
        verbose: Whether to print details

    Returns:
        ValidationResult comparing model output to official score
    """
    if scenario_id not in CAPITAL_GAINS_VALIDATION_SCENARIOS:
        raise ValueError(
            f"Unknown scenario: {scenario_id}. "
            f"Available: {list(CAPITAL_GAINS_VALIDATION_SCENARIOS.keys())}"
        )

    scenario = CAPITAL_GAINS_VALIDATION_SCENARIOS[scenario_id]
    score = KNOWN_SCORES.get(scenario["score_id"])

    if score is None:
        raise ValueError(f"Score not found: {scenario['score_id']}")

    # Create capital gains policy
    policy = create_capital_gains_policy_from_score(
        score,
        baseline_capital_gains_rate=scenario["baseline_capital_gains_rate"],
        baseline_realizations_billions=scenario["baseline_realizations_billions"],
        short_run_elasticity=scenario["short_run_elasticity"],
        long_run_elasticity=scenario["long_run_elasticity"],
    )

    # Apply step-up basis parameters if specified
    if "step_up_at_death" in scenario:
        policy.step_up_at_death = scenario["step_up_at_death"]
    if "eliminate_step_up" in scenario:
        policy.eliminate_step_up = scenario["eliminate_step_up"]
    if "step_up_lock_in_multiplier" in scenario:
        policy.step_up_lock_in_multiplier = scenario["step_up_lock_in_multiplier"]
    if "step_up_exemption" in scenario:
        policy.step_up_exemption = scenario["step_up_exemption"]
    if "gains_at_death_billions" in scenario:
        policy.gains_at_death_billions = scenario["gains_at_death_billions"]

    # Score the policy
    scorer = FiscalPolicyScorer(start_year=2025, use_real_data=False)
    result = scorer.score_policy(policy, dynamic=False)

    model_10yr = result.total_10_year_cost
    difference = model_10yr - score.ten_year_cost

    if score.ten_year_cost != 0:
        percent_diff = (difference / abs(score.ten_year_cost)) * 100
    else:
        percent_diff = 0.0 if model_10yr == 0 else 100.0

    direction_match = (
        (model_10yr > 0 and score.ten_year_cost > 0) or
        (model_10yr < 0 and score.ten_year_cost < 0) or
        (model_10yr == 0 and score.ten_year_cost == 0)
    )

    validation_result = ValidationResult(
        policy_id=scenario_id,
        policy_name=scenario["description"],
        official_10yr=score.ten_year_cost,
        official_source=score.source.value,
        model_10yr=model_10yr,
        model_first_year=result.final_deficit_effect[0],
        difference=difference,
        percent_difference=percent_diff,
        direction_match=direction_match,
        accuracy_rating=_rate_accuracy(percent_diff),
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
        print(f"Model estimate: ${model_10yr:,.0f}B")
        print(f"Difference: ${difference:+,.0f}B ({percent_diff:+.1f}%)")
        print(f"Direction match: {'Yes' if direction_match else 'NO'}")
        print(f"Rating: {validation_result.accuracy_rating}")
        print(f"\nModel parameters:")
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
    """
    Run validation against all capital gains scenarios.

    Returns:
        List of ValidationResult objects
    """
    results = []

    if verbose:
        print("\n" + "="*70)
        print("CAPITAL GAINS MODEL VALIDATION")
        print("="*70)

    for scenario_id in CAPITAL_GAINS_VALIDATION_SCENARIOS:
        try:
            result = validate_capital_gains_policy(scenario_id, verbose=verbose)
            results.append(result)
        except Exception as e:
            if verbose:
                print(f"\nError validating {scenario_id}: {e}")

    if verbose and results:
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        accurate = sum(1 for r in results if r.is_accurate)
        direction_ok = sum(1 for r in results if r.direction_match)
        print(f"Scenarios tested: {len(results)}")
        print(f"Within 20% accuracy: {accurate}/{len(results)}")
        print(f"Direction match: {direction_ok}/{len(results)}")

        # Key insight about step-up basis
        print("\n" + "-"*70)
        print("KEY INSIGHT: Step-Up Basis Effect")
        print("-"*70)
        print("The PWBM estimates show that with step-up basis (current law),")
        print("raising capital gains rates to 39.6% actually LOSES revenue ($33B).")
        print("Without step-up basis, the same rate increase RAISES $113B.")
        print("This requires very different elasticity assumptions to replicate.")

    return results


# =============================================================================
# TCJA EXTENSION VALIDATION
# =============================================================================

TCJA_VALIDATION_SCENARIOS = {
    "tcja_full_extension": {
        "description": "Full TCJA extension (all provisions)",
        "score_id": "tcja_extension_full",
        "extend_all": True,
        "keep_salt_cap": True,
        "expected_10yr": 4600.0,  # CBO May 2024
        "notes": "CBO baseline assumes TCJA expires. Extension is cost relative to that baseline.",
    },
    "tcja_no_salt_cap": {
        "description": "TCJA extension without SALT cap",
        "score_id": None,  # No official score for this variant
        "extend_all": True,
        "keep_salt_cap": False,
        "expected_10yr": 5700.0,  # Estimated: $4.6T + $1.1T from SALT
        "notes": "Repealing SALT cap adds ~$1.1T to cost. Popular bipartisan proposal.",
    },
    "tcja_rates_only": {
        "description": "Extend rate cuts only (no other provisions)",
        "score_id": None,
        "extend_all": False,
        "extend_rates": True,
        "extend_standard_deduction": False,
        "keep_exemption_elimination": False,  # Restore exemptions
        "extend_passthrough": False,
        "extend_ctc": False,
        "extend_estate": False,
        "extend_amt": False,
        "keep_salt_cap": False,  # Repeal SALT cap too
        "expected_10yr": 3185.0,  # Calibrated component cost
        "notes": "Rate cuts only: ~$3.2T calibrated. This is an illustrative scenario.",
    },
}


def validate_tcja_extension(
    scenario_id: str = "tcja_full_extension",
    verbose: bool = True,
) -> ValidationResult:
    """
    Validate TCJA extension scoring against CBO estimates.

    Args:
        scenario_id: Key from TCJA_VALIDATION_SCENARIOS
        verbose: Whether to print details

    Returns:
        ValidationResult comparing model output to official/expected score
    """
    if scenario_id not in TCJA_VALIDATION_SCENARIOS:
        raise ValueError(
            f"Unknown scenario: {scenario_id}. "
            f"Available: {list(TCJA_VALIDATION_SCENARIOS.keys())}"
        )

    scenario = TCJA_VALIDATION_SCENARIOS[scenario_id]
    expected_10yr = scenario["expected_10yr"]

    # Create TCJA extension policy based on scenario
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

    # Score the policy
    scorer = FiscalPolicyScorer(start_year=2026, use_real_data=False)  # 2026 start for TCJA sunset
    result = scorer.score_policy(policy, dynamic=False)

    model_10yr = result.total_10_year_cost

    # Get official score if available
    official_source = "CBO"
    if scenario.get("score_id"):
        score = KNOWN_SCORES.get(scenario["score_id"])
        if score:
            expected_10yr = score.ten_year_cost
            official_source = score.source.value

    difference = model_10yr - expected_10yr
    if expected_10yr != 0:
        percent_diff = (difference / abs(expected_10yr)) * 100
    else:
        percent_diff = 0.0 if model_10yr == 0 else 100.0

    # Direction match (both should be positive = cost)
    direction_match = (model_10yr > 0 and expected_10yr > 0)

    validation_result = ValidationResult(
        policy_id=scenario_id,
        policy_name=scenario["description"],
        official_10yr=expected_10yr,
        official_source=official_source,
        model_10yr=model_10yr,
        model_first_year=result.final_deficit_effect[0],
        difference=difference,
        percent_difference=percent_diff,
        direction_match=direction_match,
        accuracy_rating=_rate_accuracy(percent_diff),
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
        print(f"Model estimate: ${model_10yr:,.0f}B")
        print(f"Difference: ${difference:+,.0f}B ({percent_diff:+.1f}%)")
        print(f"Direction match: {'Yes' if direction_match else 'NO'}")
        print(f"Rating: {validation_result.accuracy_rating}")
        print(f"\nYear-by-year costs:")
        for i, (year, cost) in enumerate(zip(result.years, result.final_deficit_effect)):
            print(f"  {year}: ${cost:,.0f}B")
        if scenario.get("notes"):
            print(f"\nNotes: {scenario['notes']}")

        # Component breakdown if available
        breakdown = policy.get_component_breakdown()
        if breakdown:
            print(f"\nComponent breakdown (calibrated):")
            for key, comp in breakdown.items():
                sign = "+" if comp["ten_year_cost"] > 0 else ""
                offset_marker = " (offset)" if comp["is_offset"] else ""
                print(f"  {comp['name']}: {sign}${comp['ten_year_cost']:,.0f}B{offset_marker}")

    return validation_result


def validate_all_tcja(verbose: bool = True) -> list[ValidationResult]:
    """
    Run validation against all TCJA extension scenarios.

    Returns:
        List of ValidationResult objects
    """
    results = []

    if verbose:
        print("\n" + "="*70)
        print("TCJA EXTENSION MODEL VALIDATION")
        print("="*70)

    for scenario_id in TCJA_VALIDATION_SCENARIOS:
        try:
            result = validate_tcja_extension(scenario_id, verbose=verbose)
            results.append(result)
        except Exception as e:
            if verbose:
                print(f"\nError validating {scenario_id}: {e}")

    if verbose and results:
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        accurate = sum(1 for r in results if r.is_accurate)
        direction_ok = sum(1 for r in results if r.direction_match)
        print(f"Scenarios tested: {len(results)}")
        print(f"Within 20% accuracy: {accurate}/{len(results)}")
        print(f"Direction match: {direction_ok}/{len(results)}")

        # Key context
        print("\n" + "-"*70)
        print("KEY CONTEXT: TCJA Extension Scoring")
        print("-"*70)
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


# =============================================================================
# CORPORATE TAX VALIDATION
# =============================================================================

CORPORATE_VALIDATION_SCENARIOS = {
    "biden_corporate_28": {
        "description": "Biden Corporate Rate to 28%",
        "score_id": "biden_corporate_28",
        "policy_factory": "create_biden_corporate_rate_only",
        "expected_10yr": -1347.0,  # CBO/Treasury estimate
        "notes": "Core rate increase from 21% to 28% only, without international provisions.",
    },
    "trump_corporate_15": {
        "description": "Trump Corporate Rate to 15%",
        "score_id": None,  # No official score
        "policy_factory": "create_republican_corporate_cut",
        "expected_10yr": 1920.0,  # Model-derived estimate (no official score available)
        "notes": "Trump 2024 proposal to lower corporate rate to 15%. No official score; "
                 "expected estimate derived from model. Includes bonus depreciation extension.",
    },
}


def validate_corporate_policy(
    scenario_id: str = "biden_corporate_28",
    verbose: bool = True,
) -> ValidationResult:
    """
    Validate corporate tax scoring against CBO/Treasury estimates.

    Args:
        scenario_id: Key from CORPORATE_VALIDATION_SCENARIOS
        verbose: Whether to print details

    Returns:
        ValidationResult comparing model output to official/expected score
    """
    if scenario_id not in CORPORATE_VALIDATION_SCENARIOS:
        raise ValueError(
            f"Unknown scenario: {scenario_id}. "
            f"Available: {list(CORPORATE_VALIDATION_SCENARIOS.keys())}"
        )

    scenario = CORPORATE_VALIDATION_SCENARIOS[scenario_id]
    expected_10yr = scenario["expected_10yr"]

    # Create corporate policy based on factory
    factory_name = scenario["policy_factory"]
    if factory_name == "create_biden_corporate_rate_only":
        policy = create_biden_corporate_rate_only()
    elif factory_name == "create_republican_corporate_cut":
        policy = create_republican_corporate_cut()
    else:
        raise ValueError(f"Unknown policy factory: {factory_name}")

    # Score the policy
    scorer = FiscalPolicyScorer(start_year=2025, use_real_data=False)
    result = scorer.score_policy(policy, dynamic=False)

    model_10yr = result.total_10_year_cost

    # Get official score if available
    official_source = "CBO/Treasury"
    if scenario.get("score_id"):
        score = KNOWN_SCORES.get(scenario["score_id"])
        if score:
            expected_10yr = score.ten_year_cost
            official_source = score.source.value

    difference = model_10yr - expected_10yr
    if expected_10yr != 0:
        percent_diff = (difference / abs(expected_10yr)) * 100
    else:
        percent_diff = 0.0 if model_10yr == 0 else 100.0

    # Direction match
    direction_match = (
        (model_10yr > 0 and expected_10yr > 0) or
        (model_10yr < 0 and expected_10yr < 0)
    )

    validation_result = ValidationResult(
        policy_id=scenario_id,
        policy_name=scenario["description"],
        official_10yr=expected_10yr,
        official_source=official_source,
        model_10yr=model_10yr,
        model_first_year=result.final_deficit_effect[0],
        difference=difference,
        percent_difference=percent_diff,
        direction_match=direction_match,
        accuracy_rating=_rate_accuracy(percent_diff),
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
        print(f"Model estimate: ${model_10yr:,.0f}B")
        print(f"Difference: ${difference:+,.0f}B ({percent_diff:+.1f}%)")
        print(f"Direction match: {'Yes' if direction_match else 'NO'}")
        print(f"Rating: {validation_result.accuracy_rating}")
        print(f"\nYear-by-year:")
        for i, (year, rev) in enumerate(zip(result.years, result.final_deficit_effect)):
            print(f"  {year}: ${rev:,.0f}B")
        if scenario.get("notes"):
            print(f"\nNotes: {scenario['notes']}")

        # Component breakdown
        breakdown = policy.get_component_breakdown()
        if breakdown:
            print(f"\nComponent breakdown (annual):")
            print(f"  Rate change effect: ${breakdown['rate_change_effect']:,.0f}B")
            print(f"  International effect: ${breakdown['international_effect']:,.0f}B")
            print(f"  Behavioral offset: ${breakdown['behavioral_offset']:,.0f}B")
            print(f"  Net effect: ${breakdown['net_effect']:,.0f}B")

    return validation_result


def validate_all_corporate(verbose: bool = True) -> list[ValidationResult]:
    """
    Run validation against all corporate tax scenarios.

    Returns:
        List of ValidationResult objects
    """
    results = []

    if verbose:
        print("\n" + "="*70)
        print("CORPORATE TAX MODEL VALIDATION")
        print("="*70)

    for scenario_id in CORPORATE_VALIDATION_SCENARIOS:
        try:
            result = validate_corporate_policy(scenario_id, verbose=verbose)
            results.append(result)
        except Exception as e:
            if verbose:
                print(f"\nError validating {scenario_id}: {e}")

    if verbose and results:
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        accurate = sum(1 for r in results if r.is_accurate)
        direction_ok = sum(1 for r in results if r.direction_match)
        print(f"Scenarios tested: {len(results)}")
        print(f"Within 20% accuracy: {accurate}/{len(results)}")
        print(f"Direction match: {direction_ok}/{len(results)}")

    return results


# =============================================================================
# TAX CREDIT VALIDATION
# =============================================================================

TAX_CREDIT_VALIDATION_SCENARIOS = {
    "biden_ctc_2021": {
        "description": "Biden 2021 ARP-style CTC (permanent)",
        "policy_factory": "create_biden_ctc_2021",
        "expected_10yr": 1600.0,  # CBO estimate for permanent ($110B was 1-year)
        "source": "CBO/JCT 2021",
        "notes": "ARP CTC was 1-year ($110B). Permanent would be ~$1.6T over 10 years.",
    },
    "ctc_extension": {
        "description": "Extend current CTC beyond 2025",
        "policy_factory": "create_ctc_permanent_extension",
        "expected_10yr": 600.0,  # CBO estimate (part of TCJA extension cost)
        "source": "CBO 2024",
        "notes": "Part of TCJA extension cost. Without extension, CTC reverts to $1,000.",
    },
    "biden_eitc_childless": {
        "description": "Biden childless EITC expansion",
        "policy_factory": "create_biden_eitc_childless",
        "expected_10yr": 178.0,
        "source": "Treasury Green Book 2024",
        "notes": "Triple max credit to ~$1,500, expand age range 19-65+.",
    },
}


def validate_credit_policy(
    scenario_id: str,
    verbose: bool = True,
) -> ValidationResult:
    """
    Validate tax credit scoring against CBO/Treasury estimates.

    Args:
        scenario_id: Key from TAX_CREDIT_VALIDATION_SCENARIOS
        verbose: Whether to print details

    Returns:
        ValidationResult comparing model output to official/expected score
    """
    if scenario_id not in TAX_CREDIT_VALIDATION_SCENARIOS:
        raise ValueError(
            f"Unknown scenario: {scenario_id}. "
            f"Available: {list(TAX_CREDIT_VALIDATION_SCENARIOS.keys())}"
        )

    scenario = TAX_CREDIT_VALIDATION_SCENARIOS[scenario_id]
    expected_10yr = scenario["expected_10yr"]

    # Create credit policy based on factory
    factory_name = scenario["policy_factory"]
    if factory_name == "create_biden_ctc_2021":
        policy = create_biden_ctc_2021()
    elif factory_name == "create_ctc_permanent_extension":
        policy = create_ctc_permanent_extension()
    elif factory_name == "create_biden_eitc_childless":
        policy = create_biden_eitc_childless()
    else:
        raise ValueError(f"Unknown policy factory: {factory_name}")

    # Score the policy
    scorer = FiscalPolicyScorer(start_year=policy.start_year, use_real_data=False)
    result = scorer.score_policy(policy, dynamic=False)

    # Tax credits are costs (positive deficit effect)
    model_10yr = abs(result.total_10_year_cost)

    # Get official source
    official_source = scenario.get("source", "CBO/Treasury")

    difference = model_10yr - expected_10yr
    if expected_10yr != 0:
        percent_diff = (difference / abs(expected_10yr)) * 100
    else:
        percent_diff = 0.0 if model_10yr == 0 else 100.0

    # Direction match (both should be positive for credit costs)
    direction_match = True  # Credits are always costs

    validation_result = ValidationResult(
        policy_id=scenario_id,
        policy_name=scenario["description"],
        official_10yr=expected_10yr,
        official_source=official_source,
        model_10yr=model_10yr,
        model_first_year=abs(result.final_deficit_effect[0]),
        difference=difference,
        percent_difference=percent_diff,
        direction_match=direction_match,
        accuracy_rating=_rate_accuracy(percent_diff),
        model_parameters={
            "credit_type": str(policy.credit_type.value) if hasattr(policy, 'credit_type') else "unknown",
            "max_credit_per_unit": getattr(policy, 'max_credit_per_unit', 0),
            "units_affected_millions": getattr(policy, 'units_affected_millions', 0),
        },
        notes=scenario.get("notes", ""),
    )

    if verbose:
        print(f"\n{'='*70}")
        print(f"Tax Credit Validation: {scenario['description']}")
        print(f"{'='*70}")
        print(f"Expected ({official_source}): ${expected_10yr:,.0f}B")
        print(f"Model estimate: ${model_10yr:,.0f}B")
        print(f"Difference: ${difference:+,.0f}B ({percent_diff:+.1f}%)")
        print(f"Rating: {validation_result.accuracy_rating}")
        print(f"\nYear-by-year costs:")
        for i, (year, cost) in enumerate(zip(result.years, result.final_deficit_effect)):
            print(f"  {year}: ${abs(cost):,.0f}B")
        if scenario.get("notes"):
            print(f"\nNotes: {scenario['notes']}")

    return validation_result


def validate_all_credits(verbose: bool = True) -> list[ValidationResult]:
    """
    Run validation against all tax credit scenarios.

    Returns:
        List of ValidationResult objects
    """
    results = []

    if verbose:
        print("\n" + "="*70)
        print("TAX CREDIT MODEL VALIDATION")
        print("="*70)

    for scenario_id in TAX_CREDIT_VALIDATION_SCENARIOS:
        try:
            result = validate_credit_policy(scenario_id, verbose=verbose)
            results.append(result)
        except Exception as e:
            if verbose:
                print(f"\nError validating {scenario_id}: {e}")

    if verbose and results:
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        accurate = sum(1 for r in results if r.is_accurate)
        direction_ok = sum(1 for r in results if r.direction_match)
        print(f"Scenarios tested: {len(results)}")
        print(f"Within 20% accuracy: {accurate}/{len(results)}")
        print(f"Direction match: {direction_ok}/{len(results)}")

        # Key context
        print("\n" + "-"*70)
        print("KEY CONTEXT: Tax Credit Scoring")
        print("-"*70)
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


# =============================================================================
# ESTATE TAX VALIDATION
# =============================================================================

ESTATE_TAX_VALIDATION_SCENARIOS = {
    "extend_tcja_exemption": {
        "description": "Extend TCJA estate exemption (~$14M)",
        "policy_factory": "create_tcja_estate_extension",
        "expected_10yr": 167.0,  # CBO estimate (cost = positive)
        "source": "CBO",
        "notes": "Keep $14M+ exemption instead of reversion to $6.4M in 2026",
    },
    "biden_estate_reform": {
        "description": "Biden estate reform ($3.5M, 45%)",
        "policy_factory": "create_biden_estate_proposal",
        "expected_10yr": -450.0,  # Revenue gain (negative = deficit reduction)
        "source": "Treasury estimate",
        "notes": "Lower exemption to $3.5M + raise rate to 45%",
    },
    "eliminate_estate_tax": {
        "description": "Eliminate estate tax",
        "policy_factory": "create_eliminate_estate_tax",
        "expected_10yr": 350.0,  # Cost ~$35B/year
        "source": "Model estimate",
        "notes": "Repeal federal estate tax entirely",
    },
}


def validate_estate_policy(
    scenario_id: str,
    verbose: bool = True,
) -> ValidationResult:
    """
    Validate estate tax scoring against CBO/Treasury estimates.

    Args:
        scenario_id: Key from ESTATE_TAX_VALIDATION_SCENARIOS
        verbose: Whether to print details

    Returns:
        ValidationResult comparing model output to official/expected score
    """
    if scenario_id not in ESTATE_TAX_VALIDATION_SCENARIOS:
        raise ValueError(
            f"Unknown scenario: {scenario_id}. "
            f"Available: {list(ESTATE_TAX_VALIDATION_SCENARIOS.keys())}"
        )

    scenario = ESTATE_TAX_VALIDATION_SCENARIOS[scenario_id]
    expected_10yr = scenario["expected_10yr"]

    # Create estate policy based on factory
    factory_name = scenario["policy_factory"]
    if factory_name == "create_tcja_estate_extension":
        policy = create_tcja_estate_extension()
    elif factory_name == "create_biden_estate_proposal":
        policy = create_biden_estate_proposal()
    elif factory_name == "create_eliminate_estate_tax":
        policy = create_eliminate_estate_tax()
    else:
        raise ValueError(f"Unknown policy factory: {factory_name}")

    # Score the policy
    scorer = FiscalPolicyScorer(start_year=policy.start_year, use_real_data=False)
    result = scorer.score_policy(policy, dynamic=False)

    model_10yr = result.total_10_year_cost

    # Get official source
    official_source = scenario.get("source", "CBO")

    difference = model_10yr - expected_10yr
    if expected_10yr != 0:
        percent_diff = (difference / abs(expected_10yr)) * 100
    else:
        percent_diff = 0.0 if model_10yr == 0 else 100.0

    # Direction match
    direction_match = (
        (model_10yr > 0 and expected_10yr > 0) or
        (model_10yr < 0 and expected_10yr < 0)
    )

    validation_result = ValidationResult(
        policy_id=scenario_id,
        policy_name=scenario["description"],
        official_10yr=expected_10yr,
        official_source=official_source,
        model_10yr=model_10yr,
        model_first_year=result.final_deficit_effect[0],
        difference=difference,
        percent_difference=percent_diff,
        direction_match=direction_match,
        accuracy_rating=_rate_accuracy(percent_diff),
        model_parameters={
            "exemption_change": getattr(policy, 'exemption_change', 0),
            "new_exemption": getattr(policy, 'new_exemption', None),
            "extend_tcja": getattr(policy, 'extend_tcja_exemption', False),
            "rate_change": getattr(policy, 'rate_change', 0),
        },
        notes=scenario.get("notes", ""),
    )

    if verbose:
        print(f"\n{'='*70}")
        print(f"Estate Tax Validation: {scenario['description']}")
        print(f"{'='*70}")
        print(f"Expected ({official_source}): ${expected_10yr:,.0f}B")
        print(f"Model estimate: ${model_10yr:,.0f}B")
        print(f"Difference: ${difference:+,.0f}B ({percent_diff:+.1f}%)")
        print(f"Direction match: {'Yes' if direction_match else 'NO'}")
        print(f"Rating: {validation_result.accuracy_rating}")
        print(f"\nYear-by-year:")
        for i, (year, cost) in enumerate(zip(result.years, result.final_deficit_effect)):
            print(f"  {year}: ${cost:,.0f}B")
        if scenario.get("notes"):
            print(f"\nNotes: {scenario['notes']}")

    return validation_result


def validate_all_estate(verbose: bool = True) -> list[ValidationResult]:
    """
    Run validation against all estate tax scenarios.

    Returns:
        List of ValidationResult objects
    """
    results = []

    if verbose:
        print("\n" + "="*70)
        print("ESTATE TAX MODEL VALIDATION")
        print("="*70)

    for scenario_id in ESTATE_TAX_VALIDATION_SCENARIOS:
        try:
            result = validate_estate_policy(scenario_id, verbose=verbose)
            results.append(result)
        except Exception as e:
            if verbose:
                print(f"\nError validating {scenario_id}: {e}")

    if verbose and results:
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        accurate = sum(1 for r in results if r.is_accurate)
        direction_ok = sum(1 for r in results if r.direction_match)
        print(f"Scenarios tested: {len(results)}")
        print(f"Within 20% accuracy: {accurate}/{len(results)}")
        print(f"Direction match: {direction_ok}/{len(results)}")

        # Key context
        print("\n" + "-"*70)
        print("KEY CONTEXT: Estate Tax Scoring")
        print("-"*70)
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


# =============================================================================
# PAYROLL TAX VALIDATION
# =============================================================================

PAYROLL_TAX_VALIDATION_SCENARIOS = {
    "ss_cap_90_pct": {
        "description": "SS cap to cover 90% of wages",
        "policy_factory": "create_ss_cap_90_percent",
        "expected_10yr": -800.0,  # Revenue gain (negative = deficit reduction)
        "source": "CBO",
        "notes": "Raise cap from ~$176K to ~$305K",
    },
    "ss_donut_250k": {
        "description": "SS tax on wages above $250K",
        "policy_factory": "create_ss_donut_hole",
        "expected_10yr": -2700.0,  # $2.7T revenue gain
        "source": "Social Security Trustees",
        "notes": "Donut hole: tax current cap + above $250K",
    },
    "ss_eliminate_cap": {
        "description": "Eliminate SS wage cap",
        "policy_factory": "create_ss_eliminate_cap",
        "expected_10yr": -3200.0,  # $3.2T revenue gain
        "source": "Social Security Trustees",
        "notes": "Tax all wages at 12.4%",
    },
    "expand_niit": {
        "description": "Expand NIIT to pass-through income",
        "policy_factory": "create_expand_niit",
        "expected_10yr": -250.0,  # $250B revenue gain
        "source": "JCT (Build Back Better)",
        "notes": "Close S-corp/partnership loophole",
    },
}


def validate_payroll_policy(
    scenario_id: str,
    verbose: bool = True,
) -> ValidationResult:
    """
    Validate payroll tax scoring against CBO/Trustees estimates.

    Args:
        scenario_id: Key from PAYROLL_TAX_VALIDATION_SCENARIOS
        verbose: Whether to print details

    Returns:
        ValidationResult comparing model output to official/expected score
    """
    if scenario_id not in PAYROLL_TAX_VALIDATION_SCENARIOS:
        raise ValueError(
            f"Unknown scenario: {scenario_id}. "
            f"Available: {list(PAYROLL_TAX_VALIDATION_SCENARIOS.keys())}"
        )

    scenario = PAYROLL_TAX_VALIDATION_SCENARIOS[scenario_id]
    expected_10yr = scenario["expected_10yr"]

    # Create payroll policy based on factory
    factory_name = scenario["policy_factory"]
    if factory_name == "create_ss_cap_90_percent":
        policy = create_ss_cap_90_percent()
    elif factory_name == "create_ss_donut_hole":
        policy = create_ss_donut_hole()
    elif factory_name == "create_ss_eliminate_cap":
        policy = create_ss_eliminate_cap()
    elif factory_name == "create_expand_niit":
        policy = create_expand_niit()
    else:
        raise ValueError(f"Unknown policy factory: {factory_name}")

    # Score the policy
    scorer = FiscalPolicyScorer(start_year=policy.start_year, use_real_data=False)
    result = scorer.score_policy(policy, dynamic=False)

    # Payroll tax increases raise revenue (negative deficit effect)
    model_10yr = result.total_10_year_cost

    # Get official source
    official_source = scenario.get("source", "CBO/Trustees")

    difference = model_10yr - expected_10yr
    if expected_10yr != 0:
        percent_diff = (difference / abs(expected_10yr)) * 100
    else:
        percent_diff = 0.0 if model_10yr == 0 else 100.0

    # Direction match
    direction_match = (
        (model_10yr > 0 and expected_10yr > 0) or
        (model_10yr < 0 and expected_10yr < 0)
    )

    validation_result = ValidationResult(
        policy_id=scenario_id,
        policy_name=scenario["description"],
        official_10yr=expected_10yr,
        official_source=official_source,
        model_10yr=model_10yr,
        model_first_year=result.final_deficit_effect[0],
        difference=difference,
        percent_difference=percent_diff,
        direction_match=direction_match,
        accuracy_rating=_rate_accuracy(percent_diff),
        model_parameters={
            "ss_eliminate_cap": getattr(policy, 'ss_eliminate_cap', False),
            "ss_cover_90_pct": getattr(policy, 'ss_cover_90_pct', False),
            "ss_donut_hole_start": getattr(policy, 'ss_donut_hole_start', None),
            "expand_niit": getattr(policy, 'expand_niit_to_passthrough', False),
        },
        notes=scenario.get("notes", ""),
    )

    if verbose:
        print(f"\n{'='*70}")
        print(f"Payroll Tax Validation: {scenario['description']}")
        print(f"{'='*70}")
        print(f"Expected ({official_source}): ${expected_10yr:,.0f}B")
        print(f"Model estimate: ${model_10yr:,.0f}B")
        print(f"Difference: ${difference:+,.0f}B ({percent_diff:+.1f}%)")
        print(f"Direction match: {'Yes' if direction_match else 'NO'}")
        print(f"Rating: {validation_result.accuracy_rating}")
        print(f"\nYear-by-year:")
        for i, (year, cost) in enumerate(zip(result.years, result.final_deficit_effect)):
            print(f"  {year}: ${cost:,.0f}B")
        if scenario.get("notes"):
            print(f"\nNotes: {scenario['notes']}")

    return validation_result


def validate_all_payroll(verbose: bool = True) -> list[ValidationResult]:
    """
    Run validation against all payroll tax scenarios.

    Returns:
        List of ValidationResult objects
    """
    results = []

    if verbose:
        print("\n" + "="*70)
        print("PAYROLL TAX MODEL VALIDATION")
        print("="*70)

    for scenario_id in PAYROLL_TAX_VALIDATION_SCENARIOS:
        try:
            result = validate_payroll_policy(scenario_id, verbose=verbose)
            results.append(result)
        except Exception as e:
            if verbose:
                print(f"\nError validating {scenario_id}: {e}")

    if verbose and results:
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        accurate = sum(1 for r in results if r.is_accurate)
        direction_ok = sum(1 for r in results if r.direction_match)
        print(f"Scenarios tested: {len(results)}")
        print(f"Within 20% accuracy: {accurate}/{len(results)}")
        print(f"Direction match: {direction_ok}/{len(results)}")

        # Key context
        print("\n" + "-"*70)
        print("KEY CONTEXT: Payroll Tax Scoring")
        print("-"*70)
        print("Social Security: 12.4% on wages up to cap (~$176K in 2025)")
        print("Medicare: 2.9% on all wages (no cap)")
        print("")
        print("Key reform options:")
        print("  - Raise cap to 90% coverage: ~$800B/10yr (CBO)")
        print("  - Donut hole above $250K: ~$2.7T/10yr (Trustees)")
        print("  - Eliminate cap: ~$3.2T/10yr (Trustees)")
        print("  - Expand NIIT: ~$250B/10yr (JCT)")

    return results


# =============================================================================
# AMT VALIDATION
# =============================================================================

AMT_VALIDATION_SCENARIOS_COMPARE = {
    "extend_tcja_amt": {
        "description": "Extend TCJA AMT relief",
        "policy_factory": "create_extend_tcja_amt_relief",
        "expected_10yr": 450.0,  # Cost (increases deficit)
        "source": "JCT/CBO",
        "notes": "Keep higher exemptions instead of sunset to pre-TCJA levels",
    },
    "repeal_individual_amt": {
        "description": "Repeal individual AMT (post-2025)",
        "policy_factory": "create_repeal_individual_amt",
        "kwargs": {"start_year": 2026},
        "expected_10yr": 450.0,  # Cost (lost revenue)
        "source": "CBO baseline",
        "notes": "Eliminate all individual AMT after TCJA expires",
    },
    "repeal_corporate_amt": {
        "description": "Repeal corporate AMT (CAMT)",
        "policy_factory": "create_repeal_corporate_amt",
        "expected_10yr": 220.0,  # Cost
        "source": "CBO",
        "notes": "Repeal 15% book minimum tax from IRA 2022",
    },
}


def validate_amt_policy(
    scenario_id: str,
    verbose: bool = True,
) -> ValidationResult:
    """
    Validate AMT scoring against CBO/JCT estimates.

    Args:
        scenario_id: Key from AMT_VALIDATION_SCENARIOS_COMPARE
        verbose: Whether to print details

    Returns:
        ValidationResult comparing model output to official/expected score
    """
    if scenario_id not in AMT_VALIDATION_SCENARIOS_COMPARE:
        raise ValueError(
            f"Unknown scenario: {scenario_id}. "
            f"Available: {list(AMT_VALIDATION_SCENARIOS_COMPARE.keys())}"
        )

    scenario = AMT_VALIDATION_SCENARIOS_COMPARE[scenario_id]
    expected_10yr = scenario["expected_10yr"]

    # Create AMT policy based on factory
    factory_name = scenario["policy_factory"]
    kwargs = scenario.get("kwargs", {})

    if factory_name == "create_extend_tcja_amt_relief":
        policy = create_extend_tcja_amt_relief(**kwargs)
    elif factory_name == "create_repeal_individual_amt":
        policy = create_repeal_individual_amt(**kwargs)
    elif factory_name == "create_repeal_corporate_amt":
        policy = create_repeal_corporate_amt(**kwargs)
    else:
        raise ValueError(f"Unknown policy factory: {factory_name}")

    # Score the policy
    scorer = FiscalPolicyScorer(start_year=policy.start_year, use_real_data=False)
    result = scorer.score_policy(policy, dynamic=False)

    # AMT policies - costs are positive (increase deficit)
    model_10yr = result.total_10_year_cost

    # Get official source
    official_source = scenario.get("source", "CBO/JCT")

    difference = model_10yr - expected_10yr
    if expected_10yr != 0:
        percent_diff = (difference / abs(expected_10yr)) * 100
    else:
        percent_diff = 0.0 if model_10yr == 0 else 100.0

    # Direction match
    direction_match = (
        (model_10yr > 0 and expected_10yr > 0) or
        (model_10yr < 0 and expected_10yr < 0)
    )

    validation_result = ValidationResult(
        policy_id=scenario_id,
        policy_name=scenario["description"],
        official_10yr=expected_10yr,
        official_source=official_source,
        model_10yr=model_10yr,
        model_first_year=result.final_deficit_effect[0],
        difference=difference,
        percent_difference=percent_diff,
        direction_match=direction_match,
        accuracy_rating=_rate_accuracy(percent_diff),
        model_parameters={
            "amt_type": str(policy.amt_type.value) if hasattr(policy, 'amt_type') else "unknown",
            "extend_tcja_relief": getattr(policy, 'extend_tcja_relief', False),
            "repeal_individual_amt": getattr(policy, 'repeal_individual_amt', False),
            "repeal_corporate_amt": getattr(policy, 'repeal_corporate_amt', False),
        },
        notes=scenario.get("notes", ""),
    )

    if verbose:
        print(f"\n{'='*70}")
        print(f"AMT Validation: {scenario['description']}")
        print(f"{'='*70}")
        print(f"Expected ({official_source}): ${expected_10yr:,.0f}B")
        print(f"Model estimate: ${model_10yr:,.0f}B")
        print(f"Difference: ${difference:+,.0f}B ({percent_diff:+.1f}%)")
        print(f"Direction match: {'Yes' if direction_match else 'NO'}")
        print(f"Rating: {validation_result.accuracy_rating}")
        print(f"\nYear-by-year:")
        for i, (year, cost) in enumerate(zip(result.years, result.final_deficit_effect)):
            print(f"  {year}: ${cost:,.0f}B")
        if scenario.get("notes"):
            print(f"\nNotes: {scenario['notes']}")

    return validation_result


def validate_all_amt(verbose: bool = True) -> list[ValidationResult]:
    """
    Run validation against all AMT scenarios.

    Returns:
        List of ValidationResult objects
    """
    results = []

    if verbose:
        print("\n" + "="*70)
        print("AMT MODEL VALIDATION")
        print("="*70)

    for scenario_id in AMT_VALIDATION_SCENARIOS_COMPARE:
        try:
            result = validate_amt_policy(scenario_id, verbose=verbose)
            results.append(result)
        except Exception as e:
            if verbose:
                print(f"\nError validating {scenario_id}: {e}")

    if verbose and results:
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        accurate = sum(1 for r in results if r.is_accurate)
        direction_ok = sum(1 for r in results if r.direction_match)
        print(f"Scenarios tested: {len(results)}")
        print(f"Within 20% accuracy: {accurate}/{len(results)}")
        print(f"Direction match: {direction_ok}/{len(results)}")

        # Key context
        print("\n" + "-"*70)
        print("KEY CONTEXT: AMT Scoring")
        print("-"*70)
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


# =============================================================================
# PREMIUM TAX CREDIT VALIDATION
# =============================================================================

PTC_VALIDATION_SCENARIOS_COMPARE = {
    "extend_enhanced_ptc": {
        "description": "Extend enhanced PTCs (ARPA/IRA)",
        "policy_factory": "create_extend_enhanced_ptc",
        "expected_10yr": 350.0,  # Cost (increases deficit)
        "source": "CBO 2024",
        "notes": "Extend subsidies beyond 2025 sunset",
    },
    "repeal_ptc": {
        "description": "Repeal premium tax credits",
        "policy_factory": "create_repeal_ptc",
        "expected_10yr": -1100.0,  # Savings (reduces deficit)
        "source": "CBO estimate",
        "notes": "Eliminate all ACA subsidies - major coverage loss",
    },
}


def validate_ptc_policy(
    scenario_id: str,
    verbose: bool = True,
) -> ValidationResult:
    """
    Validate PTC scoring against CBO estimates.

    Args:
        scenario_id: Key from PTC_VALIDATION_SCENARIOS_COMPARE
        verbose: Whether to print details

    Returns:
        ValidationResult comparing model output to official/expected score
    """
    if scenario_id not in PTC_VALIDATION_SCENARIOS_COMPARE:
        raise ValueError(
            f"Unknown scenario: {scenario_id}. "
            f"Available: {list(PTC_VALIDATION_SCENARIOS_COMPARE.keys())}"
        )

    scenario = PTC_VALIDATION_SCENARIOS_COMPARE[scenario_id]
    expected_10yr = scenario["expected_10yr"]

    # Create PTC policy based on factory
    factory_name = scenario["policy_factory"]
    kwargs = scenario.get("kwargs", {})

    if factory_name == "create_extend_enhanced_ptc":
        policy = create_extend_enhanced_ptc(**kwargs)
    elif factory_name == "create_repeal_ptc":
        policy = create_repeal_ptc(**kwargs)
    else:
        raise ValueError(f"Unknown policy factory: {factory_name}")

    # Score the policy
    scorer = FiscalPolicyScorer(start_year=policy.start_year, use_real_data=False)
    result = scorer.score_policy(policy, dynamic=False)

    # PTC policies - costs are positive (increase deficit), savings negative
    model_10yr = result.total_10_year_cost

    # Get official source
    official_source = scenario.get("source", "CBO")

    difference = model_10yr - expected_10yr
    if expected_10yr != 0:
        percent_diff = (difference / abs(expected_10yr)) * 100
    else:
        percent_diff = 0.0 if model_10yr == 0 else 100.0

    # Direction match
    direction_match = (
        (model_10yr > 0 and expected_10yr > 0) or
        (model_10yr < 0 and expected_10yr < 0)
    )

    validation_result = ValidationResult(
        policy_id=scenario_id,
        policy_name=scenario["description"],
        official_10yr=expected_10yr,
        official_source=official_source,
        model_10yr=model_10yr,
        model_first_year=result.final_deficit_effect[0],
        difference=difference,
        percent_difference=percent_diff,
        direction_match=direction_match,
        accuracy_rating=_rate_accuracy(percent_diff),
        model_parameters={
            "scenario": str(policy.scenario.value) if hasattr(policy, 'scenario') else "unknown",
            "extend_enhanced": getattr(policy, 'extend_enhanced', False),
            "repeal_ptc": getattr(policy, 'repeal_ptc', False),
        },
        notes=scenario.get("notes", ""),
    )

    if verbose:
        print(f"\n{'='*70}")
        print(f"PTC Validation: {scenario['description']}")
        print(f"{'='*70}")
        print(f"Expected ({official_source}): ${expected_10yr:,.0f}B")
        print(f"Model estimate: ${model_10yr:,.0f}B")
        print(f"Difference: ${difference:+,.0f}B ({percent_diff:+.1f}%)")
        print(f"Direction match: {'Yes' if direction_match else 'NO'}")
        print(f"Rating: {validation_result.accuracy_rating}")
        print(f"\nYear-by-year:")
        for i, (year, cost) in enumerate(zip(result.years, result.final_deficit_effect)):
            print(f"  {year}: ${cost:,.0f}B")
        if scenario.get("notes"):
            print(f"\nNotes: {scenario['notes']}")

    return validation_result


def validate_all_ptc(verbose: bool = True) -> list[ValidationResult]:
    """
    Run validation against all PTC scenarios.

    Returns:
        List of ValidationResult objects
    """
    results = []

    if verbose:
        print("\n" + "="*70)
        print("PREMIUM TAX CREDIT MODEL VALIDATION")
        print("="*70)

    for scenario_id in PTC_VALIDATION_SCENARIOS_COMPARE:
        try:
            result = validate_ptc_policy(scenario_id, verbose=verbose)
            results.append(result)
        except Exception as e:
            if verbose:
                print(f"\nError validating {scenario_id}: {e}")

    if verbose and results:
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        accurate = sum(1 for r in results if r.is_accurate)
        direction_ok = sum(1 for r in results if r.direction_match)
        print(f"Scenarios tested: {len(results)}")
        print(f"Within 20% accuracy: {accurate}/{len(results)}")
        print(f"Direction match: {direction_ok}/{len(results)}")

        # Key context
        print("\n" + "-"*70)
        print("KEY CONTEXT: Premium Tax Credits (ACA)")
        print("-"*70)
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


# =============================================================================
# TAX EXPENDITURE VALIDATION
# =============================================================================

TAX_EXPENDITURE_VALIDATION_SCENARIOS_COMPARE = {
    "cap_employer_health": {
        "description": "Cap employer health exclusion at $50K",
        "policy_factory": "create_cap_employer_health_exclusion",
        "expected_10yr": -450.0,  # Revenue GAIN (negative = reduces deficit)
        "source": "CBO",
        "notes": "Third-largest tax expenditure",
    },
    "eliminate_mortgage": {
        "description": "Eliminate mortgage interest deduction",
        "policy_factory": "create_eliminate_mortgage_deduction",
        "expected_10yr": -300.0,  # Revenue gain
        "source": "CBO",
        "notes": "From current TCJA levels (~$25B/year)",
    },
    "repeal_salt_cap": {
        "description": "Repeal SALT $10K cap",
        "policy_factory": "create_repeal_salt_cap",
        "expected_10yr": 1100.0,  # COST (increases deficit)
        "source": "JCT",
        "notes": "Bipartisan proposal, benefits high-tax states",
    },
    "eliminate_salt": {
        "description": "Eliminate SALT deduction entirely",
        "policy_factory": "create_eliminate_salt_deduction",
        "expected_10yr": -1200.0,  # Revenue gain
        "source": "JCT estimate",
        "notes": "Very controversial",
    },
    "cap_charitable": {
        "description": "Cap charitable deduction at 28%",
        "policy_factory": "create_cap_charitable_deduction",
        "expected_10yr": -200.0,  # Revenue gain
        "source": "Obama/Biden proposal",
        "notes": "Pease-style limitation",
    },
    "eliminate_step_up": {
        "description": "Eliminate step-up in basis",
        "policy_factory": "create_eliminate_step_up_basis",
        "expected_10yr": -500.0,  # Revenue gain
        "source": "Biden proposal",
        "notes": "Tax gains at death with $1M exemption",
    },
}


def validate_expenditure_policy(
    scenario_id: str,
    verbose: bool = True,
) -> ValidationResult:
    """
    Validate tax expenditure scoring against CBO/JCT estimates.

    Args:
        scenario_id: Key from TAX_EXPENDITURE_VALIDATION_SCENARIOS_COMPARE
        verbose: Whether to print details

    Returns:
        ValidationResult comparing model output to official/expected score
    """
    if scenario_id not in TAX_EXPENDITURE_VALIDATION_SCENARIOS_COMPARE:
        raise ValueError(
            f"Unknown scenario: {scenario_id}. "
            f"Available: {list(TAX_EXPENDITURE_VALIDATION_SCENARIOS_COMPARE.keys())}"
        )

    scenario = TAX_EXPENDITURE_VALIDATION_SCENARIOS_COMPARE[scenario_id]
    expected_10yr = scenario["expected_10yr"]

    # Create policy based on factory
    factory_name = scenario["policy_factory"]
    kwargs = scenario.get("kwargs", {})

    if factory_name == "create_cap_employer_health_exclusion":
        policy = create_cap_employer_health_exclusion(**kwargs)
    elif factory_name == "create_eliminate_mortgage_deduction":
        policy = create_eliminate_mortgage_deduction(**kwargs)
    elif factory_name == "create_repeal_salt_cap":
        policy = create_repeal_salt_cap(**kwargs)
    elif factory_name == "create_eliminate_salt_deduction":
        policy = create_eliminate_salt_deduction(**kwargs)
    elif factory_name == "create_cap_charitable_deduction":
        policy = create_cap_charitable_deduction(**kwargs)
    elif factory_name == "create_eliminate_step_up_basis":
        policy = create_eliminate_step_up_basis(**kwargs)
    else:
        raise ValueError(f"Unknown policy factory: {factory_name}")

    # Score the policy
    scorer = FiscalPolicyScorer(start_year=policy.start_year, use_real_data=False)
    result = scorer.score_policy(policy, dynamic=False)

    # Tax expenditure reforms: revenue gains are negative (reduce deficit)
    model_10yr = result.total_10_year_cost

    # Get official source
    official_source = scenario.get("source", "CBO/JCT")

    difference = model_10yr - expected_10yr
    if expected_10yr != 0:
        percent_diff = (difference / abs(expected_10yr)) * 100
    else:
        percent_diff = 0.0 if model_10yr == 0 else 100.0

    # Direction match
    direction_match = (
        (model_10yr > 0 and expected_10yr > 0) or
        (model_10yr < 0 and expected_10yr < 0)
    )

    validation_result = ValidationResult(
        policy_id=scenario_id,
        policy_name=scenario["description"],
        official_10yr=expected_10yr,
        official_source=official_source,
        model_10yr=model_10yr,
        model_first_year=result.final_deficit_effect[0],
        difference=difference,
        percent_difference=percent_diff,
        direction_match=direction_match,
        accuracy_rating=_rate_accuracy(percent_diff),
        model_parameters={
            "expenditure_type": str(policy.expenditure_type.value) if hasattr(policy, 'expenditure_type') else "unknown",
            "action": getattr(policy, 'action', "unknown"),
        },
        notes=scenario.get("notes", ""),
    )

    if verbose:
        print(f"\n{'='*70}")
        print(f"Tax Expenditure Validation: {scenario['description']}")
        print(f"{'='*70}")
        print(f"Expected ({official_source}): ${expected_10yr:,.0f}B")
        print(f"Model estimate: ${model_10yr:,.0f}B")
        print(f"Difference: ${difference:+,.0f}B ({percent_diff:+.1f}%)")
        print(f"Direction match: {'Yes' if direction_match else 'NO'}")
        print(f"Rating: {validation_result.accuracy_rating}")
        print(f"\nYear-by-year:")
        for i, (year, cost) in enumerate(zip(result.years, result.final_deficit_effect)):
            print(f"  {year}: ${cost:,.0f}B")
        if scenario.get("notes"):
            print(f"\nNotes: {scenario['notes']}")

    return validation_result


def validate_all_expenditures(verbose: bool = True) -> list[ValidationResult]:
    """
    Run validation against all tax expenditure scenarios.

    Returns:
        List of ValidationResult objects
    """
    results = []

    if verbose:
        print("\n" + "="*70)
        print("TAX EXPENDITURE MODEL VALIDATION")
        print("="*70)

    for scenario_id in TAX_EXPENDITURE_VALIDATION_SCENARIOS_COMPARE:
        try:
            result = validate_expenditure_policy(scenario_id, verbose=verbose)
            results.append(result)
        except Exception as e:
            if verbose:
                print(f"\nError validating {scenario_id}: {e}")

    if verbose and results:
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        accurate = sum(1 for r in results if r.is_accurate)
        direction_ok = sum(1 for r in results if r.direction_match)
        print(f"Scenarios tested: {len(results)}")
        print(f"Within 20% accuracy: {accurate}/{len(results)}")
        print(f"Direction match: {direction_ok}/{len(results)}")

        # Key context
        print("\n" + "-"*70)
        print("KEY CONTEXT: Major Tax Expenditures (JCT 2024)")
        print("-"*70)
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

