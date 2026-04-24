"""
Tests for the CBO/JCT distributional benchmark suite.

These tests cover the benchmark database and comparison engine; they do
not yet exercise the model's own microsim against the benchmarks (that
needs the Priority-1 CPS microsim to be in place). See the scaffolding
plan in ``docs/CHANGELOG.md``.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from fiscal_model.validation.cbo_distributions import (
    CBO_ARP_2021,
    CBO_JCT_BENCHMARKS,
    CBO_TCJA_2018,
    CORPORATE_INCIDENCE_SOURCES,
    BenchmarkComparison,
    CBODistributionalBenchmark,
    DistributionSource,
    JCT_CORPORATE_28_2022,
    JCT_SALT_REPEAL_2024,
    JCT_TCJA_2019,
    compare_distribution,
    format_comparison,
    run_full_cbo_jct_validation,
)


# ---------------------------------------------------------------------------
# Benchmark database sanity
# ---------------------------------------------------------------------------


class TestBenchmarkDatabase:
    def test_all_benchmarks_have_nonempty_rows(self):
        for benchmark in CBO_JCT_BENCHMARKS:
            assert benchmark.rows, f"{benchmark.policy_id} has no rows"

    def test_tcja_benchmarks_are_net_cuts(self):
        """Every row in a tax cut should have avg_tax_change < 0."""
        for benchmark in (CBO_TCJA_2018, JCT_TCJA_2019):
            for row in benchmark.rows:
                assert row.avg_tax_change_dollars <= 0, (
                    f"{benchmark.policy_id} {row.group_label}: expected cut"
                )

    def test_tcja_shares_approximately_sum_to_minus_one(self):
        """A net cut's shares should sum to roughly -1.0 (±5% from rounding)."""
        for benchmark in (CBO_TCJA_2018, JCT_TCJA_2019):
            total = sum(row.share_of_total for row in benchmark.rows)
            assert -1.05 <= total <= -0.95, (
                f"{benchmark.policy_id}: shares sum to {total}, "
                "expected ~-1.0 for a net cut"
            )

    def test_arp_concentrated_at_bottom(self):
        """ARP refundable credits should give more (in share) to bottom deciles."""
        rows = CBO_ARP_2021.rows
        lowest = rows[0].share_of_total
        highest = rows[-1].share_of_total
        # Both negative (cuts); |lowest| > |highest| means bottom gets more.
        assert abs(lowest) > abs(highest)

    def test_salt_repeal_concentrated_at_top(self):
        """SALT cap repeal should give ~66% of the cut to filers >$500k."""
        top_share = sum(
            r.share_of_total
            for r in JCT_SALT_REPEAL_2024.rows
            if r.group_label in {"$500k–$1M", "$1M+"}
        )
        # Cut → negative shares; top_share should be < -0.60 (60%+ of cut at top).
        assert top_share < -0.60
        # And the bottom two classes essentially get nothing.
        bottom_share = sum(
            r.share_of_total
            for r in JCT_SALT_REPEAL_2024.rows
            if r.group_label in {"<$50k", "$50k–$100k"}
        )
        assert abs(bottom_share) < 0.01

    def test_corporate_benchmark_records_incidence_split(self):
        """JCT corporate benchmark must record its 75/25 capital-labor split."""
        assert JCT_CORPORATE_28_2022.corporate_incidence_capital_share == 0.75

    def test_corporate_28_is_revenue_raise(self):
        """A corporate rate increase should yield positive shares (deficit cut)."""
        non_total = [
            r for r in JCT_CORPORATE_28_2022.rows if r.group_label != "Total"
        ]
        assert all(r.avg_tax_change_dollars >= 0 for r in non_total)
        assert sum(r.share_of_total for r in non_total) == pytest.approx(1.0, abs=0.02)

    def test_sources_are_distinct(self):
        sources = {b.source for b in CBO_JCT_BENCHMARKS}
        # At least two independent agencies represented.
        assert len(sources) >= 2


# ---------------------------------------------------------------------------
# Corporate-incidence disagreement
# ---------------------------------------------------------------------------


class TestCorporateIncidence:
    def test_capital_shares_span_expected_range(self):
        shares = sorted(a.capital_share for a in CORPORATE_INCIDENCE_SOURCES)
        assert shares[0] == pytest.approx(0.75)  # CBO/JCT floor
        assert shares[-1] == pytest.approx(0.82)  # Treasury ceiling

    def test_each_assumption_sums_to_one(self):
        for a in CORPORATE_INCIDENCE_SOURCES:
            total = a.capital_share + a.labor_share + a.consumer_share
            assert total == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Comparison engine
