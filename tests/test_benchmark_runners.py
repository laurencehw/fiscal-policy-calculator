"""
Integration tests for the CBO/JCT benchmark runner.

These tests exercise ``default_model_runner`` end-to-end against the
distributional engine. They lock in the *current* model-vs-benchmark
comparisons so future changes to the distributional engine that
inadvertently degrade an accuracy number will fail loudly.

The exact mean-absolute-share-error thresholds are set with a little
headroom so day-to-day refactoring is not noisy, but tightening them
is a deliberate decision: if a benchmark moves from "acceptable" to
"good", the threshold should follow.
"""

from __future__ import annotations

from fiscal_model.validation.benchmark_runners import default_model_runner
from fiscal_model.validation.cbo_distributions import (
    CBO_ARP_2021,
    CBO_TCJA_2018,
    JCT_CORPORATE_28_2022,
    JCT_TCJA_2019,
    compare_distribution,
    run_full_cbo_jct_validation,
)


class TestEndToEndBenchmarks:
    def test_cbo_tcja_2018_every_decile_matches(self):
        result = default_model_runner(CBO_TCJA_2018)
        assert result is not None
        comparison = compare_distribution(result, CBO_TCJA_2018)
        assert len(comparison.per_group) == len(CBO_TCJA_2018.rows), (
            f"Label-normalisation dropped rows: {len(comparison.per_group)}/"
            f"{len(CBO_TCJA_2018.rows)}"
        )
        # Lock in current accuracy with headroom. If the engine improves
        # and this becomes too loose, tighten.
        assert comparison.mean_absolute_share_error_pp is not None
        assert comparison.mean_absolute_share_error_pp < 10.0

    def test_jct_tcja_2019_agi_class_matches(self):
        result = default_model_runner(JCT_TCJA_2019)
        assert result is not None
        comparison = compare_distribution(result, JCT_TCJA_2019)
        assert len(comparison.per_group) == len(JCT_TCJA_2019.rows)
        assert comparison.overall_rating in {"good", "acceptable"}

    def test_cbo_arp_2021_quintile_matches(self):
        result = default_model_runner(CBO_ARP_2021)
        assert result is not None
        comparison = compare_distribution(result, CBO_ARP_2021)
        # All five quintiles must match.
        assert len(comparison.per_group) == len(CBO_ARP_2021.rows)
        # Current engine misses CTC non-filer correction; known outlier.
        assert comparison.mean_absolute_share_error_pp is not None
        assert comparison.mean_absolute_share_error_pp < 15.0

    def test_jct_corporate_28_2022_rated_good(self):
        """
        Corporate benchmark: after the distribution_effects.calculate_corporate_effect
        fix (SOI Table 1.4-calibrated capital/labor tier lookup), this benchmark
        moved from 15.25pp (needs_improvement) to ~2.5pp (good).
        """
        result = default_model_runner(JCT_CORPORATE_28_2022)
        assert result is not None
        comparison = compare_distribution(result, JCT_CORPORATE_28_2022)
        assert len(comparison.per_group) > 0
        assert comparison.mean_absolute_share_error_pp is not None
        # Lock in the current accuracy with headroom so a regression
        # in the capital/labor tier tables fails this test.
        assert comparison.mean_absolute_share_error_pp < 5.0
        assert comparison.overall_rating in {"good", "acceptable"}

    def test_full_runner_executes_every_benchmark(self):
        comparisons = run_full_cbo_jct_validation(default_model_runner)
        # All 4 mapped benchmarks should produce a result.
        assert len(comparisons) == 4
        for c in comparisons:
            # No crashes, each comparison is well-formed.
            assert c.benchmark is not None
            assert c.overall_rating in {
                "excellent",
                "good",
                "acceptable",
                "needs_improvement",
                "no_overlap",
            }
