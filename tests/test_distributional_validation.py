"""
Tests for distributional validation helpers.
"""

from __future__ import annotations

from types import SimpleNamespace

from fiscal_model.validation.distributional_validation import (
    TPC_TCJA_2018,
    print_validation_report,
    validate_tcja_distribution,
)


def _make_result(quintile: str, avg_change: float, share: float):
    return SimpleNamespace(
        income_group=SimpleNamespace(name=quintile),
        tax_change_avg=avg_change,
        share_of_total_change=share,
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
