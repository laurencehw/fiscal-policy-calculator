"""
Focused coverage for fiscal_model.data.validation helper branches.
"""

from __future__ import annotations

import logging
from types import SimpleNamespace

import pandas as pd

from fiscal_model.data.validation import DataValidator, ValidationResult


def test_validate_irs_table_1_1_collects_multiple_issues():
    df = pd.DataFrame(
        {
            "other": [1, 2],
            "returns_total": [50_000_000, -1],
        }
    )

    result = DataValidator.validate_irs_table_1_1(df, 2022)

    assert result.passed is False
    assert "validation failed" in result.message.lower()
    issues = result.details["issues"]
    assert any("Missing expected columns" in issue for issue in issues)
    assert any("Negative values found in column: returns_total" == issue for issue in issues)
    assert any("outside expected range" in issue for issue in issues)


def test_validate_irs_table_3_3_flags_missing_columns_and_low_revenue():
    df = pd.DataFrame(
        {
            "tax_liability": [900.0, 200.0],
            "other": [1, 2],
        }
    )

    result = DataValidator.validate_irs_table_3_3(df, 2022)

    assert result.passed is False
    issues = result.details["issues"]
    assert any("Missing expected columns" in issue for issue in issues)
    assert any("outside expected range" in issue for issue in issues)


def test_validate_fred_series_handles_recent_nans_and_series_specific_ranges():
    bad_unrate = pd.Series([3.5, 4.0, float("nan"), 20.0])
    bad_rate = pd.Series([2.0, 25.0])
    bad_civpart = pd.Series([54.0])

    unrate_result = DataValidator.validate_fred_series(bad_unrate, "UNRATE")
    rate_result = DataValidator.validate_fred_series(bad_rate, "DGS10")
    civpart_result = DataValidator.validate_fred_series(bad_civpart, "CIVPART")

    assert unrate_result.passed is False
    assert any("NaN values in recent data" in issue for issue in unrate_result.details["issues"])
    assert any("outside expected range" in issue for issue in unrate_result.details["issues"])
    assert rate_result.passed is False
    assert "10-year rate" in rate_result.details["issues"][0]
    assert civpart_result.passed is False
    assert "Labor force participation" in civpart_result.details["issues"][0]


def test_validate_fred_series_unknown_series_returns_latest_value_only():
    result = DataValidator.validate_fred_series(pd.Series([1.0, 2.0, 3.0]), "CUSTOM")

    assert result.passed is True
    assert result.details == {"latest_value": 3.0}


def test_validate_all_irs_data_wraps_loader_failures():
    irs_data = SimpleNamespace(
        load_table_1_1=lambda year: pd.DataFrame(
            {"returns": [120_000_000], "agi": [5_000_000_000_000], "income": [5_500_000_000_000]}
        ),
        load_table_3_3=lambda year: (_ for _ in ()).throw(FileNotFoundError(f"missing {year}")),
    )

    results = DataValidator.validate_all_irs_data(irs_data, 2022)

    assert len(results) == 2
    assert results[0].passed is True
    assert results[1].passed is False
    assert "Failed to load Table 3.3 for 2022" in results[1].message


def test_validate_all_fred_data_collects_successes_and_failures():
    series_map = {
        "GDP": pd.Series([28_000.0]),
        "GDPC1": pd.Series([22_000.0]),
        "UNRATE": pd.Series([4.0]),
        "DGS10": pd.Series([4.2]),
        "CIVPART": pd.Series([62.5]),
    }

    fred_data = SimpleNamespace(
        get_series=lambda series_id: series_map[series_id]
        if series_id in series_map
        else (_ for _ in ()).throw(RuntimeError("no api")),
    )

    results = DataValidator.validate_all_fred_data(fred_data)

    assert len(results) == 6
    assert sum(result.passed for result in results) == 5
    assert results[-1].passed is False
    assert "Failed to load FRED series CPIAUCSL" in results[-1].message


def test_print_validation_report_emits_logs_and_details(capsys, caplog):
    results = [
        ValidationResult(True, "Good", details={"latest_value": 3.0}),
        ValidationResult(False, "Bad", details={"issues": ["problem"]}),
    ]

    with caplog.at_level(logging.INFO):
        DataValidator.print_validation_report(results)

    output = capsys.readouterr().out

    assert "DATA VALIDATION REPORT" in output
    assert "SUMMARY: 1/2 checks passed" in output
    assert "latest_value: 3.0" in output
    assert "issues: ['problem']" in output
    assert any("1 validation check(s) failed" in record.getMessage() for record in caplog.records)
