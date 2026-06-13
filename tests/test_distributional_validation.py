"""
Tests for distributional validation helpers.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from fiscal_model.validation.distributional_validation import (
    DISTRIBUTIONAL_BENCHMARKS,
    TPC_CAPITAL_GAINS_INCREASE,
    TPC_CORPORATE_RATE_INCREASE,
    TPC_TCJA_2018,
    DistributionalBenchmark,
    print_validation_report,
    validate_distribution,
    validate_tcja_distribution,
)


def _make_result(quintile: str, avg_change: float, share: float):
    return SimpleNamespace(
        income_group=SimpleNamespace(name=quintile),
        tax_change_avg=avg_change,
        share_of_total_change=share,
    )


def _model_from_benchmark(benchmark: DistributionalBenchmark, inflation_adj: float = 1.0):
    return SimpleNamespace(
        year=2024,
        results=[
            _make_result(name, avg * inflation_adj, share)
            for name, (avg, share) in benchmark.quintile_data.items()
        ],
    )


def test_validate_tcja_distribution_scores_matching_data_as_excellent():
    model_results = SimpleNamespace(
        year=2024,
        results=[
            _make_result(name, avg * 1.25, share)
            for name, (avg, share) in TPC_TCJA_2018.quintile_data.items()
        ],
    )

    validation = validate_tcja_distribution(model_results)

    assert validation["overall_score"] == "EXCELLENT"
    assert validation["overall_share_error"] == 0
    assert len(validation["quintile_comparison"]) == len(TPC_TCJA_2018.quintile_data)


def test_print_validation_report_emits_summary(capsys):
    validation = {
        "benchmark": "TCJA",
        "benchmark_year": 2018,
        "model_year": 2024,
        "overall_score": "GOOD",
        "overall_share_error": 12.5,
        "quintile_comparison": [
            {
                "quintile": "Middle Quintile",
                "model_share": 0.10,
                "tpc_share": 0.10,
                "share_error_pct": 0.0,
            }
        ],
    }

    print_validation_report(validation)
    output = capsys.readouterr().out

    assert "DISTRIBUTIONAL VALIDATION REPORT" in output
    assert "Middle Quintile" in output


class TestBenchmarkIntegrity:
    """The published benchmarks should be internally consistent."""

    def test_registry_contains_all_benchmarks(self):
        assert set(DISTRIBUTIONAL_BENCHMARKS) >= {
            "tcja_2018", "tcja_2027",
            "corporate_rate_increase", "capital_gains_increase",
        }
        for bench in DISTRIBUTIONAL_BENCHMARKS.values():
            assert isinstance(bench, DistributionalBenchmark)
            assert bench.quintile_data

    def test_burden_shares_sum_to_one(self):
        # Tax-increase benchmarks: the quintile shares of the total increase
        # should sum to ~1.0.
        for bench in (TPC_CORPORATE_RATE_INCREASE, TPC_CAPITAL_GAINS_INCREASE):
            total = sum(share for _avg, share in bench.quintile_data.values())
            assert total == pytest.approx(1.0, abs=1e-6)

    def test_capital_gains_more_concentrated_than_corporate(self):
        # Realised gains are more top-skewed than corporate incidence.
        cg_top = TPC_CAPITAL_GAINS_INCREASE.quintile_data["Top Quintile"][1]
        corp_top = TPC_CORPORATE_RATE_INCREASE.quintile_data["Top Quintile"][1]
        assert cg_top > corp_top

    def test_bottom_four_quintiles_bear_little_of_capital_gains(self):
        bottom = sum(
            share
            for name, (_avg, share) in TPC_CAPITAL_GAINS_INCREASE.quintile_data.items()
            if name != "Top Quintile"
        )
        assert bottom < 0.05


class TestGenericValidator:
    def test_perfect_match_scores_excellent(self):
        for bench in (TPC_CORPORATE_RATE_INCREASE, TPC_CAPITAL_GAINS_INCREASE):
            model = _model_from_benchmark(bench)
            validation = validate_distribution(model, bench)
            assert validation["overall_score"] == "EXCELLENT"
            assert validation["overall_share_error"] == pytest.approx(0.0)

    def test_inflation_adjustment_is_applied(self):
        # When the model is the benchmark scaled by inflation, shares still
        # match perfectly (shares are scale-invariant) and the adjusted dollar
        # figure is recorded.
        model = _model_from_benchmark(TPC_TCJA_2018, inflation_adj=1.25)
        validation = validate_distribution(model, TPC_TCJA_2018, inflation_adj=1.25)
        assert validation["overall_share_error"] == pytest.approx(0.0)

    def test_no_overlap_returns_sentinel(self):
        # A model whose quintiles don't match the benchmark's names.
        model = SimpleNamespace(
            year=2024,
            results=[_make_result("Decile 1", 100, 0.5)],
        )
        validation = validate_distribution(model, TPC_CORPORATE_RATE_INCREASE)
        assert validation["overall_score"] == "NO OVERLAP"
        assert validation["quintile_comparison"] == []

    def test_tcja_wrapper_matches_generic(self):
        model = _model_from_benchmark(TPC_TCJA_2018, inflation_adj=1.25)
        via_wrapper = validate_tcja_distribution(model)
        via_generic = validate_distribution(model, TPC_TCJA_2018, inflation_adj=1.25)
        assert via_wrapper["overall_score"] == via_generic["overall_score"]
        assert via_wrapper["overall_share_error"] == pytest.approx(
            via_generic["overall_share_error"]
        )