# ---------------------------------------------------------------------------


def _fake_model_result_matching(benchmark: CBODistributionalBenchmark):
    """Build a model-result stand-in whose shares exactly match the benchmark."""
    rows = []
    for bench in benchmark.rows:
        rows.append(
            SimpleNamespace(
                income_group=SimpleNamespace(name=bench.group_label),
                tax_change_avg=bench.avg_tax_change_dollars,
                share_of_total_change=bench.share_of_total,
            )
        )
    return SimpleNamespace(results=rows)


def _fake_model_result_biased(benchmark: CBODistributionalBenchmark, bias_pp: float):
    """Build a model-result with a constant share-bias in percentage points."""
    rows = []
    for bench in benchmark.rows:
        rows.append(
            SimpleNamespace(
                income_group=SimpleNamespace(name=bench.group_label),
                tax_change_avg=bench.avg_tax_change_dollars,
                share_of_total_change=bench.share_of_total + bias_pp / 100.0,
            )
        )
    return SimpleNamespace(results=rows)


class TestCompareDistribution:
    def test_exact_match_scores_excellent(self):
        result = _fake_model_result_matching(JCT_TCJA_2019)
        comparison = compare_distribution(result, JCT_TCJA_2019)
        assert comparison.overall_rating == "excellent"
        assert comparison.mean_absolute_share_error_pp == pytest.approx(0.0)
        assert len(comparison.per_group) == len(JCT_TCJA_2019.rows)

    def test_small_bias_scores_good_or_acceptable(self):
        result = _fake_model_result_biased(JCT_TCJA_2019, bias_pp=3.0)
        comparison = compare_distribution(result, JCT_TCJA_2019)
        # 3pp bias translated through absolute-share comparison lands in
        # the "good" / "acceptable" range. The exact mean is slightly
        # below 3pp because some benchmark rows have |share| < 3pp, so
        # adding 3pp flips their sign and the absolute gap is smaller.
        assert comparison.overall_rating in {"acceptable", "good"}
        assert comparison.mean_absolute_share_error_pp is not None
        assert 2.0 <= comparison.mean_absolute_share_error_pp <= 3.0

    def test_large_bias_flags_improvement(self):
        # Need a large bias to cross the 10pp rating threshold after
        # sign-flip cancellation. 25pp is clearly above the threshold
        # for every benchmark row.
        result = _fake_model_result_biased(CBO_TCJA_2018, bias_pp=25.0)
        comparison = compare_distribution(result, CBO_TCJA_2018)
        assert comparison.overall_rating == "needs_improvement"

    def test_no_overlap_reports_cleanly(self):
        """When group labels don't match, the comparison degrades gracefully."""
        mismatched = SimpleNamespace(
            results=[
                SimpleNamespace(
                    income_group=SimpleNamespace(name="<$5k"),
                    tax_change_avg=-10,
                    share_of_total_change=-0.01,
                )
            ]
        )
        comparison = compare_distribution(mismatched, JCT_TCJA_2019)
        assert comparison.overall_rating == "no_overlap"
        assert comparison.mean_absolute_share_error_pp is None

    def test_format_comparison_includes_source(self):
        result = _fake_model_result_matching(CBO_TCJA_2018)
        rendered = format_comparison(compare_distribution(result, CBO_TCJA_2018))
        assert "CBO" in rendered or "Congressional Budget" in rendered
        assert "Decile 1 (lowest)" in rendered


class TestFullValidationRunner:
    def test_runs_every_benchmark_with_matching_runner(self):
        comparisons = run_full_cbo_jct_validation(_fake_model_result_matching)
        assert len(comparisons) == len(CBO_JCT_BENCHMARKS)
        assert all(isinstance(c, BenchmarkComparison) for c in comparisons)
        assert all(c.overall_rating == "excellent" for c in comparisons)

    def test_runner_skips_benchmarks_when_model_returns_none(self):
        def only_tcja(benchmark):
            return _fake_model_result_matching(benchmark) if "tcja" in benchmark.policy_id else None

        comparisons = run_full_cbo_jct_validation(only_tcja)
        assert len(comparisons) == 2  # CBO_TCJA_2018 + JCT_TCJA_2019

    def test_source_enum_roundtrip(self):
        """DistributionSource must be round-trippable through its value."""
        for benchmark in CBO_JCT_BENCHMARKS:
            assert DistributionSource(benchmark.source.value) is benchmark.source
