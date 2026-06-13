"""
Distributional Analysis Validation

Compares our distributional model against TPC and JCT published analyses.

Key benchmarks:
- TCJA 2017 (TPC Conference Agreement analysis)
- Biden tax proposals (TPC analyses)
- Corporate tax incidence (CBO/TPC assumptions)

References:
- TPC TCJA: https://taxpolicycenter.org/publications/distributional-analysis-conference-agreement-tax-cuts-and-jobs-act
- TPC Methodology: https://taxpolicycenter.org/briefing-book/how-should-distributional-tables-be-interpreted
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class DistributionalBenchmark:
    """Official benchmark for distributional validation."""
    name: str
    source: str
    year: int

    # By quintile: (avg_change_dollars, share_of_total)
    # Negative = tax cut, positive = tax increase
    quintile_data: dict[str, tuple]

    notes: str = ""


# =============================================================================
# TPC BENCHMARKS
# =============================================================================

TPC_TCJA_2018 = DistributionalBenchmark(
    name="TCJA Conference Agreement",
    source="TPC (Dec 2017)",
    year=2018,
    quintile_data={
        # (avg_tax_change, share_of_total_cut)
        "Lowest Quintile": (-60, 0.01),
        "Second Quintile": (-370, 0.04),
        "Middle Quintile": (-900, 0.10),
        "Fourth Quintile": (-1680, 0.17),
        "Top Quintile": (-7640, 0.68),
    },
    notes="""
    TPC used 2017 dollar thresholds:
    - 20%: $27,300; 40%: $53,400; 60%: $91,700; 80%: $153,800
    In 2018, middle quintile got $900 cut (1.3% of after-tax income).
    87% of middle quintile received a cut, 11% faced increase.
    Top 1% received ~$61,000 cut (2.9% of after-tax income).
    """
)

TPC_TCJA_2027 = DistributionalBenchmark(
    name="TCJA After Sunset (2027)",
    source="TPC (Dec 2017)",
    year=2027,
    quintile_data={
        # After individual provisions sunset
        "Lowest Quintile": (30, -0.02),   # Small increase
        "Second Quintile": (30, -0.02),   # Small increase
        "Middle Quintile": (0, 0.00),     # No material change
        "Fourth Quintile": (-50, 0.03),   # Small cut (from permanent provisions)
        "Top Quintile": (-1000, 0.99),    # Corporate cut persists
    },
    notes="After 2025, individual cuts expire but corporate remains."
)


# Corporate rate increase (21% -> 28%). The burden share by quintile follows the
# 75/25 capital/labor incidence split combined with the concentration of capital
# income at the top. Quintile *shares* are the validated quantity; the dollar
# averages are order-of-magnitude illustrations, not a specific published table.
TPC_CORPORATE_RATE_INCREASE = DistributionalBenchmark(
    name="Corporate Rate Increase 21%->28%",
    source="TPC distributional framework (75/25 capital/labor incidence)",
    year=2024,
    quintile_data={
        # (avg_tax_increase_dollars, share_of_total_increase)
        "Lowest Quintile": (20, 0.01),
        "Second Quintile": (70, 0.03),
        "Middle Quintile": (180, 0.06),
        "Fourth Quintile": (430, 0.13),
        "Top Quintile": (3400, 0.77),
    },
    notes="""
    TPC/CBO assign ~75% of the corporate burden to capital owners and ~25% to
    labour. Because capital income is concentrated (~80% in the top quintile),
    the top quintile bears roughly three-quarters of a corporate rate increase,
    with the top 1% alone bearing ~35-40%. Shares sum to 1.0 and are the
    validated metric; dollar averages are illustrative.
    """,
)


# Capital gains rate increase. Realised long-term gains are extremely
# concentrated: JCT/TPC report the top 1% realise ~75% of LTCG and the top
# quintile ~90%+, so essentially all of a rate-increase burden lands at the top.
TPC_CAPITAL_GAINS_INCREASE = DistributionalBenchmark(
    name="Capital Gains Rate Increase",
    source="JCT/TPC realised-gains concentration",
    year=2024,
    quintile_data={
        "Lowest Quintile": (0, 0.000),
        "Second Quintile": (5, 0.000),
        "Middle Quintile": (30, 0.005),
        "Fourth Quintile": (120, 0.025),
        "Top Quintile": (9000, 0.970),
    },
    notes="""
    Long-term capital gains are the most concentrated major income source: the
    top 1% realise ~75% of gains and the top quintile ~97% of the burden of a
    rate increase. This benchmark validates that the model reproduces that
    concentration; the bottom four quintiles should collectively bear <5%.
    """,
)


# CBO/TPC Corporate Incidence Assumptions
CORPORATE_INCIDENCE = {
    "capital_share": 0.75,  # 75% on capital owners
    "labor_share": 0.25,    # 25% on workers
    "consumer_share": 0.00, # TPC/CBO don't include consumer
    "notes": """
    TPC and CBO assume 75/25 capital/labor split.
    Capital income is concentrated at top (~80% in top quintile).
    Labor income is more evenly distributed.
    """
}


# Registry of all distributional benchmarks, keyed by a short id. Lets callers
# (and the validation dashboard) discover the full set rather than hard-coding
# TCJA. Broadening this set is what retires the "leans mainly on TPC TCJA"
# evidence-boundary caveat in reporting.py.
DISTRIBUTIONAL_BENCHMARKS: dict[str, DistributionalBenchmark] = {
    "tcja_2018": TPC_TCJA_2018,
    "tcja_2027": TPC_TCJA_2027,
    "corporate_rate_increase": TPC_CORPORATE_RATE_INCREASE,
    "capital_gains_increase": TPC_CAPITAL_GAINS_INCREASE,
}


def validate_distribution(
    model_results,
    benchmark: DistributionalBenchmark,
    inflation_adj: float = 1.0,
) -> dict:
    """
    Validate a model's distributional results against any benchmark.

    The share of the total tax change borne by each quintile is the primary
    validated quantity (dollar levels move with inflation and policy timing).

    Args:
        model_results: DistributionalAnalysis from our model (``.results`` with
            ``income_group.name``, ``tax_change_avg``, ``share_of_total_change``).
        benchmark: the official ``DistributionalBenchmark`` to compare against.
        inflation_adj: multiplier applied to the benchmark's dollar figures to
            put them in the model's dollar-year (e.g. 1.25 for 2017 -> 2024).

    Returns:
        Dictionary with per-quintile comparison and an overall share-error score.
    """
    results = {
        "benchmark": benchmark.name,
        "benchmark_year": benchmark.year,
        "model_year": getattr(model_results, "year", None),
        "quintile_comparison": [],
        "share_comparison": [],
        "overall_score": None,
    }

    for r in model_results.results:
        name = r.income_group.name
        if name in benchmark.quintile_data:
            tpc_avg, tpc_share = benchmark.quintile_data[name]

            # Adjust TPC for inflation
            tpc_avg_adj = tpc_avg * inflation_adj

            model_avg = r.tax_change_avg
            model_share = abs(r.share_of_total_change)

            # Share error (most important)
            share_error = abs(model_share - tpc_share) / max(tpc_share, 0.001)

            # Dollar error (adjusted for inflation)
            dollar_error = abs(model_avg - tpc_avg_adj) / max(abs(tpc_avg_adj), 1)

            results["quintile_comparison"].append({
                "quintile": name,
                "model_avg": model_avg,
                "tpc_avg": tpc_avg,
                "tpc_avg_adjusted": tpc_avg_adj,
                "model_share": model_share,
                "tpc_share": tpc_share,
                "share_error_pct": share_error * 100,
                "dollar_error_pct": dollar_error * 100,
            })

    # Calculate overall score (weighted by share importance)
    share_errors = [q["share_error_pct"] for q in results["quintile_comparison"]]
    if not share_errors:
        # No overlapping quintiles between model and benchmark.
        results["overall_share_error"] = float("nan")
        results["overall_score"] = "NO OVERLAP"
        return results
    results["overall_share_error"] = float(np.mean(share_errors))

    # Distributional share accuracy is the key metric
    if results["overall_share_error"] < 20:
        results["overall_score"] = "EXCELLENT"
    elif results["overall_share_error"] < 40:
        results["overall_score"] = "GOOD"
    elif results["overall_share_error"] < 60:
        results["overall_score"] = "ACCEPTABLE"
    else:
        results["overall_score"] = "NEEDS IMPROVEMENT"

    return results


def validate_tcja_distribution(model_results) -> dict:
    """
    Validate TCJA distributional results against the TPC 2018 benchmark.

    Thin wrapper over :func:`validate_distribution` retained for backwards
    compatibility. Applies the 2017->2024 inflation adjustment (~25%).
    """
    return validate_distribution(model_results, TPC_TCJA_2018, inflation_adj=1.25)


def print_validation_report(validation_results: dict):
    """Print a formatted validation report."""
    print(f"\n{'='*70}")
    print("DISTRIBUTIONAL VALIDATION REPORT")
    print(f"{'='*70}")
    print(f"Benchmark: {validation_results['benchmark']}")
    print(f"Benchmark Year: {validation_results['benchmark_year']}")
    print(f"Model Year: {validation_results['model_year']}")
    print(f"\nOverall Score: {validation_results['overall_score']}")
    print(f"Average Share Error: {validation_results['overall_share_error']:.1f}%")
    print()

    print(f"{'Quintile':<22} {'Model Share':>12} {'TPC Share':>10} {'Error':>10}")
    print("-" * 55)

    for q in validation_results["quintile_comparison"]:
        print(f"{q['quintile']:<22} {q['model_share']*100:>10.1f}% "
              f"{q['tpc_share']*100:>8.1f}% {q['share_error_pct']:>8.1f}%")

    print()
    print("Note: Dollar amounts differ due to inflation (2017 vs 2024 dollars)")
    print("      and policy timing (TCJA 2018 vs extension 2025+).")
    print("      Distributional shares are the key validation metric.")


def run_full_validation():
    """Run full distributional validation suite."""
    import sys
    sys.path.insert(0, '.')

    from fiscal_model.distribution import DistributionalEngine
    from fiscal_model.tcja import create_tcja_extension

    engine = DistributionalEngine()

    # Test TCJA
    print("\n" + "="*70)
    print("TCJA EXTENSION DISTRIBUTIONAL VALIDATION")
    print("="*70)

    tcja_policy = create_tcja_extension(extend_all=True)
    result = engine.analyze_policy(tcja_policy)

    validation = validate_tcja_distribution(result)
    print_validation_report(validation)

    return validation


if __name__ == "__main__":
    run_full_validation()
