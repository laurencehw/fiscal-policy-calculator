"""Pins the corporate +1pp Outlook-vintage install and the two readings beside it.

``scripts/corporate_options_vintage_gap.py`` is CHECK-ONLY. Since
``planning/lanes/CORP_outlook_vintages.md`` the install has happened: each of
the four Tier 1 Options rows names the CBO Outlook its own volume was priced
against, ``data_files/corporate/cbo_corporate_receipts.csv`` carries a block for
each, and what the script used to print as a *prediction* is the **live** score.

Three quantities, and this file exists so they can never be confused:

``live`` / ``contemporaneous``
    The score, and the script's reconstruction of it on that edition's own
    Outlook path, agreeing to the dollar.
``pre_install``
    History — what each row scored when all four windows read February 2024.
``first_year_mts``
    R3's diagnostic, computed on the pre-install figure, which is what R3
    computed it on. It was never the install and must not be quoted as its
    outturn.
"""

from __future__ import annotations

from scripts.corporate_options_vintage_gap import build_report


def _row(report: dict, policy_id: str) -> dict:
    for row in report["rows"]:
        if row["policy_id"] == policy_id:
            return row
    raise AssertionError(f"{policy_id} missing from vintage-gap report")


def test_the_own_outlook_identity_reproduces_the_live_scores() -> None:
    """The reconstruction now checks the *installed* path, not the old one."""
    report = build_report()
    for row in report["rows"]:
        assert row["reconstruction_gap"] < report["reconstruction_tolerance_billions"]


def test_each_row_scores_on_the_outlook_its_own_volume_names() -> None:
    report = build_report()
    assert _row(report, "cbo2019_opt24_corporate_rate_1pp")[
        "contemporaneous_vintage"
    ] == "cbo_apr_2018"
    assert _row(report, "cbo2021_opt19_corporate_rate_1pp")[
        "contemporaneous_vintage"
    ] == "cbo_sep_2020"
    assert _row(report, "cbo2023_opt50_corporate_rate_1pp")[
        "contemporaneous_vintage"
    ] == "cbo_may_2022"
    assert _row(report, "cbo_opt64_corporate_rate_1pp")[
        "contemporaneous_vintage"
    ] == "cbo_feb_2024"
    # Every block a score reads is CBO's own published path, every year of it.
    for row in report["rows"]:
        assert row["contemporaneous_sourcing"] == "published_path"


def test_the_install_landed_on_its_pre_registered_figures() -> None:
    report = build_report()

    row_2018 = _row(report, "cbo2019_opt24_corporate_rate_1pp")
    row_2020 = _row(report, "cbo2021_opt19_corporate_rate_1pp")
    row_2022 = _row(report, "cbo2023_opt50_corporate_rate_1pp")
    row_2024 = _row(report, "cbo_opt64_corporate_rate_1pp")

    # The live figures ``CORP_outlook_vintages.md`` §3.1 registered before
    # ``corporate.py`` was opened.
    assert round(row_2018["error_pct"], 1) == 53.4
    assert round(row_2020["error_pct"], 1) == 21.8
    assert round(row_2022["error_pct"], 1) == 41.6
    assert round(row_2024["error_pct"], 1) == 44.5

    # HISTORY: what the same four rows read on the February 2024 block alone.
    assert round(row_2018["pre_install_error_pct"], 1) == 99.7
    assert round(row_2020["pre_install_error_pct"], 1) == 93.1
    assert round(row_2022["pre_install_error_pct"], 1) == 49.2
    assert round(row_2024["pre_install_error_pct"], 1) == 44.5

    # R3's first-year MTS diagnostic, kept so it cannot be quoted as the
    # install. It is computed on the PRE-INSTALL figure, which is the quantity
    # R3 computed it on; deflating the live score would be a third number.
    assert round(row_2018["first_year_mts_deflated_error_pct"], 1) == 10.0
    assert round(row_2020["first_year_mts_deflated_error_pct"], 1) == 42.2
    assert round(row_2022["first_year_mts_deflated_error_pct"], 1) == 25.3
    assert row_2018["error_pct"] > row_2018["first_year_mts_deflated_error_pct"]
    assert row_2020["error_pct"] < row_2020["first_year_mts_deflated_error_pct"]


def test_the_2024_row_did_not_move_and_that_is_the_falsification_test() -> None:
    """FY2025-2034 *is* the February 2024 block, so naming it must change nothing.

    A lane that installs three older receipts paths and moves the one row that
    already had its own has changed something else.
    """
    report = build_report()
    row_2024 = _row(report, "cbo_opt64_corporate_rate_1pp")
    assert abs(row_2024["model_10yr_billions"] - (-196.081903)) < 0.005
    # The engine sums its own year path and the script sums its
    # reconstruction, so they agree to summation order (~2e-13 of a
    # billion) rather than bit for bit. "To the cent" is 1e-11 here.
    assert abs(
        row_2024["model_10yr_billions"] - row_2024["pre_install_model_10yr"]
    ) < 1e-9
    assert abs(row_2024["receipts_ratio_pre_install_over_contemporaneous"] - 1.0) < 1e-9


def test_the_install_was_worth_about_125_error_mass() -> None:
    report = build_report()
    assert round(report["live_class_mean_pct"], 1) == 40.3
    assert round(report["pre_install_class_mean_pct"], 1) == 71.6
    assert round(report["mass_reduction"], 1) == 125.2
    # The two older editions do almost all of it; May 2022 is the tidy-up.
    by_id = {row["policy_id"]: row for row in report["rows"]}
    older = sum(
        by_id[pid]["pre_install_error_pct"] - by_id[pid]["error_pct"]
        for pid in (
            "cbo2019_opt24_corporate_rate_1pp",
            "cbo2021_opt19_corporate_rate_1pp",
        )
    )
    assert round(older, 1) == 117.6


def test_what_the_install_did_not_close() -> None:
    """40.3% is one gap read four times, not four findings — and it is still there.

    After the vintage is right, ``0.808 / JCT's own implied share - 1``
    reproduces each row's error, which is why the class mean is still 40%. A
    later reader must not take 71.6% -> 40.3% as an accuracy claim about the
    module's marginal share, which did not move by a decimal.
    """
    report = build_report()
    assert report["live_class_mean_pct"] > 35.0
    assert report["base_per_dollar_of_receipts"] > 4.8
    # One anchor ratio for all four paths (§1.4): a per-edition anchor would be
    # a fitted degree of freedom per row.
    assert len({row["contemporaneous_vintage"] for row in report["rows"]}) == 4
