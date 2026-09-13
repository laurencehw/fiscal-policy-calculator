"""Pins the corporate +1pp vintage-gap diagnostic.

``scripts/corporate_options_vintage_gap.py`` is CHECK-ONLY: it scores the four
Tier 1 Options rows on the shipped February 2024 receipts path and on the
contemporaneous Outlook annuals already transcribed in
``corporate_yield_reconciliation.BASELINES``. The planning note
``planning/lanes/CORP_class_accuracy.md`` quotes those leftovers. This test
fails if the install prediction is silently replaced by the first-year MTS
diagnostic R3 published (10.0% / 42.2% on the 2018 / 2020 rows), which is a
different quantity.
"""

from __future__ import annotations

from scripts.corporate_options_vintage_gap import build_report


def _row(report: dict, policy_id: str) -> dict:
    for row in report["rows"]:
        if row["policy_id"] == policy_id:
            return row
    raise AssertionError(f"{policy_id} missing from vintage-gap report")


def test_shipped_identity_reproduces_the_live_scores() -> None:
    report = build_report()
    for row in report["rows"]:
        assert row["shipped_reconstruction_gap"] < report["reconstruction_tolerance_billions"]


def test_contemporaneous_outlooks_leave_the_share_gap_not_the_first_year_mts_diagnostic() -> None:
    report = build_report()

    row_2018 = _row(report, "cbo2019_opt24_corporate_rate_1pp")
    row_2020 = _row(report, "cbo2021_opt19_corporate_rate_1pp")
    row_2022 = _row(report, "cbo2023_opt50_corporate_rate_1pp")
    row_2024 = _row(report, "cbo_opt64_corporate_rate_1pp")

    # Live figures R3 registered and this tree still scores.
    assert round(row_2018["error_pct"], 1) == 99.7
    assert round(row_2020["error_pct"], 1) == 93.1
    assert round(row_2022["error_pct"], 1) == 49.2
    assert round(row_2024["error_pct"], 1) == 44.5

    # The quantity a lane would install — each option's own Outlook path.
    assert round(row_2018["contemporaneous_error_pct"], 1) == 53.4
    assert round(row_2020["contemporaneous_error_pct"], 1) == 21.8
    assert round(row_2022["contemporaneous_error_pct"], 1) == 41.6
    assert round(row_2024["contemporaneous_error_pct"], 1) == 44.5

    # R3's first-year MTS diagnostic, kept so it cannot be quoted as the install.
    assert round(row_2018["first_year_mts_deflated_error_pct"], 1) == 10.0
    assert round(row_2020["first_year_mts_deflated_error_pct"], 1) == 42.2
    assert row_2018["contemporaneous_error_pct"] > row_2018["first_year_mts_deflated_error_pct"]
    assert row_2020["contemporaneous_error_pct"] < row_2020["first_year_mts_deflated_error_pct"]

    # 2024 is already on its own path; wiring older Outlooks must not move it.
    assert abs(row_2024["model_10yr_billions"] - row_2024["contemporaneous_model_10yr"]) < 0.05


def test_wiring_three_outlooks_is_worth_about_125_error_mass() -> None:
    report = build_report()
    assert round(report["live_class_mean_pct"], 1) == 71.6
    assert round(report["contemporaneous_class_mean_pct"], 1) == 40.3
    assert round(report["mass_reduction"], 1) == 125.2
    # 2024's receipts path is the February 2024 block; ratio 1.000 is the
    # falsification that a "transcribe historical paths" lane has a no-op row.
    row_2024 = _row(report, "cbo_opt64_corporate_rate_1pp")
    assert abs(row_2024["receipts_ratio_shipped_over_contemporaneous"] - 1.0) < 1e-9
